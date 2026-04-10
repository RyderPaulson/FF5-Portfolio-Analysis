"""Efficient frontier plot with portfolio scatter overlays."""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from scipy.optimize import minimize

from ff5.analytics.covariance import ledoit_wolf_shrink
from ff5.app.theme import FIGURE_LAYOUT, get_color
from ff5.data.ff5_loader import load_ff5
from ff5.models import AnalysisResults, PortfolioSpec

TRADING_DAYS_PER_YEAR = 252


def _compute_frontier(
    mu: np.ndarray,
    sigma: np.ndarray,
    n_points: int = 200,
) -> tuple[np.ndarray, np.ndarray]:
    """Compute the efficient frontier via minimum-variance sweep.

    Uses quadratic optimization with tight tolerances for a smooth curve.
    Returns (risks, returns) arrays in raw (decimal) units.
    """
    n = len(mu)
    bounds = [(0.0, 1.0)] * n
    w0 = np.ones(n) / n
    sum_constraint = {"type": "eq", "fun": lambda w: np.sum(w) - 1.0}

    # Find the global minimum-variance portfolio
    def port_var(w):
        return 0.5 * w @ sigma @ w

    res_gmv = minimize(port_var, w0, method="SLSQP", bounds=bounds,
                       constraints=[sum_constraint], options={"maxiter": 2000, "ftol": 1e-14})
    gmv_ret = float(res_gmv.x @ mu) if res_gmv.success else mu.min()

    # Sweep from GMV return up to max achievable return
    target_rets = np.linspace(gmv_ret, mu.max(), n_points)
    frontier_risk = []
    frontier_ret = []

    for target in target_rets:
        constraints = [
            sum_constraint,
            {"type": "eq", "fun": lambda w, t=target: w @ mu - t},
        ]
        res = minimize(port_var, w0, method="SLSQP", bounds=bounds,
                       constraints=constraints, options={"maxiter": 2000, "ftol": 1e-14})
        if res.success:
            w = res.x
            risk = float(np.sqrt(w @ sigma @ w))
            ret = float(w @ mu)
            frontier_risk.append(risk)
            frontier_ret.append(ret)

    return np.array(frontier_risk), np.array(frontier_ret)


def _find_tangency_portfolio(
    mu: np.ndarray,
    sigma: np.ndarray,
    rf: float,
) -> tuple[float, float] | None:
    """Find the tangency (max Sharpe) portfolio. Returns (risk, return) or None."""
    n = len(mu)
    bounds = [(0.0, 1.0)] * n
    w0 = np.ones(n) / n

    def neg_sharpe(w):
        vol = np.sqrt(w @ sigma @ w)
        return -(w @ mu - rf) / vol if vol > 1e-12 else 0.0

    res = minimize(neg_sharpe, w0, method="SLSQP", bounds=bounds,
                   constraints=[{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}],
                   options={"maxiter": 2000, "ftol": 1e-14})
    if res.success:
        w = res.x
        return float(np.sqrt(w @ sigma @ w)), float(w @ mu)
    return None


