from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.demo.scenarios import SCENARIOS
from app.demo.state import DemoState, get_demo_state
from app.main import app
from app.repo import get_repo
from tests.fakes import FakeRepo

client = TestClient(app)
TOKEN = {"X-Demo-Token": "demo-secret"}


class Clock:
    def __init__(self) -> None:
        self.now = datetime(2026, 10, 4, 10, 0, tzinfo=UTC)

    def __call__(self) -> datetime:
        return self.now


@pytest.fixture
def clock():
    return Clock()


@pytest.fixture
def state(clock):
    demo = DemoState(clock)
    app.dependency_overrides[get_demo_state] = lambda: demo
    app.dependency_overrides[get_repo] = lambda: FakeRepo()
    yield demo
    app.dependency_overrides.clear()


@pytest.fixture
def demo_on(monkeypatch, state):
    monkeypatch.setattr(settings, "demo_mode", True)
    monkeypatch.setattr(settings, "demo_admin_token", "demo-secret")
    monkeypatch.setattr(settings, "demo_ttl_minutes", 30)
    return state


def test_lists_three_scenarios(demo_on):
    body = client.get("/demo/scenarios").json()

    assert body == [
        {"id": "flood", "title": "Powódź"},
        {"id": "power_outage", "title": "Brak prądu"},
        {"id": "bomb_threat", "title": "Atak bombowy"},
    ]


def test_activation_switches_warnings_to_simulated_data(demo_on):
    real = client.get("/warnings").json()
    assert real["is_simulated"] is False
    assert real["data"][0]["kind"] == "drought"

    response = client.post("/demo/activate/flood", headers=TOKEN)
    assert response.json() == {"active": "flood", "expires_at": "2026-10-04T12:30:00+02:00"}

    body = client.get("/warnings").json()
    assert body["is_simulated"] is True
    assert body["is_stale"] is False
    assert body["source"] == "IMGW (symulacja)"
    assert body["data"][0]["kind"] == "flood"
    assert body["data"][0]["level"] == 3


def test_bomb_threat_warning_and_real_shelters(demo_on):
    client.post("/demo/activate/bomb_threat", headers=TOKEN)

    body = client.get("/warnings").json()
    assert body["source"] == "RCB (symulacja)"
    assert body["data"][0]["kind"] == "bomb_threat"
    # Shelters stay real: the user is sent to an actual place
    shelters = client.get("/shelters/nearest", params={"lat": 50.03, "lon": 19.92}).json()
    assert shelters["is_simulated"] is False


@pytest.mark.parametrize("scenario_id", list(SCENARIOS))
def test_every_scenario_marks_all_data_endpoints(demo_on, scenario_id):
    client.post(f"/demo/activate/{scenario_id}", headers=TOKEN)

    for path in ("/warnings", "/water-levels", "/power-outages", "/air-quality"):
        body = client.get(path).json()
        assert body["is_simulated"] is True, path
        assert body["data"] is not None, path
    summary = client.get("/summary").json()
    assert summary["demo_scenario"] == scenario_id
    assert all(t["is_simulated"] and t["status"] != "no_data" for t in summary["tiles"])


def test_flood_raises_vistula_above_alarm(demo_on):
    client.post("/demo/activate/flood", headers=TOKEN)

    bielany = client.get("/water-levels").json()["data"][0]
    assert bielany["status"] == "alarm"
    assert bielany["level_cm"] > bielany["alarm_cm"]
    water = next(t for t in client.get("/summary").json()["tiles"] if t["kind"] == "water")
    assert water["status"] == "danger"


def test_power_outage_lists_unplanned_outages(demo_on):
    client.post("/demo/activate/power_outage", headers=TOKEN)

    outages = client.get("/power-outages").json()["data"]
    assert len(outages) == 3
    assert not any(o["planned"] for o in outages)


def test_deactivation_restores_real_data(demo_on):
    client.post("/demo/activate/flood", headers=TOKEN)

    assert client.post("/demo/deactivate", headers=TOKEN).json() == {
        "active": None,
        "expires_at": None,
    }
    assert client.get("/warnings").json()["is_simulated"] is False
    assert client.get("/summary").json()["demo_scenario"] is None


def test_active_reports_scenario_and_expiry(demo_on):
    assert client.get("/demo/active").json() == {"active": None, "expires_at": None}

    client.post("/demo/activate/power_outage", headers=TOKEN)

    assert client.get("/demo/active").json() == {
        "active": "power_outage",
        "expires_at": "2026-10-04T12:30:00+02:00",
    }


def test_scenario_expires_after_ttl(demo_on, clock):
    client.post("/demo/activate/flood", headers=TOKEN)
    clock.now += timedelta(minutes=29)
    assert client.get("/warnings").json()["is_simulated"] is True

    clock.now += timedelta(minutes=1)
    assert client.get("/warnings").json()["is_simulated"] is False


def test_unknown_scenario_is_404(demo_on):
    assert client.post("/demo/activate/meteor", headers=TOKEN).status_code == 404


@pytest.mark.parametrize("headers", [{}, {"X-Demo-Token": "wrong"}])
def test_switching_requires_token(demo_on, headers):
    assert client.post("/demo/activate/flood", headers=headers).status_code == 403
    assert client.post("/demo/deactivate", headers=headers).status_code == 403
    assert client.get("/warnings").json()["is_simulated"] is False


def test_empty_admin_token_blocks_switching(demo_on, monkeypatch):
    monkeypatch.setattr(settings, "demo_admin_token", "")

    response = client.post("/demo/activate/flood", headers={"X-Demo-Token": ""})
    assert response.status_code == 403


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", "/demo/scenarios"),
        ("get", "/demo/active"),
        ("post", "/demo/activate/flood"),
        ("post", "/demo/deactivate"),
    ],
)
def test_demo_endpoints_are_404_when_demo_mode_is_off(state, monkeypatch, method, path):
    monkeypatch.setattr(settings, "demo_mode", False)
    monkeypatch.setattr(settings, "demo_admin_token", "demo-secret")

    assert getattr(client, method)(path, headers=TOKEN).status_code == 404


def test_active_scenario_is_ignored_when_demo_mode_is_off(state, monkeypatch):
    state.activate("flood", timedelta(minutes=30))
    monkeypatch.setattr(settings, "demo_mode", False)

    assert client.get("/warnings").json()["is_simulated"] is False
    assert client.get("/summary").json()["demo_scenario"] is None
