# LiquidRound — Corp-Dev Contacts & Outreach (Product Brief)

**Status:** Spike in flight · Sep 2026  
**Owner:** Predictive Labs / LiquidRound  
**Repo:** `predictivelabsai/liquidround`  
**Related:** Deal Radar, Buyer Scanner, free Find Buyers tool, IR agent squad

---

## Problem

LiquidRound already finds **which public companies** should buy **which private targets** (Deal Radar, `buyer_scanner`, `/tools/match`). It does not yet store **whom to contact** inside those issuers.

Today:
- `liquidround.companies` / `deal_radar_pairs` are firm-level only
- `prompts/market_outreach.md` asks for decision-makers but was **orphaned** (not in the agent registry) — now promoted as `outreach:` / `corpdev_outreach`
- Buyer pipeline stages include Approached / Engaged with no person FK
- `liquidround.leads` captures inbound free-tool users — not outbound corp-dev
- Roadmap already names the gap: Pipeline CRM + Email Outreach (`routes/api.py` / `PLAN.md` Phase 8)

Result: users get a ranked buyer list, then leave the product to hunt LinkedIn / IR pages by hand.

---

## Opportunity

Attach a **corp-dev contacts graph** to public tickers that already appear in Deal Radar. Then draft outreach that cites the exact synergy pair — context competitors cannot fake with generic sequencers.

**Wedge hook:** “3 private assets in your adjacency scored ≥4.0 this week — here’s who to email at {BUYER}.”

---

## ICP (GTM) — priority order

| Priority | Who | Why LiquidRound |
|---|---|---|
| **1 (PRIMARY)** | **Tech SaaS corporate development / Head of M&A / Corporate Strategy at US + Canada listed issuers** | Serial acquirers + strategics already on radar watchlists; high volume of tuck-ins; Sales Nav discoverable |
| 2 | Nordic / Baltic boutique IB & M&A advisors | Already use Baltic private targets + Deal Radar |
| 3 | IR teams using `ir-*` agents | Land with press-release workflow → expand to M&A peers |
| 4 | PE associates | Find Buyers + scoring → outreach packs |

**Geography (v1):** **United States + Canada first** for SaaS corp-dev; Baltics / Nordics / UK / DACH retained for Deal Radar target coverage and secondary buyer lists.

---

## US & Canada SaaS outreach

**ICP detail:** Corp-dev, Head of M&A, VP Corporate Development, Corporate Strategy at listed SaaS and vertical software (e.g. CRM, NOW, ADBE, INTU, WDAY, TEAM, SNOW, DDOG, NET, ZM, OKTA, HUBS, SHOP.TO, OTEX.TO, DSGX.TO, CSU.TO, TOI.V, LMN.V, ENGH.TO, ROP, PYPL).

**People discovery (primary):** LinkedIn **Sales Navigator** saved searches — **manual paste / CSV export into `corpdev_contacts`** with `source=manual` and `linkedin_url` set. See `docs/linkedin-sales-nav-saas-playbook.md`.

**Hard rule:** no LinkedIn scrape automation / ToS-violating bots. LiquidRound never drives a Sales Nav session.

**Officer corroboration:**
- **US** — SEC EDGAR (DEF 14A / officer changes via `utils/edgar.py`)
- **CA** — SEDAR+ circulars (follow-on; schema already has `source=sedar_circular`)
- IR / leadership pages via Exa/Tavily as secondary

**Role priority in product:** `corp_dev` → `mna` → `strategy` → C-suite → `ir` → `board`.

---

## Product shape (v1)

Not a Salesforce clone. Thin layer:

1. **Contacts DB** next to issuers/tickers (`corpdev_contacts`, enrichment runs, outreach touches)
2. **Enricher** for Deal Radar buyers + `BUYER_WATCHLIST` ∪ US/CA SaaS list (EDGAR, Companies House for `.L`, IR stubs; Sales Nav = paste-only)
3. **`outreach:` agent** — drafts only; human approve before any send
4. **Deal Radar → contacts drawer + XLSX** (follow-on UI)
5. **Pipeline CRM v0** — Approached/Engaged logs a touch against a person

**Hard rule:** human approve before any Postmark send. v1 can be export + copy-paste.

---

## Data model (summary)

- `public_issuers` — ticker, exchange, CIK/LEI, IR URL, `metadata.sector` / geo
- `corpdev_contacts` — person + `role_family` (`corp_dev` | `mna` | `strategy` | `ir` | `ceo` | `cfo` | `board` | `other`) + `linkedin_url` + email status + source + confidence + `metadata` (`geo`, `sector=saas`, Sales Nav ids)
- `contact_enrichment_runs` — audit / cost
- `outreach_sequences` / `outreach_touches` — drafted→sent→replied, optional `deal_radar_pair_id` / `pipeline_item_id`

Keep `leads` for inbound product users; keep `corpdev_contacts` for outbound issuer people.

---

## Sources (order)

1. **LinkedIn Sales Nav** (paste / export → `source=manual`) — primary for US/CA SaaS people  
2. SEC EDGAR (`utils/edgar.py`) — DEF 14A / officer corroboration (US)  
3. UK Companies House officers (`utils/companies_house_api.py`) — `.L` tickers  
4. SEDAR+ circulars (CA) — P2  
5. Issuer IR / leadership pages via Exa/Tavily  
6. Paid verify (Apollo etc.) only after hit-rate measured  

---

## GTM motion

1. **PLG** — free tools → `leads` → digest/Beehiiv nurture  
2. **Deal Radar habit** — digest CTA: “See who to contact at {buyer}” (gated)  
3. **Context outbound** — radar pair + named corp-dev → personalized draft (`outreach:`)  
4. **Sales Nav playbook** — shared boolean recipes for US/CA SaaS corp-dev seats  
5. **IR land-and-expand** — win IR seat → introduce corp-dev outreach  
6. **Partnerships** — boutique ECM desks, Baltic ecosystem content (secondary)

**Metrics:** % radar pairs with ≥1 corp-dev contact · drafts created · Approached→Engaged · digest→activated · free-tool→signup · % contacts with `linkedin_url` from Sales Nav paste

---

## Backlog

| P | Item |
|---|---|
| P0 | Migration `23-corpdev-contacts` |
| P0 | Enricher spike on watchlist + US/CA SaaS list + last-30d radar buyers |
| P0 | Register `outreach:` agent |
| P0 | Deal Radar contacts drawer + XLSX |
| P1 | Sequence board (Pipeline CRM v0) + approve-to-send |
| P1 | Sales Nav import UX (paste URL / CSV → `source=manual`) |
| P2 | Email verify; SEDAR batch; un-stub seller workflow |

---

## This spike

- Ship schema + dry-run enricher on `BUYER_WATCHLIST` ∪ `data/saas_buyer_watchlist_us_ca.txt`  
- Promote `corpdev_outreach` (`outreach:`) from orphaned `market_outreach.md`  
- Publish this brief + Sales Nav playbook; lead with **US/CA tech SaaS corp-dev**  
- Measure email/title hit-rate before buying contact data  

**Non-goals for spike:** auto-blast email, LinkedIn scraping/automation, CapIQ/Bloomberg day-1 dependency.

---

*Predictive Labs Ltd · liquidround.ai*
