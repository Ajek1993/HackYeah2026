import json
from datetime import UTC, datetime

import httpx
import pytest

from app.tools import GUIDE_TOPICS, TOOL_DEFINITIONS, ToolExecutor

NOW = datetime(2026, 10, 4, 12, 0, tzinfo=UTC)
FRESH = "2026-10-04T13:30:00+02:00"  # 11:30 UTC
STALE = "2026-10-04T07:00:00+02:00"  # 05:00 UTC -> 7h old


def envelope(data, *, source="IMGW", updated_at=FRESH, is_stale=False, is_simulated=False):
    return {
        "source": source,
        "source_url": "https://danepubliczne.imgw.pl/",
        "updated_at": updated_at,
        "is_stale": is_stale,
        "is_simulated": is_simulated,
        "data": data,
    }


def make_executor(handler) -> tuple[ToolExecutor, list[httpx.Request]]:
    requests: list[httpx.Request] = []

    def recording(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return handler(request)

    client = httpx.Client(base_url="http://api.test", transport=httpx.MockTransport(recording))
    return ToolExecutor(client, now=NOW), requests


def respond(payload, status: int = 200):
    return lambda request: httpx.Response(status, json=payload)


def test_tool_definitions_cover_all_agent_tools():
    names = {tool["function"]["name"] for tool in TOOL_DEFINITIONS}

    assert names == {
        "geocode",
        "get_warnings",
        "get_water_levels",
        "get_air_quality",
        "get_power_outages",
        "find_nearest_shelter",
        "get_guide",
    }


def test_geocode_passes_query_and_returns_payload():
    payload = {"query": "Kobierzyńska 1, Kraków", "found": True, "in_krakow": True}
    executor, requests = make_executor(respond(payload))

    result = executor.execute("geocode", json.dumps({"query": "Kobierzyńska 1, Kraków"}))

    assert requests[0].url.path == "/geocode"
    assert requests[0].url.params["q"] == "Kobierzyńska 1, Kraków"
    assert result.payload == payload
    assert result.sources == []


def test_warnings_with_point_returns_source_metadata():
    executor, requests = make_executor(respond(envelope([{"kind": "flood", "level": 2}])))

    result = executor.execute("get_warnings", {"lat": 50.03, "lon": 19.92})

    assert requests[0].url.path == "/warnings"
    assert requests[0].url.params["lat"] == "50.03"
    assert len(result.sources) == 1
    source = result.sources[0]
    assert (source.name, source.updated_at, source.is_stale) == ("IMGW", FRESH, False)
    assert json.loads(result.content)["data"][0]["kind"] == "flood"


def test_warnings_without_point_queries_whole_city():
    executor, requests = make_executor(respond(envelope([])))

    executor.execute("get_warnings", {})

    assert "lat" not in requests[0].url.params


@pytest.mark.parametrize(
    ("name", "args", "path"),
    [
        ("get_water_levels", {}, "/water-levels"),
        ("get_air_quality", {"lat": 50.06, "lon": 19.94}, "/air-quality"),
        ("get_power_outages", {"lat": 50.06, "lon": 19.94}, "/power-outages"),
        ("find_nearest_shelter", {"lat": 50.06, "lon": 19.94}, "/shelters/nearest"),
        ("get_guide", {"topic": "flood"}, "/guide/flood"),
    ],
)
def test_tools_call_expected_endpoints(name, args, path):
    executor, requests = make_executor(respond(envelope({})))

    result = executor.execute(name, args)

    assert requests[0].url.path == path
    assert len(result.sources) == 1


def test_nearest_shelter_defaults_to_three_results():
    executor, requests = make_executor(respond(envelope([])))

    executor.execute("find_nearest_shelter", {"lat": 50.06, "lon": 19.94})

    assert requests[0].url.params["limit"] == "3"


def test_stale_reading_gets_age_in_hours():
    stale = envelope({"index": "bad"}, updated_at=STALE, is_stale=True)
    executor, _ = make_executor(respond(stale))

    result = executor.execute("get_air_quality", {"lat": 50.06, "lon": 19.94})

    content = json.loads(result.content)
    assert content["is_stale"] is True
    assert content["age_hours"] == 7
    assert result.sources[0].is_stale is True


def test_fresh_reading_has_no_age_field():
    executor, _ = make_executor(respond(envelope({"index": "good"})))

    result = executor.execute("get_air_quality", {})

    assert "age_hours" not in json.loads(result.content)


def test_missing_data_is_marked_no_data():
    executor, _ = make_executor(respond(envelope(None)))

    result = executor.execute("get_power_outages", {})

    content = json.loads(result.content)
    assert content["data"] is None
    assert content["note"] == "Brak danych"
    assert result.sources[0].name == "IMGW"


def test_simulated_reading_is_flagged_in_sources():
    executor, _ = make_executor(respond(envelope([], is_simulated=True)))

    result = executor.execute("get_warnings", {})

    assert result.sources[0].is_simulated is True


def test_api_error_returns_no_data_instead_of_raising():
    executor, _ = make_executor(respond({"detail": "boom"}, status=500))

    result = executor.execute("get_water_levels", {})

    assert json.loads(result.content) == {"error": "Brak danych"}
    assert result.sources == []


def test_api_unreachable_returns_no_data():
    def unreachable(request):
        raise httpx.ConnectError("connection refused", request=request)

    executor, _ = make_executor(unreachable)

    result = executor.execute("get_warnings", {})

    assert json.loads(result.content) == {"error": "Brak danych"}


def test_unknown_guide_topic_is_rejected_without_request():
    executor, requests = make_executor(respond(envelope({})))

    result = executor.execute("get_guide", {"topic": "zombies"})

    assert requests == []
    assert "flood" in json.loads(result.content)["error"]
    assert set(GUIDE_TOPICS) >= {"flood", "power_outage", "bomb_threat"}


@pytest.mark.parametrize(
    ("name", "arguments"),
    [
        ("get_weather_on_mars", {}),
        ("geocode", "{not json"),
        ("geocode", {}),
        ("find_nearest_shelter", {"lat": "abc", "lon": 19.9}),
    ],
)
def test_invalid_calls_return_error(name, arguments):
    executor, requests = make_executor(respond(envelope({})))

    result = executor.execute(name, arguments)

    assert "error" in json.loads(result.content)
    assert requests == []
