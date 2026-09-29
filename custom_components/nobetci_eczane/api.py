"""Client for the İstanbul Eczacı Odası duty-pharmacy service."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from html import unescape
from html.parser import HTMLParser
import json
import re
from time import monotonic
from typing import Any

from aiohttp import ClientError, ClientSession

from .const import SOURCE_URL

API_URL = f"{SOURCE_URL}index.php"
USER_AGENT = (
    "HomeAssistant-NobetciEczane/0.5.1 "
    "(+https://github.com/cmrcan/HA_Pharmacy_on_Duty)"
)
CACHE_TTL_SECONDS = 60


class NobetciEczaneError(Exception):
    """Base exception for the integration."""


class NobetciEczaneConnectionError(NobetciEczaneError):
    """Raised when the source cannot be reached."""


class NobetciEczaneResponseError(NobetciEczaneError):
    """Raised when the source returns an unexpected response."""


class _TokenParser(HTMLParser):
    """Extract the rotating request token from the official page."""

    def __init__(self) -> None:
        super().__init__()
        self.token: str | None = None

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        if tag != "input":
            return
        values = dict(attrs)
        if values.get("id") == "h" or values.get("name") == "h":
            self.token = values.get("value")


class _TextParser(HTMLParser):
    """Convert the small HTML fragments returned by the service to text."""

    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
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


def extract_token(page: str) -> str:
    """Extract the required rotating token from the landing page."""
    parser = _TokenParser()
    parser.feed(page)
    if not parser.token:
        raise NobetciEczaneResponseError("Request token was not found")
    return parser.token


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

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> Pharmacy:
        """Create a pharmacy from the official service payload."""

        def coordinate(key: str) -> float | None:
            value = payload.get(key)
            if value in (None, ""):
                return None
            try:
                return float(value)
            except (TypeError, ValueError):
                return None

        address = html_to_text(payload.get("adres"), "Adres")
        if not address:
            street = " ".join(
                part
                for part in (
                    str(payload.get("cadde_sokak") or "").strip(),
                    str(payload.get("bina_kapi") or "").strip(),
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
            name=turkish_title(str(payload.get("eczane_ad") or "")),
            phone=normalize_phone(payload.get("eczane_tel")),
            address=address,
            directions=html_to_text(payload.get("tarif"), "Tarif"),
            latitude=coordinate("lat"),
            longitude=coordinate("lng"),
            duty_ends=(str(payload["nobet_bitis"]) if payload.get("nobet_bitis") else None),
            province=str(payload.get("il") or "").strip(),
            district=str(payload.get("ilce") or "").strip(),
            neighborhood=str(payload.get("mahalle") or "").strip(),
            subdistrict=str(payload.get("semt") or "").strip(),
            postal_code=str(payload.get("posta_kodu") or "").strip(),
        )


class NobetciEczaneClient:
    """Async client for the official İstanbul/Yalova service."""

    def __init__(self, session: ClientSession) -> None:
        self._session = session
        self._headers = {
            "User-Agent": USER_AGENT,
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Referer": SOURCE_URL,
            "X-Requested-With": "XMLHttpRequest",
        }
        self._token: str | None = None
        self._pharmacy_cache: tuple[Pharmacy, ...] | None = None
        self._pharmacy_cache_time = 0.0
        self._cache_lock = asyncio.Lock()

    async def _async_get_token(self, *, force: bool = False) -> str:
        if self._token is not None and not force:
            return self._token
        try:
            async with self._session.get(
                SOURCE_URL, headers=self._headers, timeout=15
            ) as response:
                response.raise_for_status()
                self._token = extract_token(await response.text())
                return self._token
        except NobetciEczaneResponseError:
            raise
        except (ClientError, TimeoutError) as err:
            raise NobetciEczaneConnectionError(str(err)) from err

    async def _async_post(self, operation: str, **parameters: str) -> dict[str, Any]:
        # The token can rotate between the GET and POST (observed at midnight),
        # so retry the complete handshake once when the service rejects it.
        last_message = "Unknown service response"
        for attempt in range(2):
            token = await self._async_get_token(force=attempt > 0)
            data = {"jx": "1", "islem": operation, "h": token, **parameters}
            try:
                async with self._session.post(
                    API_URL, data=data, headers=self._headers, timeout=15
                ) as response:
                    response.raise_for_status()
                    # The server labels JSON as text/html, so parse the body manually.
                    payload = json.loads(await response.text())
            except json.JSONDecodeError as err:
                raise NobetciEczaneResponseError("Service did not return JSON") from err
            except (ClientError, TimeoutError) as err:
                raise NobetciEczaneConnectionError(str(err)) from err

            if not isinstance(payload, dict):
                raise NobetciEczaneResponseError("Unexpected JSON structure")
            if payload.get("error") == 0:
                return payload
            self._token = None
            last_message = html_to_text(str(payload.get("message", last_message)))

        raise NobetciEczaneResponseError(last_message)

    async def async_get_districts(self, province_code: str) -> list[str]:
        """Return available districts for an İstanbul Eczacı Odası province."""
        payload = await self._async_post("get_ilce", il=province_code)
        districts = payload.get("ilceler")
        if not isinstance(districts, list):
            raise NobetciEczaneResponseError("District list is missing")
        return sorted(
            {
                str(item.get("ilce", "")).strip()
                for item in districts
                if isinstance(item, dict) and item.get("ilce")
            }
        )

    async def async_get_pharmacies(self, district: str) -> list[Pharmacy]:
        """Return the currently active duty pharmacies in a district."""
        payload = await self._async_post("get_ilce_eczane", ilce=district)
        pharmacies = payload.get("eczaneler")
        if not isinstance(pharmacies, list):
            raise NobetciEczaneResponseError("Pharmacy list is missing")
        return [
            Pharmacy.from_payload(item) for item in pharmacies if isinstance(item, dict)
        ]

    async def async_get_all_pharmacies(self) -> list[Pharmacy]:
        """Return all active pharmacies with full marker metadata.

        The official page uses this operation to populate its map. A short cache
        coalesces simultaneous config-entry refreshes into one source request.
        """
        now = monotonic()
        if (
            self._pharmacy_cache is not None
            and now - self._pharmacy_cache_time < CACHE_TTL_SECONDS
        ):
            return list(self._pharmacy_cache)

        async with self._cache_lock:
            now = monotonic()
            if (
                self._pharmacy_cache is not None
                and now - self._pharmacy_cache_time < CACHE_TTL_SECONDS
            ):
                return list(self._pharmacy_cache)

            payload = await self._async_post("get_eczane_markers")
            pharmacies = payload.get("eczaneler")
            if not isinstance(pharmacies, list):
                raise NobetciEczaneResponseError("Pharmacy marker list is missing")
            self._pharmacy_cache = tuple(
                Pharmacy.from_payload(item)
                for item in pharmacies
                if isinstance(item, dict)
            )
            self._pharmacy_cache_time = monotonic()
            return list(self._pharmacy_cache)
