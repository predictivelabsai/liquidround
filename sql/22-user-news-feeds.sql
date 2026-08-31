-- Per-user RSS feed configuration for the contextual news pane.

CREATE TABLE IF NOT EXISTS liquidround.user_news_feeds (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL
        REFERENCES liquidround.users(user_id) ON DELETE CASCADE,
    feed_key VARCHAR(96) NOT NULL,
    name VARCHAR(180) NOT NULL,
    url TEXT NOT NULL,
    icon VARCHAR(8) NOT NULL,
    is_builtin BOOLEAN NOT NULL DEFAULT FALSE,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, feed_key),
    UNIQUE (user_id, url)
);

CREATE INDEX IF NOT EXISTS ix_user_news_feeds_enabled
    ON liquidround.user_news_feeds (user_id, enabled);

-- The operator requested that ERR be disabled for their personal feed.
INSERT INTO liquidround.user_news_feeds
    (user_id, feed_key, name, url, icon, is_builtin, enabled)
SELECT user_id, 'err-news', 'ERR News', 'https://news.err.ee/rss', 'ERR', TRUE, FALSE
FROM liquidround.users
WHERE lower(email) = 'kaljuvee@gmail.com'
ON CONFLICT (user_id, feed_key) DO UPDATE
SET enabled = FALSE,
    updated_at = NOW();
