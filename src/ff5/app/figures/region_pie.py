"""Regional distribution pie chart."""

from __future__ import annotations

import plotly.graph_objects as go

from ff5.app.theme import COLOR_TEXT, COLOR_TEXT_MUTED, FIGURE_LAYOUT, FONT_FAMILY, PORTFOLIO_COLORS


def create_region_pie(
    regions: list[str],
    weights: list[float],
) -> go.Figure:
    """Create a pie chart of portfolio regional distribution.

    Parameters
    ----------
    regions : region label per asset
    weights : portfolio weight per asset (decimal, sums to 1)
    """
    # Aggregate weights by region
    region_weights: dict[str, float] = {}
    for region, w in zip(regions, weights):
        region_weights[region] = region_weights.get(region, 0) + w

    labels = list(region_weights.keys())
    values = [region_weights[r] * 100 for r in labels]

    fig = go.Figure(
        go.Pie(
            labels=labels,
            values=values,
            hole=0.45,
            marker=dict(colors=PORTFOLIO_COLORS[: len(labels)]),
            textinfo="label+percent",
            textfont=dict(size=12, family=FONT_FAMILY, color=COLOR_TEXT),
            hovertemplate="%{label}: %{value:.1f}%<extra></extra>",
        )
    )

    fig.update_layout(
        font=dict(family=FONT_FAMILY, color=COLOR_TEXT),
        margin=dict(l=20, r=20, t=40, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=True,
        legend=dict(
            font=dict(size=11, color=COLOR_TEXT_MUTED),
            bgcolor="rgba(0,0,0,0)",
        ),
        title=dict(text="Regional Distribution", font=dict(size=13, color=COLOR_TEXT_MUTED)),
    )

    return fig
