-- Scope editable agent skills to individual users while preserving a global baseline.

ALTER TABLE liquidround.prompt_versions
    ADD COLUMN IF NOT EXISTS user_id UUID
        REFERENCES liquidround.users(user_id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS ix_prompt_versions_user_published
    ON liquidround.prompt_versions (user_id, slug, id DESC)
    WHERE status = 'published';

-- The primary operator account predates database-backed administration.
UPDATE liquidround.users
SET is_admin = TRUE,
    updated_at = NOW()
WHERE lower(email) = 'kaljuvee@gmail.com'
  AND is_admin = FALSE;
