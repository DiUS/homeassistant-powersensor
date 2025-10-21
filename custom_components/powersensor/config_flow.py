"""Config flow for the integration."""
import logging
from typing import Any
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.helpers.service_info import zeroconf
from homeassistant.const import CONF_HOST, CONF_PORT

from .const import DEFAULT_PORT, DOMAIN

def _extract_device_name(discovery_info) -> str:
    """Extract a user-friendly device name from zeroconf info."""
    properties = discovery_info.properties or {}

    if "id" in properties:
        return f'🔌 Mac({properties["id"].strip()})'
    # Fall back to cleaning up the service name
    name = discovery_info.name or ""

    # Remove common suffixes
    if name.endswith(".local."):
        name = name[:-7]
    if "._" in name:
        name = name.split("._")[0]

    # Replace common patterns
    name = name.replace("-", " ")
    name = name.replace("_", " ")

    # Capitalize words
    name = " ".join(word.capitalize() for word in name.split())

    # If still not great, add a prefix
    if not name or len(name) < 3:
        name = f"Device at {discovery_info.host}"

    return name

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
    }
)


class PowersensorConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow."""

    VERSION = 2

    def __init__(self):
        """Initialize the config flow."""

    # async def async_step_user(self, user_input=None) -> ConfigFlowResult:
    #     """Handle manual user setup."""
    #     errors = {}
    #
    #     if user_input is not None:
    #         # Validate the host/connection here if needed
    #         try:
    #             # Set unique ID based on host to prevent duplicates
    #             await self.async_set_unique_id(user_input[CONF_HOST])
    #             self._abort_if_unique_id_configured()
    #
    #             return self.async_create_entry(
    #                 title=user_input[CONF_NAME],
    #                 data=user_input
    #             )
    #         except Exception as ex:
    #             _LOGGER.error("Error validating configuration: %s", ex)
    #             errors["base"] = "cannot_connect"
    #
    #     data_schema = vol.Schema(
    #         {
    #             vol.Required(CONF_NAME): cv.string,
    #             vol.Required(CONF_HOST): cv.string,
    #             vol.Optional(CONF_PORT, default=80): cv.port,
    #         }
    #     )
    #
    #     return self.async_show_form(
    #         step_id="user",
    #         data_schema=data_schema,
    #         errors=errors
    #     )

    async def async_step_zeroconf(
        self, discovery_info: zeroconf.ZeroconfServiceInfo
    ) -> ConfigFlowResult:
        """Handle zeroconf discovery."""
        host = discovery_info.host
        port = discovery_info.port or DEFAULT_PORT
        display_name = _extract_device_name(discovery_info) or ""
        properties = discovery_info.properties or {}
        mac = None
        if "id" in properties:
            mac = properties["id"].strip()

        plug_data = {'host' : host,'port' :  port,  'display_name' : display_name,
                     'mac': mac, 'name': discovery_info.name}

        if DOMAIN not in self.hass.data:
            self.hass.data[DOMAIN] = {}

        discovered_plugs_key = "discovered_plugs"
        if discovered_plugs_key not in self.hass.data[DOMAIN]:
            self.hass.data[DOMAIN][discovered_plugs_key] = {}

        if mac in self.hass.data[DOMAIN][discovered_plugs_key].keys():
            _LOGGER.debug("Mac found existing in data!")
        else:
            self.hass.data[DOMAIN][discovered_plugs_key][mac] = plug_data



        # register a unique id for the single power sensor entry
        await self.async_set_unique_id(DOMAIN)

        # abort now if configuration is on going in another thread (i.e. this thread isn't the first)
        if self._async_current_entries() or self._async_in_progress():
            _LOGGER.warning("Aborting - found existing entry!")
            return self.async_abort(reason="already_configured")

        display_name = f"⚡ Powersensor 🔌\n"
        self.context.update({
            "title_placeholders": {
                "name": display_name
            }
        })
        return await self.async_step_discovery_confirm()

    async def async_step_discovery_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:

        """Confirm discovery."""
        if user_input is not None:
            _LOGGER.debug(self.hass.data[DOMAIN]["discovered_plugs"])
            return self.async_create_entry(
                title="Powersensor",
                data={
                    'devices': self.hass.data[DOMAIN]["discovered_plugs"],
                    'with_solar': False,
                    'roles': {},
                }
            )
        return self.async_show_form(step_id="discovery_confirm")
