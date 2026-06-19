-- SPAC tracker — stores SPAC lifecycle data from NASDAQ calendar + SEC EDGAR + yfinance.
-- Parallels ipo_pipeline for operating-company IPOs.

CREATE TABLE IF NOT EXISTS liquidround.spac_data (
    id              SERIAL PRIMARY KEY,
    spac_key        TEXT UNIQUE NOT NULL,
    ticker          TEXT,
    warrant_ticker  TEXT,
    company_name    TEXT NOT NULL,
    sponsor         TEXT,
    status          TEXT NOT NULL DEFAULT 'searching',
    trust_size      BIGINT,
    trust_per_share NUMERIC(10,2),
    current_price   NUMERIC(10,2),
    warrant_price   NUMERIC(10,2),
    nav_premium_pct NUMERIC(6,2),
    target_name     TEXT,
    target_sector   TEXT,
    ipo_date        DATE,
    da_date         DATE,
    vote_date       DATE,
    completion_date DATE,
    deadline_date   DATE,
    redemption_pct  NUMERIC(6,2),
    exchange        TEXT,
    sector_focus    TEXT,
    country         TEXT DEFAULT 'United States',
    ipo_size        BIGINT,
    deal_value      BIGINT,
    post_merge_return_1m  NUMERIC(8,2),
    post_merge_return_3m  NUMERIC(8,2),
    post_merge_return_6m  NUMERIC(8,2),
    source          TEXT DEFAULT 'nasdaq',
    last_updated    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_spac_status ON liquidround.spac_data (status);
CREATE INDEX IF NOT EXISTS ix_spac_trust  ON liquidround.spac_data (trust_size DESC NULLS LAST);
CREATE INDEX IF NOT EXISTS ix_spac_ipo    ON liquidround.spac_data (ipo_date);
CREATE INDEX IF NOT EXISTS ix_spac_ticker ON liquidround.spac_data (ticker);
