from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app import mapping
from app.envelope import envelope
from app.repo import Repo, get_repo

router = APIRouter()

RepoDep = Annotated[Repo, Depends(get_repo)]
# Poland with a margin; every handler also accepts a missing point (whole Kraków)
Lat = Annotated[float | None, Query(ge=49.0, le=55.0, allow_inf_nan=False)]
Lon = Annotated[float | None, Query(ge=14.0, le=24.2, allow_inf_nan=False)]

KRAKOW_CENTER = (50.0614, 19.9366)


@router.get("/shelters")
async def shelters(repo: RepoDep) -> dict:
    name, url = mapping.SOURCES["shelters"]
    rows = await repo.shelters_in_krakow()
    return envelope(
        name, url, await repo.last_fetch("shelters"), [mapping.shelter(r) for r in rows]
    )


@router.get("/shelters/nearest")
async def nearest_shelters(
    repo: RepoDep,
    lat: Annotated[float, Query(ge=49.0, le=55.0, allow_inf_nan=False)],
    lon: Annotated[float, Query(ge=14.0, le=24.2, allow_inf_nan=False)],
    limit: Annotated[int, Query(ge=1, le=10)] = 3,
) -> dict:
    name, url = mapping.SOURCES["shelters"]
    rows = await repo.nearest_shelters(lat, lon, limit)
    return envelope(
        name, url, await repo.last_fetch("shelters"), [mapping.shelter(r) for r in rows]
    )


@router.get("/warnings")
async def warnings(repo: RepoDep, lat: Lat = None, lon: Lon = None) -> dict:
    # Kraków-wide: IMGW warnings cover catchments and districts, not single addresses
    name, url = mapping.SOURCES["imgw"]
    rows = await repo.krakow_warnings()
    return envelope(
        name, url, await repo.last_fetch("imgw_warnings"), [mapping.warning(r) for r in rows]
    )


@router.get("/water-levels")
async def water_levels(repo: RepoDep) -> dict:
    name, url = mapping.SOURCES["imgw"]
    rows = await repo.krakow_water_levels()
    return envelope(
        name, url, await repo.last_fetch("hydro_stations"), [mapping.water_level(r) for r in rows]
    )


@router.get("/power-outages")
async def power_outages(repo: RepoDep, lat: Lat = None, lon: Lon = None) -> dict:
    name, url = mapping.SOURCES["tauron"]
    rows = await repo.krakow_power_outages()
    return envelope(
        name, url, await repo.last_fetch("power_outages"), [mapping.power_outage(r) for r in rows]
    )


@router.get("/air-quality")
async def air_quality(repo: RepoDep, lat: Lat = None, lon: Lon = None) -> dict:
    point = (lat, lon) if lat is not None and lon is not None else KRAKOW_CENTER
    row = await repo.freshest_air_quality(*point)
    if row is None:
        name, url = mapping.SOURCES["gios"]
        return envelope(name, url, await repo.last_fetch("air_quality_readings"), None)
    name, url = mapping.SOURCES[row["provider"]]
    return envelope(name, url, row["last_seen_at"], mapping.air_quality(row))
