"""Air quality from Airly (airapi.airly.eu/v2). Runs only when AIRLY_API_KEY is set.

Free plan: 100 requests per day. One run = 1 + MAX_INSTALLATIONS requests and the
beat schedule fires every 2h, so a day stays well under the limit (SPEC: Airly every 2h).
"""

import logging
from datetime import datetime

import requests

from app.celery_app import app
from app.config import settings
from app.db import get_conn

logger = logging.getLogger(__name__)

KRAKOW_CENTER = (50.0614, 19.9366)
MAX_INSTALLATIONS = 4

# Airly CAQI levels -> contract enum
CAQI_LEVELS = {
    "VERY_LOW": "very_good",
    "LOW": "good",
    "MEDIUM": "moderate",
    "HIGH": "bad",
    "VERY_HIGH": "very_bad",
    "EXTREME": "very_bad",
    "AIRMAGEDDON": "very_bad",
}


def _get(path: str, **params) -> dict | list:
    resp = requests.get(
        f"{settings.airly_api_url}{path}",
        params=params,
        headers={"apikey": settings.airly_api_key, "Accept-Language": "pl"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def parse_measurement(installation: dict, payload: dict) -> dict | None:
    current = payload.get("current") or {}
    location = installation.get("location") or {}
    if location.get("latitude") is None or location.get("longitude") is None:
        return None
    index = next((i for i in current.get("indexes") or [] if i.get("name") == "AIRLY_CAQI"), {})
    values = {v.get("name"): v.get("value") for v in current.get("values") or []}
    address = installation.get("address") or {}
    measured = current.get("tillDateTime")
    return {
        "id": str(installation["id"]),
        "name": ", ".join(p for p in (address.get("city"), address.get("street")) if p)
        or "Czujnik Airly",
        "lat": float(location["latitude"]),
        "lon": float(location["longitude"]),
        "level": CAQI_LEVELS.get(index.get("level") or ""),
        "label": index.get("description"),
        "pm25": values.get("PM25"),
        "pm10": values.get("PM10"),
        "measured_at": datetime.fromisoformat(measured.replace("Z", "+00:00"))
        if measured
        else None,
    }


@app.task(name="app.sources.airly.fetch_airly_air_quality", bind=True, max_retries=1)
def fetch_airly_air_quality(self):
    if not settings.airly_api_key:
        return {"status": "skipped", "reason": "AIRLY_API_KEY not set"}

    try:
        installations = _get(
            "/installations/nearest",
            lat=KRAKOW_CENTER[0],
            lng=KRAKOW_CENTER[1],
            maxDistanceKM=8,
            maxResults=MAX_INSTALLATIONS,
        )
        readings = []
        for installation in installations:
            payload = _get("/measurements/installation", installationId=installation["id"])
            reading = parse_measurement(installation, payload)
            if reading:
                readings.append(reading)
    except requests.RequestException as exc:
        logger.error("Failed to fetch Airly: %s", exc)
        raise self.retry(exc=exc, countdown=600) from exc

    if not readings:
        return {"status": "empty"}

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
                        VALUES ('airly', %s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326),
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
                            r["pm25"],
                            r["pm10"],
                            r["measured_at"],
                        ),
                    )
    finally:
        conn.close()

    return {"status": "ok", "installations": len(readings)}
