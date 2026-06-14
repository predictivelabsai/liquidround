"""AI market commentary for the IPO Map — LLM analysis with a statistical fallback."""
from __future__ import annotations

import logging

import pandas as pd

from .ipo_utils import format_percentage

logger = logging.getLogger(__name__)


def _stats_summary(df: pd.DataFrame) -> str:
    """Compact stats block fed to the LLM (and reused as the fallback body)."""
    lines = [f"Total IPOs: {len(df)}",
             f"Average performance since IPO: {format_percentage(df['price_change_since_ipo'].mean())}"]
    if "region" in df.columns:
        for region, grp in df.groupby("region"):
            lines.append(f"- {region}: {len(grp)} IPOs, avg {format_percentage(grp['price_change_since_ipo'].mean())}")
    top_sectors = df.groupby("sector")["price_change_since_ipo"].mean().sort_values(ascending=False).head(5)
    for sector, val in top_sectors.items():
        lines.append(f"- Sector {sector}: avg {format_percentage(val)}")
    return "\n".join(lines)


def _fallback(df: pd.DataFrame, timeframe: str) -> str:
    regions = "\n".join(
        f"- **{r}:** {format_percentage(df[df['region'] == r]['price_change_since_ipo'].mean())} avg return"
        for r in df["region"].unique()
    ) if "region" in df.columns else ""
    sectors = "\n".join(
        f"- **{s}:** {format_percentage(df[df['sector'] == s]['price_change_since_ipo'].mean())} avg"
        for s in df["sector"].value_counts().head(5).index
    )
    return (
        f"### IPO Market Analysis — {timeframe}\n\n"
        f"**Overview:** {len(df)} IPOs with an average performance of "
        f"{format_percentage(df['price_change_since_ipo'].mean())} since listing.\n\n"
        f"**Regional performance:**\n{regions}\n\n"
        f"**Sector analysis:**\n{sectors}\n\n"
        f"*AI-generated commentary unavailable — showing statistical summary.*"
    )


def get_ipo_commentary(df: pd.DataFrame, timeframe: str = "Last 3 years") -> str:
    """Return markdown commentary on the filtered IPO set."""
    if df is None or df.empty:
        return "No IPO data available for the current filters."
    try:
        from .llm_factory import create_llm
        prompt = (
            "You are an equity capital markets analyst. Write a concise, insightful "
            "markdown commentary (3-4 short paragraphs) on the IPO market based on the "
            f"statistics below for {timeframe}. Cover overall sentiment, standout regions "
            "and sectors, and what it implies for issuers and investors. Do not invent "
            "specific tickers not implied by the data.\n\n"
            f"Statistics:\n{_stats_summary(df)}"
        )
        text = create_llm().invoke(prompt).content
        return text or _fallback(df, timeframe)
    except Exception as e:  # noqa: BLE001
        logger.warning("IPO commentary LLM failed: %s", e)
        return _fallback(df, timeframe)
