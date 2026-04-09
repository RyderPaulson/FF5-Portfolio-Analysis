"""Minimize Conditional Value-at-Risk (Expected Shortfall)."""

from __future__ import annotations

import numpy as np
from scipy.optimize import linprog

from ff5.models import AnalysisResults, OptimOptions, PortfolioSpec


def optim_cvar(
    portfolio: PortfolioSpec,
    results: AnalysisResults,
    opts: OptimOptions,
) -> PortfolioSpec:
    """CVaR optimization via linear programming.

    LP formulation (Rockafellar & Uryasev 2000):
        min   z + 1/(alpha*S) * sum(u_s)
        s.t.  u_s >= -R_s * w - z   for all s
              u_s >= 0
              sum(w) = 1,  lb <= w <= ub

    Decision variables: [w (N); z (1); u (S)]
    """
    n = portfolio.n_assets
    alpha = opts.alpha

    # Scenario returns
    R = opts.scenario_returns
    if R is None:
        R = results.asset_returns
    S, n_cols = R.shape
    assert n_cols == n, f"scenario_returns has {n_cols} cols but portfolio has {n} assets"

    # Decision variable layout: x = [w(n), z(1), u(S)]
    n_vars = n + 1 + S

    # Objective: min 0'w + 1*z + (1/(alpha*S))*1'u
    c = np.zeros(n_vars)
    c[n] = 1.0  # z coefficient
    c[n + 1 :] = 1.0 / (alpha * S)  # u coefficients

    # Inequality: -R*w - z*1 - I*u <= 0
    # i.e. u_s >= -R_s*w - z
    A_ub = np.zeros((S, n_vars))
    A_ub[:, :n] = -R  # -R * w
    A_ub[:, n] = -1.0  # -z
    A_ub[:, n + 1 :] = -np.eye(S)  # -u
    b_ub = np.zeros(S)

    # Equality: sum(w) = 1
    A_eq = np.zeros((1, n_vars))
    A_eq[0, :n] = 1.0
    b_eq = np.array([1.0])

    # Bounds
    lb_full = np.concatenate([opts.min_weight, [-np.inf], np.zeros(S)])
    ub_full = np.concatenate([opts.max_weight, [np.inf], np.full(S, np.inf)])
    bounds = list(zip(lb_full, ub_full))

    result = linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq, bounds=bounds, method="highs")

    if result.success:
        w = result.x[:n]
        w = w / w.sum()  # safety normalization
    else:
        w = np.ones(n) / n

    return PortfolioSpec(
        assets=portfolio.assets,
        weights=w.tolist(),
        title=portfolio.title,
        rebalance_cost=portfolio.rebalance_cost,
    )
