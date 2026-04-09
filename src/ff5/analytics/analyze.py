"""Main analysis orchestrator — equivalent of analyzePortfolio.m."""

from __future__ import annotations

import numpy as np
import pandas as pd

from ff5.analytics.covariance import ledoit_wolf_shrink
from ff5.analytics.garch import fit_garch, garch_simulate
from ff5.analytics.regression import ff5_regression
from ff5.analytics.risk_metrics import compute_milestone_stats, compute_risk_metrics
from ff5.data.cache import (
    get_cached_results,
    load_or_fetch_bars,
    save_results,
)
from ff5.data.ff5_loader import load_ff5
from ff5.models import (
    AnalysisResults,
    ForecastedReturns,
    Milestone,
    MilestoneResult,
    PortfolioSpec,
)

TRADING_DAYS_PER_YEAR = 252


def analyze_portfolio(
    portfolio: PortfolioSpec,
    *,
    rf: float = 0.045,
    n_simulations: int = 10_000,
    horizon_years: int = 44,
    milestones: list[Milestone] | None = None,
    milestone_targets: list[float] | None = None,
    use_cache: bool = True,
    verbose: bool = False,
) -> AnalysisResults:
    """Run full FF5 factor analysis, GARCH Monte Carlo, and risk metrics.

    Parameters
    ----------
    portfolio : PortfolioSpec with assets and weights
    rf : annualized risk-free rate
    n_simulations : number of Monte Carlo paths
    horizon_years : simulation horizon in years
    milestones : list of Milestone(name, year)
    milestone_targets : wealth multiples for probability estimates
    use_cache : whether to use/save result cache
    verbose : print progress

    Returns
    -------
    AnalysisResults dataclass with all computed metrics
    """
    if milestones is None:
        milestones = [Milestone("House", 10), Milestone("Retire", 44)]
    if milestone_targets is None:
        milestone_targets = [3.0, 10.0]

    symbols = portfolio.assets
    weights = np.array(portfolio.weights)
    n_assets = portfolio.n_assets

    # Level-2 cache check
    if use_cache:
        cached = get_cached_results(portfolio)
        if cached is not None:
            if verbose:
                print("  [cache] Portfolio results loaded from cache.")
            return cached

    # Data Download (Level-1 cache via load_or_fetch_bars)
    prices = load_or_fetch_bars(symbols)

    # Compute returns
    returns = prices.pct_change().dropna()
    asset_returns = returns[symbols].values
    return_dates = returns.index

    # Drop rows with any NaN
    valid_mask = ~np.any(np.isnan(asset_returns), axis=1)
    asset_returns = asset_returns[valid_mask]
    return_dates = return_dates[valid_mask]

    if verbose:
        print(
            f"  Usable observations: {len(asset_returns)} "
            f"({len(asset_returns) / TRADING_DAYS_PER_YEAR:.1f} years)"
        )

    # Fama-French 5-Factor Expected Returns
    ff5 = load_ff5()

    # Synchronize asset returns with FF5 factors by date
    return_dates_day = return_dates.normalize()
    asset_df = pd.DataFrame(
        asset_returns,
        index=return_dates_day,
        columns=[f"Asset{i}" for i in range(n_assets)],
    )
    # Remove duplicate dates (keep last)
    asset_df = asset_df[~asset_df.index.duplicated(keep="last")]
    ff5_nodups = ff5[~ff5.index.duplicated(keep="last")]

    sync_df = asset_df.join(ff5_nodups, how="inner")
    sync_df = sync_df.dropna()

    asset_ret_sync = sync_df[[f"Asset{i}" for i in range(n_assets)]].values
    factor_matrix = sync_df[["MktRF", "SMB", "HML", "RMW", "CMA"]].values
    rf_daily_vec = sync_df["RF"].values
    sync_dates = sync_df.index.tolist()

    # OLS regression
    factor_betas, alphas = ff5_regression(asset_ret_sync, factor_matrix, rf_daily_vec)

    # Expected returns using long-run factor premia
    full_factors = ff5[["MktRF", "SMB", "HML", "RMW", "CMA"]].values
    factor_premia_daily = full_factors.mean(axis=0)
    factor_premia_annual = factor_premia_daily * TRADING_DAYS_PER_YEAR
    mu_annual = rf + factor_betas @ factor_premia_annual
    mu_daily = mu_annual / TRADING_DAYS_PER_YEAR

    # Portfolio factor exposures
    port_factor_betas = weights @ factor_betas

    # Ledoit-Wolf Shrinkage Covariance
    sigma_daily, shrinkage_intensity = ledoit_wolf_shrink(asset_ret_sync)

    if verbose:
        print(f"  Ledoit-Wolf shrinkage intensity: {shrinkage_intensity:.4f}")

    # Portfolio-level moments
    port_mu_annual = float(weights @ mu_annual)
    sigma_annual = sigma_daily * TRADING_DAYS_PER_YEAR
    port_sigma_annual = float(np.sqrt(weights @ sigma_annual @ weights))

    # GARCH(1,1) fitting
    total_days = horizon_years * TRADING_DAYS_PER_YEAR
    omega, alpha_g, beta_g = fit_garch(asset_ret_sync)

    if verbose:
        print("\n  GARCH(1,1) Parameters:")
        for i, sym in enumerate(symbols):
            print(f"  {sym:6s} omega={omega[i]:.6f} alpha={alpha_g[i]:.6f} beta={beta_g[i]:.6f}")

    # Correlation matrix for correlated shocks
    D = np.sqrt(np.diag(sigma_daily))
    corr_matrix = sigma_daily / np.outer(D, D)
    # Ensure positive definite
    eigvals = np.linalg.eigvalsh(corr_matrix)
    if eigvals.min() < 1e-10:
        corr_matrix += np.eye(n_assets) * (1e-10 - eigvals.min())
    L = np.linalg.cholesky(corr_matrix)

    # Monte Carlo simulation
    rng = np.random.default_rng(42)
    port_ret_paths = garch_simulate(
        mu_daily, omega, alpha_g, beta_g, L, weights, total_days, n_simulations, rng
    )

    # Cumulative wealth paths
    initial_value = 1 - portfolio.rebalance_cost
    paths = initial_value * np.cumprod(1 + port_ret_paths, axis=0)
    t_years = np.arange(1, total_days + 1) / TRADING_DAYS_PER_YEAR

    # Fan-chart percentiles
    pct5 = np.percentile(paths, 5, axis=1)
    pct25 = np.percentile(paths, 25, axis=1)
    pct50 = np.percentile(paths, 50, axis=1)
    pct75 = np.percentile(paths, 75, axis=1)
    pct95 = np.percentile(paths, 95, axis=1)

    # Save a small sample of MC paths for visualization
    n_sample = min(10, n_simulations)
    sample_idx = rng.choice(n_simulations, size=n_sample, replace=False)
    sample_paths = paths[:, sample_idx]

    # Historical risk metrics
    port_hist_returns = asset_ret_sync @ weights
    metrics = compute_risk_metrics(
        port_hist_returns, port_mu_annual, port_sigma_annual, rf, TRADING_DAYS_PER_YEAR
    )

    # Milestone statistics
    milestone_results = []
    milestone_vals_list = []
    for m in milestones:
        stats = compute_milestone_stats(
            paths, m.year, m.name, milestone_targets, TRADING_DAYS_PER_YEAR
        )
        if stats is not None:
            milestone_results.append(
                MilestoneResult(
                    name=stats["name"],
                    year=stats["year"],
                    median_growth=stats["median_growth"],
                    pct5=stats["pct5"],
                    pct95=stats["pct95"],
                    prob_loss=stats["prob_loss"],
                    var5=stats["var5"],
                    cvar5=stats["cvar5"],
                    cagr=stats["cagr"],
                    target_multiples=stats["target_multiples"],
                    target_probs=stats["target_probs"],
                )
            )
            milestone_vals_list.append(stats["vals"])

    n_hist = len(port_hist_returns)
    results = AnalysisResults(
        symbols=symbols,
        weights=portfolio.weights,
        factor_betas=factor_betas,
        alphas=alphas,
        port_factor_betas=port_factor_betas,
        mu_annual=mu_annual,
        factor_premia_annual=factor_premia_annual,
        port_mu_annual=port_mu_annual,
        port_sigma_annual=port_sigma_annual,
        sigma_annual=sigma_annual,
        shrinkage_intensity=shrinkage_intensity,
        garch_params={"omega": omega, "alpha": alpha_g, "beta": beta_g},
        arith_return=metrics["arith_return"],
        geom_return=metrics["geom_return"],
        downside_dev=metrics["downside_dev"],
        max_drawdown=metrics["max_drawdown"],
        sharpe=metrics["sharpe"],
        hist_sharpe=metrics["hist_sharpe"],
        sortino=metrics["sortino"],
        calmar=metrics["calmar"],
        hist_drawdown=metrics["hist_drawdown"],
        hist_dates=sync_dates[:n_hist],
        forecasted_returns=ForecastedReturns(
            t_years=t_years,
            pct5=pct5,
            pct25=pct25,
            pct50=pct50,
            sample_paths=sample_paths,
            pct75=pct75,
            pct95=pct95,
        ),
        milestones=milestone_results,
        milestone_vals=milestone_vals_list,
        asset_returns=asset_ret_sync,
    )

    # Save to Level-2 cache
    if use_cache:
        save_results(portfolio, results)

    return results
