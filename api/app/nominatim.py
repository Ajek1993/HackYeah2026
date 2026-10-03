"""Geocoding through Nominatim (OpenStreetMap, ODbL).

Usage policy: at most 1 request per second, an identifying User-Agent and caching.
The cache lives only in process memory with a TTL, so user addresses are never
persisted (SPEC: Never).
"""

import asyncio
import time
from collections import OrderedDict
from typing import Any

import httpx

from app.config import settings

# Bias search results to Kraków (lon_min, lat_max, lon_max, lat_min)
KRAKOW_VIEWBOX = "19.78,50.15,20.12,49.95"
CACHE_TTL_SECONDS = 3600
CACHE_MAX_ENTRIES = 1000
MIN_INTERVAL_SECONDS = 1.0


class Nominatim:
    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client or httpx.AsyncClient(
            base_url=settings.nominatim_url, timeout=httpx.Timeout(10.0, connect=3.0)
        )
        # Sent on every request, also with an injected client (usage policy)
        self._headers = {"User-Agent": settings.nominatim_user_agent, "Accept-Language": "pl"}
        self._lock = asyncio.Lock()
        self._last_request = 0.0
        self._cache: OrderedDict[tuple, tuple[float, Any]] = OrderedDict()

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _get(self, path: str, params: dict[str, Any]) -> Any:
        key = (path, tuple(sorted(params.items())))
        cached = self._cache.get(key)
        if cached and time.monotonic() - cached[0] < CACHE_TTL_SECONDS:
            self._cache.move_to_end(key)
            return cached[1]

        async with self._lock:
            wait = MIN_INTERVAL_SECONDS - (time.monotonic() - self._last_request)
            if wait > 0:
                await asyncio.sleep(wait)
            try:
                response = await self._client.get(
                    path, params={**params, "format": "jsonv2"}, headers=self._headers
                )
            finally:
                self._last_request = time.monotonic()
        response.raise_for_status()
        data = response.json()

        self._cache[key] = (time.monotonic(), data)
        while len(self._cache) > CACHE_MAX_ENTRIES:
            self._cache.popitem(last=False)
        return data

    async def search(self, query: str) -> dict | None:
        results = await self._get(
            "/search",
            {
                "q": query,
                "countrycodes": "pl",
                "viewbox": KRAKOW_VIEWBOX,
                "addressdetails": 1,
                "limit": 1,
            },
        )
        return results[0] if results else None

    async def reverse(self, lat: float, lon: float) -> dict | None:
        result = await self._get(
            "/reverse", {"lat": round(lat, 6), "lon": round(lon, 6), "addressdetails": 1}
        )
        return None if not result or "error" in result else result


def is_krakow_address(place: dict) -> bool:
    address = place.get("address") or {}
    return "Kraków" in (address.get("city"), address.get("town"), address.get("municipality"))


def district(place: dict) -> str | None:
    address = place.get("address") or {}
    for key in ("city_district", "suburb", "borough", "quarter"):
        if address.get(key):
            return address[key]
    return None


def short_name(place: dict) -> str | None:
    """'Kobierzyńska 1, Dębniki, Kraków' instead of the long Nominatim display_name."""
    address = place.get("address") or {}
    street = address.get("road") or address.get("pedestrian") or address.get("square")
    if street and address.get("house_number"):
        street = f"{street} {address['house_number']}"
    city = address.get("city") or address.get("town") or address.get("village")
    parts = [p for p in (street or place.get("name"), district(place), city) if p]
    return ", ".join(dict.fromkeys(parts)) or place.get("display_name")
