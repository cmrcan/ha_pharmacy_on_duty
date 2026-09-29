"""Geolocation entities for active duty pharmacies."""

from __future__ import annotations

import logging
from typing import Any, override

from homeassistant.components.geo_location import GeolocationEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfLength
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import Pharmacy
from .cleanup import remove_orphaned_geolocation_entities
from .const import (
    DOMAIN,
    CARD_VERSION,
    PHARMACY_MARKER_URL,
    SOURCE_NAME,
    SOURCE_URL,
)
from .coordinator import NobetciEczaneCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Create and remove geolocation entities as the duty roster changes."""
    coordinator: NobetciEczaneCoordinator = entry.runtime_data
    entities: dict[str, DutyPharmacyGeolocationEntity] = {}

    @callback
    def sync_entities() -> None:
        current_ids = {
            pharmacy.registration_id
            for pharmacy in coordinator.data.pharmacies
            if pharmacy.latitude is not None and pharmacy.longitude is not None
        }

        removed_registry_entries = remove_orphaned_geolocation_entities(
            hass,
            entry,
            current_ids,
            managed_unique_ids={entity.unique_id for entity in entities.values()},
        )
        if removed_registry_entries:
            _LOGGER.debug(
                "Removed %s stale duty-pharmacy registry entries",
                removed_registry_entries,
            )

        new_entities: list[DutyPharmacyGeolocationEntity] = []
        for external_id in current_ids - entities.keys():
            entity = DutyPharmacyGeolocationEntity(coordinator, entry, external_id)
            entities[external_id] = entity
            new_entities.append(entity)
        if new_entities:
            _LOGGER.debug("Adding %s duty-pharmacy locations", len(new_entities))
            async_add_entities(new_entities)

        for external_id in tuple(entities.keys() - current_ids):
            entity = entities.pop(external_id)
            _LOGGER.debug("Removing expired duty-pharmacy location %s", external_id)
            hass.async_create_task(entity.async_remove(force_remove=True))

    entry.async_on_unload(coordinator.async_add_listener(sync_entities))
    sync_entities()


class DutyPharmacyGeolocationEntity(
    CoordinatorEntity[NobetciEczaneCoordinator], GeolocationEvent
):
    """An active duty pharmacy represented as a geolocation event."""

    _attr_should_poll = False
    _attr_source = DOMAIN
    _attr_unit_of_measurement = UnitOfLength.KILOMETERS
    _attr_icon = "mdi:pharmacy"
    _attr_entity_picture = f"{PHARMACY_MARKER_URL}?v={CARD_VERSION}"

    def __init__(
        self,
        coordinator: NobetciEczaneCoordinator,
        entry: ConfigEntry,
        external_id: str,
    ) -> None:
        super().__init__(coordinator)
        self.entry = entry
        self.external_id = external_id
        self._attr_unique_id = f"{entry.entry_id}_{external_id}"
        self._pharmacy: Pharmacy | None = None
        self._update_from_coordinator()

    def _update_from_coordinator(self) -> None:
        pharmacy = next(
            (
                item
                for item in self.coordinator.data.pharmacies
                if item.registration_id == self.external_id
            ),
            None,
        )
        if pharmacy is None:
            return
        self._pharmacy = pharmacy
        self._attr_name = pharmacy.name
        self._attr_distance = pharmacy.distance_km
        self._attr_latitude = pharmacy.latitude
        self._attr_longitude = pharmacy.longitude

    @callback
    @override
    def _handle_coordinator_update(self) -> None:
        """Refresh attributes before writing the new state."""
        self._update_from_coordinator()
        super()._handle_coordinator_update()

    @property
    @override
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose contact and duty information."""
        pharmacy = self._pharmacy
        if pharmacy is None:
            return {}
        phone = f"0{pharmacy.phone}" if len(pharmacy.phone) == 10 else pharmacy.phone
        phone_e164 = f"+90{pharmacy.phone}" if len(pharmacy.phone) == 10 else None
        return {
            "external_id": self.external_id,
            "integration": DOMAIN,
            "province": pharmacy.province or self.coordinator.province,
            "district": pharmacy.district,
            "configured_district": self.coordinator.district,
            "phone": phone,
            "phone_e164": phone_e164,
            "address": pharmacy.address,
            "directions": pharmacy.directions,
            "neighborhood": pharmacy.neighborhood,
            "subdistrict": pharmacy.subdistrict,
            "postal_code": pharmacy.postal_code,
            "duty_ends": pharmacy.duty_ends,
            "radius_km": self.coordinator.radius_km,
            "fetched_at": self.coordinator.data.fetched_at.isoformat(),
            "update_interval_minutes": int(
                self.coordinator.update_interval.total_seconds() / 60
            ),
            "data_source": SOURCE_NAME,
            "source_url": SOURCE_URL,
        }
