"""Server-side application state management."""

from __future__ import annotations

from ff5.config import load_config, save_config
from ff5.models import AnalysisResults, AppConfig, Milestone, PortfolioSpec


class AppState:
    """Server-side singleton holding portfolios and analysis results.

    Since this is a single-user local app, a simple in-memory store
    is sufficient. Results are large numpy arrays that shouldn't be
    serialized to browser-side dcc.Store.
    """

    def __init__(self):
        self.config: AppConfig = AppConfig()
        self.results: dict[str, AnalysisResults] = {}

    def load_from_yaml(self):
        """Load portfolios from YAML config file."""
        self.config = load_config()

    def save_to_yaml(self):
        """Save current config to YAML."""
        save_config(self.config)

    @property
    def portfolios(self) -> list[PortfolioSpec]:
        return self.config.portfolios

    @portfolios.setter
    def portfolios(self, value: list[PortfolioSpec]):
        self.config.portfolios = value

    @property
    def milestones(self) -> list[Milestone]:
        return self.config.milestones

    def add_portfolio(self, portfolio: PortfolioSpec):
        self.config.portfolios.append(portfolio)

    def remove_portfolio(self, index: int):
        if 0 <= index < len(self.config.portfolios):
            title = self.config.portfolios[index].title
            del self.config.portfolios[index]
            self.results.pop(title, None)

    def update_portfolio(self, index: int, portfolio: PortfolioSpec):
        if 0 <= index < len(self.config.portfolios):
            old_title = self.config.portfolios[index].title
            self.results.pop(old_title, None)
            self.config.portfolios[index] = portfolio

    def set_result(self, title: str, result: AnalysisResults):
        self.results[title] = result

    def get_result(self, title: str) -> AnalysisResults | None:
        return self.results.get(title)

    def get_analyzed_pairs(self) -> list[tuple[str, AnalysisResults]]:
        """Return list of (title, results) for all analyzed portfolios."""
        pairs = []
        for p in self.portfolios:
            r = self.results.get(p.title)
            if r is not None:
                pairs.append((p.title, r))
        return pairs

    def clear_results(self):
        self.results.clear()


# Module-level singleton
state = AppState()
