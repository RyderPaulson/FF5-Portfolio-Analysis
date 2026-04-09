"""Yahoo Finance data loader — provides consolidated (SIP-equivalent) price data."""

from __future__ import annotations

import pandas as pd
import yfinance as yf


def _to_yf_ticker(sym: str) -> str:
    """Convert standard ticker to Yahoo Finance format (e.g. BRK.B -> BRK-B)."""
    return sym.replace(".", "-")


def fetch_yfinance_bars(symbols: list[str], start: str = "2000-01-01") -> dict[str, pd.DataFrame]:
    """Fetch historical daily bars from Yahoo Finance.

    Returns a dict mapping symbol -> DataFrame with columns matching the
    Alpaca format: Open, High, Low, Close, Volume (indexed by UTC datetime).
    Keys use the original symbol names (not Yahoo format).
    """
    result = {}
    for sym in symbols:
        yf_sym = _to_yf_ticker(sym)
        ticker = yf.Ticker(yf_sym)
        df = ticker.history(start=start, auto_adjust=True)
        if df.empty:
            continue

        # Normalize index to UTC DatetimeIndex to match Alpaca/FF5 format
        df.index = pd.to_datetime(df.index.date).tz_localize("UTC")

        # Keep only the columns the pipeline uses
        df = df[["Open", "High", "Low", "Close", "Volume"]]
        result[sym] = df  # key is the original symbol, not the yfinance one

    return result
