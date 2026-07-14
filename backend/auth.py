import os
from typing import Any
from backend.database import get_supabase

from dotenv import load_dotenv

load_dotenv()

def _user_from_session(u: Any) -> dict:
    """Build a consistent user dict from a Supabase Auth user object."""
    return {
        "id": u.id,
        "email": u.email,
        "full_name": (
            u.user_metadata.get("full_name")
            or u.user_metadata.get("user_name")
            or ""
        ),
    }


def register_user(email: str, password: str, full_name: str) -> dict:
    supabase = get_supabase()
    try:
        result = supabase.auth.sign_up({
            "email": email,
            "password": password,
            "options": {"data": {"full_name": full_name}},
        })
        user = result.user
        return {
            "success": True,
            "message": "Registration successful. You can now log in.",
            "access_token": None,
            "user": {
                "id": user.id,
                "email": user.email,
                "full_name": full_name,
            },
        }
    except Exception as e:
        msg = str(e)
        if "already registered" in msg.lower():
            return {"success": False, "message": "An account with this email already exists."}
        return {"success": False, "message": f"Registration failed: {msg}"}


def login_user(email: str, password: str) -> dict:
    supabase = get_supabase()
    try:
        result = supabase.auth.sign_in_with_password({"email": email, "password": password})
        token = result.session.access_token
        return {
            "success": True,
            "message": "Login successful",
            "access_token": token,
            "user": _user_from_session(result.user),
        }
    except Exception as e:
        msg = str(e)
        if "email not confirmed" in msg.lower():
            return {"success": False, "message": "Please confirm your email before logging in."}
        return {"success": False, "message": "Invalid email or password"}


def send_reset_email(email: str) -> dict:
    supabase = get_supabase()
    try:
        supabase.auth.reset_password_email(email)
        return {"success": True, "message": "Password reset link sent to your email."}
    except Exception as e:
        return {"success": False, "message": f"Failed to send reset email: {e}"}



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
        "user": _user_from_session(session.user),
    }
