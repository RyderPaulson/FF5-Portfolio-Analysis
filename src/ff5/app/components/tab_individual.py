"""Individual Portfolio Analysis tab — deep-dive into a single portfolio."""

from __future__ import annotations

import numpy as np
import plotly.graph_objects as go
import dash_bootstrap_components as dbc
from dash import Input, Output, State, callback, dash_table, dcc, html, no_update

from ff5.app.asset_classification import classify_portfolio
from ff5.app.figures.region_pie import create_region_pie
from ff5.app.figures.style_box import create_style_box
from ff5.app.theme import (
    BG_CARD,
    BENTO_CARD_STYLE,
    BENTO_CARD_STYLE_COMPACT,
    COLOR_BORDER,
    COLOR_PRIMARY,
    COLOR_TEXT,
    COLOR_TEXT_MUTED,
    FIGURE_LAYOUT,
    FONT_FAMILY,
    PORTFOLIO_COLORS,
)

_GRAPH_STYLE = {"height": "300px"}
_GRAPH_CONFIG = {"displayModeBar": False}


def create_individual_tab_content() -> html.Div:
    """Return the layout for the Individual Portfolio tab."""
    return html.Div(
        style={
            "display": "grid",
            "gridTemplateColumns": "1fr 1fr",
            "gap": "12px",
        },
        children=[
            # ── Portfolio selector (full width) ─────────────────
            html.Div(
                style={**BENTO_CARD_STYLE, "gridColumn": "1 / 3", "padding": "12px 20px"},
                children=[
                    html.Div(
                        style={"display": "flex", "alignItems": "center", "gap": "12px"},
                        children=[
                            html.H6("Portfolio", style={"margin": 0, "color": COLOR_TEXT_MUTED}),
                            dbc.Select(
                                id="indiv-portfolio-select",
                                options=[],
                                value=None,
                                style={"maxWidth": "250px", "fontSize": "13px"},
                            ),
                        ],
                    ),
                ],
            ),

            # ── Holdings table (full width) ─────────────────────
            html.Div(
                style={**BENTO_CARD_STYLE, "gridColumn": "1 / 3"},
                children=[
                    html.H6("Holdings", style={"marginBottom": "12px", "color": COLOR_TEXT_MUTED}),
                    html.Div(id="indiv-holdings-table"),
                ],
            ),

            # ── Region pie (left) ───────────────────────────────
            html.Div(
                style=BENTO_CARD_STYLE_COMPACT,
                children=[
                    dcc.Graph(id="graph-region-pie", style=_GRAPH_STYLE, config=_GRAPH_CONFIG),
                ],
            ),

            # ── Style box (right) ───────────────────────────────
            html.Div(
                style=BENTO_CARD_STYLE_COMPACT,
                children=[
                    dcc.Graph(id="graph-style-box", style=_GRAPH_STYLE, config=_GRAPH_CONFIG),
                ],
            ),

            # ── Rebalancing calculator (full width) ─────────────
            html.Div(
                style={**BENTO_CARD_STYLE, "gridColumn": "1 / 3"},
                children=[
                    html.H6("Rebalancing Calculator", style={"marginBottom": "12px", "color": COLOR_TEXT_MUTED}),
                    html.Div(
                        style={"display": "flex", "gap": "16px", "marginBottom": "12px", "alignItems": "center"},
                        children=[
                            html.Div([
                                html.Label("Total Portfolio Value ($)", style={"fontSize": "12px", "color": COLOR_TEXT_MUTED}),
                                dbc.Input(id="rebal-total-value", type="number", value=10000, min=0, step=100, size="sm"),
                            ]),
                            html.Div([
                                html.Label("Additional Contribution ($)", style={"fontSize": "12px", "color": COLOR_TEXT_MUTED}),
                                dbc.Input(id="rebal-contribution", type="number", value=500, min=0, step=50, size="sm"),
                            ]),
                        ],
                    ),
                    html.Div(id="rebal-table"),
                ],
            ),

            # ── Correlation heatmap (full width) ────────────────
            html.Div(
                style={**BENTO_CARD_STYLE_COMPACT, "gridColumn": "1 / 3"},
                children=[
                    html.H6("Asset Correlation", style={"marginBottom": "8px", "color": COLOR_TEXT_MUTED}),
                    dcc.Graph(id="graph-asset-correlation", style={"height": "380px"}, config=_GRAPH_CONFIG),
                ],
            ),

            # ── Return attribution (full width) ─────────────────
            html.Div(
                style={**BENTO_CARD_STYLE_COMPACT, "gridColumn": "1 / 3"},
                children=[
                    html.H6("Return Attribution", style={"marginBottom": "8px", "color": COLOR_TEXT_MUTED}),
                    dcc.Graph(id="graph-return-attribution", style=_GRAPH_STYLE, config=_GRAPH_CONFIG),
                ],
            ),
        ],
    )


