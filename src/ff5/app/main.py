"""Dash application — main entry point."""

from __future__ import annotations

import traceback

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, State, callback, ctx, dcc, html, no_update

from ff5.analytics.analyze import analyze_portfolio
from ff5.app.components.analysis_controls import create_run_button, create_settings_panel
from ff5.app.components.portfolio_editor import (
    create_asset_weight_row,
    create_portfolio_editor_layout,
)
from ff5.app.components.summary_table import create_summary_table
from ff5.app.figures.efficient_frontier import create_efficient_frontier
from ff5.app.figures.factor_exposures import create_factor_exposures
from ff5.app.figures.forecasted_returns import create_forecasted_returns
from ff5.app.figures.historical_drawdown import create_historical_drawdown
from ff5.app.figures.return_distributions import create_return_distributions
from ff5.app.state import state
from ff5.models import Milestone, OptimOptions, PortfolioSpec
from ff5.optimizers.dispatcher import run_optimizer


def create_app() -> dash.Dash:
    """Create and configure the Dash application."""
    app = dash.Dash(
        __name__,
        external_stylesheets=[dbc.themes.FLATLY],
        suppress_callback_exceptions=True,
    )

    app.title = "FF5 Portfolio Analysis"

    # Load saved config
    state.load_from_yaml()

    app.layout = _create_layout()
    _register_callbacks(app)

    return app


def _create_layout() -> dbc.Container:
    return dbc.Container(
        [
            # Header
            dbc.Navbar(
                dbc.Container(
                    [
                        dbc.NavbarBrand(
                            "FF5 Portfolio Analysis",
                            className="fw-bold",
                        ),
                        create_run_button(),
                    ],
                    fluid=True,
                    className="d-flex align-items-center",
                ),
                color="dark",
                dark=True,
                className="mb-3",
            ),
            # Main content
            dbc.Row(
                [
                    # Sidebar
                    dbc.Col(
                        html.Div(
                            [
                                create_portfolio_editor_layout(),
                                create_settings_panel(),
                            ],
                            className="p-3",
                            style={
                                "height": "calc(100vh - 80px)",
                                "overflowY": "auto",
                            },
                        ),
                        width=3,
                        className="bg-light border-end",
                    ),
                    # Main content area
                    dbc.Col(
                        [
                            # Status/loading
                            dbc.Alert(
                                id="status-alert",
                                is_open=False,
                                duration=5000,
                                className="mb-2",
                            ),
                            dcc.Loading(
                                id="loading-indicator",
                                type="default",
                                children=[
                                    dbc.Tabs(
                                        [
                                            dbc.Tab(
                                                html.Div(id="tab-summary"),
                                                label="Summary",
                                            ),
                                            dbc.Tab(
                                                dcc.Graph(id="graph-frontier"),
                                                label="Efficient Frontier",
                                            ),
                                            dbc.Tab(
                                                html.Div([
                                                    dbc.Select(
                                                        id="forecast-portfolio-select",
                                                        options=[],
                                                        value=None,
                                                        className="mb-2",
                                                        style={"maxWidth": "300px"},
                                                    ),
                                                    dcc.Graph(id="graph-forecast"),
                                                ]),
                                                label="Forecasted Returns",
                                            ),
                                            dbc.Tab(
                                                dcc.Graph(id="graph-distributions"),
                                                label="Distributions",
                                            ),
                                            dbc.Tab(
                                                dcc.Graph(id="graph-factors"),
                                                label="Factor Exposures",
                                            ),
                                            dbc.Tab(
                                                dcc.Graph(id="graph-drawdown"),
                                                label="Drawdown",
                                            ),
                                        ],
                                        id="main-tabs",
                                        active_tab="tab-0",
                                    ),
                                ],
                            ),
                        ],
                        width=9,
                        className="p-3",
                    ),
                ],
                className="g-0",
            ),
            # Hidden stores for state synchronization
            dcc.Store(id="store-portfolios-version", data=0),
            dcc.Store(id="store-results-version", data=0),
        ],
        fluid=True,
        className="p-0",
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
        State("portfolio-selector", "value"),
        State("store-portfolios-version", "data"),
        prevent_initial_call=False,
    )
    def manage_portfolios(add_clicks, remove_clicks, selected, version):
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
            # Re-normalize: give new ticker equal share
            n = len(p.weights)
            p.weights = [1.0 / n] * n
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
        return (version or 0) + 1, f"Analysis complete — {n_analyzed} portfolios.", True, "success"

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
        State("store-portfolios-version", "data"),
        prevent_initial_call=True,
    )
    def run_optimization(n_clicks, method, source_idx, rf, version):
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
            opts = OptimOptions(rf=rf or 0.045)
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
    # Update Visualizations
    # ------------------------------------------------------------------ #

    @callback(
        Output("tab-summary", "children"),
        Output("graph-frontier", "figure"),
        Output("graph-forecast", "figure"),
        Output("graph-distributions", "figure"),
        Output("graph-factors", "figure"),
        Output("graph-drawdown", "figure"),
        Output("forecast-portfolio-select", "options"),
        Output("forecast-portfolio-select", "value"),
        Input("store-results-version", "data"),
    )
    def update_visualizations(_version):
        pairs = state.get_analyzed_pairs()
        empty_fig = {"data": [], "layout": {"title": "Run analysis to see results"}}

        if not pairs:
            return (
                html.P("No analysis results yet. Add portfolios and click 'Run All'."),
                empty_fig,
                empty_fig,
                empty_fig,
                empty_fig,
                empty_fig,
                [],
                None,
            )

        results_map = {title: r for title, r in pairs}

        summary = create_summary_table(pairs)

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
        distributions = create_return_distributions(pairs, state.milestones)
        factors = create_factor_exposures(pairs)
        drawdown = create_historical_drawdown(pairs)

        forecast_options = [{"label": title, "value": title} for title, _ in pairs]

        return summary, frontier, forecast, distributions, factors, drawdown, forecast_options, first_title

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


def main():
    """Entry point for the application."""
    app = create_app()
    print("Starting FF5 Portfolio Analysis on http://127.0.0.1:8050")
    app.run(debug=True, host="127.0.0.1", port=8050)


if __name__ == "__main__":
    main()
