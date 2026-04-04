"""
Plotly chart wrappers for FastHTML.
"""
import json
from fasthtml.common import *


def PlotlyDiv(chart_id: str, data: list, layout: dict):
    """Render a Plotly chart as a FastHTML component."""
    return Div(
        Div(id=chart_id, cls="w-full"),
        Script(f"Plotly.newPlot('{chart_id}', {json.dumps(data)}, {json.dumps(layout)}, {{responsive: true}});"),
    )


def RadarChart(chart_id: str, dimensions: dict, title: str = "Synergy Score Breakdown"):
    """Radar/spider chart for scoring dimensions."""
    labels = [k.replace("_", " ").title() for k in dimensions.keys()]
    values = []
    for v in dimensions.values():
        if isinstance(v, dict):
            values.append(v.get("score", 0))
        else:
            values.append(v)
    # Close the polygon
    labels.append(labels[0])
    values.append(values[0])

    data = [{
        "type": "scatterpolar",
        "r": values,
        "theta": labels,
        "fill": "toself",
        "fillcolor": "rgba(59, 130, 246, 0.2)",
        "line": {"color": "rgb(59, 130, 246)", "width": 2},
        "marker": {"size": 6},
    }]
    layout = {
        "polar": {
            "radialaxis": {"visible": True, "range": [0, 10], "tickfont": {"size": 10}},
            "angularaxis": {"tickfont": {"size": 11}},
        },
        "title": {"text": title, "font": {"size": 14}},
        "showlegend": False,
        "margin": {"l": 60, "r": 60, "t": 50, "b": 30},
        "height": 350,
    }
    return PlotlyDiv(chart_id, data, layout)


def DealsByTypeChart(chart_id: str, by_type: dict):
    """Horizontal bar chart of deals by workflow type."""
    types = list(by_type.keys()) or ["No data"]
    counts = list(by_type.values()) or [0]
    colors = {"conversation": "#3b82f6", "buyer_ma": "#2563eb", "seller_ma": "#16a34a", "ipo": "#f59e0b", "unknown": "#9ca3af"}
    bar_colors = [colors.get(t, "#6b7280") for t in types]
    labels = [t.replace("_", " ").title() for t in types]
    data = [{"type": "bar", "x": counts, "y": labels, "orientation": "h",
             "marker": {"color": bar_colors}, "text": counts, "textposition": "auto"}]
    layout = {"title": "Workflows by Type", "margin": {"l": 120, "r": 20, "t": 40, "b": 30},
              "height": 250, "xaxis": {"title": "Count"}, "yaxis": {"automargin": True}}
    return PlotlyDiv(chart_id, data, layout)


def DealTimelineChart(chart_id: str, timeline: list):
    """Line chart of deal creation over time."""
    months = [t[0] for t in timeline] or ["No data"]
    counts = [t[1] for t in timeline] or [0]
    data = [{"type": "scatter", "x": months, "y": counts, "mode": "lines+markers",
             "line": {"color": "#3b82f6", "width": 2}, "marker": {"size": 8},
             "fill": "tozeroy", "fillcolor": "rgba(59,130,246,0.1)"}]
    layout = {"title": "Activity Timeline", "margin": {"l": 40, "r": 20, "t": 40, "b": 40},
              "height": 250, "xaxis": {"title": ""}, "yaxis": {"title": "Workflows"}}
    return PlotlyDiv(chart_id, data, layout)


def DealStatusPie(chart_id: str, by_status: dict):
    """Pie chart of deal statuses."""
    labels = [s.replace("_", " ").title() for s in by_status.keys()] or ["No data"]
    values = list(by_status.values()) or [0]
    colors = {"Pending": "#f59e0b", "Active": "#3b82f6", "Completed": "#16a34a", "Failed": "#ef4444", "Routing": "#8b5cf6", "Executing": "#6366f1"}
    marker_colors = [colors.get(l, "#9ca3af") for l in labels]
    data = [{"type": "pie", "labels": labels, "values": values, "hole": 0.4,
             "marker": {"colors": marker_colors}, "textinfo": "label+value"}]
    layout = {"title": "Status Breakdown", "margin": {"l": 20, "r": 20, "t": 40, "b": 20},
              "height": 250, "showlegend": False}
    return PlotlyDiv(chart_id, data, layout)


def SectorHeatmap(chart_id: str, sectors: list, years: list, values: list):
    """Sector performance heatmap."""
    data = [{
        "type": "heatmap",
        "z": values,
        "x": years,
        "y": sectors,
        "colorscale": "RdYlGn",
        "showscale": True,
    }]
    layout = {
        "title": "Sector Performance (%)",
        "margin": {"l": 150, "r": 30, "t": 50, "b": 50},
        "height": 400,
    }
    return PlotlyDiv(chart_id, data, layout)
