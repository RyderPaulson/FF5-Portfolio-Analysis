"""KDE comparison of simulated terminal wealth at each milestone."""

from __future__ import annotations

import numpy as np
import plotly.graph_objects as go
from scipy.stats import gaussian_kde

from ff5.app.theme import FIGURE_LAYOUT, get_color
from ff5.models import AnalysisResults, Milestone


def create_return_distribution_single(
    portfolios_results: list[tuple[str, AnalysisResults]],
    milestone_index: int = 0,
    milestones: list[Milestone] | None = None,
) -> go.Figure:
    """Create KDE return distribution for a single milestone."""
    if milestones is None:
        milestones = [Milestone("House", 10), Milestone("Retire", 44)]

    if milestone_index >= len(milestones):
        return go.Figure()

    m = milestones[milestone_index]
    use_log = m.year >= 30
    fig = go.Figure()

    for pi, (title, results) in enumerate(portfolios_results):
        if milestone_index >= len(results.milestone_vals):
            continue
        vals = results.milestone_vals[milestone_index]
        if vals is None or len(vals) == 0:
            continue

        if use_log:
            vals = vals[vals > 0]
            if len(vals) == 0:
                continue
            vals = np.log10(vals)

        try:
            kde = gaussian_kde(vals)
            x_grid = np.linspace(
                np.percentile(vals, 0.5),
                np.percentile(vals, 99.5),
                500,
            )
            y_vals = kde(x_grid)

            fig.add_trace(
                go.Scatter(
                    x=x_grid,
                    y=y_vals,
                    mode="lines",
                    name=title or f"Portfolio {pi + 1}",
                    line=dict(color=get_color(pi), width=2),
                )
            )
        except np.linalg.LinAlgError:
            continue

    be_val = 0.0 if use_log else 1.0
    fig.add_vline(x=be_val, line_dash="dash", line_color="black", line_width=1)

    x_label = (
        "Portfolio Value \u2014 log\u2081\u2080(x Initial)"
        if use_log
        else "Portfolio Value \u2014 Multiple of Initial"
    )

    fig.update_layout(
        **FIGURE_LAYOUT,
        title=f"{m.name} ({m.year}-Year) Distribution",
        xaxis_title=x_label,
        yaxis_title="Density",
    )

    return fig


def create_return_distributions(
    portfolios_results: list[tuple[str, AnalysisResults]],
    milestones: list[Milestone] | None = None,
) -> go.Figure:
    """Create KDE return distribution for first milestone (backward compat)."""
    return create_return_distribution_single(portfolios_results, 0, milestones)
