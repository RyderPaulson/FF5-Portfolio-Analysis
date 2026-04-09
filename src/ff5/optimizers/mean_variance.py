"""Mean-variance (Markowitz) portfolio optimization."""

from __future__ import annotations

import numpy as np
from scipy.optimize import minimize

from ff5.models import AnalysisResults, OptimOptions, PortfolioSpec


def optim_mean_variance(
    portfolio: PortfolioSpec,
    results: AnalysisResults,
    opts: OptimOptions,
) -> PortfolioSpec:
    """Mean-variance portfolio optimization.

    Two modes:
    - opts.max_sharpe = True: maximize Sharpe ratio (default)
    - opts.max_sharpe = False: minimize variance for opts.target_return
    """
    n = portfolio.n_assets
    mu = results.mu_annual
    sigma = results.sigma_annual
    rf = opts.rf

    lb = opts.min_weight
    ub = opts.max_weight

    bounds = list(zip(lb, ub))
    w0 = np.ones(n) / n

    if opts.max_sharpe:
        # Maximize Sharpe = (w'mu - Rf) / sqrt(w'Sigma w)
        # Equivalent to minimize negative Sharpe
        def neg_sharpe(w):
            port_ret = w @ mu
            port_vol = np.sqrt(w @ sigma @ w)
            return -(port_ret - rf) / port_vol if port_vol > 1e-12 else 0.0

        constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]

        result = minimize(
            neg_sharpe,
            w0,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
            options={"maxiter": 1000, "ftol": 1e-12},
        )

        if result.success:
            w = result.x
        else:
            w = np.ones(n) / n

    else:
        # Minimize variance for a target return
        target_ret = opts.target_return
        if target_ret is None:
            raise ValueError("max_sharpe is False but no target_return specified.")

        def portfolio_var(w):
            return 0.5 * w @ sigma @ w

        constraints = [
            {"type": "eq", "fun": lambda w: np.sum(w) - 1.0},
            {"type": "eq", "fun": lambda w: w @ mu - target_ret},
        ]

        result = minimize(
            portfolio_var,
            w0,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
            options={"maxiter": 1000, "ftol": 1e-12},
        )

        if result.success:
            w = result.x
        else:
            w = np.ones(n) / n

    # Safety normalization
    w = w / w.sum()

    return PortfolioSpec(
        assets=portfolio.assets,
        weights=w.tolist(),
        title=portfolio.title,
        rebalance_cost=portfolio.rebalance_cost,
    )
