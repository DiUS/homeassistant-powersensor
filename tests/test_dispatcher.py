import asyncio
import logging
from ipaddress import ip_address

import pytest


from custom_components.powersensor.const import CREATE_PLUG_SIGNAL, CREATE_SENSOR_SIGNAL, ROLE_UPDATE_SIGNAL, \
    DATA_UPDATE_SIGNAL_FMT_MAC_EVENT

MAC="a4cf1218f158"
from unittest.mock import Mock, call

logging.getLogger().setLevel(logging.CRITICAL)
@pytest.fixture
def monkey_patched_dispatcher(hass, monkeypatch):
    def create_task(coroutine, name = None):
        return asyncio.create_task(coroutine)
    monkeypatch.setattr(hass, 'async_create_background_task', create_task)

    import importlib
    powersensor_dispatcher_module = importlib.import_module("custom_components.powersensor.PowersensorMessageDispatcher")

    async_dispatcher_connect = Mock()
    monkeypatch.setattr(powersensor_dispatcher_module, "async_dispatcher_connect", async_dispatcher_connect)
    async_dispatcher_send = Mock()
    monkeypatch.setattr(powersensor_dispatcher_module, "async_dispatcher_send", async_dispatcher_send)
    vhh = powersensor_dispatcher_module.VirtualHousehold(False)
    entry = Mock()
    dispatcher = powersensor_dispatcher_module.PowersensorMessageDispatcher(hass, entry, vhh,debounce_timeout =2)
    if not hasattr(dispatcher, 'dispatch_send_reference'):
        object.__setattr__(dispatcher, 'dispatch_send_reference', {})
    dispatcher.dispatch_send_reference = async_dispatcher_send

    return dispatcher

@pytest.fixture
def network_info():
    return dict({
        'mac' : MAC,
        'host' : ip_address("192.168.0.33"),
        'port' : 49476,
        'name' : f"Powersensor-gateway-{MAC}-civet._powersensor._udp.local."
    })


@pytest.fixture
def zeroconf_discovery_info():
    return dict({'type': "_powersensor._udp.local.",
                 'name': f"Powersensor-gateway-{MAC}-civet._powersensor._udp.local.",
                 'addresses': [ip_address("192.168.0.33")],
                 'port': 49476,
                 'server': f"Powersensor-gateway-{MAC}-civet.local.",
                 'properties': {
                    "version": "1",
                    b"id": f"{MAC}".encode("UTF-8"),
                  }
             })


async def follow_normal_add_sequence(dispatcher, network_info):
    assert not dispatcher.plugs
    await dispatcher.enqueue_plug_for_adding(network_info)
    await dispatcher.process_plug_queue()
    for _ in range(3):
        await dispatcher._hass.async_block_till_done()

    # check signal was sent to sensors
    dispatcher.dispatch_send_reference.assert_called_once_with(dispatcher._hass, CREATE_PLUG_SIGNAL,
                                                               network_info['mac'],
                                                               network_info['host'],
                                                               network_info['port'],
                                                               network_info['name']
                                                               )

    # if we're at this point the signal should be coming back triggering acknowledge
    await dispatcher._acknowledge_plug_added_to_homeassistant(network_info['mac'], network_info['host'],
                                                              network_info['port'], network_info['name'])
    for _ in range(3):
        await dispatcher._hass.async_block_till_done()

    # an api object should have been created
    assert MAC in dispatcher.plugs
    # Think this is a sign that the finally block is not running as expected.
    # @todo: delete this block here as well after investigation complete
    if dispatcher._monitor_add_plug_queue is not None:
        dispatcher._monitor_add_plug_queue.cancel()
        try:
            await dispatcher._monitor_add_plug_queue
        except asyncio.CancelledError:
            pass
        finally:
            dispatcher._monitor_add_plug_queue = None

@pytest.mark.asyncio
async def test_dispatcher_monitor_plug_queue(monkeypatch, monkey_patched_dispatcher, network_info):
    dispatcher=monkey_patched_dispatcher

    # mac address known, but not in plugs
    dispatcher._known_plugs.add(MAC)

    assert not dispatcher.plugs
    await dispatcher.enqueue_plug_for_adding(network_info)
    await dispatcher.process_plug_queue()
    for _ in range(3):
        await dispatcher._hass.async_block_till_done()

    # an api object should have been created
    assert MAC in dispatcher.plugs
    # Think this is a sign that the finally block is not running as expected.
    # @todo: investigate dispatcher plug queue watching task cleanup
    if dispatcher._monitor_add_plug_queue is not None:
        dispatcher._monitor_add_plug_queue.cancel()
        try:
            await dispatcher._monitor_add_plug_queue
        except asyncio.CancelledError:
            pass
        finally:
            dispatcher._monitor_add_plug_queue = None


    for _ in range(3):
        await dispatcher._hass.async_block_till_done()
    # try to see if queue gets properly cleared
    await dispatcher.enqueue_plug_for_adding(network_info)
    await dispatcher.process_plug_queue()
    for _ in range(3):
        await dispatcher._hass.async_block_till_done()

    assert MAC in dispatcher.plugs

