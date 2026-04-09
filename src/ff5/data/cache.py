"""Two-level caching for bar data and portfolio results."""

from __future__ import annotations

import pickle
from datetime import date
from pathlib import Path

import pandas as pd

from ff5.config import CACHE_DIR
from ff5.models import AnalysisResults, PortfolioSpec


def _ensure_cache_dir():
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _today_str() -> str:
    return date.today().strftime("%Y%m%d")


# --------------------------------------------------------------------------- #
# Level 1: Per-symbol bar cache
# --------------------------------------------------------------------------- #

def _bar_cache_path(symbol: str, date_str: str) -> Path:
    return CACHE_DIR / f"bars_{symbol.lower().replace('.', '_')}_{date_str}.pkl"


def get_cached_bars(symbol: str) -> pd.DataFrame | None:
    """Return cached bars for today, or None if not cached."""
    _ensure_cache_dir()
    path = _bar_cache_path(symbol, _today_str())
    if path.exists():
        with open(path, "rb") as f:
            return pickle.load(f)
    return None


def save_bars(symbol: str, df: pd.DataFrame):
    """Save bars to cache, removing stale files for this symbol."""
    _ensure_cache_dir()
    safe_sym = symbol.lower().replace(".", "_")
    # Remove stale cache files
    for old in CACHE_DIR.glob(f"bars_{safe_sym}_*.pkl"):
        old.unlink()
    path = _bar_cache_path(symbol, _today_str())
    with open(path, "wb") as f:
        pickle.dump(df, f)


def load_or_fetch_bars(
    symbols: list[str], alpaca_client, start_date: str = "2000-01-01"
) -> pd.DataFrame:
    """Load bars from cache or fetch from Alpaca, returning synchronized close prices.

    Returns a DataFrame with DatetimeIndex and one column per symbol.
    """
    missing = [s for s in symbols if get_cached_bars(s) is None]

    if missing:
        bar_data = alpaca_client.get_bars(missing, "1Day", start_date)
        for sym in missing:
            if sym in bar_data:
                save_bars(sym, bar_data[sym])

    # Load all from cache and merge
    frames = {}
    for sym in symbols:
        df = get_cached_bars(sym)
        if df is not None and "Close" in df.columns:
            frames[sym] = df["Close"].rename(sym)

    if not frames:
        raise RuntimeError(f"No data available for symbols: {symbols}")

    prices = pd.concat(frames.values(), axis=1, join="inner")
    prices = prices.sort_index()
    return prices


# --------------------------------------------------------------------------- #
# Level 2: Portfolio results cache
# --------------------------------------------------------------------------- #

def _port_cache_path(cache_key: str) -> Path:
    return CACHE_DIR / f"{cache_key.replace(':', '_')}.pkl"


def get_cached_results(portfolio: PortfolioSpec) -> AnalysisResults | None:
    """Return cached analysis results for today, or None."""
    _ensure_cache_dir()
    key = portfolio.cache_key(_today_str())
    path = _port_cache_path(key)
    if path.exists():
        with open(path, "rb") as f:
            results = pickle.load(f)
            if isinstance(results, AnalysisResults) and results.forecasted_returns is not None:
                return results
    return None


def save_results(portfolio: PortfolioSpec, results: AnalysisResults):
    """Save analysis results to cache."""
    _ensure_cache_dir()
    key = portfolio.cache_key(_today_str())
    path = _port_cache_path(key)
    with open(path, "wb") as f:
        pickle.dump(results, f)
