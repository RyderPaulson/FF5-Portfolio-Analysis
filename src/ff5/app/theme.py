"""Color palette and Plotly template for the app."""

from __future__ import annotations

# Portfolio colors — matches the MATLAB colors array style
PORTFOLIO_COLORS = [
    "#009E5E",  # green
    "#142D69",  # navy
    "#D4442E",  # red
    "#E8A317",  # amber
    "#7B2D8E",  # purple
    "#0077B6",  # blue
    "#E85D75",  # rose
    "#2D8E6E",  # teal
]

COLOR_PRIMARY = "#009E5E"
COLOR_SECONDARY = "#142D69"
COLOR_MUTED = "#999999"

PLOTLY_TEMPLATE = "plotly_white"

FIGURE_LAYOUT = dict(
    template=PLOTLY_TEMPLATE,
    font=dict(family="system-ui, -apple-system, sans-serif", size=12),
    margin=dict(l=60, r=30, t=50, b=50),
    legend=dict(
        bgcolor="rgba(255,255,255,0.8)",
        borderwidth=0,
    ),
)


def get_color(index: int) -> str:
    """Get a portfolio color by index, cycling if needed."""
    return PORTFOLIO_COLORS[index % len(PORTFOLIO_COLORS)]