@pytest.mark.asyncio
async def test_dispatcher_monitor_plug_queue_error_handling(monkeypatch, monkey_patched_dispatcher, network_info):
    dispatcher = monkey_patched_dispatcher
    def raise_error(*args, **kwargs):
        raise NotImplementedError
    monkeypatch.setattr(dispatcher, '_plug_has_been_seen', raise_error)
    assert not dispatcher.plugs
    await dispatcher.enqueue_plug_for_adding(network_info)
    await dispatcher.process_plug_queue()
    for _ in range(3):
        await dispatcher._hass.async_block_till_done()
    assert not dispatcher.plugs


@pytest.mark.asyncio
async def test_dispatcher_handle_plug_exception(monkeypatch, monkey_patched_dispatcher, network_info):
    # @todo: use powersensor_local mock_plug and generate an exception that pass through
    # for now I pointlessly verify this does not crash
    dispatcher = monkey_patched_dispatcher
    await dispatcher.handle_exception('exception', NotImplementedError)


@pytest.mark.asyncio
async def test_dispatcher_removal(monkeypatch, monkey_patched_dispatcher, network_info, zeroconf_discovery_info):
    dispatcher=monkey_patched_dispatcher

    # test removal of plug not added
    await dispatcher._schedule_plug_removal(network_info['name'], zeroconf_discovery_info)
    await asyncio.sleep(dispatcher._debounce_seconds + 1)
    for _ in range(3):
        await dispatcher._hass.async_block_till_done()

    assert MAC not in dispatcher.plugs.keys()

    await follow_normal_add_sequence(dispatcher, network_info)


    await dispatcher._schedule_plug_removal(network_info['name'], zeroconf_discovery_info)
    await asyncio.sleep(dispatcher._debounce_seconds+1)
    for _ in range(3):
        await dispatcher._hass.async_block_till_done()
    assert MAC not in dispatcher.plugs.keys()

    await follow_normal_add_sequence(dispatcher, network_info)
    assert MAC in dispatcher.plugs
    await dispatcher._schedule_plug_removal(network_info['name'], zeroconf_discovery_info)

    await asyncio.sleep(dispatcher._debounce_seconds//2)
    await dispatcher.stop_pending_removal_tasks()
    await asyncio.sleep(dispatcher._debounce_seconds // 2 +1)
    for _ in range(3):
        await dispatcher._hass.async_block_till_done()
    # the removal should not have happened if it was interrupted
    assert MAC in dispatcher.plugs.keys()

    # cancel just one mac
    await dispatcher._schedule_plug_removal(network_info['name'], zeroconf_discovery_info)
    await dispatcher._schedule_plug_removal(network_info['name'], zeroconf_discovery_info)
    await asyncio.sleep(dispatcher._debounce_seconds//2)
    await dispatcher.cancel_any_pending_removal(MAC, "test-cancellation")
    await asyncio.sleep(dispatcher._debounce_seconds // 2 +1)
    for _ in range(3):
        await dispatcher._hass.async_block_till_done()
    # the removal should not have happened if it was interrupted
    assert MAC in dispatcher.plugs.keys()


@pytest.mark.asyncio
async def test_dispatcher_handle_relaying_for(monkeypatch, monkey_patched_dispatcher):
    dispatcher=monkey_patched_dispatcher
    await dispatcher.handle_relaying_for("test-event", {'mac': None, 'device_type': 'plug'})
    assert dispatcher.dispatch_send_reference.call_count == 0
    await dispatcher.handle_relaying_for("test-event", {'mac': None, 'device_type': 'sensor'})
    assert dispatcher.dispatch_send_reference.call_count == 0
    await dispatcher.handle_relaying_for("test-event", {'mac': MAC, 'device_type': 'plug'})
    assert dispatcher.dispatch_send_reference.call_count == 0
    await dispatcher.handle_relaying_for("test-event", {'mac': MAC, 'device_type': 'sensor', 'role': 'house-net'})
    assert dispatcher.dispatch_send_reference.call_count == 2
    dispatcher.dispatch_send_reference.call_args_list[0] = call(dispatcher._hass, CREATE_SENSOR_SIGNAL, MAC, 'house-net')
    dispatcher.dispatch_send_reference.call_args_list[1] = call(dispatcher._hass, ROLE_UPDATE_SIGNAL, MAC, 'house-net')

@pytest.mark.asyncio
async def test_dispatcher_handle_message(monkeypatch, monkey_patched_dispatcher):
    dispatcher=monkey_patched_dispatcher
    role = 'house-net'
    event = "average_power"
    message = {'mac': MAC, 'device_type': 'sensor', 'role': role}
    await dispatcher.handle_message(event, message)
    assert dispatcher.dispatch_send_reference.call_count ==3
    dispatcher.dispatch_send_reference.call_args_list[0] = call(dispatcher._hass, ROLE_UPDATE_SIGNAL, MAC, role)
    dispatcher.dispatch_send_reference.call_args_list[1] = call(dispatcher._hass,
                                                                DATA_UPDATE_SIGNAL_FMT_MAC_EVENT % (MAC, event),
                                                                event, message)
    dispatcher.dispatch_send_reference.call_args_list[2] = call(dispatcher._hass,
                                                                DATA_UPDATE_SIGNAL_FMT_MAC_EVENT % (MAC, 'role'),
                                                                'role', {'role': role})
    event = "summation_energy"
    await dispatcher.handle_message(event, message)
    assert dispatcher.dispatch_send_reference.call_count == 6
    dispatcher.dispatch_send_reference.call_args_list[3] = call(dispatcher._hass, ROLE_UPDATE_SIGNAL, MAC, role)
    dispatcher.dispatch_send_reference.call_args_list[4] = call(dispatcher._hass,
                                                                DATA_UPDATE_SIGNAL_FMT_MAC_EVENT % (MAC, event),
                                                                event, message)
    dispatcher.dispatch_send_reference.call_args_list[5] = call(dispatcher._hass,
                                                                DATA_UPDATE_SIGNAL_FMT_MAC_EVENT % (MAC, 'role'),
                                                                'role', {'role': role})

@pytest.mark.asyncio
async def test_dispatcher_acknowledge_added_to_homeassistant(monkeypatch, monkey_patched_dispatcher):
    dispatcher = monkey_patched_dispatcher
    dispatcher._acknowledge_sensor_added_to_homeassistant(MAC, 'test-role')
    assert dispatcher.sensors.get(MAC, None) == 'test-role'

@pytest.mark.asyncio
async def test_dispatcher_plug_added(monkeypatch, monkey_patched_dispatcher, zeroconf_discovery_info):
    dispatcher=monkey_patched_dispatcher
    await dispatcher._plug_added(zeroconf_discovery_info)
    dispatcher._safe_to_process_plug_queue = True
    await dispatcher._plug_added(zeroconf_discovery_info)

@pytest.mark.asyncio
async def test_dispatcher_plug_updated(monkeypatch, monkey_patched_dispatcher,network_info, zeroconf_discovery_info):
    dispatcher=monkey_patched_dispatcher
    await dispatcher._plug_updated(zeroconf_discovery_info)

    for _ in range(3):
        await dispatcher._hass.async_block_till_done()

    dispatcher.dispatch_send_reference.assert_called_once_with(dispatcher._hass, CREATE_PLUG_SIGNAL,
                                              network_info['mac'], network_info['host'],
                                              network_info['port'], network_info['name'])
    assert MAC not in dispatcher.plugs
    await follow_normal_add_sequence(dispatcher, network_info)
    assert MAC in dispatcher.plugs

    await dispatcher._plug_updated(zeroconf_discovery_info)

    for _ in range(3):
        await dispatcher._hass.async_block_till_done()

    assert dispatcher.dispatch_send_reference.call_count == 1
    assert MAC in dispatcher.plugs
    # fake ip mismatch
    dispatcher.plugs[MAC]._listener._ip = ip_address("192.168.0.34")
    await dispatcher._plug_updated(zeroconf_discovery_info)
    assert dispatcher.dispatch_send_reference.call_count == 1
    dispatcher.plugs[MAC]._listener._ip = ip_address("192.168.0.33")
    # fake plug removal
    assert MAC in dispatcher.plugs
    await dispatcher.plugs[MAC].disconnect()
    del dispatcher.plugs[MAC]
    await dispatcher._plug_updated(zeroconf_discovery_info)
