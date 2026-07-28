-- Merger-topic press releases from publisher-provided RSS feeds.

CREATE TABLE IF NOT EXISTS liquidround.merger_news (
    id              BIGSERIAL PRIMARY KEY,
    source          TEXT NOT NULL,
    external_id     TEXT NOT NULL,
    title           TEXT NOT NULL,
    source_url      TEXT NOT NULL,
    published_at    TIMESTAMPTZ,
    summary         TEXT,
    event_stage     TEXT NOT NULL DEFAULT 'other',
    acquirer        TEXT,
    target          TEXT,
    deal_value      NUMERIC,
    is_reverse_merger BOOLEAN NOT NULL DEFAULT FALSE,
    metadata        JSONB NOT NULL DEFAULT '{}'::jsonb,
    first_seen_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (source, external_id)
);

CREATE INDEX IF NOT EXISTS ix_merger_news_published
    ON liquidround.merger_news (published_at DESC);
CREATE INDEX IF NOT EXISTS ix_merger_news_stage
    ON liquidround.merger_news (event_stage, source);
