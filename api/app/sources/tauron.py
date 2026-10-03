import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone

import requests

from app.celery_app import app
from app.config import settings
from app.db import get_conn

logger = logging.getLogger(__name__)

HEADERS = {"User-Agent": "KryzIO/1.0 (HackYeah2026; crisis-info-aggregator)"}

KRAKOW_BBOX = {
    "lat_min": 49.95,
    "lat_max": 50.15,
    "lon_min": 19.78,
    "lon_max": 20.12,
}


def _item_hash(item: dict) -> str:
    raw = json.dumps(item, sort_keys=True, default=str)
    return hashlib.md5(raw.encode()).hexdigest()


def _is_in_krakow(item: dict) -> bool:
    center = item.get("Center")
    if center and center.get("lat") and center.get("lng"):
        lat, lng = center["lat"], center["lng"]
        if (
            KRAKOW_BBOX["lat_min"] <= lat <= KRAKOW_BBOX["lat_max"]
            and KRAKOW_BBOX["lon_min"] <= lng <= KRAKOW_BBOX["lon_max"]
        ):
            return True

    coords = item.get("Coordinates") or []
    for c in coords:
        if c.get("lat") and c.get("lng"):
            lat, lng = c["lat"], c["lng"]
            if (
                KRAKOW_BBOX["lat_min"] <= lat <= KRAKOW_BBOX["lat_max"]
                and KRAKOW_BBOX["lon_min"] <= lng <= KRAKOW_BBOX["lon_max"]
            ):
                return True

    msg = (item.get("Message") or "").lower()
    if "kraków" in msg or "krakow" in msg or "nowa huta" in msg:
        return True

    return False


def _build_geom_wkt(item: dict) -> str | None:
    coords = item.get("Coordinates") or []
    if not coords:
        return None

    points = [(c["lng"], c["lat"]) for c in coords if c.get("lat") and c.get("lng")]
    if not points:
        return None

    if len(points) == 1:
        return f"SRID=4326;POINT({points[0][0]} {points[0][1]})"

    if len(points) >= 4 and points[0] == points[-1]:
        ring = ", ".join(f"{lon} {lat}" for lon, lat in points)
        return f"SRID=4326;POLYGON(({ring}))"

    mp = ", ".join(f"{lon} {lat}" for lon, lat in points)
    return f"SRID=4326;MULTIPOINT({mp})"


def _build_center_wkt(item: dict) -> str | None:
    center = item.get("Center")
    if center and center.get("lat") and center.get("lng"):
        return f"SRID=4326;POINT({center['lng']} {center['lat']})"
    return None


@app.task(name="app.sources.tauron.fetch_tauron_outages", bind=True, max_retries=2)
def fetch_tauron_outages(self):
    now_utc = datetime.now(timezone.utc)
    params = {
        "fromDate": now_utc.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        "toDate": (now_utc + timedelta(days=5)).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
    }

    try:
        resp = requests.get(
            settings.tauron_api_url, params=params, headers=HEADERS, timeout=30
        )
        resp.raise_for_status()
        items = resp.json()
    except requests.RequestException as exc:
        logger.error("Failed to fetch Tauron outages: %s", exc)
        raise self.retry(countdown=120, exc=exc)

    krakow_items = [it for it in items if _is_in_krakow(it)]

    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("SELECT now() AS ts")
                run_ts = cur.fetchone()["ts"]

                for it in krakow_items:
                    geom_wkt = _build_geom_wkt(it)
                    center_wkt = _build_center_wkt(it)

                    cur.execute(
                        """
                        INSERT INTO power_outages
                            (provider, outage_id, start_at, end_at, type_id,
                             message, source_modified_at, region_ids,
                             address_point_ids, coords_type,
                             geom, center, radius_m,
                             source_is_active, row_hash, last_seen_at, is_active)
                        VALUES
                            ('tauron', %(outage_id)s, %(start_at)s, %(end_at)s, %(type_id)s,
                             %(message)s, %(modified)s, %(region_ids)s,
                             %(address_point_ids)s, %(coords_type)s,
                             %(geom)s::geometry, %(center)s::geometry, %(radius_m)s,
                             %(is_active)s, %(row_hash)s, %(run_ts)s, true)
                        ON CONFLICT (provider, outage_id, start_at) DO UPDATE SET
                            end_at = EXCLUDED.end_at,
                            type_id = EXCLUDED.type_id,
                            message = EXCLUDED.message,
                            source_modified_at = EXCLUDED.source_modified_at,
                            region_ids = EXCLUDED.region_ids,
                            address_point_ids = EXCLUDED.address_point_ids,
                            coords_type = EXCLUDED.coords_type,
                            geom = EXCLUDED.geom,
                            center = EXCLUDED.center,
                            radius_m = EXCLUDED.radius_m,
                            source_is_active = EXCLUDED.source_is_active,
                            row_hash = EXCLUDED.row_hash,
                            last_seen_at = EXCLUDED.last_seen_at,
                            is_active = true
                        """,
                        {
                            "outage_id": it["OutageId"],
                            "start_at": it.get("StartDate"),
                            "end_at": it.get("EndDate"),
                            "type_id": it.get("TypeId"),
                            "message": it.get("Message", ""),
                            "modified": it.get("Modified"),
                            "region_ids": it.get("IdsWWW"),
                            "address_point_ids": it.get("AddressPointIds"),
                            "coords_type": it.get("CoordinatesType"),
                            "geom": geom_wkt,
                            "center": center_wkt,
                            "radius_m": it.get("Radius"),
                            "is_active": it.get("IsActive"),
                            "row_hash": _item_hash(it),
                            "run_ts": run_ts,
                        },
                    )

                cur.execute(
                    """UPDATE power_outages SET is_active = false
                       WHERE provider = 'tauron' AND last_seen_at < %s AND is_active""",
                    (run_ts,),
                )
                deactivated = cur.rowcount

        logger.info(
            "Tauron: %d total items, %d in Kraków, %d deactivated",
            len(items), len(krakow_items), deactivated,
        )
        return {
            "status": "ok",
            "total": len(items),
            "krakow": len(krakow_items),
            "deactivated": deactivated,
        }
    finally:
        conn.close()
