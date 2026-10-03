from fastapi.testclient import TestClient

from app.config import settings
from app.main import app

client = TestClient(app)


def test_health_returns_ok():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


# The default (off) is covered in test_config; this must also pass in the demo container
def test_health_reports_demo_mode(monkeypatch):
    monkeypatch.setattr(settings, "demo_mode", True)
    assert client.get("/health").json()["demo_mode"] is True

    monkeypatch.setattr(settings, "demo_mode", False)
    assert client.get("/health").json()["demo_mode"] is False
