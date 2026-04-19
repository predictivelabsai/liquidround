-- Adds a per-user default role (buyer | seller | both) so the Configuration
-- screen's role selector can persist across sessions.
--
-- Idempotent — safe to re-run.

ALTER TABLE liquidround.users
    ADD COLUMN IF NOT EXISTS default_role VARCHAR(16);

-- Optional: seed existing rows to a sensible default (they can change it in /settings).
UPDATE liquidround.users
   SET default_role = 'buyer'
 WHERE default_role IS NULL;
