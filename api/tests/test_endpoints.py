import pytest
from fastapi.testclient import TestClient

from app.envelope import iso
from app.main import app
from app.repo import get_repo
from tests.fakes import FRESH, STALE, FakeRepo

client = TestClient(app)


@pytest.fixture
def repo():
    fake = FakeRepo()
    app.dependency_overrides[get_repo] = lambda: fake
    yield fake
    app.dependency_overrides.clear()


ENVELOPE_KEYS = {"source", "source_url", "updated_at", "is_stale", "is_simulated", "data"}


def test_shelters_returns_contract_envelope(repo):
    body = client.get("/shelters").json()

    assert set(body) == ENVELOPE_KEYS
    assert body["source"].startswith("Punkty schronienia")
    assert body["is_stale"] is False
    assert body["is_simulated"] is False
    shelter = body["data"][0]
    assert shelter == {
        "id": "OZO-TEST1",
        "name": "Miejsce ochronne",
        "address": "ul. Testowa 2, Kraków",
        "lat": 50.034,
        "lon": 19.92,
        "capacity": None,
        "type": "hiding_place",
        "availability": "Całodobowa",
    }


def test_nearest_shelters_passes_point_and_limit(repo):
    body = client.get("/shelters/nearest", params={"lat": 50.03, "lon": 19.92, "limit": 1}).json()

    assert repo.calls[-1] == ("nearest_shelters", 50.03, 19.92, 1)
    assert body["data"][0]["distance_m"] == 412


def test_nearest_shelters_defaults_to_three(repo):
    client.get("/shelters/nearest", params={"lat": 50.03, "lon": 19.92})

    assert repo.calls[-1][-1] == 3


@pytest.mark.parametrize(
    "params",
    [
        {"lat": 50.03},
        {"lat": 91, "lon": 19.9},
        {"lat": 50.03, "lon": 19.92, "limit": 0},
        {"lat": 50.03, "lon": 19.92, "limit": 11},
        {"lat": "nan", "lon": 19.92},
    ],
)
def test_nearest_shelters_validates_input(repo, params):
    assert client.get("/shelters/nearest", params=params).status_code == 422


def test_stale_source_is_marked(repo):
    repo.fetched["shelters"] = STALE

    assert client.get("/shelters").json()["is_stale"] is True


def test_never_fetched_source_returns_no_data(repo):
    repo.fetched["power_outages"] = None

    body = client.get("/power-outages").json()

    assert body["data"] is None
    assert body["updated_at"] is None


def test_warnings_are_mapped(repo):
    warning = client.get("/warnings").json()["data"][0]

    assert warning["kind"] == "drought"
    assert warning["level"] == 1
    assert warning["area"].startswith("małopolskie, zlewnie Rudawy")
    assert warning["valid_to"] is None
    assert warning["geometry"] is None


def test_water_levels_are_mapped(repo):
    stations = client.get("/water-levels").json()["data"]

    assert stations[1] == {
        "station": "Kraków - Bielany",
        "river": "Wisła",
        "lat": 50.04,
        "lon": 19.84,
        "level_cm": 148,
        "warning_cm": 370,
        "alarm_cm": 520,
        "status": "normal",
        "trend": None,
        "measured_at": iso(FRESH),
    }


def test_power_outages_are_mapped(repo):
    outage = client.get("/power-outages").json()["data"][0]

    assert outage["planned"] is True
    assert outage["area"] == "Kraków ul. Testowa 1-10"


def test_air_quality_uses_provider_of_freshest_reading(repo):
    repo.air = {**repo.air, "provider": "airly"}

    body = client.get("/air-quality", params={"lat": 50.06, "lon": 19.94}).json()

    assert body["source"] == "Airly"
    assert body["data"]["index"] == "good"
    assert repo.calls[-1] == ("freshest_air_quality", 50.06, 19.94)


def test_air_quality_without_point_uses_city_centre(repo):
    client.get("/air-quality")

    assert repo.calls[-1] == ("freshest_air_quality", 50.0614, 19.9366)


def test_air_quality_without_reading_returns_no_data(repo):
    repo.air = None

    body = client.get("/air-quality").json()

    assert body["data"] is None
    assert body["source"] == "GIOŚ"


def test_guide_returns_official_steps():
    body = client.get("/guide/flood").json()

    assert body["source"].startswith("Poradnik bezpieczeństwa")
    assert body["is_stale"] is False
    data = body["data"]
    assert data["title"] == "Powódź"
    assert data["before"] and data["during"]
    assert {"name": "Numer alarmowy", "number": "112"} in data["emergency_numbers"]
    assert data["source_url"].startswith("https://www.gov.pl/")


def test_guide_topic_not_covered_by_the_guide_returns_null():
    assert client.get("/guide/drought").json()["data"] is None


@pytest.mark.parametrize("topic", ["zombies", "..%2F..%2Fetc%2Fpasswd", "FLOOD"])
def test_guide_rejects_unknown_topics(topic):
    assert client.get(f"/guide/{topic}").status_code == 404


def test_summary_tiles(repo):
    body = client.get("/summary").json()

    tiles = {tile["kind"]: tile for tile in body["tiles"]}
    assert list(tiles) == ["warnings", "water", "air", "power"]
    assert tiles["warnings"]["status"] == "warning"
    assert tiles["warnings"]["headline"] == "1 ostrzeżenie, m.in. susza hydrologiczna"
    assert tiles["water"]["status"] == "ok"
    assert tiles["water"]["headline"] == "Wisła: 148 cm (ostrzegawczy 370)"
    assert tiles["air"]["headline"] == "Jakość powietrza: dobra"
    assert tiles["power"]["headline"] == "1 wyłączenie prądu"
    assert body["demo_scenario"] is None


def test_summary_marks_missing_sources_as_no_data(repo):
    repo.fetched["power_outages"] = None
    repo.air = None
    repo.water = []

    tiles = {tile["kind"]: tile for tile in client.get("/summary").json()["tiles"]}

    for kind in ("power", "air", "water"):
        assert tiles[kind]["status"] == "no_data"
        assert tiles[kind]["headline"] == "Brak danych"


def test_summary_escalates_water_and_warning_levels(repo):
    repo.water = [{**repo.water[1], "level_status": "alarmowy", "water_level_cm": 530}]
    repo.warnings = [{**repo.warnings[0], "severity": 2, "title": "Burze z gradem"}] * 3
    repo.outages = []

    tiles = {tile["kind"]: tile for tile in client.get("/summary").json()["tiles"]}

    assert tiles["water"]["status"] == "danger"
    assert tiles["warnings"]["status"] == "danger"
    assert tiles["warnings"]["headline"] == "3 ostrzeżenia, m.in. burze z gradem"
    assert tiles["power"]["status"] == "ok"


def test_timestamps_are_in_krakow_time(repo):
    updated = client.get("/shelters").json()["updated_at"]

    assert updated.endswith(("+02:00", "+01:00"))
