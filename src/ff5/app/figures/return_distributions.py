"""KDE comparison of simulated terminal wealth at each milestone."""

from __future__ import annotations

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy.stats import gaussian_kde

from ff5.app.theme import FIGURE_LAYOUT, get_color
from ff5.models import AnalysisResults, Milestone


def create_return_distributions(
    portfolios_results: list[tuple[str, AnalysisResults]],
    milestones: list[Milestone] | None = None,
) -> go.Figure:
    """Create KDE return distribution comparison at each milestone."""
    if milestones is None:
        milestones = [Milestone("House", 10), Milestone("Retire", 44)]

    n_mile = len(milestones)
    fig = make_subplots(rows=n_mile, cols=1, subplot_titles=[
        f"{m.name} ({m.year}-Year Horizon)" for m in milestones
    ])

    for mi, m in enumerate(milestones):
        use_log = m.year >= 30

        for pi, (title, results) in enumerate(portfolios_results):
            if mi >= len(results.milestone_vals):
                continue
            vals = results.milestone_vals[mi]
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
                        showlegend=(mi == 0),
                    ),
                    row=mi + 1,
                    col=1,
                )
            except np.linalg.LinAlgError:
                continue

        # Breakeven line
        be_val = 0.0 if use_log else 1.0
        fig.add_vline(
            x=be_val,
            line_dash="dash",
            line_color="black",
            line_width=1,
            row=mi + 1,
            col=1,
        )

        x_label = (
            f"Portfolio Value — log10(x Initial)"
            if use_log
            else "Portfolio Value — Multiple of Initial"
        )
        fig.update_xaxes(title_text=x_label, row=mi + 1, col=1)
        fig.update_yaxes(title_text="Probability Density", row=mi + 1, col=1)

    fig.update_layout(
        **FIGURE_LAYOUT,
        title="Return Distribution Comparison",
        height=400 * n_mile,
    )

    return fig
