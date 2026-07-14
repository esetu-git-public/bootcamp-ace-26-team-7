import io
import json
from unittest.mock import MagicMock, patch

import bcrypt
import pytest
from fastapi.testclient import TestClient
from PIL import Image

# Mock Supabase and service client before any backend imports
_mock_supabase = MagicMock()
_mock_service = MagicMock()

# Wire up the users table mock chain for both clients
_table_mock = MagicMock()
_query_mock = MagicMock()
_table_mock.select.return_value = _query_mock
_query_mock.eq.return_value = _query_mock

_mock_supabase.table.return_value = _table_mock
_mock_service.table.return_value = _table_mock

# Default: empty result for users table queries
_query_mock.execute.return_value = MagicMock(data=[])

# GitHub OAuth mocks (used by complete_github_login)
_mock_supabase.auth.exchange_code_for_session.return_value = MagicMock(
    user=MagicMock(
        id="gh-uid",
        email="gh@user.com",
        user_metadata={"user_name": "ghuser", "full_name": "GH User"},
    ),
    session=MagicMock(access_token="gh-token"),
)

patch("backend.database.get_supabase", return_value=_mock_supabase).start()
patch("backend.database.get_service_client", return_value=_mock_service).start()

from backend.main import app, create_jwt_token

client = TestClient(app)


def _fake_user(username="testuser", uid="uid-1", full_name="Test User", pwhash=None):
    return {
        "id": uid,
        "username": username,
        "full_name": full_name,
        "password_hash": pwhash,
        "github_id": None,
    }


def _set_query_result(data: list):
    """Set the return value for the chained .select().eq().execute() call."""
    _query_mock.execute.return_value = MagicMock(data=data)


def _set_insert_result(data: list):
    """Set the return value for the chained .insert().execute() call."""
    _table_mock.insert.return_value = MagicMock()
    _table_mock.insert.return_value.execute.return_value = MagicMock(data=data)


class TestHealthAndRoot:
    def test_health(self):
        r = client.get("/api/health")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}

    def test_root_returns_html(self):
        r = client.get("/")
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/html")


class TestLogin:
    def test_login_success(self):
        pwhash = bcrypt.hashpw(b"Pass@123", bcrypt.gensalt()).decode()
        _set_query_result([_fake_user(username="testuser", pwhash=pwhash)])
        r = client.post("/api/auth/login", json={"username": "testuser", "password": "Pass@123"})
        assert r.status_code == 200
        body = r.json()
        assert body["success"] is True
        assert isinstance(body["access_token"], str) and len(body["access_token"]) > 0
        assert body["user"]["username"] == "testuser"
        assert body["user"]["full_name"] == "Test User"

    def test_login_bad_password(self):
        pwhash = bcrypt.hashpw(b"RealPass1", bcrypt.gensalt()).decode()
        _set_query_result([_fake_user(username="testuser", pwhash=pwhash)])
        r = client.post("/api/auth/login", json={"username": "testuser", "password": "wrong"})
        assert r.status_code == 200
        assert r.json()["success"] is False

    def test_login_unknown_user(self):
        _set_query_result([])
        r = client.post("/api/auth/login", json={"username": "nobody", "password": "x"})
        assert r.status_code == 200
        assert r.json()["success"] is False

    def test_login_empty_body(self):
        r = client.post("/api/auth/login", json={})
        assert r.status_code == 422


class TestRegister:
    def test_register_success(self):
        _set_insert_result([_fake_user(username="newuser", uid="uid-2", full_name="New User")])
        r = client.post("/api/auth/register", json={
            "username": "newuser",
            "password": "Pass1234",
            "full_name": "New User",
        })
        assert r.status_code == 200
        body = r.json()
        assert body["success"] is True
        assert body["user"]["username"] == "newuser"
        assert body["user"]["full_name"] == "New User"

    def test_register_duplicate(self):
        _table_mock.insert.return_value.execute.side_effect = Exception("duplicate key")
        r = client.post("/api/auth/register", json={
            "username": "dup", "password": "x", "full_name": "Dup",
        })
        assert r.status_code == 200
        assert r.json()["success"] is False

    def test_register_missing_field(self):
        r = client.post("/api/auth/register", json={
            "username": "testuser",
        })
        assert r.status_code == 422


class TestForgotPassword:
    def test_forgot_route_not_found(self):
        r = client.post("/api/auth/forgot-password", json={"email": "test@test.com"})
        assert r.status_code == 404


class TestGitHub:
    def test_github_url_missing_param(self):
        r = client.get("/api/auth/github")
        assert r.status_code == 422

    def test_github_callback_no_code(self):
        r = client.get("/api/auth/github/callback")
        assert r.status_code == 422

    def test_github_callback_success(self):
        _set_query_result([])
        _set_insert_result([_fake_user(username="ghuser", uid="gh-uuid", full_name="GH User")])
        r = client.get("/api/auth/github/callback?code=some-code")
        assert r.status_code == 200
        body = r.json()
        assert body["success"] is True
        assert isinstance(body["access_token"], str) and len(body["access_token"]) > 0
        assert body["user"]["username"] == "ghuser"


class TestPredict:
    @pytest.fixture
    def auth_token(self):
        return create_jwt_token("test-user-id", "testuser")

    @pytest.fixture
    def sample_jpeg(self):
        img = Image.new("RGB", (224, 224), color="gray")
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        buf.seek(0)
        return buf

    def test_predict_no_auth(self):
        r = client.post("/api/predict")
        assert r.status_code == 401

    def test_predict_invalid_token(self):
        r = client.post(
            "/api/predict",
            headers={"Authorization": "Bearer invalid_token"},
        )
        assert r.status_code == 401

    def test_predict_no_file(self, auth_token):
        r = client.post(
            "/api/predict",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert r.status_code == 422

    def test_predict_with_image(self, auth_token, sample_jpeg):
        r = client.post(
            "/api/predict",
            headers={"Authorization": f"Bearer {auth_token}"},
            files={"image": ("test.jpg", sample_jpeg, "image/jpeg")},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["success"] is True
        assert body["predicted_class"] in ["Cracks", "Patch", "Potholes", "Surface Defects", "N/A"]
        assert body["confidence"] >= 0.0
        assert set(body["class_probabilities"].keys()) == {
            "Cracks", "Patch", "Potholes", "Surface Defects",
        }
        assert body["severity_label"] in ["Low", "Medium", "High"]
        assert "repair_cost" in body
        assert "repair_time" in body


class TestCors:
    def test_cors_headers(self):
        r = client.options(
            "/api/health",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert r.status_code == 200
        assert "access-control-allow-origin" in r.headers
