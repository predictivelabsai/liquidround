#!/usr/bin/env bash
# Build the LiquidRound user guide: Markdown → HTML → PDF
# Requires: pandoc, weasyprint
# Usage: bash scripts/build_user_guide.sh

set -euo pipefail
cd "$(dirname "$0")/.."

SRC="docs/liquidround_user_guide.md"
CSS="docs/assets/guide.css"
OUT_HTML="docs/liquidround_user_guide.html"
OUT_PDF="docs/liquidround_user_guide.pdf"

echo "→ Converting Markdown to HTML..."
pandoc "$SRC" \
  --standalone \
  --css="$CSS" \
  --metadata title="LiquidRound User Guide" \
  --from=markdown+yaml_metadata_block \
  --to=html5 \
  -o "$OUT_HTML"

echo "→ Converting HTML to PDF (A4 landscape)..."
weasyprint "$OUT_HTML" "$OUT_PDF"

echo "✓ Built: $OUT_PDF"
