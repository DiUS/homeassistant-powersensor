"""Config flow for the integration."""
import asyncio
import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.helpers.service_info import zeroconf
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_NAME
from homeassistant.helpers import config_validation as cv

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

    VERSION = 1

    def __init__(self):
        """Initialize the config flow."""
        self._discovered_port = None
        self._discovered_name = None
        self._discovered_host = None
        self.discovery_info = {}

    async def async_step_user(self, user_input=None) -> ConfigFlowResult:
        """Handle manual user setup."""
        errors = {}

        if user_input is not None:
            # Validate the host/connection here if needed
            try:
                # Set unique ID based on host to prevent duplicates
                await self.async_set_unique_id(user_input[CONF_HOST])
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=user_input[CONF_NAME],
                    data=user_input
                )
            except Exception as ex:
                _LOGGER.error("Error validating configuration: %s", ex)
                errors["base"] = "cannot_connect"

        data_schema = vol.Schema(
            {
                vol.Required(CONF_NAME): cv.string,
                vol.Required(CONF_HOST): cv.string,
                vol.Optional(CONF_PORT, default=80): cv.port,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors
        )

    async def async_step_zeroconf(
        self, discovery_info: zeroconf.ZeroconfServiceInfo
    ) -> ConfigFlowResult:
        """Handle zeroconf discovery."""
        host = discovery_info.host
        port = discovery_info.port or DEFAULT_PORT
        name = _extract_device_name(discovery_info) or ""

        # Set unique_id to prevent duplicate entries
        await self.async_set_unique_id(f"{host}:{port}")
        self._abort_if_unique_id_configured(
            updates={CONF_HOST: host, CONF_PORT: port}
        )

        self.context.update({
            "title_placeholders": {
                "name": name,
                "host": host,
            }
        })
        # Store discovered info
        self._discovered_host = host
        self._discovered_name = name
        self._discovered_port = port
        self.discovery_info = {CONF_HOST: host, CONF_PORT: port}

        return await self.async_step_discovery_confirm()

    async def async_step_discovery_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm discovery."""
        if user_input is not None:
            # Create the entry with discovered data
            data = {
                CONF_NAME: self._discovered_name,
                CONF_HOST: self._discovered_host,
                CONF_PORT: self._discovered_port,
            }
            result = self.async_create_entry(
                title=self._discovered_name +" @ " + self._discovered_host,
                data=data
            )
            return result
        return self.async_show_form(step_id="discovery_confirm",
            description_placeholders={
                "name": self._discovered_name,
                "host": self._discovered_host,
                "port": self._discovered_port,
            },
        )