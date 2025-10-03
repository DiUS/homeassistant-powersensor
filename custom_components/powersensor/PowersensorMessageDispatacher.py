import logging

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send, async_dispatcher_connect

from powersensor_local import PlugApi, VirtualHousehold

from custom_components.powersensor.const import POWER_SENSOR_UPDATE_SIGNAL, DOMAIN

_LOGGER = logging.getLogger(__name__)
class PowersensorMessageDispatcher:
    def __init__(self, hass: HomeAssistant, vhh: VirtualHousehold):
        self._hass = hass
        self._vhh = vhh
        self.plugs = dict()
        self.sensors = dict()
        self.on_start_sensor_queue = dict()
        self._unsubscribe_from_sensor_added_signal = (
            async_dispatcher_connect(self._hass,
                                     f"{DOMAIN}_sensor_added_to_homeassistant",
                                     self._acknowledge_sensor_added_to_homeassistant)
        )


    def add_api(self, mac, network_info):

        _LOGGER.info(f"Adding API for mac={network_info['mac']}, ip={network_info['host']}, port={network_info['port']}")
        api = PlugApi(mac=network_info['mac'], ip=network_info['host'], port=network_info['port'])
        self.plugs[mac] = api
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
        if self._unsubscribe_from_sensor_added_signal is not None:
            self._unsubscribe_from_sensor_added_signal()

    @callback
    def _acknowledge_sensor_added_to_homeassistant(self,mac, role):
        self.sensors[mac] = role