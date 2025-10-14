import asyncio
import logging

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send, async_dispatcher_connect

from powersensor_local import PlugApi, VirtualHousehold

from custom_components.powersensor.AsyncSet import AsyncSet
from custom_components.powersensor.const import POWER_SENSOR_UPDATE_SIGNAL, DOMAIN, DEFAULT_PORT

_LOGGER = logging.getLogger(__name__)
class PowersensorMessageDispatcher:
    def __init__(self, hass: HomeAssistant, vhh: VirtualHousehold):
        self._hass = hass
        self._vhh = vhh
        self.plugs = dict()
        self._known_plugs = set()
        self._known_plug_names = dict()
        self.sensors = dict()
        self.on_start_sensor_queue = dict()
        self._unsubscribe_from_signals = [
            async_dispatcher_connect(self._hass,
                                     f"{DOMAIN}_sensor_added_to_homeassistant",
                                     self._acknowledge_sensor_added_to_homeassistant),
            async_dispatcher_connect(self._hass,
                                     f"{DOMAIN}_zeroconf_add_plug",
                                     self._plug_added),
            async_dispatcher_connect(self._hass,
                                     f"{DOMAIN}_zeroconf_update_plug",
                                     self._plug_updated),
            async_dispatcher_connect(self._hass,
                                     f"{DOMAIN}_zeroconf_remove_plug",
                                     self._plug_remove),
            async_dispatcher_connect(self._hass,
                                     f"{DOMAIN}_plug_added_to_homeassistant",
                                     self._acknowledge_plug_added_to_homeassistant),
        ]

        self._monitor_add_plug_queue = None
        self._stop_task = False
        self._plug_added_queue = AsyncSet()
        self._safe_to_process_plug_queue = False

    async def enqueue_plug_for_adding(self, network_info: dict):
        _LOGGER.debug(f"Adding to plug processing queue: {network_info}")
        await self._plug_added_queue.add((network_info['mac'], network_info['host'],
                                          network_info['port'], network_info['name']))

    async def process_plug_queue(self):
        """Start the background task if not already running."""
        self._safe_to_process_plug_queue = True
        if self._monitor_add_plug_queue is None or self._monitor_add_plug_queue.done():
            self._stop_task = False
            self._monitor_add_plug_queue = self._hass.async_create_background_task(self._monitor_plug_queue(), name="plug_queue_monitor")
            _LOGGER.debug("Background task started")

    def _plug_has_been_seen(self, mac_address, name)->bool:
        return mac_address in self.plugs or mac_address in self._known_plugs or name in self._known_plug_names

    async def _monitor_plug_queue(self):
        """The actual background task loop."""
        try:
            while not self._stop_task and self._plug_added_queue:
                queue_snapshot = await self._plug_added_queue.copy()
                for mac_address, host, port, name in queue_snapshot:
                    if not self._plug_has_been_seen(mac_address, name):
                        async_dispatcher_send(self._hass, f"{DOMAIN}_create_plug",
                                              mac_address, host, port, name)
                    else:
                        _LOGGER.debug(f"Plug: {mac_address} has already been created as an entity in Home Assistant."
                                      f" Skipping and flushing from queue.")
                        await self._plug_added_queue.remove((mac_address, host, port, name))


                await asyncio.sleep(5)
            _LOGGER.debug("Plug queue has been processed!")

        except asyncio.CancelledError:
            _LOGGER.debug("Plug queue processing cancelled")
            raise
        except Exception as e:
            _LOGGER.error(f"Error in Plug queue processing task: {e}")
        finally:
            self._monitor_add_plug_queue = None

    async def stop_processing_plug_queue(self):
        """Stop the background task."""
        self._stop_task = True
        if self._monitor_add_plug_queue and not self._monitor_add_plug_queue.done():
            self._monitor_add_plug_queue.cancel()
            try:
                await self._monitor_add_plug_queue
            except asyncio.CancelledError:
                pass
            _LOGGER.debug("Background task stopped")
            self._monitor_add_plug_queue = None

    def _create_api(self, mac_address, ip, port, name):
        _LOGGER.info(f"Creating API for mac={mac_address}, ip={ip}, port={port}")
        api = PlugApi(mac=mac_address, ip=ip, port=port)
        self.plugs[mac_address] = api
        self._known_plugs.add(mac_address)
        self._known_plug_names[name] = mac_address
        known_evs = [
            'exception',
            'average_flow',
            'average_power',
            'average_power_components',
            'battery_level',
            'now_relaying_for',
            'radio_signal_quality',
            'summation_energy',
            'summation_volume',
            'uncalibrated_instant_reading',
        ]

        for ev in known_evs:
            api.subscribe(ev, lambda event, message: self.handle_message( event, message))
        api.connect()

    def add_api(self, network_info):
        _LOGGER.debug("Manually adding API, this could cause API's and entities to get out of sync")
        self._create_api(mac_address=network_info['mac'], ip=network_info['host'],
                         port=network_info['port'], name=network_info['name'])


    async def handle_message(self, event: str, message: dict):
        mac = message['mac']
        if mac not in self.plugs.keys():
            if mac not in self.sensors:
                role = None
                if 'role' in message:
                    self.on_start_sensor_queue[mac] = role
                    role = message['role']
                async_dispatcher_send(self._hass, f"{DOMAIN}_create_sensor", mac, role)

        # Feed the household calculations
        if event == 'average_power':
            await self._vhh.process_average_power_event(message)
        elif event == 'summation_energy':
            await self._vhh.process_summation_event(message)

        async_dispatcher_send(self._hass, f"{POWER_SENSOR_UPDATE_SIGNAL}_{mac}_{event}", event, message)

    async def disconnect(self):
        for _ in range(len(self.plugs)):
            _, api = self.plugs.popitem()
            await api.disconnect()
        for unsubscribe in self._unsubscribe_from_signals:
            if unsubscribe is not None:
                unsubscribe()

        await self.stop_processing_plug_queue()

    @callback
    def _acknowledge_sensor_added_to_homeassistant(self,mac, role):
        self.sensors[mac] = role

    async def _acknowledge_plug_added_to_homeassistant(self, mac_address, host, port, name):
        _LOGGER.info(f"Adding new API for mac={mac_address}, ip={host}, port={port}")
        self._create_api(mac_address, host, port, name)
        await self._plug_added_queue.remove((mac_address, host, port, name))

    async def _plug_added(self, info):
        _LOGGER.debug(f" Request to add plug received: {info}")
        network_info = dict()
        network_info['mac'] = info['properties'][b'id'].decode('utf-8')
        network_info['host'] = info['addresses'][0]
        network_info['port'] = info['port']
        network_info['name'] = info['name']

        if self._safe_to_process_plug_queue:
            await self.enqueue_plug_for_adding(network_info)
            await self.process_plug_queue()
        else:
            await self.enqueue_plug_for_adding(network_info)

    async def _plug_updated(self, info):
        _LOGGER.debug(f" Request to update plug received: {info}")
        mac = info['properties'][b'id'].decode('utf-8')
        host = info['addresses'][0]
        port = info['port']
        name = info['name']

        if mac in self.plugs:
            current_api: PlugApi = self.plugs[mac]
            if current_api._listener._ip == host and current_api._listener._port == port:
                _LOGGER.info(f"Request to update plug with mac {mac} does not alter ip from existing API."
                             f"IP still {host} and port is {port}. Skipping update...")
                return
            await current_api.disconnect()

        if mac in self._known_plugs:
            self._create_api(mac, host, port, name)
        else:
            network_info = dict()
            network_info['mac'] = mac
            network_info['host'] = host
            network_info['port'] = port
            network_info['name'] = name
            await self.enqueue_plug_for_adding(network_info)
            await self.process_plug_queue()

    async def _plug_remove(self,name, info):
        _LOGGER.debug(f" Request to delete plug received: {info}")
        if name in self._known_plug_names:
            mac = self._known_plug_names[name]
            if mac in self.plugs:
                await self.plugs[mac].disconnect()
                del self.plugs[mac]
        else:
            _LOGGER.warning(f"Received request to delete api for gateway with name [{name}], but this name"
                            f"is not associated with an existing PlugAPI. Ignoring...")
