"""Class for creation of Homeassistant Entities related to all Powersensor Plug measurements."""

import logging

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import (
    EntityCategory,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo

from ..const import DOMAIN
from .plug_measurements import PlugMeasurements
from .powersensor_entity import PowersensorEntity, PowersensorSensorEntityDescription

_LOGGER = logging.getLogger(__name__)


_config: dict[PlugMeasurements, PowersensorSensorEntityDescription] = {
    PlugMeasurements.WATTS: PowersensorSensorEntityDescription(
        key="Power",
        translation_key="power",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        suggested_display_precision=1,
        event="average_power",
        message_key="watts",
    ),
    PlugMeasurements.VOLTAGE: PowersensorSensorEntityDescription(
        key="Volts",
        translation_key="volts",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        suggested_display_precision=2,
        event="average_power_components",
        message_key="volts",
        entity_registry_visible_default=False,
    ),
    PlugMeasurements.APPARENT_CURRENT: PowersensorSensorEntityDescription(
        key="Apparent Current",
        translation_key="apparent_current",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        suggested_display_precision=2,
        event="average_power_components",
        message_key="apparent_current",
        entity_registry_visible_default=False,
    ),
    PlugMeasurements.ACTIVE_CURRENT: PowersensorSensorEntityDescription(
        key="Active Current",
        translation_key="active_current",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        suggested_display_precision=2,
        event="average_power_components",
        message_key="active_current",
        entity_registry_visible_default=False,
    ),
    PlugMeasurements.REACTIVE_CURRENT: PowersensorSensorEntityDescription(
        key="Reactive Current",
        translation_key="reactive_current",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        suggested_display_precision=2,
        event="average_power_components",
        message_key="reactive_current",
        entity_registry_visible_default=False,
    ),
    PlugMeasurements.SUMMATION_ENERGY: PowersensorSensorEntityDescription(
        key="Total Energy",
        translation_key="total_energy",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=2,
        event="summation_energy",
        message_key="summation_joules",
        conversion_function=lambda v: v / 3600000.0,
    ),
    PlugMeasurements.ROLE: PowersensorSensorEntityDescription(
        key="Device Role",
        translation_key="device_role",
        entity_category=EntityCategory.DIAGNOSTIC,
        event="role",
        message_key="role",
    ),
}


class PowersensorPlugEntity(PowersensorEntity):
    """Powersensor Plug Class--designed to handle all measurements of the plug--perhaps less expressive."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        hass: HomeAssistant,
        entry_id: str,
        mac_address: str,
        role: str,
        measurement_type: PlugMeasurements,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(hass, entry_id, mac_address, role, _config, measurement_type)
        self.measurement_type = measurement_type
        config = _config[measurement_type]

    @property
    def device_info(self) -> DeviceInfo:
        """DeviceInfo for PowersensorPlug. Includes mac address, name and model."""
        return {
            "identifiers": {(DOMAIN, self._mac)},
            "manufacturer": "Powersensor",
            "model": "PowersensorPlug",
            "translation_key": "plug",
            "translation_placeholders": {
                "id": self._mac,
            },
        }
