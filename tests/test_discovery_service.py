import asyncio
import logging
from ipaddress import ip_address

import pytest
from asyncmock import AsyncMock
from zeroconf import ServiceInfo

from custom_components.powersensor import PowersensorDiscoveryService
from custom_components.powersensor.PowersensorDiscoveryService import PowersensorServiceListener
from custom_components.powersensor.const import (
    ZEROCONF_ADD_PLUG_SIGNAL, ZEROCONF_REMOVE_PLUG_SIGNAL, ZEROCONF_UPDATE_PLUG_SIGNAL,
)

MAC="a4cf1218f158"
from unittest.mock import Mock, call

logging.getLogger().setLevel(logging.CRITICAL)

@pytest.fixture
def mock_service_info():
    """Create a mock service info"""
    return ServiceInfo(
      addresses=[ip_address("192.168.0.33").packed],
      server=f"Powersensor-gateway-{MAC}-civet.local.",
      name=f"Powersensor-gateway-{MAC}-civet._powersensor._udp.local.",
      port=49476,
      type_="_powersensor._udp.local.",
      properties={
        "version": "1",
        "id": f"{MAC}",
      },
    )

@pytest.mark.asyncio
async def test_discovery_add(hass, monkeypatch, mock_service_info):
    mock_send = Mock()
    monkeypatch.setattr(PowersensorServiceListener, 'dispatch',mock_send )
    service = PowersensorServiceListener(hass)
    mock_zc = Mock()
    zc_info = mock_service_info
    mock_zc.get_service_info.return_value = zc_info

    service.add_service(mock_zc, zc_info.type, zc_info.name)
    mock_zc.get_service_info.assert_called_once_with(zc_info.type, zc_info.name)

    await hass.async_block_till_done()
    await hass.async_block_till_done()

    mock_send.assert_called_once_with( ZEROCONF_ADD_PLUG_SIGNAL, service._plugs[zc_info.name])


@pytest.mark.asyncio
async def test_discovery_add_and_remove(hass, monkeypatch, mock_service_info):
    mock_send = Mock()
    monkeypatch.setattr(PowersensorServiceListener, 'dispatch',mock_send )
    # set debounce timeout very short for testing
    service = PowersensorServiceListener(hass, debounce_timeout=3)
    mock_zc = Mock()
    zc_info = mock_service_info
    mock_zc.get_service_info.return_value = zc_info

    service.add_service(mock_zc, zc_info.type, zc_info.name)
    mock_zc.get_service_info.assert_called_once_with(zc_info.type, zc_info.name)

    await hass.async_block_till_done()
    await hass.async_block_till_done()

    mock_send.assert_called_once_with(ZEROCONF_ADD_PLUG_SIGNAL, service._plugs[zc_info.name])


    # reset mock_send
    mock_send = Mock()
    monkeypatch.setattr(PowersensorServiceListener, 'dispatch', mock_send)
    # cache plug data for checking
    data = service._plugs[zc_info.name].copy()

    service.remove_service(mock_zc, zc_info.type, zc_info.name)

    # mock_zc.get_service_info.assert_called_once_with(zc_info.type, zc_info.name)
    mock_zc.get_service_info.assert_called_once_with(zc_info.type, zc_info.name)
    mock_send.assert_not_called()
    await asyncio.sleep(service._debounce_seconds +1)

    for _ in range(3):
        await hass.async_block_till_done()
    mock_send.assert_called_once_with(ZEROCONF_REMOVE_PLUG_SIGNAL, zc_info.name, data)

