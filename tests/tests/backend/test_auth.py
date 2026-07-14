from unittest.mock import patch, MagicMock

import bcrypt
import pytest

from backend.auth import login_user, register_user, complete_github_login, get_github_login_url


@pytest.fixture(autouse=True)
def mock_db():
    """Mock both get_supabase() and get_service_client() for all tests."""
    with patch("backend.auth.get_supabase") as mock_supabase, \
         patch("backend.auth.get_service_client") as mock_service:
        supabase = MagicMock()
        service = MagicMock()
        mock_supabase.return_value = supabase
        mock_service.return_value = service
        yield supabase, service


def _fake_user(username="testuser", uid="00000000-0000-0000-0000-000000000001", full_name="Test User", pwhash=None):
    return {
        "id": uid,
        "username": username,
        "full_name": full_name,
        "password_hash": pwhash,
        "github_id": None,
    }


class TestRegister:
    def test_register_success(self, mock_db):
        _, service = mock_db
        service.table("users").insert().execute.return_value = MagicMock(
            data=[_fake_user(username="newuser", uid="u1", full_name="New User")],
        )
        result = register_user(username="newuser", password="Pass@123", full_name="New User")
        assert result["success"] is True
        assert "Registration successful" in result["message"]

    def test_register_returns_user(self, mock_db):
        _, service = mock_db
        service.table("users").insert().execute.return_value = MagicMock(
            data=[_fake_user(username="alice", uid="22222222-2222-2222-2222-222222222222", full_name="Alice")],
        )
        result = register_user(username="alice", password="Pass@123", full_name="Alice")
        user = result["user"]
        assert user["username"] == "alice"
        assert user["full_name"] == "Alice"
        assert user["id"] == "22222222-2222-2222-2222-222222222222"

    def test_register_access_token_is_none(self, mock_db):
        _, service = mock_db
        service.table("users").insert().execute.return_value = MagicMock(
            data=[_fake_user()],
        )
        result = register_user(username="anyuser", password="Pass@123", full_name="Any")
        assert result["access_token"] is None

    def test_register_duplicate_username(self, mock_db):
        _, service = mock_db
        service.table("users").insert().execute.side_effect = Exception("duplicate key value violates unique constraint")
        result = register_user(username="dup", password="Pass@123", full_name="Dup")
        assert result["success"] is False
        assert "already taken" in result["message"]


class TestLogin:
    def test_login_success(self, mock_db):
        _, service = mock_db
        pwhash = bcrypt.hashpw(b"Pass@123", bcrypt.gensalt()).decode()
        service.table("users").select("*").eq("username", "testuser").execute.return_value = MagicMock(
            data=[_fake_user(pwhash=pwhash)],
        )
        result = login_user(username="testuser", password="Pass@123")
        assert result["success"] is True
        assert result["user"]["username"] == "testuser"
        assert result["user"]["full_name"] == "Test User"

    def test_login_failure_wrong_password(self, mock_db):
        _, service = mock_db
        pwhash = bcrypt.hashpw(b"RealPass1", bcrypt.gensalt()).decode()
        service.table("users").select("*").eq("username", "testuser").execute.return_value = MagicMock(
            data=[_fake_user(pwhash=pwhash)],
        )
        result = login_user(username="testuser", password="WrongPass")
        assert result["success"] is False
        assert "Invalid" in result["message"]

    def test_login_failure_unknown_user(self, mock_db):
        _, service = mock_db
        service.table("users").select("*").eq("username", "nobody").execute.return_value = MagicMock(data=[])
        result = login_user(username="nobody", password="x")
        assert result["success"] is False
        assert "Invalid" in result["message"]

    def test_login_failure_github_user_no_password(self, mock_db):
        _, service = mock_db
        service.table("users").select("*").eq("username", "ghuser").execute.return_value = MagicMock(
            data=[_fake_user(username="ghuser", pwhash=None)],
        )
        result = login_user(username="ghuser", password="anything")
        assert result["success"] is False
        assert "GitHub" in result["message"]


class TestGitHub:
    def test_get_url_calls_supabase_oauth(self, mock_db):
        supabase, _ = mock_db
        supabase.auth.sign_in_with_oauth.return_value = MagicMock(url="https://github.com/login/oauth/authorize?...")
        url = get_github_login_url("https://app.com/callback")
        assert url.startswith("https://github.com")

    def test_complete_login_creates_new_user(self, mock_db):
        supabase, service = mock_db
        supabase.auth.exchange_code_for_session.return_value = MagicMock(
            user=MagicMock(
                id="gh-123",
                email="gh@user.com",
                user_metadata={"user_name": "octocat", "full_name": "Octo Cat"},
            ),
            session=MagicMock(access_token="gh-token"),
        )
        service.table("users").select("*").eq("github_id", "gh-123").execute.return_value = MagicMock(data=[])
        service.table("users").insert().execute.return_value = MagicMock(
            data=[_fake_user(username="octocat", uid="new-uuid", full_name="Octo Cat")],
        )
        result = complete_github_login("auth-code-123")
        assert result["success"] is True
        assert result["user"]["username"] == "octocat"
        assert result["user"]["full_name"] == "Octo Cat"

    def test_complete_login_finds_existing_user(self, mock_db):
        supabase, service = mock_db
        supabase.auth.exchange_code_for_session.return_value = MagicMock(
            user=MagicMock(
                id="gh-456",
                email="returning@user.com",
                user_metadata={"user_name": "returninguser", "full_name": "Returning User"},
            ),
            session=MagicMock(access_token="gh-token"),
        )
        service.table("users").select("*").eq("github_id", "gh-456").execute.return_value = MagicMock(
            data=[_fake_user(username="returninguser", uid="existing-uuid", full_name="Returning User")],
        )
        result = complete_github_login("auth-code-456")
        assert result["success"] is True
        assert result["user"]["id"] == "existing-uuid"
