"""Factor-exposure portfolio optimization."""

from __future__ import annotations

import numpy as np
from scipy.optimize import minimize

from ff5.models import AnalysisResults, OptimOptions, PortfolioSpec


def optim_factor_based(
    portfolio: PortfolioSpec,
    results: AnalysisResults,
    opts: OptimOptions,
) -> PortfolioSpec:
    """Factor-based optimization targeting FF5 factor exposures.

    Objective:
        min  (B'w - t)' P (B'w - t) + lambda * w' Sigma w

    where B = factorBetas (N x 5), t = target exposures,
    P = diag(FactorPenalty), lambda = RiskAversion.
    Only factors with non-NaN targets are included.
    """
    n = portfolio.n_assets
    sigma_annual = results.sigma_annual

    if opts.factor_betas is None:
        raise ValueError("factor_betas (N x 5) is required for factor-based optimization.")

    B = opts.factor_betas  # N x 5
    t_full = opts.factor_targets  # 5
    p_full = opts.factor_penalty  # 5
    lam = opts.risk_aversion

    # Select only factors with finite targets
    valid = ~np.isnan(t_full)
    if not np.any(valid):
        raise ValueError("At least one element of factor_targets must be non-NaN.")

    Bv = B[:, valid]  # N x K
    tv = t_full[valid]  # K
    Pv = np.diag(p_full[valid])  # K x K

    def objective(w):
        dev = Bv.T @ w - tv
        factor_cost = dev @ Pv @ dev
        risk_cost = lam * w @ sigma_annual @ w
        return factor_cost + risk_cost

    def gradient(w):
        dev = Bv.T @ w - tv
        return 2 * Bv @ Pv @ dev + 2 * lam * sigma_annual @ w

    w0 = np.ones(n) / n
    bounds = list(zip(opts.min_weight, opts.max_weight))
    constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]

    result = minimize(
        objective,
        w0,
        jac=gradient,
        method="SLSQP",
        bounds=bounds,
        constraints=constraints,
        options={"maxiter": 1000, "ftol": 1e-12},
    )

    if result.success:
        w = result.x
        w = w / w.sum()
    else:
        w = np.ones(n) / n

    return PortfolioSpec(
        assets=portfolio.assets,
        weights=w.tolist(),
        title=portfolio.title,
        rebalance_cost=portfolio.rebalance_cost,
    )
