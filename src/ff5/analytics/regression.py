"""OLS factor regression for FF5 model."""

from __future__ import annotations

import numpy as np


def ff5_regression(
    asset_returns: np.ndarray,
    factor_matrix: np.ndarray,
    rf_daily: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Run OLS regression of excess asset returns on FF5 factors.

    Parameters
    ----------
    asset_returns : (T, N) array of asset daily returns
    factor_matrix : (T, 5) array of [MktRF, SMB, HML, RMW, CMA]
    rf_daily : (T,) array of daily risk-free rates

    Returns
    -------
    factor_betas : (N, 5) factor loadings
    alphas : (N,) regression intercepts
    """
    n_obs, n_assets = asset_returns.shape
    X = np.column_stack([np.ones(n_obs), factor_matrix])  # T x 6

    factor_betas = np.zeros((n_assets, 5))
    alphas = np.zeros(n_assets)

    for i in range(n_assets):
        excess_ret = asset_returns[:, i] - rf_daily
        coeffs, _, _, _ = np.linalg.lstsq(X, excess_ret, rcond=None)
        alphas[i] = coeffs[0]
        factor_betas[i, :] = coeffs[1:6]

    return factor_betas, alphas
