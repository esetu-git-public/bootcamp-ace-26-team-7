-- ============================================================================
-- Surface Crack Detection — Feedback Schema (Phase 3)
-- Bootcamp ACE 26 — Team 7
--
-- Stores user feedback on predictions (star rating + optional comment).
-- The feedback table is referenced from backend/feedback.py.
--
-- Usage:
--   Run in Supabase SQL Editor or via psql:
--     psql -d <DB> -f migrations/03-feedback.sql
-- ============================================================================

BEGIN;

-- ============================================================================
-- 1. FEEDBACK
-- ============================================================================
CREATE TABLE IF NOT EXISTS feedback (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    predicted_class VARCHAR(50) NOT NULL,
    confidence      NUMERIC(6,5) CHECK (confidence BETWEEN 0 AND 1),
    rating          SMALLINT NOT NULL CHECK (rating BETWEEN 1 AND 5),
    comment         TEXT DEFAULT '',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_feedback_user_id ON feedback(user_id);
CREATE INDEX IF NOT EXISTS idx_feedback_predicted_class ON feedback(predicted_class);

COMMIT;