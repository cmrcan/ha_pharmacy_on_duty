"""Client for the İstanbul Eczacı Odası duty-pharmacy service."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from html import unescape
from html.parser import HTMLParser
import json
from math import isfinite
import re
from time import monotonic
from typing import Any
from urllib.parse import urlsplit

from aiohttp import ClientError, ClientSession

from .const import RADIUS_PRESETS_KM, SOURCE_URL

ORIGIN = "https://www.istanbuleczaciodasi.org.tr"
API_URL = f"{ORIGIN}/api/nobetci-eczane-web/"
RADIUS_PRESETS = RADIUS_PRESETS_KM
USER_AGENT = (
    "HomeAssistant-NobetciEczane/0.6.1 "
    "(+https://github.com/cmrcan/HA_Pharmacy_on_Duty)"
)
CACHE_TTL_SECONDS = 60


class NobetciEczaneError(Exception):
    """Base exception for the integration."""


class NobetciEczaneConnectionError(NobetciEczaneError):
    """Raised when the source cannot be reached."""


class NobetciEczaneResponseError(NobetciEczaneError):
    """Raised when the source returns an unexpected response."""

    def __init__(self, message: str, code: str = "unavailable") -> None:
        super().__init__(message)
        self.code = code


class _BootParser(HTMLParser):
    """Read the JSON boot data embedded in the official page."""

    def __init__(self) -> None:
        super().__init__()
        self._inside = False
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "script" and dict(attrs).get("id") == "boot":
            self._inside = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "script":
            self._inside = False

    def handle_data(self, data: str) -> None:
        if self._inside:
            self.parts.append(data)


class _TextParser(HTMLParser):
    """Convert the small HTML fragments returned by the service to text."""

    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "br":
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    @property
    def text(self) -> str:
        text = unescape("".join(self.parts)).replace("\r", "")
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r" *\n+ *", "\n", text)
        return text.strip()


def extract_boot(page: str) -> dict[str, Any]:
    """Extract and validate the page's new boot contract."""
    parser = _BootParser()
    parser.feed(page)
    try:
        boot = json.loads("".join(parser.parts))
    except (ValueError, TypeError) as err:
        raise NobetciEczaneResponseError("Page boot data was not found") from err
    if (
        not isinstance(boot, dict)
        or not isinstance(boot.get("token"), str)
        or not boot["token"]
    ):
        raise NobetciEczaneResponseError("Request token was not found")
    # Never send the session token to another origin or an unexpected endpoint.
    if boot.get("gateUrl") != urlsplit(API_URL).path:
        raise NobetciEczaneResponseError("Unexpected web API endpoint")
    return boot


def extract_token(page: str) -> str:
    """Extract the rotating web token from the landing page."""
    return extract_boot(page)["token"]


def request_radius(radius_km: float) -> int:
    """Validate the exact radius selected in Home Assistant."""
    if radius_km not in RADIUS_PRESETS:
        raise NobetciEczaneResponseError("Search radius must be 3, 6, 9 or 12 km")
    return int(radius_km)


