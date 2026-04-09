"""Configuration management — env vars and YAML I/O."""

from __future__ import annotations

import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

from ff5.models import AppConfig, Milestone, PortfolioSpec

load_dotenv()

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
CONFIG_DIR = PROJECT_ROOT / "config"
CACHE_DIR = PROJECT_ROOT / "cache"
FF5_CSV_PATH = DATA_DIR / "ff5_daily.csv"


def get_alpaca_keys() -> tuple[str, str]:
    key_id = os.environ.get("ALPACA_KEY_ID", "")
    secret = os.environ.get("ALPACA_SECRET_KEY", "")
    if not key_id or not secret:
        raise EnvironmentError(
            "ALPACA_KEY_ID and ALPACA_SECRET_KEY must be set. "
            "Copy .env.example to .env and fill in your credentials."
        )
    return key_id, secret


def load_config(path: Path | None = None) -> AppConfig:
    """Load app config from YAML file."""
    if path is None:
        path = CONFIG_DIR / "portfolios.yaml"
    if not path.exists():
        return AppConfig()

    with open(path) as f:
        data = yaml.safe_load(f) or {}

    config = AppConfig(
        rf=data.get("rf", 0.045),
        n_simulations=data.get("n_simulations", 10_000),
        horizon_years=data.get("horizon_years", 44),
        milestone_targets=data.get("milestone_targets", [3.0, 10.0]),
    )

    if "milestones" in data:
        config.milestones = [Milestone(m["name"], m["year"]) for m in data["milestones"]]

    if "portfolios" in data:
        config.portfolios = [PortfolioSpec.from_dict(p) for p in data["portfolios"]]

    return config


def save_config(config: AppConfig, path: Path | None = None):
    """Save app config to YAML file."""
    if path is None:
        path = CONFIG_DIR / "portfolios.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "rf": config.rf,
        "n_simulations": config.n_simulations,
        "horizon_years": config.horizon_years,
        "milestones": [{"name": m.name, "year": m.year} for m in config.milestones],
        "milestone_targets": config.milestone_targets,
        "portfolios": [p.to_dict() for p in config.portfolios],
    }

    with open(path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)
