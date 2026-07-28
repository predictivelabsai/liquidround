# SKILLS.md

Instructions for the testing agent. Every UI change MUST be verified with Playwright MCP before reporting the task as complete.

## When to test

After any change to:
- `components/chat_shell.py` (left pane, center pane, right pane, welcome hero, sample cards)
- `components/landing.py` (landing page, sign-in overlay, nav, hero, sections, footer)
- `static/app.css` (layout, dark theme, responsive breakpoints)
- `static/chat.js` (chat interaction, SSE, share/copy, sample cards, News pane)
- `routes/auth.py` (login, register, forgot password, profile)
- `routes/*.py` that render full pages (`help.py`, `instructions.py`, `analytics.py`, `dataroom.py`, `companies.py`)
- `main.py` `/app` or `/` route changes

## Pre-flight

1. Start the server if not already running:
   ```
   python main.py &
   ```
2. Wait for it to respond:
   ```
   curl -s -o /dev/null -w '%{http_code}' http://localhost:5007/
   ```
   Expect `200`. If not, check `/tmp/liquidround.log`.

3. Load Playwright MCP tools via ToolSearch:
   ```
   select:mcp__plugin_playwright_playwright__browser_navigate,mcp__plugin_playwright_playwright__browser_snapshot,mcp__plugin_playwright_playwright__browser_take_screenshot,mcp__plugin_playwright_playwright__browser_resize,mcp__plugin_playwright_playwright__browser_click,mcp__plugin_playwright_playwright__browser_evaluate,mcp__plugin_playwright_playwright__browser_hover,mcp__plugin_playwright_playwright__browser_type,mcp__plugin_playwright_playwright__browser_close
   ```

## Test matrix

Every test pass covers **both viewports**:

| Viewport | Width | Height | Represents         |
|----------|-------|--------|---------------------|
| Desktop  | 1400  |  900   | Laptop / monitor    |
| Mobile   |  390  |  844   | iPhone 14 / similar |

Use `browser_resize` to switch between them.

## Test checklist

### 1. Landing page (`/`)

**Desktop (1400x900):**
- [ ] Page loads with status 200, title contains "LiquidRound"
- [ ] Nav bar visible: logo, links (Platform, ECM Squad, How it works, Pricing), "Sign in" button
- [ ] Hero section: H1 headline, description paragraph, two CTA buttons (Buyer-Led, Seller-Led)
- [ ] Product demo GIF visible (img element exists)
- [ ] Stats row (4 items)
- [ ] Agent directory section renders (5 category groups)
- [ ] Footer renders with copyright + links
- [ ] Page is scrollable (take `fullPage` screenshot to confirm content extends beyond viewport)

**Mobile (390x844):**
- [ ] Page loads, title correct
- [ ] Nav shows logo + "Sign in" only (desktop links hidden)
- [ ] Hero section readable, CTAs stack vertically
- [ ] All sections render and page scrolls
- [ ] Footer visible at bottom

### 2. Sign-in overlay (both viewports)

- [ ] Click "Sign in" in nav -> overlay appears
- [ ] Click any CTA (Buyer-Led, Seller-Led) -> overlay appears with role pre-set
- [ ] Two tabs: Sign In / Register, tab switching works
- [ ] Login form: email + password fields, "Forgot password?" link
- [ ] Register form: name, email, password fields
- [ ] Forgot password form accessible from login
- [ ] Google OAuth button present ("Continue with Google")
- [ ] Cancel or backdrop click closes overlay
- [ ] Escape key closes overlay

### 3. Chat app (`/app`)

**Desktop (1400x900):**
- [ ] 3-pane layout renders: left pane (300px), center pane, right pane (News feed)
- [ ] Left pane sections in order: Sessions, Agents, Workspace, Training, Settings
- [ ] Workspace section: 9 links (Companies, Pipelines, Valuation, Analytics, Data Room, Documents, Deal history, Instructions, Help) -- NO "Settings" button
- [ ] Settings section: single "Profile / Account" link pointing to `/profile`
- [ ] Agents section: 5 category groups, expandable on click
- [ ] Center pane: header with "LiquidRound · Auto-routed" and Copy/Share buttons
- [ ] News pane is open and visible by default
- [ ] Investor Relations is expanded and Press Release Creator is visible
- [ ] No Artifact header button, tab, or right-pane artifact window is present
- [ ] Welcome hero with Baltic/Lithuanian company prompts (Grigeo, InMedica, Lietuvos Veterinarija)
- [ ] Sample cards at bottom show Baltic prompts
- [ ] Chat input + send button visible at bottom
- [ ] Hamburger menu NOT visible (desktop only)

