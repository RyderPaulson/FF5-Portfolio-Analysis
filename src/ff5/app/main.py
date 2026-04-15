"""Dash application — main entry point."""

from __future__ import annotations

import traceback

import dash
import dash_bootstrap_components as dbc
from dash import ALL, Input, Output, State, callback, ctx, dcc, html, no_update

from ff5.analytics.analyze import analyze_portfolio
from ff5.app.components.analysis_controls import create_run_button, create_settings_panel
from ff5.app.components.portfolio_editor import (
    create_asset_weight_row,
    create_portfolio_editor_layout,
)
from ff5.app.components.summary_table import create_export_button, create_summary_table
from ff5.app.components.tab_individual import create_individual_tab_content, register_individual_callbacks
from ff5.app.components.tab_macro import create_macro_tab_content
from ff5.app.components.tab_wiki import create_wiki_tab_content
from ff5.app.figures.efficient_frontier import create_efficient_frontier
from ff5.app.figures.factor_exposures import create_factor_exposures
from ff5.app.figures.forecasted_returns import create_forecasted_returns
from ff5.app.figures.historical_drawdown import create_historical_drawdown
from ff5.app.figures.return_distributions import create_return_distribution_single
from ff5.app.state import state
from ff5.app.theme import (
    BG_CARD,
    BG_PAGE,
    BG_SIDEBAR,
    BENTO_CARD_STYLE,
    COLOR_BORDER,
    COLOR_PRIMARY,
    COLOR_TEXT,
    COLOR_TEXT_MUTED,
    FONT_FAMILY,
    TAB_SELECTED_STYLE,
    TAB_STYLE,
)
from ff5.models import Milestone, OptimOptions, PortfolioSpec
from ff5.optimizers.dispatcher import run_optimizer


def create_app() -> dash.Dash:
    """Create and configure the Dash application."""
    app = dash.Dash(
        __name__,
        external_stylesheets=[dbc.themes.BOOTSTRAP],
        suppress_callback_exceptions=True,
    )

    app.title = "FF5 Portfolio Analysis"
    state.load_from_yaml()

    app.layout = _create_layout()
    _register_callbacks(app)
    register_individual_callbacks(app, state)

    return app


def _create_layout() -> html.Div:
    return html.Div(
        style={
            "backgroundColor": BG_PAGE,
            "minHeight": "100vh",
            "fontFamily": FONT_FAMILY,
            "color": COLOR_TEXT,
        },
        children=[
            # ── Header bar ──────────────────────────────────────────
            html.Div(
                style={
                    "padding": "16px 24px",
                    "display": "flex",
                    "alignItems": "center",
                    "justifyContent": "space-between",
                },
                children=[
                    html.H4(
                        "FF5 Portfolio Analysis",
                        style={
                            "margin": 0,
                            "fontWeight": "600",
                            "color": COLOR_TEXT,
                            "letterSpacing": "-0.02em",
                        },
                    ),
                    html.Div(
                        style={"display": "flex", "gap": "8px", "alignItems": "center"},
                        children=[
                            dbc.Alert(
                                id="status-alert",
                                is_open=False,
                                duration=5000,
                                style={"margin": 0, "padding": "6px 12px", "fontSize": "13px"},
                            ),
                            create_run_button(),
                        ],
                    ),
                ],
            ),

            # ── Two-column layout: sidebar + tabbed content ─────────
            html.Div(
                style={
                    "display": "grid",
                    "gridTemplateColumns": "280px 1fr",
                    "gap": "12px",
                    "padding": "0 24px 24px 24px",
                },
                children=[
                    # ── Sidebar ──────────────────────────────────────
                    html.Div(
                        style={
                            **BENTO_CARD_STYLE,
                            "backgroundColor": BG_SIDEBAR,
                        },
                        children=[
                            create_portfolio_editor_layout(),
                            html.Hr(style={"borderColor": COLOR_BORDER, "margin": "16px 0"}),
                            create_settings_panel(),
                        ],
                    ),

                    # ── Tabbed main content ──────────────────────────
                    html.Div(
                        children=[
                            dcc.Tabs(
                                id="main-tabs",
                                value="macro",
                                children=[
                                    dcc.Tab(
                                        label="Macro Analysis",
                                        value="macro",
                                        style=TAB_STYLE,
                                        selected_style=TAB_SELECTED_STYLE,
                                        children=create_macro_tab_content(),
                                    ),
                                    dcc.Tab(
                                        label="Individual Portfolio",
                                        value="individual",
                                        style=TAB_STYLE,
                                        selected_style=TAB_SELECTED_STYLE,
                                        children=create_individual_tab_content(),
                                    ),
                                    dcc.Tab(
                                        label="Methodology",
                                        value="wiki",
                                        style=TAB_STYLE,
                                        selected_style=TAB_SELECTED_STYLE,
                                        children=create_wiki_tab_content(),
                                    ),
                                ],
                            ),
                        ],
                    ),
                ],
            ),

            # Hidden stores
            dcc.Store(id="store-portfolios-version", data=0),
            dcc.Store(id="store-results-version", data=0),
        ],
    )


