# backtest/data.py

import os
from typing import Any

import pandas as pd
import requests


ALPHAVANTAGE_API_KEY = os.getenv("ALPHAVANTAGE_API_KEY", "")


def fetch_price_history(
    symbol: str,
    start_date: str,
    end_date: str,
) -> pd.DataFrame:
    """
    Fetch daily historical data from AlphaVantage (free TIME_SERIES_DAILY + compact).
    Returns DataFrame with columns: date, open, high, low, close, volume
    Sorted by date and filtered by start_date/end_date.
    """
    if not ALPHAVANTAGE_API_KEY:
        raise ValueError("Missing AlphaVantage API Key. Set ALPHAVANTAGE_API_KEY environment variable.")

    url = "https://www.alphavantage.co/query"
    params: dict[str, Any] = {
        "function": "TIME_SERIES_DAILY",
        "symbol": symbol,
        "apikey": ALPHAVANTAGE_API_KEY,
        "outputsize": "compact",
        "datatype": "json",
    }

    resp = requests.get(url, params=params, timeout=15)
    if resp.status_code != 200:
        raise ValueError(f"AlphaVantage request failed with HTTP status: {resp.status_code}")

    data = resp.json()

    if "Time Series (Daily)" not in data:
        # Get error message and sanitize it to remove API key
        raw_msg = (
            data.get("Note")
            or data.get("Error Message")
            or data.get("Information")
            or str(data)
        )
        
        # Remove API key from error message if present
        if ALPHAVANTAGE_API_KEY and ALPHAVANTAGE_API_KEY in raw_msg:
            msg = raw_msg.replace(ALPHAVANTAGE_API_KEY, "[API_KEY_HIDDEN]")
        else:
            msg = raw_msg
        
        # Check for common error types and provide user-friendly messages
        if "rate limit" in msg.lower() or "25 requests per day" in msg.lower():
            raise ValueError(
                "AlphaVantage API rate limit exceeded. "
                "Free tier allows 25 requests per day. "
                "Please try again later or upgrade to a premium plan."
            )
        elif "API key" in msg.lower() and "detected" in msg.lower():
            # This is the rate limit message that includes API key
            raise ValueError(
                "AlphaVantage API rate limit exceeded. "
                "Free tier allows 25 requests per day. "
                "Please try again later or upgrade to a premium plan."
            )
        else:
            # Generic error without exposing API key
            raise ValueError(f"AlphaVantage API error: {msg}")

    ts = data["Time Series (Daily)"]

    records = []
    for date_str, daily in ts.items():
        try:
            records.append(
                {
                    "date": pd.to_datetime(date_str),
                    "open": float(daily["1. open"]),
                    "high": float(daily["2. high"]),
                    "low": float(daily["3. low"]),
                    "close": float(daily["4. close"]),
                    "volume": float(daily["5. volume"]),
                }
            )
        except Exception:
            continue

    if not records:
        raise ValueError("AlphaVantage returned empty or invalid data")

    df = pd.DataFrame(records)
    df.sort_values("date", inplace=True)
    df.reset_index(drop=True, inplace=True)

    start = pd.to_datetime(start_date)
    end = pd.to_datetime(end_date)
    df = df[(df["date"] >= start) & (df["date"] <= end)].copy()
    df.reset_index(drop=True, inplace=True)

    if df.empty:
        raise ValueError("No data in specified date range. Try shortening the range to recent months or check dates.")

    return df