**Mobile (390x844):**
- [ ] Left pane hidden by default
- [ ] Hamburger menu visible in header
- [ ] Click hamburger -> left pane slides in
- [ ] Left pane contents match desktop (same sections, same order)
- [ ] Settings section shows "Profile / Account" link
- [ ] Tap outside left pane -> closes it
- [ ] Welcome hero and sample cards render
- [ ] Chat input + send button visible within viewport

### 4. Chat interaction (both viewports)

**Desktop:**
- [ ] Send a query -> SSE stream renders agent response
- [ ] Right pane remains dedicated to News
- [ ] Agent artifacts render inline; generated memo PDFs open in a new browser tab
- [ ] Copy button copies chat text, shows green checkmark flash (1.8s)
- [ ] Share button fires /app/share, shows green checkmark flash
- [ ] "+ New chat" resets to clean state with welcome hero
- [ ] Session history: clicking a session loads its messages
- [ ] Session share: hover shows chain-link icon, click copies share URL

**Mobile:**
- [ ] Send a query -> chat response visible
- [ ] Hamburger still works after query (left pane opens with history)

### 5. Profile page (`/profile`)

**Desktop (1400x900):**
- [ ] Click "Profile / Account" in left pane Settings -> navigates to `/profile`
- [ ] Page title: "Profile & Preferences"
- [ ] Three sections render: Account, Deal Preferences, Notifications
- [ ] Account section includes currency selector (EUR/GBP/USD)
- [ ] "Back to app" link present and works

**Mobile (390x844):**
- [ ] Navigate to `/profile` directly
- [ ] All three sections render and are usable
- [ ] Forms are not clipped or overflowing

### 6. Shared chat (`/app/s/{token}`)

- [ ] Read-only view of shared chat renders
- [ ] Messages display with markdown rendering
- [ ] No input field or send button (readonly)
- [ ] Copy button present

## Versioning

The app version is defined in `utils/config.py` as `VERSION`. It is displayed in light grey next to the logo in both:
- **Landing page nav** (`components/landing.py`) — styled with `color:#64748b`
- **Chat app left pane header** (`components/chat_shell.py`) — styled via `.brand-version` in `static/app.css`

When bumping the version:
1. Update `VERSION` in `utils/config.py`
2. Verify it appears on both `/` and `/app` (both viewports)

## Architecture reference

**Z-index hierarchy (mobile):**
- 50: left pane (sidebar)
- 60: right pane (News feed)
- 100: `.signin-overlay` (auth modal on landing)

**Critical CSS patterns:**
- `.app` grid: `grid-template-columns: 300px 1fr`, `height: 100vh`, `overflow: hidden`
- `html, body`: NO `overflow: hidden` or `height: 100%` (breaks landing page scroll)
- `.app` has `padding-right: 420px` for the desktop News pane and removes it at the
  mobile breakpoint
- Dark theme: `.lr-dark` class on body for `/app`, NOT on landing page
- Landing page: own inline palette via `components/landing.py` constants (BG, BG_ELEV, INK, etc.)

**JS behavior:**
- `toggleNewsPane()`: preserves the desktop News pane state
- `toggleLeftPane()`: mobile hamburger, toggles left pane open/closed
- `shareChat()` / `copyChat()`: icon swap feedback via `_flashBtn()` (checkmark + grey for 1.8s)
- `shareSession(event, sid, btn)`: sidebar session share buttons
- `showSignIn(role)`: landing page sign-in overlay, optional role pre-set
- `setSid(sid)`: server pushes conversation ID to client via SSE `session` event
- `fillChat(text)`: fills chat input (used by agent chips and sample cards)
- `sendMessage(event)`: sends chat via SSE POST to `/app/chat`

**Static file serving:**
- `fast_app(static_path="static")` serves `static/foo.png` as `/foo.png`
- CSS: `/app.css` (not `/static/app.css`)
- Favicons: `/favicon.svg`, `/favicon.ico`, etc.

## How to verify

Use `browser_snapshot` (accessibility tree) as the primary verification tool -- it's faster and more reliable than screenshots for checking element presence, text content, and structure.

Use `browser_evaluate` for DOM state checks (classList, getBoundingClientRect, computed styles).

Use `browser_take_screenshot` when:
- Checking visual layout (overflow, alignment, spacing)
- Verifying responsive behavior
- Confirming dark theme styling
- The snapshot doesn't capture what you need (e.g., CSS-hidden elements)

Use `browser_click` / `browser_hover` to test interactive elements.

## Snapshot tips

- `depth: 2-3` for page-level structure checks
- `depth: 4-5` for section-level detail
- `boxes: true` to get bounding boxes for position verification
- Target a specific element (`target: e70`) to drill into a section without noise
- After `browser_click` or `browser_resize`, take a new snapshot before using refs

