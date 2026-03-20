"""
File upload routes for XLS, PPT, PDF.
"""
import os
from pathlib import Path
from fasthtml.common import *
from starlette.datastructures import UploadFile
from components.layout import Shell
from components.upload_form import UploadZone, UploadResult

ar = APIRouter()

UPLOAD_DIR = Path(__file__).parent.parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)
MAX_SIZE = 50 * 1024 * 1024  # 50MB


@ar("/upload")
def get():
    """Upload page (GET)."""
    return Shell(UploadZone())


@ar("/upload")
async def post(file: UploadFile):
    """Handle file upload (POST)."""
    if not file or not file.filename:
        return P("No file selected.", cls="text-red-500 text-sm")

    ext = Path(file.filename).suffix.lower()
    allowed = {".xlsx", ".xls", ".pptx", ".ppt", ".pdf"}
    if ext not in allowed:
        return P(f"Unsupported file type: {ext}. Allowed: {', '.join(allowed)}", cls="text-red-500 text-sm")

    # Read and save
    content = await file.read()
    if len(content) > MAX_SIZE:
        return P("File too large (max 50MB).", cls="text-red-500 text-sm")

    save_path = UPLOAD_DIR / file.filename
    save_path.write_bytes(content)

    # Parse
    from utils.document_parser import document_parser
    parsed = document_parser.parse(str(save_path))

    return UploadResult(parsed)
