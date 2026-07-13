# Authentication Audit Report

**Project:** Surface Crack Detection — Bootcamp ACE 26, Team 7

**Repository:** https://github.com/esetu-git-public/bootcamp-ace-26-team-7

**Audit Date:** July 12, 2026

**Auditor:** N.Varshashri

**Scope:** Login, Registration, Forgot Password, Session Handling, Route/Feature Protection, Backend API

**Framework note:** The application has moved from Streamlit to **Gradio** (`app.py`, single file, `gradio==5.20.1`).

**Files Reviewed:**
- `app.py`
- `backend/auth.py`
- `backend/main.py`
- `backend/database.py`
- `backend/prediction.py`
- `migrations/01-login.sql`
- `requirements.txt`, `.env.example`

---

## 1. Executive Summary

The database schema is well designed (hashed passwords, sessions, audit log, lockout fields all present). GitHub OAuth login, via Supabase, is implemented correctly and is genuinely secure. Outside of that, the core email/password authentication is still not connected to real user data, and the switch to Gradio has introduced a new access-control gap: the app currently protects features by **hiding UI elements**, not by checking who's logged in on the server side — which is not the same thing in Gradio's client-server model.

---

## 2. Findings

### 🔴 CRITICAL

#### F-01: Registration does not persist users
**File:** `backend/auth.py`, `register_user()`
```python
def register_user(email: str, password: str, full_name: str) -> dict:
    return {
        "success": True,
        "message": "Registration successful. You can now log in.",
        "access_token": None,
        "user": {"id": str(_uuid.uuid4()), "email": email, "full_name": full_name},
    }
```
This always reports success without writing anything to Supabase. No password is hashed or stored anywhere. Any "registered" account is not retrievable on a later login attempt.
**Recommendation:** Insert a real row into the `users` table (schema already supports this — see `migrations/01-login.sql`), with the password hashed via bcrypt (already listed in `requirements.txt`, just not used yet).

#### F-02: Login only recognizes a single hardcoded admin account
**File:** `backend/auth.py`, `login_user()`
```python
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@surfacedetect.com")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "Admin@123")
...
if email == ADMIN_EMAIL and password == ADMIN_PASSWORD:
    ...
return {"success": False, "message": "Invalid email or password"}
```
Every non-admin login attempt is rejected outright, regardless of whether that user "registered" successfully. There is no real credential check against the database. The token issued on success is also a fixed string (`"hardcoded-admin-token"`), not a real, verifiable session token.
**Recommendation:** Query the real `users` table, verify the bcrypt hash, and issue a random, single-use session token stored (hashed) in the `sessions` table.

#### F-03: A second, separate hardcoded credential exists in `backend/main.py`
```python
@app.post("/")
def login(user: LoginRequest):
    if user.email == "admin@surfacedetect.com" and user.password == "Admin@123":
        return {"success": True, "message": "Login Successful"}
    return {"success": False, "message": "Invalid Email or Password"}
```
This is a plaintext credential in a public repository, in a file separate from — and inconsistent with — `backend/auth.py`. It does not appear to be called by `app.py`, but being unused doesn't reduce the exposure: it's still committed and visible to anyone with repo access.
**Recommendation:** Delete this route entirely, or connect it to the same real auth logic as `backend/auth.py` if this FastAPI backend is meant to be used for something.

#### F-04: No server-side authorization check on the prediction/inference handlers
**File:** `app.py` — `run_dash_prediction()`, `run_predict_prediction()`
These functions are wired directly to their buttons (`dash_run.click(...)`, `pred_run.click(...)`) and call `predict_image()` without taking `auth_token` as an input or checking it at all. The only thing currently preventing an unauthenticated user from reaching these is that their containing UI section (`predict_page`, `dashboard_page`) is set to `visible=False` until login succeeds.
**Why this matters:** In Gradio, hiding a component in the browser does not remove its server-side event handler — the handler is still registered and reachable through Gradio's own API layer independent of what's visually shown. Visibility toggling is a UI convenience, not an access control mechanism.
**Recommendation:** Add an explicit check at the top of both handler functions — reject the request if `auth_token` (passed in as a `gr.State` input) is empty/invalid, rather than relying on the button being hidden.

### 🟠 HIGH

#### F-05: Forgot-password flow does not send anything or generate a real token
**File:** `backend/auth.py`, `send_reset_email()`
```python
def send_reset_email(email: str) -> dict:
    return {"success": True, "message": "Password reset link sent to your email."}
```
Always reports success with no email sent and no token created, despite `migrations/01-login.sql` already defining a `password_reset_tokens` table for exactly this purpose.
**Recommendation:** Generate a real token, store its hash with an expiry in `password_reset_tokens`, and send it via an email provider.

### 🟡 MEDIUM

