-- Corp-dev contacts graph for Deal Radar / outreach.
-- Public issuers (tickers) + people (corp-dev / M&A / strategy / IR / C-suite)
-- + enrichment audit + draft-only outreach sequences/touches.
-- Soft-links to deal_radar_pairs and pipeline_items; leads remain inbound-only.

-- ── Public issuers (listed buyers) ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS liquidround.public_issuers (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticker            TEXT NOT NULL,
    exchange          TEXT,
    cik               TEXT,
    lei               TEXT,
    name              TEXT NOT NULL,
    country           TEXT,                 -- ISO-ish: US, CA, GB, DE, …
    ir_url            TEXT,
    website           TEXT,
    yfinance_key      TEXT,                 -- Yahoo Finance symbol if different from ticker
    last_enriched_at  TIMESTAMPTZ,
    metadata          JSONB NOT NULL DEFAULT '{}'::jsonb,  -- e.g. {"sector":"saas","geo":"US"}
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (ticker)
);

CREATE INDEX IF NOT EXISTS idx_public_issuers_country
    ON liquidround.public_issuers (country);
CREATE INDEX IF NOT EXISTS idx_public_issuers_enriched
    ON liquidround.public_issuers (last_enriched_at DESC NULLS LAST);

-- ── Corp-dev / M&A contacts ─────────────────────────────────────────────────
-- role_family prioritises corp_dev / mna / strategy for SaaS US+CA GTM.
-- linkedin_url + metadata.geo / metadata.sector (saas) for Sales Nav paste imports
-- (source=manual). Do NOT automate LinkedIn scraping.
CREATE TABLE IF NOT EXISTS liquidround.corpdev_contacts (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    issuer_id            UUID REFERENCES liquidround.public_issuers(id) ON DELETE SET NULL,
    company_id           UUID REFERENCES liquidround.companies(id) ON DELETE SET NULL,
    ticker               TEXT,              -- denormalised for fast radar joins
    full_name            TEXT NOT NULL,
    title                TEXT,
    role_family          TEXT NOT NULL
                         CHECK (role_family IN (
                             'corp_dev', 'mna', 'strategy', 'ir',
                             'ceo', 'cfo', 'board', 'other'
                         )),
    seniority            TEXT,              -- e.g. VP, Director, Head, Analyst
    email                TEXT,
    email_status         TEXT NOT NULL DEFAULT 'unknown'
                         CHECK (email_status IN (
                             'guessed', 'verified', 'bounced', 'unknown'
                         )),
    phone                TEXT,
    linkedin_url         TEXT,              -- Sales Nav / public profile paste
    location             TEXT,              -- free-text; prefer US / CA for v1 ICP
    source               TEXT NOT NULL
                         CHECK (source IN (
                             'edgar_def14a', 'sedar_circular', 'ir_page',
                             'companies_house', 'manual', 'llm_web', 'yfinance'
                         )),
    source_url           TEXT,
    source_date          DATE,
    confidence           NUMERIC(4,3) CHECK (confidence IS NULL OR (confidence >= 0 AND confidence <= 1)),
    metadata             JSONB NOT NULL DEFAULT '{}'::jsonb,
    -- Suggested metadata keys: geo (US|CA|…), sector (saas|…),
    -- sales_nav_search_id, imported_at, notes
    is_primary_corpdev   BOOLEAN NOT NULL DEFAULT false,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Soft uniqueness on (ticker, full_name, title) — allow NULL titles via coalesce
CREATE UNIQUE INDEX IF NOT EXISTS uq_corpdev_contacts_ticker_name_title
    ON liquidround.corpdev_contacts (
        ticker,
        lower(full_name),
        lower(COALESCE(title, ''))
    )
    WHERE ticker IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_corpdev_contacts_ticker
    ON liquidround.corpdev_contacts (ticker);
CREATE INDEX IF NOT EXISTS idx_corpdev_contacts_role_family
    ON liquidround.corpdev_contacts (role_family);
CREATE INDEX IF NOT EXISTS idx_corpdev_contacts_email
    ON liquidround.corpdev_contacts (email)
    WHERE email IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_corpdev_contacts_issuer
    ON liquidround.corpdev_contacts (issuer_id);
CREATE INDEX IF NOT EXISTS idx_corpdev_contacts_primary
    ON liquidround.corpdev_contacts (ticker)
    WHERE is_primary_corpdev;

-- ── Enrichment run audit ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS liquidround.contact_enrichment_runs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    tickers         TEXT[] NOT NULL DEFAULT '{}',
    source_mix      JSONB NOT NULL DEFAULT '{}'::jsonb,  -- {edgar_def14a: n, …}
    contacts_found  INTEGER NOT NULL DEFAULT 0,
    contacts_upserted INTEGER NOT NULL DEFAULT 0,
    dry_run         BOOLEAN NOT NULL DEFAULT false,
    status          TEXT NOT NULL DEFAULT 'completed'
                    CHECK (status IN ('running', 'completed', 'failed', 'partial')),
    error_message   TEXT,
    metadata        JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_contact_enrichment_runs_at
    ON liquidround.contact_enrichment_runs (run_at DESC);

-- ── Outreach sequences (draft-first; human approve before send) ─────────────
CREATE TABLE IF NOT EXISTS liquidround.outreach_sequences (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            TEXT NOT NULL,
    purpose         TEXT,                   -- e.g. radar_pair_intro, ir_expand
    owner_user_id   UUID REFERENCES liquidround.users(user_id) ON DELETE SET NULL,
    status          TEXT NOT NULL DEFAULT 'draft'
                    CHECK (status IN ('draft', 'active', 'paused', 'completed', 'archived')),
    metadata        JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_outreach_sequences_status
    ON liquidround.outreach_sequences (status);

-- ── Outreach touches ────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS liquidround.outreach_touches (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sequence_id          UUID REFERENCES liquidround.outreach_sequences(id) ON DELETE SET NULL,
    contact_id           UUID REFERENCES liquidround.corpdev_contacts(id) ON DELETE SET NULL,
    deal_radar_pair_id   INTEGER REFERENCES liquidround.deal_radar_pairs(id) ON DELETE SET NULL,
    pipeline_item_id     UUID REFERENCES liquidround.pipeline_items(id) ON DELETE SET NULL,
    channel              TEXT NOT NULL DEFAULT 'email'
                         CHECK (channel IN ('email', 'linkedin', 'phone', 'other')),
    subject              TEXT,
    body                 TEXT,
    status               TEXT NOT NULL DEFAULT 'drafted'
                         CHECK (status IN (
                             'drafted', 'queued', 'sent', 'replied',
                             'bounced', 'do_not_contact'
                         )),
    scheduled_at         TIMESTAMPTZ,
    sent_at              TIMESTAMPTZ,
    replied_at           TIMESTAMPTZ,
    metadata             JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_outreach_touches_status
    ON liquidround.outreach_touches (status);
CREATE INDEX IF NOT EXISTS idx_outreach_touches_contact
    ON liquidround.outreach_touches (contact_id);
CREATE INDEX IF NOT EXISTS idx_outreach_touches_radar
    ON liquidround.outreach_touches (deal_radar_pair_id)
    WHERE deal_radar_pair_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_outreach_touches_pipeline
    ON liquidround.outreach_touches (pipeline_item_id)
    WHERE pipeline_item_id IS NOT NULL;
