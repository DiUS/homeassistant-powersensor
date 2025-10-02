import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send

from powersensor_local import PlugApi

from custom_components.powersensor.const import POWER_SENSOR_UPDATE_SIGNAL, DOMAIN

_LOGGER = logging.getLogger(__name__)
class PowersensorMessageDispatcher:
    def __init__(self, hass: HomeAssistant):
        self._hass = hass
        self.plugs = dict()
        self.sensors = set()


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
                self.sensors.add(mac)
                async_dispatcher_send(self._hass, f"{DOMAIN}_create_sensor", mac )

        async_dispatcher_send(self._hass, f"{POWER_SENSOR_UPDATE_SIGNAL}_{mac}_{event}", event, message)

    async def disconnect(self):
        for _ in range(len(self.plugs)):
            _, api = self.plugs.popitem()
            await api.disconnect()
