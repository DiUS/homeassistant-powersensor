import logging

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import EntityCategory, UnitOfPower, UnitOfElectricPotential, UnitOfElectricCurrent, UnitOfEnergy
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo

from .PlugMeasurements import PlugMeasurements
from .PowersensorEntity import PowersensorEntity
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


_config = {
    PlugMeasurements.WATTS: {
        "name": "Power",
        "device_class": SensorDeviceClass.POWER,
        "unit": UnitOfPower.WATT,
        "precision": 1,
        'event': 'average_power',
        'message_key': 'watts'
    },
    PlugMeasurements.VOLTAGE: {
        "name": "Volts",
        "device_class": SensorDeviceClass.VOLTAGE,
        "unit": UnitOfElectricPotential.VOLT,
        "precision": 2,
        'event': 'average_power_components',
        'message_key': 'volts',
        'visible': False,
    },
    PlugMeasurements.APPARENT_CURRENT: {
        "name": "Apparent Current",
        "device_class": SensorDeviceClass.CURRENT,
        "unit": UnitOfElectricCurrent.AMPERE,
        "precision": 2,
        'event': 'average_power_components',
        'message_key': 'apparent_current',
        'visible': False,
    },
    PlugMeasurements.ACTIVE_CURRENT: {
        "name": "Active Current",
        "device_class": SensorDeviceClass.CURRENT,
        "unit": UnitOfElectricCurrent.AMPERE,
        "precision": 2,
        'event': 'average_power_components',
        'message_key': 'active_current',
        'visible': False,
    },
    PlugMeasurements.REACTIVE_CURRENT: {
        "name": "Reactive Current",
        "device_class": SensorDeviceClass.CURRENT,
        "unit": UnitOfElectricCurrent.AMPERE,
        "precision": 2,
        'event': 'average_power_components',
        'message_key': 'reactive_current',
        'visible': False,
    },
    PlugMeasurements.SUMMATION_ENERGY: {
        "name": "Total Energy",
        "device_class": SensorDeviceClass.ENERGY,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "precision": 2,
        "state_class": SensorStateClass.TOTAL,
        'event': 'summation_energy',
        'message_key': 'summation_joules',
        'callback' : lambda v : v/3600000.0
    },
    PlugMeasurements.ROLE: {
        'name': 'Device Role',
        'category': EntityCategory.DIAGNOSTIC,
        'event': 'role',
        'message_key': 'role',
    },
}



class PowersensorPlugEntity(PowersensorEntity):
    """Powersensor Plug Class--designed to handle all measurements of the plug--perhaps less expressive"""
    def __init__(self, hass: HomeAssistant, mac_address: str, measurement_type: PlugMeasurements):
        """Initialize the sensor."""
        super().__init__(hass, mac_address, _config, measurement_type)
        self._model = f"PowersensorPlug"
        self.measurement_type = measurement_type
        config = _config[measurement_type]
        self._device_name = self._default_device_name()
        self._attr_name = f"{self._device_name } {config['name']}"

    @property
    def device_info(self) -> DeviceInfo:
        return {
            'identifiers': {(DOMAIN, self._mac)},
            'manufacturer': "Powersensor",
            'model': self._model,
            'name': self._device_name,
        }

    def _default_device_name(self) -> str:
        return f"Powersensor Plug (ID: {self._mac}) 🔌"

