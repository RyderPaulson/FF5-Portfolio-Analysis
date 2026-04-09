"""Risk-parity (equal risk contribution) optimization."""

from __future__ import annotations

import numpy as np
from scipy.optimize import minimize

from ff5.models import AnalysisResults, OptimOptions, PortfolioSpec


def optim_risk_parity(
    portfolio: PortfolioSpec,
    results: AnalysisResults,
    opts: OptimOptions,
) -> PortfolioSpec:
    """Risk-parity optimization using Spinu (2013) convex formulation.

    min  0.5 y' Sigma y - c * sum(log(y))
    s.t. y > 0
    then w = y / sum(y).
    """
    n = portfolio.n_assets
    sigma_annual = results.sigma_annual
    c = 1.0  # barrier parameter

    def objective(y):
        return 0.5 * y @ sigma_annual @ y - c * np.sum(np.log(np.maximum(y, 1e-20)))

    def gradient(y):
        return sigma_annual @ y - c / np.maximum(y, 1e-20)

    y0 = np.ones(n)
    bounds = [(1e-8, None)] * n

    result = minimize(
        objective,
        y0,
        jac=gradient,
        method="L-BFGS-B",
        bounds=bounds,
        options={"maxiter": 1000, "ftol": 1e-15},
    )

    if result.success:
        w = result.x / result.x.sum()
    else:
        w = np.ones(n) / n

    return PortfolioSpec(
        assets=portfolio.assets,
        weights=w.tolist(),
        title=portfolio.title,
        rebalance_cost=portfolio.rebalance_cost,
    )
