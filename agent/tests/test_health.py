from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_ok_with_model_name():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "model": "glm-5.3"}


def test_docs_are_hidden_in_production():
    import subprocess
    import sys

    code = "from app.main import app; print(app.openapi_url, app.docs_url)"
    out = subprocess.run(
        [sys.executable, "-c", code],
        env={"APP_ENV": "production", "PATH": ""},
        capture_output=True,
        text=True,
        check=True,
    )
    assert out.stdout.split() == ["None", "None"]
