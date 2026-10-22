"""Exercise coordinator filtering, migration and authenticated phone routing with HA doubles."""

from __future__ import annotations

import ast
from datetime import datetime, timezone
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock, patch

import probatio

from test_api import api, load_module, PACKAGE, ROOT, ROW


def module(name, **members):
    result = ModuleType(name)
    result.__dict__.update(members)
    return result


class CoordinatorBase:
    def __class_getitem__(cls, item):
        return cls

    def __init__(self, hass, **kwargs):
        self.hass = hass
        self.update_interval = kwargs["update_interval"]


class UpdateFailed(Exception):
    pass


def websocket_command(schema):
    def decorate(function):
        function._ws_schema = probatio.Schema({probatio.Required("id"): int}).extend(
            schema
        )
        function._ws_command = schema["type"]
        return function

    return decorate


websocket_api = module(
    "homeassistant.components.websocket_api",
    websocket_command=websocket_command,
    async_response=lambda function: function,
    async_register_command=Mock(),
)
registry = module(
    "homeassistant.helpers.entity_registry", async_get=lambda hass: hass.registry
)
ha_modules = {
    "homeassistant": module("homeassistant"),
    "homeassistant.config_entries": module(
        "homeassistant.config_entries", ConfigEntry=object
    ),
    "homeassistant.core": module(
        "homeassistant.core", HomeAssistant=object, callback=lambda f: f
    ),
    "homeassistant.helpers": module("homeassistant.helpers", entity_registry=registry),
    registry.__name__: registry,
    "homeassistant.helpers.update_coordinator": module(
        "homeassistant.helpers.update_coordinator",
        DataUpdateCoordinator=CoordinatorBase,
        UpdateFailed=UpdateFailed,
    ),
    "homeassistant.util": module(
        "homeassistant.util",
        dt=SimpleNamespace(utcnow=lambda: datetime.now(timezone.utc)),
    ),
    "homeassistant.components": module(
        "homeassistant.components", websocket_api=websocket_api
    ),
    websocket_api.__name__: websocket_api,
}
with patch.dict(sys.modules, ha_modules):
    coordinator = load_module(f"{PACKAGE}.coordinator", ROOT / "coordinator.py")
    websocket = load_module(f"{PACKAGE}.websocket", ROOT / "websocket.py")


class CoordinatorTests(unittest.IsolatedAsyncioTestCase):
    async def test_exact_radius_filters_before_rounding_and_keeps_neighboring_districts(
        self,
    ):
        entry = SimpleNamespace(
            options={"radius_km": 10},
            data={"province": "İstanbul", "district": "Çekmeköy"},
        )
        hass = SimpleNamespace(config=SimpleNamespace(latitude=41.03, longitude=29.22))
        rows = [
            api.Pharmacy.from_payload({**ROW, "sicil": n, "il": province})
            for n, province in ((1, "İstanbul"), (2, "İstanbul"), (3, "Yalova"))
        ]
        client = SimpleNamespace(
            async_get_nearby_pharmacies=AsyncMock(return_value=rows)
        )
        instance = coordinator.NobetciEczaneCoordinator(hass, entry, client)
        with patch.object(coordinator, "haversine_km", side_effect=[9.999, 10.001]):
            data = await instance._async_update_data()
        self.assertEqual([p.registration_id for p in data.pharmacies], ["1"])
        self.assertEqual(data.pharmacies[0].district, "Sancaktepe")
        client.async_get_nearby_pharmacies.assert_awaited_once_with(41.03, 29.22, 10)

    async def test_source_errors_do_not_become_empty_success(self):
        entry = SimpleNamespace(
            options={}, data={"province": "İstanbul", "district": "Çekmeköy"}
        )
        hass = SimpleNamespace(config=SimpleNamespace(latitude=41, longitude=29))
        client = SimpleNamespace(
            async_get_nearby_pharmacies=AsyncMock(
                side_effect=api.NobetciEczaneResponseError("offline")
            )
        )
        instance = coordinator.NobetciEczaneCoordinator(hass, entry, client)
        with self.assertRaises(UpdateFailed):
            await instance._async_update_data()


class PhoneRoutingTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.entity = SimpleNamespace(
            platform="nobetci_eczane",
            config_entry_id="entry-1",
            unique_id="entry-1_12009",
        )
        self.client = SimpleNamespace(
            async_get_phone=AsyncMock(return_value=("2165551234",))
        )
        self.coordinator = SimpleNamespace(
            client=self.client,
            radius_km=10,
            last_update_success=True,
            data=SimpleNamespace(pharmacies=[api.Pharmacy.from_payload(ROW)]),
        )
        self.entry = SimpleNamespace(
            domain="nobetci_eczane", entry_id="entry-1", runtime_data=self.coordinator
        )
        self.hass = SimpleNamespace(
            registry=SimpleNamespace(async_get=Mock(return_value=self.entity)),
            config_entries=SimpleNamespace(
                async_get_entry=Mock(return_value=self.entry)
            ),
            config=SimpleNamespace(latitude=41, longitude=29),
        )
        self.connection = SimpleNamespace(
            user=SimpleNamespace(
                permissions=SimpleNamespace(check_entity=Mock(return_value=True))
            ),
            send_error=Mock(),
            send_result=Mock(),
        )
        self.msg = {
            "id": 1,
            "type": "nobetci_eczane/phone",
            "entity_id": "geo_location.eczane",
        }

    async def test_success_returns_numbers_without_tickets(self):
        websocket.async_get_phone._ws_schema(self.msg)
        await websocket.async_get_phone(self.hass, self.connection, self.msg)
        self.connection.send_result.assert_called_once_with(
            1, {"phones": ["+902165551234"]}
        )
        self.client.async_get_phone.assert_awaited_once_with("12009", 41, 29, 10)

    async def test_unmanaged_entity_is_rejected(self):
        self.entity.platform = "other"
        await websocket.async_get_phone(self.hass, self.connection, self.msg)
        self.client.async_get_phone.assert_not_awaited()
        self.assertEqual(self.connection.send_error.call_args.args[1], "not_found")

    async def test_permission_is_checked_before_source_request(self):
        self.connection.user.permissions.check_entity.return_value = False
        await websocket.async_get_phone(self.hass, self.connection, self.msg)
        self.client.async_get_phone.assert_not_awaited()
        self.assertEqual(self.connection.send_error.call_args.args[1], "unauthorized")

    async def test_removed_pharmacy_is_rejected(self):
        self.coordinator.data.pharmacies = []
        await websocket.async_get_phone(self.hass, self.connection, self.msg)
        self.client.async_get_phone.assert_not_awaited()
        self.assertEqual(self.connection.send_error.call_args.args[1], "not_found")

    async def test_source_error_has_safe_user_message(self):
        self.client.async_get_phone.side_effect = api.NobetciEczaneResponseError(
            "secret-ticket"
        )
        await websocket.async_get_phone(self.hass, self.connection, self.msg)
        self.assertNotIn("secret-ticket", str(self.connection.send_error.call_args))
        self.assertEqual(
            self.connection.send_error.call_args.args[1], "phone_unavailable"
        )

    def test_schema_rejects_custom_source_urls_and_missing_entity(self):
        for message in (
            {"id": 1, "type": "nobetci_eczane/phone"},
            {**self.msg, "url": "https://example.org"},
        ):
            with self.assertRaises(probatio.Invalid):
                websocket.async_get_phone._ws_schema(message)


class MigrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_existing_entries_keep_settings_and_cap_only_radius(self):
        # Compile the actual migration function alone to avoid loading a full HA
        # server for this dependency-light suite.
        tree = ast.parse((ROOT / "__init__.py").read_text())
        function = next(
            n
            for n in tree.body
            if isinstance(n, ast.AsyncFunctionDef) and n.name == "async_migrate_entry"
        )
        future = ast.ImportFrom(
            module="__future__", names=[ast.alias(name="annotations")], level=0
        )
        code = ast.fix_missing_locations(
            ast.Module(body=[future, function], type_ignores=[])
        )
        constants = sys.modules[f"{PACKAGE}.const"]
        namespace = {
            key: value for key, value in vars(constants).items() if key.isupper()
        }
        exec(compile(code, str(ROOT / "__init__.py"), "exec"), namespace)
        for before, after in ((10, 10), (100, 12), (3, 3)):
            options = {
                "radius_km": before,
                "update_interval_minutes": 45,
                "district": "Çekmeköy",
            }
            entry = SimpleNamespace(version=4, options=options, data={})
            update = Mock()
            hass = SimpleNamespace(
                config_entries=SimpleNamespace(async_update_entry=update)
            )
            self.assertTrue(await namespace["async_migrate_entry"](hass, entry))
            changed = update.call_args.kwargs
            self.assertEqual(changed["version"], 5)
            self.assertEqual(changed["options"], {**options, "radius_km": after})
