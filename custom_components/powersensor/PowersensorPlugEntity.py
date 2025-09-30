from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.const import UnitOfPower, UnitOfElectricPotential, UnitOfElectricCurrent, UnitOfEnergy
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.typing import StateType

from .coordinator import PlugMeasurements, PowersensorDataUpdateCoordinator
from .const import DOMAIN


class PowersensorPlugEntity(SensorEntity):
    """Powersensor Plug Class--designed to handle all measurements of the plug--perhaps less expressive"""
    def __init__(self, hass: HomeAssistant, coordinator: PowersensorDataUpdateCoordinator, mac_address: str,
                 measurement_type: PlugMeasurements):
        """Initialize the sensor."""
        self.coordinator = coordinator
        self._hass = hass
        self._mac = mac_address
        self._model = f"PowersensorPlug"
        self._config  = {
            PlugMeasurements.WATTS : {
                "name" : "Power",
                "device_class" : SensorDeviceClass.POWER,
                "unit" : UnitOfPower.WATT,
                "precision" : 1
            },
            PlugMeasurements.VOLTAGE: {
                "name": "Volts",
                "device_class": SensorDeviceClass.VOLTAGE,
                "unit": UnitOfElectricPotential.VOLT,
                "precision" : 2
            },
            PlugMeasurements.APPARENT_CURRENT: {
                "name": "Apparent Current",
                "device_class": SensorDeviceClass.CURRENT,
                "unit": UnitOfElectricCurrent.AMPERE,
                "precision": 2
            },
            PlugMeasurements.ACTIVE_CURRENT: {
                "name": "Active Current",
                "device_class": SensorDeviceClass.CURRENT,
                "unit": UnitOfElectricCurrent.AMPERE,
                "precision": 2
            },
            PlugMeasurements.REACTIVE_CURRENT: {
                "name": "Reactive Current",
                "device_class": SensorDeviceClass.CURRENT,
                "unit": UnitOfElectricCurrent.AMPERE,
                "precision": 2
            },
            PlugMeasurements.SUMMATION_ENERGY: {
                "name": "Total Energy",
                "device_class": SensorDeviceClass.ENERGY,
                "unit": UnitOfEnergy.KILO_WATT_HOUR,
                "precision": 2,
                "state_class" : SensorStateClass.TOTAL
            },
        }
        self.measurement_type = measurement_type
        config = self._config[measurement_type]
        self._attr_name = f"🔌 MAC address: ({self._mac}) {config['name']}"
        self._attr_unique_id = f"{DOMAIN}_{self._mac}_{measurement_type}"
        self._attr_device_class = config["device_class"]
        self._attr_native_unit_of_measurement = config["unit"]
        self._attr_device_info = self.device_info
        self._attr_suggested_display_precision = config["precision"]
        if 'state_class' in config.keys():
            self._attr_state_class = config['state_class']

    @property
    def device_info(self) -> DeviceInfo:
        return {
            'identifiers': {(DOMAIN, self._mac)},
            'manufacturer': "Powersensor",
            'model': self._model,
            'name': f'🔌 MAC address: ({self._mac})',
            # "via_device": # if we use this, can it be updated dynamically?
        }

    @property
    def native_value(self) -> StateType | date | datetime | Decimal:
        return self.coordinator.plug_data.get(self._mac).get(self.measurement_type)

    @property
    def available(self) -> bool:
        """Does data exist for this sensor type"""
        return self.coordinator.plug_data.get(self._mac).get(self.measurement_type, None) is not None

    async def async_added_to_hass(self) -> None:
        """Listen for updates from coordinator"""
        self.async_on_remove(self.coordinator.async_add_listener(self.async_write_ha_state))
