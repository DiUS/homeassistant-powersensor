import asyncio

import pytest
import custom_components.powersensor
from asyncmock import AsyncMock

from custom_components.powersensor import PowersensorConfigFlow
from custom_components.powersensor.const import (
  DOMAIN,
  ROLE_UPDATE_SIGNAL,
  SENSOR_NAME_FORMAT,
)
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo
from ipaddress import ip_address

MAC="a4cf1218f158"
SECOND_MAC="a4cf1218f160"

@pytest.fixture(autouse=True)
def bypass_setup(monkeypatch):
  monkeypatch.setattr(custom_components.powersensor, "async_setup_entry", AsyncMock(return_value=True))


def validate_config_data(data):
  assert isinstance(data['devices'], dict)
  assert isinstance(data['roles'], dict)


### Tests ################################################

async def test_user(hass):
  result = await hass.config_entries.flow.async_init(
    DOMAIN, context={"source": config_entries.SOURCE_USER}
  )
  assert result["type"] == FlowResultType.FORM
  assert result["step_id"] == "manual_confirm"

  result = await hass.config_entries.flow.async_configure(
    result["flow_id"],
    user_input={"next_step_id": result["step_id"]},
  )
  assert result["type"] == FlowResultType.CREATE_ENTRY
  validate_config_data(result["data"])


async def test_zeroconf(hass):
  result = await hass.config_entries.flow.async_init(
    DOMAIN, context={"source": config_entries.SOURCE_ZEROCONF},
    data=ZeroconfServiceInfo(
      ip_address=ip_address("192.168.0.33"),
      ip_addresses=[ip_address("192.168.0.33")],
      hostname=f"Powersensor-gateway-{MAC}-civet.local",
      name=f"Powersensor-gateway-{MAC}-civet._powersensor._udp.local",
      port=49476,
      type="_powersensor._udp.local.",
      properties={
        "version": "1",
        "id": f"{MAC}",
      },
    )
  )
  assert result["type"] == FlowResultType.FORM
  assert result["step_id"] == "discovery_confirm"

  result = await hass.config_entries.flow.async_configure(
    result["flow_id"],
    user_input={"next_step_id": result["step_id"]},
  )
  assert result["type"] == FlowResultType.CREATE_ENTRY
  validate_config_data(result["data"])
  assert MAC in result["data"]['devices']

async def test_zeroconf_two_plugs(hass):
  result = await hass.config_entries.flow.async_init(
    DOMAIN, context={"source": config_entries.SOURCE_ZEROCONF},
    data=ZeroconfServiceInfo(
      ip_address=ip_address("192.168.0.33"),
      ip_addresses=[ip_address("192.168.0.33")],
      hostname=f"Powersensor-gateway-{MAC}-civet.local",
      name=f"Powersensor-gateway-{MAC}-civet._powersensor._udp.local",
      port=49476,
      type="_powersensor._udp.local.",
      properties={
        "version": "1",
        "id": f"{MAC}",
      },
    )
  )

  second_result = await hass.config_entries.flow.async_init(
      DOMAIN, context={"source": config_entries.SOURCE_ZEROCONF},
      data=ZeroconfServiceInfo(
          ip_address=ip_address("192.168.0.37"),
          ip_addresses=[ip_address("192.168.0.37")],
          hostname=f"Powersensor-gateway-{SECOND_MAC}-civet.local",
          name=f"Powersensor-gateway-{SECOND_MAC}-civet._powersensor._udp.local",
          port=49476,
          type="_powersensor._udp.local.",
          properties={
              "version": "1",
              "id": f"{SECOND_MAC}",
          },
      )
  )

  assert result["type"] == FlowResultType.FORM
  assert result["step_id"] == "discovery_confirm"

  result = await hass.config_entries.flow.async_configure(
    result["flow_id"],
    user_input={"next_step_id": result["step_id"]},
  )
  assert result["type"] == FlowResultType.CREATE_ENTRY
  validate_config_data(result["data"])
  assert MAC in result["data"]['devices']

  # # we expect the second plug config flow to get canceled if the integration has already been configured
  assert second_result["type"] == FlowResultType.ABORT

