"""Sensor platform for the integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .PlugMeasurements import PlugMeasurements
from .PowersensorHouseholdEntity import HouseholdMeasurements, PowersensorHouseholdEntity
from .PowersensorPlugEntity import PowersensorPlugEntity
from .PowersensorSensorEntity import PowersensorSensorEntity
from .SensorMeasurements import SensorMeasurements
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

    # Register household entities
    # vhh = plug_update_coordinator._vhh # TODO tidy up
    # household_entities = []
    # for measurement_type in HouseholdMeasurements:
    #     # TODO: only include to_grid/solar if have solar?
    #     # Should we dynamically register the household only in response to
    #     # getting role:house-net and role:solar messages, maybe?
    #     household_entities.append(PowersensorHouseholdEntity(vhh, measurement_type))
    # async_add_entities(household_entities)


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

