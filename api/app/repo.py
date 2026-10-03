"""SQL queries for the API endpoints (async, parametrized).

Routers depend on `Repo` through `get_repo`, so tests swap it for a fake.
"""

from collections.abc import AsyncIterator
from datetime import datetime
from typing import Any

from fastapi import Request
from psycopg import AsyncConnection

from app.config import settings

# Fallback when the Kraków boundary is not loaded yet (same box as the Tauron filter)
KRAKOW_BBOX = "ST_MakeEnvelope(19.78, 49.95, 20.12, 50.15, 4326)"
KRAKOW_CENTER = "ST_SetSRID(ST_MakePoint(19.9366, 50.0614), 4326)"

# Hydro warnings have no geometry, only catchment descriptions; these cover Kraków
KRAKOW_CATCHMENTS = [
    "%Wisła od ujścia Przemszy do ujścia Raby%",
    "%Rudawy%",
    "%Prądnika%",
    "%Wilgi%",
    "%Skawinki%",
    "%Dłubni%",
]


def in_krakow_sql(point: str) -> str:
    """SQL boolean: point inside the Kraków boundary, or inside the bbox fallback.

    `point` must be a qualified column (e.g. "s.geom"): ref_areas has its own `geom`.
    """
    return f"""COALESCE(
        (SELECT ST_Contains(a.geom, {point}) FROM ref_areas a
          WHERE a.area_type = 'powiat' AND a.code = %(teryt)s),
        ST_Within({point}, {KRAKOW_BBOX}))"""


def _point() -> str:
    return "ST_SetSRID(ST_MakePoint(%(lon)s, %(lat)s), 4326)"


