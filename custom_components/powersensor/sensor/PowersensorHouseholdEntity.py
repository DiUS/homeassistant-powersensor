from datetime import date, datetime
from dataclasses import dataclass
from enum import Enum
from typing import Callable

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.const import UnitOfPower, UnitOfEnergy
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.typing import StateType

from powersensor_local import VirtualHousehold # type: ignore[import-untyped]

from ..const import DOMAIN

class HouseholdMeasurements(Enum):
    POWER_HOME_USE = 1
    POWER_FROM_GRID = 2
    POWER_TO_GRID = 3
    POWER_SOLAR_GENERATION = 4
    ENERGY_HOME_USE = 5
    ENERGY_FROM_GRID = 6
    ENERGY_TO_GRID = 7
    ENERGY_SOLAR_GENERATION = 8

ConsumptionMeasurements = [
    HouseholdMeasurements.POWER_HOME_USE,
    HouseholdMeasurements.POWER_FROM_GRID,
    HouseholdMeasurements.ENERGY_HOME_USE,
    HouseholdMeasurements.ENERGY_FROM_GRID
]
ProductionMeasurements = [
    HouseholdMeasurements.POWER_TO_GRID,
    HouseholdMeasurements.POWER_SOLAR_GENERATION,
    HouseholdMeasurements.ENERGY_TO_GRID,
    HouseholdMeasurements.ENERGY_SOLAR_GENERATION
]

@dataclass
class EntityConfig:
    name : str
    device_class : SensorDeviceClass
    state_class : SensorStateClass | None
    unit : UnitOfPower | UnitOfEnergy
    formatter: Callable
    precision: int
    event: str

FMT_INT = lambda f: int(f)
FMT_WS_TO_KWH = lambda f: float(f)/3600000

class PowersensorHouseholdEntity(SensorEntity):
    """Powersensor Virtual Household entity"""

    should_poll = False
    _attr_has_entity_name = True
    _attr_available = True

    _ENTITY_CONFIGS  = {
        HouseholdMeasurements.POWER_HOME_USE : EntityConfig(
            "Power - Home use", SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, UnitOfPower.WATT, FMT_INT, 0, "home_usage"),
        HouseholdMeasurements.POWER_FROM_GRID : EntityConfig(
            "Power - From grid", SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, UnitOfPower.WATT, FMT_INT, 0, "from_grid"),
        HouseholdMeasurements.POWER_TO_GRID : EntityConfig(
            "Power - To grid", SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, UnitOfPower.WATT, FMT_INT, 0, "to_grid"),
        HouseholdMeasurements.POWER_SOLAR_GENERATION : EntityConfig(
            "Power - Solar generation", SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, UnitOfPower.WATT, FMT_INT, 0, "solar_generation"),

        HouseholdMeasurements.ENERGY_HOME_USE : EntityConfig(
            "Energy - Home usage", SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING, UnitOfEnergy.KILO_WATT_HOUR, FMT_WS_TO_KWH, 3, "home_usage_summation"),
        HouseholdMeasurements.ENERGY_FROM_GRID : EntityConfig(
            "Energy - From grid", SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING, UnitOfEnergy.KILO_WATT_HOUR, FMT_WS_TO_KWH, 3, "from_grid_summation"),
        HouseholdMeasurements.ENERGY_TO_GRID : EntityConfig(
            "Energy - To grid", SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING, UnitOfEnergy.KILO_WATT_HOUR, FMT_WS_TO_KWH, 3, "to_grid_summation"),
        HouseholdMeasurements.ENERGY_SOLAR_GENERATION : EntityConfig(
            "Energy - Solar generation", SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING, UnitOfEnergy.KILO_WATT_HOUR, FMT_WS_TO_KWH, 3, "solar_generation_summation"),
    }

    def __init__(self, vhh: VirtualHousehold, measurement_type: HouseholdMeasurements):
        """Initialize the entity."""
        self._vhh = vhh
        self._config = self._ENTITY_CONFIGS[measurement_type]

        self._attr_name = self._config.name
        self._attr_unique_id = f"{DOMAIN}_vhh_{self._config.event}"
        self._attr_device_class = self._config.device_class
        self._attr_state_class = self._config.state_class
        self._attr_native_unit_of_measurement = self._config.unit
        self._attr_suggested_display_precision = self._config.precision

    @property
    def device_info(self) -> DeviceInfo:
        return {
            'identifiers': {(DOMAIN, "vhh")},
            'manufacturer': "Powersensor",
            'model': "Virtual",
            'name': "Powersensor Household View 🏠",
        }

    async def async_added_to_hass(self):
        self._vhh.subscribe(self._config.event, self._on_event)

    async def async_will_remove_from_hass(self):
        self._vhh.unsubscribe(self._config.event, self._on_event)

    async def _on_event(self, _, msg):
        val = None
        if self._config.unit == UnitOfPower.WATT:
            key = "watts"
            if key in msg:
                val = msg[key]
        elif self._config.unit == UnitOfEnergy.KILO_WATT_HOUR:
            key = "summation_joules"
            if key in msg:
                val = msg[key]
        if val is not None:
            self._attr_native_value = self._config.formatter(val)
            self.async_write_ha_state()
