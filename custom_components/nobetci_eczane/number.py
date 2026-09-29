"""Editable numeric settings shown on the integration device."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, UnitOfLength, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import (
    CONF_RADIUS_KM,
    CONF_UPDATE_INTERVAL_MINUTES,
    DEFAULT_RADIUS_KM,
    DEFAULT_UPDATE_INTERVAL_MINUTES,
    MAX_RADIUS_KM,
    MAX_UPDATE_INTERVAL_MINUTES,
    MIN_RADIUS_KM,
    MIN_UPDATE_INTERVAL_MINUTES,
)
from .device import device_info


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up editable radius and polling interval controls."""
    async_add_entities(
        [
            DutyPharmacySettingNumber(
                entry,
                CONF_RADIUS_KM,
                "radius_km",
                DEFAULT_RADIUS_KM,
                MIN_RADIUS_KM,
                MAX_RADIUS_KM,
                1,
                UnitOfLength.KILOMETERS,
                "mdi:radius-outline",
            ),
            DutyPharmacySettingNumber(
                entry,
                CONF_UPDATE_INTERVAL_MINUTES,
                "update_interval",
                DEFAULT_UPDATE_INTERVAL_MINUTES,
                MIN_UPDATE_INTERVAL_MINUTES,
                MAX_UPDATE_INTERVAL_MINUTES,
                5,
                UnitOfTime.MINUTES,
                "mdi:update",
            ),
        ]
    )


class DutyPharmacySettingNumber(NumberEntity):
    """A config-entry option exposed as an editable diagnostic entity."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_mode = NumberMode.BOX

    def __init__(
        self,
        entry: ConfigEntry,
        option_key: str,
        translation_key: str,
        default: float,
        minimum: float,
        maximum: float,
        step: float,
        unit: str,
        icon: str,
    ) -> None:
        self._entry = entry
        self._option_key = option_key
        self._default = default
        self._attr_translation_key = translation_key
        self._attr_unique_id = f"{entry.entry_id}_{option_key}"
        self._attr_native_min_value = minimum
        self._attr_native_max_value = maximum
        self._attr_native_step = step
        self._attr_native_unit_of_measurement = unit
        self._attr_icon = icon
        self._attr_device_info = device_info(entry)

    @property
    def native_value(self) -> float:
        """Return the current option value."""
        return float(self._entry.options.get(self._option_key, self._default))

    async def async_set_native_value(self, value: float) -> None:
        """Persist a new option value; the config-entry listener reloads it."""
        options = dict(self._entry.options)
        numeric_value = float(value)
        options[self._option_key] = (
            int(numeric_value) if numeric_value.is_integer() else numeric_value
        )
        self.hass.config_entries.async_update_entry(self._entry, options=options)
