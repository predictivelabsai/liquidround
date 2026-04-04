"""
Pipeline Kanban board components for Target and Buyer pipelines.
"""
import json
from fasthtml.common import *

TARGET_STAGES = ["Lead", "Qualified", "Shortlist", "Negotiation", "Due Diligence", "Closed"]
BUYER_STAGES = ["Identified", "Approached", "Engaged", "Term Sheet", "Due Diligence", "Closed"]

STAGE_COLORS = {
    "Lead": "blue", "Qualified": "indigo", "Shortlist": "purple",
    "Negotiation": "yellow", "Due Diligence": "orange", "Closed": "green",
    "Identified": "blue", "Approached": "indigo", "Engaged": "purple",
    "Term Sheet": "yellow",
}


def PipelineBoard(items, pipeline_type, title="Pipeline"):
    """Full kanban board with stage columns."""
    stages = TARGET_STAGES if pipeline_type == "target" else BUYER_STAGES
    grouped = {s: [] for s in stages}
    for item in items:
        stage = item.get("stage", stages[0])
        if stage in grouped:
            grouped[stage].append(item)

    return Div(
        Div(
            H2(title, cls="text-xl font-bold text-gray-800"),
            P(f"{len(items)} items", cls="text-sm text-gray-500"),
            cls="mb-4",
        ),
        Div(
            *[PipelineColumn(stage, grouped[stage], pipeline_type, stages) for stage in stages],
            cls="flex gap-3 overflow-x-auto pb-4",
            id="pipeline-board",
        ),
        cls="p-6",
    )


def PipelineColumn(stage, items, pipeline_type, all_stages):
    """Single kanban column."""
    color = STAGE_COLORS.get(stage, "gray")
    return Div(
        Div(
            Span(stage, cls=f"text-xs font-bold text-{color}-700 uppercase tracking-wide"),
            Span(str(len(items)), cls=f"text-xs bg-{color}-100 text-{color}-700 px-1.5 py-0.5 rounded-full ml-2"),
            cls="flex items-center justify-between mb-3",
        ),
        Div(
            *[PipelineCard(item, pipeline_type, all_stages) for item in items],
            P("No items", cls="text-xs text-gray-400 italic py-4 text-center") if not items else "",
            cls="space-y-2 min-h-[100px]",
            id=f"stage-{stage.lower().replace(' ', '-')}",
        ),
        cls=f"flex-shrink-0 w-52 bg-gray-50 rounded-lg p-3 border border-gray-200",
    )


def PipelineCard(item, pipeline_type, all_stages):
    """Single pipeline card with move buttons."""
    score = item.get("score")
    company = item.get("company_name", "Unknown")
    stage = item.get("stage", all_stages[0])
    item_id = item.get("id", "")
    metadata = item.get("metadata", {})
    stage_idx = all_stages.index(stage) if stage in all_stages else 0

    score_badge = ""
    if score is not None:
        sc = "green" if score >= 70 else "yellow" if score >= 50 else "red"
        score_badge = Span(f"{score}", cls=f"text-xs font-bold bg-{sc}-100 text-{sc}-700 px-1.5 py-0.5 rounded")

    # Move buttons
    move_btns = []
    if stage_idx > 0:
        prev_stage = all_stages[stage_idx - 1]
        move_btns.append(
            Button("<<",
                   hx_post="/pipeline/move",
                   hx_vals=json.dumps({"item_id": item_id, "new_stage": prev_stage, "pipeline_type": pipeline_type}),
                   hx_target="#pipeline-board",
                   hx_swap="outerHTML",
                   cls="text-xs text-gray-400 hover:text-blue-600 px-1")
        )
    if stage_idx < len(all_stages) - 1:
        next_stage = all_stages[stage_idx + 1]
        move_btns.append(
            Button(">>",
                   hx_post="/pipeline/move",
                   hx_vals=json.dumps({"item_id": item_id, "new_stage": next_stage, "pipeline_type": pipeline_type}),
                   hx_target="#pipeline-board",
                   hx_swap="outerHTML",
                   cls="text-xs text-gray-400 hover:text-blue-600 px-1")
        )

    # Delete button
    move_btns.append(
        Button("x",
               hx_delete=f"/pipeline/item/{item_id}",
               hx_vals=json.dumps({"pipeline_type": pipeline_type}),
               hx_target="#pipeline-board",
               hx_swap="outerHTML",
               hx_confirm=f"Remove {company} from pipeline?",
               cls="text-xs text-gray-300 hover:text-red-500 px-1 ml-auto")
    )

    industry = metadata.get("industry", "")
    ticker = metadata.get("ticker", "")

    return Div(
        Div(
            Span(company, cls="text-sm font-medium text-gray-800 truncate block"),
            Div(
                Span(ticker, cls="text-xs text-gray-400") if ticker else "",
                score_badge,
                cls="flex items-center gap-2 mt-0.5",
            ),
            P(industry, cls="text-xs text-gray-500 truncate") if industry else "",
        ),
        Div(*move_btns, cls="flex items-center gap-0.5 mt-2 pt-2 border-t border-gray-100"),
        cls="bg-white rounded-lg p-2.5 border border-gray-200 shadow-sm hover:shadow transition-shadow",
        id=f"card-{item_id}",
    )


def AddToPipelineButton(company_name, pipeline_type, score=None, workflow_id=None, metadata=None):
    """Button to add a company to a pipeline from chat results."""
    label = "Add to Target Pipeline" if pipeline_type == "target" else "Add to Buyer Pipeline"
    color = "blue" if pipeline_type == "target" else "green"
    stage = TARGET_STAGES[0] if pipeline_type == "target" else BUYER_STAGES[0]
    vals = {
        "company_name": company_name,
        "pipeline_type": pipeline_type,
        "stage": stage,
    }
    if score is not None:
        vals["score"] = score
    if workflow_id:
        vals["workflow_id"] = workflow_id
    if metadata:
        vals["metadata"] = json.dumps(metadata)
    return Button(
        label,
        hx_post="/pipeline/add",
        hx_vals=json.dumps(vals),
        hx_target="#chat-area",
        hx_swap="beforeend",
        cls=f"bg-{color}-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-{color}-700 mt-2",
    )
