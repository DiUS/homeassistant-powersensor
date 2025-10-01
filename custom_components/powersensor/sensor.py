"""Sensor platform for the integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .PowersensorHouseholdEntity import HouseholdMeasurements, PowersensorHouseholdEntity
from .PowersensorPlugEntity import PowersensorPlugEntity
from .const import DOMAIN
from .coordinator import PlugMeasurements
_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Powersensor sensors."""
    _LOGGER.error("Fairy pants")

    plug_update_coordinator  = hass.data[DOMAIN][entry.entry_id]
    plug_sensors = []
    for plug in plug_update_coordinator.plug_data:
        plug_sensors.extend([PowersensorPlugEntity(hass, plug_update_coordinator, plug, PlugMeasurements.WATTS),
                    PowersensorPlugEntity(hass, plug_update_coordinator, plug, PlugMeasurements.VOLTAGE),
                    PowersensorPlugEntity(hass, plug_update_coordinator, plug, PlugMeasurements.APPARENT_CURRENT),
                    PowersensorPlugEntity(hass, plug_update_coordinator, plug, PlugMeasurements.ACTIVE_CURRENT),
                    PowersensorPlugEntity(hass, plug_update_coordinator, plug, PlugMeasurements.REACTIVE_CURRENT),
                    PowersensorPlugEntity(hass, plug_update_coordinator, plug, PlugMeasurements.SUMMATION_ENERGY)])

    async_add_entities(plug_sensors, True)

    # Register household entities
    vhh = plug_update_coordinator._vhh # TODO tidy up
    household_entities = []
    for measurement_type in HouseholdMeasurements:
        # TODO: only include to_grid/solar if have solar?
        # Should we dynamically register the household only in response to
        # getting role:house-net and role:solar messages, maybe?
        household_entities.append(PowersensorHouseholdEntity(vhh, measurement_type))
    async_add_entities(household_entities)

    plug_update_coordinator.async_add_sensor_entities  = async_add_entities


