-- Fund bookmarks — let logged-in users favourite hedge funds on the treemap page.
CREATE TABLE IF NOT EXISTS liquidround.fund_bookmarks (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES liquidround.users(id) ON DELETE CASCADE,
    fund_name   TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(user_id, fund_name)
);
CREATE INDEX IF NOT EXISTS ix_fund_bookmarks_user ON liquidround.fund_bookmarks (user_id);
