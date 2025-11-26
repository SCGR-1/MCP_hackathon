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
    从 AlphaVantage 拉取日线历史数据（免费 TIME_SERIES_DAILY），
    返回按日期升序排序的 DataFrame。
    列：date, open, high, low, close, volume
    """
    if not ALPHAVANTAGE_API_KEY:
        raise ValueError("缺少 AlphaVantage API Key，请设置环境变量 ALPHAVANTAGE_API_KEY。")

    url = "https://www.alphavantage.co/query"
    params: dict[str, Any] = {
        # 使用免费的 TIME_SERIES_DAILY
        "function": "TIME_SERIES_DAILY",
        "symbol": symbol,
        "apikey": ALPHAVANTAGE_API_KEY,
        # 关键：改成 compact，避免 premium 限制
        "outputsize": "compact",
        "datatype": "json",
    }

    resp = requests.get(url, params=params, timeout=15)
    if resp.status_code != 200:
        raise ValueError(f"请求 AlphaVantage 失败，HTTP 状态码：{resp.status_code}")

    data = resp.json()

    if "Time Series (Daily)" not in data:
        msg = (
            data.get("Note")
            or data.get("Error Message")
            or data.get("Information")
            or str(data)
        )
        raise ValueError(f"AlphaVantage 返回异常：{msg}")

    ts = data["Time Series (Daily)"]

    records = []
    for date_str, daily in ts.items():
        records.append(
            {
                "date": pd.to_datetime(date_str),
                "open": float(daily["1. open"]),
                "high": float(daily["2. high"]),
                "low": float(daily["3. low"]),
                "close": float(daily["4. close"]),   # DAILY 接口: 4. close
                "volume": float(daily["5. volume"]),
            }
        )

    df = pd.DataFrame(records)
    df.sort_values("date", inplace=True)
    df.reset_index(drop=True, inplace=True)

    start = pd.to_datetime(start_date)
    end = pd.to_datetime(end_date)
    df = df[(df["date"] >= start) & (df["date"] <= end)].copy()
    df.reset_index(drop=True, inplace=True)

    if df.empty:
        raise ValueError("在指定时间范围内没有数据，请尝试缩短时间范围到最近几个月。")

    return df
