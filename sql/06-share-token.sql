-- Add share_token column to workflows for shareable chat links
ALTER TABLE liquidround.workflows ADD COLUMN IF NOT EXISTS share_token VARCHAR(64);
CREATE INDEX IF NOT EXISTS idx_workflows_share_token ON liquidround.workflows(share_token) WHERE share_token IS NOT NULL;