def create_efficient_frontier(
    portfolios: list[PortfolioSpec],
    results_map: dict[str, AnalysisResults],
    *,
    rf: float = 0.045,
    n_points: int = 200,
    prices_df=None,
) -> go.Figure:
    """Build efficient frontier from the union of all assets across portfolios."""
    fig = go.Figure()

    # Collect all unique symbols
    all_symbols = []
    for p in portfolios:
        all_symbols.extend(p.assets)
    all_symbols = list(dict.fromkeys(all_symbols))

    # Factor premia from full FF5 history
    ff5 = load_ff5()
    full_factors = ff5[["MktRF", "SMB", "HML", "RMW", "CMA"]].values
    factor_premia_ann = full_factors.mean(axis=0) * TRADING_DAYS_PER_YEAR

    # Aggregate factor betas and date-aligned returns across all portfolios' assets
    symbol_betas = {}
    symbol_return_series = {}
    for p in portfolios:
        r = results_map.get(p.title)
        if r is None:
            continue
        dates = r.hist_dates
        for i, sym in enumerate(r.symbols):
            if sym not in symbol_betas:
                symbol_betas[sym] = r.factor_betas[i]
                symbol_return_series[sym] = pd.Series(
                    r.asset_returns[:, i], index=dates, name=sym,
                )

    frontier_symbols = [s for s in all_symbols if s in symbol_betas]
    n_frontier = len(frontier_symbols)

    if n_frontier < 2:
        _add_portfolio_markers(fig, portfolios, results_map)
        fig.update_layout(**FIGURE_LAYOUT, title="Portfolio Risk vs Return")
        return fig

    betas_arr = np.array([symbol_betas[s] for s in frontier_symbols])
    mu_ann = rf + betas_arr @ factor_premia_ann

    # Inner-join on dates so all columns share the same time periods
    aligned = pd.concat(
        [symbol_return_series[s] for s in frontier_symbols], axis=1, join="inner",
    ).dropna()
    returns_matrix = aligned.values
    sigma_daily, _ = ledoit_wolf_shrink(returns_matrix)
    sigma_ann = sigma_daily * TRADING_DAYS_PER_YEAR

    # Compute the risky-asset efficient frontier
    frontier_risk, frontier_ret = _compute_frontier(mu_ann, sigma_ann, n_points)

    # Compute Capital Market Line (risk-free to tangency portfolio)
    tangency = _find_tangency_portfolio(mu_ann, sigma_ann, rf)

    frontier_risk_pct = frontier_risk * 100
    frontier_ret_pct = frontier_ret * 100

    if frontier_risk_pct.size > 0:
        fig.add_trace(
            go.Scatter(
                x=frontier_risk_pct.tolist(),
                y=frontier_ret_pct.tolist(),
                mode="lines",
                name="Efficient Frontier",
                line=dict(color="#8A8473", width=2),
            )
        )

    if tangency is not None:
        tang_risk, tang_ret = tangency
        # Extend the CML from risk=0 past the tangency portfolio
        cml_x_max = tang_risk * 1.5
        cml_slope = (tang_ret - rf) / tang_risk
        cml_x = [0, cml_x_max * 100]
        cml_y = [rf * 100, (rf + cml_slope * cml_x_max) * 100]
        fig.add_trace(
            go.Scatter(
                x=cml_x,
                y=cml_y,
                mode="lines",
                name="Capital Market Line",
                line=dict(color="#5A8EAE", width=2, dash="dash"),
            )
        )

    _add_portfolio_markers(fig, portfolios, results_map)

    # Focus axes tightly around portfolio markers
    port_x = []
    port_y = []
    for p in portfolios:
        r = results_map.get(p.title)
        if r:
            port_x.append(r.port_sigma_annual * 100)
            port_y.append(r.port_mu_annual * 100)

    layout_overrides = {}
    if port_x and port_y:
        x_pad = (max(port_x) - min(port_x)) * 0.15 or 1.0
        x_min = min(frontier_risk_pct) - x_pad if frontier_risk_pct.size > 0 else min(port_x) - x_pad
        layout_overrides["xaxis_range"] = [x_min, max(port_x) + x_pad]

        # Vertical range: include the frontier curve within the x-axis window
        x_max_visible = max(port_x) + x_pad
        visible_frontier_y = frontier_ret_pct[frontier_risk_pct <= x_max_visible].tolist() if frontier_risk_pct.size > 0 else []
        all_y = port_y + visible_frontier_y + [rf * 100]
        y_pad = (max(all_y) - min(all_y)) * 0.10 or 1.0
        layout_overrides["yaxis_range"] = [min(all_y) - y_pad, max(all_y) + y_pad]

    fig.update_layout(
        **FIGURE_LAYOUT,
        **layout_overrides,
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
