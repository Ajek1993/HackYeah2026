import subprocess
import sys

from fastapi.testclient import TestClient

from app.main import app
from app.ratelimit import RateLimiter
from app.repo import get_repo
from app.routers import geo
from app.routers.geo import get_geocode_limiter, get_nominatim
from tests.fakes import FakeRepo


def test_docs_are_hidden_in_production():
    code = "from app.main import app; print(app.openapi_url, app.docs_url)"
    out = subprocess.run(
        [sys.executable, "-c", code],
        env={"APP_ENV": "production", "PATH": ""},
        capture_output=True,
        text=True,
        check=True,
    )
    assert out.stdout.split() == ["None", "None"]


def test_docs_are_available_in_development():
    assert app.openapi_url == "/openapi.json"


def test_geocode_is_rate_limited_per_client():
    limiter = RateLimiter(1)  # one instance shared by all requests of the test
    app.dependency_overrides[get_geocode_limiter] = lambda: limiter
    app.dependency_overrides[get_repo] = lambda: FakeRepo()
    app.dependency_overrides[get_nominatim] = lambda: None  # never reached: q fails validation
    try:
        client = TestClient(app)
        # The first call passes the limiter (and then fails validation), the second is limited
        assert client.get("/geocode", params={"q": "x"}).status_code == 422
        response = client.get("/geocode", params={"q": "x"})
        assert response.status_code == 429
        assert "Za dużo wyszukiwań" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()


def test_agent_with_internal_token_skips_the_limit(monkeypatch):
    monkeypatch.setattr(geo.settings, "internal_token", "secret-token")
    limiter = RateLimiter(1)  # one instance shared by all requests of the test
    app.dependency_overrides[get_geocode_limiter] = lambda: limiter
    app.dependency_overrides[get_repo] = lambda: FakeRepo()
    app.dependency_overrides[get_nominatim] = lambda: None  # never reached: q fails validation
    try:
        client = TestClient(app)
        headers = {"X-Internal-Token": "secret-token"}
        codes = [
            client.get("/geocode", params={"q": "x"}, headers=headers).status_code for _ in range(3)
        ]
        assert codes == [422, 422, 422]
        wrong = client.get("/geocode", params={"q": "x"}, headers={"X-Internal-Token": "nope"})
        assert wrong.status_code == 422  # first non-agent call still passes
        assert client.get("/geocode", params={"q": "x"}).status_code == 429
    finally:
        app.dependency_overrides.clear()


def test_rate_limiter_window_slides():
    now = [0.0]
    limiter = RateLimiter(2, window_seconds=60, clock=lambda: now[0])

    assert [limiter.allow("ip") for _ in range(3)] == [True, True, False]
    now[0] = 61.0
    assert limiter.allow("ip") is True
    assert limiter.allow("other") is True
