"""Data coordinator for Nöbetçi Eczane."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, replace
from datetime import datetime
import logging
from math import asin, cos, radians, sin, sqrt

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import NobetciEczaneClient, NobetciEczaneError, Pharmacy
from .const import CONF_DISTRICT, DEFAULT_UPDATE_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


def haversine_km(
    latitude_a: float,
    longitude_a: float,
    latitude_b: float,
    longitude_b: float,
) -> float:
    """Calculate straight-line distance between two WGS84 coordinates."""
    radius_km = 6371.0088
    lat_a, lon_a, lat_b, lon_b = map(
        radians, (latitude_a, longitude_a, latitude_b, longitude_b)
    )
    d_lat = lat_b - lat_a
    d_lon = lon_b - lon_a
    value = sin(d_lat / 2) ** 2 + cos(lat_a) * cos(lat_b) * sin(d_lon / 2) ** 2
    return 2 * radius_km * asin(sqrt(value))


@dataclass(frozen=True, slots=True)
class DutyPharmacyData:
    """Coordinator data shared by all entities."""

    pharmacies: tuple[Pharmacy, ...]
    fetched_at: datetime


class NobetciEczaneCoordinator(DataUpdateCoordinator[DutyPharmacyData]):
    """Coordinate polling of the official service."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: NobetciEczaneClient,
    ) -> None:
        self.client = client
        self.district = entry.data[CONF_DISTRICT]
        super().__init__(
            hass,
            logger=_LOGGER,
            name=f"{DOMAIN}_{self.district}",
            config_entry=entry,
            update_interval=DEFAULT_UPDATE_INTERVAL,
            always_update=False,
        )

    async def _async_update_data(self) -> DutyPharmacyData:
        try:
            async with asyncio.timeout(20):
                pharmacies = await self.client.async_get_pharmacies(self.district)
        except NobetciEczaneError as err:
            raise UpdateFailed(str(err)) from err

        home_latitude = self.hass.config.latitude
        home_longitude = self.hass.config.longitude
        enriched: list[Pharmacy] = []
        for pharmacy in pharmacies:
            distance: float | None = None
            if pharmacy.latitude is not None and pharmacy.longitude is not None:
                distance = round(
                    haversine_km(
                        home_latitude,
                        home_longitude,
                        pharmacy.latitude,
                        pharmacy.longitude,
                    ),
                    2,
                )
            enriched.append(replace(pharmacy, distance_km=distance))

        enriched.sort(
            key=lambda item: (
                item.distance_km is None,
                item.distance_km if item.distance_km is not None else float("inf"),
                item.name,
            )
        )
        return DutyPharmacyData(tuple(enriched), dt_util.utcnow())
