import pytest
from asyncmock import AsyncMock
from custom_components.powersensor.const import DOMAIN, SENSOR_NAME_FORMAT
import custom_components.powersensor
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo
from ipaddress import ip_address

MAC="a4cf1218f158"

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
  def my_entry(_):
    return def_config_entry
  monkeypatch.setattr(hass.config_entries, "async_get_entry", my_entry)
  result = await hass.config_entries.flow.async_init(
    DOMAIN,
    context={
      "source": config_entries.SOURCE_RECONFIGURE,
      "entry_id": def_config_entry
    },
  )
  assert result["type"] == FlowResultType.FORM

  mac2name = { mac: SENSOR_NAME_FORMAT % mac for mac in def_config_entry.runtime_data['dispatcher'].sensors }
  result = await hass.config_entries.flow.async_configure(
    result["flow_id"],
    user_input={ mac2name['cafebabe']: 'water' }
  )
  assert result["type"] == FlowResultType.ABORT
