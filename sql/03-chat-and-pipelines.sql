-- LiquidRound: Chat persistence + Pipeline workspaces
-- Run after 02-create-users.sql

-- 1. Add conversation_title to workflows for chat history display
ALTER TABLE liquidround.workflows
    ADD COLUMN IF NOT EXISTS conversation_title VARCHAR(200);

-- 2. Index for user's conversations (chat history)
CREATE INDEX IF NOT EXISTS idx_lr_workflows_user_conv
    ON liquidround.workflows (user_id, workflow_type, created_at DESC);

-- 3. Pipeline items table
CREATE TABLE IF NOT EXISTS liquidround.pipeline_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES liquidround.users(user_id) ON DELETE CASCADE,
    pipeline_type VARCHAR(10) NOT NULL CHECK (pipeline_type IN ('target', 'buyer')),
    company_name TEXT NOT NULL,
    stage VARCHAR(30) NOT NULL,
    score INTEGER,
    workflow_id UUID REFERENCES liquidround.workflows(id),
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_lr_pipeline_user
    ON liquidround.pipeline_items (user_id, pipeline_type);
CREATE INDEX IF NOT EXISTS idx_lr_pipeline_stage
    ON liquidround.pipeline_items (stage);
