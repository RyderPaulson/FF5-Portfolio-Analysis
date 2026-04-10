"""Asset classification — cap size, style, and region for ETFs and stocks."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class AssetClassification:
    ticker: str
    region: str       # "US", "International", "Emerging", "Global", "Unknown"
    cap_size: str     # "Large", "Mid", "Small", "Unknown"
    style: str        # "Value", "Blend", "Growth", "Unknown"
    category: str     # descriptive string
    source: str       # "hardcoded", "ff5_inferred"


# ── Tier 1: Hardcoded ETF lookup ────────────────────────────────────────

ETF_CLASSIFICATIONS: dict[str, dict] = {
    # US Broad Market
    "VOO":  {"region": "US", "cap": "Large", "style": "Blend", "category": "S&P 500"},
    "VTI":  {"region": "US", "cap": "Large", "style": "Blend", "category": "US Total Market"},
    "SPY":  {"region": "US", "cap": "Large", "style": "Blend", "category": "S&P 500"},
    "IVV":  {"region": "US", "cap": "Large", "style": "Blend", "category": "S&P 500"},
    "ITOT": {"region": "US", "cap": "Large", "style": "Blend", "category": "US Total Market"},
    "SCHB": {"region": "US", "cap": "Large", "style": "Blend", "category": "US Total Market"},
    "SPTM": {"region": "US", "cap": "Large", "style": "Blend", "category": "US Total Market"},

    # US Growth
    "QQQ":  {"region": "US", "cap": "Large", "style": "Growth", "category": "Nasdaq 100"},
    "VUG":  {"region": "US", "cap": "Large", "style": "Growth", "category": "US Large Growth"},
    "IWF":  {"region": "US", "cap": "Large", "style": "Growth", "category": "US Large Growth"},
    "SCHG": {"region": "US", "cap": "Large", "style": "Growth", "category": "US Large Growth"},
    "MGK":  {"region": "US", "cap": "Large", "style": "Growth", "category": "US Mega Growth"},
    "VOT":  {"region": "US", "cap": "Mid", "style": "Growth", "category": "US Mid Growth"},

    # US Value
    "VTV":  {"region": "US", "cap": "Large", "style": "Value", "category": "US Large Value"},
    "IWD":  {"region": "US", "cap": "Large", "style": "Value", "category": "US Large Value"},
    "SCHV": {"region": "US", "cap": "Large", "style": "Value", "category": "US Large Value"},
    "AVUV": {"region": "US", "cap": "Small", "style": "Value", "category": "US Small Value"},
    "AVLV": {"region": "US", "cap": "Large", "style": "Value", "category": "US Large Value"},

    # US Mid/Small
    "VO":   {"region": "US", "cap": "Mid", "style": "Blend", "category": "US Mid Blend"},
    "IJH":  {"region": "US", "cap": "Mid", "style": "Blend", "category": "US Mid Blend"},
    "VB":   {"region": "US", "cap": "Small", "style": "Blend", "category": "US Small Blend"},
    "VBK":  {"region": "US", "cap": "Small", "style": "Growth", "category": "US Small Growth"},
    "VBR":  {"region": "US", "cap": "Small", "style": "Value", "category": "US Small Value"},
    "IWM":  {"region": "US", "cap": "Small", "style": "Blend", "category": "US Small Blend"},

    # International Developed
    "VXUS": {"region": "International", "cap": "Large", "style": "Blend", "category": "Intl Developed + EM"},
    "VEA":  {"region": "International", "cap": "Large", "style": "Blend", "category": "Intl Developed"},
    "IXUS": {"region": "International", "cap": "Large", "style": "Blend", "category": "Intl Total"},
    "EFA":  {"region": "International", "cap": "Large", "style": "Blend", "category": "Intl Developed"},
    "SCHF": {"region": "International", "cap": "Large", "style": "Blend", "category": "Intl Developed"},
    "AVDV": {"region": "International", "cap": "Large", "style": "Value", "category": "Intl Value"},
    "AVDE": {"region": "International", "cap": "Large", "style": "Blend", "category": "Intl Developed"},

    # Emerging Markets
    "VWO":  {"region": "Emerging", "cap": "Large", "style": "Blend", "category": "Emerging Markets"},
    "IEMG": {"region": "Emerging", "cap": "Large", "style": "Blend", "category": "Emerging Markets"},
    "AVES": {"region": "Emerging", "cap": "Large", "style": "Value", "category": "EM Value"},

    # Global / All-World
    "VT":   {"region": "Global", "cap": "Large", "style": "Blend", "category": "Total World"},
    "ACWI": {"region": "Global", "cap": "Large", "style": "Blend", "category": "All Country World"},
    "AVGE": {"region": "Global", "cap": "Large", "style": "Blend", "category": "All Equity Markets"},
    "DFAW": {"region": "Global", "cap": "Large", "style": "Value", "category": "World ex-US Core Equity"},

    # Sector / Specialty
    "VNQ":  {"region": "US", "cap": "Mid", "style": "Blend", "category": "US Real Estate"},
    "VNQI": {"region": "International", "cap": "Mid", "style": "Blend", "category": "Intl Real Estate"},
    "AAAU": {"region": "Global", "cap": "Large", "style": "Blend", "category": "Gold"},
    "GLD":  {"region": "Global", "cap": "Large", "style": "Blend", "category": "Gold"},
    "IAU":  {"region": "Global", "cap": "Large", "style": "Blend", "category": "Gold"},

    # Bonds
    "BND":  {"region": "US", "cap": "Large", "style": "Blend", "category": "US Total Bond"},
    "AGG":  {"region": "US", "cap": "Large", "style": "Blend", "category": "US Aggregate Bond"},
    "BNDX": {"region": "International", "cap": "Large", "style": "Blend", "category": "Intl Bond"},
    "TLT":  {"region": "US", "cap": "Large", "style": "Blend", "category": "US Long Treasury"},
    "SHV":  {"region": "US", "cap": "Large", "style": "Blend", "category": "US Short Treasury"},
}


# ── Tier 2: FF5 beta inference ──────────────────────────────────────────

def _infer_from_betas(
    ticker: str, factor_betas: np.ndarray
) -> AssetClassification:
    """Classify based on FF5 factor betas (SMB → size, HML → value/growth)."""
    smb = factor_betas[1]  # SMB beta
    hml = factor_betas[2]  # HML beta

    if smb > 0.3:
        cap = "Small"
    elif smb < -0.3:
        cap = "Large"
    else:
        cap = "Mid"

    if hml > 0.3:
        style = "Value"
    elif hml < -0.3:
        style = "Growth"
    else:
        style = "Blend"

    return AssetClassification(
        ticker=ticker,
        region="Unknown",
        cap_size=cap,
        style=style,
        category=f"{cap} {style} (inferred)",
        source="ff5_inferred",
    )


# ── Tier 3: yfinance lookup (cached) ────────────────────────────────────

_yfinance_cache: dict[str, dict] = {}

_COUNTRY_TO_REGION = {
    "United States": "US",
    "Canada": "US",
    "United Kingdom": "International",
    "Germany": "International",
    "France": "International",
    "Japan": "International",
    "Australia": "International",
    "Switzerland": "International",
    "Netherlands": "International",
    "Sweden": "International",
    "Ireland": "International",
    "China": "Emerging",
    "India": "Emerging",
    "Brazil": "Emerging",
    "Taiwan": "Emerging",
    "South Korea": "Emerging",
    "Mexico": "Emerging",
    "South Africa": "Emerging",
}


def _fetch_yfinance_info(ticker: str) -> dict | None:
    """Fetch and cache yfinance .info for a ticker."""
    if ticker in _yfinance_cache:
        return _yfinance_cache[ticker]

    try:
        import yfinance as yf
        from ff5.data.yfinance_loader import _to_yf_ticker

        yf_sym = _to_yf_ticker(ticker)
        info = yf.Ticker(yf_sym).info
        _yfinance_cache[ticker] = info
        return info
    except Exception:
        _yfinance_cache[ticker] = {}
        return None


def _classify_from_yfinance(
    ticker: str, factor_betas: np.ndarray | None,
) -> AssetClassification | None:
    """Classify a stock using yfinance .info for region, FF5 betas for size/style."""
    info = _fetch_yfinance_info(ticker)
    if not info or not info.get("country"):
        return None

    country = info.get("country", "")
    region = _COUNTRY_TO_REGION.get(country, "International")
    sector = info.get("sector", "")
    industry = info.get("industry", "")

    # Use FF5 betas for size/style if available
    if factor_betas is not None:
        smb, hml = factor_betas[1], factor_betas[2]
        cap = "Small" if smb > 0.3 else ("Large" if smb < -0.3 else "Mid")
        style = "Value" if hml > 0.3 else ("Growth" if hml < -0.3 else "Blend")
    else:
        cap = "Unknown"
        style = "Unknown"

    category = f"{sector} — {industry}" if sector and industry else sector or "Stock"

    return AssetClassification(
        ticker=ticker,
        region=region,
        cap_size=cap,
        style=style,
        category=category,
        source="yfinance",
    )


# ── Public API ──────────────────────────────────────────────────────────

def classify_asset(
    ticker: str,
    factor_betas: np.ndarray | None = None,
) -> AssetClassification:
    """Classify an asset using tiered lookup: hardcoded → yfinance → FF5 inference."""
    ticker_upper = ticker.upper()

    # Tier 1: hardcoded lookup
    if ticker_upper in ETF_CLASSIFICATIONS:
        info = ETF_CLASSIFICATIONS[ticker_upper]
        return AssetClassification(
            ticker=ticker_upper,
            region=info["region"],
            cap_size=info["cap"],
            style=info["style"],
            category=info["category"],
            source="hardcoded",
        )

    # Tier 2: yfinance (gives region for stocks)
    yf_result = _classify_from_yfinance(ticker_upper, factor_betas)
    if yf_result is not None:
        return yf_result

    # Tier 3: FF5 beta inference only (no region)
    if factor_betas is not None:
        return _infer_from_betas(ticker_upper, factor_betas)

    # Fallback
    return AssetClassification(
        ticker=ticker_upper,
        region="Unknown",
        cap_size="Unknown",
        style="Unknown",
        category="Unknown",
        source="none",
    )


def classify_portfolio(
    symbols: list[str],
    factor_betas: np.ndarray | None = None,
) -> list[AssetClassification]:
    """Classify all assets in a portfolio."""
    results = []
    for i, sym in enumerate(symbols):
        betas = factor_betas[i] if factor_betas is not None else None
        results.append(classify_asset(sym, betas))
    return results
