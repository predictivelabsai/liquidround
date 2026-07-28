---
name: fasthtml-user-guide
description: >
  Generate a polished landscape user guide (PDF + PPTX) with a real product
  screenshot on every page, for a FastHTML server-rendered web app (the Fast*
  cockpit family: FastClinic, DrVet, FastCRM, FastERP, …). Use when the user
  wants a user guide, slide deck, product walkthrough doc, or "screenshots on
  each page" guide built from a running app. Drives a headless browser to
  capture screens, then renders markdown → PDF (WeasyPrint) and PPTX (python-pptx).
---

# FastHTML app → landscape user guide (PDF + PPTX)

Produces a shareable user guide where each feature gets one slide: a short
explanation on the left, a live screenshot floated on the right, on a branded
landscape page. Two formats from one markdown master — PDF (print/email) and
PPTX (editable deck). This is the pipeline used for the DrVet and FastClinic
guides.

```text
running app -> capture screenshots (Playwright) -> write slide markdown
   -> pandoc+WeasyPrint (PDF, A4 landscape) + python-pptx (16:9 PPTX)
```

`you` = the developer asking the agent to build the guide.

## When to use

- "Generate a user guide / product guide with screenshots on each page"
- "Build a slide deck (PDF and PPTX) explaining the app"
- Any Fast* FastHTML cockpit that needs an end-user walkthrough document.

Do **not** use for API/developer reference docs (no screenshots) or a README.

## Prerequisites

- The app runs locally and is reachable (e.g. `http://localhost:5005`), with a
  demo login. **Seed operational data first** (appointments, invoices, reminders)
  so feature pages render populated, not empty — empty screenshots look broken.
- Tools: `pandoc`, `weasyprint` (CLI), and Python packages `python-pptx`,
  `playwright` + a Chromium (`python -m playwright install chromium`), `pillow`.

## Assets in this skill (`scripts/`)

- `capture_guide_screenshots.py` — headless-Chromium screenshotter. Edit the
  `SHOTS` list (filename, interaction-kind, route) for the target app's routes
  and login selectors. `kind` handles special cases (login page, click-to-populate).
- `build_pptx.py` — markdown → 16:9 PPTX: branded cover, native tables, one
  screenshot per slide, inline-markdown runs. Recolor the palette constants at
  the top to the app's brand.
- `build_user_guide.sh` — orchestrator: newest `docs/<app>_user_guide_*.md`
  → PDF (pandoc + WeasyPrint + `guide.css`) and PPTX. Stamps version + date.
- `guide.css.template` — landscape print stylesheet (screenshot floats right,
  slide-title bar, cover). Copy to `docs/assets/guide.css` and swap the palette.

## Procedure

1. **Palette** — copy `guide.css.template` → `docs/assets/guide.css` and replace
   the brand hex values (title bar, accent bar, links). Do the same for the
   `RGBColor` constants at the top of `build_pptx.py` and its `FOOTER`.
2. **Screenshots** — adapt `capture_guide_screenshots.py` `SHOTS` to the app's
   routes and login fields. Seed demo data, start the app, then:
   `DEMO_BASE_URL=http://localhost:5005 python scripts/capture_guide_screenshots.py --out docs/img`
   Inspect a few PNGs; re-seed and re-capture any that render empty (`--only`).
3. **Write the guide markdown** — `docs/<app>_user_guide_<date>.md`, slides
   separated by `---`. Structure: a `::: cover` slide, a `## Contents` slide,
   then one `## Feature` slide each with a `![alt](img/NN-name.png)` and 2–4
   short sentences. Keep it end-user friendly — **no internal/technical terms**
   (table names, storage engines, file paths). End with a "weekly playbook".
4. **Build** — `bash scripts/build_user_guide.sh` → PDF + PPTX in `docs/`.
5. **Verify** — read a few PDF pages (cover, contents, a screenshot slide) to
   confirm layout/palette; check the Contents fits one page (tighten long lists
   onto one line if it overflows); confirm the PPTX opens with images embedded.
6. **Commit** — ensure `docs/img/*.png` are not caught by a global `*.png`
   gitignore (add `!docs/img/*.png`), so the guide rebuilds reproducibly.

## Notes

- Playwright browser version must match the venv's `playwright` package — run
  `python -m playwright install chromium` in that venv if launch fails.
- WeasyPrint floats the screenshot right and caps its height so each slide fits
  one landscape page; keep body text short so it doesn't overflow past the image.
- The same repo usually also has a `demo_walkthrough.py` that stitches the
  screens into an animated GIF for the README — a lighter companion to this guide.
