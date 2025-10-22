import logging

from homeassistant.core import async_get_hass
from homeassistant.helpers.translation import async_get_cached_translations

from .const import DOMAIN


def translate(key: str) -> str:
    hass = async_get_hass()
    translations = async_get_cached_translations(hass, hass.config.language, "custom", DOMAIN)
    key = f"component.{DOMAIN}.custom.{key}"
    return translations.get(key, f"🚨 UNTRANSLATED:{key} 🚨")
