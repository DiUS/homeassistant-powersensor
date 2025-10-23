from datetime import timedelta
from typing import Callable, Union

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.dispatcher import async_dispatcher_connect, async_dispatcher_send
from homeassistant.helpers.event import async_track_point_in_utc_time
from homeassistant.util.dt import utcnow
from .PlugMeasurements import PlugMeasurements
from .SensorMeasurements import SensorMeasurements
from .const import DATA_UPDATE_SIGNAL_FMT_MAC_EVENT, DOMAIN, ROLE_UPDATE_SIGNAL

import logging
_LOGGER = logging.getLogger(__name__)

class PowersensorEntity(SensorEntity):
    """Powersensor Plug Class--designed to handle all measurements of the plug--perhaps less expressive"""
    def __init__(self, hass: HomeAssistant, mac: str, role: str,
                 input_config: dict[Union[SensorMeasurements|PlugMeasurements], dict],
                 measurement_type: SensorMeasurements|PlugMeasurements, timeout_seconds: int = 60):
        """Initialize the sensor."""
        self._role = role
        self._has_recently_received_update_message = False
        self._attr_native_value = 0.0
        self._hass = hass
        self._mac = mac
        self._model = f"PowersensorDevice"
        self._device_name = f'Powersensor Device (ID: {self._mac})'
        self._measurement_name= None
        self._remove_unavailability_tracker = None
        self._timeout = timedelta(seconds=timeout_seconds)  # Adjust as needed

        self.measurement_type = measurement_type
        config = input_config[measurement_type]
        self._attr_unique_id = f"powersensor_{mac}_{measurement_type}"
        self._attr_device_class = config.get("device_class", None)
        self._attr_native_unit_of_measurement = config.get("unit", None)
        self._attr_device_info = self.device_info
        self._attr_suggested_display_precision = config.get("precision", None)
        self._attr_entity_registry_visible_default = config.get('visible', True)
        self._attr_entity_category = config.get('category', None)
        self._attr_state_class = config.get('state_class', None)

        self._signal = DATA_UPDATE_SIGNAL_FMT_MAC_EVENT % (mac, config['event'])
        self._message_key = config.get('message_key', None)
        self._message_callback = config.get('callback', None)

    @property
    def device_info(self) -> DeviceInfo:
        raise NotImplementedError

    @property
    def available(self) -> bool:
        """Does data exist for this sensor type"""
        return self._has_recently_received_update_message

    def _schedule_unavailable(self):
        """Schedule entity to become unavailable."""
        if self._remove_unavailability_tracker:
            self._remove_unavailability_tracker()

        self._remove_unavailability_tracker = async_track_point_in_utc_time(
            self._hass,
            self._async_make_unavailable,
            utcnow() + self._timeout
        )

    async def _async_make_unavailable(self, _now):
        """Mark entity as unavailable."""
        self._has_recently_received_update_message = False
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Subscribe to messages when added to home assistant"""
        self._has_recently_received_update_message = False
        self.async_on_remove(async_dispatcher_connect(
            self._hass,
            self._signal,
            self._handle_update
        ))
        self.async_on_remove(async_dispatcher_connect(
            self._hass,
            ROLE_UPDATE_SIGNAL,
            self._handle_role_update
        ))

    async def async_will_remove_from_hass(self):
        """Clean up."""
        if self._remove_unavailability_tracker:
            self._remove_unavailability_tracker()

    def _rename_based_on_role(self):
        return False

    @callback
    def _handle_role_update(self, mac: str, role: str):
        if self._mac != mac or self._role == role:
            return

        self._role = role
        name_updated = self._rename_based_on_role()

        if name_updated:
            device_registry = dr.async_get(self._hass)
            device = device_registry.async_get_device(
                identifiers={(DOMAIN, self._mac)}
            )

            if device and device.name != self._device_name:
                # Update the device name
                device_registry.async_update_device(
                    device.id,
                    name=self._device_name
                )

            entity_registry = er.async_get(self._hass)
            entity_registry.async_update_entity(
                self.entity_id,
                name = self._attr_name
            )

            self.async_write_ha_state()

    @callback
    def _handle_update(self, event, message):
        """handle pushed data."""

        # event is not presently used, but is passed to maintain flexibility for future development

        self._has_recently_received_update_message = True

        if self._message_key in message.keys():
            if self._message_callback:
                self._attr_native_value = self._message_callback( message[self._message_key])
            else:
                self._attr_native_value = message[self._message_key]
        self._schedule_unavailable()

        self.async_write_ha_state()
