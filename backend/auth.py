import streamlit as st
import uuid as _uuid
from backend.database import get_supabase

from dotenv import load_dotenv

load_dotenv()

ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
ADMIN_NAME = os.getenv("ADMIN_NAME", "Admin")

def register_user(email: str, password: str, full_name: str) -> dict:
    return {
        "success": True,
        "message": "Registration successful. You can now log in.",
        "access_token": None,
        "user": {"id": str(_uuid.uuid4()), "email": email, "full_name": full_name},
    }


def login_user(email: str, password: str) -> dict:
    if email == ADMIN_EMAIL and password == ADMIN_PASSWORD:
        return {
            "success": True,
            "message": "Login successful",
            "access_token": "hardcoded-admin-token",
            "user": {
                "id": str(_uuid.uuid4()),
                "email": ADMIN_EMAIL,
                "full_name": ADMIN_NAME,
            },
        }
    return {"success": False, "message": "Invalid email or password"}


def send_reset_email(email: str) -> dict:
    return {"success": True, "message": "Password reset link sent to your email."}


def require_login():
    """Call at the top of every protected Streamlit page.
    Redirects to the login page if no valid session exists."""
    if not st.session_state.get("access_token"):
        st.warning("Please log in to continue.")
        st.switch_page("pages/login.py")
        st.stop()


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
                or session.user.user_metadata.get("user_name"),  # GitHub username fallback
        },
    }
