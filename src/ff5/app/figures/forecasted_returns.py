"""Forecasted returns — sampled Monte Carlo paths per portfolio."""

from __future__ import annotations

import numpy as np
import plotly.graph_objects as go

from ff5.app.theme import COLOR_SECONDARY, FIGURE_LAYOUT, get_color
from ff5.models import AnalysisResults, Milestone

TRADING_DAYS_PER_YEAR = 252

# Subsample paths to every N-th day so the plot isn't overwhelmed with points
_PLOT_STRIDE = 5


def create_forecasted_returns(
    portfolios_results: list[tuple[str, AnalysisResults]],
    milestones: list[Milestone] | None = None,
    selected_title: str | None = None,
) -> go.Figure:
    """Show sampled MC paths for all portfolios in grey, highlighted portfolio in color.

    Parameters
    ----------
    portfolios_results : list of (title, AnalysisResults) tuples
    milestones : milestone markers
    selected_title : which portfolio to highlight (None = first)
    """
    if milestones is None:
        milestones = [Milestone("House", 10), Milestone("Retire", 44)]

    fig = go.Figure()

    if selected_title is None and portfolios_results:
        selected_title = portfolios_results[0][0]

    # Draw all non-selected portfolios first (grey, background)
    for title, results in portfolios_results:
        if title == selected_title:
            continue
        _add_sample_paths(fig, results, title, color="rgba(180,180,180,0.25)", show_legend_once=True)

    # Draw the selected portfolio on top (colored)
    for title, results in portfolios_results:
        if title != selected_title:
            continue
        color_idx = next(
            (i for i, (t, _) in enumerate(portfolios_results) if t == title), 0
        )
        color = get_color(color_idx)
        _add_sample_paths(fig, results, title, color=f"rgba({_hex_to_rgb(color)},0.5)", show_legend_once=True)
        # Add median line
        fc = results.forecasted_returns
        t = fc.t_years[::_PLOT_STRIDE]
        fig.add_trace(
            go.Scatter(
                x=t, y=fc.pct50[::_PLOT_STRIDE],
                mode="lines",
                name=f"{title} (median)",
                line=dict(color=color, width=3),
            )
        )

    # Breakeven line
    fig.add_hline(y=1, line_dash="dash", line_color="black", line_width=0.5)

    # Milestone markers
    for m in milestones:
        fig.add_vline(
            x=m.year, line_dash="dash", line_color=COLOR_SECONDARY, line_width=1.5,
            annotation_text=m.name, annotation_position="top left",
        )

    fig.update_layout(
        **FIGURE_LAYOUT,
        title=f"Forecasted Returns — {selected_title}" if selected_title else "Forecasted Returns",
        xaxis_title="Years",
        yaxis_title="Portfolio Value (multiple of initial)",
        yaxis_type="log",
    )

    return fig


def _add_sample_paths(
    fig: go.Figure,
    results: AnalysisResults,
    title: str,
    color: str,
    show_legend_once: bool = True,
):
    """Add sampled MC paths as individual traces."""
    fc = results.forecasted_returns
    if fc.sample_paths is None:
        return

    t = fc.t_years[::_PLOT_STRIDE]
    n_samples = fc.sample_paths.shape[1]

    for j in range(n_samples):
        fig.add_trace(
            go.Scatter(
                x=t,
                y=fc.sample_paths[::_PLOT_STRIDE, j],
                mode="lines",
                line=dict(color=color, width=1),
                name=title if (j == 0 and show_legend_once) else None,
                showlegend=(j == 0 and show_legend_once),
                legendgroup=title,
                hoverinfo="skip",
            )
        )


def _hex_to_rgb(hex_color: str) -> str:
    """Convert '#RRGGBB' to 'R,G,B'."""
    h = hex_color.lstrip("#")
    return f"{int(h[0:2], 16)},{int(h[2:4], 16)},{int(h[4:6], 16)}"
