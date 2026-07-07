# Authentication Audit Report

**Project:** Surface Crack Detection — Bootcamp ACE 26, Team 7

**Repository:** https://github.com/esetu-git-public/bootcamp-ace-26-team-7

**Audit Date:** July 7, 2026

**Auditor:** N.Varshashri

**Scope:** Login, Registration, Forgot Password, Session Handling, Route Protection

**Files Reviewed:**
- `backend/auth.py`
- `backend/main.py`
- `backend/database.py`
- `pages/login.py`, `pages/register.py`, `pages/forgotpwd.py`, `pages/Home.py`
- `app.py`
- `migrations/01-login.sql`
- `.env.example`, `requirements.txt`, `.gitignore`

---

## 1. Executive Summary

The authentication **database schema** (`migrations/01-login.sql`) is well designed — it includes hashed passwords, session tracking, password-reset tokens, login audit logging, and brute-force lockout fields. However, the **actual authentication code in `backend/auth.py` does not use this schema at all.**

Login, registration, and password reset are currently implemented as **hardcoded mock functions** with no connection to the Supabase database. This means:
- There is a single hardcoded admin account with a plaintext password checked into source control.
- No user who registers is actually saved anywhere.
- The session/access token is a fixed string, not a real, verifiable token.
- Protected pages (e.g. `Home.py`) do not check whether a user is logged in at all.

**This is expected for an early-stage bootcamp prototype**, but it should not be mistaken for a working auth system, and none of it should reach a real deployment with real user data in its current state. The findings below are organized by severity so the team can prioritize fixes.

---

## 2. Findings

### 🔴 CRITICAL

#### F-01: Hardcoded admin credentials in source code
**File:** `backend/auth.py`, lines 3–4
```python
ADMIN_EMAIL = "admin@surfacedetect.com"
ADMIN_PASSWORD = "Admin@123"
```
**Risk:** The only working login credential is committed in plaintext to a **public GitHub repository**. Anyone can view the source and log in as admin. Since it's in git history, even removing it later won't delete it from past commits.
**Recommendation:** Remove immediately. Move any admin bootstrap credential to an environment variable or a securely seeded database row with a hashed password. Rotate this password now since it's already public.

#### F-02: No password hashing — passwords are not actually stored
**File:** `backend/auth.py`, `register_user()` (lines 8–14)
**Risk:** `register_user()` returns a success response but never writes to the database. There is no `bcrypt`/`argon2` hashing anywhere in the codebase, and neither library is even in `requirements.txt`. Registration currently does nothing persistent — it just tells the user it worked.
**Recommendation:** Implement real registration: hash the password (bcrypt or argon2) and insert a row into the `users` table defined in `migrations/01-login.sql`, which already has a `password_hash` column ready for this.

#### F-03: Login token is a hardcoded string, not a real session/JWT
**File:** `backend/auth.py`, line 22
```python
"access_token": "hardcoded-admin-token",
```
**Risk:** This is not a signed, expiring, or verifiable token — it's a fixed string returned to every successful login. It is never validated against anything on subsequent requests, meaning any client could just hardcode this same string and skip login entirely by setting it directly in session state.
**Recommendation:** Issue a real signed token (JWT via `python-jose` or similar) or use Supabase Auth's built-in session tokens, and populate the `sessions` table already defined in the schema (`token_hash`, `expires_at`, `revoked_at`).

#### F-04: No authentication check on protected pages
**File:** `pages/Home.py` (entire file)
**Risk:** `Home.py` — the page with image upload and the ML prediction feature — never checks `st.session_state.get("access_token")` or `user`. Anyone can navigate directly to `pages/Home.py` in the browser and use the full app **without logging in at all.** The login page is effectively decorative.
**Recommendation:** Add a guard at the top of every protected page:
```python
if not st.session_state.get("access_token"):
    st.warning("Please log in first.")
    st.switch_page("pages/login.py")
    st.stop()
```

### 🟠 HIGH

#### F-05: Forgot-password flow does not send anything or generate a real token
**File:** `backend/auth.py`, `send_reset_email()` (lines 32–33)
**Risk:** This function always returns success regardless of whether the email exists, and never generates a `password_reset_tokens` row or sends an email. Users are told a reset link was sent when nothing happens — this could confuse real users and hides a completely missing feature.
**Recommendation:** Implement real token generation (store a hash in `password_reset_tokens`, matching the schema), send via an email provider, and expire tokens after use per the `used_at` field already designed.

