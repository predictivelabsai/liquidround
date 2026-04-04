"""
Pipeline routes — Target and Buyer kanban boards.
"""
import json
from fasthtml.common import *
from starlette.responses import RedirectResponse

ar = APIRouter()

TARGET_STAGES = ["Lead", "Qualified", "Shortlist", "Negotiation", "Due Diligence", "Closed"]
BUYER_STAGES = ["Identified", "Approached", "Engaged", "Term Sheet", "Due Diligence", "Closed"]


def _auth_guard(session):
    """Return user dict or None."""
    return session.get("user")


@ar("/pipeline/target")
def target_pipeline(session):
    user = _auth_guard(session)
    if not user:
        return RedirectResponse("/signin")
    from utils.database import db_service
    from components.pipeline import PipelineBoard
    items = db_service.get_pipeline_items(user["user_id"], "target")
    return PipelineBoard(items, "target", title="Target Pipeline")


@ar("/pipeline/buyer")
def buyer_pipeline(session):
    user = _auth_guard(session)
    if not user:
        return RedirectResponse("/signin")
    from utils.database import db_service
    from components.pipeline import PipelineBoard
    items = db_service.get_pipeline_items(user["user_id"], "buyer")
    return PipelineBoard(items, "buyer", title="Buyer Pipeline")


@ar("/pipeline/add")
async def pipeline_add(session, company_name: str = "", pipeline_type: str = "target",
                       stage: str = "", score: int = None, workflow_id: str = None,
                       metadata: str = "{}"):
    user = _auth_guard(session)
    if not user:
        return P("Please sign in to use pipelines.", cls="text-sm text-red-500")
    if not company_name:
        return P("Company name required.", cls="text-sm text-red-500")

    from utils.database import db_service
    if not stage:
        stage = TARGET_STAGES[0] if pipeline_type == "target" else BUYER_STAGES[0]
    try:
        meta = json.loads(metadata) if isinstance(metadata, str) else metadata
    except Exception:
        meta = {}

    conv_id = session.get("conversation_id")
    item_id = db_service.add_pipeline_item(
        user_id=user["user_id"],
        pipeline_type=pipeline_type,
        company_name=company_name,
        stage=stage,
        score=score,
        workflow_id=workflow_id or conv_id,
        metadata=meta,
    )
    pipeline_label = "Target" if pipeline_type == "target" else "Buyer"
    return Div(
        Div(
            P(f"Added {company_name} to {pipeline_label} Pipeline ({stage})", cls="text-sm text-green-700"),
            A(f"View {pipeline_label} Pipeline",
              hx_get=f"/pipeline/{pipeline_type}",
              hx_target="#main-content",
              hx_push_url="true",
              cls="text-xs text-blue-600 hover:underline mt-1 block"),
            cls="bg-green-50 rounded-lg p-3 border border-green-200",
        ),
        cls="flex justify-start mb-3",
    )


@ar("/pipeline/move")
async def pipeline_move(session, item_id: str = "", new_stage: str = "", pipeline_type: str = "target"):
    user = _auth_guard(session)
    if not user:
        return ""
    from utils.database import db_service
    from components.pipeline import PipelineBoard
    db_service.move_pipeline_item(item_id, user["user_id"], new_stage)
    items = db_service.get_pipeline_items(user["user_id"], pipeline_type)
    title = "Target Pipeline" if pipeline_type == "target" else "Buyer Pipeline"
    return PipelineBoard(items, pipeline_type, title=title)


@ar("/pipeline/item/{item_id}")
async def pipeline_delete(session, item_id: str = "", pipeline_type: str = "target"):
    user = _auth_guard(session)
    if not user:
        return ""
    from utils.database import db_service
    from components.pipeline import PipelineBoard
    db_service.delete_pipeline_item(item_id, user["user_id"])
    items = db_service.get_pipeline_items(user["user_id"], pipeline_type)
    title = "Target Pipeline" if pipeline_type == "target" else "Buyer Pipeline"
    return PipelineBoard(items, pipeline_type, title=title)
