"""Config flow for Nöbetçi Eczane."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import NobetciEczaneClient, NobetciEczaneError
from .const import (
    CONF_DISTRICT,
    CONF_PROVINCE,
    CONF_PROVINCE_CODE,
    CONF_RADIUS_KM,
    CONF_UPDATE_INTERVAL_MINUTES,
    DEFAULT_RADIUS_KM,
    DEFAULT_UPDATE_INTERVAL_MINUTES,
    DOMAIN,
    MAX_RADIUS_KM,
    MAX_UPDATE_INTERVAL_MINUTES,
    MIN_RADIUS_KM,
    MIN_UPDATE_INTERVAL_MINUTES,
    PROVINCES,
)


def _province_schema(province_code: str) -> vol.Schema:
    """Build the province selector schema."""
    options = [{"value": code, "label": name} for code, name in PROVINCES.items()]
    return vol.Schema(
        {
            vol.Required(
                CONF_PROVINCE_CODE, default=province_code
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=options,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            )
        }
    )


def _settings_schema(
    districts: list[str],
    district: str | None,
    radius: float,
    interval_minutes: int,
) -> vol.Schema:
    """Build the district, radius and polling settings schema."""
    default_district = district if district in districts else districts[0]
    return vol.Schema(
        {
            vol.Required(
                CONF_DISTRICT, default=default_district
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=districts,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Required(CONF_RADIUS_KM, default=radius): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=MIN_RADIUS_KM,
                    max=MAX_RADIUS_KM,
                    step=1,
                    mode=selector.NumberSelectorMode.BOX,
                    unit_of_measurement="km",
                )
            ),
            vol.Required(
                CONF_UPDATE_INTERVAL_MINUTES, default=interval_minutes
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=MIN_UPDATE_INTERVAL_MINUTES,
                    max=MAX_UPDATE_INTERVAL_MINUTES,
                    step=5,
                    mode=selector.NumberSelectorMode.BOX,
                    unit_of_measurement="min",
                )
            ),
        }
    )


class NobetciEczaneConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the integration setup flow."""

    VERSION = 4

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> "NobetciEczaneOptionsFlow":
        """Return the options flow handler."""
        return NobetciEczaneOptionsFlow()

    def __init__(self) -> None:
        self._province_code = "34"
        self._districts: list[str] = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Select the province."""
        errors: dict[str, str] = {}
        if user_input is not None:
            self._province_code = user_input[CONF_PROVINCE_CODE]
            try:
                client = NobetciEczaneClient(async_get_clientsession(self.hass))
                self._districts = await client.async_get_districts(self._province_code)
            except NobetciEczaneError:
                errors["base"] = "cannot_connect"
            else:
                if self._districts:
                    return await self.async_step_district()
                errors["base"] = "no_districts"

        return self.async_show_form(
            step_id="user",
            data_schema=_province_schema(self._province_code),
            errors=errors,
        )

    async def async_step_district(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Select a district and validate the data source."""
        if user_input is not None:
            district = user_input[CONF_DISTRICT]
            province = PROVINCES[self._province_code]
            await self.async_set_unique_id(
                f"{self._province_code}_{district.casefold()}"
            )
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=f"{district} Nöbetçi Eczaneler",
                data={
                    CONF_PROVINCE_CODE: self._province_code,
                    CONF_PROVINCE: province,
                    CONF_DISTRICT: district,
                },
                options={
                    CONF_PROVINCE_CODE: self._province_code,
                    CONF_PROVINCE: province,
                    CONF_DISTRICT: district,
                    CONF_RADIUS_KM: user_input[CONF_RADIUS_KM],
                    CONF_UPDATE_INTERVAL_MINUTES: user_input[
                        CONF_UPDATE_INTERVAL_MINUTES
                    ],
                },
            )

        return self.async_show_form(
            step_id="district",
            data_schema=_settings_schema(
                self._districts,
                None,
                DEFAULT_RADIUS_KM,
                DEFAULT_UPDATE_INTERVAL_MINUTES,
            ),
        )


class NobetciEczaneOptionsFlow(OptionsFlow):
    """Manage all integration parameters from the integration page."""

    def __init__(self) -> None:
        self._province_code = "34"
        self._districts: list[str] = []

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Select the province and load its districts."""
        errors: dict[str, str] = {}
        if user_input is not None:
            self._province_code = user_input[CONF_PROVINCE_CODE]
            try:
                client = NobetciEczaneClient(async_get_clientsession(self.hass))
                self._districts = await client.async_get_districts(
                    self._province_code
                )
            except NobetciEczaneError:
                errors["base"] = "cannot_connect"
            else:
                if self._districts:
                    return await self.async_step_settings()
                errors["base"] = "no_districts"

        return self.async_show_form(
            step_id="init",
            data_schema=_province_schema(
                self.config_entry.options.get(
                    CONF_PROVINCE_CODE,
                    self.config_entry.data[CONF_PROVINCE_CODE],
                )
            ),
            errors=errors,
        )

    async def async_step_settings(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Edit the district, radius and update interval."""
        if user_input is not None:
            province = PROVINCES[self._province_code]
            district = user_input[CONF_DISTRICT]
            options = {
                CONF_PROVINCE_CODE: self._province_code,
                CONF_PROVINCE: province,
                CONF_DISTRICT: district,
                CONF_RADIUS_KM: user_input[CONF_RADIUS_KM],
                CONF_UPDATE_INTERVAL_MINUTES: user_input[
                    CONF_UPDATE_INTERVAL_MINUTES
                ],
            }
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                title=f"{district} Nöbetçi Eczaneler",
            )
            return self.async_create_entry(title="", data=options)

        current_province_code = self.config_entry.options.get(
            CONF_PROVINCE_CODE,
            self.config_entry.data[CONF_PROVINCE_CODE],
        )
        current_district = (
            self.config_entry.options.get(CONF_DISTRICT)
            if self._province_code == current_province_code
            else None
        )
        return self.async_show_form(
            step_id="settings",
            data_schema=_settings_schema(
                self._districts,
                current_district or self.config_entry.data[CONF_DISTRICT],
                self.config_entry.options.get(CONF_RADIUS_KM, DEFAULT_RADIUS_KM),
                self.config_entry.options.get(
                    CONF_UPDATE_INTERVAL_MINUTES,
                    DEFAULT_UPDATE_INTERVAL_MINUTES,
                ),
            ),
        )
