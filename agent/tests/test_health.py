from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_ok_with_model_name():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "model": "glm-5.3"}
