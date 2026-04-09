"""Black-Litterman portfolio optimization with FF5 factor views."""

from __future__ import annotations

import numpy as np

from ff5.models import AnalysisResults, OptimOptions, PortfolioSpec
from ff5.optimizers.mean_variance import optim_mean_variance


def optim_black_litterman(
    portfolio: PortfolioSpec,
    results: AnalysisResults,
    opts: OptimOptions,
) -> PortfolioSpec:
    """Black-Litterman optimization.

    Combines market-equilibrium returns with FF5 factor-model views
    to produce posterior expected returns, then optimizes via mean-variance.
    """
    n = portfolio.n_assets
    rf = opts.rf
    mu_annual = results.mu_annual
    sigma_annual = results.sigma_annual

    if opts.factor_betas is None or opts.factor_premia_annual is None:
        raise ValueError("factor_betas and factor_premia_annual are required for Black-Litterman.")

    B = opts.factor_betas  # N x 5
    tau = opts.tau

    # Equilibrium weights
    if opts.equilibrium_weights is not None:
        w_eq = np.array(opts.equilibrium_weights)
        w_eq = w_eq / w_eq.sum()
    else:
        w_eq = np.ones(n) / n

    # Implied risk-aversion & equilibrium returns
    port_var = w_eq @ sigma_annual @ w_eq
    port_mu = w_eq @ mu_annual
    delta = (port_mu - rf) / port_var
    Pi = delta * sigma_annual @ w_eq  # N equilibrium excess returns

    # Views from FF5
    P = B.T  # 5 x N
    Q = opts.factor_premia_annual  # 5

    # View uncertainty (Omega)
    if opts.view_confidence is not None:
        conf = np.array(opts.view_confidence)
    else:
        conf = np.ones(len(Q))

    tau_sigma = tau * sigma_annual
    view_var = np.diag(P @ tau_sigma @ P.T)

    # Idzorek-style: Omega = diag(viewVar * (1-conf)/conf)
    conf = np.clip(conf, 1e-6, 1 - 1e-6)
    Omega = np.diag(view_var * (1 - conf) / conf)

    # BL posterior
    M1 = np.linalg.solve(tau_sigma, np.eye(n))
    Omega_inv = np.linalg.solve(Omega, np.eye(len(Q)))
    M2 = P.T @ Omega_inv @ P

    mu_BL = np.linalg.solve(M1 + M2, M1 @ Pi + P.T @ Omega_inv @ Q)
    mu_BL = mu_BL + rf  # shift to absolute returns

    # Create modified results with BL returns for mean-variance optimization
    from dataclasses import replace

    bl_results = replace(results, mu_annual=mu_BL, sigma_annual=sigma_annual)

    bl_opts = OptimOptions(
        long_only=opts.long_only,
        min_weight=opts.min_weight,
        max_weight=opts.max_weight,
        fully_invested=opts.fully_invested,
        rf=opts.rf,
        max_sharpe=True,
    )

    port_out = optim_mean_variance(portfolio, bl_results, bl_opts)
    return PortfolioSpec(
        assets=port_out.assets,
        weights=port_out.weights,
        title=portfolio.title,
        rebalance_cost=portfolio.rebalance_cost,
    )
