"""
File upload routes for XLS, PPT, PDF.
"""
from pathlib import Path
from fasthtml.common import *
from starlette.datastructures import UploadFile
from components.layout import Shell
from components.upload_form import UploadZone, UploadResult

ar = APIRouter()

UPLOAD_DIR = Path(__file__).parent.parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)
@ar("/upload")
def get(session):
    """Upload page (GET)."""
    return Shell(UploadZone())


@ar("/upload")
async def post(file: UploadFile, session):
    """Handle file upload (POST)."""
    if not file or not file.filename:
        return P("No file selected.", cls="text-red-500 text-sm")

    user = session.get("user")
    if not user:
        return P("Sign in required.", cls="text-red-500 text-sm")
    from utils.security import safe_upload_target, UPLOAD_MAX_BYTES
    content = await file.read()
    if len(content) > UPLOAD_MAX_BYTES:
        return P("File too large.", cls="text-red-500 text-sm")
    try:
        save_path, _document_id = safe_upload_target(UPLOAD_DIR, user["user_id"], file.filename)
    except ValueError as exc:
        return P(str(exc), cls="text-red-500 text-sm")
    save_path.write_bytes(content)

    # Parse
    from utils.document_parser import document_parser
    parsed = document_parser.parse(str(save_path))

    return UploadResult(parsed)
