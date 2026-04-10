"""Macro Analysis tab — multi-portfolio comparison bento grid."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import dcc, html

from ff5.app.theme import (
    BENTO_CARD_STYLE,
    BENTO_CARD_STYLE_COMPACT,
    COLOR_TEXT_MUTED,
)

_GRAPH_STYLE = {"height": "340px"}
_GRAPH_CONFIG = {"displayModeBar": False}


def _bento_compact(children, **style_overrides):
    s = {**BENTO_CARD_STYLE_COMPACT, **style_overrides}
    return html.Div(children, style=s)


def create_macro_tab_content() -> html.Div:
    """Return the bento grid content for the Macro Analysis tab."""
    return html.Div(
        style={
            "display": "grid",
            "gridTemplateColumns": "1fr 1fr",
            "gap": "12px",
        },
        children=[
            # ── Row 1: Summary table ────────────────────────────
            html.Div(
                style={
                    **BENTO_CARD_STYLE,
                    "gridColumn": "1 / 3",
                },
                children=[
                    html.Div(
                        style={"display": "flex", "justifyContent": "space-between", "alignItems": "center", "marginBottom": "12px"},
                        children=[
                            html.H6("Summary", style={"margin": 0, "color": COLOR_TEXT_MUTED}),
                            html.Div(id="summary-export-container"),
                        ],
                    ),
                    html.Div(id="tab-summary"),
                ],
            ),

            # ── Row 2: Efficient Frontier + Forecasted Returns ──
            _bento_compact(
                [
                    html.H6("Efficient Frontier", style={"marginBottom": "8px", "color": COLOR_TEXT_MUTED}),
                    dcc.Graph(id="graph-frontier", style=_GRAPH_STYLE, config=_GRAPH_CONFIG),
                ],
            ),
            _bento_compact(
                [
                    html.Div(
                        style={"display": "flex", "justifyContent": "space-between", "alignItems": "center", "marginBottom": "8px"},
                        children=[
                            html.H6("Forecasted Returns", style={"margin": 0, "color": COLOR_TEXT_MUTED}),
                            dbc.Select(
                                id="forecast-portfolio-select",
                                options=[],
                                value=None,
                                style={"maxWidth": "160px", "fontSize": "12px", "padding": "2px 8px"},
                            ),
                        ],
                    ),
                    dcc.Graph(id="graph-forecast", style=_GRAPH_STYLE, config=_GRAPH_CONFIG),
                ],
            ),

            # ── Row 3: House Distribution + Retire Distribution ─
            _bento_compact(
                [
                    html.H6("House Distribution", style={"marginBottom": "8px", "color": COLOR_TEXT_MUTED}),
                    dcc.Graph(id="graph-dist-house", style=_GRAPH_STYLE, config=_GRAPH_CONFIG),
                ],
            ),
            _bento_compact(
                [
                    html.H6("Retirement Distribution", style={"marginBottom": "8px", "color": COLOR_TEXT_MUTED}),
                    dcc.Graph(id="graph-dist-retire", style=_GRAPH_STYLE, config=_GRAPH_CONFIG),
                ],
            ),

            # ── Row 4: Drawdown + Factor Exposures ──────────────
            _bento_compact(
                [
                    html.Div(
                        style={"display": "flex", "justifyContent": "space-between", "alignItems": "center", "marginBottom": "8px"},
                        children=[
                            html.H6("Historical Drawdown", style={"margin": 0, "color": COLOR_TEXT_MUTED}),
                            dbc.Select(
                                id="drawdown-portfolio-select",
                                options=[],
                                value=None,
                                style={"maxWidth": "160px", "fontSize": "12px", "padding": "2px 8px"},
                            ),
                        ],
                    ),
                    dcc.Graph(id="graph-drawdown", style=_GRAPH_STYLE, config=_GRAPH_CONFIG),
                ],
            ),
            _bento_compact(
                [
                    html.H6("Factor Exposures", style={"marginBottom": "8px", "color": COLOR_TEXT_MUTED}),
                    dcc.Graph(id="graph-factors", style=_GRAPH_STYLE, config=_GRAPH_CONFIG),
                ],
            ),
        ],
    )