@pytest.mark.asyncio
async def test_discovery_remove_without_add(hass, monkeypatch, mock_service_info):
    mock_send = Mock()
    monkeypatch.setattr(PowersensorServiceListener, 'dispatch',mock_send )
    # set debounce timeout very short for testing
    service = PowersensorServiceListener(hass, debounce_timeout=3)
    mock_zc = Mock()
    zc_info = mock_service_info
    mock_zc.get_service_info.return_value = zc_info

    service.remove_service(mock_zc, zc_info.type, zc_info.name)
    # mock_zc.get_service_info.assert_called_once_with(zc_info.type, zc_info.name)
    mock_zc.get_service_info.assert_not_called()
    mock_send.assert_not_called()
    await asyncio.sleep(service._debounce_seconds +1)

    for _ in range(3):
        await hass.async_block_till_done()
    mock_send.assert_called_once_with(ZEROCONF_REMOVE_PLUG_SIGNAL, zc_info.name, None)


@pytest.mark.asyncio
async def test_discovery_remove_cancel(hass, monkeypatch, mock_service_info):
    mock_send = Mock()
    monkeypatch.setattr(PowersensorServiceListener, 'dispatch',mock_send )
    # set debounce timeout very short for testing
    service = PowersensorServiceListener(hass, debounce_timeout=3)
    mock_zc = Mock()
    zc_info = mock_service_info
    mock_zc.get_service_info.return_value = zc_info

    service.add_service(mock_zc, zc_info.type, zc_info.name)
    mock_zc.get_service_info.assert_called_once_with(zc_info.type, zc_info.name)

    await hass.async_block_till_done()
    await hass.async_block_till_done()

    mock_send.assert_called_once_with(ZEROCONF_ADD_PLUG_SIGNAL, service._plugs[zc_info.name])


    # reset mock_send
    mock_send = Mock()
    monkeypatch.setattr(PowersensorServiceListener, 'dispatch', mock_send)
    # cache plug data for checking

    service.remove_service(mock_zc, zc_info.type, zc_info.name)

    # mock_zc.get_service_info.assert_called_once_with(zc_info.type, zc_info.name)
    mock_zc.get_service_info.assert_called_once_with(zc_info.type, zc_info.name)
    mock_send.assert_not_called()

    service.add_service(mock_zc, zc_info.type, zc_info.name)
    assert mock_zc.get_service_info.call_count == 2
    mock_zc.get_service_info.assert_has_calls([
        call(zc_info.type, zc_info.name),
        call(zc_info.type, zc_info.name)
    ])

