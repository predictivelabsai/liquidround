---
name: validate-liquidround-ui
description: Validate LiquidRound UI changes with a real local Playwright browser before committing or pushing. Use whenever routes, navigation, forms, styles, JavaScript, exports, user-facing workflows, guides, demos, or screenshots change, and whenever preparing a LiquidRound release or deployment.
---

# Validate LiquidRound UI

Use the system `playwright` skill for browser operation.

## Required workflow

1. Inspect the working tree and identify every affected user-facing route.
2. Start LiquidRound locally from the exact source state intended for commit.
3. Confirm the local HTTP endpoint responds before opening the browser.
4. Use a real Playwright browser at desktop size. Add a mobile pass when layout or navigation changed.
5. Exercise the changed workflow, including navigation, required-field validation, primary actions, and relevant error states. Do not call paid or destructive integrations unless the user requested an end-to-end test.
6. Check browser console errors, failed network requests, HTTP status, visible content, and server logs.
7. Capture representative screenshots under `screenshots/` after the page reaches a stable validated state. Use descriptive kebab-case filenames, for example:
   - `screenshots/investor-relations-press-release-desktop.png`
   - `screenshots/investor-relations-press-release-mobile.png`
   - `screenshots/investor-relations-generated-draft.png`
8. Preserve screenshots suitable for later user-guide and product-demo generation. Do not include passwords, tokens, personal data, debug overlays, transient loading states, or browser chrome.
9. Report the tested URLs, viewport sizes, interactions, console/network results, screenshot paths, and any untested integration boundary.
10. Do not commit or push user-facing changes when the local Playwright check fails. Fix and repeat the check first.

## Authentication

Prefer an existing test account. If unavailable, use a temporary browser-only local session where the application architecture permits it. Do not create production users or modify production data merely to render a local page.

## Screenshot policy

Treat `screenshots/` as the reusable source library for documentation and demos. Replace obsolete screenshots only when the newer capture covers the same workflow and is clearly superior. Keep intermediate debugging captures outside this library.
