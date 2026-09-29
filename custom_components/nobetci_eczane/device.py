"""Shared Home Assistant device metadata."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo

from .const import DOMAIN, SOURCE_NAME, SOURCE_URL


def device_info(entry: ConfigEntry) -> DeviceInfo:
    """Return the service device shared by configuration entities."""
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name=entry.title,
        manufacturer=SOURCE_NAME,
        model="Nöbetçi Eczane Web Servisi",
        configuration_url=SOURCE_URL,
        entry_type=DeviceEntryType.SERVICE,
    )
