"""Ledoit-Wolf shrinkage toward constant-correlation target."""

from __future__ import annotations

import numpy as np


def ledoit_wolf_shrink(X: np.ndarray) -> tuple[np.ndarray, float]:
    """Ledoit-Wolf shrinkage covariance estimator.

    Parameters
    ----------
    X : (T, N) matrix of asset returns (raw, not demeaned).

    Returns
    -------
    sigma_shrunk : (N, N) shrunk covariance matrix
    delta : optimal shrinkage intensity in [0, 1]
    """
    T, N = X.shape
    X = X - X.mean(axis=0)  # demean
    S = (X.T @ X) / T  # sample covariance

    # Constant-correlation target
    s_vec = np.sqrt(np.diag(S))  # asset std devs
    R = S / np.outer(s_vec, s_vec)  # sample correlation matrix
    r_bar = (R.sum() - N) / (N * (N - 1))  # mean off-diagonal correlation
    F = r_bar * np.outer(s_vec, s_vec)  # target covariance
    np.fill_diagonal(F, np.diag(S))  # keep sample variances on diagonal

    # Optimal shrinkage intensity (Ledoit & Wolf 2004)
    X2 = X**2
    pi_mat = (X2.T @ X2) / T - S**2  # element-wise pi
    pi_sum = pi_mat.sum()

    # rho: asymptotic covariance with the target
    theta_mat = ((X**3).T @ X) / T - np.diag(np.diag(S)) @ R
    rho_off_diag = (r_bar * np.outer(s_vec / s_vec[:, None].ravel(), np.ones(N)) * theta_mat).sum()
    rho_sum = np.diag(pi_mat).sum() + rho_off_diag

    # gamma: squared Frobenius distance
    gamma_sum = np.linalg.norm(S - F, "fro") ** 2

    # Optimal intensity
    kappa = (pi_sum - rho_sum) / gamma_sum
    delta = max(0.0, min(1.0, kappa / T))

    sigma_shrunk = delta * F + (1 - delta) * S
    return sigma_shrunk, delta
