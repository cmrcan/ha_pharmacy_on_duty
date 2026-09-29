"""Editable province and district settings shown on the integration device."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .api import NobetciEczaneError
from .const import (
    CONF_DISTRICT,
    CONF_PROVINCE,
    CONF_PROVINCE_CODE,
    PROVINCES,
)
from .device import device_info


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up editable province and district selectors."""
    coordinator = entry.runtime_data
    province_code = entry.options.get(
        CONF_PROVINCE_CODE, entry.data[CONF_PROVINCE_CODE]
    )
    try:
        districts = await coordinator.client.async_get_districts(province_code)
    except NobetciEczaneError:
        districts = [coordinator.district]

    async_add_entities(
        [
            DutyPharmacyProvinceSelect(entry, coordinator.client),
            DutyPharmacyDistrictSelect(entry, districts),
        ]
    )


class _DutyPharmacySelect(SelectEntity):
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, entry: ConfigEntry, translation_key: str, icon: str) -> None:
        self._entry = entry
        self._attr_translation_key = translation_key
        self._attr_unique_id = f"{entry.entry_id}_{translation_key}"
        self._attr_icon = icon
        self._attr_device_info = device_info(entry)

    def _update_entry(self, options: dict, district: str) -> None:
        self.hass.config_entries.async_update_entry(
            self._entry,
            title=f"{district} Nöbetçi Eczaneler",
            options=options,
        )


class DutyPharmacyProvinceSelect(_DutyPharmacySelect):
    """Province selector that also resets the district when needed."""

    def __init__(self, entry: ConfigEntry, client) -> None:
        super().__init__(entry, "province", "mdi:map")
        self._client = client
        self._attr_options = list(PROVINCES.values())

    @property
    def current_option(self) -> str:
        return self._entry.options.get(
            CONF_PROVINCE, self._entry.data[CONF_PROVINCE]
        )

    async def async_select_option(self, option: str) -> None:
        province_code = next(
            (code for code, name in PROVINCES.items() if name == option), None
        )
        if province_code is None:
            raise HomeAssistantError(f"Unsupported province: {option}")
        try:
            districts = await self._client.async_get_districts(province_code)
        except NobetciEczaneError as err:
            raise HomeAssistantError(str(err)) from err
        if not districts:
            raise HomeAssistantError("The source returned no districts")

        options = dict(self._entry.options)
        district = options.get(CONF_DISTRICT, self._entry.data[CONF_DISTRICT])
        if district not in districts:
            district = districts[0]
        options.update(
            {
                CONF_PROVINCE_CODE: province_code,
                CONF_PROVINCE: option,
                CONF_DISTRICT: district,
            }
        )
        self._update_entry(options, district)


class DutyPharmacyDistrictSelect(_DutyPharmacySelect):
    """Primary district selector."""

    def __init__(self, entry: ConfigEntry, districts: list[str]) -> None:
        super().__init__(entry, "district", "mdi:map-marker-radius")
        current = entry.options.get(CONF_DISTRICT, entry.data[CONF_DISTRICT])
        self._attr_options = sorted(set([*districts, current]))

    @property
    def current_option(self) -> str:
        return self._entry.options.get(
            CONF_DISTRICT, self._entry.data[CONF_DISTRICT]
        )

    async def async_select_option(self, option: str) -> None:
        if option not in self.options:
            raise HomeAssistantError(f"Unsupported district: {option}")
        options = dict(self._entry.options)
        options[CONF_DISTRICT] = option
        self._update_entry(options, option)
