-- Prompt version history for the instructions editor
CREATE TABLE IF NOT EXISTS liquidround.prompt_versions (
    id SERIAL PRIMARY KEY,
    slug VARCHAR(255) NOT NULL,
    content TEXT NOT NULL DEFAULT '',
    changed_by VARCHAR(255) DEFAULT 'web-editor',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_prompt_versions_slug ON liquidround.prompt_versions(slug);
