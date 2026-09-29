"""Nöbetçi Eczane integration."""

from __future__ import annotations

from pathlib import Path
import logging
from typing import TypeAlias

from homeassistant.components import frontend
from homeassistant.components.http import StaticPathConfig
from homeassistant.components.lovelace.const import LOVELACE_DATA, MODE_STORAGE
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import NobetciEczaneClient
from .const import (
    CARD_URL,
    CARD_VERSION,
    CONF_DISTRICT,
    CONF_PROVINCE,
    CONF_PROVINCE_CODE,
    CONF_RADIUS_KM,
    CONF_UPDATE_INTERVAL_MINUTES,
    DEFAULT_RADIUS_KM,
    DEFAULT_UPDATE_INTERVAL_MINUTES,
    DOMAIN,
    PHARMACY_MARKER_URL,
)
from .cleanup import remove_orphaned_geolocation_entities
from .coordinator import NobetciEczaneCoordinator

NobetciEczaneConfigEntry: TypeAlias = ConfigEntry[NobetciEczaneCoordinator]

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [
    Platform.GEO_LOCATION,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up shared frontend resources."""
    static_dir = Path(__file__).parent / "static"
    await hass.http.async_register_static_paths(
        [
            StaticPathConfig(
                CARD_URL,
                str(static_dir / "nobetci-eczane-card.js"),
                cache_headers=True,
            ),
            StaticPathConfig(
                PHARMACY_MARKER_URL,
                str(static_dir / "pharmacy-marker.svg"),
                cache_headers=True,
            ),
        ]
    )
    await _async_register_card_resource(hass)
    return True


async def _async_register_card_resource(hass: HomeAssistant) -> None:
    """Register or update the bundled Lovelace card resource."""
    resource_url = f"{CARD_URL}?v={CARD_VERSION}"
    lovelace = hass.data.get(LOVELACE_DATA)
    if lovelace is None:
        _LOGGER.warning("Lovelace is unavailable; custom card was not registered")
        return

    try:
        if lovelace.resource_mode != MODE_STORAGE:
            frontend.add_extra_js_url(hass, resource_url)
            return

        resources = lovelace.resources
        # Force storage to load before async_items(); otherwise existing resources
        # can be treated as an empty list during early startup.
        await resources.async_get_info()
        for item in resources.async_items():
            if item.get("url", "").split("?", 1)[0] != CARD_URL:
                continue
            if item["url"] != resource_url or item.get("res_type") != "module":
                await resources.async_update_item(
                    item["id"], {"res_type": "module", "url": resource_url}
                )
            return
        await resources.async_create_item(
            {"res_type": "module", "url": resource_url}
        )
    except Exception:  # noqa: BLE001 - card failure must not block the integration
        _LOGGER.exception("Unable to register the Nöbetçi Eczane Lovelace card")


async def async_setup_entry(
    hass: HomeAssistant, entry: NobetciEczaneConfigEntry
) -> bool:
    """Set up Nöbetçi Eczane from a config entry."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    client = domain_data.get("client")
    if client is None:
        client = domain_data["client"] = NobetciEczaneClient(
            async_get_clientsession(hass)
        )
    coordinator = NobetciEczaneCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    remove_orphaned_geolocation_entities(
        hass,
        entry,
        {
            pharmacy.registration_id
            for pharmacy in coordinator.data.pharmacies
            if pharmacy.latitude is not None and pharmacy.longitude is not None
        },
    )
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def _async_update_listener(
    hass: HomeAssistant, entry: NobetciEczaneConfigEntry
) -> None:
    """Reload the integration after its editable parameters change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(
    hass: HomeAssistant, entry: NobetciEczaneConfigEntry
) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_migrate_entry(
    hass: HomeAssistant, entry: NobetciEczaneConfigEntry
) -> bool:
    """Remove superseded summary entities from releases before 0.2.0."""
    options = dict(entry.options)
    if entry.version < 2:
        registry = er.async_get(hass)
        for suffix in ("pharmacy_count", "nearest_pharmacy"):
            entity_id = registry.async_get_entity_id(
                Platform.SENSOR, DOMAIN, f"{entry.entry_id}_{suffix}"
            )
            if entity_id:
                registry.async_remove(entity_id)
    if entry.version < 3:
        options.setdefault(CONF_RADIUS_KM, DEFAULT_RADIUS_KM)
        options.setdefault(
            CONF_UPDATE_INTERVAL_MINUTES, DEFAULT_UPDATE_INTERVAL_MINUTES
        )
    if entry.version < 4:
        options.setdefault(CONF_PROVINCE_CODE, entry.data[CONF_PROVINCE_CODE])
        options.setdefault(CONF_PROVINCE, entry.data[CONF_PROVINCE])
        options.setdefault(CONF_DISTRICT, entry.data[CONF_DISTRICT])
        hass.config_entries.async_update_entry(entry, version=4, options=options)
    return True
