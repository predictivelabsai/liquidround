"""LangChain StructuredTools used by the 32 specialist agents.

Each tool wraps an existing utility (utils/yfinance_util, utils/research_tools,
utils/document_parser, utils/ipo_utils) and where relevant emits a structured
artifact (`"__ARTIFACT__" + json.dumps(...)`) that the SSE stream picks up
and renders into the right-pane canvas.
"""
