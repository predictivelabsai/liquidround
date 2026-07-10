"""Shared branded PDF builder for workspace pages.

Usage:
    from utils.page_pdf import build_pdf, Section, Row
    sections = [
        Section("Companies", rows=[
            Row(["Acme Corp", "Fintech", "€12M", "Estonia"]),
        ], headers=["Name", "Sector", "Revenue", "Country"]),
        Section("Summary", text="Total 42 companies in pool."),
    ]
    path = build_pdf("Companies", "Company directory export", sections)
    return FileResponse(str(path), ...)
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer,
    HRFlowable, Table as RLTable, TableStyle,
)

_CACHE_DIR = Path("/tmp/liquidround-page-pdf")
_CACHE_DIR.mkdir(parents=True, exist_ok=True)

INK       = HexColor("#0F172A")
INK_MUTED = HexColor("#475569")
ACCENT    = HexColor("#F59E0B")
NAVY      = HexColor("#0B1220")
RULE      = HexColor("#CBD5E1")
WHITE     = HexColor("#FFFFFF")
LIGHT_BG  = HexColor("#F8FAFC")


@dataclass
class Row:
    cells: list[str]


@dataclass
class Section:
    title: str
    text: str = ""
    rows: list[Row] = field(default_factory=list)
    headers: list[str] = field(default_factory=list)
    kv: list[tuple[str, str]] = field(default_factory=list)


def _styles():
    ss = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("pg_title", parent=ss["Title"], fontName="Helvetica-Bold",
                                fontSize=20, leading=24, textColor=INK, spaceAfter=2),
        "subtitle": ParagraphStyle("pg_subtitle", parent=ss["Normal"], fontName="Helvetica",
                                   fontSize=10, textColor=INK_MUTED, spaceAfter=10),
        "h2": ParagraphStyle("pg_h2", parent=ss["Heading2"], fontName="Helvetica-Bold",
                             fontSize=13, leading=17, textColor=INK, spaceAfter=5, spaceBefore=12),
        "body": ParagraphStyle("pg_body", parent=ss["BodyText"], fontName="Helvetica",
                               fontSize=9, leading=12.5, textColor=INK, spaceAfter=3),
        "kv_label": ParagraphStyle("pg_kv_label", parent=ss["Normal"], fontName="Helvetica",
                                   fontSize=8.5, textColor=INK_MUTED),
        "kv_value": ParagraphStyle("pg_kv_value", parent=ss["Normal"], fontName="Helvetica-Bold",
                                   fontSize=8.5, textColor=INK),
        "th": ParagraphStyle("pg_th", parent=ss["Normal"], fontName="Helvetica-Bold",
                             fontSize=8, textColor=INK_MUTED, leading=10),
        "td": ParagraphStyle("pg_td", parent=ss["Normal"], fontName="Helvetica",
                             fontSize=8.5, textColor=INK, leading=11),
        "caption": ParagraphStyle("pg_caption", parent=ss["Italic"], fontName="Helvetica-Oblique",
                                  fontSize=7.5, leading=9, textColor=INK_MUTED),
    }


_INLINE_RE = [
    (re.compile(r"\*\*(.+?)\*\*"), r"<b>\1</b>"),
    (re.compile(r"`([^`]+)`"), r"<font face='Courier'>\1</font>"),
]


def _esc(text: str) -> str:
    out = str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    for rx, repl in _INLINE_RE:
        out = rx.sub(repl, out)
    return out


def build_pdf(
    page_title: str,
    page_subtitle: str,
    sections: list[Section],
    *,
    date_str: str | None = None,
) -> Path:
    today = date_str or date.today().isoformat()
    st = _styles()

    fid = hashlib.sha1(f"{page_title}-{today}".encode()).hexdigest()[:16]
    out = _CACHE_DIR / f"{fid}.pdf"

    def _footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(INK_MUTED)
        canvas.drawString(2 * cm, 0.9 * cm, f"LiquidRound · {page_title} · {today}")
        canvas.drawRightString(A4[0] - 2 * cm, 0.9 * cm, f"Page {doc.page}")
        canvas.setStrokeColor(RULE)
        canvas.setLineWidth(0.3)
        canvas.line(2 * cm, 1.15 * cm, A4[0] - 2 * cm, 1.15 * cm)
        canvas.restoreState()

    def _header(canvas, doc):
        _footer(canvas, doc)
        if doc.page == 1:
            canvas.saveState()
            canvas.setFillColor(NAVY)
            canvas.rect(0, A4[1] - 1.5 * cm, A4[0], 1.5 * cm, fill=True, stroke=False)
            canvas.setFont("Helvetica-Bold", 15)
            canvas.setFillColor(ACCENT)
            canvas.drawString(2 * cm, A4[1] - 1.05 * cm, "LiquidRound")
            canvas.setFont("Helvetica", 8.5)
            canvas.setFillColor(HexColor("#94A3B8"))
            canvas.drawRightString(A4[0] - 2 * cm, A4[1] - 1.05 * cm,
                                   f"{page_subtitle} — {today}")
            canvas.restoreState()

    doc = BaseDocTemplate(
        str(out), pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=2 * cm, bottomMargin=1.6 * cm,
        title=f"LiquidRound — {page_title} — {today}",
        author="LiquidRound · Predictive Labs Ltd",
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="main")
    doc.addPageTemplates([PageTemplate(id="page", frames=[frame], onPage=_header)])

    story: list = [Spacer(1, 4)]

    for sec in sections:
        story.append(Paragraph(_esc(sec.title), st["h2"]))

        if sec.text:
            for line in sec.text.split("\n"):
                line = line.strip()
                if line:
                    story.append(Paragraph(_esc(line), st["body"]))

        if sec.kv:
            kv_data = [[Paragraph(_esc(k), st["kv_label"]),
                         Paragraph(_esc(v), st["kv_value"])] for k, v in sec.kv]
            kv_table = RLTable(kv_data, colWidths=[5 * cm, None])
            kv_table.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ("LINEBELOW", (0, 0), (-1, -1), 0.3, RULE),
            ]))
            story.append(kv_table)
            story.append(Spacer(1, 4))

        if sec.rows and sec.headers:
            avail = doc.width
            n_cols = len(sec.headers)
            col_w = avail / n_cols

            header_cells = [Paragraph(_esc(h), st["th"]) for h in sec.headers]
            data_rows = [[Paragraph(_esc(c), st["td"]) for c in row.cells[:n_cols]]
                         for row in sec.rows]
            all_data = [header_cells] + data_rows

            tbl = RLTable(all_data, colWidths=[col_w] * n_cols, repeatRows=1)
            tbl.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), HexColor("#F1F5F9")),
                ("TEXTCOLOR", (0, 0), (-1, 0), INK_MUTED),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 8),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("LINEBELOW", (0, 0), (-1, 0), 0.8, INK_MUTED),
                ("LINEBELOW", (0, 1), (-1, -1), 0.3, RULE),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_BG]),
            ]))
            story.append(tbl)
            story.append(Spacer(1, 6))

        story.append(Spacer(1, 2))

    story.append(Spacer(1, 12))
    story.append(HRFlowable(width="100%", thickness=0.3, color=RULE, spaceAfter=6))
    story.append(Paragraph(
        "Generated by LiquidRound AI · Predictive Labs Ltd. "
        "AI-generated analysis for informational purposes only. Not investment advice.",
        st["caption"],
    ))

    doc.build(story)
    return out


def pdf_filename(slug: str, date_str: str | None = None) -> str:
    today = date_str or date.today().isoformat()
    return f"LiquidRound-{slug}-{today}.pdf"
