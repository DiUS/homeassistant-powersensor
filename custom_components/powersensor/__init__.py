"""The Powersensor integration."""
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform, EVENT_HOMEASSISTANT_STOP
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import PowersensorDataUpdateCoordinator
_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]



async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up integration from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    if entry.entry_id not in hass.data[DOMAIN]:
        _LOGGER.error(entry.entry_id)
        _LOGGER.error("sowr")
        hass.data[DOMAIN][entry.entry_id]  = PowersensorDataUpdateCoordinator(hass,entry)

    async def shutdown_cleanup(event):
        _LOGGER.warning(f"Homeassistant is shutting down. Forcing cleanup of {entry.entry_id}")
        await hass.data[DOMAIN][entry.entry_id] .stop()
        if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
            hass.data[DOMAIN].pop(entry.entry_id, None)
            if not hass.data[DOMAIN]:
                hass.data.pop(DOMAIN, None)
    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, shutdown_cleanup)
    _LOGGER.error("HEREHEHEHERHEHREHEHEHEH")
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    _LOGGER.error("BEEERBEERBERBEBERE")
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

    hass.data[DOMAIN].pop(entry.entry_id, None)
    if not hass.data[DOMAIN]:
        hass.data.pop(DOMAIN, None)

    _LOGGER.warning("Finished unloading for %s (unload_ok %s)", entry.entry_id, unload_ok)
    return unload_ok
