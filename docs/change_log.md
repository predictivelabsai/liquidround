# LiquidRound Change Log

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
