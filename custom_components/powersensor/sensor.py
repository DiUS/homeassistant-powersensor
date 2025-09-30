"""Sensor platform for the integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

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
    plug_update_coordinator.async_add_sensor_entities  = async_add_entities


