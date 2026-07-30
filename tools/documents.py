"""Document-parsing tools — PDF / XLS / PPT key-terms extraction.

Consumed by:
  - contract_abstractor  (diligence)
  - vdr_auditor          (diligence)
  - teaser_designer      (capital) — read source CIMs
  - ic_memo_writer       (capital) — read DD doc excerpts
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from utils.document_parser import DocumentParser
from tools.artifact import emit

PUBLIC_DOC_PATH = (Path(__file__).resolve().parent.parent / "docs-data").resolve()
UPLOAD_ROOT = (Path(__file__).resolve().parent.parent / "uploads").resolve()


def _resolve(filename: str) -> Optional[Path]:
    """Resolve only a public demo document or the current user's opaque upload."""
    from utils.request_context import current_user_id

    basename = Path(filename or "").name
    if not basename or basename != filename:
        return None
    user_id = current_user_id()
    candidates = [PUBLIC_DOC_PATH / basename]
    if user_id:
        candidates.insert(0, UPLOAD_ROOT / user_id / basename)
    for candidate in candidates:
        resolved = candidate.resolve()
        allowed_parent = (UPLOAD_ROOT / user_id).resolve() if user_id and resolved.parent != PUBLIC_DOC_PATH else PUBLIC_DOC_PATH
        if resolved.parent == allowed_parent and resolved.is_file():
            return resolved
    return None


class DocArgs(BaseModel):
    filename: str = Field(description="Opaque uploaded document id or bundled demo filename. Paths are not accepted.")


# ────────────────────────────────────────────────────────────────────────
# read_document — return extracted text + summary
# ────────────────────────────────────────────────────────────────────────

def _read_document(filename: str) -> str:
    path = _resolve(filename)
    if not path:
        return f"Document not found: {filename}. Try uploading first."
    parser = DocumentParser()
    parsed = parser.parse(str(path))
    if "error" in parsed:
        return f"Parse error: {parsed['error']}"

    # Summarize contents depending on file type
    if parsed["type"] == "pptx":
        body = "\n\n".join(
            f"**Slide {s['slide_number']}**\n" + "\n".join(s["texts"]) for s in parsed["slides"][:10]
        )
    elif parsed["type"] == "xlsx":
        lines = []
        for sheet_name in parsed["sheet_names"][:3]:
            lines.append(f"**{sheet_name}**")
            rows = parsed["sheets"].get(sheet_name, [])[:15]
            for r in rows:
                lines.append(" | ".join(r))
        body = "\n".join(lines)
    else:  # pdf
        body = (parsed.get("text") or "")[:6000]

    return emit(
        kind="document",
        title=parsed.get("summary") or path.name,
        subtitle=f"{parsed['type'].upper()} · {path.name}",
        body_md=body,
    )


read_document = StructuredTool.from_function(
    func=_read_document,
    name="read_document",
    description="Read an uploaded document (PDF, XLSX, PPTX) and return its text content as a document artifact.",
    args_schema=DocArgs,
)


# ────────────────────────────────────────────────────────────────────────
# extract_key_terms — structured M&A key terms
# ────────────────────────────────────────────────────────────────────────

def _extract_key_terms(filename: str) -> str:
    """Return the raw document text for the agent to extract from.

    The heavy lifting (structured JSON extraction) happens in the LLM step
    using the contract_abstractor / key_terms prompt — this tool just exposes
    the document text to the model.
    """
    path = _resolve(filename)
    if not path:
        return f"Document not found: {filename}. Try uploading first."
    parser = DocumentParser()
    parsed = parser.parse(str(path))
    if "error" in parsed:
        return f"Parse error: {parsed['error']}"

    if parsed["type"] == "pdf":
        text = parsed.get("text", "")
    elif parsed["type"] == "pptx":
        text = "\n".join(" ".join(s["texts"]) for s in parsed.get("slides", []))
    else:  # xlsx
        rows_text: list[str] = []
        for sheet_name in parsed.get("sheet_names", [])[:3]:
            for row in parsed["sheets"].get(sheet_name, [])[:30]:
                rows_text.append(" | ".join(row))
        text = "\n".join(rows_text)

    return json.dumps({
        "filename": path.name,
        "type": parsed["type"],
        "text": text[:12000],
    }, default=str)


extract_key_terms = StructuredTool.from_function(
    func=_extract_key_terms,
    name="extract_key_terms",
    description="Return the raw text of an uploaded doc so the agent can extract key M&A terms (parties, EV, consideration mix, covenants, closing conditions, etc.) using its system prompt.",
    args_schema=DocArgs,
)


# ────────────────────────────────────────────────────────────────────────
# list_documents — what's available
# ────────────────────────────────────────────────────────────────────────

class NoArgs(BaseModel):
    pass


def _list_documents() -> str:
    from utils.request_context import current_user_id

    rows = []
    folders = [PUBLIC_DOC_PATH]
    user_id = current_user_id()
    if user_id:
        folders.insert(0, UPLOAD_ROOT / user_id)
    for folder in folders:
        if not folder.exists():
            continue
        for f in sorted(folder.iterdir()):
            if f.is_file() and f.suffix.lower() in (".pdf", ".xlsx", ".xls", ".pptx", ".ppt"):
                rows.append({
                    "filename": f.name,
                    "folder": "My uploads" if user_id and folder == UPLOAD_ROOT / user_id else "Demo documents",
                    "size_kb": round(f.stat().st_size / 1024, 1),
                    "type": f.suffix[1:].lower(),
                })
    if not rows:
        return "No documents uploaded yet."
    return emit(
        kind="table",
        title="Available documents",
        subtitle=f"{len(rows)} file(s)",
        columns=["filename", "folder", "type", "size_kb"],
        rows=rows,
    )


list_documents = StructuredTool.from_function(
    func=_list_documents,
    name="list_documents",
    description="List all uploaded / available documents (PDFs, XLSX, PPTX). Emits a table artifact.",
    args_schema=NoArgs,
)
