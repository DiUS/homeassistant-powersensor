"""DataUpdateCoordinator for the Powersensor integration."""
import asyncio
import logging
from datetime import timedelta

from enum import Enum

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from powersensor_local import PlugApi


from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)

class PlugMeasurements(Enum):
    WATTS = 1
    VOLTAGE = 2
    APPARENT_CURRENT = 3
    ACTIVE_CURRENT = 4
    REACTIVE_CURRENT =5
    SUMMATION_ENERGY = 6

class SensorMeasurements(Enum):
    Battery  =1
    WATTS = 2
    SUMMATION_ENERGY = 3



class PowersensorDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the plug."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
    ) -> None:
        """Initialize."""

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN
        )
        self.sensor_data = dict()

        self._plug_apis =dict()
        self._ips = dict()

        for mac, network_info in entry.data.items():
            # raise Exception
            _LOGGER.error(f"mac={network_info['mac']}, ip={network_info['host']}, port={network_info['port']}")
            self._plug_apis[mac] = PlugApi(mac=network_info['mac'], ip=network_info['host'], port=network_info['port'])
            self._ips[mac] = network_info['host']
        self.async_add_sensor_entities = None
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
        self.plug_data = dict()
        for mac, api in self._plug_apis.items():
            for ev in known_evs:
                api.subscribe(ev, self.handle_message)
            _LOGGER.error(f"connecting [{mac}]")
            api.connect()

            self.plug_data[mac] = {
                PlugMeasurements.WATTS : 0.0,
                PlugMeasurements.VOLTAGE : 0.0,
                PlugMeasurements.APPARENT_CURRENT :  0.0,
                PlugMeasurements.ACTIVE_CURRENT :  0.0,
                PlugMeasurements.REACTIVE_CURRENT :  0.0,
                PlugMeasurements.SUMMATION_ENERGY: 0.0,
            }


    async def stop(self):
        """stop listening to plug"""
        for mac, api in self._plug_apis.items():
            _LOGGER.warning(
                f"Removing Plug Api with ip={self._ips[mac]} and mac={mac} from {DOMAIN}.")
            await api.disconnect()
            await asyncio.sleep(0)

        #explicitly delete
        for mac in self._plug_apis.keys():
            self._plug_apis[mac] = None
        del self._plug_apis
        self._plug_apis = dict()
        _LOGGER.warning("All UDP listeners closed.")

    async def _async_update_data(self):
        return self.plug_data

    async def handle_message(self, event, message):
        mac = message['mac']
        if mac in self.plug_data.keys():
            # handle plugs
            if event == 'average_power':
                self.plug_data[mac][PlugMeasurements.WATTS] = message['watts']
            elif event == 'average_power_components':
                self.plug_data[mac][PlugMeasurements.VOLTAGE] = message['volts']
                self.plug_data[mac][PlugMeasurements.APPARENT_CURRENT] = message['apparent_current']
                self.plug_data[mac][PlugMeasurements.ACTIVE_CURRENT] = message['active_current']
                self.plug_data[mac][PlugMeasurements.REACTIVE_CURRENT] = message['reactive_current']

            elif event == "summation_energy":
                self.plug_data[mac][PlugMeasurements.SUMMATION_ENERGY] = message['summation_joules']/3600000.0
            else:
                _LOGGER.warning(f"{event}: {message}")
        else:
            # handle sensors
            await self.handle_device_discovery(message)
            if event == 'average_power':
                self.sensor_data[mac][SensorMeasurements.WATTS] = message['watts']
            elif event == "summation_energy":
                self.sensor_data[message['mac']][SensorMeasurements.SUMMATION_ENERGY] = message['summation_joules']/3600000.0
            elif event in ['radio_signal_quality', 'battery_level', 'now_relaying_for']:
                await self.handle_device_discovery(message)
                if event == 'radio_signal_quality':
                    _LOGGER.warning(f"{event}: {message}")
                elif event == 'battery_level':
                    self.sensor_data[message['mac']][SensorMeasurements.Battery] = message['volts']
                elif event == 'now_relaying_for':
                    _LOGGER.warning(f"{event}: {message}")
            else:
                _LOGGER.warning(f"{event}: {message}")

        self.async_update_listeners()

    async def handle_device_discovery(self, message):
        if message['mac'] not in self.sensor_data.keys():
            self.sensor_data[message['mac']] = dict({
                SensorMeasurements.Battery : 0.0
            })

            from .PowersensorSensorEntity import PowersensorSensorEntity
            new_sensor_entities = [
                PowersensorSensorEntity(self.hass, self, message['mac'], SensorMeasurements.Battery),
                PowersensorSensorEntity(self.hass, self, message['mac'], SensorMeasurements.WATTS),
                PowersensorSensorEntity(self.hass, self, message['mac'], SensorMeasurements.SUMMATION_ENERGY)
            ]
            self.async_add_sensor_entities(new_sensor_entities)
            _LOGGER.error(f"New sensor found, with Mac Address: {message['mac']}")
