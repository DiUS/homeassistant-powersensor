"""The Powersensor integration."""
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import PowersensorDataUpdateCoordinator
_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]



async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up integration from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    plug_coordinator = PowersensorDataUpdateCoordinator(hass,entry)
    hass.data[DOMAIN][entry.entry_id] = plug_coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.warning("Started unloading for %s", entry.entry_id)
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        if DOMAIN in hass.data.keys():
            if entry.entry_id in hass.data[DOMAIN].keys():
                    plug_coordinator = hass.data[DOMAIN][entry.entry_id]
                    await plug_coordinator.stop()
                    del hass.data[DOMAIN][entry.entry_id]

            if 'discovered_plugs' in hass.data[DOMAIN].keys():
                del hass.data[DOMAIN]['discovered_plugs']
    _LOGGER.warning("Finished unloading for %s (unload_ok %s)", entry.entry_id, unload_ok)

    return unload_ok
