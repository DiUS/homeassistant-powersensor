"""DataUpdateCoordinator for the Powersensor integration."""
from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class PowersensorDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the plug."""

    def __init__(
        self,
        hass: HomeAssistant,
        session: aiohttp.ClientSession,
        host: str,
        port: int,
    ) -> None:
        """Initialize."""
        self.host = host
        self.port = port
        self.session = session
        
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Update data via library."""
        try:
            async with asyncio.timeout(10):
                async with self.session.get(
                    f"http://{self.host}:{self.port}/api/data"
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data
                    raise UpdateFailed(f"Error fetching data: {response.status}")
        except asyncio.TimeoutError as err:
            raise UpdateFailed(f"Timeout communicating with device: {err}") from err
        except Exception as err:
            raise UpdateFailed(f"Error communicating with device: {err}") from err
