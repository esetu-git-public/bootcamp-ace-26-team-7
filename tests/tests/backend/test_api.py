import io
import json

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from backend.main import app, create_jwt_token

client = TestClient(app)


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
        r = client.post("/api/auth/login", json={
            "email": "admin@surfacedetection.com",
            "password": "Admin@123",
        })
        assert r.status_code == 200
        body = r.json()
        assert body["success"] is True
        assert isinstance(body["access_token"], str) and len(body["access_token"]) > 20
        assert body["user"]["email"] == "admin@surfacedetection.com"
        assert body["user"]["full_name"] == "Admin"

    def test_login_bad_password(self):
        r = client.post("/api/auth/login", json={
            "email": "admin@surfacedetection.com",
            "password": "wrong",
        })
        assert r.status_code == 200
        assert r.json()["success"] is False

    def test_login_bad_email(self):
        r = client.post("/api/auth/login", json={
            "email": "nobody@example.com",
            "password": "Admin@123",
        })
        assert r.status_code == 200
        assert r.json()["success"] is False

    def test_login_empty_body(self):
        r = client.post("/api/auth/login", json={})
        assert r.status_code == 422


class TestRegister:
    def test_register_success(self):
        r = client.post("/api/auth/register", json={
            "email": "new@user.com",
            "password": "Pass1234",
            "full_name": "New User",
        })
        assert r.status_code == 200
        body = r.json()
        assert body["success"] is True
        assert body["user"]["email"] == "new@user.com"
        assert body["user"]["full_name"] == "New User"

    def test_register_missing_field(self):
        r = client.post("/api/auth/register", json={
            "email": "test@test.com",
        })
        assert r.status_code == 422


class TestForgotPassword:
    def test_forgot_success(self):
        r = client.post("/api/auth/forgot-password", json={
            "email": "test@test.com",
        })
        assert r.status_code == 200
        body = r.json()
        assert body["success"] is True
        assert "sent" in body["message"].lower()

    def test_forgot_empty_body(self):
        r = client.post("/api/auth/forgot-password", json={})
        assert r.status_code == 422


class TestGitHub:
    def test_github_url_missing_param(self):
        r = client.get("/api/auth/github")
        assert r.status_code == 422

    def test_github_callback_no_code(self):
        r = client.get("/api/auth/github/callback")
        assert r.status_code == 422


class TestPredict:
    @pytest.fixture
    def auth_token(self):
        return create_jwt_token("test-user-id", "test@example.com")

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