def register_individual_callbacks(app, state):
    """Register all callbacks for the Individual Portfolio tab."""

    # ── Sync portfolio dropdown ─────────────────────────────────
    @callback(
        Output("indiv-portfolio-select", "options"),
        Output("indiv-portfolio-select", "value"),
        Input("store-portfolios-version", "data"),
        Input("store-results-version", "data"),
    )
    def sync_indiv_dropdown(_pv, _rv):
        pairs = state.get_analyzed_pairs()
        options = [{"label": title, "value": title} for title, _ in pairs]
        value = pairs[0][0] if pairs else None
        return options, value

    # ── Update holdings, figures, correlation, attribution ──────
    @callback(
        Output("indiv-holdings-table", "children"),
        Output("graph-region-pie", "figure"),
        Output("graph-style-box", "figure"),
        Output("graph-asset-correlation", "figure"),
        Output("graph-return-attribution", "figure"),
        Input("indiv-portfolio-select", "value"),
        Input("store-results-version", "data"),
    )
    def update_individual_tab(selected_title, _version):
        empty_fig = {"data": [], "layout": {"title": "Run analysis first"}}

        if not selected_title:
            return html.P("Select a portfolio.", style={"color": COLOR_TEXT_MUTED}), empty_fig, empty_fig, empty_fig, empty_fig

        r = state.get_result(selected_title)
        if r is None:
            return html.P("Portfolio not yet analyzed.", style={"color": COLOR_TEXT_MUTED}), empty_fig, empty_fig, empty_fig, empty_fig

        symbols = r.symbols
        weights = r.weights
        betas = r.factor_betas

        # Classify assets
        classifications = classify_portfolio(symbols, betas)

        # Holdings table
        holdings_data = []
        for i, (sym, w, cls) in enumerate(zip(symbols, weights, classifications)):
            holdings_data.append({
                "Ticker": sym,
                "Weight %": round(w * 100, 2),
                "Cap Size": cls.cap_size,
                "Style": cls.style,
                "Region": cls.region,
                "Category": cls.category,
            })

        holdings_table = dash_table.DataTable(
            columns=[{"name": c, "id": c} for c in ["Ticker", "Weight %", "Cap Size", "Style", "Region", "Category"]],
            data=holdings_data,
            style_table={"overflowX": "auto"},
            style_cell={
                "textAlign": "left",
                "padding": "8px 12px",
                "fontFamily": FONT_FAMILY,
                "fontSize": "13px",
                "color": COLOR_TEXT,
                "backgroundColor": BG_CARD,
                "border": f"1px solid {COLOR_BORDER}",
            },
            style_cell_conditional=[
                {"if": {"column_id": "Weight %"}, "textAlign": "right", "fontWeight": "bold"},
            ],
            style_header={
                "fontWeight": "bold",
                "backgroundColor": "#E8E5D8",
                "borderBottom": f"2px solid {COLOR_BORDER}",
            },
            style_data_conditional=[
                {"if": {"row_index": "odd"}, "backgroundColor": "#F4F2EA"},
            ],
        )

        # Region pie
        regions = [c.region for c in classifications]
        region_fig = create_region_pie(regions, weights)

        # Style box — weighted average of SMB and HML betas
        w_arr = np.array(weights)
        avg_smb = float(w_arr @ betas[:, 1])
        avg_hml = float(w_arr @ betas[:, 2])
        style_fig = create_style_box(avg_smb, avg_hml, title=selected_title)

        # Correlation heatmap — from raw returns, not shrunk covariance
        corr_fig = _create_correlation_heatmap(r.asset_returns, symbols)

        # Return attribution
        attr_fig = _create_return_attribution(symbols, weights, r.mu_annual)

        return holdings_table, region_fig, style_fig, corr_fig, attr_fig

    # ── Rebalancing calculator ──────────────────────────────────
    @callback(
        Output("rebal-table", "children"),
        Input("rebal-total-value", "value"),
        Input("rebal-contribution", "value"),
        Input("indiv-portfolio-select", "value"),
        State("store-results-version", "data"),
    )
    def update_rebalancing(total_value, contribution, selected_title, _version):
        if not selected_title or total_value is None or contribution is None:
            return html.P("Enter values above.", style={"color": COLOR_TEXT_MUTED})

        r = state.get_result(selected_title)
        if r is None:
            return html.P("Portfolio not yet analyzed.", style={"color": COLOR_TEXT_MUTED})

        V = float(total_value)
        C = float(contribution)
        new_total = V + C

        rows = []
        for sym, w in zip(r.symbols, r.weights):
            current = V * w
            target = new_total * w
            action = target - current
            rows.append({
                "Ticker": sym,
                "Target %": f"{w * 100:.1f}",
                "Current $": f"{current:,.2f}",
                "Target $": f"{target:,.2f}",
                "Buy $": f"{action:,.2f}",
            })

        return dash_table.DataTable(
            columns=[{"name": c, "id": c} for c in ["Ticker", "Target %", "Current $", "Target $", "Buy $"]],
            data=rows,
            style_table={"overflowX": "auto"},
            style_cell={
                "textAlign": "right",
                "padding": "8px 12px",
                "fontFamily": FONT_FAMILY,
                "fontSize": "13px",
                "color": COLOR_TEXT,
                "backgroundColor": BG_CARD,
                "border": f"1px solid {COLOR_BORDER}",
            },
            style_cell_conditional=[
                {"if": {"column_id": "Ticker"}, "textAlign": "left", "fontWeight": "bold"},
            ],
            style_header={
                "fontWeight": "bold",
                "backgroundColor": "#E8E5D8",
                "borderBottom": f"2px solid {COLOR_BORDER}",
            },
            style_data_conditional=[
                {"if": {"row_index": "odd"}, "backgroundColor": "#F4F2EA"},
            ],
        )


