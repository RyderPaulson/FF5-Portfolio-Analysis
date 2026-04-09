"""Alpaca Markets API client for historical stock data."""

from __future__ import annotations

import time
from collections import deque

import httpx
import pandas as pd


class AlpacaClient:
    """HTTP client for Alpaca Markets data API v2."""

    BASE_URL = "https://data.alpaca.markets/v2"

    def __init__(self, key_id: str, secret_key: str, rate_limit: int = 200):
        self._key_id = key_id
        self._secret_key = secret_key
        self._rate_limit = rate_limit
        self._request_times: deque[float] = deque()
        self._client = httpx.Client(
            headers={
                "APCA-API-KEY-ID": key_id,
                "APCA-API-SECRET-KEY": secret_key,
            },
            timeout=30.0,
        )

    def close(self):
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def get_bars(
        self,
        symbols: list[str],
        timeframe: str = "1Day",
        start: str = "2000-01-01",
        end: str | None = None,
        adjustment: str = "split",
    ) -> dict[str, pd.DataFrame]:
        """Fetch historical OHLCV bars for one or more symbols.

        Returns a dict mapping symbol -> DataFrame with columns:
        Open, High, Low, Close, Volume, TradeCount, VWAP
        """
        if end is None:
            end = pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d")

        params = {
            "symbols": ",".join(symbols),
            "timeframe": timeframe,
            "start": start,
            "end": end,
            "limit": "10000",
        }
        if adjustment:
            params["adjustment"] = adjustment

        raw = self._paginated_request("/stocks/bars", params, "bars")
        return self._parse_bars(raw, symbols)

    def _throttle(self):
        now = time.monotonic()
        # Prune timestamps older than 60 seconds
        while self._request_times and self._request_times[0] < now - 60:
            self._request_times.popleft()

        buffer = 10
        if len(self._request_times) >= self._rate_limit - buffer:
            oldest = self._request_times[0]
            wait = 60 - (now - oldest) + 0.1
            if wait > 0:
                time.sleep(wait)
                # Re-prune after waiting
                now = time.monotonic()
                while self._request_times and self._request_times[0] < now - 60:
                    self._request_times.popleft()

    def _request(self, endpoint: str, params: dict) -> dict:
        self._throttle()
        url = self.BASE_URL + endpoint

        max_retries = 3
        for attempt in range(max_retries):
            try:
                resp = self._client.get(url, params=params)
                self._request_times.append(time.monotonic())
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429 and attempt < max_retries - 1:
                    time.sleep(5)
                else:
                    raise RuntimeError(
                        f"Alpaca API request failed: {e}\nURL: {url}"
                    ) from e

    def _paginated_request(
        self, endpoint: str, params: dict, data_field: str
    ) -> dict[str, list]:
        all_data: dict[str, list] = {}
        page_token = None

        while True:
            if page_token:
                params["page_token"] = page_token

            data = self._request(endpoint, params)

            if data_field in data and data[data_field]:
                page_data = data[data_field]
                for sym, rows in page_data.items():
                    if sym in all_data:
                        all_data[sym].extend(rows)
                    else:
                        all_data[sym] = list(rows) if isinstance(rows, list) else [rows]

            next_token = data.get("next_page_token")
            if next_token:
                page_token = next_token
            else:
                break

        return all_data

    def _parse_bars(
        self, raw: dict[str, list], symbols: list[str]
    ) -> dict[str, pd.DataFrame]:
        result = {}
        for sym in symbols:
            bars = raw.get(sym, [])
            if not bars:
                continue

            records = []
            for b in bars:
                records.append(
                    {
                        "Time": pd.Timestamp(b["t"], tz="UTC"),
                        "Open": b["o"],
                        "High": b["h"],
                        "Low": b["l"],
                        "Close": b["c"],
                        "Volume": b["v"],
                        "TradeCount": b["n"],
                        "VWAP": b["vw"],
                    }
                )
            df = pd.DataFrame(records).set_index("Time")
            result[sym] = df

        return result
