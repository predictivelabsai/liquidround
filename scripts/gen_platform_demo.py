#!/usr/bin/env python3
"""Archive prior guide outputs and build a timestamped LiquidRound demo PDF.

The PDF includes a cover, a page-numbered table of contents, footer page
numbers, and the content from docs/user_guide.md.
"""
from __future__ import annotations

import argparse
import html
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
SOURCE = DOCS / "user_guide.md"
ARCHIVE = DOCS / "archive"
PREFIX = "liquidround-ai-platform-demo"

NAVY = "#0B1220"
AMBER = "#F59E0B"
INK = "#0F172A"
MUTED = "#64748B"
LINE = "#CBD5E1"
PALE = "#F8FAFC"


def timestamp_slug() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def archive_outputs(stamp: str) -> list[Path]:
    """Move prior timestamped demo outputs into one timestamped archive folder."""
    targets = sorted(
        p for p in DOCS.glob(f"{PREFIX}-*")
        if p.is_file() and p.suffix.lower() in {".md", ".pdf", ".docx", ".pptx", ".html"}
    )
    if not targets:
        return []
    destination = ARCHIVE / stamp
    destination.mkdir(parents=True, exist_ok=True)
    moved = []
    for path in targets:
        dest = destination / path.name
        collision = 1
        while dest.exists():
            dest = destination / f"{path.stem}-archived-{collision}{path.suffix}"
            collision += 1
        shutil.move(str(path), str(dest))
        moved.append(dest)
    return moved


def parse_source(path: Path) -> tuple[str, list[dict]]:
    text = path.read_text(encoding="utf-8")
    title = "LiquidRound AI Platform Demo"
    sections: list[dict] = []
    current = None
    for line in text.splitlines():
        match = re.match(r"^(#{1,3})\s+(.+)$", line)
        if match:
            level = len(match.group(1))
            heading = match.group(2).strip()
            if level == 1:
                title = heading
                continue
            if current:
                sections.append(current)
            current = {"level": level, "title": heading, "lines": []}
        elif current is not None:
            current["lines"].append(line)
    if current:
        sections.append(current)
    return title, sections


def inline_markup(text: str) -> str:
    # ReportLab's mini-HTML parser can leave a stray semicolon when extracting
    # ampersand entities; spelling out "and" keeps both display and PDF text clean.
    text = text.replace("M&A", "Mergers and Acquisitions")
    text = html.escape(text, quote=False)
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"`(.+?)`", r'<font face="Courier">\1</font>', text)
    return text


