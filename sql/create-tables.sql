-- LiquidRound Database Schema (PostgreSQL)
-- Multi-Agent M&A and IPO Deal Flow System
-- Schema: liquidround

CREATE SCHEMA IF NOT EXISTS liquidround;

-- Deals table - Core deal information
CREATE TABLE IF NOT EXISTS liquidround.deals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    deal_type TEXT NOT NULL CHECK (deal_type IN ('buyer_ma', 'seller_ma', 'ipo')),
    company_name TEXT,
    industry TEXT,
    sector TEXT,
    deal_size_min BIGINT,
    deal_size_max BIGINT,
    deal_size_currency TEXT DEFAULT 'USD',
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'active', 'completed', 'failed', 'cancelled')),
    priority TEXT DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high', 'urgent')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Workflows table - Workflow execution tracking
CREATE TABLE IF NOT EXISTS liquidround.workflows (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    deal_id UUID REFERENCES liquidround.deals(id),
    user_query TEXT NOT NULL,
    workflow_type TEXT,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'routing', 'executing', 'completed', 'failed')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Workflow results table - Agent execution results
CREATE TABLE IF NOT EXISTS liquidround.workflow_results (
    id SERIAL PRIMARY KEY,
    workflow_id UUID NOT NULL REFERENCES liquidround.workflows(id),
    agent_name TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pending', 'in_progress', 'success', 'failed')),
    result_data JSONB,
    execution_time REAL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Messages table - Chat conversation history
CREATE TABLE IF NOT EXISTS liquidround.messages (
    id SERIAL PRIMARY KEY,
    workflow_id UUID NOT NULL REFERENCES liquidround.workflows(id),
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Companies table - Target companies and acquisition candidates
CREATE TABLE IF NOT EXISTS liquidround.companies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    ticker_symbol TEXT,
    industry TEXT,
    sector TEXT,
    market_cap NUMERIC,
    revenue NUMERIC,
    ebitda NUMERIC,
    employees INTEGER,
    founded_year INTEGER,
    headquarters TEXT,
    website TEXT,
    description TEXT,
    financial_data JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Deal targets table - Links deals to target companies
CREATE TABLE IF NOT EXISTS liquidround.deal_targets (
    id SERIAL PRIMARY KEY,
    deal_id UUID NOT NULL REFERENCES liquidround.deals(id),
    company_id UUID NOT NULL REFERENCES liquidround.companies(id),
    target_type TEXT NOT NULL CHECK (target_type IN ('acquisition_target', 'buyer_candidate', 'competitor', 'comparable')),
    strategic_fit_score REAL CHECK (strategic_fit_score >= 0 AND strategic_fit_score <= 5),
    valuation_low NUMERIC,
    valuation_high NUMERIC,
    valuation_currency TEXT DEFAULT 'USD',
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(deal_id, company_id, target_type)
);

-- Valuations table - Financial valuations and analysis
CREATE TABLE IF NOT EXISTS liquidround.valuations (
    id SERIAL PRIMARY KEY,
    deal_id UUID NOT NULL REFERENCES liquidround.deals(id),
    company_id UUID REFERENCES liquidround.companies(id),
    valuation_method TEXT NOT NULL CHECK (valuation_method IN ('dcf', 'comparable_companies', 'precedent_transactions', 'asset_based')),
    valuation_amount NUMERIC NOT NULL,
    currency TEXT DEFAULT 'USD',
    assumptions JSONB,
    confidence_level TEXT CHECK (confidence_level IN ('low', 'medium', 'high')),
    created_by_agent TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Market data table - Market data snapshots
CREATE TABLE IF NOT EXISTS liquidround.market_data (
    id SERIAL PRIMARY KEY,
    symbol TEXT NOT NULL,
    data_type TEXT NOT NULL CHECK (data_type IN ('stock_price', 'financial_metrics', 'news', 'analyst_rating')),
    data_value REAL,
    data_text TEXT,
    data_json JSONB,
    source TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Deal activities table - Audit trail of deal activities
CREATE TABLE IF NOT EXISTS liquidround.deal_activities (
    id SERIAL PRIMARY KEY,
    deal_id UUID NOT NULL REFERENCES liquidround.deals(id),
    activity_type TEXT NOT NULL,
    description TEXT NOT NULL,
    performed_by TEXT,
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- IPO data table
CREATE TABLE IF NOT EXISTS liquidround.ipo_data (
    id SERIAL PRIMARY KEY,
    ticker TEXT UNIQUE NOT NULL,
    company_name TEXT,
    sector TEXT,
    industry TEXT,
    exchange TEXT,
    ipo_date DATE,
    ipo_price REAL,
    current_price REAL,
    market_cap BIGINT,
    price_change_since_ipo REAL,
    volume BIGINT,
    last_updated TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- IPO refresh log table
CREATE TABLE IF NOT EXISTS liquidround.ipo_refresh_log (
    id SERIAL PRIMARY KEY,
    refresh_type TEXT,
    status TEXT,
    records_processed INTEGER,
    error_message TEXT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ DEFAULT NOW()
);

-- Uploaded documents table (new)
CREATE TABLE IF NOT EXISTS liquidround.documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filename TEXT NOT NULL,
    file_type TEXT NOT NULL,
    file_size BIGINT,
    file_path TEXT,
    parsed_data JSONB,
    analysis JSONB,
    uploaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deal_id UUID REFERENCES liquidround.deals(id)
);

-- Scoring results table (new)
CREATE TABLE IF NOT EXISTS liquidround.scoring_results (
    id SERIAL PRIMARY KEY,
    workflow_id UUID REFERENCES liquidround.workflows(id),
    buyer TEXT,
    target TEXT,
    composite_score INTEGER,
    dimensions JSONB,
    recommendation TEXT,
    key_risks JSONB,
    next_steps JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Research results table (new)
CREATE TABLE IF NOT EXISTS liquidround.research_results (
    id SERIAL PRIMARY KEY,
    workflow_id UUID REFERENCES liquidround.workflows(id),
    query TEXT NOT NULL,
    exa_results JSONB,
    tavily_results JSONB,
    thinking_trace JSONB,
    summary TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Users table (auth)
CREATE TABLE IF NOT EXISTS liquidround.users (
    id SERIAL PRIMARY KEY,
    user_id UUID UNIQUE NOT NULL DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255),
    google_id VARCHAR(255) UNIQUE,
    display_name VARCHAR(255),
    is_admin BOOLEAN NOT NULL DEFAULT FALSE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Password reset tokens
CREATE TABLE IF NOT EXISTS liquidround.password_reset_tokens (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES liquidround.users(user_id) ON DELETE CASCADE,
    token VARCHAR(128) UNIQUE NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    used_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_lr_deals_type_status ON liquidround.deals (deal_type, status);
CREATE INDEX IF NOT EXISTS idx_lr_deals_created_at ON liquidround.deals (created_at);
CREATE INDEX IF NOT EXISTS idx_lr_workflows_status ON liquidround.workflows (status);
CREATE INDEX IF NOT EXISTS idx_lr_workflows_created_at ON liquidround.workflows (created_at);
CREATE INDEX IF NOT EXISTS idx_lr_companies_industry ON liquidround.companies (industry);
CREATE INDEX IF NOT EXISTS idx_lr_companies_market_cap ON liquidround.companies (market_cap);
CREATE INDEX IF NOT EXISTS idx_lr_deal_targets_deal_id ON liquidround.deal_targets (deal_id);
CREATE INDEX IF NOT EXISTS idx_lr_deal_targets_fit ON liquidround.deal_targets (strategic_fit_score);
CREATE INDEX IF NOT EXISTS idx_lr_valuations_deal_id ON liquidround.valuations (deal_id);
CREATE INDEX IF NOT EXISTS idx_lr_market_data_symbol ON liquidround.market_data (symbol);
CREATE INDEX IF NOT EXISTS idx_lr_market_data_ts ON liquidround.market_data (timestamp);
CREATE INDEX IF NOT EXISTS idx_lr_ipo_ticker ON liquidround.ipo_data (ticker);
CREATE INDEX IF NOT EXISTS idx_lr_ipo_sector ON liquidround.ipo_data (sector);
CREATE INDEX IF NOT EXISTS idx_lr_ipo_date ON liquidround.ipo_data (ipo_date);
CREATE INDEX IF NOT EXISTS idx_lr_documents_deal ON liquidround.documents (deal_id);
CREATE INDEX IF NOT EXISTS idx_lr_scoring_workflow ON liquidround.scoring_results (workflow_id);
CREATE INDEX IF NOT EXISTS idx_lr_research_workflow ON liquidround.research_results (workflow_id);

-- Views for common queries
CREATE OR REPLACE VIEW liquidround.active_deals AS
SELECT
    d.*,
    COUNT(dt.id) AS target_count,
    AVG(dt.strategic_fit_score) AS avg_strategic_fit,
    MAX(v.valuation_amount) AS max_valuation
FROM liquidround.deals d
LEFT JOIN liquidround.deal_targets dt ON d.id = dt.deal_id
LEFT JOIN liquidround.valuations v ON d.id = v.deal_id
WHERE d.status IN ('pending', 'active')
GROUP BY d.id;

CREATE OR REPLACE VIEW liquidround.deal_summary AS
SELECT
    d.id,
    d.deal_type,
    d.company_name,
    d.industry,
    d.status,
    d.created_at,
    COUNT(DISTINCT dt.company_id) AS target_companies,
    COUNT(DISTINCT v.id) AS valuations_count,
    AVG(dt.strategic_fit_score) AS avg_strategic_fit,
    MIN(v.valuation_amount) AS min_valuation,
    MAX(v.valuation_amount) AS max_valuation
FROM liquidround.deals d
LEFT JOIN liquidround.deal_targets dt ON d.id = dt.deal_id
LEFT JOIN liquidround.valuations v ON d.id = v.deal_id
GROUP BY d.id;
