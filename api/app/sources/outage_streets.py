"""Street-level location for Tauron outages published only with a district centre.

For most Kraków outages Tauron sends `CoordinatesType` 3: `Center` is the centre of the
whole power district (Kraków: Rynek Główny), so all of them land on one point. The
message names the streets, so its first address is geocoded with Nominatim and cached
in `geocode_cache`. These are public outage addresses, never user input.
"""

import logging
import re
import time
from collections.abc import Callable, Iterable
from datetime import UTC, datetime, timedelta

import requests

from app.config import settings

logger = logging.getLogger(__name__)

# Nominatim viewbox (lon_min, lat_max, lon_max, lat_min) and the same box for checks
KRAKOW_VIEWBOX = "19.78,50.15,20.12,49.95"
LAT_RANGE = (49.95, 50.15)
LON_RANGE = (19.78, 20.12)
# Usage policy: at most 1 request per second; new lookups per refresh are capped
MIN_INTERVAL_S = 1.1
MAX_LOOKUPS_PER_RUN = 15
RETRY_NOT_FOUND_AFTER = timedelta(days=7)

_CITY = re.compile(r"^(?:w\s+)?krak(?:ów|owie|ow)\b[\s,:]*", re.IGNORECASE)
_STREET_PREFIX = re.compile(r"^(?:ul\.|ulica|ulicy|al\.|aleja|alei)\s*", re.IGNORECASE)
_TAIL = re.compile(r"\s(?:od|do|oraz|klatka|nr|w kierunku)\b.*$", re.IGNORECASE)
_ADDRESS = re.compile(r"(?P<name>\D+)(?P<number>\d+[^\W\d_]{0,3})?")
_NOT_A_STREET = ("miejscowo", "części", "gmin")

Point = tuple[float, float]  # (lat, lon)


def street_queries(message: str) -> list[str]:
    """Geocoder queries for the first address in an outage message, most precise first.

    "Krakowie ul. Szuwarowa 4, Kobierzyńska od 132..." -> ["Szuwarowa 4, Kraków",
    "Szuwarowa, Kraków"]
    """
    text = " ".join((message or "").split())
    # Only city addresses: nearby villages share the district, and "<village>, Kraków"
    # would match a namesake street inside the city
    city = _CITY.match(text)
    if not city:
        return []
    text = _STREET_PREFIX.sub("", text[city.end() :])
    text = re.split(r"[,;]", text, maxsplit=1)[0]
    text = _TAIL.sub("", text).strip(" .")
    match = _ADDRESS.match(text)
    if not match:
        return []
    name = match["name"].strip(" .-")
    if len(name) < 3 or any(word in name.lower() for word in _NOT_A_STREET):
        return []
    queries = [f"{name} {match['number']}, Kraków"] if match["number"] else []
    return [*queries, f"{name}, Kraków"]


def _in_krakow(lat: float, lon: float) -> bool:
    return LAT_RANGE[0] <= lat <= LAT_RANGE[1] and LON_RANGE[0] <= lon <= LON_RANGE[1]


def nominatim_point(query: str) -> Point | None:
    response = requests.get(
        f"{settings.nominatim_url}/search",
        params={
            "q": query,
            "format": "jsonv2",
            "limit": 1,
            "countrycodes": "pl",
            "viewbox": KRAKOW_VIEWBOX,
            "bounded": 1,
        },
        headers={"User-Agent": settings.nominatim_user_agent, "Accept-Language": "pl"},
        timeout=10,
    )
    response.raise_for_status()
    results = response.json()
    if not isinstance(results, list) or not results or not isinstance(results[0], dict):
        return None
    try:
        lat, lon = float(results[0]["lat"]), float(results[0]["lon"])
    except (KeyError, TypeError, ValueError):
        return None
    return (lat, lon) if _in_krakow(lat, lon) else None


def locate_streets(
    conn,
    messages: Iterable[str],
    lookup: Callable[[str], Point | None] = nominatim_point,
    sleep: Callable[[float], None] = time.sleep,
    now: datetime | None = None,
) -> dict[str, Point]:
    """Point of the first address of every message that can be located.

    Cached answers are reused; Nominatim is called outside any transaction, so a slow
    geocoder never holds database locks.
    """
    now = now or datetime.now(UTC)
    wanted = {message: street_queries(message) for message in set(messages)}
    queries = sorted({query for candidates in wanted.values() for query in candidates})
    if not queries:
        return {}

    with conn.transaction(), conn.cursor() as cur:
        cur.execute(
            "SELECT query, found, lat, lon, fetched_at FROM geocode_cache WHERE query = ANY(%s)",
            (queries,),
        )
        cache = {row["query"]: row for row in cur.fetchall()}

    fresh: dict[str, Point | None] = {}
    budget = MAX_LOOKUPS_PER_RUN

    def resolve(query: str) -> Point | None:
        nonlocal budget
        row = cache.get(query)
        if row and (row["found"] or now - row["fetched_at"] < RETRY_NOT_FOUND_AFTER):
            return (row["lat"], row["lon"]) if row["found"] else None
        if query in fresh:
            return fresh[query]
        if budget <= 0:
            return None  # next refresh continues
        if budget < MAX_LOOKUPS_PER_RUN:
            sleep(MIN_INTERVAL_S)
        budget -= 1
        try:
            fresh[query] = lookup(query)
        except requests.RequestException as exc:
            logger.warning("Outage street geocoding unavailable: %s", exc)
            budget = 0
            return None
        return fresh[query]

    points: dict[str, Point] = {}
    for message, candidates in wanted.items():
        for query in candidates:
            point = resolve(query)
            if point:
                points[message] = point
                break

    if fresh:
        with conn.transaction(), conn.cursor() as cur:
            for query, point in fresh.items():
                cur.execute(
                    """INSERT INTO geocode_cache (query, found, lat, lon, fetched_at)
                       VALUES (%s, %s, %s, %s, now())
                       ON CONFLICT (query) DO UPDATE SET found = EXCLUDED.found,
                           lat = EXCLUDED.lat, lon = EXCLUDED.lon, fetched_at = now()""",
                    (query, point is not None, *(point or (None, None))),
                )
    return points
