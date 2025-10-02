from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.const import UnitOfPower, UnitOfElectricPotential, UnitOfEnergy
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.typing import StateType

from .SensorMeasurements import SensorMeasurements
from .const import DOMAIN, POWER_SENSOR_UPDATE_SIGNAL


def get_config(measurement_type : SensorMeasurements)->dict:
    _config = {
        SensorMeasurements.Battery: {
            "name": "Battery Level",
            "device_class": SensorDeviceClass.VOLTAGE,
            "unit": UnitOfElectricPotential.VOLT,
            "precision": 2,
            'event': 'battery_level',
            'message_key': 'volts'
        },
        SensorMeasurements.WATTS: {
            "name": "Power",
            "device_class": SensorDeviceClass.POWER,
            "unit": UnitOfPower.WATT,
            "precision": 1,
            'event': 'average_power',
            'message_key': 'watts',
        },
        SensorMeasurements.SUMMATION_ENERGY: {
            "name": "Total Energy",
            "device_class": SensorDeviceClass.ENERGY,
            "unit": UnitOfEnergy.KILO_WATT_HOUR,
            "precision": 2,
            "state_class": SensorStateClass.TOTAL,
            'event': 'summation_energy',
            'message_key': 'summation_joules',
            'callback': lambda v: v / 3600000.0
        },
    }
    return _config[measurement_type]

class PowersensorSensorEntity(SensorEntity):
    """Powersensor Plug Class--designed to handle all measurements of the plug--perhaps less expressive"""
    def __init__(self, hass: HomeAssistant, mac : str,
                 measurement_type: SensorMeasurements):
        """Initialize the sensor."""
        self.role = None
        self._has_received_at_least_one_message = False
        self._value = 0.0
        self._hass = hass
        self._mac = mac
        self._model = f"PowersensorSensor"

        self.measurement_type = measurement_type
        config = get_config(measurement_type)
        self._attr_name = f"Sensor MAC address: ({self._mac}) {config['name']}"
        self._attr_unique_id = f"powersensor_{mac}_{measurement_type}"
        self._attr_device_class = config["device_class"]
        self._attr_native_unit_of_measurement = config["unit"]
        self._attr_device_info = self.device_info
        self._attr_suggested_display_precision = config["precision"]
        self._signal = f"{POWER_SENSOR_UPDATE_SIGNAL}_{self._mac}_{config['event']}"
        if 'state_class' in config.keys():
            self._attr_state_class = config['state_class']
        self._message_key = config.get('message_key', None)
        self._message_callback = config.get('callback', None)

    @property
    def device_info(self) -> DeviceInfo:
        return {
            'identifiers': {(DOMAIN, self._mac)},
            'manufacturer': "Powersensor",
            'model': self._model,
            'name': f'Sensor MAC address: ({self._mac})',
            # "via_device": # if we use this, can it be updated dynamically?
        }

    @property
    def native_value(self) -> StateType | date | datetime | Decimal:
        return self._value

    @property
    def available(self) -> bool:
        """Does data exist for this sensor type"""
        return self._has_received_at_least_one_message

    async def async_added_to_hass(self) -> None:
        """Subscribe to messages when added to home assistant"""
        self._has_received_at_least_one_message = False
        self.async_on_remove(async_dispatcher_connect(
            self._hass,
            self._signal,
            self._handle_update
        ))

    @callback
    def _handle_update(self, event, message):
        """handle pushed data."""
        self._has_received_at_least_one_message = True
        if not self.role:
            if 'role' in message.keys():
                self.role = message['role']
        if self._message_key in message.keys():
            if self._message_callback:
                self._value = self._message_callback( message[self._message_key])
            else:
                self._value = message[self._message_key]

        self.async_write_ha_state()