async def test_zeroconf_two_plugs_race(hass, monkeypatch):
    # WIP: this may not yet really simulate the race condition previously observed in HA
    call_count =0
    original_set_unique_id = PowersensorConfigFlow.async_set_unique_id
    async def delayed_set_unique_id(self, *args, **kwargs):
        nonlocal call_count
        call_count+=1
        if call_count == 1:
            await asyncio.sleep(1.0)
        return await original_set_unique_id(self, *args, **kwargs)

    monkeypatch.setattr(PowersensorConfigFlow, "async_set_unique_id", delayed_set_unique_id)
    task1 = asyncio.create_task( hass.config_entries.flow.async_init(
    DOMAIN, context={"source": config_entries.SOURCE_ZEROCONF},
    data=ZeroconfServiceInfo(
      ip_address=ip_address("192.168.0.33"),
      ip_addresses=[ip_address("192.168.0.33")],
      hostname=f"Powersensor-gateway-{MAC}-civet.local",
      name=f"Powersensor-gateway-{MAC}-civet._powersensor._udp.local",
      port=49476,
      type="_powersensor._udp.local.",
      properties={
        "version": "1",
        "id": f"{MAC}",
      },
    )
    )
    )
    await asyncio.sleep(0.99)
    task2 = asyncio.create_task( hass.config_entries.flow.async_init(
      DOMAIN, context={"source": config_entries.SOURCE_ZEROCONF},
      data=ZeroconfServiceInfo(
          ip_address=ip_address("192.168.0.37"),
          ip_addresses=[ip_address("192.168.0.37")],
          hostname=f"Powersensor-gateway-{SECOND_MAC}-civet.local",
          name=f"Powersensor-gateway-{SECOND_MAC}-civet._powersensor._udp.local",
          port=49476,
          type="_powersensor._udp.local.",
          properties={
              "version": "1",
              "id": f"{SECOND_MAC}",
          },
      )
    )
    )
    result, second_result = await asyncio.gather(task1, task2)

    assert second_result["type"] == FlowResultType.FORM
    assert second_result["step_id"] == "discovery_confirm"

    second_result = await hass.config_entries.flow.async_configure(
    second_result["flow_id"],
    user_input={"next_step_id": second_result["step_id"]},
    )
    assert second_result["type"] == FlowResultType.CREATE_ENTRY
    validate_config_data(second_result["data"])
    assert SECOND_MAC in second_result["data"]['devices']

    # # # we expect the plug arriving second in config flow to get canceled if the integration has already been configured
    assert result["type"] == FlowResultType.ABORT
    print(result["reason"])

