import os
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from jose import JWTError, jwt
from dotenv import load_dotenv

from backend.auth import (
    login_user,
    register_user,
    send_reset_email,
    get_github_login_url,
    complete_github_login,
)
from backend.prediction import predict_image

load_dotenv()

app = FastAPI(title="Surface Crack Detection API")


@app.get("/")
def root():
    from fastapi.responses import HTMLResponse
    html = """<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Surface Crack Detection API</title>
<style>
  body{background:#0B0D15;color:#E4E4ED;font-family:system-ui,sans-serif;display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0}
  .card{background:#12141F;border:1px solid #232636;border-radius:12px;padding:2.5rem;max-width:480px;text-align:center}
  h1{font-size:1.5rem;margin:0 0 0.5rem}
  p{color:#6B6D82;font-size:0.875rem;margin:0 0 1.5rem}
  .links{display:flex;flex-direction:column;gap:0.75rem}
  a{background:#1A1D2E;border:1px solid #2E3148;border-radius:8px;padding:10px 16px;color:#C4C4D0;text-decoration:none;font-size:0.875rem;transition:border-color .15s}
  a:hover{border-color:#6366F1;color:#E4E4ED}
</style></head>
<body><div class="card">
  <h1>Surface Crack Detection API</h1>
  <p>Backend is running. Connect the frontend to these endpoints.</p>
  <div class="links">
    <a href="/docs">API Documentation (Swagger UI)</a>
    <a href="/api/health">Health Check</a>
  </div>
</div></body></html>"""
    return HTMLResponse(html)

# CORS — allow frontend dev server and production
origins = os.getenv("CORS_ORIGINS", "*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins.split(",") if origins != "*" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# JWT config
JWT_SECRET = os.getenv("JWT_SECRET", "super-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

security = HTTPBearer(auto_error=False)


def create_jwt_token(user_id: str, email: str) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_token(credentials: HTTPAuthorizationCredentials | None = Depends(security)):
    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


# --- Request / Response models ---

class LoginRequest(BaseModel):
    email: str
    password: str

class RegisterRequest(BaseModel):
    email: str
    password: str
    full_name: str

class ForgotRequest(BaseModel):
    email: str


# --- Auth routes (always return 200; body.success tells the real outcome) ---

@app.post("/api/auth/login")
def login_route(req: LoginRequest):
    result = login_user(req.email, req.password)
    if result["success"]:
        token = create_jwt_token(result["user"]["id"], result["user"]["email"])
        return {
            "success": True,
            "access_token": token,
            "user": result["user"],
        }
    return {
        "success": False,
        "message": result["message"],
    }


@app.post("/api/auth/register")
def register_route(req: RegisterRequest):
    return register_user(req.email, req.password, req.full_name)


@app.post("/api/auth/forgot-password")
def forgot_route(req: ForgotRequest):
    return send_reset_email(req.email)


@app.get("/api/auth/github")
def github_start(redirect_to: str = Query(...)):
    try:
        url = get_github_login_url(redirect_to)
        return {"url": url}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"GitHub OAuth setup failed: {e}")


@app.get("/api/auth/github/callback")
def github_callback(code: str = Query(...)):
    try:
        result = complete_github_login(code)
        token = create_jwt_token(result["user"]["id"], result["user"]["email"])
        return {
            "success": True,
            "access_token": token,
            "user": result["user"],
        }
    except Exception as e:
        return {"success": False, "message": f"GitHub login failed: {e}"}


# --- Prediction (requires valid JWT) ---

@app.post("/api/predict")
async def predict_route(
    image: UploadFile = File(...),
    token_payload: dict = Depends(verify_token),
):
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image (JPEG/PNG)")

    contents = await image.read()
    if len(contents) == 0:
        raise HTTPException(status_code=400, detail="Empty file")

    try:
        result = predict_image(contents, image.filename or "upload.jpg")
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {e}")


@app.get("/api/health")
def health():
    return {"status": "ok"}
