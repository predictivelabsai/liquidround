-- YTD returns for securities held in 13F filings.
-- Populated by: python -m scripts.sync_security_returns

CREATE TABLE IF NOT EXISTS liquidround.security_returns (
    cusip           TEXT PRIMARY KEY,
    ticker          TEXT,
    company_name    TEXT,
    return_ytd      NUMERIC(10,4),   -- e.g. 0.2534 = +25.34%
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_security_returns_ticker
    ON liquidround.security_returns (ticker);