def _create_correlation_heatmap(asset_returns: np.ndarray, symbols: list[str]) -> go.Figure:
    """Build a correlation heatmap from raw asset returns (not shrunk covariance)."""
    corr = np.corrcoef(asset_returns, rowvar=False)

    fig = go.Figure(
        go.Heatmap(
            z=corr,
            x=symbols,
            y=symbols,
            colorscale=[
                [0, "#5A8EAE"],    # dusty blue (negative)
                [0.5, "#FAFAF7"],  # card white (zero)
                [1, "#DA7756"],    # terra cotta (positive)
            ],
            zmin=-1, zmax=1,
            text=np.round(corr, 2),
            texttemplate="%{text}",
            textfont=dict(size=11),
            hovertemplate="%{x} vs %{y}: %{z:.3f}<extra></extra>",
            colorbar=dict(title="Corr", thickness=12, len=0.8),
        )
    )

    fig.update_layout(
        **{**FIGURE_LAYOUT, "margin": dict(l=60, r=30, t=50, b=60)},
        title="Asset Correlation Matrix",
        xaxis=dict(side="bottom"),
        yaxis=dict(autorange="reversed"),
    )

    return fig


def _create_return_attribution(
    symbols: list[str], weights: list[float], mu_annual: np.ndarray,
) -> go.Figure:
    """Bar chart showing each asset's contribution to portfolio return."""
    contributions = [w * mu * 100 for w, mu in zip(weights, mu_annual)]

    fig = go.Figure(
        go.Bar(
            x=symbols,
            y=contributions,
            marker_color=[PORTFOLIO_COLORS[i % len(PORTFOLIO_COLORS)] for i in range(len(symbols))],
            text=[f"{c:.2f}%" for c in contributions],
            textposition="outside",
            hovertemplate="%{x}: %{y:.2f}% contribution<extra></extra>",
        )
    )

    fig.update_layout(
        **FIGURE_LAYOUT,
        title="Return Attribution (weight x expected return)",
        yaxis_title="Contribution to E[r] (%)",
        showlegend=False,
    )

    return fig
