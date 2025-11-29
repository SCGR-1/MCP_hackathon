# backtest/strategies.py

from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd

from .metrics import compute_max_drawdown, annualized_return


def _build_result(
    equity_list: List[Tuple[pd.Timestamp, float]],
    trades: List[Dict[str, Any]],
    initial_cash: float,
) -> Dict[str, Any]:
    """Common result builder with metrics calculation"""
    equity_df = pd.DataFrame(equity_list, columns=["date", "equity"])

    if equity_df.empty:
        return {
            "equity_curve": [],
            "trades": [],
            "metrics": {
                "initial_cash": float(initial_cash),
                "final_equity": float(initial_cash),
                "total_return": 0.0,
                "annualized_return": 0.0,
                "max_drawdown": 0.0,
                "num_trades": 0,
                "win_rate": 0.0,
            },
        }

    total_return = equity_df["equity"].iloc[-1] / equity_df["equity"].iloc[0] - 1.0
    max_dd = compute_max_drawdown(equity_df["equity"])
    ann_ret = annualized_return(equity_df["equity"])

    win_trades = [t for t in trades if t.get("pnl", 0.0) > 0]
    win_rate = len(win_trades) / len(trades) if trades else 0.0

    metrics = {
        "initial_cash": float(initial_cash),
        "final_equity": float(equity_df["equity"].iloc[-1]),
        "total_return": float(total_return),
        "annualized_return": float(ann_ret),
        "max_drawdown": float(max_dd),
        "num_trades": int(len(trades)),
        "win_rate": float(win_rate),
    }

    equity_curve = [
        {"date": d.strftime("%Y-%m-%d"), "equity": float(v)}
        for d, v in equity_list
    ]

    return {
        "equity_curve": equity_curve,
        "trades": trades,
        "metrics": metrics,
    }


def run_ma_cross_strategy(
    df: pd.DataFrame,
    params: Dict[str, Any],
    initial_cash: float = 10000.0,
) -> Dict[str, Any]:
    """
    Moving average crossover strategy:
    - Buy when short MA crosses above long MA
    - Sell when short MA crosses below long MA
    """
    short_window = int(params.get("short_window", 20))
    long_window = int(params.get("long_window", 60))

    if short_window >= long_window:
        raise ValueError("short_window must be less than long_window in ma_cross strategy")

    prices = df["close"].copy()

    df_ma = df.copy()
    df_ma["ma_short"] = prices.rolling(window=short_window).mean()
    df_ma["ma_long"] = prices.rolling(window=long_window).mean()

    cash = initial_cash
    shares = 0.0
    equity_list: List[Tuple[pd.Timestamp, float]] = []
    trades: List[Dict[str, Any]] = []

    last_signal = 0  # 0: no position, 1: long position
    entry_price = None
    entry_date = None

    for i in range(len(df_ma)):
        date = df_ma.loc[i, "date"]
        price = df_ma.loc[i, "close"]
        ma_s = df_ma.loc[i, "ma_short"]
        ma_l = df_ma.loc[i, "ma_long"]

        if np.isnan(ma_s) or np.isnan(ma_l):
            equity = cash + shares * price
            equity_list.append((date, equity))
            continue

        if i == 0:
            signal = 0
        else:
            prev_ma_s = df_ma.loc[i - 1, "ma_short"]
            prev_ma_l = df_ma.loc[i - 1, "ma_long"]
            signal = last_signal
            if (prev_ma_s <= prev_ma_l) and (ma_s > ma_l):
                signal = 1
            elif (prev_ma_s >= prev_ma_l) and (ma_s < ma_l):
                signal = 0

        if signal == 1 and last_signal == 0:
            if cash > 0:
                shares = cash // price
                cost = shares * price
                cash -= cost
                entry_price = price
                entry_date = date

        elif signal == 0 and last_signal == 1:
            if shares > 0:
                proceeds = shares * price
                cash += proceeds
                if entry_price is not None and entry_date is not None:
                    pnl = proceeds - entry_price * shares
                    trades.append(
                        {
                            "entry_date": entry_date.strftime("%Y-%m-%d"),
                            "exit_date": date.strftime("%Y-%m-%d"),
                            "entry_price": float(entry_price),
                            "exit_price": float(price),
                            "shares": float(shares),
                            "pnl": float(pnl),
                            "side": "long",
                            "strategy": "ma_cross",
                        }
                    )
                shares = 0.0
                entry_price = None
                entry_date = None

        equity = cash + shares * price
        equity_list.append((date, equity))
        last_signal = signal

    return _build_result(equity_list, trades, initial_cash)


