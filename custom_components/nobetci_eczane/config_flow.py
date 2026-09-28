"""Config flow for Nöbetçi Eczane."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import NobetciEczaneClient, NobetciEczaneError
from .const import CONF_DISTRICT, CONF_PROVINCE, CONF_PROVINCE_CODE, DOMAIN, PROVINCES


class NobetciEczaneConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the integration setup flow."""

    VERSION = 2

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

        options = [
            {"value": code, "label": name} for code, name in PROVINCES.items()
        ]
        schema = vol.Schema(
            {
                vol.Required(CONF_PROVINCE_CODE, default=self._province_code): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=options,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                )
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_district(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Select a district and validate the data source."""
        errors: dict[str, str] = {}
        if user_input is not None:
            district = user_input[CONF_DISTRICT]
            try:
                client = NobetciEczaneClient(async_get_clientsession(self.hass))
                await client.async_get_pharmacies(district)
            except NobetciEczaneError:
                errors["base"] = "cannot_connect"
            else:
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
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_DISTRICT): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=self._districts,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                )
            }
        )
        return self.async_show_form(
            step_id="district", data_schema=schema, errors=errors
        )