def html_to_text(fragment: str | None, label: str | None = None) -> str:
    """Turn a returned HTML fragment into normalized plain text."""
    if not fragment:
        return ""
    parser = _TextParser()
    parser.feed(fragment)
    text = parser.text
    if label:
        text = re.sub(rf"^{re.escape(label)}\s*:\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r",\s*,+", ",", text)
    return text.strip(" ,\n")


def normalize_phone(phone: str | None) -> str:
    """Return a digits-only Turkish phone number without a leading zero."""
    digits = re.sub(r"\D", "", phone or "")
    if digits.startswith("90") and len(digits) == 12:
        digits = digits[2:]
    if digits.startswith("0") and len(digits) == 11:
        digits = digits[1:]
    return digits


def turkish_title(value: str | None) -> str:
    """Convert uppercase source text to title case with Turkish I rules."""
    text = (value or "").strip().translate(str.maketrans({"I": "ı", "İ": "i"})).lower()

    def uppercase(match: re.Match[str]) -> str:
        prefix, letter = match.groups()
        return prefix + {"i": "İ", "ı": "I"}.get(letter, letter.upper())

    return re.sub(r"(^|[\s\-/'(])([a-zçğıöşü])", uppercase, text)


@dataclass(frozen=True, slots=True)
class Pharmacy:
    """Normalized duty-pharmacy data."""

    registration_id: str
    name: str
    phone: str
    address: str
    directions: str
    latitude: float | None
    longitude: float | None
    duty_ends: str | None
    province: str
    district: str
    neighborhood: str
    subdistrict: str
    postal_code: str
    distance_km: float | None = None
    region_id: int | None = None
    phone_count: int = 0
    phone_ticket: str = field(default="", repr=False, compare=False)

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> Pharmacy:
        """Create a pharmacy from the official service payload."""

        def coordinate(key: str) -> float | None:
            value = payload.get(key)
            if value in (None, ""):
                return None
            try:
                number = float(value)
                limit = 90 if key == "lat" else 180
                return number if isfinite(number) and abs(number) <= limit else None
            except (TypeError, ValueError):
                return None

        address = html_to_text(payload.get("adres"), "Adres")
        if not address:
            street = " ".join(
                part
                for part in (
                    str(
                        payload.get("caddeSokak") or payload.get("cadde_sokak") or ""
                    ).strip(),
                    str(
                        payload.get("binaKapi") or payload.get("bina_kapi") or ""
                    ).strip(),
                )
                if part
            )
            address = ", ".join(
                part
                for part in (
                    str(payload.get("mahalle") or "").strip(),
                    street,
                    str(payload.get("semt") or "").strip(),
                )
                if part
            )

        return cls(
            registration_id=str(payload.get("sicil") or ""),
            name=turkish_title(
                str(payload.get("ad") or payload.get("eczane_ad") or "")
            ),
            phone=normalize_phone(payload.get("eczane_tel")),
            address=address,
            directions=html_to_text(payload.get("tarif"), "Tarif"),
            latitude=coordinate("lat"),
            longitude=coordinate("lng"),
            duty_ends=payload.get("dutyEndsAt") or payload.get("nobet_bitis") or None,
            province=str(payload.get("il") or "").strip(),
            district=str(payload.get("ilce") or "").strip(),
            neighborhood=str(payload.get("mahalle") or "").strip(),
            subdistrict=str(payload.get("semt") or "").strip(),
            postal_code=str(payload.get("posta_kodu") or "").strip(),
            region_id=payload.get("regionId"),
            phone_count=(
                payload.get("phones") if isinstance(payload.get("phones"), int) else 0
            ),
            phone_ticket=str(payload.get("phoneTicket") or ""),
        )


class NobetciEczaneClient:
    """Async client for the official web gate, with a private source session."""

    def __init__(self, session: ClientSession) -> None:
        self._session = session
        self._headers = {
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
            "Referer": SOURCE_URL,
            "Origin": ORIGIN,
        }
        self._token: str | None = None
        self._cookies: dict[str, str] = {}
        self._districts: list[dict[str, Any]] = []
        self._cache: dict[
            tuple[float, float, int], tuple[float, tuple[Pharmacy, ...]]
        ] = {}
        self._phones: dict[tuple[str, str | None], tuple[str, ...]] = {}
        # Serialize bootstrap, token refresh and tickets from all config entries.
        self._lock = asyncio.Lock()

    def _remember_session(self, response: Any) -> None:
        # HA's shared session may use a DummyCookieJar. Keep this source's cookie
        # explicitly, without depending on (or modifying) the shared cookie jar.
        if "PHPSESSID" in response.cookies:
            self._cookies["PHPSESSID"] = response.cookies["PHPSESSID"].value

    async def _async_bootstrap(self, *, force: bool = False) -> None:
        if self._token and not force:
            return
        try:
            async with self._session.get(
                SOURCE_URL, headers=self._headers, cookies=self._cookies, timeout=15
            ) as response:
                response.raise_for_status()
                self._remember_session(response)
                boot = extract_boot(await response.text())
        except (ClientError, TimeoutError) as err:
            raise NobetciEczaneConnectionError("Unable to load source session") from err
        self._token = boot["token"]
        self._districts = boot.get("districts", [])
        if not isinstance(self._districts, list):
            raise NobetciEczaneResponseError("District list is missing")
        self._cache.clear()  # Phone tickets belong to the token that issued them.

    async def _async_call(
        self,
        action: str,
        *,
        params: dict[str, Any] | None = None,
        body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        await self._async_bootstrap()
        for attempt in range(2):
            try:
                async with self._session.request(
                    "POST" if body is not None else "GET",
                    API_URL,
                    params={"action": action, **(params or {})},
                    json=body,
                    headers={**self._headers, "X-Web-Token": self._token},
                    cookies=self._cookies,
                    timeout=15,
                ) as response:
                    self._remember_session(response)
                    status = response.status
                    payload = json.loads(await response.text())
            except (ValueError, TypeError) as err:
                raise NobetciEczaneResponseError("Service did not return JSON") from err
            except (ClientError, TimeoutError) as err:
                raise NobetciEczaneConnectionError(
                    "Unable to reach source API"
                ) from err
            if not isinstance(payload, dict):
                raise NobetciEczaneResponseError("Unexpected JSON structure")
            if 200 <= status < 300 and payload.get("success") is True:
                return payload
            error = payload.get("error")
            error = error if isinstance(error, dict) else {}
            code = str(error.get("code") or "unavailable")
            if code == "token" and attempt == 0:
                await self._async_bootstrap(force=True)
                continue
            raise NobetciEczaneResponseError(
                str(error.get("message") or "Source API rejected the request"), code
            )
        raise NobetciEczaneResponseError("Unable to refresh source token")

    async def async_get_districts(self, province_code: str) -> list[str]:
        """Return districts from the page bootstrap, filtered by province."""
        async with self._lock:
            await self._async_bootstrap()
            return sorted(
                {
                    str(item["ilceAd"]).strip()
                    for item in self._districts
                    if isinstance(item, dict)
                    and str(item.get("ilId")) == str(province_code)
                    and item.get("ilceAd")
                }
            )

    async def _async_nearby(
        self,
        latitude: float,
        longitude: float,
        radius_km: float,
        *,
        force: bool = False,
    ) -> list[Pharmacy]:
        radius = request_radius(radius_km)
        if not (
            isfinite(latitude)
            and isfinite(longitude)
            and abs(latitude) <= 90
            and abs(longitude) <= 180
        ):
            raise NobetciEczaneResponseError("Invalid home coordinates")
        key = (latitude, longitude, radius)
        cached = self._cache.get(key)
        if not force and cached and monotonic() - cached[0] < CACHE_TTL_SECONDS:
            return list(cached[1])
        payload = await self._async_call(
            "nearby", body={"lat": latitude, "lng": longitude, "radiusKm": radius}
        )
        rows = payload.get("data")
        if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
            raise NobetciEczaneResponseError("Pharmacy list is missing or invalid")
        pharmacies = tuple(Pharmacy.from_payload(row) for row in rows)
        if any(not item.registration_id or not item.name for item in pharmacies):
            raise NobetciEczaneResponseError("Pharmacy identity is missing")
        if len(self._cache) >= 16:
            self._cache.clear()
        self._cache[key] = (monotonic(), pharmacies)
        return list(pharmacies)

    async def async_get_nearby_pharmacies(
        self, latitude: float, longitude: float, radius_km: float
    ) -> list[Pharmacy]:
        """Query one supported radius; the coordinator applies the exact radius."""
        async with self._lock:
            return await self._async_nearby(latitude, longitude, radius_km)

    async def _async_phone_request(self, pharmacy: Pharmacy) -> tuple[str, ...]:
        if not pharmacy.phone_ticket or pharmacy.region_id is None:
            raise NobetciEczaneResponseError("Phone is unavailable", "not_found")
        body = {
            "regionId": pharmacy.region_id,
            "sicil": pharmacy.registration_id,
            "ticket": pharmacy.phone_ticket,
        }
        for attempt in range(2):
            try:
                payload = await self._async_call("phone", body=body)
                break
            except NobetciEczaneResponseError as err:
                if err.code != "too_fast" or attempt:
                    raise
                # Follow the official client's single delayed retry; no polling.
                await asyncio.sleep(2.1)
        data = payload.get("data")
        if not isinstance(data, dict):
            raise NobetciEczaneResponseError("Phone response is invalid")
        phones = tuple(
            dict.fromkeys(
                phone
                for key in ("tel", "tel2")
                if len(phone := normalize_phone(data.get(key))) == 10
            )
        )
        if not phones:
            raise NobetciEczaneResponseError("Phone is unavailable", "not_found")
        return phones

    async def async_get_phone(
        self, registration_id: str, latitude: float, longitude: float, radius_km: float
    ) -> tuple[str, ...]:
        """Resolve a single pharmacy only when the user asks to call it."""
        async with self._lock:
            pharmacies = await self._async_nearby(latitude, longitude, radius_km)
            pharmacy = next(
                (p for p in pharmacies if p.registration_id == registration_id), None
            )
            if pharmacy is None:
                raise NobetciEczaneResponseError(
                    "Pharmacy is no longer on duty", "not_found"
                )
            key = (registration_id, pharmacy.duty_ends)
            if key in self._phones:
                return self._phones[key]
            try:
                phones = await self._async_phone_request(pharmacy)
            except NobetciEczaneResponseError as err:
                if err.code != "forbidden":
                    raise
                # A session refresh invalidates old tickets: re-read this list once.
                pharmacies = await self._async_nearby(
                    latitude, longitude, radius_km, force=True
                )
                pharmacy = next(
                    (p for p in pharmacies if p.registration_id == registration_id),
                    None,
                )
                if pharmacy is None:
                    raise NobetciEczaneResponseError(
                        "Pharmacy is no longer on duty", "not_found"
                    ) from err
                phones = await self._async_phone_request(pharmacy)
            if len(self._phones) >= 128:
                self._phones.clear()
            self._phones[key] = phones
            return phones