def build_pdf(source: Path, output: Path, stamp: str) -> None:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        BaseDocTemplate, Frame, PageBreak, PageTemplate, Paragraph, Spacer,
        Table, TableStyle,
    )
    from reportlab.platypus.tableofcontents import TableOfContents

    title, sections = parse_source(source)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        "DemoCover", parent=styles["Title"], fontName="Helvetica-Bold",
        fontSize=29, leading=34, textColor=colors.HexColor(AMBER),
        alignment=TA_CENTER, spaceAfter=12,
    ))
    styles.add(ParagraphStyle(
        "DemoSubtitle", parent=styles["BodyText"], fontSize=12, leading=17,
        textColor=colors.HexColor(PALE), alignment=TA_CENTER,
    ))
    styles.add(ParagraphStyle(
        "DemoH2", parent=styles["Heading1"], fontName="Helvetica-Bold",
        fontSize=18, leading=22, textColor=colors.HexColor(NAVY),
        spaceBefore=12, spaceAfter=8, keepWithNext=True,
    ))
    styles.add(ParagraphStyle(
        "DemoH3", parent=styles["Heading2"], fontName="Helvetica-Bold",
        fontSize=13, leading=17, textColor=colors.HexColor(AMBER),
        spaceBefore=9, spaceAfter=5, keepWithNext=True,
    ))
    styles.add(ParagraphStyle(
        "DemoBody", parent=styles["BodyText"], fontSize=9.3, leading=13.2,
        textColor=colors.HexColor(INK), spaceAfter=5,
    ))
    styles.add(ParagraphStyle(
        "DemoBullet", parent=styles["BodyText"], fontSize=9.3, leading=13.2,
        leftIndent=15, firstLineIndent=-8, textColor=colors.HexColor(INK),
        spaceAfter=3,
    ))
    styles.add(ParagraphStyle(
        "DemoTOCHeading", parent=styles["Heading1"], fontName="Helvetica-Bold",
        fontSize=20, textColor=colors.HexColor(NAVY), spaceAfter=12,
    ))
    styles.add(ParagraphStyle(
        "DemoTOC1", parent=styles["BodyText"], fontSize=10, leading=14,
        leftIndent=0, firstLineIndent=0, textColor=colors.HexColor(INK),
        spaceBefore=3,
    ))
    styles.add(ParagraphStyle(
        "DemoTOC2", parent=styles["BodyText"], fontSize=9, leading=12,
        leftIndent=12, firstLineIndent=0, textColor=colors.HexColor(MUTED),
    ))
    styles.add(ParagraphStyle(
        "DemoCell", parent=styles["BodyText"], fontSize=7.7, leading=10,
        textColor=colors.HexColor(INK),
    ))
    styles.add(ParagraphStyle(
        "DemoCellHead", parent=styles["BodyText"], fontName="Helvetica-Bold",
        fontSize=8, leading=10, textColor=colors.white,
    ))

    class DemoDocTemplate(BaseDocTemplate):
        def afterFlowable(self, flowable):
            if isinstance(flowable, Paragraph) and hasattr(flowable, "_toc_level"):
                level = flowable._toc_level
                text = flowable.getPlainText()
                key = flowable._toc_key
                self.canv.bookmarkPage(key)
                self.canv.addOutlineEntry(text, key, level=level, closed=False)
                self.notify("TOCEntry", (level, text, self.page, key))

    page_w, page_h = A4
    frame = Frame(18 * mm, 18 * mm, page_w - 36 * mm, page_h - 34 * mm,
                  leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)

    def decorate(canvas, doc):
        canvas.saveState()
        if doc.page == 1:
            canvas.setFillColor(colors.HexColor(NAVY))
            canvas.rect(0, 0, page_w, page_h, fill=1, stroke=0)
        else:
            canvas.setStrokeColor(colors.HexColor(LINE))
            canvas.line(18 * mm, 14 * mm, page_w - 18 * mm, 14 * mm)
            canvas.setFont("Helvetica", 7.5)
            canvas.setFillColor(colors.HexColor(MUTED))
            canvas.drawString(18 * mm, 9 * mm, "LiquidRound AI Platform Demo")
            canvas.drawRightString(page_w - 18 * mm, 9 * mm, f"Page {doc.page}")
        canvas.restoreState()

    doc = DemoDocTemplate(
        str(output), pagesize=A4, title=title,
        author="Predictive Labs Ltd", subject="LiquidRound AI Platform Demo",
    )
    doc.addPageTemplates(PageTemplate(id="demo", frames=[frame], onPage=decorate))
    story = [
        Spacer(1, 62 * mm),
        Paragraph(title, styles["DemoCover"]),
        Paragraph("Mergers and Acquisitions · IPO · Public Markets · Investor Relations", styles["DemoSubtitle"]),
        Spacer(1, 9 * mm),
        Paragraph(f"Generated {stamp} · Predictive Labs Ltd", styles["DemoSubtitle"]),
        PageBreak(),
        Paragraph("Table of Contents", styles["DemoTOCHeading"]),
    ]
    toc = TableOfContents()
    toc.levelStyles = [styles["DemoTOC1"], styles["DemoTOC2"]]
    story.extend([toc, PageBreak()])

    def add_table(lines: list[str]):
        rows = []
        for line in lines:
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells):
                continue
            style = styles["DemoCellHead"] if not rows else styles["DemoCell"]
            rows.append([Paragraph(inline_markup(cell), style) for cell in cells])
        if not rows:
            return
        widths = [(page_w - 36 * mm) / len(rows[0])] * len(rows[0])
        table = Table(rows, colWidths=widths, repeatRows=1, hAlign="LEFT")
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(NAVY)),
            ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor(PALE)),
            ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor(LINE)),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.extend([table, Spacer(1, 5)])

    heading_index = 0
    for section in sections:
        if section["title"] == "Table of Contents":
            continue
        level = 0 if section["level"] == 2 else 1
        style = styles["DemoH2"] if level == 0 else styles["DemoH3"]
        heading_index += 1
        heading = Paragraph(inline_markup(section["title"]), style)
        heading._toc_level = level
        heading._toc_key = f"heading-{heading_index}"
        story.append(heading)

        lines = section["lines"]
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if line.startswith("|"):
                table_lines = []
                while i < len(lines) and lines[i].strip().startswith("|"):
                    table_lines.append(lines[i].strip())
                    i += 1
                add_table(table_lines)
                continue
            if not line or line == "---":
                story.append(Spacer(1, 3))
            elif re.match(r"^\d+\.\s+", line):
                story.append(Paragraph(inline_markup(line), styles["DemoBullet"]))
            elif line.startswith("- "):
                story.append(Paragraph("• " + inline_markup(line[2:]), styles["DemoBullet"]))
            elif line.startswith("> "):
                story.append(Paragraph("<i>" + inline_markup(line[2:]) + "</i>", styles["DemoBody"]))
            elif not line.startswith("!["):
                story.append(Paragraph(inline_markup(line), styles["DemoBody"]))
            i += 1

    output.parent.mkdir(parents=True, exist_ok=True)
    doc.multiBuild(story)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--timestamp", default=timestamp_slug())
    parser.add_argument("--no-archive", action="store_true")
    args = parser.parse_args()
    stamp = args.timestamp
    if not re.fullmatch(r"\d{8}T\d{6}Z", stamp):
        parser.error("--timestamp must use YYYYMMDDTHHMMSSZ")
    if not SOURCE.exists():
        parser.error(f"missing source: {SOURCE}")

    moved = [] if args.no_archive else archive_outputs(stamp)
    slug = f"{PREFIX}-{stamp}"
    markdown_out = DOCS / f"{slug}.md"
    pdf_out = DOCS / f"{slug}.pdf"
    shutil.copy2(SOURCE, markdown_out)
    build_pdf(SOURCE, pdf_out, stamp)

    print(f"Archived: {len(moved)} file(s)")
    print(f"Markdown: {markdown_out}")
    print(f"PDF: {pdf_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
