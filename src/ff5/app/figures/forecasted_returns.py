"""Forecasted returns fan chart."""

from __future__ import annotations

import numpy as np
import plotly.graph_objects as go

from ff5.app.theme import COLOR_SECONDARY, FIGURE_LAYOUT, get_color
from ff5.models import AnalysisResults, Milestone

TRADING_DAYS_PER_YEAR = 252


def create_forecasted_returns(
    portfolios_results: list[tuple[str, AnalysisResults]],
    milestones: list[Milestone] | None = None,
    overlay: bool = True,
) -> go.Figure:
    """Create forecasted returns fan chart.

    Parameters
    ----------
    portfolios_results : list of (title, AnalysisResults) tuples
    milestones : milestone markers
    overlay : if True, overlay median lines for multiple portfolios;
              if False, show full fan chart for first portfolio only
    """
    if milestones is None:
        milestones = [Milestone("House", 10), Milestone("Retire", 44)]

    fig = go.Figure()

    if len(portfolios_results) == 1 or not overlay:
        # Full fan chart for single portfolio
        title, results = portfolios_results[0]
        fc = results.forecasted_returns
        color = get_color(0)

        # 5th-95th band
        fig.add_trace(
            go.Scatter(
                x=np.concatenate([fc.t_years, fc.t_years[::-1]]),
                y=np.concatenate([fc.pct5, fc.pct95[::-1]]),
                fill="toself",
                fillcolor=f"rgba({_hex_to_rgb(color)},0.1)",
                line=dict(width=0),
                name="5th–95th",
                showlegend=True,
            )
        )

        # 25th-75th band
        fig.add_trace(
            go.Scatter(
                x=np.concatenate([fc.t_years, fc.t_years[::-1]]),
                y=np.concatenate([fc.pct25, fc.pct75[::-1]]),
                fill="toself",
                fillcolor=f"rgba({_hex_to_rgb(color)},0.2)",
                line=dict(width=0),
                name="25th–75th",
                showlegend=True,
            )
        )

        # Median
        fig.add_trace(
            go.Scatter(
                x=fc.t_years,
                y=fc.pct50,
                mode="lines",
                name="Median",
                line=dict(color=color, width=2.5),
            )
        )

        chart_title = f"Forecasted Returns — {title}" if title else "Forecasted Returns"
    else:
        # Multiple portfolios: median lines only
        for i, (title, results) in enumerate(portfolios_results):
            fc = results.forecasted_returns
            fig.add_trace(
                go.Scatter(
                    x=fc.t_years,
                    y=fc.pct50,
                    mode="lines",
                    name=title or f"Portfolio {i + 1}",
                    line=dict(color=get_color(i), width=2),
                )
            )
        chart_title = "Forecasted Returns — Median Comparison"

    # Breakeven line
    fig.add_hline(y=1, line_dash="dash", line_color="black", line_width=0.5)

    # Milestone markers
    for m in milestones:
        fig.add_vline(
            x=m.year,
            line_dash="dash",
            line_color=COLOR_SECONDARY,
            line_width=1.5,
            annotation_text=m.name,
            annotation_position="top left",
        )

    fig.update_layout(
        **FIGURE_LAYOUT,
        title=chart_title,
        xaxis_title="Years",
        yaxis_title="Portfolio Value (multiple of initial)",
        yaxis_type="log",
    )

    return fig


def _hex_to_rgb(hex_color: str) -> str:
    """Convert '#RRGGBB' to 'R,G,B'."""
    h = hex_color.lstrip("#")
    return f"{int(h[0:2], 16)},{int(h[2:4], 16)},{int(h[4:6], 16)}"
