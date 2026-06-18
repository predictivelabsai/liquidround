-- Lead capture from free tools (comparables, match, valuation)
CREATE TABLE IF NOT EXISTS liquidround.leads (
    id            SERIAL PRIMARY KEY,
    full_name     TEXT NOT NULL,
    email         TEXT NOT NULL,
    phone         TEXT DEFAULT '',
    timeline      TEXT DEFAULT '',
    tool          TEXT NOT NULL,          -- 'comparables' | 'match' | 'valuation'
    company_url   TEXT DEFAULT '',
    company_name  TEXT DEFAULT '',
    metadata      JSONB DEFAULT '{}',
    created_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_leads_email ON liquidround.leads(email);
CREATE INDEX IF NOT EXISTS idx_leads_created ON liquidround.leads(created_at DESC);
