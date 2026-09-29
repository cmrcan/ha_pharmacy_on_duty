"""Constants for the Nöbetçi Eczane integration."""

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

DEFAULT_RADIUS_KM = 10
MIN_RADIUS_KM = 1
MAX_RADIUS_KM = 100

DEFAULT_UPDATE_INTERVAL_MINUTES = 30
MIN_UPDATE_INTERVAL_MINUTES = 15
MAX_UPDATE_INTERVAL_MINUTES = 360
SOURCE_NAME = "İstanbul Eczacı Odası"
SOURCE_URL = "https://www.istanbuleczaciodasi.org.tr/nobetci-eczane/"

CARD_URL = "/nobetci_eczane/nobetci-eczane-card.js"
PHARMACY_MARKER_URL = "/nobetci_eczane/pharmacy-marker.svg"
CARD_VERSION = "0.5.1"
