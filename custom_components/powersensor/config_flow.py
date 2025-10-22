"""Config flow for the integration."""
import logging
from typing import Any
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.service_info import zeroconf
from homeassistant.helpers.selector import selector

from .const import DEFAULT_PORT, DOMAIN, SENSOR_NAME_FORMAT

def _extract_device_name(discovery_info) -> str:
    """Extract a user-friendly device name from zeroconf info."""
    properties = discovery_info.properties or {}

    if "id" in properties:
        return f"🔌 Mac({properties["id"].strip()})"

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


class PowersensorConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow."""

    VERSION = 2

    def __init__(self):
        """Initialize the config flow."""

    async def async_step_reconfigure(self, user_input: dict | None = None)->FlowResult:
        entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        dispatcher = entry.runtime_data["dispatcher"]

        mac2name = { mac: SENSOR_NAME_FORMAT % mac for mac in dispatcher.sensors }

        unknown = "<unknown>"
        if user_input is not None:
            name2mac = { name: mac for mac, name in mac2name.items() }
            for name, role in user_input.items():
                mac = name2mac.get(name)
                if role == unknown:
                    role = None
                _LOGGER.debug(f"Applying {role} to {mac}")
                async_dispatcher_send(self.hass, f"{DOMAIN}_update_role", mac, role)
            return self.async_abort(reason="Roles successfully applied!")

        sensor_roles = {}
        for sensor_mac in dispatcher.sensors:
            role = entry.data.get('roles', {}).get(sensor_mac, unknown)
            sel = selector({
                "select": {
                    "options": [
                        # Note: these strings are NOT subject to translation
                        "house-net", "solar", "water", "appliance", unknown
                    ],
                    "mode": "dropdown",
                }
            })
            sensor_roles[vol.Optional(mac2name[sensor_mac], description={"suggested_value": role})] = sel

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema(sensor_roles),
            description_placeholders={
                "device_count": str(len(sensor_roles)),
                "docs_url" : "https://dius.github.io/homeassistant-powersensor/data.html#virtual-household"
            }
        )

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
