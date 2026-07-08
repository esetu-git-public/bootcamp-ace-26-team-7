import re
import uuid as _uuid

import pytest

from backend.auth import ADMIN_EMAIL, ADMIN_PASSWORD, login_user, register_user, send_reset_email


class TestLogin:
    def test_login_success(self):
        result = login_user(email=ADMIN_EMAIL, password=ADMIN_PASSWORD)
        assert result["success"] is True
        assert result["access_token"] == "hardcoded-admin-token"
        assert result["user"]["email"] == ADMIN_EMAIL

    def test_login_success_sets_session_user(self):
        result = login_user(email=ADMIN_EMAIL, password=ADMIN_PASSWORD)
        user = result["user"]
        assert "id" in user
        assert _uuid.UUID(user["id"], version=4)
        assert user["full_name"] == "Admin"

    def test_login_failure_wrong_email(self):
        result = login_user(
            email="wrong@surfacedetect.com", password=ADMIN_PASSWORD
        )
        assert result["success"] is False
        assert "Invalid" in result["message"]

    def test_login_failure_wrong_password(self):
        result = login_user(email=ADMIN_EMAIL, password="WrongPass123")
        assert result["success"] is False
        assert "Invalid" in result["message"]

    def test_login_failure_both_wrong(self):
        result = login_user(email="x@y.com", password="bad")
        assert result["success"] is False

    @pytest.mark.parametrize("email,password", [
        ("", ADMIN_PASSWORD),
        (ADMIN_EMAIL, ""),
        ("", ""),
    ])
    def test_login_failure_empty_credentials(self, email, password):
        result = login_user(email=email, password=password)
        assert result["success"] is False


class TestRegister:
    def test_register_success(self):
        result = register_user(
            email="test@example.com",
            password="Test@123",
            full_name="Test User",
        )
        assert result["success"] is True
        assert "Registration successful" in result["message"]

    def test_register_returns_user_with_uuid(self):
        result = register_user(
            email="user@example.com",
            password="Pass@123",
            full_name="Alice",
        )
        user = result["user"]
        assert user["email"] == "user@example.com"
        assert user["full_name"] == "Alice"
        assert _uuid.UUID(user["id"], version=4)

    def test_register_access_token_is_none(self):
        result = register_user(
            email="any@example.com",
            password="Pass@123",
            full_name="Any",
        )
        assert result["access_token"] is None


class TestResetPassword:
    def test_reset_email_success(self):
        result = send_reset_email(email="admin@surfacedetect.com")
        assert result["success"] is True
        assert "reset link" in result["message"].lower()

    def test_reset_email_any_email_succeeds(self):
        result = send_reset_email(email="nonexistent@example.com")
        assert result["success"] is True