#### F-06: Unsafe fallback default for the admin password
**File:** `backend/auth.py`
```python
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "Admin@123")
```
If `.env` is missing or misconfigured (e.g., a fresh clone, a new teammate, a misconfigured deployment), this silently falls back to a known plaintext password instead of failing loudly.
**Recommendation:**
```python
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
if not ADMIN_PASSWORD:
    raise RuntimeError("ADMIN_PASSWORD must be set in .env")
```

#### F-07: Password policy is only enforced client-side, and is weak
**File:** `app.py`, `handle_register()`
```python
if len(password) < 6:
    return gr.update(visible=True, value="Password must be at least 6 characters.")
```
This check lives in the Gradio event handler, not in `register_user()` itself — and once registration is actually connected to the database (F-01), this same handler is the only thing standing between a 1-character password and a stored account, if `register_user()` isn't called some other way. 6 characters is also a weak minimum by current standards.
**Recommendation:** Move validation into `register_user()` directly (defense in depth), and raise the minimum to 8+ characters with a basic complexity check.

#### F-08: `bcrypt` dependency present but unused
**File:** `requirements.txt` lists `bcrypt==4.3.0`, but no file under `backend/` or `src/` imports it.
**Recommendation:** Either finish wiring it into real password hashing (resolves F-01/F-02), or remove the unused dependency to avoid confusion about what's actually implemented.

### 🟢 LOW

#### F-09: No brute-force lockout logic in code
`migrations/01-login.sql` defines `failed_login_attempts` and `locked_until` columns on `users`, but nothing in `backend/auth.py` reads or writes them yet. Not exploitable today only because there's no real login path to brute-force in the first place (F-02) — but should be implemented alongside the real login logic, not after.

---

## 3. What's Already Done Well

- **GitHub OAuth login is implemented correctly.** `get_github_login_url()` and `complete_github_login()` in `backend/auth.py` delegate to Supabase's real OAuth flow — this is genuinely secure and not something to change.
- **Database schema is solid.** `migrations/01-login.sql` defines hashed passwords, sessions, password reset tokens, and a login audit log — everything needed is already modeled; it just isn't connected to the email/password code path yet.
- **`.env` is correctly git-ignored**, and `backend/database.py` properly separates the anon key from the service-role key.

---

## 4. Summary Table

| ID | Finding | Severity | File |
|----|---------|----------|------|
| F-01 | Registration doesn't persist users | 🔴 Critical | `backend/auth.py` |
| F-02 | Login only recognizes hardcoded admin | 🔴 Critical | `backend/auth.py` |
| F-03 | Duplicate hardcoded credential | 🔴 Critical | `backend/main.py` |
| F-04 | No server-side check on prediction handlers | 🔴 Critical | `app.py` |
| F-05 | Forgot-password flow non-functional | 🟠 High | `backend/auth.py` |
| F-06 | Unsafe `.env` fallback default | 🟡 Medium | `backend/auth.py` |
| F-07 | Password policy client-side only, weak | 🟡 Medium | `app.py` |
| F-08 | Unused `bcrypt` dependency | 🟡 Medium | `requirements.txt` |
| F-09 | No brute-force lockout logic | 🟢 Low | `backend/auth.py` |

---

## 5. Recommended Priority Order

1. **F-03** — Delete the duplicate hardcoded credential in `backend/main.py` (quickest fix, public exposure)
2. **F-04** — Add real server-side auth checks to the prediction handlers in `app.py`
3. **F-01 / F-02** — Connect registration and login to Supabase with real bcrypt hashing and real session tokens
4. **F-06** — Remove the unsafe fallback once real credential handling is in place
5. **F-05** — Implement the real forgot-password flow
6. **F-07 / F-08 / F-09** — Hardening, once the core flow is real

---

## 6. Issues to File

**Issue: Remove duplicate hardcoded credential from backend/main.py**
> A second, independent hardcoded admin login exists in `backend/main.py`, separate from `backend/auth.py`. Delete it or connect it to real auth logic.
> Severity: Critical

**Issue: Add server-side auth checks to prediction handlers**
> `run_dash_prediction()` and `run_predict_prediction()` in `app.py` don't check `auth_token` before running inference — only the surrounding UI is hidden pre-login, which isn't a real access control in Gradio's client-server model.
> Severity: Critical

**Issue: Connect registration/login to Supabase with bcrypt hashing**
> `register_user()` and `login_user()` in `backend/auth.py` are still mock logic with no real database read/write.
> Severity: Critical

**Issue: Implement real password reset flow**
> `send_reset_email()` always returns success without sending anything or creating a reset token.
> Severity: High

---

## 7. Review Log

| Date | Reviewer | Notes |
|------|----------|-------|
| 2026-07-13 | N.Varshashri | Audit of current Gradio-based app.py architecture — findings F-01 through F-09 logged |
| | | |
