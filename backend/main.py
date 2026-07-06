"""
FastAPI REST API — thin wrappers around backend logic modules.
Run standalone with:  uvicorn backend.main:app --reload
The Streamlit UI imports backend.auth and backend.prediction directly.
"""

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr

from backend.auth import register_user, login_user, send_reset_email
from backend.prediction import predict_image

app = FastAPI(title="Surface Crack Detection API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str

class LoginRequest(BaseModel):
    email: str
    password: str

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/register")
def register(req: RegisterRequest):
    try:
        return register_user(email=req.email, password=req.password, full_name=req.full_name)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/login")
def login(req: LoginRequest):
    try:
        return login_user(email=req.email, password=req.password)
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid email or password")


@app.post("/forgot-password")
def forgot_password(req: ForgotPasswordRequest):
    try:
        return send_reset_email(email=req.email)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/predict")
def predict(file: UploadFile = File(...)):
    image_bytes = file.file.read()
    return predict_image(image_bytes=image_bytes, filename=file.filename)