def _register_callbacks(app: dash.Dash):
    # ------------------------------------------------------------------ #
    # Portfolio Management Callbacks
    # ------------------------------------------------------------------ #

    @callback(
        Output("portfolio-selector", "options"),
        Output("portfolio-selector", "value"),
        Output("store-portfolios-version", "data"),
        Input("btn-add-portfolio", "n_clicks"),
        Input("btn-remove-portfolio", "n_clicks"),
        Input("store-portfolios-version", "data"),
        State("portfolio-selector", "value"),
        prevent_initial_call=False,
    )
    def manage_portfolios(add_clicks, remove_clicks, version, selected):
        triggered = ctx.triggered_id

        if triggered == "btn-add-portfolio":
            idx = len(state.portfolios) + 1
            state.add_portfolio(
                PortfolioSpec(
                    assets=["VOO"],
                    weights=[1.0],
                    title=f"Portfolio {idx}",
                )
            )
            version = (version or 0) + 1
        elif triggered == "btn-remove-portfolio" and selected is not None:
            state.remove_portfolio(int(selected))
            version = (version or 0) + 1

        options = [
            {"label": p.title or f"Portfolio {i + 1}", "value": str(i)}
            for i, p in enumerate(state.portfolios)
        ]
        value = selected if selected is not None and int(selected) < len(state.portfolios) else (
            "0" if state.portfolios else None
        )

        return options, value, version or 0

    @callback(
        Output("portfolio-title", "value"),
        Output("portfolio-rebalance-cost", "value"),
        Output("asset-weights-container", "children"),
        Input("portfolio-selector", "value"),
        Input("store-portfolios-version", "data"),
    )
    def display_selected_portfolio(selected, _version):
        if selected is None or not state.portfolios:
            return "", 0, []

        idx = int(selected)
        if idx >= len(state.portfolios):
            return "", 0, []

        p = state.portfolios[idx]
        rows = [
            create_asset_weight_row(sym, w, i)
            for i, (sym, w) in enumerate(zip(p.assets, p.weights))
        ]
        return p.title, p.rebalance_cost, rows

    @callback(
        Output("store-portfolios-version", "data", allow_duplicate=True),
        Input("portfolio-title", "value"),
        Input("portfolio-rebalance-cost", "value"),
        State("portfolio-selector", "value"),
        State("store-portfolios-version", "data"),
        prevent_initial_call=True,
    )
    def update_portfolio_metadata(title, cost, selected, version):
        if selected is None or not state.portfolios:
            return no_update
        idx = int(selected)
        if idx >= len(state.portfolios):
            return no_update

        p = state.portfolios[idx]
        changed = False
        if title is not None and title != p.title:
            p.title = title
            changed = True
        if cost is not None and cost != p.rebalance_cost:
            p.rebalance_cost = cost
            changed = True

        return (version or 0) + 1 if changed else no_update

    @callback(
        Output("store-portfolios-version", "data", allow_duplicate=True),
        Input("btn-add-ticker", "n_clicks"),
        State("new-ticker-input", "value"),
        State("portfolio-selector", "value"),
        State("store-portfolios-version", "data"),
        prevent_initial_call=True,
    )
    def add_ticker(n_clicks, ticker, selected, version):
        if not ticker or selected is None:
            return no_update
        idx = int(selected)
        if idx >= len(state.portfolios):
            return no_update

        p = state.portfolios[idx]
        ticker = ticker.upper().strip()
        if ticker and ticker not in p.assets:
            p.assets.append(ticker)
            p.weights.append(0.0)
            n = len(p.weights)
            p.weights = [1.0 / n] * n
            return (version or 0) + 1
        return no_update

    # ------------------------------------------------------------------ #
    # Remove Ticker
    # ------------------------------------------------------------------ #

    @callback(
        Output("store-portfolios-version", "data", allow_duplicate=True),
        Input({"type": "btn-remove-ticker", "index": ALL}, "n_clicks"),
        State("portfolio-selector", "value"),
        State("store-portfolios-version", "data"),
        prevent_initial_call=True,
    )
    def remove_ticker(n_clicks_list, selected, version):
        if selected is None or not any(n_clicks_list):
            return no_update
        idx = int(selected)
        if idx >= len(state.portfolios):
            return no_update

        triggered = ctx.triggered_id
        if not isinstance(triggered, dict):
            return no_update
        remove_idx = triggered["index"]

        p = state.portfolios[idx]
        if remove_idx < len(p.assets) and len(p.assets) > 1:
            p.assets.pop(remove_idx)
            p.weights.pop(remove_idx)
            total = sum(p.weights)
            if total > 0:
                p.weights = [w / total for w in p.weights]
            else:
                n = len(p.weights)
                p.weights = [1.0 / n] * n
            return (version or 0) + 1
        return no_update

    # ------------------------------------------------------------------ #
    # Update Weights from Numeric Inputs
    # ------------------------------------------------------------------ #

    @callback(
        Output("store-portfolios-version", "data", allow_duplicate=True),
        Input({"type": "weight-input", "index": ALL}, "value"),
        State("portfolio-selector", "value"),
        State("store-portfolios-version", "data"),
        prevent_initial_call=True,
    )
    def update_weights(weight_values, selected, version):
        if selected is None or not weight_values:
            return no_update
        idx = int(selected)
        if idx >= len(state.portfolios):
            return no_update

        p = state.portfolios[idx]
        if len(weight_values) != len(p.weights):
            return no_update

        new_weights = []
        for v in weight_values:
            val = float(v) if v is not None else 0.0
            new_weights.append(max(0.0, val) / 100.0)

        total = sum(new_weights)
        if total > 0:
            new_weights = [w / total for w in new_weights]

        if new_weights != p.weights:
            p.weights = new_weights
            return (version or 0) + 1
        return no_update

    # ------------------------------------------------------------------ #
    # Run Analysis
    # ------------------------------------------------------------------ #

    @callback(
        Output("store-results-version", "data"),
        Output("status-alert", "children"),
        Output("status-alert", "is_open"),
        Output("status-alert", "color"),
        Input("btn-run-all", "n_clicks"),
        State("input-rf", "value"),
        State("input-n-sims", "value"),
        State("input-horizon", "value"),
        State("store-results-version", "data"),
        prevent_initial_call=True,
    )
    def run_analysis(n_clicks, rf, n_sims, horizon, version):
        if not state.portfolios:
            return no_update, "No portfolios defined.", True, "warning"

        rf = rf or 0.045
        n_sims = n_sims or 10000
        horizon = horizon or 44

        milestones = state.milestones
        milestone_targets = state.config.milestone_targets

        errors = []
        for p in state.portfolios:
            try:
                result = analyze_portfolio(
                    p,
                    rf=rf,
                    n_simulations=n_sims,
                    horizon_years=horizon,
                    milestones=milestones,
                    milestone_targets=milestone_targets,
                    verbose=False,
                )
                state.set_result(p.title, result)
            except Exception as e:
                errors.append(f"{p.title}: {e}")
                traceback.print_exc()

        if errors:
            msg = f"Analysis completed with errors: {'; '.join(errors)}"
            return (version or 0) + 1, msg, True, "warning"

        n_analyzed = len(state.get_analyzed_pairs())
        return (version or 0) + 1, f"Analysis complete \u2014 {n_analyzed} portfolios.", True, "success"

    # ------------------------------------------------------------------ #
    # Show/hide factor targets
    # ------------------------------------------------------------------ #

    @callback(
        Output("factor-targets-container", "style"),
        Input("optimizer-method", "value"),
    )
    def toggle_factor_targets(method):
        if method == "factorbased":
            return {"display": "block"}
        return {"display": "none"}

    # ------------------------------------------------------------------ #
    # Run Optimizer
    # ------------------------------------------------------------------ #

    @callback(
        Output("store-portfolios-version", "data", allow_duplicate=True),
        Output("status-alert", "children", allow_duplicate=True),
        Output("status-alert", "is_open", allow_duplicate=True),
        Output("status-alert", "color", allow_duplicate=True),
        Input("btn-run-optimizer", "n_clicks"),
        State("optimizer-method", "value"),
        State("optimizer-source-portfolio", "value"),
        State("input-rf", "value"),
        State("factor-target-0", "value"),
        State("factor-target-1", "value"),
        State("factor-target-2", "value"),
        State("factor-target-3", "value"),
        State("factor-target-4", "value"),
        State("store-portfolios-version", "data"),
        prevent_initial_call=True,
    )
    def run_optimization(n_clicks, method, source_idx, rf, ft0, ft1, ft2, ft3, ft4, version):
        if source_idx is None or not method:
            return no_update, "Select a source portfolio and method.", True, "warning"

        idx = int(source_idx)
        if idx >= len(state.portfolios):
            return no_update, "Invalid portfolio selection.", True, "danger"

        p = state.portfolios[idx]
        r = state.get_result(p.title)
        if r is None:
            return no_update, f'"{p.title}" has not been analyzed yet. Run analysis first.', True, "warning"

        try:
            import numpy as np
            opts = OptimOptions(rf=rf or 0.045)

            if method == "factorbased":
                raw = [ft0, ft1, ft2, ft3, ft4]
                targets = np.array([
                    float(v) if v is not None and v != "" else np.nan
                    for v in raw
                ])
                opts.factor_targets = targets

            opt_port = run_optimizer(method, p, r, opts)
            opt_port.title = f"{p.title} ({method})"
            state.add_portfolio(opt_port)
            return (version or 0) + 1, f"Optimized: {opt_port.title}", True, "success"
        except Exception as e:
            return no_update, f"Optimization failed: {e}", True, "danger"

    # ------------------------------------------------------------------ #
    # Update optimizer source portfolio dropdown
    # ------------------------------------------------------------------ #

    @callback(
        Output("optimizer-source-portfolio", "options"),
        Input("store-portfolios-version", "data"),
    )
    def update_optimizer_source_options(_version):
        return [
            {"label": p.title or f"Portfolio {i + 1}", "value": str(i)}
            for i, p in enumerate(state.portfolios)
        ]

    # ------------------------------------------------------------------ #
    # Update Macro Visualizations
    # ------------------------------------------------------------------ #

    @callback(
        Output("tab-summary", "children"),
        Output("summary-export-container", "children"),
        Output("graph-frontier", "figure"),
        Output("graph-forecast", "figure"),
        Output("graph-dist-house", "figure"),
        Output("graph-dist-retire", "figure"),
        Output("graph-factors", "figure"),
        Output("graph-drawdown", "figure"),
        Output("forecast-portfolio-select", "options"),
        Output("forecast-portfolio-select", "value"),
        Output("drawdown-portfolio-select", "options"),
        Output("drawdown-portfolio-select", "value"),
        Input("store-results-version", "data"),
    )
    def update_visualizations(_version):
        pairs = state.get_analyzed_pairs()
        empty_fig = {"data": [], "layout": {"title": "Run analysis to see results"}}

        if not pairs:
            return (
                html.P("No analysis results yet. Add portfolios and click 'Run All'.",
                       style={"color": COLOR_TEXT_MUTED}),
                html.Span(),
                empty_fig,
                empty_fig,
                empty_fig,
                empty_fig,
                empty_fig,
                empty_fig,
                [],
                None,
                [],
                None,
            )

        results_map = {title: r for title, r in pairs}

        summary = create_summary_table(pairs)
        export_btn = create_export_button(pairs)

        try:
            frontier = create_efficient_frontier(
                [p for p in state.portfolios if p.title in results_map],
                results_map,
                rf=state.config.rf,
            )
        except Exception:
            frontier = empty_fig

        first_title = pairs[0][0] if pairs else None
        forecast = create_forecasted_returns(pairs, state.milestones, selected_title=first_title)
        dist_house = create_return_distribution_single(pairs, 0, state.milestones)
        dist_retire = create_return_distribution_single(pairs, 1, state.milestones)
        factors = create_factor_exposures(pairs)
        drawdown = create_historical_drawdown(pairs, selected_title=first_title)

        portfolio_options = [{"label": title, "value": title} for title, _ in pairs]

        return (summary, export_btn, frontier, forecast, dist_house, dist_retire, factors, drawdown,
                portfolio_options, first_title, portfolio_options, first_title)

    @callback(
        Output("graph-forecast", "figure", allow_duplicate=True),
        Input("forecast-portfolio-select", "value"),
        State("store-results-version", "data"),
        prevent_initial_call=True,
    )
    def update_forecast_selection(selected_title, _version):
        pairs = state.get_analyzed_pairs()
        if not pairs:
            return no_update
        return create_forecasted_returns(pairs, state.milestones, selected_title=selected_title)

    @callback(
        Output("graph-drawdown", "figure", allow_duplicate=True),
        Input("drawdown-portfolio-select", "value"),
        State("store-results-version", "data"),
        prevent_initial_call=True,
    )
    def update_drawdown_selection(selected_title, _version):
        pairs = state.get_analyzed_pairs()
        if not pairs:
            return no_update
        return create_historical_drawdown(pairs, selected_title=selected_title)

    # ------------------------------------------------------------------ #
    # Config save/load
    # ------------------------------------------------------------------ #

    @callback(
        Output("status-alert", "children", allow_duplicate=True),
        Output("status-alert", "is_open", allow_duplicate=True),
        Output("status-alert", "color", allow_duplicate=True),
        Input("btn-save-config", "n_clicks"),
        prevent_initial_call=True,
    )
    def save_config(_n):
        state.save_to_yaml()
        return "Configuration saved.", True, "success"

    @callback(
        Output("store-portfolios-version", "data", allow_duplicate=True),
        Output("status-alert", "children", allow_duplicate=True),
        Output("status-alert", "is_open", allow_duplicate=True),
        Output("status-alert", "color", allow_duplicate=True),
        Input("btn-load-config", "n_clicks"),
        State("store-portfolios-version", "data"),
        prevent_initial_call=True,
    )
    def load_config_cb(_n, version):
        state.load_from_yaml()
        state.clear_results()
        n = len(state.portfolios)
        return (version or 0) + 1, f"Loaded {n} portfolios from config.", True, "info"

    # ------------------------------------------------------------------ #
    # Brokerage integration (SnapTrade)
    # ------------------------------------------------------------------ #

    @callback(
        Output("store-portfolios-version", "data", allow_duplicate=True),
        Output("brokerage-status", "children"),
        Output("status-alert", "children", allow_duplicate=True),
        Output("status-alert", "is_open", allow_duplicate=True),
        Output("status-alert", "color", allow_duplicate=True),
        Output("rebal-total-value", "value"),
        Input("btn-load-brokerage", "n_clicks"),
        State("store-portfolios-version", "data"),
        prevent_initial_call=True,
    )
    def load_from_brokerage(_n, version):
        from ff5.data.snaptrade_client import (
            fetch_holdings,
            holdings_to_portfolio,
            is_configured,
            is_connected,
            register_and_connect,
        )

        if not is_configured():
            return (
                no_update,
                "Add SNAPTRADE_CLIENT_ID and SNAPTRADE_CONSUMER_KEY to .env",
                "SnapTrade credentials not configured. See .env.example.",
                True,
                "warning",
                no_update,
            )

        if not is_connected():
            try:
                url = register_and_connect()
                return (
                    no_update,
                    html.A("Open connection portal", href=url, target="_blank",
                           style={"color": COLOR_PRIMARY, "fontSize": "12px"}),
                    "Open the connection portal link in the sidebar to link your brokerage, then click Load again.",
                    True,
                    "info",
                    no_update,
                )
            except Exception as e:
                return no_update, str(e), f"SnapTrade error: {e}", True, "danger", no_update

        # Already connected — fetch holdings
        try:
            holdings = fetch_holdings()
            if not holdings:
                return no_update, "No holdings found.", "No holdings found in linked accounts.", True, "warning", no_update

            symbols, weights, total_value = holdings_to_portfolio(holdings)

            # Find or create the "Current" portfolio
            current_idx = None
            for i, p in enumerate(state.portfolios):
                if p.title == "Current":
                    current_idx = i
                    break

            new_port = PortfolioSpec(
                assets=symbols,
                weights=weights,
                title="Current",
            )

            if current_idx is not None:
                state.portfolios[current_idx] = new_port
            else:
                state.portfolios.insert(0, new_port)

            n_holdings = len(symbols)
            msg = f"Loaded {n_holdings} holdings (${total_value:,.0f}) into 'Current' portfolio."
            return (version or 0) + 1, f"Connected \u2014 {n_holdings} holdings", msg, True, "success", round(total_value, 2)

        except Exception as e:
            return no_update, f"Error: {e}", f"Failed to fetch holdings: {e}", True, "danger", no_update


def main():
    """Entry point for the application."""
    app = create_app()
    print("Starting FF5 Portfolio Analysis on http://127.0.0.1:8050")
    app.run(debug=True, host="127.0.0.1", port=8050)


if __name__ == "__main__":
    main()
