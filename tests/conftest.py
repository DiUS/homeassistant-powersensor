import pytest
import zeroconf
import homeassistant.components.zeroconf

from custom_components.powersensor.config_flow import PowersensorConfigFlow
from custom_components.powersensor.const import DOMAIN
from homeassistant.config_entries import ConfigEntryState
from powersensor_local import PlugListenerUdp
from pytest_homeassistant_custom_component.common import MockConfigEntry


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
  pass


@pytest.fixture(autouse=True)
def no_powersensor_local(monkeypatch):
  def no_connect(self):
    pass
  monkeypatch.setattr(PlugListenerUdp, "connect", no_connect)


@pytest.fixture(autouse=True)
def no_zeroconf(monkeypatch):
    async def no_zc(hass):
      return None
    monkeypatch.setattr(homeassistant.components.zeroconf, "async_get_instance", no_zc)
    def empty_zc_init(self, service_type, listener, _):
      pass
    monkeypatch.setattr(zeroconf.ServiceBrowser, "__init__", empty_zc_init)


@pytest.fixture
def def_config_entry():
  entry = MockConfigEntry(
    domain=DOMAIN,
    data={
      'devices': {
        '0123456789abcd': {
          'name': 'test-plug',
          'display_name': 'Test Plug',
          'mac': '0123456789abcd',
          'host': '192.168.0.33',
          'port': 49476,
        }
      },
      'with_solar': False,
      'roles': { 'c001eat5': 'house-net', 'cafebabe': 'solar' },
    },
    entry_id="test",
    version=PowersensorConfigFlow.VERSION,
    minor_version=1,
    state=ConfigEntryState.LOADED,
  )
  class MockDispatcher:
    sensors = [ 'coo1eat5', 'cafebabe' ]
  entry.runtime_data={ 'dispatcher': MockDispatcher() }
  return entry
