"""Tests covering the generic/abstract Powersensor Entity class and subclasses."""

import importlib
from unittest.mock import Mock

from powersensor_local import VirtualHousehold
import pytest

from custom_components.powersensor.const import DOMAIN
from custom_components.powersensor.sensor.plug_measurements import (
    PlugMeasurements,
)
from custom_components.powersensor.sensor.powersensor_entity import (
    PowersensorEntity, PowersensorSensorEntityDescription,
)
from custom_components.powersensor.sensor.powersensor_household_entity import (
    HouseholdMeasurements,
    PowersensorHouseholdEntity,
)
from custom_components.powersensor.sensor.powersensor_plug_entity import (
    PowersensorPlugEntity,
)
from custom_components.powersensor.sensor.powersensor_sensor_entity import (
    PowersensorSensorEntity,
)
from custom_components.powersensor.sensor.sensor_measurements import (
    SensorMeasurements,
)
from homeassistant.core import HomeAssistant

MAC = "a4cf1218f158"


@pytest.fixture
def mock_config():
    """Create a mock service info."""
    return {
        SensorMeasurements.SUMMATION_ENERGY: PowersensorSensorEntityDescription(
            key="Total Energy",
            device_class=None,
            native_unit_of_measurement=None,
            suggested_display_precision=2,
            state_class=None,
            event="summation_energy",
            message_key="summation_joules",
            conversion_function=lambda v: v / 3600000.0,
        )
    }


### Tests ################################################
@pytest.mark.asyncio
async def test_generic_powersensor_entity(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch, mock_config
) -> None:
    """Test behavior of generic Powersensor entities.

    This test verifies that:
    - Device info and availability tracking work as expected.
    - Role updates are handled correctly, including renaming logic.
    """
    _config = mock_config

    monkeypatch.setattr(
        PowersensorEntity,
        "device_info",
        lambda self: {
            "identifiers": {(DOMAIN, self._mac)},
            "manufacturer": "Powersensor",
            "model": self._model,
            "translation_key": "unknown_sensor",
        },
    )

    monkeypatch.setattr(PowersensorEntity, "async_write_ha_state", lambda self: None)
    entity = PowersensorEntity(
        hass, "", MAC, "house-net", _config, SensorMeasurements.SUMMATION_ENERGY
    )

    assert not entity.available
    assert entity._remove_unavailability_tracker is None
    entity._handle_update("event", {})
    assert entity.available

    entity._schedule_unavailable()
    assert entity._remove_unavailability_tracker is not None
    entity._handle_update("event", {})
    assert entity._remove_unavailability_tracker is not None
    assert callable(entity._remove_unavailability_tracker)

    await entity._async_make_unavailable(None)
    assert not entity.available

    # this should not be implemented for generics and "renaming" should fail and be false
    assert not entity._rename_based_on_role()
    entity._handle_role_update(MAC + "garbage", "solar")
    # should not have gotten renamed
    assert entity._role == "house-net"

    # to trigger renaming logic for abstract clas we need to
    entity._handle_role_update(MAC, "solar")
    # should now be solar
    assert entity._role == "solar"