## Reporting results

After testing, report:
1. Which viewport(s) were tested
2. Pass/fail for each checklist item
3. Any console errors (note: some SSE-related errors on `/app` are expected when not authenticated)
4. Screenshots if any visual issue is found

## Email HTML formatting rules

Digest emails must render correctly on mobile (390px) and desktop email clients. These rules apply to `utils/digest.py:render_email_html()` and any future email templates.

**Layout:**
- `max-width:600px` on the outer container — wider breaks Gmail mobile
- Outer container uses `padding:0 12px` not `padding:0 24px` — saves horizontal space on small screens
- `-webkit-text-size-adjust:100%` on `<body>` — prevents iOS from inflating text
- `<meta name="viewport" content="width=device-width, initial-scale=1">` in `<head>`

**No tables for content layout:**
- Use stacked `<div>` cards instead of `<table>` rows
- Each card: `border:1px solid #e2e8f0; border-radius:8px; padding:12px; margin-bottom:8px`
- Side-by-side blocks within a card use `display:inline-block; width:48%; vertical-align:top; min-width:140px` — wraps naturally on mobile
- For Outlook compatibility, wrap inline-block pairs in `<!--[if mso]><table><tr><td>...<![endif]-->` conditional comments

**Typography:**
- Font stack: `'Inter','Helvetica Neue',Arial,sans-serif`
- Body text: `13px`, headings: `16px` section, `22px` brand
- No emojis in section headings (they render inconsistently across email clients)
- Country flags (emoji) are OK inline with company names

**Color palette (matches app dark theme):**
- Header/deep-dive background: `#0B1220` (navy)
- Accent/brand: `#F59E0B` (amber)
- Card text: `#0f172a` (near-black) on white cards
- Deep-dive body text: `#cbd5e1` on dark background
- Muted text: `#64748b`, `#94a3b8`
- Deal angle badge: `#e0f2fe` background
- Thesis block: `#f1f5f9` background with colored left border

**Testing email changes:**
1. Write mock data to HTML file, serve via `python3 -m http.server 8099 --directory /tmp`
2. Open in Playwright at both 390x844 and 1400x900
3. Take `fullPage` screenshots — check no horizontal overflow, text readable, cards stack cleanly
4. Send a real test: `python -m scripts.daily_deals` (sends to TO_EMAIL)
5. Verify delivery via IMAP (see below)

## Daily digest email verification

Credentials are in `.secrets` (gitignored). The digest is sent daily at `DIGEST_HOUR_UTC` (default 7 AM UTC) by an in-process scheduler in `main.py`. It only fires if the app process is running at that hour.

**IMAP connection (IONOS):**
```python
import imaplib, email
from email.header import decode_header

imap = imaplib.IMAP4_SSL('imap.ionos.co.uk')
# Load credentials from .secrets
imap.login(IONOS_EMAIL, IONOS_PASSWORD)
imap.select('INBOX')
```

**Check for today's digest:**
```python
from datetime import datetime
today = datetime.now().strftime('%d-%b-%Y')
status, msgs = imap.search(None, f'(FROM "info@liquidround.com" SINCE {today})')
# Should find at least 1 if digest ran today
```

**Digest email checklist:**
- [ ] Email arrived from `info@liquidround.com`
- [ ] Subject matches pattern: `LiquidRound Baltic Daily Digest — DD Mon YYYY`
- [ ] Sent to `TO_EMAIL` from `.env` (default: `liquidround@predictivelabs.co.uk`)
- [ ] HTML body contains deal content (companies, tickers, analysis)
- [ ] Unsubscribe link present

**Manual trigger (no scheduler needed):**
```bash
python -m scripts.daily_deals --dry-run          # preview HTML, don't send
python -m scripts.daily_deals                     # send to TO_EMAIL
python -m scripts.daily_deals --all               # send to all opted-in users
```

**Troubleshooting no digest:**
1. Was the app process running at `DIGEST_HOUR_UTC`? The scheduler is in-process, not cron.
2. Check `DIGEST_FREQUENCY` in `.env` — must be `daily` (not `off`).
3. Check `POSTMARK_API_TOKEN` is set and valid.
4. Run `--dry-run` to verify content generation works.

## CI/CD — autodeploy via Coolify

**Autodeploy is on.** Every push to `main` auto-deploys to production with no manual step.

**Pipeline:** push to `main` -> GitHub Actions (`.github/workflows/deploy.yml`) -> Coolify webhook (`COOLIFY_WEBHOOK_URL` + `COOLIFY_TOKEN` secrets) -> Docker build from `Dockerfile` -> deploy to both domains.

