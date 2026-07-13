from fastapi import FastAPI
from pydantic import BaseModel

from backend.auth import login_user

app = FastAPI()


class LoginRequest(BaseModel):
    email: str
    password: str


@app.post("/")
def login(user: LoginRequest):
    # Routed through the real, Supabase-backed login logic in backend/auth.py —
    # this used to be a separate hardcoded credential check (security finding F-03).
    result = login_user(email=user.email, password=user.password)
    return result