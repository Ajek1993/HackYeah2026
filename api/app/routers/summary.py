from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends

from app import mapping
from app.envelope import is_stale
from app.repo import Repo, get_repo
from app.routers.data import KRAKOW_CENTER

router = APIRouter()

RepoDep = Annotated[Repo, Depends(get_repo)]

AIR_LABELS = {
    "very_good": "bardzo dobra",
    "good": "dobra",
    "moderate": "umiarkowana",
    "sufficient": "dostateczna",
    "bad": "zła",
    "very_bad": "bardzo zła",
}
AIR_STATUS = {
    "very_good": "ok",
    "good": "ok",
    "moderate": "warning",
    "sufficient": "warning",
    "bad": "danger",
    "very_bad": "danger",
}


def tile(kind: str, status: str, headline: str, source: str, updated_at: datetime | None) -> dict:
    if updated_at is None:
        status, headline = "no_data", "Brak danych"
    return {
        "kind": kind,
        "status": status,
        "headline": headline,
        "source": source,
        "updated_at": mapping.iso(updated_at),
        "is_stale": is_stale(updated_at),
        "is_simulated": False,
    }


def warnings_tile(rows: list[dict], updated_at: datetime | None) -> dict:
    source = mapping.SOURCES["imgw"][0]
    if not rows:
        return tile("warnings", "ok", "Brak ostrzeżeń IMGW dla Krakowa", source, updated_at)
    count = len(rows)
    levels = [mapping.warning_level(r.get("severity")) for r in rows]
    noun = mapping.plural(count, "ostrzeżenie", "ostrzeżenia", "ostrzeżeń")
    headline = f"{count} {noun}, m.in. {rows[0]['title'].lower()}"
    return tile(
        "warnings", "danger" if max(levels) >= 2 else "warning", headline, source, updated_at
    )


def water_tile(rows: list[dict], updated_at: datetime | None) -> dict:
    source = mapping.SOURCES["imgw"][0]
    # Main gauge for the city: the Vistula station closest to the centre
    station = next((r for r in rows if r.get("river") == "Wisła"), rows[0] if rows else None)
    if station is None or station.get("water_level_cm") is None:
        return tile("water", "no_data", "Brak danych", source, None)
    status = {"alarmowy": "danger", "ostrzegawczy": "warning"}.get(
        station.get("level_status") or "", "ok"
    )
    headline = f"{station.get('river') or station['name']}: {station['water_level_cm']} cm"
    if station.get("warning_level_cm"):
        headline += f" (ostrzegawczy {station['warning_level_cm']})"
    return tile("water", status, headline, source, updated_at)


def air_tile(row: dict | None, updated_at: datetime | None) -> dict:
    if row is None or row.get("index_level") is None:
        return tile("air", "no_data", "Brak danych", mapping.SOURCES["gios"][0], None)
    level = row["index_level"]
    headline = f"Jakość powietrza: {AIR_LABELS[level]}"
    return tile("air", AIR_STATUS[level], headline, mapping.SOURCES[row["provider"]][0], updated_at)


def power_tile(rows: list[dict], updated_at: datetime | None) -> dict:
    source = mapping.SOURCES["tauron"][0]
    if not rows:
        return tile("power", "ok", "Brak wyłączeń prądu w Krakowie", source, updated_at)
    count = len(rows)
    noun = mapping.plural(count, "wyłączenie", "wyłączenia", "wyłączeń")
    return tile("power", "warning", f"{count} {noun} prądu", source, updated_at)


@router.get("/summary")
async def summary(repo: RepoDep) -> dict:
    air = await repo.freshest_air_quality(*KRAKOW_CENTER)
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "demo_scenario": None,
        "tiles": [
            warnings_tile(await repo.krakow_warnings(), await repo.last_fetch("imgw_warnings")),
            water_tile(await repo.krakow_water_levels(), await repo.last_fetch("hydro_stations")),
            air_tile(air, air["last_seen_at"] if air else None),
            power_tile(await repo.krakow_power_outages(), await repo.last_fetch("power_outages")),
        ],
    }
