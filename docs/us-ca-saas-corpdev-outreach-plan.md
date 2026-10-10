# US + CA outreach plan — Tech SaaS Corp Dev (primary)

**ICP #1:** Corporate Development / M&A / Strategy at **public tech SaaS** companies headquartered or listing in **United States** and **Canada**.
**Secondary:** PE tech/SaaS growth; boutique tech IB covering SaaS.
**Not primary:** Baltic advisors, industrials, IR-only seats (keep as expansion later).

---

## 1) Who exactly

**Titles (priority order)**
1. VP / SVP / Head of Corporate Development
2. Director, Corporate Development / M&A
3. VP Strategy & Corp Dev (combined)
4. Chief Strategy Officer (when corp-dev reports in)
5. CEO/CFO only for small-cap serial acquirers (<$5B) where corp-dev is thin

**Company filters**
- Sector: Software / SaaS / internet software & services
- Listing: NYSE, Nasdaq, TSX, TSXV
- Behaviour: serial M&A or stated inorganic growth (vertical software acquirers especially)
- Size bands: mid-cap + large-cap strategics first; micro-cap only if active buyers

**Seed buyer set (LiquidRound watchlist-aligned + SaaS densify)**
- CA: `CSU.TO` (Constellation), `ENGH.TO`, `SHOP.TO` / Shopify, `TOI.V`, `LMN.V`
- US: `ROP`, `CRM`, `NOW`, `ADBE`, `INTU`, `WDAY`, `TEAM`, `DDOG`, `SNOW`, `HUBS`, `PCTY`, `PAYC`, `TYL`, `BL`, `ZM`, `PYPL` (fintech-adjacent)

---

## 2) LinkedIn as the people search layer

**Do:** Sales Navigator (or Recruiter Lite) **saved searches** + paste profile URL/name into LiquidRound contacts.
**Don't:** scrape LinkedIn, auto-connect bots, or unattended InMail blasting (ToS + deliverability risk).

### Sales Nav saved-search recipe (copy/paste)

**Search A — US SaaS Corp Dev**
- Title: `"Corporate Development" OR "Corp Dev" OR "M&A" OR "Mergers and Acquisitions" OR "Inorganic"`
- Title exclude: `Intern OR Assistant OR Coordinator OR Recruiter OR Sales`
- Current company: list of tickers/names from seed set (or Industry = Software Development + Company headcount 201–10,000+)
- Geography: United States
- Seniority: Director, VP, CXO, Partner
- Function: Business Development, Strategy/Planning, Finance (narrow manually)

**Search B — Canada SaaS Corp Dev**
- Same titles
- Geography: Canada (and Toronto / Vancouver / Montreal metro as filters)
- Company: Constellation ecosystem + TSX software issuers

**Search C — Serial acquirer watch**
- Company = Constellation Software / Roper / Adobe / Salesforce / ServiceNow / Intuit / Shopify
- Title contains Corp Dev OR M&A
- Posted in past 90 days (catch movers)

### Workflow in LiquidRound
1. Run saved search → open profile
2. In product: **Add contact** (or agent `outreach:` with paste) → store `linkedin_url`, title, company ticker, `role_family=corp_dev`, `source=manual`
3. Enricher fills email later (pattern + verify) — LinkedIn is identity source of truth
4. Optional: chrome snippet / CSV export from SN → import CSV into `corpdev_contacts`

### Product features to support LinkedIn search (build order)
| P | Feature |
|---|---|
| P0 | `linkedin_url` on `corpdev_contacts` + manual add / CSV import |
| P0 | Saved-search recipe library in-app (US SaaS / CA SaaS / watchlist co.) |
| P1 | “Paste LinkedIn profile text → normalize contact” skill |
| P1 | Filter contacts: geography US|CA, sector saas, role corp_dev |
| P2 | Browser assist (user-driven) to open SN search URLs pre-filled — still human clicks |
| — | **Out of scope:** automated LinkedIn login/scrape |

---

## 3) Outreach motion (US + CA SaaS)

**Offer:** Deal Radar–style **SaaS adjacency targets** (private SaaS / vertical software) scored against their M&A pattern — not generic “we do AI.”

**Sequence (human-approved)**
- Day 0 — Email or InMail: 4–6 lines, cite 1–2 named adjacency targets or thesis (vertical, geo, ARR band)
- Day 3 — LinkedIn note if no reply (different angle: peer acquisition comps)
- Day 7 — Bump with one fresh radar pair
- Day 14 — Breakup / quarterly nurture into digest

**Message angle library**
1. “Vertical software bolt-ons in [vertical] at $[x–y]m ARR”
2. “CA/US private targets that look like your last 3 deals”
3. “Cross-border (Baltic/Nordic → NA acquirer) where you have sparse coverage”

**Compliance**
- CASL (Canada): consent / soft opt-in + unsubscribe
- US CAN-SPAM: physical address, unsubscribe
- No MNPI; public-company outreach only on public theses

---

## 4) Channel mix

| Channel | Role |
|---|---|
| LinkedIn SN search | Primary **discovery** |
| LinkedIn InMail / connection | Secondary **touch** (personalized) |
| Email (verified) | Primary **conversion** once address known |
| Deal Radar / digest CTA | Inbound for issuers who already use LiquidRound |
| Conferences (SaaStr, Collision, Idealab-type) | Warm follow-up to SN list |

---

## 5) 30 / 60 / 90 days

**Days 1–30**
- Lock ICP = tech SaaS corp-dev US/CA
- Ship contacts schema + LinkedIn URL + CSV import
- Build SN saved searches A/B/C; manually load **50** priority contacts (top 15 issuers × ~3 people)
- Draft 3 templates in `outreach:` agent

**Days 31–60**
- Enrich emails for those 50; start approved sequences (target 40 touches)
- Expand watchlist to full US/CA SaaS acquirer set
- Measure: reply rate, meeting rate, % with linkedin_url

**Days 61–90**
- Scale to 200 contacts; add PE tech corp-dev as secondary
- Radar drawer “Find on LinkedIn” deep-link (pre-filled SN URL)
- Kill what doesn’t convert; double down on vertical-software acquirers

---

## 6) Success metrics

- Contacts with `role_family=corp_dev` + US/CA + saas tag
- % with `linkedin_url` filled
- SN → contact → drafted → sent → replied → meeting
- Meetings per 100 touches (goal: learn, not spray)

---

## 7) Immediate next build (aligned with spike)

1. Schema + enricher (in flight)
2. Brief/ICP rewrite → SaaS corp-dev US/CA primary
3. Expand US/CA SaaS tickers on watchlist / enricher defaults
4. LinkedIn saved-search recipes doc + CSV import path
5. No LinkedIn scrape — paste/import only
