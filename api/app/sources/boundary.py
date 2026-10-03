"""Kraków administrative boundary from OpenStreetMap (Nominatim, ODbL).

Stored in ref_areas as powiat 1261, so that:
- endpoints can tell whether a point lies inside Kraków (ST_Contains),
- the imgw_warnings trigger can draw meteo warnings issued for TERYT 1261.
"""

import json
import logging

import requests

from app.celery_app import app
from app.config import settings
from app.db import get_conn

logger = logging.getLogger(__name__)

SEARCH_PARAMS = {
    "city": "Kraków",
    "country": "Poland",
    "format": "geojson",
    "polygon_geojson": 1,
    # Simplifies the outline to ~50 m; plenty for "is this point in Kraków"
    "polygon_threshold": 0.0005,
    "limit": 1,
}


def _extract_polygon(payload: dict) -> dict | None:
    for feature in payload.get("features") or []:
        props = feature.get("properties") or {}
        geometry = feature.get("geometry") or {}
        if props.get("category") == "boundary" and geometry.get("type") in (
            "Polygon",
            "MultiPolygon",
        ):
            return geometry
    return None


@app.task(name="app.sources.boundary.fetch_krakow_boundary", bind=True, max_retries=2)
def fetch_krakow_boundary(self):
    try:
        resp = requests.get(
            f"{settings.nominatim_url}/search",
            params=SEARCH_PARAMS,
            headers={"User-Agent": settings.nominatim_user_agent},
            timeout=30,
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        logger.error("Failed to fetch Kraków boundary: %s", exc)
        raise self.retry(exc=exc, countdown=120) from exc

    geometry = _extract_polygon(resp.json())
    if geometry is None:
        logger.warning("Nominatim returned no boundary polygon for Kraków; keeping old one")
        return {"status": "no_polygon"}

    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO ref_areas (area_type, code, name, geom)
                    VALUES ('powiat', %s, 'Kraków',
                            ST_Multi(ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326)))
                    ON CONFLICT (area_type, code) DO UPDATE
                       SET name = EXCLUDED.name, geom = EXCLUDED.geom
                    """,
                    (settings.krakow_teryt, json.dumps(geometry)),
                )
                # Re-run the geometry trigger for warnings loaded before the boundary existed
                cur.execute("UPDATE imgw_warnings SET area_codes = area_codes")
                refreshed = cur.rowcount
    finally:
        conn.close()

    logger.info("Kraków boundary stored, %d warnings re-geocoded", refreshed)
    return {"status": "ok", "warnings_refreshed": refreshed}
