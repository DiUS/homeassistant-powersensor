"""The Powersensor integration."""
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from powersensor_local import VirtualHousehold

from .PowersensorMessageDispatacher import PowersensorMessageDispatcher
from .const import DOMAIN
_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up integration from a config entry."""

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {}
    my_data = hass.data[DOMAIN][entry.entry_id]

    # Establish our virtual household
    vhh = VirtualHousehold(my_data["with_solar"] if "with_solar" in my_data else False)
    entry.runtime_data = { "vhh": vhh }

    # TODO: can we move the dispatcher into the entry.runtime_data dict?
    my_data["dispatcher"] = PowersensorMessageDispatcher(hass, vhh)
    for mac, network_info in entry.data.items():
        my_data["dispatcher"].add_api(mac, network_info)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.warning("Started unloading for %s", entry.entry_id)
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        if DOMAIN in hass.data.keys():
            if entry.entry_id in hass.data[DOMAIN].keys():
                my_data = hass.data[DOMAIN][entry.entry_id]
                if "dispatcher" in my_data.keys():
                    await my_data["dispatcher"].disconnect()

    return unload_ok

