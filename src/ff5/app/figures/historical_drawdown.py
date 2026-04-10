"""Overlaid historical drawdown series with portfolio highlighting."""

from __future__ import annotations

import plotly.graph_objects as go

from ff5.app.theme import FIGURE_LAYOUT, get_color
from ff5.models import AnalysisResults


def _hex_to_rgb(hex_color: str) -> str:
    h = hex_color.lstrip("#")
    return f"{int(h[0:2], 16)},{int(h[2:4], 16)},{int(h[4:6], 16)}"


def create_historical_drawdown(
    portfolios_results: list[tuple[str, AnalysisResults]],
    selected_title: str | None = None,
) -> go.Figure:
    """Create overlaid historical drawdown chart with one portfolio highlighted."""
    fig = go.Figure()

    if selected_title is None and portfolios_results:
        selected_title = portfolios_results[0][0]

    # Non-selected in grey first
    for i, (title, results) in enumerate(portfolios_results):
        if title == selected_title:
            continue
        fig.add_trace(
            go.Scatter(
                x=results.hist_dates,
                y=results.hist_drawdown * 100,
                mode="lines",
                name=title or f"Portfolio {i + 1}",
                line=dict(color="rgba(180,180,180,0.4)", width=0.7),
                legendgroup=title,
            )
        )

    # Selected portfolio on top
    for i, (title, results) in enumerate(portfolios_results):
        if title != selected_title:
            continue
        color = get_color(i)
        fig.add_trace(
            go.Scatter(
                x=results.hist_dates,
                y=results.hist_drawdown * 100,
                mode="lines",
                name=title or f"Portfolio {i + 1}",
                line=dict(color=color, width=1.5),
                fill="tozeroy",
                fillcolor=f"rgba({_hex_to_rgb(color)},0.15)",
                legendgroup=title,
            )
        )

    fig.update_layout(
        **FIGURE_LAYOUT,
        title=f"Historical Drawdown \u2014 {selected_title}" if selected_title else "Historical Drawdown",
        xaxis_title="Date",
        yaxis_title="Drawdown (%)",
        yaxis_autorange="reversed",
    )

    return fig