@pytest.mark.asyncio
async def test_powersensor_sensor_default_name(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test behavior of PowersensorSensorEntity when using default names.

    This test verifies that:
    - The entity's name and device name are correctly updated based on the role.
    - The entity can be successfully added to Home Assistant.
    """
    entity = PowersensorSensorEntity(
        hass, "", MAC, "house-net", SensorMeasurements.SUMMATION_ENERGY
    )
    assert entity.device_info["translation_key"] == "mains_sensor"

    entity._current_translation_key = "unknown_sensor"
    assert entity.device_info["translation_key"] == "unknown_sensor"

    entity._rename_based_on_role()
    entity._rename_based_on_role()  # activate other branch where renaming isn't required
    assert entity.device_info["translation_key"] == "mains_sensor"

    # try adding it to hass directly
    await entity.async_added_to_hass()


@pytest.mark.asyncio
async def test_powersensor_sensor_entity_device_info(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Tests PowersensorSensorEntity provides proper device info data."""
    entity = PowersensorSensorEntity(
        hass, "", MAC, "solar", SensorMeasurements.SUMMATION_ENERGY
    )
    info = entity.device_info
    assert info["manufacturer"] is not None
    assert info["model"] is not None
    assert info["translation_key"] is not None
    assert info["translation_placeholders"] is not None

@pytest.mark.asyncio
async def test_powersensor_plug_entity_device_info(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Tests PowersensorPlugEntity provides proper device info data."""
    entity = PowersensorPlugEntity(
        hass, "", MAC, "appliance", PlugMeasurements.SUMMATION_ENERGY
    )
    info = entity.device_info
    assert info["manufacturer"] is not None
    assert info["model"] is not None
    assert info["translation_key"] is not None
    assert info["translation_placeholders"] is not None


@pytest.mark.asyncio
async def test_powersensor_virtual_household(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test behavior of PowersensorHouseholdEntity.

    This test verifies that:
    - The entity can be successfully added to Home Assistant.
    - The entity correctly updates its native value from events.
    - The entity correctly handles resets and removals.
    """
    vhh = VirtualHousehold(False)
    # we'll do everything but write the HA state
    monkeypatch.setattr(
        PowersensorHouseholdEntity, "async_write_ha_state", lambda self: None
    )
    power_from_grid_entity = PowersensorHouseholdEntity(
        vhh, HouseholdMeasurements.POWER_FROM_GRID
    )
    energy_from_grid = PowersensorHouseholdEntity(
        vhh, HouseholdMeasurements.ENERGY_FROM_GRID
    )

    # does this error?
    await power_from_grid_entity.async_added_to_hass()
    await energy_from_grid.async_added_to_hass()

    # does these error?
    await power_from_grid_entity._on_event("test-event", {"watts": 123})
    assert power_from_grid_entity.native_value == 123
    await energy_from_grid._on_event("test-event", {"summation_joules": 12356789})
    assert energy_from_grid.native_value == 12356789 / 3600000
    await energy_from_grid._on_event(
        "test-event", {"summation_resettime_utc": 1762345678}
    )

    # does this error?
    await power_from_grid_entity.async_will_remove_from_hass()
    await energy_from_grid.async_will_remove_from_hass()


@pytest.mark.asyncio
async def test_entity_removal(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test removal of PowersensorSensorEntity.

    This test verifies that:
    - The entity's unavailability tracker is correctly scheduled.
    - The entity's unavailability tracker is called when removing from Home Assistant.
    """
    entity = PowersensorSensorEntity(
        hass, "", MAC, "house-net", SensorMeasurements.SUMMATION_ENERGY
    )
    entity._has_recently_received_update_message = True  # make available

    assert entity._remove_unavailability_tracker is None
    entity._schedule_unavailable()
    assert entity._remove_unavailability_tracker is not None
    entity._remove_unavailability_tracker = Mock()
    await entity.async_will_remove_from_hass()
    entity._remove_unavailability_tracker.assert_called_once_with()


@pytest.mark.asyncio
async def test_powersensor_sensor_handle_role_update(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test handling of role updates in PowersensorSensorEntity.

    This test verifies that:
    - The entity's name and device name are correctly updated based on the new role.
    - The Home Assistant registry is accessed when handling the update.
    """

    powersensor_entity_module = importlib.import_module(
        "custom_components.powersensor.sensor.powersensor_entity"
    )
    device = Mock()

    device_registry = Mock()
    device_registry.async_get_device.return_value = device
    device_registry.async_get_or_create.return_value = "ignored"

    dr = Mock()
    dr.async_get.return_value = device_registry

    monkeypatch.setattr(powersensor_entity_module, "dr", dr)

    write_state = Mock()
    monkeypatch.setattr(
        PowersensorEntity, "async_write_ha_state", write_state
    )

    entity = PowersensorSensorEntity(
        hass, "", MAC, "house-net", SensorMeasurements.SUMMATION_ENERGY
    )
    assert entity.device_info["translation_key"] == "mains_sensor"

    entity._handle_role_update(MAC, "solar")

    assert dr.async_get.call_count == 1
    assert device_registry.async_get_or_create.call_count == 1
    assert entity.device_info["translation_key"] == "solar_sensor"

    # try adding it to hass directly
    await entity.async_added_to_hass()


@pytest.mark.asyncio
async def test_powersensor_entity_handle_update(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch, mock_config
) -> None:
    """Test handling of updates in PowersensorEntity.

    This test verifies that:
    - The entity correctly handles new measurements and updates its native value.
    - The entity's _has_recently_received_update_message flag is set correctly.
    """
    async_write_ha_state = Mock()
    monkeypatch.setattr(
        PowersensorEntity,
        "device_info",
        lambda self: {
            "identifiers": {(DOMAIN, self._mac)},
            "manufacturer": "Powersensor",
            "model": self._model,
            "name": self._device_name,
        },
    )
    monkeypatch.setattr(PowersensorEntity, "async_write_ha_state", async_write_ha_state)
    _config = mock_config
    entity = PowersensorEntity(
        hass, "", MAC, "house-net", _config, SensorMeasurements.SUMMATION_ENERGY
    )
    assert not entity._has_recently_received_update_message

    message = {"summation_joules": 123456789}
    entity._handle_update(None, message)
    assert entity._has_recently_received_update_message
    assert entity.native_value == 123456789 / 3600000

    entity._message_callback = None
    entity._has_recently_received_update_message = False
    entity._handle_update(None, message)
    assert entity._has_recently_received_update_message
    assert entity.native_value == 123456789
