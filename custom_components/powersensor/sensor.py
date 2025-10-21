"""Sensor platform for the integration."""
from __future__ import annotations

import copy
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
from .const import POWER_SENSOR_UPDATE_SIGNAL, DOMAIN
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
        this_plug_sensors = [
            PowersensorPlugEntity(hass, plug_mac_address, PlugMeasurements.WATTS),
            PowersensorPlugEntity(hass, plug_mac_address, PlugMeasurements.VOLTAGE),
            PowersensorPlugEntity(hass, plug_mac_address, PlugMeasurements.APPARENT_CURRENT),
            PowersensorPlugEntity(hass, plug_mac_address, PlugMeasurements.ACTIVE_CURRENT),
            PowersensorPlugEntity(hass, plug_mac_address, PlugMeasurements.REACTIVE_CURRENT),
            PowersensorPlugEntity(hass, plug_mac_address, PlugMeasurements.SUMMATION_ENERGY),
            PowersensorPlugEntity(hass, plug_mac_address, PlugMeasurements.ROLE),
        ]

        async_add_entities(this_plug_sensors, True)

    for plug_mac in dispatcher.plugs.keys():
        await create_plug(plug_mac)


    # Role update support
    async def handle_role_update(mac_address: str, new_role: str):
        persist_entry = False
        new_data = copy.deepcopy({ **entry.data })

        if new_role is not None:
            devices = new_data['devices']
            if mac_address in devices.keys():
                info = devices[mac_address]
                have_role = True if 'role' in info.keys() else False
                old_role = info['role'] if have_role else None
                if (not have_role) or (have_role and info['role'] != new_role):
                    _LOGGER.debug(f"Updating role for {mac_address} from {old_role} to {new_role}")
                    info['role'] = new_role
                    persist_entry = True

        if new_role == 'solar':
            new_data['with_solar'] = True  # Remember for next time we start
            persist_entry = True

        if persist_entry:
            hass.config_entries.async_update_entry(entry, data=new_data)

    # These events are sent by the entities when their cached role updates
    entry.async_on_unload(
        async_dispatcher_connect(
            hass, f"{DOMAIN}_update_role", handle_role_update
        )
    )


    # Automatic plug discovery
    async def handle_discovered_plug(plug_mac_address: str, host: str, port: int, name: str):
        await create_plug(plug_mac_address)
        async_dispatcher_send(hass, f"{DOMAIN}_plug_added_to_homeassistant",
                              plug_mac_address, host, port, name)
        async_dispatcher_send(hass, f"{DOMAIN}_update_role",
                              plug_mac_address, "appliance") # default role

    entry.async_on_unload(
        async_dispatcher_connect(
            hass, f"{DOMAIN}_create_plug", handle_discovered_plug
        )
    )
    await dispatcher.process_plug_queue()


    # Automatic sensor discovery
    async def handle_discovered_sensor(sensor_mac: str, sensor_role: str):
        new_sensors = [
            PowersensorSensorEntity(hass, sensor_mac, SensorMeasurements.Battery),
            PowersensorSensorEntity(hass, sensor_mac, SensorMeasurements.WATTS),
            PowersensorSensorEntity(hass, sensor_mac, SensorMeasurements.SUMMATION_ENERGY),
            PowersensorSensorEntity(hass, sensor_mac, SensorMeasurements.ROLE),
        ]
        async_add_entities(new_sensors, True)
        async_dispatcher_send(hass, f"{DOMAIN}_sensor_added_to_homeassistant", sensor_mac, sensor_role)
        # Trigger initial entity role update
        async_dispatcher_send(hass, f"{POWER_SENSOR_UPDATE_SIGNAL}_{sensor_mac}_role", 'role', { 'role': sensor_role })

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

