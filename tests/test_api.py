"""Small dependency-light tests for parsing the official source."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys
from types import ModuleType
import unittest


ROOT = Path(__file__).parents[1] / "custom_components" / "nobetci_eczane"
PACKAGE = "custom_components.nobetci_eczane"

for package_name, package_path in (
    ("custom_components", ROOT.parent),
    (PACKAGE, ROOT),
):
    package = ModuleType(package_name)
    package.__path__ = [str(package_path)]
    sys.modules[package_name] = package


def load_module(name: str, path: Path):
    spec = spec_from_file_location(name, path)
    module = module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


load_module(f"{PACKAGE}.const", ROOT / "const.py")
api = load_module(f"{PACKAGE}.api", ROOT / "api.py")

Pharmacy = api.Pharmacy
extract_token = api.extract_token
html_to_text = api.html_to_text
normalize_phone = api.normalize_phone


class ParserTests(unittest.TestCase):
    def test_extract_token(self):
        page = '<input type="hidden" name="h" id="h" value="rotating-token"/>'
        self.assertEqual(extract_token(page), "rotating-token")

    def test_html_to_text(self):
        fragment = "<br><strong>Tarif:</strong> Metro yanı\r\nSağlık ocağı karşısı"
        self.assertEqual(
            html_to_text(fragment, "Tarif"), "Metro yanı\nSağlık ocağı karşısı"
        )
        self.assertEqual(
            html_to_text("<strong>Adres:</strong> Cadde 1, , Çekmeköy", "Adres"),
            "Cadde 1, Çekmeköy",
        )

    def test_normalize_phone(self):
        self.assertEqual(normalize_phone("0 (216) 641-91-34"), "2166419134")
        self.assertEqual(normalize_phone("+90 216 641 91 34"), "2166419134")

    def test_pharmacy_payload(self):
        pharmacy = Pharmacy.from_payload(
            {
                "sicil": 27538,
                "eczane_ad": "ÇEKMEKÖY YAŞAM ECZANESİ",
                "eczane_tel": "2166419134",
                "tarif": "<strong>Tarif:</strong> Metro yanı",
                "adres": "<strong>Adres:</strong> Mimar Sinan Caddesi, 22C",
                "lat": "41.031282",
                "lng": "29.182904",
                "nobet_bitis": None,
            }
        )
        self.assertEqual(pharmacy.registration_id, "27538")
        self.assertEqual(pharmacy.address, "Mimar Sinan Caddesi, 22C")
        self.assertEqual(pharmacy.directions, "Metro yanı")
        self.assertAlmostEqual(pharmacy.latitude, 41.031282)


if __name__ == "__main__":
    unittest.main()
