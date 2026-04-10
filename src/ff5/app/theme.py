"""Color palette and Plotly template — Claude-inspired warm theme."""

from __future__ import annotations

# Claude-inspired palette
BG_PAGE = "#EEECE2"        # warm cream page background
BG_CARD = "#FAFAF7"        # slightly lighter card background
BG_SIDEBAR = "#E8E5D8"     # warmer tone for sidebar
COLOR_PRIMARY = "#DA7756"   # terra cotta accent
COLOR_PRIMARY_DARK = "#BD5D3A"  # darker terra cotta (buttons/hover)
COLOR_TEXT = "#3D3929"      # dark brown body text
COLOR_TEXT_MUTED = "#8A8473"  # muted brown
COLOR_BORDER = "#DDD9CB"   # subtle warm border
COLOR_SECONDARY = "#BD5D3A"
COLOR_MUTED = "#8A8473"

# Portfolio colors — warm-compatible series
PORTFOLIO_COLORS = [
    "#DA7756",  # terra cotta
    "#5B8A72",  # sage green
    "#7B6CB5",  # muted purple
    "#C4963C",  # warm gold
    "#5A8EAE",  # dusty blue
    "#C45E6A",  # muted rose
    "#3D7A6E",  # dark teal
    "#9B7653",  # warm brown
]

FONT_FAMILY = "ui-serif, Georgia, Cambria, 'Times New Roman', Times, serif"
FONT_FAMILY_MONO = "ui-monospace, 'SF Mono', Monaco, monospace"

PLOTLY_TEMPLATE = "plotly_white"

FIGURE_LAYOUT = dict(
    template=PLOTLY_TEMPLATE,
    font=dict(family=FONT_FAMILY, size=12, color=COLOR_TEXT),
    margin=dict(l=60, r=30, t=50, b=50),
    legend=dict(
        bgcolor="rgba(250,250,247,0.9)",
        borderwidth=0,
    ),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
)

# Shared bento card style (applied via inline style dict)
BENTO_CARD_STYLE = {
    "backgroundColor": BG_CARD,
    "borderRadius": "16px",
    "border": f"1px solid {COLOR_BORDER}",
    "padding": "20px",
    "height": "100%",
}

BENTO_CARD_STYLE_COMPACT = {
    **BENTO_CARD_STYLE,
    "padding": "16px",
}


def get_color(index: int) -> str:
    """Get a portfolio color by index, cycling if needed."""
    return PORTFOLIO_COLORS[index % len(PORTFOLIO_COLORS)]