async def test_zeroconf_two_plugs_skipping_unique_id(hass, monkeypatch):
    call_count = 0
    original_set_unique_id = PowersensorConfigFlow.async_set_unique_id

    async def delayed_set_unique_id(self, *args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            return None
        return await original_set_unique_id(self, *args, **kwargs)

    monkeypatch.setattr(PowersensorConfigFlow, "async_set_unique_id", delayed_set_unique_id)
    result = await hass.config_entries.flow.async_init(
    DOMAIN, context={"source": config_entries.SOURCE_ZEROCONF},
    data=ZeroconfServiceInfo(
      ip_address=ip_address("192.168.0.33"),
      ip_addresses=[ip_address("192.168.0.33")],
      hostname=f"Powersensor-gateway-{MAC}-civet.local",
      name=f"Powersensor-gateway-{MAC}-civet._powersensor._udp.local",
      port=49476,
      type="_powersensor._udp.local.",
      properties={
        "version": "1",
        "id": f"{MAC}",
      },
    )
    )

    second_result = await hass.config_entries.flow.async_init(
      DOMAIN, context={"source": config_entries.SOURCE_ZEROCONF},
      data=ZeroconfServiceInfo(
          ip_address=ip_address("192.168.0.37"),
          ip_addresses=[ip_address("192.168.0.37")],
          hostname=f"Powersensor-gateway-{SECOND_MAC}-civet.local",
          name=f"Powersensor-gateway-{SECOND_MAC}-civet._powersensor._udp.local",
          port=49476,
          type="_powersensor._udp.local.",
          properties={
              "version": "1",
              "id": f"{SECOND_MAC}",
          },
      )
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "discovery_confirm"

    result = await hass.config_entries.flow.async_configure(
    result["flow_id"],
    user_input={"next_step_id": result["step_id"]},
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    validate_config_data(result["data"])
    assert MAC in result["data"]['devices']

    # we expect the second plug config flow to get canceled if the integration has already been configured
    # but...for whatever reason that's not what's happening
    # @todo: determine if we like this behaviour and update test accordingly
    assert second_result["type"] == FlowResultType.FORM

async def test_zeroconf_already_discovered(hass):
  result = await hass.config_entries.flow.async_init(
    DOMAIN, context={"source": config_entries.SOURCE_ZEROCONF},
    data=ZeroconfServiceInfo(
      ip_address=ip_address("192.168.0.33"),
      ip_addresses=[ip_address("192.168.0.33")],
      hostname=f"Powersensor-gateway-{MAC}-civet.local",
      name=f"Powersensor-gateway-{MAC}-civet._powersensor._udp.local",
      port=49476,
      type="_powersensor._udp.local.",
      properties={
        "version": "1",
        "id": f"{MAC}",
      },
    )
  )

  result2 = await hass.config_entries.flow.async_init(
    DOMAIN, context={"source": config_entries.SOURCE_ZEROCONF},
    data=ZeroconfServiceInfo(
      ip_address=ip_address("192.168.0.33"),
      ip_addresses=[ip_address("192.168.0.33")],
      hostname=f"Powersensor-gateway-{MAC}-civet.local",
      name=f"Powersensor-gateway-{MAC}-civet._powersensor._udp.local",
      port=49476,
      type="_powersensor._udp.local.",
      properties={
        "version": "1",
        "id": f"{MAC}",
      },
    )
  )


  assert result["type"] == FlowResultType.FORM
  assert result["step_id"] == "discovery_confirm"
  assert result2["type"] == FlowResultType.ABORT
  assert result2["reason"] == "already_in_progress"

  result = await hass.config_entries.flow.async_configure(
    result["flow_id"],
    user_input={"next_step_id": result["step_id"]},
  )
  assert result["type"] == FlowResultType.CREATE_ENTRY
  validate_config_data(result["data"])
  assert MAC in result["data"]['devices']

async def test_zeroconf_missing_id(hass):
  """No plug should advertise without an 'id' property, but just in case..."""
  result = await hass.config_entries.flow.async_init(
    DOMAIN, context={"source": config_entries.SOURCE_ZEROCONF},
    data=ZeroconfServiceInfo(
      ip_address=ip_address("192.168.0.33"),
      ip_addresses=[ip_address("192.168.0.33")],
      hostname=f"Powersensor-gateway-{MAC}-civet.local",
      name=f"Powersensor-gateway-{MAC}-civet._powersensor._udp.local",
      port=49476,
      type="_powersensor._udp.local.",
      properties={
        "version": "1",
      },
    )
  )
  assert result["type"] == FlowResultType.ABORT


async def test_reconfigure(hass, monkeypatch, def_config_entry):
  # Make the config_flow use our precanned entry
  def my_entry(_):
    return def_config_entry
  monkeypatch.setattr(hass.config_entries, "async_get_entry", my_entry)

  # Kick off the reconfigure
  result = await hass.config_entries.flow.async_init(
    DOMAIN,
    context={
      "source": config_entries.SOURCE_RECONFIGURE,
      "entry_id": def_config_entry
    },
  )
  assert result["type"] == FlowResultType.FORM

  # Hook into role updates to see role change come through
  called = 0
  async def verify_roles(mac, role):
    nonlocal called
    called += 1
    assert (mac == 'cafebabe' and role == 'water')

  discon = async_dispatcher_connect(hass, ROLE_UPDATE_SIGNAL, verify_roles)

  # Prepare user_input, and submit it
  mac2name = { mac: SENSOR_NAME_FORMAT % mac for mac in def_config_entry.runtime_data['dispatcher'].sensors }
  result = await hass.config_entries.flow.async_configure(
    result["flow_id"],
    user_input={ mac2name['cafebabe']: 'water' }
  )
  discon()
  # Verify
  assert result["type"] == FlowResultType.ABORT
  assert called == 1


async def test_unknown_role(hass, monkeypatch, def_config_entry):
  # Make the config_flow use our precanned entry
  def my_entry(_):
    return def_config_entry
  monkeypatch.setattr(hass.config_entries, "async_get_entry", my_entry)

  # Kick off the reconfigure
  result = await hass.config_entries.flow.async_init(
    DOMAIN,
    context={
      "source": config_entries.SOURCE_RECONFIGURE,
      "entry_id": def_config_entry
    },
  )
  assert result["type"] == FlowResultType.FORM

  # Hook into role updates to see role change come through
  called = 0
  async def verify_roles(mac, role):
    nonlocal called
    called += 1
    assert (mac == 'd3adB33f' and role is None)

  discon = async_dispatcher_connect(hass, ROLE_UPDATE_SIGNAL, verify_roles)

  # Prepare user_input, and submit it
  mac2name = { mac: SENSOR_NAME_FORMAT % mac for mac in def_config_entry.runtime_data['dispatcher'].sensors }
  result = await hass.config_entries.flow.async_configure(
    result["flow_id"],
    user_input={ mac2name['d3adB33f']: '<unknown>' }
  )
  discon()
  # Verify
  assert result["type"] == FlowResultType.ABORT
  assert called == 1
