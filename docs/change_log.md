# LiquidRound Change Log

## 0.8.1 — 2026-08-31

### Changed
- Made agent skill edits private to each signed-in user, with personal history and runtime prompt isolation.
- Kept Hermes Orchestrator, IR Publish, and IR Distribution as administrator-controlled workspace defaults.
- Unified verified Google SSO with an existing password account by normalized email and made administrator emails deployment-configurable.
- Added per-user RSS source configuration with automatic feed discovery, safe URL validation, and enable/disable controls; ERR is disabled for the operator account.

## 0.8.0 — 2026-07-30

### Added
- Configurable Hermes Orchestrator as a bounded LangGraph specialist
- Typed routing decisions, structured mandate refinement, and agent-run traces
- Checked-in 100-question routing and refinement evaluation
- Ordered migrations, pinned dependencies, CI gates, and readiness endpoints
- Mobile News launcher with desktop context remaining visible by default

### Changed
- Hardened tenant isolation, administrator controls, uploads, outbound URL
  fetching, analytics SQL, production secrets, OAuth callbacks, and prompt publishing
- Restored role/currency configuration, repaired the mobile context pane,
  consolidated navigation, added the IR hub, and paginated Reverse Mergers
- Bounded every LangGraph run with configurable timeout, recursion, and tool-call
  budgets; sanitized generated HTML and removed live values from schema snapshots

## 0.7.0 — 2026-07-28

Investor Relations agent squad, platform demo regeneration, DB timeout fix, and
Coolify memory limit.

### Added
- Investor Relations & Communications category with 5 agents: IR Event Triage
  (`ir-triage:`), Press Release Writer (`write-release:`), IR Compliance Reviewer
  (`ir-compliance:`), IR Publish Agent (`ir-publish:`), IR Distribution Planner
  (`ir-distribute:`)
- Agent count bumped from 26 to 30 across 7 categories
- SEDAR+ ingestion pipeline documentation (`docs/sedarplus_ingestion.md`)
- Platform demo regenerated as landscape PDF (dark navy theme), PPTX, and
  Markdown with screenshots on every page
- `.opencode/skills/` directory consolidating codex and claude skills into
  opencode format (5 skills: liquidround-release, regenerate-liquidround-demo,
  validate-liquidround-ui, alpaca-trading-backtest, fasthtml-user-guide)

### Changed
- `gen_platform_demo.py` rewritten to use pandoc + WeasyPrint for dark navy
  landscape PDF (matching the original user guide CSS) instead of ReportLab
- `capture_screenshots.py` updated with login flow for auth-gated routes and
  4 new IR screenshots
- `docs/user_guide.md` rewritten with screenshot per page, shortened text,
  explicit page breaks between sections
- `docs/assets/guide.css` updated with full-page dark background, h2 page breaks,
  cover page styling

### Fixed
- `utils/database.py get_conn()` — added `connect_timeout=10` and
  `statement_timeout=30000` to prevent prod server hangs on unreachable DB
- `routes/ipo_map.py _load_df()` — consolidated 3 year-by-year DB queries into
  single `get_ipo_data_since()` query
- `agents/router.py strip_prefix()` — fixed regex to handle hyphenated prefixes
  (`ir-triage:`, `write-release:`)

### Infrastructure
- Coolify container memory limit set to 512m for predictivelabsai/liquidround

## 0.6.0 — 2026-07-28

Public-markets and Investor Relations expansion introducing a full disclosure
lifecycle and reverse-merger intelligence.

### Added

- Reverse Mergers workspace with traditional RTO, Canadian reviewed-record, and
  SPAC/de-SPAC comparison subtabs.
- Three-year US EDGAR discovery and evidence classification based on relevant
  Form 8-K items, shell-exit language, and transaction signals.
- Reverse Merger Analyst with the `rto:` prefix and source-linked tools.
- Reviewed Canadian RTO/CPC manual imports with a replaceable licensed-provider
  boundary; SEDAR+ is cited but not scraped or mirrored.
