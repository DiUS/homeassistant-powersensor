"""The Powersensor integration."""
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.loader import async_get_integration

from powersensor_local import VirtualHousehold

from .PowersensorDiscoveryService import PowersensorDiscoveryService
from .PowersensorMessageDispatacher import PowersensorMessageDispatcher
from .const import DOMAIN
_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up integration from a config entry."""

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {}

    integration = await async_get_integration(hass, DOMAIN)
    manifest  = integration.manifest

    # Establish create the zeroconf discovery service
    zeroconf_service= PowersensorDiscoveryService(hass, manifest["zeroconf"][0])
    await zeroconf_service.start()

    # Establish our virtual household
    vhh = VirtualHousehold(False)


    # TODO: can we move the dispatcher into the entry.runtime_data dict?
    dispatcher = PowersensorMessageDispatcher(hass, vhh)
    for mac, network_info in entry.data.items():
        await dispatcher.enqueue_plug_for_adding(network_info)

    entry.runtime_data = { "vhh": vhh , "dispatcher" : dispatcher, "zeroconf" : zeroconf_service}
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("Started unloading for %s", entry.entry_id)
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        if "dispatcher" in entry.runtime_data .keys():
            await entry.runtime_data["dispatcher"].disconnect()
        if "zeroconf" in entry.runtime_data .keys():
            await entry.runtime_data["zeroconf"].stop()

    return unload_ok

