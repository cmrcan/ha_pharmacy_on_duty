"""Verify the radius UI choices and direct Home Assistant setting updates."""

from __future__ import annotations

import ast
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import probatio

from test_api import load_module, PACKAGE, ROOT
from test_runtime import ha_modules, module

constants = sys.modules[f"{PACKAGE}.const"]


class HAError(Exception):
    pass


class NumberEntity:
    @property
    def options(self):
        return self._attr_options


with patch.dict(
    sys.modules,
    {
        **ha_modules,
        "homeassistant.components.number": module(
            "homeassistant.components.number",
            NumberEntity=NumberEntity,
            NumberMode=SimpleNamespace(BOX="box", SLIDER="slider"),
        ),
        "homeassistant.const": module(
            "homeassistant.const",
            EntityCategory=SimpleNamespace(DIAGNOSTIC="diagnostic"),
            UnitOfLength=SimpleNamespace(KILOMETERS="km"),
            UnitOfTime=SimpleNamespace(MINUTES="min"),
        ),
        "homeassistant.exceptions": module(
            "homeassistant.exceptions", HomeAssistantError=HAError
        ),
        "homeassistant.helpers.entity_platform": module(
            "homeassistant.helpers.entity_platform",
            AddConfigEntryEntitiesCallback=object,
        ),
        f"{PACKAGE}.device": module(f"{PACKAGE}.device", device_info=lambda entry: {}),
    },
):
    number = load_module(f"{PACKAGE}.number", ROOT / "number.py")


class RadiusSettingTests(unittest.IsolatedAsyncioTestCase):
    def make_entity(self):
        entry = SimpleNamespace(
            entry_id="entry-1", options={"radius_km": 12, "update_interval_minutes": 30}
        )
        entity = number.DutyPharmacySettingNumber(
            entry, "radius_km", "radius_km", 12, 3, 12, 3, "km", "mdi:radius-outline"
        )
        entity.hass = SimpleNamespace(
            config_entries=SimpleNamespace(async_update_entry=Mock())
        )
        return entity

    async def test_device_radius_uses_slider_with_three_km_steps(self):
        entry = SimpleNamespace(entry_id="entry-1", options={})
        entities = []
        await number.async_setup_entry(None, entry, entities.extend)
        radius = entities[0]
        self.assertEqual(
            (
                radius._attr_native_min_value,
                radius._attr_native_max_value,
                radius._attr_native_step,
            ),
            (3, 12, 3),
        )
        self.assertEqual(radius._attr_mode, "slider")
        self.assertEqual(radius._attr_unique_id, "entry-1_radius_km")
        self.assertEqual(entities[1]._attr_mode, "box")

    async def test_all_presets_persist_without_changing_other_settings(self):
        for value in (3, 6, 9, 12):
            entity = self.make_entity()
            await entity.async_set_native_value(value)
            self.assertEqual(
                entity.hass.config_entries.async_update_entry.call_args.kwargs[
                    "options"
                ],
                {"radius_km": value, "update_interval_minutes": 30},
            )

    async def test_direct_service_calls_cannot_store_unsupported_radii(self):
        for value in (1, 4, 5, 10, 13, float("nan")):
            entity = self.make_entity()
            with self.assertRaises(HAError):
                await entity.async_set_native_value(value)
            entity.hass.config_entries.async_update_entry.assert_not_called()

    def test_config_form_exposes_exact_four_choices_and_valid_legacy_default(self):
        class Select:
            def __init__(self, config):
                self.config = config

            def __call__(self, value):
                if value not in [
                    item["value"] if isinstance(item, dict) else item
                    for item in self.config["options"]
                ]:
                    raise probatio.Invalid("Unsupported option")
                return value

        selector = SimpleNamespace(
            SelectSelector=Select,
            SelectSelectorConfig=dict,
            SelectSelectorMode=SimpleNamespace(DROPDOWN="dropdown"),
            NumberSelector=lambda config: lambda value: value,
            NumberSelectorConfig=dict,
            NumberSelectorMode=SimpleNamespace(BOX="box"),
        )
        tree = ast.parse((ROOT / "config_flow.py").read_text())
        function = next(
            n
            for n in tree.body
            if isinstance(n, ast.FunctionDef) and n.name == "_settings_schema"
        )
        future = ast.ImportFrom(
            module="__future__", names=[ast.alias(name="annotations")], level=0
        )
        code = ast.fix_missing_locations(
            ast.Module(body=[future, function], type_ignores=[])
        )
        namespace = {**vars(constants), "vol": probatio, "selector": selector}
        exec(compile(code, str(ROOT / "config_flow.py"), "exec"), namespace)
        schema = namespace["_settings_schema"](["Çekmeköy"], None, 10, 30)
        config = schema.schema["radius_km"].config
        self.assertEqual(
            config["options"],
            [{"value": str(v), "label": f"{v} km"} for v in (3, 6, 9, 12)],
        )
        validated = schema({"district": "Çekmeköy", "update_interval_minutes": 30})
        self.assertEqual(validated["radius_km"], "12")
        with self.assertRaises(probatio.Invalid):
            schema(
                {
                    "district": "Çekmeköy",
                    "radius_km": "5",
                    "update_interval_minutes": 30,
                }
            )
