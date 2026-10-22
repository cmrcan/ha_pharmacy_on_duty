"""Small dependency-light tests for parsing the official source."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys
from types import ModuleType
import unittest
import asyncio
import json
from http.cookies import SimpleCookie
from unittest.mock import AsyncMock, patch

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
turkish_title = api.turkish_title


class ParserTests(unittest.TestCase):
    def test_extract_token(self):
        page = boot_page()
        self.assertEqual(extract_token(page), "rotating-token")

    def test_rejects_missing_boot_and_untrusted_gate(self):
        for page in ("<html></html>", boot_page(gate="https://example.org/api/")):
            with self.assertRaises(api.NobetciEczaneResponseError):
                extract_token(page)

    def test_supported_radius_only_accepts_exact_presets(self):
        for value in (3, 6, 9, 12):
            self.assertEqual(api.request_radius(value), value)
        for invalid in (0, 1, 4, 5, 7, 10, 11, 13, 100, float("nan"), float("inf")):
            with self.assertRaises(api.NobetciEczaneResponseError):
                api.request_radius(invalid)

    def test_new_nearby_payload(self):
        pharmacy = Pharmacy.from_payload(ROW)
        self.assertEqual(pharmacy.name, "Eczane Çınar")
        self.assertEqual(pharmacy.duty_ends, "2026-10-23T09:00:00+03:00")
        self.assertEqual(pharmacy.phone, "")
        self.assertEqual(pharmacy.phone_count, 1)
        self.assertNotIn("ticket-1", repr(pharmacy))

    def test_invalid_coordinates_are_not_mapped(self):
        for lat, lng in (("nan", "29"), ("91", "29"), ("41", "181"), ("41", "inf")):
            pharmacy = Pharmacy.from_payload({**ROW, "lat": lat, "lng": lng})
            self.assertTrue(pharmacy.latitude is None or pharmacy.longitude is None)

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

    def test_turkish_title(self):
        self.assertEqual(turkish_title("EBRU ECZANESİ"), "Ebru Eczanesi")
        self.assertEqual(turkish_title("IŞIK ECZANESİ"), "Işık Eczanesi")
        self.assertEqual(turkish_title("İPEK-ŞİFA ECZANESİ"), "İpek-Şifa Eczanesi")

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
        self.assertEqual(pharmacy.name, "Çekmeköy Yaşam Eczanesi")
        self.assertEqual(pharmacy.address, "Mimar Sinan Caddesi, 22C")
        self.assertEqual(pharmacy.directions, "Metro yanı")
        self.assertAlmostEqual(pharmacy.latitude, 41.031282)

    def test_marker_payload_includes_location_and_builds_address(self):
        pharmacy = Pharmacy.from_payload(
            {
                "sicil": "12345",
                "eczane_ad": "SINIR ECZANESİ",
                "eczane_tel": "0 (216) 555 12 34",
                "il": "İstanbul",
                "ilce": "Üsküdar",
                "mahalle": "Kısıklı Mahallesi",
                "cadde_sokak": "Alemdar Caddesi",
                "bina_kapi": "No: 8",
                "semt": "Kısıklı",
                "posta_kodu": "34692",
                "lat": "41.025",
                "lng": "29.075",
            }
        )
        self.assertEqual(pharmacy.phone, "2165551234")
        self.assertEqual(pharmacy.province, "İstanbul")
        self.assertEqual(pharmacy.district, "Üsküdar")
        self.assertEqual(pharmacy.neighborhood, "Kısıklı Mahallesi")
        self.assertEqual(pharmacy.postal_code, "34692")
        self.assertEqual(
            pharmacy.address,
            "Kısıklı Mahallesi, Alemdar Caddesi No: 8, Kısıklı",
        )


def boot_page(token="rotating-token", gate="/api/nobetci-eczane-web/"):
    return (
        '<script type="application/json" id="boot">'
        + json.dumps(
            {
                "token": token,
                "gateUrl": gate,
                "districts": [
                    {"ilceId": 40, "ilceAd": "Çekmeköy", "ilId": 34},
                    {"ilceId": 32, "ilceAd": "Yalova", "ilId": 77},
                ],
            }
        )
        + "</script>"
    )


ROW = {
    "sicil": 12009,
    "ad": "ECZANE ÇINAR",
    "il": "İstanbul",
    "ilce": "Sancaktepe",
    "ilceId": 41,
    "adres": "Atatürk Mahallesi, Yüce Sokak, 12A",
    "lat": 41.011175,
    "lng": 29.225385,
    "dutyEndsAt": "2026-10-23T09:00:00+03:00",
    "regionId": 107,
    "phones": 1,
    "phoneTicket": "ticket-1",
}


class Response:
    def __init__(self, payload, status=200, cookie=None):
        self.body = payload if isinstance(payload, str) else json.dumps(payload)
        self.status = status
        self.cookies = SimpleCookie()
        if cookie:
            self.cookies["PHPSESSID"] = cookie

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    def raise_for_status(self):
        if self.status >= 400:
            raise AssertionError("Unexpected bootstrap failure")

    async def text(self):
        return self.body


class Session:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []

    def request(self, method, url, **kwargs):
        # Copy mutable cookies/headers to verify their value at request time.
        kwargs = {k: dict(v) if isinstance(v, dict) else v for k, v in kwargs.items()}
        self.calls.append((method, url, kwargs))
        return self.responses.pop(0)

    def get(self, url, **kwargs):
        return self.request("GET", url, **kwargs)


def nearby(*rows):
    return Response({"success": True, "data": list(rows)})


def failure(code, status=403):
    return Response(
        {"success": False, "error": {"code": code, "message": code}}, status
    )


class ClientTests(unittest.IsolatedAsyncioTestCase):
    async def test_json_contract_cookies_and_shared_cache(self):
        session = Session(Response(boot_page(), cookie="private-session"), nearby(ROW))
        client = api.NobetciEczaneClient(session)
        first, second = await asyncio.gather(
            client.async_get_nearby_pharmacies(41.03, 29.22, 12),
            client.async_get_nearby_pharmacies(41.03, 29.22, 12),
        )
        self.assertEqual(first, second)
        self.assertEqual(len(session.calls), 2)
        method, url, options = session.calls[1]
        self.assertEqual((method, url), ("POST", api.API_URL))
        self.assertEqual(options["params"], {"action": "nearby"})
        self.assertEqual(options["json"], {"lat": 41.03, "lng": 29.22, "radiusKm": 12})
        self.assertEqual(options["headers"]["X-Web-Token"], "rotating-token")
        self.assertEqual(options["cookies"]["PHPSESSID"], "private-session")

    async def test_cache_separates_location_and_query_radius(self):
        session = Session(Response(boot_page()), nearby(ROW), nearby(), nearby())
        client = api.NobetciEczaneClient(session)
        await client.async_get_nearby_pharmacies(41, 29, 3)
        await client.async_get_nearby_pharmacies(41, 29, 6)
        await client.async_get_nearby_pharmacies(41.1, 29, 3)
        self.assertEqual(len(session.calls), 4)

    async def test_districts_reuse_boot_data_and_filter_province(self):
        session = Session(Response(boot_page()))
        client = api.NobetciEczaneClient(session)
        self.assertEqual(await client.async_get_districts("34"), ["Çekmeköy"])
        self.assertEqual(await client.async_get_districts("77"), ["Yalova"])
        self.assertEqual(len(session.calls), 1)

    async def test_refreshes_rejected_token_once(self):
        session = Session(
            Response(boot_page()),
            failure("token", 401),
            Response(boot_page("new-token")),
            nearby(ROW),
        )
        client = api.NobetciEczaneClient(session)
        self.assertEqual(len(await client.async_get_nearby_pharmacies(41, 29, 3)), 1)
        self.assertEqual(session.calls[-1][2]["headers"]["X-Web-Token"], "new-token")

    async def test_repeated_token_rejection_does_not_loop(self):
        session = Session(
            Response(boot_page()),
            failure("token", 401),
            Response(boot_page("new-token")),
            failure("token", 401),
        )
        client = api.NobetciEczaneClient(session)
        with self.assertRaises(api.NobetciEczaneResponseError):
            await client.async_get_nearby_pharmacies(41, 29, 3)
        self.assertEqual(len(session.calls), 4)

    async def test_rate_limit_and_malformed_data_do_not_look_like_empty_results(self):
        for response in (
            failure("rate_limited", 429),
            Response("<html>offline</html>"),
            Response({"success": True, "data": {}}),
            nearby({"lat": 41}),
        ):
            session = Session(Response(boot_page()), response)
            client = api.NobetciEczaneClient(session)
            with self.assertRaises(api.NobetciEczaneResponseError):
                await client.async_get_nearby_pharmacies(41, 29, 3)
            self.assertEqual(len(session.calls), 2)

    async def test_phone_is_requested_only_on_demand_and_cached(self):
        session = Session(
            Response(boot_page()),
            nearby(ROW),
            Response({"success": True, "data": {"tel": "02165551234", "tel2": ""}}),
        )
        client = api.NobetciEczaneClient(session)
        await client.async_get_nearby_pharmacies(41, 29, 3)
        self.assertEqual(len(session.calls), 2)
        for _ in range(2):
            self.assertEqual(
                await client.async_get_phone("12009", 41, 29, 3), ("2165551234",)
            )
        self.assertEqual(len(session.calls), 3)
        self.assertEqual(
            session.calls[-1][2]["json"],
            {"regionId": 107, "sicil": "12009", "ticket": "ticket-1"},
        )

    async def test_phone_stale_ticket_refreshes_list_once(self):
        session = Session(
            Response(boot_page()),
            nearby(ROW),
            failure("forbidden"),
            nearby({**ROW, "phoneTicket": "ticket-2"}),
            Response({"success": True, "data": {"tel": "02165551234"}}),
        )
        client = api.NobetciEczaneClient(session)
        self.assertEqual(
            await client.async_get_phone("12009", 41, 29, 3), ("2165551234",)
        )
        self.assertEqual(session.calls[-1][2]["json"]["ticket"], "ticket-2")

    async def test_phone_too_fast_uses_one_delayed_retry(self):
        session = Session(
            Response(boot_page()),
            nearby(ROW),
            failure("too_fast"),
            Response({"success": True, "data": {"tel": "02165551234"}}),
        )
        client = api.NobetciEczaneClient(session)
        with patch.object(api.asyncio, "sleep", new_callable=AsyncMock) as sleep:
            await client.async_get_phone("12009", 41, 29, 3)
            sleep.assert_awaited_once_with(2.1)

    async def test_missing_pharmacy_never_requests_phone(self):
        session = Session(Response(boot_page()), nearby())
        client = api.NobetciEczaneClient(session)
        with self.assertRaises(api.NobetciEczaneResponseError):
            await client.async_get_phone("12009", 41, 29, 3)
        self.assertEqual(len(session.calls), 2)


if __name__ == "__main__":
    unittest.main()
