"""Optimizer dispatcher — run any optimizer by name."""

from __future__ import annotations

from ff5.models import AnalysisResults, OptimOptions, PortfolioSpec
from ff5.optimizers.black_litterman import optim_black_litterman
from ff5.optimizers.cvar import optim_cvar
from ff5.optimizers.factor_based import optim_factor_based
from ff5.optimizers.mean_variance import optim_mean_variance
from ff5.optimizers.risk_parity import optim_risk_parity

OPTIMIZERS = {
    "meanvariance": optim_mean_variance,
    "cvar": optim_cvar,
    "blacklitterman": optim_black_litterman,
    "riskparity": optim_risk_parity,
    "factorbased": optim_factor_based,
}

OPTIMIZER_LABELS = {
    "meanvariance": "Mean-Variance",
    "cvar": "CVaR",
    "blacklitterman": "Black-Litterman",
    "riskparity": "Risk Parity",
    "factorbased": "Factor-Based",
}


def run_optimizer(
    method: str,
    portfolio: PortfolioSpec,
    results: AnalysisResults,
    opts: OptimOptions | None = None,
) -> PortfolioSpec:
    """Run an optimizer by name.

    Parameters
    ----------
    method : one of "meanvariance", "cvar", "blacklitterman", "riskparity", "factorbased"
    portfolio : input portfolio
    results : analysis results for the portfolio
    opts : optimizer options (defaults populated if None)

    Returns
    -------
    PortfolioSpec with optimized weights
    """
    method_key = method.lower().replace("-", "").replace("_", "")

    if method_key not in OPTIMIZERS:
        valid = ", ".join(OPTIMIZERS.keys())
        raise ValueError(f'Unknown optimizer "{method}". Valid options: {valid}')

    if opts is None:
        opts = OptimOptions()
    opts.populate_from_results(results, portfolio.n_assets)

    return OPTIMIZERS[method_key](portfolio, results, opts)
