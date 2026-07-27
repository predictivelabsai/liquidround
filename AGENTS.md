# LiquidRound repository rules

## Mandatory local UI validation

Before committing or pushing any user-facing change, use the repository skill
`.codex/skills/validate-liquidround-ui/SKILL.md`.

- Run the affected routes locally with a real Playwright browser.
- Verify rendering, navigation, key interactions, browser console, network failures, and server logs.
- Capture stable representative screenshots in `screenshots/` with descriptive kebab-case names.
- Preserve useful screenshots for later user-guide and product-demo generation.
- Never commit or push a user-facing change while its local Playwright validation is failing.
