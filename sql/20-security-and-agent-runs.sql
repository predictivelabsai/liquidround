-- Security hardening and structured agent-run observability.

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'liquidround'
          AND table_name = 'fund_bookmarks'
          AND column_name = 'user_id'
          AND data_type IN ('integer', 'bigint')
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'liquidround'
          AND table_name = 'fund_bookmarks_integer_legacy'
    ) THEN
        ALTER TABLE liquidround.fund_bookmarks RENAME TO fund_bookmarks_integer_legacy;
        ALTER INDEX IF EXISTS liquidround.ix_fund_bookmarks_user
            RENAME TO ix_fund_bookmarks_integer_legacy_user;
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS liquidround.fund_bookmarks (
    id          BIGSERIAL PRIMARY KEY,
    user_id     UUID NOT NULL REFERENCES liquidround.users(user_id) ON DELETE CASCADE,
    fund_name   TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(user_id, fund_name)
);
CREATE INDEX IF NOT EXISTS ix_fund_bookmarks_user
    ON liquidround.fund_bookmarks (user_id);

ALTER TABLE liquidround.messages
    ADD COLUMN IF NOT EXISTS agent_slug TEXT,
    ADD COLUMN IF NOT EXISTS metadata JSONB NOT NULL DEFAULT '{}'::jsonb;

ALTER TABLE liquidround.prompt_versions
    ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'archived';
CREATE INDEX IF NOT EXISTS ix_prompt_versions_published
    ON liquidround.prompt_versions (slug, id DESC)
    WHERE status = 'published';

CREATE TABLE IF NOT EXISTS liquidround.agent_runs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id     UUID REFERENCES liquidround.workflows(id) ON DELETE SET NULL,
    user_id         UUID REFERENCES liquidround.users(user_id) ON DELETE SET NULL,
    agent_slug      TEXT NOT NULL,
    router_payload  JSONB NOT NULL DEFAULT '{}'::jsonb,
    prompt_version  TEXT,
    model_provider  TEXT,
    model_name      TEXT,
    tool_calls      JSONB NOT NULL DEFAULT '[]'::jsonb,
    artifacts       JSONB NOT NULL DEFAULT '[]'::jsonb,
    status          TEXT NOT NULL DEFAULT 'running'
                    CHECK (status IN ('running', 'completed', 'failed', 'cancelled')),
    latency_ms      INTEGER,
    input_tokens    INTEGER,
    output_tokens   INTEGER,
    estimated_cost NUMERIC,
    error_code      TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at    TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS ix_agent_runs_user_created
    ON liquidround.agent_runs (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS ix_agent_runs_workflow
    ON liquidround.agent_runs (workflow_id, created_at);
