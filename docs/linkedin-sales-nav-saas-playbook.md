# LinkedIn Sales Nav — US/CA SaaS Corp-Dev Playbook

**Purpose:** Reusable Sales Navigator search recipes to find corporate development / M&A / strategy contacts at LiquidRound US + Canada SaaS buyer watchlist issuers, then **paste or export** into `liquidround.corpdev_contacts` (`source=manual`, set `linkedin_url`).

**Hard rule:** Manual / human-in-the-loop only. No scraping, no unattended browser automation, no ToS-violating bots.

---

## 1. Saved search — title boolean

**Current title** contains:

```
("Corporate Development" OR "Corp Dev" OR "Corp. Dev" OR "M&A" OR "Mergers and Acquisitions" OR "Merger & Acquisition" OR "Corporate Strategy" OR "Head of Strategy")
```

Optional seniority filter (Sales Nav UI): VP, Director, Head, Partner, Chief — exclude Intern / Student.

**Prefer role_family mapping when importing:**

| Title contains | `role_family` |
|---|---|
| Corporate Development / Corp Dev | `corp_dev` |
| M&A / Mergers and Acquisitions | `mna` |
| Corporate Strategy / Head of Strategy | `strategy` |
| Investor Relations | `ir` |
| CFO / Chief Financial | `cfo` |
| CEO / Chief Executive | `ceo` |

---

## 2. Current company = watchlist issuers

In Sales Nav **Current company** filter, add (and save as a list):

**US SaaS / software strategics:** Salesforce (CRM), ServiceNow (NOW), Adobe (ADBE), Intuit (INTU), Workday (WDAY), Atlassian (TEAM), Snowflake (SNOW), Datadog (DDOG), Cloudflare (NET), Zoom (ZM), Okta (OKTA), HubSpot (HUBS), Roper Technologies (ROP), PayPal (PYPL)

**Canada:** Shopify (SHOP.TO), Open Text (OTEX.TO), Descartes (DSGX.TO), Constellation Software (CSU.TO), Topicus (TOI.V), Lumine (LMN.V), Enghouse (ENGH.TO)

Keep the list in sync with `data/saas_buyer_watchlist_us_ca.txt` and `scripts/enrich_corpdev_contacts.SAAS_BUYER_WATCHLIST_US_CA`.

---

## 3. Geography & industry

- **Geography:** United States **OR** Canada (include metro areas if needed: SF Bay Area, NYC, Seattle, Austin, Toronto, Waterloo, Vancouver, Montreal)
- **Industry:** Software Development; Information Technology & Services; Computer Software (Sales Nav taxonomy varies — pick closest)

---

## 4. Boolean recipe (copy/paste into keyword box if UI lacks title ORs)

```
("Corporate Development" OR "Corp Dev" OR "M&A" OR "Mergers and Acquisitions" OR "Corporate Strategy")
```

Combine with company list + US/CA geography in the left-rail filters (do not put company names only in keywords — use **Current company** for precision).

---

## 5. Import into LiquidRound

For each result (or CSV export from Sales Nav / LinkedIn export tools you already license):

1. Create/update `corpdev_contacts` row:
   - `ticker` — Yahoo Finance symbol from watchlist
   - `full_name`, `title`, `role_family` (table above)
   - `linkedin_url` — profile or Sales Nav lead URL
   - `location` — US / CA / city
   - `source` = **`manual`**
   - `email_status` = `unknown` until verified
   - `confidence` ≈ `0.7` for SN-sourced titles you eyeballed
   - `metadata`: `{"geo":"US"|"CA","sector":"saas","sales_nav":true}`
2. Optionally mark `is_primary_corpdev = true` for the best corp_dev / mna seat per ticker.
3. Use agent prefix `outreach:` to draft a touch; leave status `drafted` until human approve-to-send.

**Do not** wire Sales Nav credentials into LiquidRound env files.

---

## 6. Corroborate (optional)

- US: EDGAR DEF 14A officer list (`source` stays `manual` for the SN row; enricher may add a separate EDGAR hint row)
- CA: SEDAR+ management circulars (P2)

---

*Predictive Labs Ltd · liquidround.ai*
