-- Daily M&A Deal Radar — buyer↔target synergy pairs.
--
-- Buyer  = a PUBLIC company (validated to a Yahoo Finance ticker).
-- Target = a PRIVATE company in the deal_candidates pool.
-- Pairs are scored by the editable deal_radar_synergy prompt (5-bucket, 1-5,
-- weighted composite) and the top-N per run are persisted here for the email
-- and the in-app Deal Radar view.

-- Target-financial columns on deal_candidates (register syncs populate these).
ALTER TABLE liquidround.deal_candidates ADD COLUMN IF NOT EXISTS estimated_revenue_eur NUMERIC;
ALTER TABLE liquidround.deal_candidates ADD COLUMN IF NOT EXISTS estimated_ebitda_eur  NUMERIC;
ALTER TABLE liquidround.deal_candidates ADD COLUMN IF NOT EXISTS reg_code TEXT;
ALTER TABLE liquidround.deal_candidates ADD COLUMN IF NOT EXISTS last_synced TIMESTAMPTZ;
CREATE INDEX IF NOT EXISTS idx_deal_cand_regcode ON liquidround.deal_candidates (reg_code);

CREATE TABLE IF NOT EXISTS liquidround.deal_radar_pairs (
    id                  SERIAL PRIMARY KEY,
    run_date            DATE        NOT NULL,
    rank                INTEGER     NOT NULL,
    -- buyer (public)
    buyer_name          TEXT        NOT NULL,
    buyer_ticker        TEXT        NOT NULL,
    buyer_exchange      TEXT,
    buyer_country       TEXT,
    buyer_mktcap_usd    NUMERIC,
    -- target (private)
    target_name         TEXT        NOT NULL,
    target_country      TEXT,
    target_sector       TEXT,
    target_revenue_eur  NUMERIC,
    -- score
    composite_score     NUMERIC(4,2) NOT NULL,   -- 1.00–5.00, weighted
    recommendation      TEXT,                    -- interpretation band
    bucket_scores       JSONB,                   -- {cost_operational:{score,weight,rationale}, ...}
    reasoning           TEXT,                    -- short synthesis
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_deal_radar_run   ON liquidround.deal_radar_pairs (run_date DESC, rank);
CREATE INDEX IF NOT EXISTS idx_deal_radar_score ON liquidround.deal_radar_pairs (composite_score DESC);