def run_dca_strategy(
    df: pd.DataFrame,
    params: Dict[str, Any],
    initial_cash: float = 10000.0,
) -> Dict[str, Any]:
    """
    Dollar-Cost Averaging (DCA) strategy:
    - Invest fixed amount buy_amount every interval_days
    - No selling, calculate total return at end date
    """
    interval_days = int(params.get("interval_days", 7))
    buy_amount = float(params.get("buy_amount", 1000.0))

    if interval_days <= 0:
        raise ValueError("interval_days must be a positive integer in dca strategy")
    if buy_amount <= 0:
        raise ValueError("buy_amount must be greater than 0 in dca strategy")

    cash = initial_cash
    shares = 0.0
    equity_list: List[Tuple[pd.Timestamp, float]] = []
    raw_trades: List[Dict[str, Any]] = []

    last_buy_date = None

    for i in range(len(df)):
        date = df.loc[i, "date"]
        price = df.loc[i, "close"]

        should_buy = False
        if last_buy_date is None:
            should_buy = True
        else:
            delta_days = (date - last_buy_date).days
            if delta_days >= interval_days:
                should_buy = True

        if should_buy and cash > 0:
            invest = min(buy_amount, cash)
            if invest > 0:
                buy_shares = invest / price
                shares += buy_shares
                cash -= invest
                last_buy_date = date
                raw_trades.append(
                    {
                        "entry_date": date,
                        "entry_price": float(price),
                        "shares": float(buy_shares),
                    }
                )

        equity = cash + shares * price
        equity_list.append((date, equity))

    trades: List[Dict[str, Any]] = []
    if len(df) > 0 and raw_trades:
        final_date = df["date"].iloc[-1]
        final_price = float(df["close"].iloc[-1])
        for t in raw_trades:
            pnl = (final_price - t["entry_price"]) * t["shares"]
            trades.append(
                {
                    "entry_date": t["entry_date"].strftime("%Y-%m-%d"),
                    "exit_date": final_date.strftime("%Y-%m-%d"),
                    "entry_price": float(t["entry_price"]),
                    "exit_price": float(final_price),
                    "shares": float(t["shares"]),
                    "pnl": float(pnl),
                    "side": "long",
                    "strategy": "dca",
                }
            )

    return _build_result(equity_list, trades, initial_cash)


def run_buy_and_hold_strategy(
    df: pd.DataFrame,
    params: Dict[str, Any],
    initial_cash: float = 10000.0,
) -> Dict[str, Any]:
    """
    Buy & Hold strategy:
    - Buy at first bar's open price using buy_fraction * initial_cash
    - No further trading, equity = shares * close_price
    """
    buy_fraction = params.get("buy_fraction", 1.0)

    first_price = df.iloc[0]["open"]
    cash_to_use = initial_cash * buy_fraction

    if first_price <= 0:
        raise ValueError("Invalid first price")

    shares = cash_to_use / first_price
    entry_date = df.iloc[0]["date"]
    entry_price = float(first_price)
    final_date = df.iloc[-1]["date"]
    final_price = float(df.iloc[-1]["close"])

    equity_list: List[Tuple[pd.Timestamp, float]] = []
    for _, row in df.iterrows():
        equity = shares * row["close"]
        equity_list.append((row["date"], equity))

    trades: List[Dict[str, Any]] = []
    if len(df) > 0:
        pnl = (final_price - entry_price) * shares
        trades.append({
            "entry_date": entry_date.strftime("%Y-%m-%d"),
            "exit_date": final_date.strftime("%Y-%m-%d"),
            "entry_price": entry_price,
            "exit_price": final_price,
            "shares": float(shares),
            "pnl": float(pnl),
            "side": "long",
            "strategy": "buy_and_hold",
        })

    return _build_result(equity_list, trades, initial_cash)


def run_strategy(
    df: pd.DataFrame,
    strategy_config: Dict[str, Any],
    initial_cash: float = 10000.0,
) -> Dict[str, Any]:
    """
    Generic strategy entry point.
    strategy_config format:
    {
        "type": "ma_cross" | "dca" | ...,
        "params": { ... }
    }
    """
    stype = strategy_config.get("type")
    params = strategy_config.get("params", {}) or {}

    if stype == "ma_cross":
        return run_ma_cross_strategy(df, params, initial_cash)
    elif stype == "dca":
        return run_dca_strategy(df, params, initial_cash)
    elif stype == "buy_and_hold":
        return run_buy_and_hold_strategy(df, params, initial_cash)
    else:
        raise ValueError(f"Unsupported strategy type: {stype}")
