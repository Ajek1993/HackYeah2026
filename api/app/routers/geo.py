from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.nominatim import Nominatim, district, is_krakow_address, short_name
from app.repo import Repo, get_repo

router = APIRouter()

RepoDep = Annotated[Repo, Depends(get_repo)]


def get_nominatim(request: Request) -> Nominatim:
    return request.app.state.nominatim


NominatimDep = Annotated[Nominatim, Depends(get_nominatim)]


def _not_found(query: str | None) -> dict:
    return {
        "query": query,
        "found": False,
        "lat": None,
        "lon": None,
        "display_name": None,
        "district": None,
        "in_krakow": None,
    }


async def _place(repo: Repo, query: str | None, place: dict | None) -> dict:
    if not place or place.get("lat") is None or place.get("lon") is None:
        return _not_found(query)
    lat, lon = float(place["lat"]), float(place["lon"])
    inside = await repo.point_in_krakow(lat, lon)
    return {
        "query": query,
        "found": True,
        "lat": lat,
        "lon": lon,
        "display_name": short_name(place),
        "district": district(place),
        "in_krakow": inside if inside is not None else is_krakow_address(place),
    }


@router.get("/geocode")
async def geocode(
    repo: RepoDep,
    nominatim: NominatimDep,
    q: Annotated[str, Query(min_length=2, max_length=200)],
) -> dict:
    try:
        place = await nominatim.search(q.strip())
    except httpx.HTTPError as exc:
        raise HTTPException(503, "geocoder_unavailable") from exc
    return await _place(repo, q, place)


@router.get("/reverse")
async def reverse(
    repo: RepoDep,
    nominatim: NominatimDep,
    lat: Annotated[float, Query(ge=-90, le=90, allow_inf_nan=False)],
    lon: Annotated[float, Query(ge=-180, le=180, allow_inf_nan=False)],
) -> dict:
    try:
        place = await nominatim.reverse(lat, lon)
    except httpx.HTTPError as exc:
        raise HTTPException(503, "geocoder_unavailable") from exc
    if place:
        # Report the user's own point, not the centre of the matched address
        place = {**place, "lat": lat, "lon": lon}
    return await _place(repo, None, place)
