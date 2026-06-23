-- Deal candidate pool — persistent companies for daily digest rotation.
CREATE TABLE IF NOT EXISTS liquidround.deal_candidates (
    id                 SERIAL PRIMARY KEY,
    company_name       TEXT NOT NULL,
    country            TEXT,
    sector             TEXT,
    description        TEXT,
    deal_context       TEXT,
    deal_size_estimate TEXT,
    source             TEXT,
    source_url         TEXT,
    discovered_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_featured      DATE,
    feature_count      INTEGER NOT NULL DEFAULT 0,
    is_active          BOOLEAN NOT NULL DEFAULT TRUE,
    UNIQUE(company_name, country)
);

CREATE INDEX IF NOT EXISTS ix_deal_candidates_active
    ON liquidround.deal_candidates (is_active, last_featured NULLS FIRST);
