-- Prompt versioning: audit trail for agent system prompts
CREATE TABLE IF NOT EXISTS liquidround.prompt_versions (
    id          BIGSERIAL PRIMARY KEY,
    slug        TEXT        NOT NULL,
    content     TEXT        NOT NULL,
    changed_by  TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS prompt_versions_slug_idx
    ON liquidround.prompt_versions(slug, id DESC);
