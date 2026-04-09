"""Risk metric computations."""

from __future__ import annotations

import numpy as np


def compute_risk_metrics(
    port_hist_returns: np.ndarray,
    port_mu_annual: float,
    port_vol_annual: float,
    rf: float,
    trading_days_per_year: int = 252,
) -> dict:
    """Compute risk metrics from historical portfolio returns.

    Returns dict with: arith_return, geom_return, downside_dev,
    max_drawdown, sharpe, hist_sharpe, sortino, calmar,
    hist_drawdown, cum_wealth.
    """
    n_hist = len(port_hist_returns)
    rf_daily = rf / trading_days_per_year

    # Downside deviation
    downside_ret = np.minimum(port_hist_returns - rf_daily, 0)
    downside_dev = np.sqrt(np.mean(downside_ret**2)) * np.sqrt(trading_days_per_year)

    # Drawdown
    cum_wealth = np.cumprod(1 + port_hist_returns)
    running_max = np.maximum.accumulate(cum_wealth)
    drawdown_series = 1 - cum_wealth / running_max
    max_drawdown = drawdown_series.max()

    # Returns
    arith_return = np.mean(port_hist_returns) * trading_days_per_year
    geom_return = np.exp(np.sum(np.log(1 + port_hist_returns)) / n_hist) ** trading_days_per_year - 1

    # Ratios
    sharpe = (port_mu_annual - rf) / port_vol_annual if port_vol_annual > 0 else 0.0
    hist_sharpe = (arith_return - rf) / port_vol_annual if port_vol_annual > 0 else 0.0
    sortino = (port_mu_annual - rf) / downside_dev if downside_dev > 0 else 0.0
    calmar = geom_return / max_drawdown if max_drawdown > 0 else 0.0

    return {
        "arith_return": arith_return,
        "geom_return": geom_return,
        "downside_dev": downside_dev,
        "max_drawdown": max_drawdown,
        "sharpe": sharpe,
        "hist_sharpe": hist_sharpe,
        "sortino": sortino,
        "calmar": calmar,
        "hist_drawdown": drawdown_series,
    }


def compute_milestone_stats(
    paths: np.ndarray,
    milestone_year: int,
    milestone_name: str,
    milestone_targets: list[float],
    trading_days_per_year: int = 252,
) -> dict | None:
    """Compute statistics for a single milestone from simulation paths.

    Parameters
    ----------
    paths : (total_days, n_sim) cumulative wealth paths
    milestone_year : year of the milestone
    milestone_name : label
    milestone_targets : target wealth multiples
    trading_days_per_year : default 252

    Returns
    -------
    dict with milestone statistics, or None if milestone is beyond horizon
    """
    m_idx = milestone_year * trading_days_per_year - 1  # 0-indexed
    total_days = paths.shape[0]

    if m_idx >= total_days:
        return None

    vals = paths[m_idx, :]

    pct5_val = np.percentile(vals, 5)
    target_probs = [(np.mean(vals >= t) * 100) for t in milestone_targets]

    return {
        "name": milestone_name,
        "year": milestone_year,
        "median_growth": float(np.median(vals)),
        "pct5": float(pct5_val),
        "pct95": float(np.percentile(vals, 95)),
        "prob_loss": float(np.mean(vals < 1) * 100),
        "var5": float(1 - pct5_val),
        "cvar5": float(1 - np.mean(vals[vals <= pct5_val])) if np.any(vals <= pct5_val) else 0.0,
        "cagr": float(np.median(vals) ** (1 / milestone_year) - 1),
        "target_multiples": milestone_targets,
        "target_probs": target_probs,
        "vals": vals,
    }
