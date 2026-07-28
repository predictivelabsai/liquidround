# LiquidRound Change Log

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
