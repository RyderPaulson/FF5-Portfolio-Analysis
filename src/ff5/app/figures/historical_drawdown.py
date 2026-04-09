"""Overlaid historical drawdown series."""

from __future__ import annotations

import plotly.graph_objects as go

from ff5.app.theme import FIGURE_LAYOUT, get_color
from ff5.models import AnalysisResults


def create_historical_drawdown(
    portfolios_results: list[tuple[str, AnalysisResults]],
) -> go.Figure:
    """Create overlaid historical drawdown chart."""
    fig = go.Figure()

    for i, (title, results) in enumerate(portfolios_results):
        fig.add_trace(
            go.Scatter(
                x=results.hist_dates,
                y=results.hist_drawdown * 100,
                mode="lines",
                name=title or f"Portfolio {i + 1}",
                line=dict(color=get_color(i), width=0.7),
            )
        )

    fig.update_layout(
        **FIGURE_LAYOUT,
        title="Historical Drawdown Comparison",
        xaxis_title="Date",
        yaxis_title="Drawdown (%)",
        yaxis_autorange="reversed",
    )

    return fig
