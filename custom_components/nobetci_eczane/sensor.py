"""Diagnostic sensor for Nöbetçi Eczane."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_DISTRICT, CONF_PROVINCE, DOMAIN, SOURCE_NAME, SOURCE_URL
from .coordinator import NobetciEczaneCoordinator


async def async_setup_entry(
    hass,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the diagnostic sensor."""
    coordinator: NobetciEczaneCoordinator = entry.runtime_data
    async_add_entities([DutyPharmacyLastCheckSensor(coordinator, entry)])


class DutyPharmacyLastCheckSensor(
    CoordinatorEntity[NobetciEczaneCoordinator], SensorEntity
):
    """Timestamp of the last successful source fetch."""

    _attr_has_entity_name = True
    _attr_translation_key = "last_check"
    _attr_icon = "mdi:cloud-check"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_last_check"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer=SOURCE_NAME,
            model="Nöbetçi Eczane Web Servisi",
            configuration_url=SOURCE_URL,
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def native_value(self):
        return self.coordinator.data.fetched_at

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "integration": DOMAIN,
            "province": self.entry.data[CONF_PROVINCE],
            "district": self.entry.data[CONF_DISTRICT],
            "source": SOURCE_NAME,
            "source_url": SOURCE_URL,
            "pharmacy_count": len(self.coordinator.data.pharmacies),
        }
