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
    _LOGGER.info(f"Adding Plug Api with entry_id={entry.entry_id} and mac={entry.data["mac"]} to {DOMAIN} apis." )
    plug_coordinator = PowersensorDataUpdateCoordinator(hass, entry)
    hass.data[DOMAIN][entry.entry_id] = plug_coordinator


    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        if DOMAIN in hass.data.keys():
            if entry.entry_id in hass.data[DOMAIN].keys():
                    _LOGGER.info(
                        f"Removing Plug Api with entry_id={entry.entry_id} and mac={entry.data["mac"]} from {DOMAIN}.")
                    plug_coordinator = hass.data[DOMAIN][entry.entry_id]
                    await plug_coordinator.stop()
                    del hass.data[DOMAIN][entry.entry_id]
    
    return unload_ok
