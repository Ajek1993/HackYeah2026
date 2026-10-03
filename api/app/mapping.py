"""Database rows -> response shapes from docs_ai/api-contract.md."""

from typing import Any

from app.envelope import iso

SOURCES = {
    "shelters": ("Punkty schronienia (KG PSP, dane.gov.pl)", "https://dane.gov.pl"),
    "imgw": ("IMGW", "https://danepubliczne.imgw.pl/"),
    "tauron": ("Tauron Dystrybucja", "https://www.tauron-dystrybucja.pl/wylaczenia"),
    "gios": ("GIOŚ", "https://powietrze.gios.gov.pl/"),
    "airly": ("Airly", "https://airly.org/map/pl/"),
}

# Order matters: the first matching keyword in the warning title wins
WARNING_KINDS = [
    ("susz", "drought"),
    ("wezbr", "flood"),
    ("powód", "flood"),
    ("roztop", "flood"),
    ("burz", "storm"),
    ("wiatr", "wind"),
    ("upał", "heat"),
    ("mróz", "frost"),
    ("przymroz", "frost"),
    ("oblodz", "frost"),
    ("pożar", "fire"),
]

LEVEL_STATUS = {
    "alarmowy": "alarm",
    "ostrzegawczy": "warning",
    "normalny": "normal",
}


def plural(count: int, one: str, few: str, many: str) -> str:
    """Polish plural: 1 ostrzeżenie, 2 ostrzeżenia, 5 ostrzeżeń."""
    if count == 1:
        return one
    if 2 <= count % 10 <= 4 and not 12 <= count % 100 <= 14:
        return few
    return many


def shelter_type(row: dict) -> str:
    text = f"{row.get('name') or ''} {row.get('object_type') or ''}".lower()
    return "shelter" if "schron" in text else "hiding_place"


def shelter(row: dict) -> dict[str, Any]:
    item = {
        "id": row["shelter_id"],
        "name": row["name"],
        "address": row.get("address") or "",
        "lat": row["lat"],
        "lon": row["lon"],
        "capacity": None,  # not published in the source data
        "type": shelter_type(row),
        "availability": row.get("availability"),
    }
    if row.get("distance_m") is not None:
        item["distance_m"] = row["distance_m"]
    return item


def warning_kind(title: str) -> str:
    lowered = title.lower()
    return next((kind for keyword, kind in WARNING_KINDS if keyword in lowered), "other")


def warning_level(severity: int | None) -> int:
    # IMGW returns -1 for hydrological drought; treat it as the lowest level
    if severity is None or severity < 1:
        return 1
    return min(severity, 3)


def warning(row: dict) -> dict[str, Any]:
    areas = [a.strip() for a in row.get("area_descriptions") or [] if a and a.strip()]
    return {
        "id": row["warning_key"],
        # Demo scenarios set the kind explicitly (e.g. bomb_threat, absent from IMGW titles)
        "kind": row.get("kind") or warning_kind(row["title"]),
        "level": warning_level(row.get("severity")),
        "title": row["title"],
        "description": row.get("body") or "",
        "area": "; ".join(areas) if areas else "Kraków",
        "valid_from": iso(row.get("valid_from")),
        "valid_to": iso(row.get("valid_to")),
        "geometry": row.get("geometry"),
    }


def water_level(row: dict) -> dict[str, Any]:
    river = row.get("river")
    return {
        "station": row["name"],
        "river": None if river in (None, "", "-") else river,
        "lat": row["lat"],
        "lon": row["lon"],
        "level_cm": row.get("water_level_cm"),
        "warning_cm": row.get("warning_level_cm"),
        "alarm_cm": row.get("alarm_level_cm"),
        "status": LEVEL_STATUS.get(row.get("level_status") or "", "unknown"),
        "trend": None,  # no measurement history is stored
        "measured_at": iso(row.get("measured_at")),
    }


def power_outage(row: dict) -> dict[str, Any]:
    return {
        "id": row["id"],
        "planned": row.get("outage_kind") == "planowane",
        "area": row.get("message") or "",
        "start": iso(row.get("start_at")),
        "end": iso(row.get("end_at")),
        "lat": row.get("lat"),
        "lon": row.get("lon"),
    }


def air_quality(row: dict) -> dict[str, Any]:
    return {
        "station": row["station_name"],
        "index": row.get("index_level"),
        "index_label": row.get("index_label"),
        "pm25": float(row["pm25"]) if row.get("pm25") is not None else None,
        "pm10": float(row["pm10"]) if row.get("pm10") is not None else None,
        "measured_at": iso(row.get("measured_at")),
    }
