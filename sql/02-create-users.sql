-- LiquidRound Users & Auth (PostgreSQL)
-- Run after 01 (create-tables.sql)

CREATE TABLE IF NOT EXISTS liquidround.users (
    id SERIAL PRIMARY KEY,
    user_id UUID UNIQUE NOT NULL DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255),
    google_id VARCHAR(255) UNIQUE,
    display_name VARCHAR(255),
    is_admin BOOLEAN NOT NULL DEFAULT FALSE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_lr_users_user_id ON liquidround.users(user_id);
CREATE INDEX IF NOT EXISTS idx_lr_users_email ON liquidround.users(email);
CREATE INDEX IF NOT EXISTS idx_lr_users_google_id ON liquidround.users(google_id);

CREATE TABLE IF NOT EXISTS liquidround.password_reset_tokens (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES liquidround.users(user_id) ON DELETE CASCADE,
    token VARCHAR(128) UNIQUE NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    used_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_lr_reset_token ON liquidround.password_reset_tokens(token);
CREATE INDEX IF NOT EXISTS idx_lr_reset_user ON liquidround.password_reset_tokens(user_id);

-- Add user_id to existing tables for multi-tenancy
ALTER TABLE liquidround.workflows ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES liquidround.users(user_id);
ALTER TABLE liquidround.deals ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES liquidround.users(user_id);
ALTER TABLE liquidround.documents ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES liquidround.users(user_id);

CREATE INDEX IF NOT EXISTS idx_lr_workflows_user ON liquidround.workflows(user_id);
CREATE INDEX IF NOT EXISTS idx_lr_deals_user ON liquidround.deals(user_id);
