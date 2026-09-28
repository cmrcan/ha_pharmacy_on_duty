"""Nöbetçi Eczane integration."""

from __future__ import annotations

from pathlib import Path
from typing import TypeAlias

from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import NobetciEczaneClient
from .const import CARD_URL, DOMAIN
from .coordinator import NobetciEczaneCoordinator

NobetciEczaneConfigEntry: TypeAlias = ConfigEntry[NobetciEczaneCoordinator]

PLATFORMS = [Platform.GEO_LOCATION, Platform.SENSOR]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up shared frontend resources."""
    static_path = Path(__file__).parent / "static" / "nobetci-eczane-card.js"
    await hass.http.async_register_static_paths(
        [StaticPathConfig(CARD_URL, str(static_path), cache_headers=True)]
    )
    return True


async def async_setup_entry(
    hass: HomeAssistant, entry: NobetciEczaneConfigEntry
) -> bool:
    """Set up Nöbetçi Eczane from a config entry."""
    client = NobetciEczaneClient(async_get_clientsession(hass))
    coordinator = NobetciEczaneCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    _remove_orphaned_geolocation_entities(hass, entry, coordinator)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


def _remove_orphaned_geolocation_entities(
    hass: HomeAssistant,
    entry: NobetciEczaneConfigEntry,
    coordinator: NobetciEczaneCoordinator,
) -> None:
    """Remove registry entries for pharmacies no longer on the active roster."""
    expected_unique_ids = {
        f"{entry.entry_id}_{pharmacy.registration_id}"
        for pharmacy in coordinator.data.pharmacies
        if pharmacy.latitude is not None and pharmacy.longitude is not None
    }
    registry = er.async_get(hass)
    for registry_entry in er.async_entries_for_config_entry(registry, entry.entry_id):
        if (
            registry_entry.domain == Platform.GEO_LOCATION
            and registry_entry.unique_id not in expected_unique_ids
        ):
            registry.async_remove(registry_entry.entity_id)


async def async_unload_entry(
    hass: HomeAssistant, entry: NobetciEczaneConfigEntry
) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_migrate_entry(
    hass: HomeAssistant, entry: NobetciEczaneConfigEntry
) -> bool:
    """Remove superseded summary entities from releases before 0.2.0."""
    if entry.version < 2:
        registry = er.async_get(hass)
        for suffix in ("pharmacy_count", "nearest_pharmacy"):
            entity_id = registry.async_get_entity_id(
                Platform.SENSOR, DOMAIN, f"{entry.entry_id}_{suffix}"
            )
            if entity_id:
                registry.async_remove(entity_id)
        hass.config_entries.async_update_entry(entry, version=2)
    return True
