"""Sensor platform for the integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send, async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .PlugMeasurements import PlugMeasurements
from .SensorMeasurements import  SensorMeasurements
from .PowersensorPlugEntity import PowersensorPlugEntity
from .PowersensorSensorEntity import PowersensorSensorEntity
from .const import DOMAIN
_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Powersensor sensors."""
    plug_sensors = []
    for plug_mac in hass.data[DOMAIN][entry.entry_id]['dispatcher'].plugs.keys():
        plug_sensors.extend([PowersensorPlugEntity(hass, plug_mac, PlugMeasurements.WATTS),
                    PowersensorPlugEntity(hass, plug_mac, PlugMeasurements.VOLTAGE),
                    PowersensorPlugEntity(hass, plug_mac, PlugMeasurements.APPARENT_CURRENT),
                    PowersensorPlugEntity(hass, plug_mac, PlugMeasurements.ACTIVE_CURRENT),
                    PowersensorPlugEntity(hass, plug_mac, PlugMeasurements.REACTIVE_CURRENT),
                    PowersensorPlugEntity(hass, plug_mac, PlugMeasurements.SUMMATION_ENERGY)])

    async_add_entities(plug_sensors, True)

    async def handle_discovered_sensor(sensor_mac):
        new_sensors = [
            PowersensorSensorEntity(hass, sensor_mac, SensorMeasurements.Battery),
            PowersensorSensorEntity(hass, sensor_mac, SensorMeasurements.WATTS),
            PowersensorSensorEntity(hass, sensor_mac, SensorMeasurements.SUMMATION_ENERGY),
        ]
        async_add_entities(new_sensors, True)

    entry.async_on_unload(
        async_dispatcher_connect(
            hass, f"{DOMAIN}_create_sensor", handle_discovered_sensor
        )
    )