@pytest.mark.asyncio
async def test_discovery_add_and_two_remove_calls(hass, monkeypatch, mock_service_info):
    mock_send = Mock()
    monkeypatch.setattr(PowersensorServiceListener, 'dispatch',mock_send )
    # set debounce timeout very short for testing
    service = PowersensorServiceListener(hass, debounce_timeout=2)
    mock_zc = Mock()
    zc_info = mock_service_info
    mock_zc.get_service_info.return_value = zc_info

    service.add_service(mock_zc, zc_info.type, zc_info.name)
    mock_zc.get_service_info.assert_called_once_with(zc_info.type, zc_info.name)

    await hass.async_block_till_done()
    await hass.async_block_till_done()

    mock_send.assert_called_once_with(ZEROCONF_ADD_PLUG_SIGNAL, service._plugs[zc_info.name])


    # reset mock_send
    mock_send = Mock()
    monkeypatch.setattr(PowersensorServiceListener, 'dispatch', mock_send)
    # cache plug data for checking
    data = service._plugs[zc_info.name].copy()

    service.remove_service(mock_zc, zc_info.type, zc_info.name)

    # mock_zc.get_service_info.assert_called_once_with(zc_info.type, zc_info.name)
    mock_zc.get_service_info.assert_called_once_with(zc_info.type, zc_info.name)
    mock_send.assert_not_called()
    await asyncio.sleep(service._debounce_seconds//2 +1)
    service.remove_service(mock_zc, zc_info.type, zc_info.name)
    await asyncio.sleep(service._debounce_seconds // 2 + 1)
    for _ in range(3):
        await hass.async_block_till_done()
    mock_send.assert_called_once_with(ZEROCONF_REMOVE_PLUG_SIGNAL, zc_info.name, data)


@pytest.mark.asyncio
async def test_discovery_update(hass, monkeypatch, mock_service_info):
    mock_send = Mock()
    monkeypatch.setattr(PowersensorServiceListener, 'dispatch',mock_send )
    # set debounce timeout very short for testing
    service = PowersensorServiceListener(hass, debounce_timeout=2)
    mock_zc = Mock()
    zc_info = mock_service_info
    mock_zc.get_service_info.return_value = zc_info

    service.add_service(mock_zc, zc_info.type, zc_info.name)
    mock_zc.get_service_info.assert_called_once_with(zc_info.type, zc_info.name)

    await hass.async_block_till_done()
    await hass.async_block_till_done()

    mock_send.assert_called_once_with(ZEROCONF_ADD_PLUG_SIGNAL, service._plugs[zc_info.name])


    # reset mock_send
    mock_send = Mock()
    monkeypatch.setattr(PowersensorServiceListener, 'dispatch', mock_send)
    # cache plug data for checking
    data = service._plugs[zc_info.name].copy()

    updated_service_info =  ServiceInfo(
      addresses=[ip_address("192.168.0.34").packed],
      server=f"Powersensor-gateway-{MAC}-civet.local.",
      name=f"Powersensor-gateway-{MAC}-civet._powersensor._udp.local.",
      port=49476,
      type_="_powersensor._udp.local.",
      properties={
        "version": "1",
        "id": f"{MAC}",
      },
    )
    mock_zc.get_service_info.return_value = updated_service_info
    service.update_service(mock_zc, updated_service_info.type, updated_service_info.name)
    for _ in range(3):
        await hass.async_block_till_done()
    mock_send.assert_called_once_with(ZEROCONF_UPDATE_PLUG_SIGNAL, service._plugs[zc_info.name])

    assert  len(service._plugs[zc_info.name]['addresses']) == 1
    assert service._plugs[zc_info.name]['addresses'][0]=='192.168.0.34'


@pytest.mark.asyncio
async def test_discovery_dispatcher(hass, monkeypatch):
    import importlib
    mod = importlib.import_module("custom_components.powersensor.PowersensorDiscoveryService")
    mock_send = Mock()
    monkeypatch.setattr(mod, 'async_dispatcher_send', mock_send)
    service = mod.PowersensorServiceListener(hass, debounce_timeout=4)
    service.dispatch('mock_signal', 1, 2, 3, 4)
    mock_send.assert_called_once_with(hass, 'mock_signal',1,2,3,4)


@pytest.mark.asyncio
async def test_discovery_get_service_info(hass, monkeypatch, mock_service_info):
    # this whole method is really more of a debugging tool
    # @todo: decide if it should just get deleted

    # set debounce timeout very short for testing
    service = PowersensorServiceListener(hass, debounce_timeout=5)
    mock_zc = AsyncMock()
    zc_info = mock_service_info
    def custom_call_rules(type_, name, *args, **kwargs):
        if type_ == zc_info.type and name == zc_info.name == name:
            return zc_info
        raise NotImplementedError

    mock_zc.async_get_service_info.side_effect = custom_call_rules

    await service._async_get_service_info(mock_zc, zc_info.type, zc_info.name)

    assert zc_info.name in service._discoveries.keys()
    assert service._discoveries[zc_info.name] == zc_info

    await service._async_get_service_info(mock_zc, zc_info.type, 'garbage_name')
    assert 'garbage_name' not in service._discoveries.keys()


@pytest.mark.asyncio
async def test_discovery_service_early_exit(hass, monkeypatch):
   service =  PowersensorDiscoveryService(hass)
   service.running = True
   await service.start()

   assert service.zc is None
   assert service.listener is None
   assert service.browser is None

@pytest.mark.asyncio
async def test_discovery_service_stop_with_canceled_task(hass, monkeypatch):
   service =  PowersensorDiscoveryService(hass)
   service.running = True
   service.zc = Mock()
   service._task = asyncio.create_task(asyncio.sleep(25))
   await service.stop()
   assert service.zc is None
   assert not service.running





