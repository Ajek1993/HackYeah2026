"""Air quality from GIOŚ (api.gios.gov.pl/pjp-api/v1, no API key)."""

import logging
from datetime import datetime
from zoneinfo import ZoneInfo

import requests

from app.celery_app import app
from app.config import settings
from app.db import get_conn

logger = logging.getLogger(__name__)

HEADERS = {"User-Agent": "KryzIO/1.0 (HackYeah2026; crisis-info-aggregator)"}
WARSAW = ZoneInfo("Europe/Warsaw")

# GIOŚ index value (0..5) -> contract enum
INDEX_LEVELS = ["very_good", "good", "moderate", "sufficient", "bad", "very_bad"]


def _list_payload(payload: dict) -> list[dict]:
    """GIOŚ wraps every list under a Polish, sometimes mis-encoded key."""
    return next((v for v in payload.values() if isinstance(v, list)), [])


def _field(item: dict, prefix: str, suffix: str = "") -> object:
    """Looks a field up by prefix/suffix, since some GIOŚ keys arrive mis-encoded."""
    for key, value in item.items():
        if key.startswith(prefix) and key.endswith(suffix):
            return value
    return None


def _parse_time(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S").replace(tzinfo=WARSAW)
    except ValueError:
        return None


def krakow_stations(stations: list[dict]) -> list[dict]:
    result = []
    for station in stations:
        if station.get("Nazwa miasta") != "Kraków":
            continue
        try:
            lat = float(_field(station, "WGS84", "N"))
            lon = float(_field(station, "WGS84", "E"))
        except (TypeError, ValueError):
            continue
        result.append(
            {
                "id": str(station["Identyfikator stacji"]),
                "name": station.get("Nazwa stacji") or "Stacja GIOŚ",
                "lat": lat,
                "lon": lon,
            }
        )
    return result


def parse_index(payload: dict) -> tuple[str | None, str | None, datetime | None]:
    index = payload.get("AqIndex") or {}
    value = index.get("Wartość indeksu")
    level = INDEX_LEVELS[value] if isinstance(value, int) and 0 <= value < 6 else None
    label = index.get("Nazwa kategorii indeksu")
    measured = _parse_time(_field(index, "Data danych źródłowych", "wskaźnika st"))
    return level, label, measured


def latest_value(payload: dict) -> float | None:
    for row in _list_payload(payload):
        value = _field(row, "Warto")
        if isinstance(value, int | float):
            return float(value)
    return None


def _get(path: str, **params) -> dict:
    resp = requests.get(
        f"{settings.gios_api_url}{path}", params=params, headers=HEADERS, timeout=30
    )
    resp.raise_for_status()
    return resp.json()


def _pm_values(station_id: str) -> dict[str, float | None]:
    values: dict[str, float | None] = {"PM2.5": None, "PM10": None}
    for sensor in _list_payload(_get(f"/station/sensors/{station_id}")):
        code = _field(sensor, "Wska", " - kod")
        if code in values:
            sensor_id = sensor.get("Identyfikator stanowiska")
            try:
                values[code] = latest_value(_get(f"/data/getData/{sensor_id}"))
            except requests.HTTPError:
                # Manual sensors publish results weeks later (HTTP 400); keep the index anyway
                values[code] = None
    return values


@app.task(name="app.sources.gios.fetch_gios_air_quality", bind=True, max_retries=2)
def fetch_gios_air_quality(self):
    try:
        stations = krakow_stations(_list_payload(_get("/station/findAll", size=500)))
    except requests.RequestException as exc:
        logger.error("Failed to fetch GIOŚ stations: %s", exc)
        raise self.retry(exc=exc, countdown=300) from exc

    readings = []
    for station in stations:
        try:
            level, label, measured = parse_index(_get(f"/aqindex/getIndex/{station['id']}"))
            pm = _pm_values(station["id"])
        except requests.RequestException as exc:
            # One station failing must not drop the others; its last reading stays in cache
            logger.warning("GIOŚ station %s skipped: %s", station["id"], exc)
            continue
        readings.append({**station, "level": level, "label": label, "measured_at": measured, **pm})

    if not readings:
        logger.warning("GIOŚ returned no readings for Kraków; keeping cached data")
        return {"status": "empty", "stations": len(stations)}

    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                for r in readings:
                    cur.execute(
                        """
                        INSERT INTO air_quality_readings
                            (provider, station_id, station_name, geom, index_level, index_label,
                             pm25, pm10, measured_at, last_seen_at, is_active)
                        VALUES ('gios', %s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326),
                                %s, %s, %s, %s, %s, now(), true)
                        ON CONFLICT (provider, station_id) DO UPDATE SET
                            station_name = EXCLUDED.station_name, geom = EXCLUDED.geom,
                            index_level = EXCLUDED.index_level,
                            index_label = EXCLUDED.index_label,
                            pm25 = EXCLUDED.pm25, pm10 = EXCLUDED.pm10,
                            measured_at = EXCLUDED.measured_at,
                            last_seen_at = EXCLUDED.last_seen_at, is_active = true
                        """,
                        (
                            r["id"],
                            r["name"],
                            r["lon"],
                            r["lat"],
                            r["level"],
                            r["label"],
                            r["PM2.5"],
                            r["PM10"],
                            r["measured_at"],
                        ),
                    )
    finally:
        conn.close()

    logger.info("GIOŚ: %d Kraków stations stored", len(readings))
    return {"status": "ok", "stations": len(readings)}
