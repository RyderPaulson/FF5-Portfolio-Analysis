"""GARCH(1,1) fitting and Monte Carlo simulation."""

from __future__ import annotations

import warnings

import numpy as np
from arch import arch_model


def fit_garch(asset_returns: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Fit GARCH(1,1) model to each asset.

    Parameters
    ----------
    asset_returns : (T, N) array of daily returns

    Returns
    -------
    omega : (N,) GARCH constants
    alpha : (N,) ARCH(1) coefficients
    beta : (N,) GARCH(1) coefficients
    """
    _, n_assets = asset_returns.shape
    omega = np.zeros(n_assets)
    alpha = np.zeros(n_assets)
    beta = np.zeros(n_assets)

    for i in range(n_assets):
        returns_pct = asset_returns[:, i] * 100  # arch expects percentage returns
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            mdl = arch_model(returns_pct, vol="GARCH", p=1, q=1, mean="Zero", rescale=False)
            res = mdl.fit(disp="off")

        # Convert back from percentage scale: omega scaled by 1/10000
        omega[i] = res.params["omega"] / 10000
        alpha[i] = res.params["alpha[1]"]
        beta[i] = res.params["beta[1]"]

    return omega, alpha, beta


def garch_simulate(
    mu_daily: np.ndarray,
    omega: np.ndarray,
    alpha: np.ndarray,
    beta_g: np.ndarray,
    L: np.ndarray,
    weights_norm: np.ndarray,
    total_days: int,
    n_sim: int,
    rng: np.random.Generator | None = None,
) -> np.ndarray:
    """GARCH(1,1) multi-asset Monte Carlo simulation.

    Parameters
    ----------
    mu_daily : (N,) daily expected returns
    omega : (N,) GARCH constants
    alpha : (N,) ARCH(1) coefficients
    beta_g : (N,) GARCH(1) coefficients
    L : (N, N) lower-triangular Cholesky of daily correlation matrix
    weights_norm : (N,) normalized portfolio weights
    total_days : simulation horizon in trading days
    n_sim : number of Monte Carlo paths
    rng : numpy random generator (for reproducibility)

    Returns
    -------
    port_ret_paths : (total_days, n_sim) daily portfolio returns
    """
    if rng is None:
        rng = np.random.default_rng(42)

    n_assets = len(mu_daily)
    unconditional_var = omega / (1 - alpha - beta_g)

    port_ret_paths = np.zeros((total_days, n_sim))
    h_prev = np.tile(unconditional_var[:, np.newaxis], (1, n_sim))  # N x nSim
    e_prev = np.zeros((n_assets, n_sim))

    mu = mu_daily[:, np.newaxis]  # N x 1 for broadcasting

    for t in range(total_days):
        # GARCH(1,1) conditional variance update
        h_curr = (
            omega[:, np.newaxis]
            + alpha[:, np.newaxis] * e_prev**2
            + beta_g[:, np.newaxis] * h_prev
        )

        # Correlated standardised shocks via Cholesky factor
        z_corr = L @ rng.standard_normal((n_assets, n_sim))

        # Scale by conditional std dev, add drift
        innovations = np.sqrt(h_curr) * z_corr
        asset_ret = mu + innovations  # N x nSim

        # Weighted portfolio return
        port_ret_paths[t, :] = weights_norm @ asset_ret

        e_prev = innovations
        h_prev = h_curr

    return port_ret_paths
