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
from .const import (CREATE_PLUG_SIGNAL,
    CREATE_SENSOR_SIGNAL,
    DATA_UPDATE_SIGNAL_FMT_MAC_EVENT,
    HAVE_SOLAR_SENSOR_SIGNAL,
    PLUG_ADDED_TO_HA_SIGNAL,
    ROLE_UPDATE_SIGNAL,
    SENSOR_ADDED_TO_HA_SIGNAL,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Powersensor sensors."""
    vhh = entry.runtime_data["vhh"]
    dispatcher: PowersensorMessageDispatcher = entry.runtime_data['dispatcher']


    plug_role = "appliance"

    async def create_plug(plug_mac_address: str, role: str):
        this_plug_sensors = [
            PowersensorPlugEntity(hass, plug_mac_address, role, PlugMeasurements.WATTS),
            PowersensorPlugEntity(hass, plug_mac_address, role, PlugMeasurements.VOLTAGE),
            PowersensorPlugEntity(hass, plug_mac_address, role, PlugMeasurements.APPARENT_CURRENT),
            PowersensorPlugEntity(hass, plug_mac_address, role, PlugMeasurements.ACTIVE_CURRENT),
            PowersensorPlugEntity(hass, plug_mac_address, role, PlugMeasurements.REACTIVE_CURRENT),
            PowersensorPlugEntity(hass, plug_mac_address, role, PlugMeasurements.SUMMATION_ENERGY),
            PowersensorPlugEntity(hass, plug_mac_address, role, PlugMeasurements.ROLE),
        ]

        async_add_entities(this_plug_sensors, True)

    for plug_mac in dispatcher.plugs.keys():
        await create_plug(plug_mac, plug_role)


    # Role update support
    async def handle_role_update(mac_address: str, new_role: str):
        persist_entry = False
        new_data = copy.deepcopy({ **entry.data })

        # We only persist actual roles. If a device forgets its role, we want
        # to keep what we've previously learned.
        if new_role is not None:
            if 'roles' not in new_data.keys():
                new_data['roles'] = {}
            roles = new_data['roles']
            old_role = roles.get(mac_address, None)
            if old_role is None or old_role != new_role:
                _LOGGER.debug(f"Updating role for {mac_address} from {old_role} to {new_role}")
                roles[mac_address] = new_role
                persist_entry = True

        if new_role == 'solar':
            new_data['with_solar'] = True  # Remember for next time we start
            persist_entry = True
            async_dispatcher_send(hass, HAVE_SOLAR_SENSOR_SIGNAL)

        # TODO: for house-net/solar <-> we'd need to change the entities too

        if persist_entry:
            hass.config_entries.async_update_entry(entry, data=new_data)

    entry.async_on_unload(
        async_dispatcher_connect(hass, ROLE_UPDATE_SIGNAL, handle_role_update)
    )


    # Automatic plug discovery
    async def handle_discovered_plug(plug_mac_address: str, host: str, port: int, name: str):
        await create_plug(plug_mac_address, plug_role)
        async_dispatcher_send(hass, PLUG_ADDED_TO_HA_SIGNAL,
                              plug_mac_address, host, port, name)

    entry.async_on_unload(
        async_dispatcher_connect(
            hass, CREATE_PLUG_SIGNAL, handle_discovered_plug
        )
    )
    await dispatcher.process_plug_queue()


    # Automatic sensor discovery
    async def handle_discovered_sensor(sensor_mac: str, sensor_role: str):
        new_sensors = [
            PowersensorSensorEntity(hass, sensor_mac, sensor_role, SensorMeasurements.Battery),
            PowersensorSensorEntity(hass, sensor_mac, sensor_role, SensorMeasurements.WATTS),
            PowersensorSensorEntity(hass, sensor_mac, sensor_role, SensorMeasurements.SUMMATION_ENERGY),
            PowersensorSensorEntity(hass, sensor_mac, sensor_role, SensorMeasurements.ROLE),
            PowersensorSensorEntity(hass, sensor_mac, sensor_role, SensorMeasurements.RSSI),
        ]
        async_add_entities(new_sensors, True)
        async_dispatcher_send(hass, SENSOR_ADDED_TO_HA_SIGNAL, sensor_mac, sensor_role)

        if sensor_role == "solar":
            async_dispatcher_send(hass, HAVE_SOLAR_SENSOR_SIGNAL)

    entry.async_on_unload(
        async_dispatcher_connect(
            hass, CREATE_SENSOR_SIGNAL, handle_discovered_sensor
        )
    )


    # Possibly unnecessary but will add sensors where the messages came in early.
    # Hopefully keeps wait time less than 30s
    for mac, role in dispatcher.on_start_sensor_queue.items():
        await handle_discovered_sensor(mac, role)

    # Register the virtual household entities
    household_entities = []
    for measurement_type in ConsumptionMeasurements:
        household_entities.append(PowersensorHouseholdEntity(vhh, measurement_type))
    async_add_entities(household_entities)

    async def add_solar_to_virtual_household():
        _LOGGER.debug("Enabling solar components in virtual household")
        solar_household_entities = []
        for solar_measurement_type in ProductionMeasurements:
            solar_household_entities.append(PowersensorHouseholdEntity(vhh, solar_measurement_type))

        async_add_entities(solar_household_entities)

    with_solar = entry.data.get('with_solar', False)
    if with_solar:
        await add_solar_to_virtual_household()
    else:
        entry.async_on_unload(
            async_dispatcher_connect(
                hass, HAVE_SOLAR_SENSOR_SIGNAL, add_solar_to_virtual_household
            )
        )
