import asyncio

import httpx
import pytest
from fastapi.testclient import TestClient

from app import nominatim as nominatim_module
from app.main import app
from app.nominatim import Nominatim
from app.repo import get_repo
from app.routers.geo import get_nominatim
from tests.fakes import FakeRepo

client = TestClient(app)

KOBIERZYNSKA = {
    "lat": "50.0213",
    "lon": "19.9091",
    "name": "Kobierzyńska",
    "display_name": "Kobierzyńska, Dębniki, Kraków, województwo małopolskie, Polska",
    "address": {
        "road": "Kobierzyńska",
        "house_number": "1",
        "city_district": "Dębniki",
        "city": "Kraków",
    },
}
SKAWINA = {
    "lat": "49.977",
    "lon": "19.823",
    "display_name": "Rynek, Skawina",
    "address": {"road": "Rynek", "suburb": "Stare Miasto", "town": "Skawina"},
}


def make_nominatim(handler):
    requests: list[httpx.Request] = []

    def recording(request):
        requests.append(request)
        return handler(request)

    transport = httpx.MockTransport(recording)
    return Nominatim(
        httpx.AsyncClient(base_url="https://nominatim.test", transport=transport)
    ), requests


@pytest.fixture
def wire(monkeypatch):
    monkeypatch.setattr(nominatim_module, "MIN_INTERVAL_SECONDS", 0)

    def factory(handler, repo=None):
        geo, requests = make_nominatim(handler)
        fake_repo = repo or FakeRepo()
        app.dependency_overrides[get_nominatim] = lambda: geo
        app.dependency_overrides[get_repo] = lambda: fake_repo
        return requests, fake_repo

    yield factory
    app.dependency_overrides.clear()


def test_geocode_found_in_krakow(wire):
    requests, _ = wire(lambda r: httpx.Response(200, json=[KOBIERZYNSKA]))

    body = client.get("/geocode", params={"q": "Kobierzyńska 1"}).json()

    assert body == {
        "query": "Kobierzyńska 1",
        "found": True,
        "lat": 50.0213,
        "lon": 19.9091,
        "display_name": "Kobierzyńska 1, Dębniki, Kraków",
        "district": "Dębniki",
        "in_krakow": True,
    }
    params = requests[0].url.params
    assert params["countrycodes"] == "pl"
    assert params["format"] == "jsonv2"
    assert requests[0].headers["User-Agent"].startswith("KryzIO")


def test_geocode_uses_boundary_check_before_address_fields(wire):
    # Boundary says outside even though Nominatim reports city=Kraków
    wire(lambda r: httpx.Response(200, json=[KOBIERZYNSKA]), FakeRepo(inside=False))

    assert client.get("/geocode", params={"q": "Kobierzyńska"}).json()["in_krakow"] is False


def test_geocode_falls_back_to_address_without_boundary(wire):
    wire(lambda r: httpx.Response(200, json=[SKAWINA]), FakeRepo(inside=None))

    body = client.get("/geocode", params={"q": "Skawina"}).json()

    assert body["in_krakow"] is False
    assert body["display_name"] == "Rynek, Stare Miasto, Skawina"


def test_geocode_not_found(wire):
    wire(lambda r: httpx.Response(200, json=[]))

    body = client.get("/geocode", params={"q": "xyz"}).json()

    assert body["found"] is False
    assert body["in_krakow"] is None


def test_geocoder_failure_returns_503(wire):
    wire(lambda r: httpx.Response(503))

    assert client.get("/geocode", params={"q": "Kobierzyńska"}).status_code == 503


@pytest.mark.parametrize("q", ["a", "x" * 201])
def test_geocode_validates_query_length(wire, q):
    wire(lambda r: httpx.Response(200, json=[]))

    assert client.get("/geocode", params={"q": q}).status_code == 422


def test_reverse_reports_the_users_own_point(wire):
    requests, repo = wire(lambda r: httpx.Response(200, json=KOBIERZYNSKA))

    body = client.get("/reverse", params={"lat": 50.0312, "lon": 19.9204}).json()

    assert (body["lat"], body["lon"]) == (50.0312, 19.9204)
    assert body["query"] is None
    assert body["in_krakow"] is True
    assert repo.calls[-1] == ("point_in_krakow", 50.0312, 19.9204)
    assert requests[0].url.path == "/reverse"


def test_reverse_without_match(wire):
    wire(lambda r: httpx.Response(200, json={"error": "Unable to geocode"}))

    assert client.get("/reverse", params={"lat": 54.5, "lon": 18.0}).json()["found"] is False


def test_nominatim_caches_repeated_queries():
    geo, requests = make_nominatim(lambda r: httpx.Response(200, json=[KOBIERZYNSKA]))

    async def run():
        await geo.search("Kobierzyńska")
        await geo.search("Kobierzyńska")

    asyncio.run(run())

    assert len(requests) == 1


def test_nominatim_spaces_requests(monkeypatch):
    monkeypatch.setattr(nominatim_module, "MIN_INTERVAL_SECONDS", 0.2)
    geo, _ = make_nominatim(lambda r: httpx.Response(200, json=[]))

    async def run():
        loop = asyncio.get_running_loop()
        start = loop.time()
        await asyncio.gather(geo.search("a1"), geo.search("b2"), geo.search("c3"))
        return loop.time() - start

    assert asyncio.run(run()) >= 0.4
