"""Canonical parsing pipeline for SEC/Canadian transaction documents.

Acquisition is regulator-specific. Parsing and fact extraction operate on the
same normalized document/section model regardless of where an authorized
document came from.
"""
from __future__ import annotations

import hashlib
import re
import tempfile
from html import unescape
from pathlib import Path


_DOCUMENT_RE = re.compile(r"<DOCUMENT>(.*?)</DOCUMENT>", re.IGNORECASE | re.DOTALL)
_FIELD_RE = re.compile(r"<(TYPE|SEQUENCE|FILENAME|DESCRIPTION)>([^\r\n<]*)", re.IGNORECASE)
_ITEM_RE = re.compile(
    r"\bITEM\s+(1\.01|2\.01|5\.01|5\.06|9\.01)\b", re.IGNORECASE
)


def html_to_markdown(value: str) -> str:
    """Convert filing HTML to compact, auditable markdown-like text."""
    value = re.sub(r"<(?:br|hr)\s*/?>", "\n", value, flags=re.IGNORECASE)
    value = re.sub(
        r"</?(?:p|div|tr|table|ul|ol|section|article)[^>]*>",
        "\n",
        value,
        flags=re.IGNORECASE,
    )
    value = re.sub(
        r"<h([1-6])[^>]*>(.*?)</h\1>",
        lambda m: f"\n{'#' * int(m.group(1))} {m.group(2)}\n",
        value,
        flags=re.IGNORECASE | re.DOTALL,
    )
    value = re.sub(r"<(?:style|script)[^>]*>.*?</(?:style|script)>", "", value,
                   flags=re.IGNORECASE | re.DOTALL)
    value = unescape(re.sub(r"<[^>]+>", " ", value))
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in value.splitlines()]
    return "\n".join(line for line in lines if line)


def parse_complete_submission(raw: str) -> list[dict]:
    """Split an EDGAR complete-submission SGML file into normalized documents."""
    documents = []
    for index, match in enumerate(_DOCUMENT_RE.finditer(raw or ""), start=1):
        block = match.group(1)
        fields = {k.lower(): v.strip() for k, v in _FIELD_RE.findall(block)}
        text_match = re.search(r"<TEXT>(.*?)</TEXT>", block, re.IGNORECASE | re.DOTALL)
        content = text_match.group(1) if text_match else block
        normalized = html_to_markdown(content)
        documents.append({
            "sequence": fields.get("sequence") or str(index),
            "document_type": fields.get("type", ""),
            "filename": fields.get("filename", ""),
            "description": fields.get("description", ""),
            "text": normalized,
            "sha256": hashlib.sha256(normalized.encode()).hexdigest(),
        })
    if not documents and raw:
        normalized = html_to_markdown(raw)
        documents.append({
            "sequence": "1",
            "document_type": "",
            "filename": "",
            "description": "Complete submission",
            "text": normalized,
            "sha256": hashlib.sha256(normalized.encode()).hexdigest(),
        })
    return documents


def relevant_transaction_documents(documents: list[dict]) -> list[dict]:
    """Keep the primary 8-K and transaction/press-release exhibits."""
    relevant = []
    for document in documents:
        kind = document.get("document_type", "").upper()
        if kind in {"8-K", "8-K/A"} or re.match(r"EX-(2|10|99)(\.|$)", kind):
            relevant.append(document)
    return relevant or documents[:1]


def extract_item_sections(text: str) -> dict[str, str]:
    """Extract the transaction-relevant 8-K item sections with their evidence."""
    matches = list(_ITEM_RE.finditer(text or ""))
    sections = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        key = match.group(1)
        value = text[match.start():end].strip()
        if value:
            sections.setdefault(key, value[:30_000])
    return sections


def build_filing_document(raw: str, *, source_url: str = "") -> dict:
    """Build the canonical document-intelligence representation."""
    documents = parse_complete_submission(raw)
    relevant = relevant_transaction_documents(documents)
    combined = "\n\n".join(
        f"## {doc['document_type'] or 'Filing'} — "
        f"{doc['description'] or doc['filename']}\n{doc['text']}"
        for doc in relevant
    )
    return {
        "source_url": source_url,
        "documents": relevant,
        "sections": extract_item_sections(combined),
        "combined_text": combined,
        "sha256": hashlib.sha256(combined.encode()).hexdigest(),
    }


def parse_authorized_document(content: bytes, filename: str) -> dict:
    """Normalize a manually obtained HTML, text, or PDF filing document."""
    suffix = Path(filename or "").suffix.lower()
    if suffix in {".htm", ".html", ".txt", ".xml"}:
        text = html_to_markdown(content.decode("utf-8", errors="replace"))
    elif suffix == ".pdf":
        from utils.document_parser import document_parser

        with tempfile.NamedTemporaryFile(suffix=".pdf") as handle:
            handle.write(content)
            handle.flush()
            parsed = document_parser.parse_pdf(handle.name)
        text = document_parser.extract_all_text(parsed)
    else:
        raise ValueError("Document must be HTML, XML, text, or PDF.")
    return {
        "filename": filename,
        "text": text,
        "sections": extract_item_sections(text),
        "sha256": hashlib.sha256(content).hexdigest(),
    }
