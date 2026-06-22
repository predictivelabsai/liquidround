-- Digest archive — persist every daily digest for blog + history.
CREATE TABLE IF NOT EXISTS liquidround.digest_archive (
    id               SERIAL PRIMARY KEY,
    digest_date      DATE NOT NULL UNIQUE,
    slug             TEXT NOT NULL UNIQUE,
    title            TEXT NOT NULL,
    digest_json      JSONB NOT NULL,
    blog_html        TEXT NOT NULL,
    company_count    INTEGER NOT NULL DEFAULT 0,
    featured_company TEXT,
    beehiiv_post_id  TEXT,
    beehiiv_url      TEXT,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_digest_archive_date ON liquidround.digest_archive (digest_date DESC);
