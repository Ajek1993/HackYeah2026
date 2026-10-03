import csv
import hashlib
import io
import logging

import requests

from app.celery_app import app
from app.config import settings
from app.db import get_conn

logger = logging.getLogger(__name__)

HEADERS = {"User-Agent": "KryzIO/1.0 (HackYeah2026; crisis-info-aggregator)"}


def _row_hash(row: dict) -> str:
    raw = "|".join(str(row.get(k, "")) for k in sorted(row.keys()))
    return hashlib.md5(raw.encode()).hexdigest()


def _parse_csv(content: bytes) -> list[dict]:
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    rows = []
    for row in reader:
        try:
            lat = float(row["Szerokosc geograficzna"])
            lon = float(row["Dlugosc geograficzna"])
        except (ValueError, KeyError):
            continue
        rows.append(
            {
                "shelter_id": row.get("Identyfikator publiczny", "").strip(),
                "name": row.get("Nazwa", "").strip(),
                "object_type": row.get("Rodzaj obiektu", "").strip() or None,
                "description": row.get("Opis ogolny", "").strip() or None,
                "address": row.get("Adres", "").strip() or None,
                "gmina": row.get("Gmina", "").strip() or None,
                "powiat": row.get("Powiat", "").strip() or None,
                "wojewodztwo": row.get("Wojewodztwo", "").strip() or None,
                "availability": row.get("Dostepnosc", "").strip() or None,
                "lat": lat,
                "lon": lon,
                "row_hash": _row_hash(row),
            }
        )
    return rows


@app.task(name="app.sources.shelters.fetch_shelters", bind=True, max_retries=2)
def fetch_shelters(self):
    try:
        resp = requests.get(settings.shelters_csv_url, headers=HEADERS, timeout=60)
        resp.raise_for_status()
    except requests.RequestException as exc:
        logger.error("Failed to download shelters CSV: %s", exc)
        raise self.retry(countdown=300, exc=exc)

    rows = _parse_csv(resp.content)
    if not rows:
        logger.warning("Shelters CSV parsed to 0 rows — skipping update")
        return {"status": "empty", "count": 0}

    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("SELECT now() AS ts")
                run_ts = cur.fetchone()["ts"]

                for r in rows:
                    cur.execute(
                        """
                        INSERT INTO shelters
                            (shelter_id, name, object_type, description, address,
                             gmina, powiat, wojewodztwo, availability,
                             geom, row_hash, last_seen_at, is_active)
                        VALUES
                            (%(shelter_id)s, %(name)s, %(object_type)s, %(description)s, %(address)s,
                             %(gmina)s, %(powiat)s, %(wojewodztwo)s, %(availability)s,
                             ST_SetSRID(ST_MakePoint(%(lon)s, %(lat)s), 4326),
                             %(row_hash)s, %(run_ts)s, true)
                        ON CONFLICT (shelter_id) DO UPDATE SET
                            name = EXCLUDED.name,
                            object_type = EXCLUDED.object_type,
                            description = EXCLUDED.description,
                            address = EXCLUDED.address,
                            gmina = EXCLUDED.gmina,
                            powiat = EXCLUDED.powiat,
                            wojewodztwo = EXCLUDED.wojewodztwo,
                            availability = EXCLUDED.availability,
                            geom = EXCLUDED.geom,
                            row_hash = EXCLUDED.row_hash,
                            last_seen_at = EXCLUDED.last_seen_at,
                            is_active = true
                        """,
                        {**r, "run_ts": run_ts},
                    )

                cur.execute(
                    "UPDATE shelters SET is_active = false WHERE last_seen_at < %s AND is_active",
                    (run_ts,),
                )
                deactivated = cur.rowcount

        logger.info("Shelters: upserted %d, deactivated %d", len(rows), deactivated)
        return {"status": "ok", "upserted": len(rows), "deactivated": deactivated}
    finally:
        conn.close()