- IR Event Triage, Compliance, Publish, and Distribution agents around the
  existing Press Release Writer.
- Landscape Platform Demo generation with PDF and editable PPTX outputs.

### Changed

- Expanded the platform to 31 specialist agents across seven categories.
- Consolidated SPAC and reverse-merger exploration into a comparable normalized UX.
- Moved the Press Release Writer into the dedicated Investor Relations category.
- Rationalized real-provider tests behind an explicit `integration` marker and
  fixed legacy workflow package imports.
- Refreshed repository guidance, architecture, screenshots, and user documentation.

### Verification

- Default unit suite, agent registry, Python compilation, JavaScript syntax, and
  reverse-merger classification tests passed.
- Desktop and mobile Playwright validation covered the combined navigation,
  Reverse Mergers workspace, Canadian import validation, and Investor Relations.

### Operations

- Apply `sql/18-reverse-mergers.sql` before running EDGAR synchronization or
  storing reviewed Canadian records.
- Canadian bulk automation requires a licensed data-distribution agreement.

## 0.5.1 — 2026-07-28

News-first chat workspace update making investor-relations access and market
intelligence immediately visible.

### Added

- Repository-local UI validation skill and rule requiring real Playwright checks.
- Gitignored, reusable screenshots under `screenshots/` for future user guides and demos.

### Changed

- The desktop News pane now opens by default and remains visible in the chat workspace.
- Investor Relations is expanded by default so Press Release Creator is immediately
  visible in the left navigation.
- Generated memo PDFs open in a dedicated browser tab.

### Removed

- The unused Artifact header button, tab, close control, and right-pane artifact window.

### Documentation

- Updated the platform guide and testing matrix for the News-first workspace.
- Regenerated the timestamped Platform Demo and archived the prior edition.

### Compatibility and operations

- Mobile keeps News off-canvas so the chat remains usable at narrow viewport widths.
- Inline agent tables, citations, charts, and other conversation artifacts are retained.
- Coolify credentials remain local and ignored by Git.

### Verification

- Python compilation, JavaScript syntax, and focused registry tests passed.
- Playwright verified desktop and mobile chat layouts, Investor Relations navigation,
  absence of Artifact controls, and visible release version.

## 0.5.0 — 2026-07-27

Investor Relations release introducing researched press-release creation, expanded
agent coverage, refreshed Skills management, and versioned platform documentation.

### Added

- Investor Relations navigation section with a guided Press Release Creator.
- Web-backed research through Tavily and EXA before release drafting.
- Press Release Writer agent and editable operating skill, separate from the existing
  Press Release Analyst.
- Copy, Markdown, Word, PDF, and Data Room save actions for drafted releases.
- Timestamped LiquidRound AI Platform Demo Markdown and PDF generation.
- Page-numbered PDF table of contents and numbered document footers.
- Automatic archival of previous guide/demo editions under `docs/archive/`.
- Portable Codex skills for demo regeneration and versioned LiquidRound releases.

### Changed

- Renamed the Instructions interface to Skills at `/app/skills`.
- Preserved legacy `/app/instructions` links through permanent redirects.
- Updated agent registration and navigation from 25 to 26 agents.
- Refreshed the canonical user guide against actual routes, tools, agents, exports,
  and workspace behavior.
- Prominently documented Investor Relations, Press Release Analyst, and Press Release Writer.

### Compatibility

- Existing Instructions bookmarks continue to work.
- The existing Press Release Analyst remains available for historical search and analysis.
- Press Release Writer uses the new `write-release:` routing prefix.

### Verification

- Focused registry suite: 139 tests passed.
- Python compilation and route-registration checks passed.
- Markdown, DOCX, and PDF release exports validated.
- Investor Relations and Skills pages verified at desktop and mobile viewport sizes.
- Platform Demo PDF validated at 11 A4 pages with TOC, Investor Relations coverage,
  and numbered footers.
