# FF5 Portfolio Analysis

A portfolio analysis and optimization tool built on the **Fama-French 5-Factor Model**. Define portfolios, run factor regressions, simulate future returns with GARCH-based Monte Carlo, and compare risk-adjusted performance across strategies.

## Features

- **FF5 Factor Regression** — OLS regression of asset excess returns against Mkt-RF, SMB, HML, RMW, and CMA factors, using the full Kenneth French data library (back to 1963)
- **Expected Returns** — Factor-model-implied expected returns using long-run factor premia (alpha intentionally dropped — only compensated factor exposures)
- **Covariance Estimation** — Ledoit-Wolf shrinkage toward a constant-correlation target for stable, invertible covariance matrices
- **GARCH(1,1) Monte Carlo** — 10,000-path simulation with time-varying volatility and correlated shocks via Cholesky decomposition
- **Risk Metrics** — Sharpe, Sortino, Calmar ratios; max drawdown; VaR/CVaR; milestone probabilities (e.g., probability of 3x growth by year 10)
- **Portfolio Optimization** — Five methods: mean-variance (Markowitz), CVaR, risk parity, factor-based, and Black-Litterman
- **Interactive Dashboard** — Dash web app with efficient frontier (including Capital Market Line), forecasted return paths, factor exposure charts, drawdown plots, and return distributions

## Quickstart

### Requirements

- Python 3.11+
- Fama-French 5-Factor daily CSV in `data/ff5_daily.csv` (download from [Kenneth French's data library](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html))

### Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

### Run

```bash
ff5
```

Open http://127.0.0.1:8050 in your browser.

### Configuration

Portfolios and analysis settings are defined in `config/portfolios.yaml`:

```yaml
rf: 0.045                    # risk-free rate
n_simulations: 10000         # Monte Carlo paths
horizon_years: 44            # simulation horizon

milestones:
  - name: House
    year: 10
  - name: Retire
    year: 44
milestone_targets: [3.0, 10.0]  # wealth multiples for probability estimates

portfolios:
  - title: VOO
    assets: [VOO]
    weights: [1.0]
    rebalance_cost: 0.06
```

You can also add, remove, and edit portfolios directly in the web UI.

## Data Sources

- **Market data**: Yahoo Finance (consolidated prices via `yfinance`)
- **Factor data**: Fama-French 5-Factor daily returns CSV

Data is cached locally in `cache/` to avoid redundant API calls.

## Project Structure

```
src/ff5/
  analytics/        # Core math: regression, covariance, GARCH, risk metrics
  app/              # Dash web app: layout, callbacks, figures
    components/     # UI components (portfolio editor, controls)
    figures/        # Plotly figure builders
  data/             # Data loaders (Yahoo Finance, FF5 CSV, caching)
  optimizers/       # Portfolio optimization (MV, CVaR, risk parity, BL, factor)
  models.py         # Data models (PortfolioSpec, AnalysisResults, etc.)
  config.py         # Configuration and paths
```

## Development

```bash
pip install -e ".[dev]"
ruff check src/
pytest
```
