import uuid
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from main import app
from core.database import get_db


def _override_get_db():
    db = MagicMock()
    db.commit = MagicMock()
    db.refresh = MagicMock()
    db.add = MagicMock()
    db.execute = MagicMock()
    db.query = MagicMock()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _override_get_db

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_overrides():
    yield
    app.dependency_overrides = {}


class TestServerRoutes:
    def test_root(self):
        response = client.get("/")
        assert response.status_code == 200
        assert response.json()["message"] == "ZenOps Backend is running"

    def test_get_servers_empty(self):
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_query.all = MagicMock(return_value=[])
        mock_db.query = MagicMock(return_value=mock_query)

        app.dependency_overrides[get_db] = lambda: mock_db

        response = client.get("/servers")
        assert response.status_code == 200
        assert response.json() == []

    def test_create_server_missing_fields(self):
        response = client.post("/servers", json={})
        assert response.status_code == 422

    def test_create_server_invalid_data(self):
        payload = {"name": "test", "tailscale_ip": "invalid"}
        response = client.post("/servers", json=payload)
        assert response.status_code == 422


class TestBindingRoutes:
    def test_bind_channel_no_auth(self):
        response = client.post("/internal/bindings/test-channel", json={"server_id": str(uuid.uuid4())})
        assert response.status_code == 403

    def test_internal_routes_require_auth(self):
        endpoints = [
            ("POST", "/internal/bindings/test", {"server_id": str(uuid.uuid4())}),
            ("DELETE", "/internal/bindings/test", None),
            ("PUT", "/internal/guilds/test/global", {"discord_channel_id": "ch"}),
            ("PUT", "/internal/bindings/test/context-limit", {"limit": 10}),
            ("DELETE", "/internal/bindings/test/context", None),
            ("GET", "/internal/bindings/test/context-info?guild_id=g", None),
        ]
        for method, path, body in endpoints:
            if method == "POST":
                response = client.post(path, json=body)
            elif method == "PUT":
                response = client.put(path, json=body)
            elif method == "GET":
                response = client.get(path)
            elif method == "DELETE":
                response = client.delete(path)
            assert response.status_code == 403, f"{method} {path} should return 403 without auth"
