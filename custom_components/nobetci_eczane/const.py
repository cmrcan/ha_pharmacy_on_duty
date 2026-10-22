"""Constants for the Nöbetçi Eczane integration."""

from math import isfinite

DOMAIN = "nobetci_eczane"

CONF_PROVINCE = "province"
CONF_PROVINCE_CODE = "province_code"
CONF_DISTRICT = "district"
CONF_RADIUS_KM = "radius_km"
CONF_UPDATE_INTERVAL_MINUTES = "update_interval_minutes"

PROVINCES: dict[str, str] = {
    "34": "İstanbul",
    "77": "Yalova",
}

RADIUS_PRESETS_KM = (3, 6, 9, 12)
DEFAULT_RADIUS_KM = 12
MIN_RADIUS_KM = RADIUS_PRESETS_KM[0]
MAX_RADIUS_KM = RADIUS_PRESETS_KM[-1]
RADIUS_STEP_KM = 3


def normalize_radius_km(value: float) -> int:
    """Move legacy radius values up to the next supported preset."""
    radius = float(value)
    if not isfinite(radius):
        return DEFAULT_RADIUS_KM
    return next(
        (preset for preset in RADIUS_PRESETS_KM if preset >= radius), MAX_RADIUS_KM
    )


DEFAULT_UPDATE_INTERVAL_MINUTES = 30
MIN_UPDATE_INTERVAL_MINUTES = 15
MAX_UPDATE_INTERVAL_MINUTES = 360
SOURCE_NAME = "İstanbul Eczacı Odası"
SOURCE_URL = "https://www.istanbuleczaciodasi.org.tr/nobetci-eczane/"

CARD_URL = "/nobetci_eczane/nobetci-eczane-card.js"
PHARMACY_MARKER_URL = "/nobetci_eczane/pharmacy-marker.svg"
CARD_VERSION = "0.6.1"