#### F-06: Backend has no auth on the `/predict` endpoint
**File:** `backend/main.py`, lines 73–76
**Risk:** The FastAPI `/predict` endpoint has no dependency requiring a valid token. If this API is ever exposed publicly (vs. only used internally by Streamlit), anyone can call it directly and run inference without logging in.
**Recommendation:** Add a FastAPI dependency that validates a bearer token before allowing access to `/predict` and any other non-public route.

#### F-07: Insecure CORS configuration
**File:** `backend/main.py`, lines 16–22
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    ...
)
```
**Risk:** `allow_origins=["*"]` combined with `allow_credentials=True` is a known insecure pattern (and is actually rejected by browsers per the CORS spec when credentials are involved, so this may silently fail in practice, or work around it via a misconfigured proxy). It's a sign that origin restrictions haven't been considered yet.
**Recommendation:** Restrict `allow_origins` to the specific frontend domain(s) that need access once deployed.

### 🟡 MEDIUM

#### F-08: No brute-force protection despite schema support
**File:** `backend/auth.py`, `login_user()`
**Risk:** `migrations/01-login.sql` defines `failed_login_attempts` and `locked_until` columns, and a full `login_audit_log` table — but none of this is used in code. There is currently no limit on login attempts.
**Recommendation:** Increment `failed_login_attempts` on failed logins, lock the account temporarily after a threshold (e.g. 5 attempts), and log every attempt to `login_audit_log`.

#### F-09: No server-side password policy enforcement
**File:** `pages/register.py`, line 29 vs. `backend/auth.py`
**Risk:** The 6-character minimum password check happens only in the Streamlit frontend (`pages/register.py`). Since `register_user()` in the backend doesn't validate anything, calling the API directly (e.g. via `/register` in `backend/main.py`) bypasses this check entirely.
**Recommendation:** Enforce password policy (length, complexity) inside `register_user()` itself, not just the UI layer.

### 🟢 LOW

#### F-10: Weak minimum password length
**File:** `pages/register.py`, line 29
**Risk:** A 6-character minimum is on the low end for current standards.
**Recommendation:** Consider raising to 8+ characters with a complexity or breached-password check (e.g. via `zxcvbn` or checking against Have I Been Pwned's API), once real registration is implemented.

---

## 3. What's Already Done Well

To keep this balanced for future reviewers:
- `.env` is correctly excluded via `.gitignore` — Supabase credentials are not committed.
- Supabase client setup (`backend/database.py`) correctly separates the anon key from the service-role key, which is the right pattern for least-privilege access.
- The **database schema design** (`migrations/01-login.sql`) is genuinely solid: hashed passwords, session table, reset-token table, audit log, and lockout fields are all present and well-commented. The team clearly planned for real security — it just hasn't been wired up to the actual auth code yet.

---

## 4. Summary Table

| ID | Finding | Severity | File | Status |
|----|---------|----------|------|--------|
| F-01 | Hardcoded admin credentials in source | 🔴 Critical | `backend/auth.py` | Open |
| F-02 | No password hashing / persistence | 🔴 Critical | `backend/auth.py` | Open |
| F-03 | Fake, non-expiring access token | 🔴 Critical | `backend/auth.py` | Open |
| F-04 | No auth check on protected pages | 🔴 Critical | `pages/Home.py` | Open |
| F-05 | Forgot-password flow is non-functional | 🟠 High | `backend/auth.py` | Open |
| F-06 | `/predict` endpoint has no auth | 🟠 High | `backend/main.py` | Open |
| F-07 | Insecure CORS (`*` + credentials) | 🟠 High | `backend/main.py` | Open |
| F-08 | No brute-force lockout logic | 🟡 Medium | `backend/auth.py` | Open |
| F-09 | Password policy not enforced server-side | 🟡 Medium | `backend/auth.py` | Open |
| F-10 | Weak minimum password length | 🟢 Low | `pages/register.py` | Open |

---

## 5. Recommended Priority Order

1. **F-01** — Remove hardcoded credentials from the repo immediately (public exposure).
2. **F-04** — Add login checks to protected pages (currently zero access control).
3. **F-02 / F-03** — Implement real registration + real session tokens together, since they're linked.
4. **F-06 / F-07** — Lock down the API layer (auth dependency + CORS).
5. **F-05** — Implement real forgot-password flow.
6. **F-08 / F-09 / F-10** — Hardening once the core flow is real.

---


---

## 6. Review Log (for future audits)

| Date | Reviewer | Notes |
|------|----------|-------|
| 2026-07-07 | N.Varshashri | Initial audit — findings F-01 through F-10 logged |
| | | |
| | | |

---
*This document should be updated each time the auth system changes, so future reviewers can see what was already flagged vs. newly introduced.*