class Repo:
    def __init__(self, conn: AsyncConnection) -> None:
        self.conn = conn

    async def _all(self, sql: str, params: dict[str, Any] | None = None) -> list[dict]:
        async with self.conn.cursor() as cur:
            await cur.execute(sql, {"teryt": settings.krakow_teryt, **(params or {})})
            return await cur.fetchall()

    async def _one(self, sql: str, params: dict[str, Any] | None = None) -> dict | None:
        rows = await self._all(sql, params)
        return rows[0] if rows else None

    async def last_fetch(self, table: str) -> datetime | None:
        # Table names come from code only (never from requests)
        tables = {
            "shelters",
            "power_outages",
            "hydro_stations",
            "imgw_warnings",
            "air_quality_readings",
        }
        if table not in tables:
            raise ValueError(table)
        row = await self._one(f"SELECT max(last_seen_at) AS ts FROM {table}")
        return row["ts"] if row else None

    async def point_in_krakow(self, lat: float, lon: float) -> bool | None:
        """None when the boundary is not loaded (caller falls back to geocoder data)."""
        row = await self._one(
            f"""SELECT ST_Contains(a.geom, {_point()}) AS inside FROM ref_areas a
                 WHERE a.area_type = 'powiat' AND a.code = %(teryt)s""",
            {"lat": lat, "lon": lon},
        )
        return row["inside"] if row else None

    async def shelters_in_krakow(self) -> list[dict]:
        return await self._all(
            f"""SELECT s.shelter_id, s.name, s.object_type, s.address, s.availability,
                       ST_Y(s.geom) AS lat, ST_X(s.geom) AS lon
                  FROM shelters s
                 WHERE s.is_active AND s.coords_ok AND {in_krakow_sql("s.geom")}
                 ORDER BY s.shelter_id"""
        )

    async def nearest_shelters(self, lat: float, lon: float, limit: int) -> list[dict]:
        return await self._all(
            # <-> (index KNN) works in degrees; take candidates by it, then sort in metres
            f"""SELECT * FROM (
                    SELECT shelter_id, name, object_type, address, availability,
                           ST_Y(geom) AS lat, ST_X(geom) AS lon,
                           round(ST_Distance(geom::geography, p::geography))::int AS distance_m
                      FROM shelters, {_point()} AS p
                     WHERE is_active AND coords_ok
                     ORDER BY geom <-> p
                     LIMIT 50) candidates
                 ORDER BY distance_m
                 LIMIT %(limit)s""",
            {"lat": lat, "lon": lon, "limit": limit},
        )

    async def krakow_warnings(self) -> list[dict]:
        return await self._all(
            """SELECT warning_key, source, title, severity, body, area_descriptions,
                      valid_from, valid_to, ST_AsGeoJSON(geom)::json AS geometry
                 FROM imgw_warnings
                WHERE is_active
                  AND (valid_to IS NULL OR valid_to > now())
                  AND (   (source = 'meteo' AND %(teryt)s = ANY (area_codes))
                       OR (source = 'hydro'
                           AND 'małopolskie' = ANY (voivodeships)
                           AND array_to_string(area_descriptions, ' | ')
                               ILIKE ANY (%(catchments)s)))
                ORDER BY severity DESC NULLS LAST, valid_from""",
            {"catchments": KRAKOW_CATCHMENTS},
        )

    async def krakow_water_levels(self) -> list[dict]:
        return await self._all(
            f"""SELECT h.station_id, h.name, h.river, ST_Y(h.geom) AS lat, ST_X(h.geom) AS lon,
                       h.water_level_cm, h.warning_level_cm, h.alarm_level_cm, h.level_status,
                       h.measured_at
                  FROM hydro_stations h
                 WHERE h.is_active
                   AND (   {in_krakow_sql("h.geom")}
                        OR ST_DWithin(h.geom::geography, {KRAKOW_CENTER}::geography, 15000))
                 ORDER BY ST_Distance(h.geom, {KRAKOW_CENTER})"""
        )

    async def krakow_power_outages(self) -> list[dict]:
        # Without exact coordinates `center` is the whole district's centre: prefer the
        # geocoded first street of the message (app/sources/outage_streets.py)
        return await self._all(
            f"""SELECT id, outage_kind, message, start_at, end_at, precision AS location_precision,
                       ST_Y(point) AS lat, ST_X(point) AS lon
                  FROM (SELECT o.outage_id::text || '@' || to_char(o.start_at AT TIME ZONE 'UTC',
                                   'YYYY-MM-DD"T"HH24:MI"Z"') AS id,
                               o.outage_kind, o.message, o.start_at, o.end_at,
                               CASE WHEN o.location_precision = 'dokladna' THEN 'exact'
                                    WHEN o.street_center IS NOT NULL THEN 'street'
                                    ELSE 'approximate' END AS precision,
                               CASE WHEN o.location_precision = 'dokladna' THEN o.center
                                    ELSE COALESCE(o.street_center, o.center) END AS point
                          FROM power_outages o
                         WHERE o.is_active
                           AND (o.end_at IS NULL OR o.end_at > now())) outage
                 WHERE outage.point IS NOT NULL
                   AND {in_krakow_sql("outage.point")}
                 ORDER BY start_at"""
        )

    async def freshest_air_quality(self, lat: float, lon: float) -> dict | None:
        """Nearest stations of every provider, then the freshest reading wins (US-04)."""
        return await self._one(
            f"""SELECT * FROM (
                    SELECT DISTINCT ON (provider)
                           provider, station_id, station_name, index_level, index_label,
                           pm25, pm10, measured_at, last_seen_at
                      FROM air_quality_readings, {_point()} AS p
                     WHERE is_active
                       AND index_level IS NOT NULL
                       AND ST_DWithin(geom::geography, p::geography, 10000)
                     ORDER BY provider, geom <-> p) nearest
                 ORDER BY measured_at DESC NULLS LAST
                 LIMIT 1""",
            {"lat": lat, "lon": lon},
        )


async def get_repo(request: Request) -> AsyncIterator[Repo]:
    async with request.app.state.pool.connection() as conn:
        yield Repo(conn)
