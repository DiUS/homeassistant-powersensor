"""Sensor platform for the integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect, async_dispatcher_send
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import PowersensorMessageDispatcher
from .PlugMeasurements import PlugMeasurements
from .PowersensorHouseholdEntity import HouseholdMeasurements, PowersensorHouseholdEntity, ConsumptionMeasurements, \
    ProductionMeasurements
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
    vhh = entry.runtime_data["vhh"]
    dispatcher: PowersensorMessageDispatcher = entry.runtime_data['dispatcher']


    async def create_plug(plug_mac_address: str):
        this_plug_sensors = [PowersensorPlugEntity(hass, plug_mac_address, PlugMeasurements.WATTS),
                             PowersensorPlugEntity(hass, plug_mac_address, PlugMeasurements.VOLTAGE),
                             PowersensorPlugEntity(hass, plug_mac_address, PlugMeasurements.APPARENT_CURRENT),
                             PowersensorPlugEntity(hass, plug_mac_address, PlugMeasurements.ACTIVE_CURRENT),
                             PowersensorPlugEntity(hass, plug_mac_address, PlugMeasurements.REACTIVE_CURRENT),
                             PowersensorPlugEntity(hass, plug_mac_address, PlugMeasurements.SUMMATION_ENERGY)]

        async_add_entities(this_plug_sensors, True)

    for plug_mac in dispatcher.plugs.keys():
        await create_plug(plug_mac)

    async def handle_discovered_plug(plug_mac_address: str, host: str, port: int, name: str):
        await create_plug(plug_mac_address)
        async_dispatcher_send(hass, f"{DOMAIN}_plug_added_to_homeassistant",
                              plug_mac_address, host, port, name)

    entry.async_on_unload(
        async_dispatcher_connect(
            hass, f"{DOMAIN}_create_plug", handle_discovered_plug
        )
    )
    await dispatcher.process_plug_queue()

    async def handle_discovered_sensor(sensor_mac: str, sensor_role: str):
        if sensor_role == 'solar':
            new_data = { **entry.data }
            new_data['with_solar'] = True  # Remember for next time we start
            hass.config_entries.async_update_entry(entry, data=new_data)

        new_sensors = [
            PowersensorSensorEntity(hass, sensor_mac, SensorMeasurements.Battery),
            PowersensorSensorEntity(hass, sensor_mac, SensorMeasurements.WATTS),
            PowersensorSensorEntity(hass, sensor_mac, SensorMeasurements.SUMMATION_ENERGY),
        ]
        async_add_entities(new_sensors, True)
        async_dispatcher_send(hass, f"{DOMAIN}_sensor_added_to_homeassistant", sensor_mac, sensor_role)

    entry.async_on_unload(
        async_dispatcher_connect(
            hass, f"{DOMAIN}_create_sensor", handle_discovered_sensor
        )
    )


    # Possibly unnecessary but will add sensors where the messages came in early.
    # Hopefully keeps wait time less than 30s
    for mac, role in dispatcher.on_start_sensor_queue.items():
        await handle_discovered_sensor(mac, role)

    async def add_solar_to_virtual_household():
        _LOGGER.debug("Received request to add solar to virtual household")
        solar_household_entities = []
        for solar_measurement_type in ProductionMeasurements:
            solar_household_entities.append(PowersensorHouseholdEntity(vhh, solar_measurement_type))

        async_add_entities(solar_household_entities)
        async_dispatcher_send(hass, f"{DOMAIN}_solar_added_to_virtual_household", True)

    entry.async_on_unload(
        async_dispatcher_connect(
            hass, f"{DOMAIN}_solar_sensor_detected", add_solar_to_virtual_household
        )
    )
    # Register the virtual household entities
    household_entities = []
    for measurement_type in ConsumptionMeasurements:
        household_entities.append(PowersensorHouseholdEntity(vhh, measurement_type))
    async_add_entities(household_entities)

    async_dispatcher_send(hass, f"{DOMAIN}_setup_complete", True)

