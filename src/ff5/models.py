"""Data models for FF5 portfolio analysis."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

import numpy as np


@dataclass
class PortfolioSpec:
    """User-defined portfolio specification (persisted to YAML)."""

    assets: list[str]
    weights: list[float]
    title: str = ""
    rebalance_cost: float = 0.0

    def __post_init__(self):
        if len(self.assets) != len(self.weights):
            raise ValueError(
                f"Assets ({len(self.assets)}) and weights ({len(self.weights)}) "
                "must have the same length."
            )
        total = sum(self.weights)
        if total > 0:
            self.weights = [w / total for w in self.weights]

    @property
    def n_assets(self) -> int:
        return len(self.assets)

    @property
    def is_valid(self) -> bool:
        return (
            len(self.assets) == len(self.weights)
            and not any(np.isnan(w) for w in self.weights)
            and abs(sum(self.weights) - 1.0) < 1e-8
        )

    def cache_key(self, date_str: str) -> str:
        key_str = "+".join(self.assets) + "|" + ",".join(f"{w:.6f}" for w in self.weights)
        h = hashlib.md5(key_str.encode()).hexdigest()[:12]
        return f"port:{h}:{date_str}"

    def to_dict(self) -> dict:
        d = {"assets": self.assets, "weights": self.weights}
        if self.title:
            d["title"] = self.title
        if self.rebalance_cost > 0:
            d["rebalance_cost"] = self.rebalance_cost
        return d

    @classmethod
    def from_dict(cls, d: dict) -> PortfolioSpec:
        return cls(
            assets=d["assets"],
            weights=d["weights"],
            title=d.get("title", ""),
            rebalance_cost=d.get("rebalance_cost", 0.0),
        )


@dataclass
class MilestoneResult:
    name: str
    year: int
    median_growth: float
    pct5: float
    pct95: float
    prob_loss: float
    var5: float
    cvar5: float
    cagr: float
    target_multiples: list[float]
    target_probs: list[float]


@dataclass
class ForecastedReturns:
    t_years: np.ndarray
    pct5: np.ndarray
    pct25: np.ndarray
    pct50: np.ndarray
    pct75: np.ndarray
    pct95: np.ndarray
    sample_paths: np.ndarray | None = None  # (total_days, n_samples) subset of MC paths


@dataclass
class AnalysisResults:
    """Complete analysis output for one portfolio."""

    symbols: list[str]
    weights: list[float]
    factor_betas: np.ndarray  # N x 5
    alphas: np.ndarray  # N x 1
    port_factor_betas: np.ndarray  # 1 x 5
    mu_annual: np.ndarray  # N
    factor_premia_annual: np.ndarray  # 5
    port_mu_annual: float
    port_sigma_annual: float
    sigma_annual: np.ndarray  # N x N
    shrinkage_intensity: float
    garch_params: dict  # {omega, alpha, beta}
    arith_return: float
    geom_return: float
    downside_dev: float
    max_drawdown: float
    sharpe: float
    hist_sharpe: float
    sortino: float
    calmar: float
    hist_drawdown: np.ndarray
    hist_dates: list
    forecasted_returns: ForecastedReturns
    milestones: list[MilestoneResult]
    milestone_vals: list[np.ndarray]
    asset_returns: np.ndarray  # T x N synced returns
    trading_days_per_year: int = 252


@dataclass
class Milestone:
    name: str
    year: int


@dataclass
class AppConfig:
    """Top-level configuration."""

    rf: float = 0.045
    n_simulations: int = 10_000
    horizon_years: int = 44
    milestones: list[Milestone] = field(
        default_factory=lambda: [Milestone("House", 10), Milestone("Retire", 44)]
    )
    milestone_targets: list[float] = field(default_factory=lambda: [3.0, 10.0])
    portfolios: list[PortfolioSpec] = field(default_factory=list)


@dataclass
class OptimOptions:
    """Unified optimizer parameters."""

    # Common
    long_only: bool = True
    min_weight: np.ndarray | None = None
    max_weight: np.ndarray | None = None
    fully_invested: bool = True
    rf: float = 0.045

    # Mean-variance
    target_return: float | None = None
    max_sharpe: bool = True

    # CVaR
    alpha: float = 0.05
    scenario_returns: np.ndarray | None = None

    # Black-Litterman
    tau: float = 0.05
    view_confidence: np.ndarray | None = None
    factor_betas: np.ndarray | None = None
    factor_premia_annual: np.ndarray | None = None
    equilibrium_weights: np.ndarray | None = None

    # Factor-based
    factor_targets: np.ndarray | None = None  # 5-element, NaN = unconstrained
    factor_penalty: np.ndarray = field(default_factory=lambda: np.ones(5))
    risk_aversion: float = 0.5

    def populate_from_results(self, results: AnalysisResults, n_assets: int):
        """Auto-populate fields from analysis results."""
        if self.factor_betas is None:
            self.factor_betas = results.factor_betas
        if self.factor_premia_annual is None:
            self.factor_premia_annual = results.factor_premia_annual
        if self.scenario_returns is None:
            self.scenario_returns = results.asset_returns
        if self.min_weight is None:
            if self.long_only:
                self.min_weight = np.zeros(n_assets)
            else:
                self.min_weight = -np.ones(n_assets)
        if self.max_weight is None:
            self.max_weight = np.ones(n_assets)
        if self.factor_targets is None:
            self.factor_targets = np.full(5, np.nan)
