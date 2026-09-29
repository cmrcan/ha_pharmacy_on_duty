"""Dependency-light tests for stale geolocation registry cleanup."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest


ROOT = Path(__file__).parents[1] / "custom_components" / "nobetci_eczane"
PACKAGE = "custom_components.nobetci_eczane"

for package_name, package_path in (
    ("custom_components", ROOT.parent),
    (PACKAGE, ROOT),
    ("homeassistant", ROOT),
    ("homeassistant.helpers", ROOT),
):
    package = ModuleType(package_name)
    package.__path__ = [str(package_path)]
    sys.modules[package_name] = package

config_entries = ModuleType("homeassistant.config_entries")
config_entries.ConfigEntry = object
sys.modules[config_entries.__name__] = config_entries

core = ModuleType("homeassistant.core")
core.HomeAssistant = object
core.callback = lambda function: function
sys.modules[core.__name__] = core

entity_registry = ModuleType("homeassistant.helpers.entity_registry")
entity_registry.async_get = lambda hass: hass.registry
entity_registry.async_entries_for_config_entry = (
    lambda registry, entry_id: [
        item for item in registry.entries if item.config_entry_id == entry_id
    ]
)
sys.modules[entity_registry.__name__] = entity_registry

spec = spec_from_file_location(f"{PACKAGE}.cleanup", ROOT / "cleanup.py")
cleanup = module_from_spec(spec)
sys.modules[spec.name] = cleanup
assert spec.loader is not None
spec.loader.exec_module(cleanup)


class FakeRegistry:
    def __init__(self, entries):
        self.entries = entries
        self.removed: list[str] = []

    def async_remove(self, entity_id: str) -> None:
        self.removed.append(entity_id)


class CleanupTests(unittest.TestCase):
    def test_only_unmanaged_stale_locations_are_removed(self):
        entry = SimpleNamespace(entry_id="entry-1")
        entries = [
            SimpleNamespace(
                config_entry_id="entry-1",
                domain="geo_location",
                unique_id="entry-1_active",
                entity_id="geo_location.active",
            ),
            SimpleNamespace(
                config_entry_id="entry-1",
                domain="geo_location",
                unique_id="entry-1_runtime_stale",
                entity_id="geo_location.runtime_stale",
            ),
            SimpleNamespace(
                config_entry_id="entry-1",
                domain="geo_location",
                unique_id="entry-1_old",
                entity_id="geo_location.old",
            ),
            SimpleNamespace(
                config_entry_id="entry-1",
                domain="sensor",
                unique_id="entry-1_last_check",
                entity_id="sensor.last_check",
            ),
        ]
        hass = SimpleNamespace(registry=FakeRegistry(entries))

        removed = cleanup.remove_orphaned_geolocation_entities(
            hass,
            entry,
            {"active"},
            managed_unique_ids={"entry-1_active", "entry-1_runtime_stale"},
        )

        self.assertEqual(removed, 1)
        self.assertEqual(hass.registry.removed, ["geo_location.old"])


if __name__ == "__main__":
    unittest.main()
