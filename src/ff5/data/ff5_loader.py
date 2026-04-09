"""Load Fama-French 5-factor daily data from CSV."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from ff5.config import FF5_CSV_PATH

FACTOR_COLS = ["MktRF", "SMB", "HML", "RMW", "CMA", "RF"]


def load_ff5(csv_path: Path | str | None = None) -> pd.DataFrame:
    """Load FF5 daily data, returning a DataFrame with DatetimeIndex.

    Values are converted from percentage points to decimals.
    """
    if csv_path is None:
        csv_path = FF5_CSV_PATH

    df = pd.read_csv(
        csv_path,
        skiprows=4,
        names=["Date"] + FACTOR_COLS,
        dtype={"Date": str},
    )

    # Remove non-data rows (copyright footer, blanks)
    df = df[df["Date"].str.len() == 8].copy()

    # Parse YYYYMMDD dates
    df["Date"] = pd.to_datetime(df["Date"], format="%Y%m%d", utc=True)
    df = df.set_index("Date")

    # Convert percentage points to decimals
    for col in FACTOR_COLS:
        df[col] = pd.to_numeric(df[col], errors="coerce") / 100.0

    df = df.dropna()
    return df
