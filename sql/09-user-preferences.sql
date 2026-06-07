-- LiquidRound User Preferences (M&A deal preferences, notifications, account info)

CREATE TABLE IF NOT EXISTS liquidround.user_preferences (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES liquidround.users(user_id) ON DELETE CASCADE UNIQUE,
    -- Account info
    company_name VARCHAR(255),
    job_title VARCHAR(255),
    phone VARCHAR(30),
    country VARCHAR(5),
    city VARCHAR(100),
    currency VARCHAR(3) DEFAULT 'EUR',
    language VARCHAR(5) DEFAULT 'en',
    -- Deal preferences
    deal_size_min_eur NUMERIC(14,2),
    deal_size_max_eur NUMERIC(14,2),
    preferred_sectors JSONB DEFAULT '[]',
    preferred_geographies JSONB DEFAULT '[]',
    preferred_deal_types JSONB DEFAULT '[]',
    target_revenue_min_eur NUMERIC(14,2),
    target_revenue_max_eur NUMERIC(14,2),
    target_ebitda_min_eur NUMERIC(14,2),
    target_ebitda_max_eur NUMERIC(14,2),
    -- Notifications
    notify_new_deals BOOLEAN DEFAULT TRUE,
    notify_price_changes BOOLEAN DEFAULT TRUE,
    notify_weekly_digest BOOLEAN DEFAULT TRUE,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_lr_user_prefs_user ON liquidround.user_preferences(user_id);
