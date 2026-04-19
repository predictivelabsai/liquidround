"""Unit tests for the memo → PDF pipeline.

Pure-Python — no live HTTP. Exercises the markdown_to_pdf renderer directly
and validates the file comes out as a readable PDF.
"""
from __future__ import annotations

from pathlib import Path

from chat_memo_pdf import markdown_to_pdf


SAMPLE_MEMO = """# Meridian Healthcare — IC Memo

## Executive Summary

**Recommendation:** APPROVE at EUR 120M EV (11x EV/EBITDA).

Base case returns: **MOIC 2.3x, IRR 22%** over a 5-year hold.

## Investment Thesis

- Market leader in Baltic HCIT
- 24% LTM revenue growth, 32% EBITDA margin
- Fragmented competitive landscape (top-5 share < 40%)

## Risks

- Integration complexity
- Customer concentration (top-10 = 45% of revenue)
- Regulatory review in Lithuania

## Returns

Base case 22% IRR at 11x exit multiple; bull case 32% at 13x; bear 9% at 9x.
"""


def test_markdown_to_pdf_writes_valid_pdf(tmp_path: Path):
    out = tmp_path / "memo.pdf"
    markdown_to_pdf(SAMPLE_MEMO, out, title="Meridian IC")
    assert out.exists()
    size = out.stat().st_size
    assert size > 1000, f"PDF suspiciously small: {size} bytes"
    with out.open("rb") as f:
        header = f.read(4)
    assert header == b"%PDF", "file header is not a valid PDF signature"


def test_markdown_to_pdf_handles_empty_input(tmp_path: Path):
    out = tmp_path / "empty.pdf"
    markdown_to_pdf("", out, title="Empty")
    assert out.exists()
    with out.open("rb") as f:
        assert f.read(4) == b"%PDF"


def test_markdown_to_pdf_escapes_html(tmp_path: Path):
    out = tmp_path / "escape.pdf"
    markdown_to_pdf("# <script>alert(1)</script>\n\nA & B > C", out)
    assert out.exists()
    assert out.stat().st_size > 800
