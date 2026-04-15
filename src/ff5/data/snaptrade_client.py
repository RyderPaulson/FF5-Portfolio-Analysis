"""SnapTrade integration — pull live brokerage holdings."""

from __future__ import annotations

import os


def _get_credentials() -> tuple[str, str, str, str]:
    """Return (client_id, consumer_key, user_id, user_secret) from environment."""
    client_id = os.environ.get("SNAPTRADE_CLIENT_ID", "")
    consumer_key = os.environ.get("SNAPTRADE_CONSUMER_KEY", "")
    user_id = os.environ.get("SNAPTRADE_USER_ID", "")
    user_secret = os.environ.get("SNAPTRADE_USER_SECRET", "")
    if not all([client_id, consumer_key, user_id, user_secret]):
        raise EnvironmentError(
            "SNAPTRADE_CLIENT_ID, SNAPTRADE_CONSUMER_KEY, SNAPTRADE_USER_ID, "
            "and SNAPTRADE_USER_SECRET must all be set in .env. "
            "Run 'python scripts/connect_brokerage.py' to set up."
        )
    return client_id, consumer_key, user_id, user_secret


def _get_client():
    from snaptrade_client import SnapTrade
    client_id, consumer_key, _, _ = _get_credentials()
    return SnapTrade(consumer_key=consumer_key, client_id=client_id)


def _user_kwargs() -> dict:
    """Return user_id and user_secret as kwargs."""
    _, _, user_id, user_secret = _get_credentials()
    return {"user_id": user_id, "user_secret": user_secret}


def is_configured() -> bool:
    try:
        _get_credentials()
        return True
    except EnvironmentError:
        return False


def is_connected() -> bool:
    if not is_configured():
        return False
    try:
        client = _get_client()
        accounts = client.account_information.list_user_accounts(**_user_kwargs())
        return len(accounts.body) > 0
    except Exception:
        return False


def register_and_connect() -> str:
    """Generate a connection portal URL for linking a brokerage."""
    client = _get_client()
    resp = client.authentication.login_snap_trade_user(**_user_kwargs())
    return resp.body.get("redirectURI") or resp.body.get("loginRedirectURI", "")


# Tickers that Chase reports differently from standard format
_TICKER_NORMALIZATIONS = {
    "BRKB": "BRK.B",
    "BRKA": "BRK.A",
}

# Security types to skip (money market funds, cash equivalents)
_SKIP_TYPES = {"oef", "mf", "mmf"}  # open-ended fund, mutual fund, money market


def fetch_holdings() -> list[dict]:
    """Fetch all holdings across linked accounts."""
    client = _get_client()
    ukw = _user_kwargs()

    accounts_resp = client.account_information.list_user_accounts(**ukw)
    accounts = accounts_resp.body

    all_positions = []
    for acct in accounts:
        acct_id = acct.get("id") or acct.get("accountId")
        if not acct_id:
            continue

        try:
            pos_resp = client.account_information.get_user_account_positions(
                account_id=acct_id, **ukw
            )
            for pos in pos_resp.body:
                sym_info = pos.get("symbol", {})
                sym_detail = sym_info.get("symbol", {}) if isinstance(sym_info, dict) else {}

                # Extract ticker from nested structure
                if isinstance(sym_detail, dict):
                    ticker = sym_detail.get("symbol", "") or sym_detail.get("raw_symbol", "")
                    sec_type = sym_detail.get("type", {}).get("code", "")
                else:
                    ticker = str(sym_detail)
                    sec_type = ""

                # Skip money market funds and open-ended funds (cash equivalents)
                if sec_type in _SKIP_TYPES:
                    continue

                # Normalize ticker format
                ticker = _TICKER_NORMALIZATIONS.get(ticker, ticker)

                units = float(pos.get("units") or pos.get("fractional_units") or 0)
                price = float(pos.get("price", 0))
                market_value = units * price

                if ticker and units > 0 and market_value > 0:
                    all_positions.append({
                        "symbol": ticker,
                        "units": units,
                        "price": price,
                        "market_value": market_value,
                    })
        except Exception:
            continue

    # Aggregate same symbol across accounts
    merged: dict[str, dict] = {}
    for p in all_positions:
        sym = p["symbol"]
        if sym in merged:
            merged[sym]["units"] += p["units"]
            merged[sym]["market_value"] += p["market_value"]
        else:
            merged[sym] = {**p}

    for sym in merged:
        if merged[sym]["units"] > 0:
            merged[sym]["price"] = merged[sym]["market_value"] / merged[sym]["units"]

    return list(merged.values())


def holdings_to_portfolio(holdings: list[dict]) -> tuple[list[str], list[float], float]:
    """Convert holdings to (symbols, weights, total_value)."""
    if not holdings:
        return [], [], 0.0
    total = sum(h["market_value"] for h in holdings)
    if total <= 0:
        return [], [], 0.0
    symbols = [h["symbol"] for h in holdings]
    weights = [h["market_value"] / total for h in holdings]
    return symbols, weights, total
