-- ============================================================================
-- Surface Crack Detection — Auth / Login Schema (Phase 1)
-- Bootcamp ACE 26 — Team 7
--
-- Covers user accounts, roles, sessions, and password reset — the minimum
-- needed for a working login system. Extend later if you add OAuth/SSO.
--
-- Usage:
--   psql -d crack_detection -f auth_schema.sql
--   psql -d crack_detection -f auth_seed.sql   (optional, seeds roles + admin)
-- ============================================================================

BEGIN;

CREATE EXTENSION IF NOT EXISTS "pgcrypto";   -- for gen_random_uuid()

-- Enum types -------------------------------------------------------------
DO $$ BEGIN
    CREATE TYPE user_role AS ENUM ('admin', 'member', 'viewer');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- ============================================================================
-- 1. USERS
-- ============================================================================
CREATE TABLE IF NOT EXISTS users (
    user_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           VARCHAR(255) NOT NULL UNIQUE,
    username        VARCHAR(50) NOT NULL UNIQUE,
    password_hash   TEXT NOT NULL,             -- bcrypt/argon2 hash, never plaintext
    full_name       VARCHAR(150),
    role            user_role NOT NULL DEFAULT 'member',
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    is_verified     BOOLEAN NOT NULL DEFAULT FALSE,
    failed_login_attempts SMALLINT NOT NULL DEFAULT 0,
    locked_until    TIMESTAMPTZ,               -- basic brute-force lockout
    last_login_at   TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_username ON users(username);

COMMENT ON TABLE users IS 'Team member accounts for the project dashboard/tooling';
COMMENT ON COLUMN users.password_hash IS 'Store only a salted hash (bcrypt/argon2) — never plaintext or reversible encryption';

-- Auto-update updated_at on row changes
CREATE OR REPLACE FUNCTION set_updated_at() RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_users_updated_at ON users;
CREATE TRIGGER trg_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ============================================================================
-- 2. SESSIONS — active login sessions (for server-side session/JWT tracking)
-- ============================================================================
CREATE TABLE IF NOT EXISTS sessions (
    session_id    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    token_hash    TEXT NOT NULL UNIQUE,        -- hash of the session/JWT token, not the raw token
    ip_address    INET,
    user_agent    TEXT,
    expires_at    TIMESTAMPTZ NOT NULL,
    revoked_at    TIMESTAMPTZ,                 -- set on logout / manual revoke
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_sessions_expires_at ON sessions(expires_at);

COMMENT ON TABLE sessions IS 'Active/past login sessions; used to support logout-everywhere and expiry checks';

-- ============================================================================
-- 3. PASSWORD_RESET_TOKENS
-- ============================================================================
CREATE TABLE IF NOT EXISTS password_reset_tokens (
    token_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    token_hash    TEXT NOT NULL UNIQUE,
    expires_at    TIMESTAMPTZ NOT NULL,
    used_at       TIMESTAMPTZ,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_reset_tokens_user_id ON password_reset_tokens(user_id);

COMMENT ON TABLE password_reset_tokens IS 'Short-lived tokens for the forgot-password flow; single-use via used_at';

-- ============================================================================
-- 4. LOGIN_AUDIT_LOG — record every login attempt (success or fail)
-- ============================================================================
CREATE TABLE IF NOT EXISTS login_audit_log (
    log_id        BIGSERIAL PRIMARY KEY,
    user_id       UUID REFERENCES users(user_id) ON DELETE SET NULL,
    email_attempted VARCHAR(255),              -- kept even if user_id is null (unknown email attempt)
    success       BOOLEAN NOT NULL,
    ip_address    INET,
    user_agent    TEXT,
    failure_reason VARCHAR(100),               -- 'bad_password' | 'no_such_user' | 'locked' | 'inactive'
    attempted_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_login_audit_user_id ON login_audit_log(user_id);
CREATE INDEX idx_login_audit_attempted_at ON login_audit_log(attempted_at);

COMMENT ON TABLE login_audit_log IS 'Every login attempt, for lockout logic and security review';

COMMIT;
