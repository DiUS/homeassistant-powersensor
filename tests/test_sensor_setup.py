import logging

import pytest
from homeassistant.helpers.dispatcher import async_dispatcher_send, async_dispatcher_connect
from powersensor_local import VirtualHousehold
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.powersensor import RT_DISPATCHER

MAC="a4cf1218f158"
OTHER_MAC = "a4cf1218f159"
from unittest.mock import AsyncMock, Mock
from custom_components.powersensor.const import DOMAIN, RT_VHH, ROLE_UPDATE_SIGNAL, UPDATE_VHH_SIGNAL, \
    CREATE_SENSOR_SIGNAL
from custom_components.powersensor.sensor import async_setup_entry

logging.getLogger().setLevel(logging.CRITICAL)

@pytest.fixture
def config_entry():
    entry = MockConfigEntry(domain=DOMAIN)
    runtime_data =dict()
    runtime_data[RT_VHH] = VirtualHousehold(False)
    runtime_data[RT_DISPATCHER] = AsyncMock()
    runtime_data[RT_DISPATCHER].plugs = dict()
    runtime_data[RT_DISPATCHER].on_start_sensor_queue = dict()
    entry.runtime_data = runtime_data
    return entry

@pytest.mark.asyncio
async def test_setup_entry(hass, monkeypatch, config_entry):
    entry = config_entry
    async_update_entry = Mock()
    monkeypatch.setattr(hass.config_entries, 'async_update_entry', async_update_entry)
    entities = list()
    def callback(new_entities, *args, **kwargs):
        entities.extend(new_entities)

    await async_setup_entry(hass, entry, callback)
    mock_handler = Mock()
    async_dispatcher_connect(hass,UPDATE_VHH_SIGNAL, mock_handler)
    await hass.async_block_till_done()

    async_dispatcher_send(hass, ROLE_UPDATE_SIGNAL,MAC, 'house-net')
    for _ in range(4):
        await hass.async_block_till_done()

    mock_handler.assert_called_once_with()


@pytest.mark.asyncio
async def test_discovered_sensor(hass, monkeypatch, config_entry):
    entry = config_entry
    async_update_entry = Mock()
    monkeypatch.setattr(hass.config_entries, 'async_update_entry', async_update_entry)
    entities = list()

    def callback(new_entities, *args, **kwargs):
        entities.extend(new_entities)

    await async_setup_entry(hass, entry, callback)
    async_dispatcher_send(hass, CREATE_SENSOR_SIGNAL, MAC, 'house-net')
    for _ in range(10):
        await hass.async_block_till_done()

    # check that the right number of entities have been added
    assert len(entities) == 5
    # @todo: check that the correct entities are created

    async_dispatcher_send(hass, CREATE_SENSOR_SIGNAL, OTHER_MAC, 'solar')
    await hass.async_block_till_done()
    # check that the right number of additional entities have been added
    assert len(entities) == 10

@pytest.mark.asyncio
async def test_initially_known_plugs_and_sensors(hass, monkeypatch, config_entry):
    entry = config_entry
    entry.runtime_data[RT_DISPATCHER].plugs[MAC] = None
    entry.runtime_data[RT_DISPATCHER].on_start_sensor_queue[OTHER_MAC] = 'house-net'
    async_update_entry = Mock()
    monkeypatch.setattr(hass.config_entries, 'async_update_entry', async_update_entry)
    entities = list()


    def callback(new_entities, *args, **kwargs):
        entities.extend(new_entities)

    await async_setup_entry(hass, entry, callback)

    assert len(entities) == 12
    # @todo: check that correct entities are created

