import asyncio
import datetime
import logging

from homeassistant.core import HomeAssistant, callback
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.dispatcher import async_dispatcher_send, async_dispatcher_connect

from powersensor_local import PlugApi, VirtualHousehold

from custom_components.powersensor.AsyncSet import AsyncSet
from custom_components.powersensor.const import (
    CREATE_PLUG_SIGNAL,
    CREATE_SENSOR_SIGNAL,
    DATA_UPDATE_SIGNAL_FMT_MAC_EVENT,
    PLUG_ADDED_TO_HA_SIGNAL,
    ROLE_UPDATE_SIGNAL,
    SENSOR_ADDED_TO_HA_SIGNAL,
    ZEROCONF_ADD_PLUG_SIGNAL,
    ZEROCONF_REMOVE_PLUG_SIGNAL,
    ZEROCONF_UPDATE_PLUG_SIGNAL,
)

_LOGGER = logging.getLogger(__name__)
class PowersensorMessageDispatcher:
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, vhh: VirtualHousehold, debounce_timeout: float = 60):
        self._hass = hass
        self._entry = entry
        self._vhh = vhh
        self.plugs = dict()
        self._known_plugs = set()
        self._known_plug_names = dict()
        self.sensors = dict()
        self.on_start_sensor_queue = dict()
        self._pending_removals = {}
        self._debounce_seconds = debounce_timeout
        self.has_solar = False
        self._solar_request_limit = datetime.timedelta(seconds = 10)
        self._unsubscribe_from_signals = [
            async_dispatcher_connect(self._hass,
                                     ZEROCONF_ADD_PLUG_SIGNAL,
                                     self._plug_added),
            async_dispatcher_connect(self._hass,
                                     ZEROCONF_UPDATE_PLUG_SIGNAL,
                                     self._plug_updated),
            async_dispatcher_connect(self._hass,
                                     ZEROCONF_REMOVE_PLUG_SIGNAL,
                                     self._schedule_plug_removal),
            async_dispatcher_connect(self._hass,
                                     PLUG_ADDED_TO_HA_SIGNAL,
                                     self._acknowledge_plug_added_to_homeassistant),
            async_dispatcher_connect(self._hass,
                                     SENSOR_ADDED_TO_HA_SIGNAL,
                                     self._acknowledge_sensor_added_to_homeassistant),
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
                    #@todo: maybe better to query the entity registry?
                    if not self._plug_has_been_seen(mac_address, name):
                        async_dispatcher_send(self._hass, CREATE_PLUG_SIGNAL,
                                              mac_address, host, port, name)
                    elif mac_address in self._known_plugs and not mac_address in self.plugs:
                        _LOGGER.info(f"Plug with mac {mac_address} is known, but API is missing."
                                        f"Reconnecting without requesting entity creation...")
                        self._create_api(mac_address,host, port, name)
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


    async def stop_pending_removal_tasks(self):
        """Stop the background removal tasks."""
        for k in range(len(self._pending_removals)):
            if self._pending_removals[k] and not self._pending_removals[k].done():
                self._pending_removals[k].cancel()
                try:
                    await self._pending_removals[k]
                except asyncio.CancelledError:
                    pass
                _LOGGER.debug("Background removal task stopped")
                self._pending_removals[k] = None
        self._pending_removals = []


    def _create_api(self, mac_address, ip, port, name):
        _LOGGER.info(f"Creating API for mac={mac_address}, ip={ip}, port={port}")
        api = PlugApi(mac=mac_address, ip=ip, port=port)
        self.plugs[mac_address] = api
        self._known_plugs.add(mac_address)
        self._known_plug_names[name] = mac_address
        known_evs = [
            #'exception',
            'average_flow',
            'average_power',
            'average_power_components',
            'battery_level',
            'radio_signal_quality',
            'summation_energy',
            'summation_volume',
            #'uncalibrated_instant_reading',
        ]

        for ev in known_evs:
            api.subscribe(ev, self.handle_message)
        api.subscribe('now_relaying_for', self.handle_relaying_for)
        api.connect()

    def cancel_any_pending_removal(self, mac, source):
        task = self._pending_removals.pop(mac, None)
        if task:
            task.cancel()
            _LOGGER.debug(f"Cancelled pending removal for {mac} by {source}.")

    async def handle_relaying_for(self, event: str, message: dict):
        """Handle a potentially new sensor being reported."""
        mac = message.get('mac', None)
        device_type = message.get('device_type', None)
        if mac is None or  device_type != "sensor":
            _LOGGER.warning(f"Ignoring relayed device with MAC \"{mac}\" and type {device_type}")
            return

        persisted_role = self._entry.data.get('roles', {}).get(mac, None)
        role = message.get('role', None)
        _LOGGER.debug(f"Relayed sensor {mac} with role {role} found")

        if mac not in self.sensors:
            _LOGGER.debug(f"Reporting new sensor {mac} with role {role}")
            self.on_start_sensor_queue[mac] = role
            async_dispatcher_send(self._hass, CREATE_SENSOR_SIGNAL, mac, role)
        if role != persisted_role:
            _LOGGER.debug(f"Restoring role for {mac} from {role} to {persisted_role}")
            async_dispatcher_send(self._hass, ROLE_UPDATE_SIGNAL, mac, persisted_role)

    async def handle_message(self, event: str, message: dict):
        mac = message['mac']
        persisted_role = self._entry.data.get('roles', {}).get(mac, None)
        role = message.get('role', persisted_role)
        message['role'] = role

        if role != persisted_role:
            async_dispatcher_send(self._hass, ROLE_UPDATE_SIGNAL, mac, role)

        self.cancel_any_pending_removal(mac, "new message received from plug")

        # Feed the household calculations
        if event == 'average_power':
            await self._vhh.process_average_power_event(message)
        elif event == 'summation_energy':
            await self._vhh.process_summation_event(message)

        async_dispatcher_send(self._hass,
              DATA_UPDATE_SIGNAL_FMT_MAC_EVENT % (mac, event), event, message)

        # Synthesise a role type message for the role diagnostic entity
        async_dispatcher_send(
            self._hass, DATA_UPDATE_SIGNAL_FMT_MAC_EVENT % (mac, 'role'),
            'role', { 'role': role })

    async def disconnect(self):
        for _ in range(len(self.plugs)):
            _, api = self.plugs.popitem()
            await api.disconnect()
        for unsubscribe in self._unsubscribe_from_signals:
            if unsubscribe is not None:
                unsubscribe()

        await self.stop_processing_plug_queue()
        await self.stop_pending_removal_tasks()

    @callback
    def _acknowledge_sensor_added_to_homeassistant(self,mac, role):
        self.sensors[mac] = role

    @callback
    async def _acknowledge_plug_added_to_homeassistant(self, mac_address, host, port, name):
        self._create_api(mac_address, host, port, name)
        await self._plug_added_queue.remove((mac_address, host, port, name))

    async def _plug_added(self, info):
        _LOGGER.debug(f" Request to add plug received: {info}")
        network_info = dict()
        mac = info['properties'][b'id'].decode('utf-8')
        network_info['mac'] = mac
        self.cancel_any_pending_removal(mac, "request to add plug")
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
        self.cancel_any_pending_removal(mac, "request to update plug")
        host = info['addresses'][0]
        port = info['port']
        name = info['name']

        if mac in self.plugs:
            current_api: PlugApi = self.plugs[mac]
            if current_api._listener._ip == host and current_api._listener._port == port:
                _LOGGER.debug(f"Request to update plug with mac {mac} does not alter ip from existing API."
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


    async def _schedule_plug_removal(self, name, info):
        _LOGGER.debug(f" Request to delete plug received: {info}")
        if name in self._known_plug_names:
            mac = self._known_plug_names[name]
            if mac in self.plugs:
                if mac in self._pending_removals:
                    # removal for this service is already pending
                    return

                _LOGGER.debug(f"Scheduling removal for {name}")
                self._pending_removals[mac] = self._hass.async_create_background_task(
                    self._delayed_plug_remove(name,mac),
                    name = f"Removal-Task-For-{name}"
                )
        else:
            _LOGGER.warning(f"Received request to delete api for gateway with name [{name}], but this name"
                            f"is not associated with an existing PlugAPI. Ignoring...")

    async def _delayed_plug_remove(self, name, mac):
        """Actually process the removal after delay."""
        try:
            await asyncio.sleep(self._debounce_seconds)
            _LOGGER.debug(f"Request to remove plug {mac} still pending after timeout. Processing remove request...")
            await self.plugs[mac].disconnect()
            del self.plugs[mac]
            del self._known_plug_names[name]
            _LOGGER.info(f"API for plug {mac} disconnected and removed.")
        except asyncio.CancelledError:
            # Task was canceled because service came back
            _LOGGER.debug(f"Request to remove plug {mac} was cancelled by request to update, add plug or new message.")
            raise
        finally:
            # Either way were done with this task
            self._pending_removals.pop(mac, None)

