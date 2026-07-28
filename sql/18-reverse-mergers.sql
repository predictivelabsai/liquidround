-- Reverse-merger / RTO intelligence. US records are discovered from SEC EDGAR.
-- Canadian records are discovered from sedarplus.ca via a headless Chromium
-- scraper (utils/sedarplus.py) and supplemented by reviewed manual imports.
-- Only metadata + a content hash are stored; documents are never mirrored.

CREATE TABLE IF NOT EXISTS liquidround.reverse_merger_transactions (
    id                  BIGSERIAL PRIMARY KEY,
    transaction_key     TEXT UNIQUE NOT NULL,
    jurisdiction        TEXT NOT NULL CHECK (jurisdiction IN ('US', 'CA')),
    transaction_type    TEXT NOT NULL,
    status              TEXT NOT NULL DEFAULT 'candidate',
    public_company      TEXT NOT NULL,
    public_ticker       TEXT,
    public_cik          TEXT,
    private_target      TEXT,
    exchange            TEXT,
    announcement_date   DATE,
    completion_date     DATE,
    deal_value          NUMERIC,
    concurrent_financing NUMERIC,
    target_ownership_pct NUMERIC(6,2),
    source_url          TEXT NOT NULL,
    source_type         TEXT NOT NULL,
    source_filing_id    TEXT,
    summary             TEXT,
    risk_flags          JSONB NOT NULL DEFAULT '[]'::jsonb,
    confidence          NUMERIC(4,3) NOT NULL DEFAULT 0.500,
    review_status       TEXT NOT NULL DEFAULT 'unreviewed',
    metadata            JSONB NOT NULL DEFAULT '{}'::jsonb,
    last_verified_at    TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_reverse_mergers_date
    ON liquidround.reverse_merger_transactions (announcement_date DESC);
CREATE INDEX IF NOT EXISTS ix_reverse_mergers_type
    ON liquidround.reverse_merger_transactions (transaction_type, status);
CREATE INDEX IF NOT EXISTS ix_reverse_mergers_ticker
    ON liquidround.reverse_merger_transactions (public_ticker);

CREATE TABLE IF NOT EXISTS liquidround.reverse_merger_filings (
    id              BIGSERIAL PRIMARY KEY,
    transaction_id  BIGINT REFERENCES liquidround.reverse_merger_transactions(id) ON DELETE CASCADE,
    regulator       TEXT NOT NULL,
    form_type       TEXT,
    filing_date     DATE,
    accession_number TEXT,
    source_url      TEXT NOT NULL,
    detected_items  JSONB NOT NULL DEFAULT '[]'::jsonb,
    document_hash   TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (regulator, accession_number, source_url)
);
