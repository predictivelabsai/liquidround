"""Hedge fund routes — treemap page + JSON data API."""
from __future__ import annotations

import logging

from fasthtml.common import *
from fasthtml.core import APIRouter
from starlette.responses import JSONResponse

from components.hedge_funds import hedge_fund_page_content

log = logging.getLogger(__name__)
ar = APIRouter()


@ar("/app/hedgefunds")
def hedge_funds_page(request):
    return hedge_fund_page_content()


@ar("/app/hedgefunds/data")
def hedge_funds_data(request):
    params = request.query_params
    fund = params.get("fund", "")
    min_value = int(params.get("min_value", 0))
    limit = min(int(params.get("limit", 500)), 2000)
    try:
        from utils.hedge_fund_db import get_treemap_data
        data = get_treemap_data(min_value=min_value, fund_filter=fund, limit=limit)
        return JSONResponse(data)
    except Exception as e:
        log.error("Treemap data error: %s", e)
        return JSONResponse([], status_code=500)
