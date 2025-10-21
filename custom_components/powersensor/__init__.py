"""The Powersensor integration."""
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.loader import async_get_integration

from powersensor_local import VirtualHousehold

from .PowersensorDiscoveryService import PowersensorDiscoveryService
from .PowersensorMessageDispatcher import PowersensorMessageDispatcher
from .config_flow import PowersensorConfigFlow
from .const import DOMAIN
_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]

#
# config entry.data structure (version 2.1):
#   {
#     devices = {
#       mac = {
#         name =,
#         display_name =,
#         mac =,
#         host =,
#         port =,
#         role =,
#     }
#     with_solar =,
#   }
#

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
    vhh = VirtualHousehold(entry.data['with_solar'])

    # Set up message dispatcher
    dispatcher = PowersensorMessageDispatcher(hass, vhh)
    for mac, network_info in entry.data['devices'].items():
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

    hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate old config entry."""
    _LOGGER.debug("Upgrading config from %s.%s", entry.version, entry.minor_version)
    if entry.version > PowersensorConfigFlow.VERSION:
        # Downgrade from future version
        return False

    if entry.version == 1:
        # Move device info into subkey, add with_solar key
        devices = { **entry.data }
        new_data = { 'devices': devices, 'with_solar': False }
        hass.config_entries.async_update_entry(entry, data=new_data, version=2, minor_version=1)

    _LOGGER.debug("Upgrading config to %s.%s", entry.version, entry.minor_version)
    return True

