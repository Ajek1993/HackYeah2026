"""Queries against the real PostGIS database; skipped when it is not reachable or empty."""

import asyncio

import psycopg
import pytest
from psycopg.rows import dict_row

from app.config import settings
from app.repo import Repo

DEBNIKI = (50.0335, 19.9205)


def _run(query):
    async def go():
        conn = await psycopg.AsyncConnection.connect(
            settings.database_url, row_factory=dict_row, connect_timeout=2
        )
        try:
            return await query(Repo(conn))
        finally:
            await conn.close()

    return asyncio.run(go())


def _database_ready() -> bool:
    try:
        with psycopg.connect(settings.database_url, connect_timeout=2) as conn:
            return conn.execute("SELECT count(*) FROM shelters").fetchone()[0] > 0
    except psycopg.Error:
        return False


pytestmark = pytest.mark.skipif(not _database_ready(), reason="PostGIS with data not available")


def test_nearest_shelter_for_debniki_is_close_and_sorted():
    rows = _run(lambda repo: repo.nearest_shelters(*DEBNIKI, 3))

    assert len(rows) == 3
    distances = [r["distance_m"] for r in rows]
    assert distances == sorted(distances)
    assert distances[0] < 2000


def test_point_in_krakow_uses_boundary():
    inside = _run(lambda repo: repo.point_in_krakow(*DEBNIKI))
    skawina = _run(lambda repo: repo.point_in_krakow(49.975, 19.828))

    if inside is None:
        pytest.skip("Kraków boundary not loaded")
    assert inside is True
    assert skawina is False


def test_krakow_queries_run():
    async def all_queries(repo):
        return (
            await repo.krakow_warnings(),
            await repo.krakow_water_levels(),
            await repo.krakow_power_outages(),
            await repo.last_fetch("shelters"),
        )

    warnings, water, outages, fetched = _run(all_queries)

    assert isinstance(warnings, list)
    assert fetched is not None
    assert all(abs(s["lat"] - 50.06) < 0.2 for s in water)
    assert all(o["lat"] is not None for o in outages)
