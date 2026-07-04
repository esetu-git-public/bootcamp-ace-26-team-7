-- ============================================================================
-- Surface Crack Detection — PostgreSQL Schema
-- Bootcamp ACE 26 — Team 7
--
-- Covers the full pipeline: raw images -> dataset splits -> training runs
-- -> per-epoch metrics -> checkpoints -> predictions/evaluation.
--
-- Usage:
--   createdb crack_detection
--   psql -d crack_detection -f schema.sql
--   psql -d crack_detection -f seed.sql   (optional, seeds the 4 classes)
-- ============================================================================

BEGIN;

-- Extensions -----------------------------------------------------------------
CREATE EXTENSION IF NOT EXISTS "pgcrypto";   -- for gen_random_uuid()

-- Enum types -------------------------------------------------------------
DO $$ BEGIN
    CREATE TYPE dataset_split AS ENUM ('train', 'val', 'test');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE run_status AS ENUM ('pending', 'running', 'completed', 'failed', 'stopped');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE training_phase AS ENUM ('warmup', 'fine_tune');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE metric_phase AS ENUM ('train', 'val', 'test');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- ============================================================================
-- 1. CLASSES — the 4 defect categories
-- ============================================================================
CREATE TABLE IF NOT EXISTS classes (
    class_id     SMALLSERIAL PRIMARY KEY,
    class_name   VARCHAR(50) NOT NULL UNIQUE,
    description  TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE classes IS 'The 4 target defect categories: Cracks, Patch, Potholes, Surface Defects';

-- ============================================================================
-- 2. IMAGES — raw dataset inventory (the 306 source images)
-- ============================================================================
CREATE TABLE IF NOT EXISTS images (
    image_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filename      VARCHAR(255) NOT NULL,
    filepath      TEXT NOT NULL UNIQUE,       -- e.g. data/raw/cracks/img_0012.jpg
    class_id      SMALLINT NOT NULL REFERENCES classes(class_id) ON DELETE RESTRICT,
    split         dataset_split,              -- NULL until prepare_data.py assigns it
    width_px      INTEGER,
    height_px     INTEGER,
    channels      SMALLINT DEFAULT 3,
    file_size_kb  NUMERIC(10,2),
    checksum_sha256 CHAR(64),                 -- dedupe / integrity check
    source        VARCHAR(100),               -- e.g. 'kaggle_road_damage_v1'
    is_augmented  BOOLEAN NOT NULL DEFAULT FALSE,
    parent_image_id UUID REFERENCES images(image_id) ON DELETE SET NULL, -- if augmented from another image
    uploaded_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    uploaded_by   VARCHAR(100)
);

CREATE INDEX IF NOT EXISTS idx_images_class_id ON images(class_id);
CREATE INDEX IF NOT EXISTS idx_images_split ON images(split);
CREATE UNIQUE INDEX IF NOT EXISTS idx_images_checksum ON images(checksum_sha256) WHERE checksum_sha256 IS NOT NULL;

COMMENT ON TABLE images IS 'Inventory of source images with class label and stratified split assignment';

-- ============================================================================
-- 3. MODEL_RUNS — one row per training experiment
-- ============================================================================
CREATE TABLE IF NOT EXISTS model_runs (
    run_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_name         VARCHAR(150) NOT NULL,
    backbone         VARCHAR(50) NOT NULL,        -- 'ResNet50' | 'EfficientNet-B0' | 'BaselineCNN'
    phase            training_phase NOT NULL DEFAULT 'warmup',
    frozen_backbone  BOOLEAN NOT NULL DEFAULT TRUE,
    epochs_planned   INTEGER NOT NULL,
    epochs_run       INTEGER,
    learning_rate    NUMERIC(10,8) NOT NULL,
    optimizer        VARCHAR(30) NOT NULL DEFAULT 'AdamW',
    loss_function    VARCHAR(50) NOT NULL DEFAULT 'WeightedCrossEntropy',
    scheduler        VARCHAR(50) DEFAULT 'CosineAnnealingLR',
    batch_size       INTEGER,
    early_stop_patience INTEGER DEFAULT 7,
    mixed_precision  BOOLEAN DEFAULT FALSE,
    status           run_status NOT NULL DEFAULT 'pending',
    git_commit_hash  VARCHAR(40),               -- reproducibility: link run to code version
    config_json      JSONB,                     -- full config.py snapshot
    started_at       TIMESTAMPTZ,
    finished_at      TIMESTAMPTZ,
    created_by       VARCHAR(100),
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_model_runs_status ON model_runs(status);
CREATE INDEX IF NOT EXISTS idx_model_runs_backbone ON model_runs(backbone);

COMMENT ON TABLE model_runs IS 'One row per training experiment/run, capturing hyperparameters for reproducibility';

-- ============================================================================
-- 4. TRAINING_METRICS — per-epoch metrics logged during training
-- ============================================================================
CREATE TABLE IF NOT EXISTS training_metrics (
    metric_id     BIGSERIAL PRIMARY KEY,
    run_id        UUID NOT NULL REFERENCES model_runs(run_id) ON DELETE CASCADE,
    epoch         INTEGER NOT NULL,
    phase         metric_phase NOT NULL,
    loss          NUMERIC(10,6),
    accuracy      NUMERIC(6,5),
    precision_macro NUMERIC(6,5),
    recall_macro  NUMERIC(6,5),
    f1_macro      NUMERIC(6,5),
    learning_rate NUMERIC(10,8),
    duration_sec  NUMERIC(8,2),
    logged_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (run_id, epoch, phase)
);

CREATE INDEX IF NOT EXISTS idx_training_metrics_run_id ON training_metrics(run_id);

COMMENT ON TABLE training_metrics IS 'Per-epoch train/val metrics logged by train.py';

-- ============================================================================
-- 5. MODEL_CHECKPOINTS — saved weights per run
-- ============================================================================
CREATE TABLE IF NOT EXISTS model_checkpoints (
    checkpoint_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id        UUID NOT NULL REFERENCES model_runs(run_id) ON DELETE CASCADE,
    epoch         INTEGER NOT NULL,
    filepath      TEXT NOT NULL,          -- e.g. models/resnet50_run3_epoch12.pt
    val_f1        NUMERIC(6,5),
    val_loss      NUMERIC(10,6),
    is_best       BOOLEAN NOT NULL DEFAULT FALSE,
    file_size_mb  NUMERIC(8,2),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_checkpoints_run_id ON model_checkpoints(run_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_one_best_per_run ON model_checkpoints(run_id) WHERE is_best;

COMMENT ON TABLE model_checkpoints IS 'ModelCheckpoint callback outputs; only one is_best=TRUE row allowed per run';

-- ============================================================================
-- 6. PREDICTIONS — per-image inference results for a given run
-- ============================================================================
CREATE TABLE IF NOT EXISTS predictions (
    prediction_id     BIGSERIAL PRIMARY KEY,
    run_id            UUID NOT NULL REFERENCES model_runs(run_id) ON DELETE CASCADE,
    image_id          UUID NOT NULL REFERENCES images(image_id) ON DELETE CASCADE,
    checkpoint_id     UUID REFERENCES model_checkpoints(checkpoint_id) ON DELETE SET NULL,
    predicted_class_id SMALLINT NOT NULL REFERENCES classes(class_id),
    true_class_id     SMALLINT NOT NULL REFERENCES classes(class_id),
    confidence        NUMERIC(6,5) NOT NULL CHECK (confidence BETWEEN 0 AND 1),
    is_correct         BOOLEAN GENERATED ALWAYS AS (predicted_class_id = true_class_id) STORED,
    class_probabilities JSONB,           -- full softmax vector, e.g. {"Cracks":0.81,...}
    predicted_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (run_id, image_id)
);

CREATE INDEX IF NOT EXISTS idx_predictions_run_id ON predictions(run_id);
CREATE INDEX IF NOT EXISTS idx_predictions_image_id ON predictions(image_id);
CREATE INDEX IF NOT EXISTS idx_predictions_correct ON predictions(is_correct);

COMMENT ON TABLE predictions IS 'Per-image predictions produced by evaluate.py for a given run/checkpoint';

-- ============================================================================
-- 7. EVALUATION_RESULTS — aggregate metrics per run per split
-- ============================================================================
CREATE TABLE IF NOT EXISTS evaluation_results (
    eval_id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id            UUID NOT NULL REFERENCES model_runs(run_id) ON DELETE CASCADE,
    split             dataset_split NOT NULL,
    accuracy          NUMERIC(6,5),
    precision_macro   NUMERIC(6,5),
    recall_macro      NUMERIC(6,5),
    f1_macro          NUMERIC(6,5),
    f1_weighted       NUMERIC(6,5),
    confusion_matrix  JSONB,             -- 4x4 matrix as nested array
    per_class_metrics JSONB,             -- {"Cracks": {"precision":.., "recall":.., "f1":..}, ...}
    report_path       TEXT,              -- reports/ path to figures/logs for this eval
    evaluated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (run_id, split)
);

CREATE INDEX IF NOT EXISTS idx_eval_results_run_id ON evaluation_results(run_id);

COMMENT ON TABLE evaluation_results IS 'Aggregate evaluation metrics per run/split, output of evaluate.py';

COMMIT;
-- ============================================================================
-- Seed data — the 4 defect classes (from README dataset overview)
-- Run after schema.sql
-- ============================================================================

INSERT INTO classes (class_name, description) VALUES
    ('Cracks',          'Linear surface cracks on road/bridge surfaces (73 images, 23.9%)'),
    ('Patch',           'Repaired/patched sections of pavement (42 images, 13.7%)'),
    ('Potholes',        'Potholes and surface cavities (91 images, 29.7%)'),
    ('Surface Defects', 'General surface defects not covered above (100 images, 32.7%)')
ON CONFLICT (class_name) DO NOTHING;

-- Example: register a training run matching Phase 1 (warmup) from the README
-- Uncomment and adjust once you actually kick off a run via train.py
--
-- INSERT INTO model_runs (
--     run_name, backbone, phase, frozen_backbone,
--     epochs_planned, learning_rate, optimizer, loss_function,
--     scheduler, early_stop_patience, status
-- ) VALUES (
--     'resnet50_warmup_v1', 'ResNet50', 'warmup', TRUE,
--     10, 0.001, 'AdamW', 'WeightedCrossEntropy',
--     'CosineAnnealingLR', 7, 'pending'
-- );
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

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);

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

CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_expires_at ON sessions(expires_at);

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

CREATE INDEX IF NOT EXISTS idx_reset_tokens_user_id ON password_reset_tokens(user_id);

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

CREATE INDEX IF NOT EXISTS idx_login_audit_user_id ON login_audit_log(user_id);
CREATE INDEX IF NOT EXISTS idx_login_audit_attempted_at ON login_audit_log(attempted_at);

COMMENT ON TABLE login_audit_log IS 'Every login attempt, for lockout logic and security review';

COMMIT;
-- ============================================================================
-- Seed data — auth schema
-- Run after auth_schema.sql
--
-- NOTE: password_hash below is a placeholder. Generate a real bcrypt hash
-- in your app (e.g. Python: bcrypt.hashpw(b'yourpassword', bcrypt.gensalt()))
-- and replace it before running this against anything but local dev.
-- ============================================================================

INSERT INTO users (email, username, password_hash, full_name, role, is_verified)
VALUES (
    'admin@team7.local',
    'admin',
    '$2b$12$REPLACE_WITH_REAL_BCRYPT_HASH',
    'Team 7 Admin',
    'admin',
    TRUE
)
ON CONFLICT (email) DO NOTHING;
-- ============================================================================
-- Surface Crack Detection — Webapp Schema (Phase 2)
-- Supports the home.py flow: upload -> predict -> severity -> report
--
-- Depends on: schema.sql (classes, model_checkpoints) and auth_schema.sql (users)
-- Run after both of those.
--
-- Usage:
--   psql -d crack_detection -f webapp_schema.sql
--   psql -d crack_detection -f webapp_seed.sql
-- ============================================================================

BEGIN;

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================================
-- 1. SEVERITY_LEVELS — lookup table for the Severity section of the app
-- ============================================================================
CREATE TABLE IF NOT EXISTS severity_levels (
    severity_id   SMALLSERIAL PRIMARY KEY,
    label         VARCHAR(20) NOT NULL UNIQUE,     -- 'Low' | 'Medium' | 'High' | 'Critical'
    min_score     NUMERIC(4,3) NOT NULL,           -- inclusive lower bound, 0-1 scale
    max_score     NUMERIC(4,3) NOT NULL,           -- exclusive upper bound
    color_hex     VARCHAR(7),                      -- for UI badges, e.g. '#E2534A'
    description   TEXT,
    CHECK (min_score < max_score)
);

COMMENT ON TABLE severity_levels IS 'Maps a 0-1 severity score to a human label for display';

-- ============================================================================
-- 2. USER_UPLOADS — images a logged-in user submits through the homepage
-- ============================================================================
CREATE TABLE IF NOT EXISTS user_uploads (
    upload_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES users(user_id) ON DELETE SET NULL,
    filename        VARCHAR(255) NOT NULL,
    filepath        TEXT NOT NULL,               -- where the file was saved server-side
    selected_class  VARCHAR(50),                 -- the sidebar radio choice at upload time
    width_px        INTEGER,
    height_px       INTEGER,
    file_size_kb    NUMERIC(10,2),
    uploaded_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_user_uploads_user_id ON user_uploads(user_id);
CREATE INDEX IF NOT EXISTS idx_user_uploads_uploaded_at ON user_uploads(uploaded_at);

COMMENT ON TABLE user_uploads IS 'Images uploaded via the homepage file_uploader, separate from the training dataset (images table)';

-- ============================================================================
-- 3. INFERENCE_RESULTS — model prediction + severity for one upload
-- ============================================================================
CREATE TABLE IF NOT EXISTS inference_results (
    inference_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    upload_id         UUID NOT NULL REFERENCES user_uploads(upload_id) ON DELETE CASCADE,
    checkpoint_id     UUID REFERENCES model_checkpoints(checkpoint_id) ON DELETE SET NULL,
    predicted_class_id SMALLINT REFERENCES classes(class_id),
    confidence        NUMERIC(6,5) CHECK (confidence BETWEEN 0 AND 1),
    class_probabilities JSONB,                  -- full softmax vector for the "Prediction" section
    severity_score    NUMERIC(4,3) CHECK (severity_score BETWEEN 0 AND 1),
    severity_id       SMALLINT REFERENCES severity_levels(severity_id),
    inference_ms      NUMERIC(8,2),             -- latency, useful for perf display/debugging
    predicted_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (upload_id)                          -- one live result per upload; re-run = new upload row
);

CREATE INDEX IF NOT EXISTS idx_inference_upload_id ON inference_results(upload_id);
CREATE INDEX IF NOT EXISTS idx_inference_severity_id ON inference_results(severity_id);

COMMENT ON TABLE inference_results IS 'Prediction + severity for a single homepage upload — backs the Prediction and Severity sections';

-- ============================================================================
-- 4. REPORTS — generated "Final Report" text, one per inference
-- ============================================================================
CREATE TABLE IF NOT EXISTS reports (
    report_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    inference_id   UUID NOT NULL REFERENCES inference_results(inference_id) ON DELETE CASCADE,
    user_id        UUID REFERENCES users(user_id) ON DELETE SET NULL,
    report_text    TEXT NOT NULL,               -- the text shown in st.text_area / downloaded
    file_path      TEXT,                        -- if also saved to disk, e.g. reports/report_<id>.txt
    generated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    downloaded_at  TIMESTAMPTZ                  -- set when the user actually clicks Download
);

CREATE INDEX IF NOT EXISTS idx_reports_inference_id ON reports(inference_id);
CREATE INDEX IF NOT EXISTS idx_reports_user_id ON reports(user_id);

COMMENT ON TABLE reports IS 'Generated report text/file backing the Final Report section and Download Report button';

COMMIT;
-- ============================================================================
-- Seed data — severity levels (0-1 score scale, adjust thresholds as your
-- severity logic is finalized)
-- ============================================================================

INSERT INTO severity_levels (label, min_score, max_score, color_hex, description) VALUES
    ('Low',      0.000, 0.250, '#4CAF50', 'Minor/cosmetic defect, no immediate action needed'),
    ('Medium',   0.250, 0.550, '#FFC107', 'Noticeable defect, schedule inspection'),
    ('High',     0.550, 0.800, '#FF7A33', 'Significant defect, prioritize repair'),
    ('Critical', 0.800, 1.001, '#E2534A', 'Severe defect, urgent action required')
ON CONFLICT (label) DO NOTHING;

