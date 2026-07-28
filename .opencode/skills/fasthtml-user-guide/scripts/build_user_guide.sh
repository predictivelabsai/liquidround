#!/usr/bin/env bash
# Build the FastClinic user guide as a landscape slide deck — PDF + PPTX.
#
#   bash scripts/build_user_guide.sh                       # newest dated guide
#   bash scripts/build_user_guide.sh docs/fastclinic_user_guide_2026-07-20.md
#
# Pipeline:
#   PDF  — pandoc (md -> standalone HTML + assets/guide.css) -> WeasyPrint
#          (A4 landscape, one slide per "---", screenshot floated per page).
#   PPTX — python-pptx (md -> 16:9 deck with a branded cover, native tables,
#          and one screenshot per slide), kept visually in sync with the PDF.
# Screenshots come from docs/img/ — refresh them with:
#   DEMO_BASE_URL=http://localhost:5005 python scripts/capture_guide_screenshots.py
#
# Requires: pandoc, weasyprint, python-pptx. Run from the repo root.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="${PYTHON:-$ROOT/.venv/bin/python}"
cd "$ROOT/docs"

# Guide source: explicit arg, else the newest dated guide.
if [ "${1:-}" != "" ]; then
  SRC="$(basename "$1")"
else
  SRC="$(ls -1 fastclinic_user_guide_*.md 2>/dev/null | sort | tail -1)"
fi
[ -n "${SRC:-}" ] && [ -f "$SRC" ] || { echo "⚠ no guide markdown found (docs/fastclinic_user_guide_*.md)"; exit 1; }

BASE="${SRC%.md}"
HTML="${BASE}.html"
PDF="${BASE}.pdf"
PPTX="${BASE}.pptx"
TITLE="FastClinic — User Guide"

VERSION="$(awk '{print $1; exit}' "$ROOT/VERSION" 2>/dev/null || echo 0.1.0)"
GEN_DATE="$(date +%Y-%m-%d)"
echo "→ building ${SRC} · v${VERSION} · ${GEN_DATE}"

# Stamp the PDF page footer (right-hand @page content in guide.css).
sed -i -E "s|content: \"[^\"]*fastclinic\.example\"|content: \"v${VERSION} · ${GEN_DATE} · fastclinic.example\"|" assets/guide.css

# PDF
pandoc "$SRC" -s -o "$HTML" \
  --from=markdown-implicit_figures \
  --css "assets/guide.css" \
  --metadata pagetitle="${TITLE} (v${VERSION}, ${GEN_DATE})"
weasyprint "$HTML" "$PDF"           # base dir = docs/, so assets/ + img/ resolve
rm -f "$HTML"
echo "✓ PDF  docs/$PDF ($(du -h "$PDF" | cut -f1))"

# PPTX
"$PY" "$ROOT/scripts/build_pptx.py" "$SRC" "$PPTX" "$TITLE"
echo "✓ PPTX docs/$PPTX ($(du -h "$PPTX" | cut -f1))"

echo "✓ FastClinic user guide built (v${VERSION}, ${GEN_DATE}): PDF + PPTX."
