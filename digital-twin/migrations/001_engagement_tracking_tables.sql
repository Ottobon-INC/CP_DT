-- ============================================================
-- Digital Twin: New Tables for Engagement Tracking
-- Run this in your Supabase SQL Editor
-- ============================================================

-- 1. Login Session Tracking
CREATE TABLE IF NOT EXISTS learner_login_sessions (
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    learner_id UUID NOT NULL,
    login_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    logout_at TIMESTAMPTZ,
    duration_seconds INTEGER,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_login_sessions_learner 
    ON learner_login_sessions(learner_id);
CREATE INDEX IF NOT EXISTS idx_login_sessions_login_at 
    ON learner_login_sessions(login_at DESC);


-- 2. Engagement Snapshots
CREATE TABLE IF NOT EXISTS learner_engagement_snapshots (
    snapshot_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    learner_id UUID NOT NULL,
    course_id UUID NOT NULL,
    snapshot_date DATE NOT NULL DEFAULT CURRENT_DATE,
    overall_progress_pct FLOAT DEFAULT 0,
    modules_completed INTEGER DEFAULT 0,
    total_modules INTEGER DEFAULT 0,
    days_since_last_login INTEGER,
    total_login_count INTEGER DEFAULT 0,
    avg_session_duration_seconds INTEGER DEFAULT 0,
    quiz_pass_rate FLOAT DEFAULT 0,
    avg_quiz_score FLOAT DEFAULT 0,
    total_quiz_attempts INTEGER DEFAULT 0,
    inactivity_stage INTEGER DEFAULT 0,
    engagement_score FLOAT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(learner_id, course_id, snapshot_date)
);

CREATE INDEX IF NOT EXISTS idx_engagement_snapshots_learner 
    ON learner_engagement_snapshots(learner_id);
CREATE INDEX IF NOT EXISTS idx_engagement_snapshots_course 
    ON learner_engagement_snapshots(learner_id, course_id);
CREATE INDEX IF NOT EXISTS idx_engagement_snapshots_date 
    ON learner_engagement_snapshots(snapshot_date DESC);


-- 3. Module Deadlines (Simple weekly check)
CREATE TABLE IF NOT EXISTS module_deadline_state (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    learner_id UUID NOT NULL,
    course_id UUID NOT NULL,
    module_no INTEGER NOT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deadline_at TIMESTAMPTZ NOT NULL,  -- started_at + 7 days
    is_completed BOOLEAN DEFAULT false,
    completed_at TIMESTAMPTZ,
    email_sent_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(learner_id, course_id, module_no)
);

CREATE INDEX IF NOT EXISTS idx_module_deadline_learner 
    ON module_deadline_state(learner_id);
CREATE INDEX IF NOT EXISTS idx_module_deadline_lookup 
    ON module_deadline_state(learner_id, course_id, module_no);


