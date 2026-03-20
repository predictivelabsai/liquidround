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
