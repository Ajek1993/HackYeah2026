from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
import requests

from app.sources import outage_streets
from app.sources.outage_streets import (
    MAX_LOOKUPS_PER_RUN,
    locate_streets,
    nominatim_point,
    street_queries,
)

NOW = datetime(2026, 10, 3, 12, 0, tzinfo=UTC)
SZUWAROWA = (50.0301, 19.9102)


@pytest.mark.parametrize(
    ("message", "queries"),
    [
        (
            "Krakowie ul. Szuwarowa 4, Kobierzyńska od 132 do 154",
            ["Szuwarowa 4, Kraków", "Szuwarowa, Kraków"],
        ),
        (
            "Kraków osiedle Wysokie 2 klatka 1.",
            ["osiedle Wysokie 2, Kraków", "osiedle Wysokie, Kraków"],
        ),
        ("Kraków ul. Dąbrowskiego 10,14", ["Dąbrowskiego 10, Kraków", "Dąbrowskiego, Kraków"]),
        (
            "Kraków ulica Sawy Calińskiego 130.",
            ["Sawy Calińskiego 130, Kraków", "Sawy Calińskiego, Kraków"],
        ),
        ("Kraków ul. Na Mostkach 3CD, 3E/1", ["Na Mostkach 3CD, Kraków", "Na Mostkach, Kraków"]),
        ("Kraków ul. Testowa 1-10", ["Testowa 1, Kraków", "Testowa, Kraków"]),
        ("Kraków W części miejscowości Bieżanów", []),
        # Villages in the same power district are never looked up as Kraków streets
        ("Nowa Góra do strony Czernej ul Wąska", []),
        ("Petrażyckiego", []),
        ("W części  miejscowości Golkowice w kierunku Ochojno.", []),
        ("", []),
    ],
)
def test_street_queries_take_the_first_address(message, queries):
    assert street_queries(message) == queries


def _conn(cache_rows=()):
    cur = MagicMock()
    cur.fetchall.return_value = list(cache_rows)
    conn = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cur
    return conn, cur


def _cached(query, point, fetched_at=NOW):
    lat, lon = point or (None, None)
    return {"query": query, "found": point is not None, "lat": lat, "lon": lon,
            "fetched_at": fetched_at}  # fmt: skip


def _inserted(cur):
    return [c.args[1] for c in cur.execute.call_args_list if "INSERT" in c.args[0]]


def test_geocodes_the_first_address_and_caches_it():
    conn, cur = _conn()
    lookup = MagicMock(return_value=SZUWAROWA)

    points = locate_streets(conn, ["Krakowie ul. Szuwarowa 4, Kobierzyńska"], lookup, now=NOW)

    assert points == {"Krakowie ul. Szuwarowa 4, Kobierzyńska": SZUWAROWA}
    lookup.assert_called_once_with("Szuwarowa 4, Kraków")
    assert _inserted(cur) == [("Szuwarowa 4, Kraków", True, *SZUWAROWA)]


def test_falls_back_to_the_street_without_number():
    conn, cur = _conn()
    lookup = MagicMock(side_effect=[None, SZUWAROWA])

    points = locate_streets(conn, ["Kraków ul. Szuwarowa 999"], lookup, sleep=lambda _: None)

    assert points == {"Kraków ul. Szuwarowa 999": SZUWAROWA}
    assert ("Szuwarowa 999, Kraków", False, None, None) in _inserted(cur)


def test_uses_the_cache_without_calling_nominatim():
    conn, cur = _conn([_cached("Szuwarowa 4, Kraków", SZUWAROWA)])
    lookup = MagicMock()

    points = locate_streets(conn, ["Kraków ul. Szuwarowa 4"], lookup, now=NOW)

    assert points == {"Kraków ul. Szuwarowa 4": SZUWAROWA}
    lookup.assert_not_called()
    assert _inserted(cur) == []


def test_retries_a_miss_only_after_a_week():
    message = "Kraków ul. Petrażyckiego"
    recent = _cached("Petrażyckiego, Kraków", None, NOW - timedelta(days=1))
    old = _cached("Petrażyckiego, Kraków", None, NOW - timedelta(days=8))
    lookup = MagicMock(return_value=SZUWAROWA)

    assert locate_streets(_conn([recent])[0], [message], lookup, now=NOW) == {}
    lookup.assert_not_called()

    assert locate_streets(_conn([old])[0], [message], lookup, now=NOW) == {message: SZUWAROWA}


def test_caps_lookups_per_run_and_waits_between_them():
    messages = [f"Kraków ul. Ulica{chr(65 + i)} 1" for i in range(MAX_LOOKUPS_PER_RUN + 5)]
    lookup = MagicMock(return_value=SZUWAROWA)
    sleep = MagicMock()

    points = locate_streets(_conn()[0], messages, lookup, sleep=sleep, now=NOW)

    assert lookup.call_count == MAX_LOOKUPS_PER_RUN
    assert len(points) == MAX_LOOKUPS_PER_RUN
    assert sleep.call_count == MAX_LOOKUPS_PER_RUN - 1


def test_geocoder_outage_stops_lookups_without_caching_a_miss():
    conn, cur = _conn()
    lookup = MagicMock(side_effect=requests.ConnectionError("down"))

    points = locate_streets(conn, ["Kraków ul. Litewska 23", "Kraków ul. Wrzosowa 117"], lookup)

    assert points == {}
    assert lookup.call_count == 1
    assert _inserted(cur) == []


def test_messages_without_a_street_skip_the_database():
    conn, _ = _conn()

    assert locate_streets(conn, ["W części miejscowości Golkowice"], MagicMock()) == {}
    conn.cursor.assert_not_called()


def _nominatim(payload):
    response = MagicMock()
    response.json.return_value = payload
    return response


@patch.object(outage_streets.requests, "get")
def test_nominatim_point_inside_krakow(mock_get):
    mock_get.return_value = _nominatim([{"lat": "50.0301", "lon": "19.9102"}])

    assert nominatim_point("Szuwarowa 4, Kraków") == SZUWAROWA
    params = mock_get.call_args.kwargs["params"]
    assert params["bounded"] == 1
    assert "User-Agent" in mock_get.call_args.kwargs["headers"]


@pytest.mark.parametrize(
    "payload",
    [[], [{"lat": "52.23", "lon": "21.01"}], [{"lat": "x"}], {"error": "bad"}],
)
@patch.object(outage_streets.requests, "get")
def test_nominatim_point_rejects_misses_and_places_outside_krakow(mock_get, payload):
    mock_get.return_value = _nominatim(payload)

    assert nominatim_point("Gdzieś, Kraków") is None
