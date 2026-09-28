"""Constants for the Nöbetçi Eczane integration."""

from datetime import timedelta

DOMAIN = "nobetci_eczane"

CONF_PROVINCE = "province"
CONF_PROVINCE_CODE = "province_code"
CONF_DISTRICT = "district"

PROVINCES: dict[str, str] = {
    "34": "İstanbul",
    "77": "Yalova",
}

DEFAULT_UPDATE_INTERVAL = timedelta(minutes=30)

SOURCE_NAME = "İstanbul Eczacı Odası"
SOURCE_URL = "https://www.istanbuleczaciodasi.org.tr/nobetci-eczane/"

CARD_URL = "/nobetci_eczane/nobetci-eczane-card.js"
CARD_VERSION = "0.3.0"
