"""Morningstar-style 3x3 style box (cap size vs value/growth)."""

from __future__ import annotations

import numpy as np
import plotly.graph_objects as go

from ff5.app.theme import COLOR_BORDER, COLOR_PRIMARY, COLOR_TEXT, COLOR_TEXT_MUTED, FONT_FAMILY


def create_style_box(
    smb_beta: float,
    hml_beta: float,
    title: str = "",
) -> go.Figure:
    """Create a Morningstar-style 3x3 box with a portfolio marker.

    Position is derived from weighted-average FF5 betas:
    - x-axis: HML beta → Value (left) to Growth (right)
    - y-axis: SMB beta → Large (top) to Small (bottom)
    """
    fig = go.Figure()

    # Map betas to 0-3 grid coordinates
    # HML: positive = value (left), negative = growth (right)
    # Clamp to [-1, 1] range then map to [0, 3]
    hml_clamped = max(-1.0, min(1.0, hml_beta))
    x_pos = 1.5 - hml_clamped * 1.5  # value=0, blend=1.5, growth=3

    # SMB: positive = small (bottom rows), negative = large (top rows)
    smb_clamped = max(-1.0, min(1.0, smb_beta))
    y_pos = 1.5 - smb_clamped * 1.5  # large=0 (top), mid=1.5, small=3

    # Determine which cell the marker falls in
    cell_x = min(int(x_pos), 2)
    cell_y = min(int(y_pos), 2)

    # Draw 3x3 grid cells
    col_labels = ["Value", "Blend", "Growth"]
    row_labels = ["Large", "Mid", "Small"]

    for row in range(3):
        for col in range(3):
            is_active = (col == cell_x and row == cell_y)
            fill_color = f"rgba({_hex_to_rgb(COLOR_PRIMARY)},0.15)" if is_active else "rgba(0,0,0,0.02)"

            fig.add_shape(
                type="rect",
                x0=col, y0=row, x1=col + 1, y1=row + 1,
                line=dict(color=COLOR_BORDER, width=1),
                fillcolor=fill_color,
                layer="below",
            )

    # Portfolio marker
    fig.add_trace(
        go.Scatter(
            x=[x_pos],
            y=[y_pos],
            mode="markers",
            marker=dict(size=14, color=COLOR_PRIMARY, symbol="circle",
                        line=dict(width=2, color="white")),
            name=title or "Portfolio",
            hovertemplate=f"HML: {hml_beta:.2f}<br>SMB: {smb_beta:.2f}<extra></extra>",
        )
    )

    # Axis labels
    fig.update_xaxes(
        tickvals=[0.5, 1.5, 2.5],
        ticktext=col_labels,
        range=[0, 3],
        showgrid=False,
        zeroline=False,
        side="bottom",
        tickfont=dict(size=11, color=COLOR_TEXT_MUTED),
    )
    fig.update_yaxes(
        tickvals=[0.5, 1.5, 2.5],
        ticktext=row_labels,
        range=[0, 3],
        showgrid=False,
        zeroline=False,
        autorange="reversed",
        tickfont=dict(size=11, color=COLOR_TEXT_MUTED),
    )

    fig.update_layout(
        font=dict(family=FONT_FAMILY, color=COLOR_TEXT),
        margin=dict(l=50, r=20, t=30, b=40),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        title=dict(text="Style Box", font=dict(size=13, color=COLOR_TEXT_MUTED)),
    )

    return fig


def _hex_to_rgb(hex_color: str) -> str:
    h = hex_color.lstrip("#")
    return f"{int(h[0:2], 16)},{int(h[2:4], 16)},{int(h[4:6], 16)}"
