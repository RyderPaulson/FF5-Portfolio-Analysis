"""Grouped bar chart of FF5 factor beta loadings."""

from __future__ import annotations

import plotly.graph_objects as go

from ff5.app.theme import FIGURE_LAYOUT
from ff5.models import AnalysisResults

FACTOR_NAMES = ["Mkt", "SMB", "HML", "RMW", "CMA"]
FACTOR_COLORS = ["#0077B6", "#E8A317", "#D4442E", "#009E5E", "#7B2D8E"]


def create_factor_exposures(
    portfolios_results: list[tuple[str, AnalysisResults]],
) -> go.Figure:
    """Create grouped bar chart of portfolio factor exposures."""
    fig = go.Figure()

    labels = [title or f"Portfolio {i + 1}" for i, (title, _) in enumerate(portfolios_results)]

    for fi, (fname, fcolor) in enumerate(zip(FACTOR_NAMES, FACTOR_COLORS)):
        values = [r.port_factor_betas[fi] for _, r in portfolios_results]
        fig.add_trace(
            go.Bar(
                name=fname,
                x=labels,
                y=values,
                marker_color=fcolor,
            )
        )

    fig.update_layout(
        **FIGURE_LAYOUT,
        title="Portfolio Factor Exposures (FF5)",
        yaxis_title="Factor Beta Loading",
        barmode="group",
    )

    return fig
