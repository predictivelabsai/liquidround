-- IPO Map + IPO Pipeline (ported from the `ipomap` Streamlit app)
-- Adds regional columns to ipo_data, a pipeline table for pre-IPO / upcoming
-- companies, and an email-signup table for the IPO Map page.

-- 1) Regional columns for the treemap (Region -> Country -> Sector -> Ticker)
ALTER TABLE liquidround.ipo_data ADD COLUMN IF NOT EXISTS country TEXT;
ALTER TABLE liquidround.ipo_data ADD COLUMN IF NOT EXISTS region  TEXT;

CREATE INDEX IF NOT EXISTS ix_ipo_data_region   ON liquidround.ipo_data (region);
CREATE INDEX IF NOT EXISTS ix_ipo_data_ipo_date ON liquidround.ipo_data (ipo_date);

-- 2) IPO pipeline — private (.PVT) companies + upcoming/filed US IPOs.
--    `pipeline_key` is a stable dedup handle, e.g. "pvt:OPAI.PVT" or
--    "nasdaq:BOLD:2025-06". `kind` distinguishes the two streams.
CREATE TABLE IF NOT EXISTS liquidround.ipo_pipeline (
    id                 SERIAL PRIMARY KEY,
    pipeline_key       TEXT UNIQUE NOT NULL,
    company_name       TEXT NOT NULL,
    ticker             TEXT,                       -- pvt ticker (OPAI.PVT) or proposed ticker
    kind               TEXT NOT NULL DEFAULT 'private',  -- private | upcoming | filed | priced
    sector             TEXT,
    industry           TEXT,
    country            TEXT DEFAULT 'United States',
    exchange           TEXT,
    -- private-company fields (yfinance .PVT)
    last_valuation     BIGINT,                     -- latestImpliedValuation
    last_round         TEXT,                       -- latestShareClass e.g. "Series C-NV"
    last_round_date    DATE,                       -- latestFundingDate
    last_amount_raised BIGINT,
    funding_to_date    BIGINT,
    total_rounds       INTEGER,
    -- upcoming/filed IPO fields (NASDAQ calendar)
    proposed_price     NUMERIC,
    shares_offered     BIGINT,
    deal_value         BIGINT,
    expected_date      DATE,
    -- shared
    investors          TEXT,
    employees          INTEGER,
    website            TEXT,
    summary            TEXT,
    status             TEXT DEFAULT 'private',
    source             TEXT DEFAULT 'yfinance',    -- yfinance | nasdaq | seed
    last_updated       TIMESTAMPTZ,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_ipo_pipeline_val  ON liquidround.ipo_pipeline (last_valuation DESC NULLS LAST);
CREATE INDEX IF NOT EXISTS ix_ipo_pipeline_kind ON liquidround.ipo_pipeline (kind);

-- 3) Email signups from the IPO Map page
CREATE TABLE IF NOT EXISTS liquidround.ipo_signups (
    id         SERIAL PRIMARY KEY,
    email      TEXT UNIQUE NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
