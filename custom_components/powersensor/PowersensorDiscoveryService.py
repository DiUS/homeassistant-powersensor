import asyncio
from typing import Optional
import logging

from homeassistant.core import HomeAssistant
from zeroconf import ServiceBrowser, ServiceListener, Zeroconf
from homeassistant.helpers.dispatcher import async_dispatcher_send
import homeassistant.components.zeroconf

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class PowersensorServiceListener(ServiceListener):
    def __init__(self, hass: HomeAssistant, debounce_timeout: float = 60):
        self._hass = hass
        self._plugs = {}
        self._pending_removals = {}
        self._debounce_seconds = debounce_timeout

    def add_service(self, zc, type_, name):
        info = self.__add_plug(zc, type_, name)
        if info:
            asyncio.run_coroutine_threadsafe(
                self._async_service_add(self._plugs[name]),
                self._hass.loop
            )

    async def _async_service_add(self, *args):
        async_dispatcher_send(self._hass, f"{DOMAIN}_zeroconf_add_plug", *args)

    async def _async_delayed_remove(self, name):
        """Actually process the removal after delay."""
        try:
            await asyncio.sleep(self._debounce_seconds)
            _LOGGER.info(f"Request to remove service {name} still pending after timeout. Processing remove request...")
            if name in self._plugs:
                data = self._plugs[name].copy()
                del self._plugs[name]
            else:
                data = None
            asyncio.run_coroutine_threadsafe(
                self._async_service_remove(name, data),
                self._hass.loop
            )
        except asyncio.CancelledError:
            # Task was cancelled because service came back
            _LOGGER.info(f"Request to remove service {name} was canceled by request to update or add plug.")

        # Either way were done with this task
        self._pending_removals.pop(name, None)

    def remove_service(self, zc, type_, name):
        if name in self._pending_removals:
            # removal for this service is already pending
            return

        _LOGGER.info(f"Scheduling removal for {name}")
        self._pending_removals[name] = asyncio.create_task(self._async_delayed_remove(name))


    async def _async_service_remove(self, *args):
        async_dispatcher_send(self._hass, f"{DOMAIN}_zeroconf_remove_plug", *args)

    def update_service(self, zc, type_, name):
        info = self.__add_plug(zc, type_, name)
        if info:
            asyncio.run_coroutine_threadsafe(
                self._async_service_update(self._plugs[name]),
                self._hass.loop
            )

    async def _async_service_update(self, *args):
        async_dispatcher_send(self._hass, f"{DOMAIN}_zeroconf_update_plug", *args)

    def __add_plug(self, zc, type_, name):
        info = zc.get_service_info(type_, name)
        task = self._pending_removals.pop(name, None)
        if task:
            task.cancel()
            _LOGGER.info(f"Cancelled pending removal for {name}")
        if info:
            self._plugs[name] = {'type': type_,
                                 'name': name,
                                 'addresses': ['.'.join(str(b) for b in addr) for addr in info.addresses],
                                 'port': info.port,
                                 'server': info.server,
                                 'properties': info.properties
                                 }
        return info


class PowersensorDiscoveryService:
    def __init__(self, hass: HomeAssistant, service_type: str = "_powersensor._tcp.local."):
        self._hass = hass
        self.service_type = service_type

        self.zc: Optional[Zeroconf] = None
        self.listener: Optional[PowersensorServiceListener] = None
        self.browser: Optional[ServiceBrowser] = None
        self.running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self):
        """Start the mDNS discovery service"""
        if self.running:
            return

        self.running = True
        self.zc = await homeassistant.components.zeroconf.async_get_instance(self._hass)
        self.listener = PowersensorServiceListener(self._hass)

        # Create browser
        self.browser = ServiceBrowser(self.zc, self.service_type, self.listener)

        # Start the background task
        self._task = asyncio.create_task(self._run())

    async def _run(self):
        """Background task that keeps the service alive"""
        try:
            while self.running:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass

    async def stop(self):
        """Stop the mDNS discovery service"""
        self.running = False

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        if self.zc:
            # self.zc.close()
            self.zc = None

        self.browser = None
        self.listener = None