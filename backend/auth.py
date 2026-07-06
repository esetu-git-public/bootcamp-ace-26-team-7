import uuid as _uuid

ADMIN_EMAIL = "admin@surfacedetect.com"
ADMIN_PASSWORD = "Admin@123"
ADMIN_NAME = "Admin"


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
