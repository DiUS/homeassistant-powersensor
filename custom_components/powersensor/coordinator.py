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



class PowersensorDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the plug."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        scan_interval = None
    ) -> None:
        """Initialize."""
        if scan_interval is None:
            scan_interval = DEFAULT_SCAN_INTERVAL

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )
        self._message_cache = {}
        self.sensor_data = dict()
        self._mac = entry.data["mac"]
        self._api = PlugApi(mac=entry.data["mac"], ip=entry.data["host"], port=entry.data["port"])
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
        for ev in known_evs:
            self._api.subscribe(ev, self.handle_message)

        self._api.connect()

        self.plug_data = {
            PlugMeasurements.WATTS : 0.0,
            PlugMeasurements.VOLTAGE : 0.0,
            PlugMeasurements.APPARENT_CURRENT :  0.0,
            PlugMeasurements.ACTIVE_CURRENT :  0.0,
            PlugMeasurements.REACTIVE_CURRENT :  0.0,
            PlugMeasurements.SUMMATION_ENERGY: 0.0,
        }

    async def start(self):
        """Start up plug api"""
        try:
            await asyncio.to_thread(self._api.connect)
        except Exception as err:
            _LOGGER.error("Error starting Plug listener!: %s", err)

    async def stop(self):
        """stop listening to plug"""
        await self._api.disconnect()

    async def _async_update_data(self):
        return self.plug_data

    async def handle_message(self, event, message):
        if event == 'average_power':
            if message['mac'] == self._mac:
                self.plug_data[PlugMeasurements.WATTS] = message['watts']
                # _LOGGER.error(
                #     f"Plug watts received over UDP, updating... to {message['watts']}, {message['mac'] == self._mac}")
        elif event == 'average_power_components':
            if message['mac'] == self._mac:
                self.plug_data[PlugMeasurements.VOLTAGE] = message['volts']
                self.plug_data[PlugMeasurements.APPARENT_CURRENT] = message['apparent_current']
                self.plug_data[PlugMeasurements.ACTIVE_CURRENT] = message['active_current']
                self.plug_data[PlugMeasurements.REACTIVE_CURRENT] = message['reactive_current']
                # _LOGGER.error(
                #     f"Plug VOLTS received over UDP, updating... to {message}")

        elif event == "summation_energy":
            if message['mac'] == self._mac:
                # convert joules to kWh
                self.plug_data[PlugMeasurements.SUMMATION_ENERGY] = message['summation_joules']/3600000.0
                # _LOGGER.error(
                #     f"Plug Energy received over UDP, updating... to {message['summation_joules']}, {message['mac'] == self._mac}")
        elif event in ['radio_signal_quality', 'battery_level', 'now_relaying_for']:
            await self.handle_device_discovery(message)
            if event == 'radio_signal_quality':
                pass
            elif event == 'battery_level':
                self.sensor_data[message['mac']][SensorMeasurements.Battery] = message['volts']
            elif event == 'now_relaying_for':
                pass
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
                PowersensorSensorEntity(self.hass, self, message['mac'], SensorMeasurements.Battery)
            ]
            self.async_add_sensor_entities(new_sensor_entities)
            _LOGGER.error(f"New sensor found, with Mac Address: {message['mac']}")