import hashlib
import json
import logging

import requests

from app.celery_app import app
from app.config import settings
from app.db import get_conn

logger = logging.getLogger(__name__)

HEADERS = {"User-Agent": "KryzIO/1.0 (HackYeah2026; crisis-info-aggregator)"}


def _json_hash(obj: dict) -> str:
    raw = json.dumps(obj, sort_keys=True, default=str)
    return hashlib.md5(raw.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Hydro stations
# ---------------------------------------------------------------------------


@app.task(name="app.sources.imgw.fetch_imgw_hydro", bind=True, max_retries=2)
def fetch_imgw_hydro(self):
    try:
        resp = requests.get(settings.imgw_hydro_url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        stations = resp.json()
    except requests.RequestException as exc:
        logger.error("Failed to fetch IMGW hydro: %s", exc)
        raise self.retry(countdown=300, exc=exc) from exc

    if not isinstance(stations, list):
        logger.warning("IMGW hydro returned non-list: %s", type(stations))
        return {"status": "unexpected_format"}

    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("SELECT now() AS ts")
                run_ts = cur.fetchone()["ts"]

                count = 0
                for s in stations:
                    try:
                        lat = float(s["lat"])
                        lon = float(s["lon"])
                    except (ValueError, KeyError, TypeError):
                        continue

                    def _int(val):
                        if val is None:
                            return None
                        try:
                            return int(val)
                        except (ValueError, TypeError):
                            return None

                    def _float(val):
                        if val is None:
                            return None
                        try:
                            return float(val)
                        except (ValueError, TypeError):
                            return None

                    cur.execute(
                        """
                        INSERT INTO hydro_stations
                            (station_id, name, river, wojewodztwo, geom,
                             water_level_cm, warning_level_cm, alarm_level_cm,
                             flow_m3s, flow_measured_at, water_temp_c, measured_at,
                             raw, row_hash, last_seen_at, is_active)
                        VALUES
                            (%(station_id)s, %(name)s, %(river)s, %(woj)s,
                             ST_SetSRID(ST_MakePoint(%(lon)s, %(lat)s), 4326),
                             %(water_level)s, %(warn_level)s, %(alarm_level)s,
                             %(flow)s, %(flow_dt)s, %(temp)s, %(measured_at)s,
                             %(raw)s, %(row_hash)s, %(run_ts)s, true)
                        ON CONFLICT (station_id) DO UPDATE SET
                            name = EXCLUDED.name,
                            river = EXCLUDED.river,
                            wojewodztwo = EXCLUDED.wojewodztwo,
                            geom = EXCLUDED.geom,
                            water_level_cm = EXCLUDED.water_level_cm,
                            warning_level_cm = EXCLUDED.warning_level_cm,
                            alarm_level_cm = EXCLUDED.alarm_level_cm,
                            flow_m3s = EXCLUDED.flow_m3s,
                            flow_measured_at = EXCLUDED.flow_measured_at,
                            water_temp_c = EXCLUDED.water_temp_c,
                            measured_at = EXCLUDED.measured_at,
                            raw = EXCLUDED.raw,
                            row_hash = EXCLUDED.row_hash,
                            last_seen_at = EXCLUDED.last_seen_at,
                            is_active = true
                        """,
                        {
                            "station_id": s["id_stacji"],
                            "name": s.get("stacja", ""),
                            "river": s.get("rzeka"),
                            "woj": s.get("wojewodztwo"),
                            "lon": lon,
                            "lat": lat,
                            "water_level": _int(s.get("stan_wody")),
                            "warn_level": _int(s.get("stan_ostrzegawczy")),
                            "alarm_level": _int(s.get("stan_alarmowy")),
                            "flow": _float(s.get("przeplyw")),
                            "flow_dt": s.get("przeplyw_data") or None,
                            "temp": _float(s.get("temperatura_wody")),
                            "measured_at": s.get("stan_wody_data_pomiaru") or None,
                            "raw": json.dumps(s, ensure_ascii=False),
                            "row_hash": _json_hash(s),
                            "run_ts": run_ts,
                        },
                    )
                    count += 1

                cur.execute(
                    "UPDATE hydro_stations SET is_active = false"
                    " WHERE last_seen_at < %s AND is_active",
                    (run_ts,),
                )
                deactivated = cur.rowcount

        logger.info("IMGW hydro: upserted %d stations, deactivated %d", count, deactivated)
        return {"status": "ok", "upserted": count, "deactivated": deactivated}
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Warnings (hydro + meteo)
# ---------------------------------------------------------------------------


def _hydro_warning_key(item: dict) -> str:
    biuro = item.get("biuro", "")
    biuro_hash = hashlib.md5(biuro.encode()).hexdigest()[:8]
    numer = item.get("numer", "0")
    year_str = (item.get("opublikowano") or "0000")[:4]
    return f"hydro:{year_str}:{biuro_hash}:{numer}"


def _flatten_area_codes(item: dict) -> list[str]:
    codes = []
    for obszar in item.get("obszary", []):
        codes.extend(obszar.get("kod_zlewni", []))
    return codes


def _flatten_voivodeships(item: dict) -> list[str]:
    return [o.get("wojewodztwo", "") for o in item.get("obszary", []) if o.get("wojewodztwo")]


def _flatten_area_descriptions(item: dict) -> list[str]:
    return [o.get("opis", "") for o in item.get("obszary", []) if o.get("opis")]


def _upsert_warnings(cur, source: str, items: list[dict], run_ts):
    count = 0
    for it in items:
        if source == "hydro":
            key = _hydro_warning_key(it)
            title = it.get("zdarzenie", "")
            severity = it.get("stopień") or it.get("stopien")
            valid_from = it.get("data_od")
            valid_to = it.get("data_do")
            published = it.get("opublikowano")
            issuer = it.get("biuro")
            warning_number = it.get("numer")
            body = it.get("przebieg")
            comment = it.get("komentarz")
            area_codes = _flatten_area_codes(it)
            voivodeships = _flatten_voivodeships(it)
            area_descriptions = _flatten_area_descriptions(it)
        else:
            key = f"meteo:{it.get('id', '')}"
            title = it.get("nazwa_zdarzenia", "")
            severity = it.get("stopien")
            valid_from = it.get("obowiazuje_od")
            valid_to = it.get("obowiazuje_do")
            published = it.get("opublikowano")
            issuer = it.get("biuro")
            warning_number = None
            body = it.get("tresc")
            comment = it.get("komentarz")
            area_codes = it.get("teryt", [])
            voivodeships = None
            area_descriptions = None

        try:
            severity_int = int(severity) if severity is not None else None
        except (ValueError, TypeError):
            severity_int = None

        try:
            prob = int(it.get("prawdopodobienstwo", "")) if it.get("prawdopodobienstwo") else None
        except (ValueError, TypeError):
            prob = None

        if valid_to == "9999-12-31 23:59:59":
            valid_to = None

        cur.execute(
            """
            INSERT INTO imgw_warnings
                (warning_key, source, title, severity, probability_pct,
                 valid_from, valid_to, published_at, issuer, warning_number,
                 body, comment, area_codes, voivodeships, area_descriptions,
                 raw, row_hash, last_seen_at, is_active)
            VALUES
                (%(key)s, %(source)s, %(title)s, %(severity)s, %(prob)s,
                 %(valid_from)s, %(valid_to)s, %(published)s, %(issuer)s, %(warning_number)s,
                 %(body)s, %(comment)s, %(area_codes)s, %(voivodeships)s, %(area_descriptions)s,
                 %(raw)s, %(row_hash)s, %(run_ts)s, true)
            ON CONFLICT (warning_key) DO UPDATE SET
                title = EXCLUDED.title,
                severity = EXCLUDED.severity,
                probability_pct = EXCLUDED.probability_pct,
                valid_from = EXCLUDED.valid_from,
                valid_to = EXCLUDED.valid_to,
                published_at = EXCLUDED.published_at,
                issuer = EXCLUDED.issuer,
                warning_number = EXCLUDED.warning_number,
                body = EXCLUDED.body,
                comment = EXCLUDED.comment,
                area_codes = EXCLUDED.area_codes,
                voivodeships = EXCLUDED.voivodeships,
                area_descriptions = EXCLUDED.area_descriptions,
                raw = EXCLUDED.raw,
                row_hash = EXCLUDED.row_hash,
                last_seen_at = EXCLUDED.last_seen_at,
                is_active = true
            """,
            {
                "key": key,
                "source": source,
                "title": title,
                "severity": severity_int,
                "prob": prob,
                "valid_from": valid_from or None,
                "valid_to": valid_to or None,
                "published": published or None,
                "issuer": issuer,
                "warning_number": warning_number,
                "body": body,
                "comment": comment,
                "area_codes": area_codes,
                "voivodeships": voivodeships,
                "area_descriptions": area_descriptions,
                "raw": json.dumps(it, ensure_ascii=False),
                "row_hash": _json_hash(it),
                "run_ts": run_ts,
            },
        )
        count += 1
    return count


@app.task(name="app.sources.imgw.fetch_imgw_warnings", bind=True, max_retries=2)
def fetch_imgw_warnings(self):
    results = {}

    for source, url in [
        ("hydro", settings.imgw_warnings_hydro_url),
        ("meteo", settings.imgw_warnings_meteo_url),
    ]:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=30)
            if resp.status_code == 404:
                results[source] = {"status": "no_warnings", "count": 0}
                continue
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as exc:
            logger.error("Failed to fetch IMGW %s warnings: %s", source, exc)
            results[source] = {"status": "error", "error": str(exc)}
            continue

        if isinstance(data, dict) and "message" in data:
            results[source] = {"status": "no_warnings", "count": 0}
            continue

        if not isinstance(data, list):
            results[source] = {"status": "unexpected_format"}
            continue

        conn = get_conn()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT now() AS ts")
                    run_ts = cur.fetchone()["ts"]

                    count = _upsert_warnings(cur, source, data, run_ts)

                    cur.execute(
                        """UPDATE imgw_warnings SET is_active = false
                           WHERE source = %s AND last_seen_at < %s AND is_active""",
                        (source, run_ts),
                    )
                    deactivated = cur.rowcount

            results[source] = {
                "status": "ok",
                "upserted": count,
                "deactivated": deactivated,
            }
            logger.info("IMGW %s warnings: upserted %d, deactivated %d", source, count, deactivated)
        finally:
            conn.close()

    return results
