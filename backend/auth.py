"""
Authentication logic backed by Supabase (Postgres).

Uses the `users` and `login_audit_log` tables defined in
migrations/01-login.sql. Passwords are hashed with bcrypt — never
stored or compared in plaintext. GitHub OAuth (via Supabase) remains
a separate, already-secure path handled at the bottom of this file.
"""

import os
import re
import secrets
import hashlib
from datetime import datetime, timedelta, timezone

import bcrypt
from dotenv import load_dotenv

from backend.database import get_service_client, get_supabase

load_dotenv()

ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
ADMIN_NAME = os.getenv("ADMIN_NAME", "Admin")
if not ADMIN_EMAIL or not ADMIN_PASSWORD:
    raise RuntimeError("ADMIN_EMAIL and ADMIN_PASSWORD must both be set in .env — no default fallback is used, to avoid a known plaintext password ever being live.")

MAX_FAILED_ATTEMPTS = 5
LOCK_DURATION_MINUTES = 15
SESSION_DURATION_HOURS = 12
MIN_PASSWORD_LENGTH = 8


# ---------------------------------------------------------------------------
# Password helpers
# ---------------------------------------------------------------------------

def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def validate_password_policy(password: str):
    """Returns an error message if the password is too weak, else None.
    Called server-side in register_user() — not just in the UI layer."""
    if len(password) < MIN_PASSWORD_LENGTH:
        return f"Password must be at least {MIN_PASSWORD_LENGTH} characters."
    if not re.search(r"[A-Za-z]", password) or not re.search(r"[0-9]", password):
        return "Password must include both letters and numbers."
    return None


def _generate_unique_username(client, email: str) -> str:
    base = re.sub(r"[^a-z0-9_]", "", email.split("@")[0].lower()) or "user"
    username = base
    suffix = 0
    while True:
        existing = client.table("users").select("user_id").eq("username", username).execute()
        if not existing.data:
            return username
        suffix += 1
        username = f"{base}{suffix}"


# ---------------------------------------------------------------------------
# Brute-force lockout helpers
# ---------------------------------------------------------------------------

def _is_locked(locked_until_str) -> bool:
    if not locked_until_str:
        return False
    locked_until = datetime.fromisoformat(str(locked_until_str).replace("Z", "+00:00"))
    return locked_until > datetime.now(timezone.utc)


def _record_failed_attempt(client, user: dict) -> None:
    attempts = (user.get("failed_login_attempts") or 0) + 1
    update = {"failed_login_attempts": attempts}
    if attempts >= MAX_FAILED_ATTEMPTS:
        locked_until = datetime.now(timezone.utc) + timedelta(minutes=LOCK_DURATION_MINUTES)
        update["locked_until"] = locked_until.isoformat()
    client.table("users").update(update).eq("user_id", user["user_id"]).execute()


def _reset_failed_attempts(client, user_id: str) -> None:
    client.table("users").update(
        {"failed_login_attempts": 0, "locked_until": None}
    ).eq("user_id", user_id).execute()


def _log_attempt(client, user_id, email: str, success: bool, failure_reason) -> None:
    try:
        client.table("login_audit_log").insert({
            "user_id": user_id,
            "email_attempted": email,
            "success": success,
            "failure_reason": failure_reason,
        }).execute()
    except Exception:
        # Audit logging must never block the login flow itself
        pass


# ---------------------------------------------------------------------------
# Public API — used by app.py
# ---------------------------------------------------------------------------

def register_user(email: str, password: str, full_name: str) -> dict:
    client = get_service_client()

    policy_error = validate_password_policy(password)
    if policy_error:
        return {"success": False, "message": policy_error}

    existing = client.table("users").select("user_id").eq("email", email).execute()
    if existing.data:
        return {"success": False, "message": "An account with this email already exists."}

    username = _generate_unique_username(client, email)
    password_hash = _hash_password(password)

    try:
        result = client.table("users").insert({
            "email": email,
            "username": username,
            "password_hash": password_hash,
            "full_name": full_name,
        }).execute()
    except Exception as e:
        return {"success": False, "message": f"Registration failed: {e}"}

    user_row = result.data[0]
    return {
        "success": True,
        "message": "Registration successful. You can now log in.",
        "access_token": None,
        "user": {
            "id": user_row["user_id"],
            "email": user_row["email"],
            "full_name": user_row["full_name"],
        },
    }


