"""Entity-registry cleanup helpers for duty-pharmacy locations."""

from __future__ import annotations

from collections.abc import Collection

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er


@callback
def remove_orphaned_geolocation_entities(
    hass: HomeAssistant,
    entry: ConfigEntry,
    active_registration_ids: Collection[str],
    *,
    managed_unique_ids: Collection[str] = (),
) -> int:
    """Remove stale registered locations not managed by a live entity object.

    Live entity objects are skipped because their platform removal also clears
    their state. Registry entries left by a prior reload or older release are
    removed directly.
    """
    expected_unique_ids = {
        f"{entry.entry_id}_{registration_id}"
        for registration_id in active_registration_ids
    }
    managed = set(managed_unique_ids)
    registry = er.async_get(hass)
    removed = 0

    for registry_entry in er.async_entries_for_config_entry(
        registry, entry.entry_id
    ):
        if (
            registry_entry.domain == "geo_location"
            and registry_entry.unique_id not in expected_unique_ids
            and registry_entry.unique_id not in managed
        ):
            registry.async_remove(registry_entry.entity_id)
            removed += 1

    return removed
