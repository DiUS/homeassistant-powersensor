"""Common fixtures for powersensor integration tests."""

from collections.abc import AsyncGenerator, Callable, Coroutine
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from powersensor_local.zeroconf_devices import PowersensorZeroconfDevices
import pytest

from custom_components.powersensor.config_flow import PowersensorConfigFlow
from custom_components.powersensor.const import DOMAIN
from homeassistant.core import HomeAssistant

from pytest_homeassistant_custom_component.common import MockConfigEntry

@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Placeholder fixture that is a no-op for enabling custom integrations."""

def _make_mock_devices() -> MagicMock:
    """Return a mock PowersensorZeroconfDevices.

    start() captures the callback so tests can inject events directly.
    The mock never opens real sockets.
    """
    devices = MagicMock(spec=PowersensorZeroconfDevices)
    devices.start = AsyncMock()
    devices.stop = AsyncMock()
    devices.subscribe = MagicMock()
    devices.unsubscribe = MagicMock()
    return devices


@pytest.fixture
def mock_devices() -> MagicMock:
    """Expose mock devices so individual tests can inspect call counts."""
    return _make_mock_devices()


@pytest.fixture
async def config_entry(
    hass: HomeAssistant,
    mock_devices: MagicMock,
    mock_async_zeroconf: MagicMock,
) -> AsyncGenerator[MockConfigEntry]:
    """Set up a powersensor config entry with a mocked library.

    Yields the entry after setup so tests can:
      - call ``await fire(event_dict)`` to inject library events
      - assert on hass.states, entity registry, device registry
      - unload and re-check teardown

    Requesting ``mock_async_zeroconf`` prevents the real zeroconf component
    from opening any sockets during dependency setup.
    """
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"roles": {}},
        version=PowersensorConfigFlow.VERSION,
        minor_version=PowersensorConfigFlow.MINOR_VERSION,
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.powersensor.PowersensorZeroconfDevices",
        return_value=mock_devices,
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        yield entry


@pytest.fixture
def fire(
    mock_devices: MagicMock,
) -> Callable[[dict[str, Any]], Coroutine[Any, Any, None]]:
    """Return an async helper that injects a library event into the integration.

    Usage::

        await fire({"event": "device_found", "mac": "aabbcc112233", "device_type": "plug"})
    """

    async def _fire(event: dict[str, Any]) -> None:
        cb = mock_devices.start.call_args[0][0]
        await cb(event)

    return _fire
