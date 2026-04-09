"""Efficient frontier plot with portfolio scatter overlays."""

from __future__ import annotations

import numpy as np
import plotly.graph_objects as go

from ff5.analytics.covariance import ledoit_wolf_shrink
from ff5.analytics.regression import ff5_regression
from ff5.app.theme import FIGURE_LAYOUT, get_color
from ff5.data.ff5_loader import load_ff5
from ff5.models import AnalysisResults, PortfolioSpec
from ff5.optimizers.mean_variance import optim_mean_variance
from ff5.models import OptimOptions

TRADING_DAYS_PER_YEAR = 252


def create_efficient_frontier(
    portfolios: list[PortfolioSpec],
    results_map: dict[str, AnalysisResults],
    *,
    rf: float = 0.045,
    n_points: int = 50,
    prices_df=None,
) -> go.Figure:
    """Build efficient frontier from the union of all assets across portfolios.

    Parameters
    ----------
    portfolios : list of PortfolioSpec
    results_map : dict mapping portfolio title -> AnalysisResults
    rf : risk-free rate
    n_points : frontier grid resolution
    prices_df : pre-loaded prices DataFrame (optional, for performance)
    """
    fig = go.Figure()

    # Collect all unique symbols and their data from results
    all_symbols = []
    for p in portfolios:
        all_symbols.extend(p.assets)
    all_symbols = list(dict.fromkeys(all_symbols))  # unique, order-preserving

    # Get first result that has asset_returns and factor data
    first_result = next(iter(results_map.values()))

    # Build the frontier using a combined asset universe
    # Use data from results to construct the frontier
    ff5 = load_ff5()
    full_factors = ff5[["MktRF", "SMB", "HML", "RMW", "CMA"]].values
    factor_premia_ann = full_factors.mean(axis=0) * TRADING_DAYS_PER_YEAR

    # Aggregate factor betas and covariance across all portfolios' assets
    # Build a mapping from symbol -> (betas, index_in_result)
    symbol_betas = {}
    symbol_returns = {}
    for p in portfolios:
        r = results_map.get(p.title)
        if r is None:
            continue
        for i, sym in enumerate(r.symbols):
            if sym not in symbol_betas:
                symbol_betas[sym] = r.factor_betas[i]
                symbol_returns[sym] = r.asset_returns[:, i]

    # Build combined arrays for frontier
    frontier_symbols = [s for s in all_symbols if s in symbol_betas]
    n_frontier = len(frontier_symbols)

    if n_frontier < 2:
        # Can't build a frontier with < 2 assets; just plot portfolios
        _add_portfolio_markers(fig, portfolios, results_map)
        fig.update_layout(**FIGURE_LAYOUT, title="Portfolio Risk vs Return")
        return fig

    betas_arr = np.array([symbol_betas[s] for s in frontier_symbols])
    mu_ann = rf + betas_arr @ factor_premia_ann

    # Build returns matrix for covariance
    min_len = min(len(symbol_returns[s]) for s in frontier_symbols)
    returns_matrix = np.column_stack(
        [symbol_returns[s][:min_len] for s in frontier_symbols]
    )
    sigma_daily, _ = ledoit_wolf_shrink(returns_matrix)
    sigma_ann = sigma_daily * TRADING_DAYS_PER_YEAR

    # Sweep the frontier
    target_rets = np.linspace(mu_ann.min(), mu_ann.max(), n_points)
    frontier_risk = []
    frontier_ret = []

    # Create a temporary portfolio and results for optimization
    temp_portfolio = PortfolioSpec(
        assets=frontier_symbols,
        weights=[1.0 / n_frontier] * n_frontier,
    )
    temp_results = AnalysisResults(
        symbols=frontier_symbols,
        weights=[1.0 / n_frontier] * n_frontier,
        factor_betas=betas_arr,
        alphas=np.zeros(n_frontier),
        port_factor_betas=np.zeros(5),
        mu_annual=mu_ann,
        factor_premia_annual=factor_premia_ann,
        port_mu_annual=0,
        port_sigma_annual=0,
        sigma_annual=sigma_ann,
        shrinkage_intensity=0,
        garch_params={},
        arith_return=0,
        geom_return=0,
        downside_dev=0,
        max_drawdown=0,
        sharpe=0,
        hist_sharpe=0,
        sortino=0,
        calmar=0,
        hist_drawdown=np.array([]),
        hist_dates=[],
        forecasted_returns=None,
        milestones=[],
        milestone_vals=[],
        asset_returns=returns_matrix,
    )

    for target in target_rets:
        opts = OptimOptions(rf=rf, max_sharpe=False, target_return=target)
        opts.populate_from_results(temp_results, n_frontier)
        try:
            opt_port = optim_mean_variance(temp_portfolio, temp_results, opts)
            w = np.array(opt_port.weights)
            ret = float(w @ mu_ann * 100)
            risk = float(np.sqrt(w @ sigma_ann @ w) * 100)
            frontier_risk.append(risk)
            frontier_ret.append(ret)
        except Exception:
            continue

    if frontier_risk:
        fig.add_trace(
            go.Scatter(
                x=frontier_risk,
                y=frontier_ret,
                mode="lines",
                name="Efficient Frontier",
                line=dict(color="#999999", width=2),
            )
        )

    _add_portfolio_markers(fig, portfolios, results_map)

    # Focus axes on portfolios
    port_risks = []
    port_returns = []
    for p in portfolios:
        r = results_map.get(p.title)
        if r:
            port_risks.append(r.port_sigma_annual * 100)
            port_returns.append(r.port_mu_annual * 100)

    fig.update_layout(
        **FIGURE_LAYOUT,
        title="Portfolio Risk vs Return — Efficient Frontier",
        xaxis_title="Risk — Annualized Volatility (%)",
        yaxis_title="Expected Annual Return (%)",
    )

    return fig


def _add_portfolio_markers(
    fig: go.Figure,
    portfolios: list[PortfolioSpec],
    results_map: dict[str, AnalysisResults],
):
    for i, p in enumerate(portfolios):
        r = results_map.get(p.title)
        if r is None:
            continue
        fig.add_trace(
            go.Scatter(
                x=[r.port_sigma_annual * 100],
                y=[r.port_mu_annual * 100],
                mode="markers",
                name=p.title or f"Portfolio {i + 1}",
                marker=dict(size=12, color=get_color(i)),
            )
        )