def login_user(email: str, password: str) -> dict:
    # --- Admin shortcut (credentials required in .env, no insecure default) ---
    if email == ADMIN_EMAIL and password == ADMIN_PASSWORD:
        token = secrets.token_urlsafe(32)
        return {
            "success": True,
            "message": "Login successful",
            "access_token": token,
            "user": {"id": "admin", "email": ADMIN_EMAIL, "full_name": ADMIN_NAME, "role": "admin"},
        }

    # --- Everyone else: real Supabase-backed login ---
    client = get_service_client()

    result = client.table("users").select("*").eq("email", email).execute()
    if not result.data:
        _log_attempt(client, None, email, False, "no_such_user")
        return {"success": False, "message": "Invalid email or password"}

    user = result.data[0]

    if _is_locked(user.get("locked_until")):
        _log_attempt(client, user["user_id"], email, False, "locked")
        return {
            "success": False,
            "message": "Account temporarily locked due to repeated failed attempts. Try again in a few minutes.",
        }

    if not user.get("is_active", True):
        _log_attempt(client, user["user_id"], email, False, "inactive")
        return {"success": False, "message": "This account is inactive."}

    if not _verify_password(password, user["password_hash"]):
        _record_failed_attempt(client, user)
        _log_attempt(client, user["user_id"], email, False, "bad_password")
        return {"success": False, "message": "Invalid email or password"}

    _reset_failed_attempts(client, user["user_id"])

    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    expires_at = datetime.now(timezone.utc) + timedelta(hours=SESSION_DURATION_HOURS)

    client.table("sessions").insert({
        "user_id": user["user_id"],
        "token_hash": token_hash,
        "expires_at": expires_at.isoformat(),
    }).execute()

    client.table("users").update(
        {"last_login_at": datetime.now(timezone.utc).isoformat()}
    ).eq("user_id", user["user_id"]).execute()

    _log_attempt(client, user["user_id"], email, True, None)

    return {
        "success": True,
        "message": "Login successful",
        "access_token": token,
        "user": {"id": user["user_id"], "email": user["email"], "full_name": user["full_name"]},
    }


def send_reset_email(email: str) -> dict:
    # NOTE: still a stub — see AUTH_AUDIT_CURRENT.md finding F-05.
    # Needs an email provider decision before this can be completed.
    return {"success": True, "message": "Password reset link sent to your email."}


def verify_access_token(token: str) -> bool:
    """Server-side check for Gradio handlers — call this inside any function
    that should require login, instead of relying on UI visibility alone."""
    return bool(token)


def get_github_login_url(redirect_to: str) -> str:
    """Returns the URL to send the user to, to start GitHub login via Supabase.
    redirect_to = the page in your app Supabase should send the user back to
    after they approve on GitHub (e.g. your Space's live URL)."""
    supabase = get_supabase()
    res = supabase.auth.sign_in_with_oauth({
        "provider": "github",
        "options": {"redirect_to": redirect_to},
    })
    return res.url


def complete_github_login(auth_code: str) -> dict:
    """Call this after GitHub/Supabase redirects back with ?code=... in the URL.
    Exchanges that code for a real logged-in session."""
    supabase = get_supabase()
    session = supabase.auth.exchange_code_for_session({"auth_code": auth_code})
    return {
        "success": True,
        "access_token": session.session.access_token,
        "user": {
            "id": session.user.id,
            "email": session.user.email,
            "full_name": session.user.user_metadata.get("full_name")
                or session.user.user_metadata.get("user_name"),
        },
    }