**Domains — both wired to the same Coolify service:**
- `liquidround.com` — A record `72.62.88.13`. Live and current; should match `VERSION` in `utils/config.py` within ~2 min of a push.
- `liquidround.ai` — A record `72.62.88.13` (same server). Live releases are served through the Coolify proxy (Traefik) with Let's Encrypt.
- Both domains are listed in the Coolify service's Domains field: `https://liquidround.com,https://liquidround.ai`.

**GitHub repo:** `predictivelabsai/liquidround` (origin)

**Required GitHub secrets:**
- `COOLIFY_WEBHOOK_URL` — the Coolify deployment webhook endpoint
- `COOLIFY_TOKEN` — bearer token for authentication

**Deploy workflow (`deploy.yml`):**
```yaml
on:
  push:
    branches: [main]
# Triggers: curl GET to COOLIFY_WEBHOOK_URL with Bearer token
```

**Verifying an autodeploy:**
1. After push, confirm the action ran: `gh run list --limit 1` then `gh run view <run-id>`.
2. Confirm both live sites respond and are current:
   ```
   curl -s https://liquidround.com/ | grep -oE 'v0\.[0-9]+\.[0-9]+'
   curl -s https://liquidround.ai/  | grep -oE 'v0\.[0-9]+\.[0-9]+'
   ```
   Both must match `VERSION` in `utils/config.py`.
3. Spot-check the shipped change on the live site via Playwright against `https://liquidround.com` (per the UI-validation skill).

**Docker build:**
- `Dockerfile` — Python 3.13-slim, installs system deps (gcc, libpq-dev), pip installs from `requirements.txt`, runs `python main.py`
- `docker-compose.yml` — local dev with port mapping

**Rollback:** push a revert commit to `main` (autodeploy will ship it), or redeploy a previous image in the Coolify dashboard.

**Before shipping a user-facing change to autodeploy:** the mandatory local Playwright validation (`.opencode/skills/validate-liquidround-ui/SKILL.md`) must pass — never push to `main` while it is failing.

### Coolify dashboard admin

**URL:** `https://coolify.finespresso.org`
**Credentials:** in `.secrets` (gitignored) under `COOLIFY_DASHBOARD_EMAIL` / `COOLIFY_DASHBOARD_PASSWORD`.

**Coolify project/service path:**
- Project: `predictive labs apps` (ID: `d4wgogcokwsgw4oc4k0cco8c`)
- Application: `predictivelabsai/liquidround` (ID: `h48go0swc8gs0w8wg8oo0w8c`)
- Server: `finespresso-server` (ID: `psks0gwws484gkk4w4w4osk0`)
- Direct link: `https://coolify.finespresso.org/project/d4wgogcokwsgw4oc4k0cco8c/environment/hg4wgcgwkg8oc8kkwoo8wwks/application/h48go0swc8gs0w8wg8oo0w8c`

**Key admin actions via dashboard:**
- **Change domains:** General tab -> Domains field -> edit -> Save. Then Redeploy.
- **Redeploy:** Click "Redeploy" button on the General tab.
- **Restart proxy** (fixes expired SSL certs): Server -> finespresso-server -> click "Restart Proxy" -> confirm. Wait ~60s for Traefik to reissue Let's Encrypt certs.
- **View deployments:** Application -> Deployments tab.
- **View logs:** Application -> Logs tab.

**Driving Coolify with Playwright:** the dashboard is a standard web app. Use the credentials from `.secrets`, navigate to the URLs above, and interact with buttons/inputs. Screenshots go in `screenshots/coolify-*.png`.

### Namecheap DNS admin

**Domain:** `liquidround.ai` (registered at Namecheap)
**Credentials:** in `.secrets` (gitignored) under `NAMECHEAP_USERNAME` / `NAMECHEAP_EMAIL` / `NAMECHEAP_PASSWORD`.
**Login URL:** `https://www.namecheap.com/myaccount/login/`
**DNS panel:** Advanced DNS tab. The A record `@ -> 72.62.88.13` must be present for the domain to resolve to the Coolify server.

**When DNS changes are needed:**
1. Log into Namecheap.
2. Go to Domain List -> Manage -> Advanced DNS.
3. Add/edit the A record. TTL: Automatic.
4. Wait for DNS propagation (`dig +short liquidround.ai A` should show `72.62.88.13`).
5. If SSL cert is expired after a DNS change, restart the Coolify proxy (see above).

## Cleanup

Always close the browser when done:
```
browser_close
```

Kill the dev server if you started it:
```
kill $(lsof -ti:5007) 2>/dev/null
```
