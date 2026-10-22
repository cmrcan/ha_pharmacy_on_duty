"""Authenticated, on-demand phone lookup for the bundled card."""

from __future__ import annotations

try:
    import probatio as vol
except ImportError:  # Home Assistant releases before the schema-library migration
    import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er

from .api import NobetciEczaneError
from .const import DOMAIN


@callback
def async_register_phone_command(hass: HomeAssistant) -> None:
    """Register one command for all integration entries."""
    websocket_api.async_register_command(hass, async_get_phone)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "nobetci_eczane/phone",
        vol.Required("entity_id"): str,
    }
)
@websocket_api.async_response
async def async_get_phone(hass, connection, msg) -> None:
    """Look up a currently managed entity without exposing source tickets."""
    entity = er.async_get(hass).async_get(msg["entity_id"])
    if entity is None or entity.platform != DOMAIN:
        connection.send_error(msg["id"], "not_found", "Pharmacy was not found")
        return
    # Respect per-user entity permissions, just like the normal HA state API.
    if not connection.user.permissions.check_entity(msg["entity_id"], "read"):
        connection.send_error(msg["id"], "unauthorized", "Entity access denied")
        return
    entry = hass.config_entries.async_get_entry(entity.config_entry_id)
    coordinator = getattr(entry, "runtime_data", None) if entry else None
    if (
        entry is None
        or entry.domain != DOMAIN
        or coordinator is None
        or not coordinator.last_update_success
    ):
        connection.send_error(msg["id"], "unavailable", "Pharmacy data is unavailable")
        return
    pharmacy = next(
        (
            item
            for item in coordinator.data.pharmacies
            if entity.unique_id == f"{entry.entry_id}_{item.registration_id}"
        ),
        None,
    )
    if pharmacy is None:
        connection.send_error(msg["id"], "not_found", "Pharmacy is no longer on duty")
        return
    try:
        phones = await coordinator.client.async_get_phone(
            pharmacy.registration_id,
            hass.config.latitude,
            hass.config.longitude,
            coordinator.radius_km,
        )
    except NobetciEczaneError:
        connection.send_error(
            msg["id"], "phone_unavailable", "Phone could not be loaded. Please retry."
        )
        return
    connection.send_result(msg["id"], {"phones": [f"+90{phone}" for phone in phones]})
