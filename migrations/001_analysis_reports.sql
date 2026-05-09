-- ALAS Migration 001 — analysis_reports
-- Run once against your NeonDB instance.

CREATE TABLE IF NOT EXISTS analysis_reports (
    id            SERIAL PRIMARY KEY,
    user_id       INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title         TEXT NOT NULL,
    filename      TEXT NOT NULL,
    disk_path     TEXT NOT NULL,
    size_bytes    BIGINT NOT NULL DEFAULT 0,
    share_token   TEXT UNIQUE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_analysis_reports_user_id
    ON analysis_reports(user_id);

CREATE INDEX IF NOT EXISTS idx_analysis_reports_share_token
    ON analysis_reports(share_token)
    WHERE share_token IS NOT NULL;
