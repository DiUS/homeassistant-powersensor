"""Class for creation of Homeassistant Entities related to all Powersensor Sensor measurements."""

import logging

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import (
    PERCENTAGE,
    SIGNAL_STRENGTH_DECIBELS,
    EntityCategory,
    UnitOfEnergy,
    UnitOfPower,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo

from ..const import DOMAIN, ROLE_HOUSENET, ROLE_SOLAR, ROLE_WATER
from .powersensor_entity import PowersensorEntity, PowersensorSensorEntityDescription
from .sensor_measurements import SensorMeasurements

_LOGGER = logging.getLogger(__name__)


_config: dict[SensorMeasurements, PowersensorSensorEntityDescription] = {
    SensorMeasurements.BATTERY: PowersensorSensorEntityDescription(
        key="Battery Level",
        translation_key="battery_level",
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        suggested_display_precision=0,
        event="battery_level",
        message_key="volts",
        conversion_function=lambda v: max(
            min(100.0 * (v - 3.3) / 0.85, 100), 0
        ),  # 0% = 3.3 V , 100% = 4.15 V
    ),
    SensorMeasurements.WATTS: PowersensorSensorEntityDescription(
        key="Power",
        translation_key="power",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        suggested_display_precision=1,
        event="average_power",
        message_key="watts",
    ),
    SensorMeasurements.SUMMATION_ENERGY: PowersensorSensorEntityDescription(
        key="Total Energy",
        translation_key="total_energy",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=2,
        state_class=SensorStateClass.TOTAL,
        event="summation_energy",
        message_key="summation_joules",
        conversion_function=lambda v: v / 3600000.0,
    ),
    SensorMeasurements.ROLE: PowersensorSensorEntityDescription(
        key="Device Role",
        translation_key="device_role",
        entity_category=EntityCategory.DIAGNOSTIC,
        event="role",
        message_key="role",
    ),
    SensorMeasurements.RSSI: PowersensorSensorEntityDescription(
        key="Signal strength (Bluetooth)",
        translation_key="rssi_ble",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS,
        suggested_display_precision=1,
        entity_category=EntityCategory.DIAGNOSTIC,
        event="radio_signal_quality",
        message_key="average_rssi",
    ),
}


class PowersensorSensorEntity(PowersensorEntity):
    """Powersensor Sensor Class--designed to handle all measurements of the sensor."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry_id: str,
        mac: str,
        role: str,
        measurement_type: SensorMeasurements,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(hass, entry_id, mac, role, _config, measurement_type)
        self.measurement_type = measurement_type
        config: PowersensorSensorEntityDescription = _config[measurement_type]
        self._measurement_name = config.key
        self._current_translation_key: str = self._get_translation_key()

    @property
    def device_info(self) -> DeviceInfo:
        """DeviceInfo for PowersensorSensor. Includes mac, name and model."""
        return {
            "identifiers": {(DOMAIN, self._mac)},
            "manufacturer": "Powersensor",
            "model": "PowersensorSensor",
            "translation_key": self._current_translation_key,
            "translation_placeholders": {
                "id": self._mac
            },
        }

    def _get_translation_key(self) -> str:
        role2key = {
            ROLE_HOUSENET: "mains_sensor",
            ROLE_SOLAR: "solar_sensor",
            ROLE_WATER: "water_sensor",
        }
        return (
            role2key[self._role]
            if self._role in [ROLE_HOUSENET, ROLE_WATER, ROLE_SOLAR]
            else "unknown_sensor"
        )

    def _rename_based_on_role(self) -> bool:
        expected_key: str = self._get_translation_key()
        if self._current_translation_key != expected_key:
            self._current_translation_key = expected_key
            return True
        return False
