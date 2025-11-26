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
    """共用的结果封装 + 指标计算"""
    equity_df = pd.DataFrame(equity_list, columns=["date", "equity"])

    if equity_df.empty:
        # 防御：极端情况下没有任何 equity 记录
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


# ========== 策略 1：均线交叉（ma_cross） ==========

def run_ma_cross_strategy(
    df: pd.DataFrame,
    params: Dict[str, Any],
    initial_cash: float = 10000.0,
) -> Dict[str, Any]:
    """
    均线交叉策略：
    - 短均线上穿长均线：全仓买入
    - 短均线下穿长均线：全部卖出
    """
    short_window = int(params.get("short_window", 20))
    long_window = int(params.get("long_window", 60))

    if short_window >= long_window:
        raise ValueError("ma_cross 策略中，short_window 必须小于 long_window。")

    prices = df["close"].copy()

    df_ma = df.copy()
    df_ma["ma_short"] = prices.rolling(window=short_window).mean()
    df_ma["ma_long"] = prices.rolling(window=long_window).mean()

    cash = initial_cash
    shares = 0.0
    equity_list: List[Tuple[pd.Timestamp, float]] = []
    trades: List[Dict[str, Any]] = []

    last_signal = 0  # 0: 空仓, 1: 持多
    entry_price = None
    entry_date = None

    for i in range(len(df_ma)):
        date = df_ma.loc[i, "date"]
        price = df_ma.loc[i, "close"]
        ma_s = df_ma.loc[i, "ma_short"]
        ma_l = df_ma.loc[i, "ma_long"]

        # 均线未形成，记录权益但不交易
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
            # 金叉
            if (prev_ma_s <= prev_ma_l) and (ma_s > ma_l):
                signal = 1
            # 死叉
            elif (prev_ma_s >= prev_ma_l) and (ma_s < ma_l):
                signal = 0

        # 执行交易
        if signal == 1 and last_signal == 0:
            # 买入
            if cash > 0:
                shares = cash // price  # 整股
                cost = shares * price
                cash -= cost
                entry_price = price
                entry_date = date

        elif signal == 0 and last_signal == 1:
            # 卖出
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


# ========== 策略 2：定投（dca） ==========

def run_dca_strategy(
    df: pd.DataFrame,
    params: Dict[str, Any],
    initial_cash: float = 10000.0,
) -> Dict[str, Any]:
    """
    定投策略（Dollar-Cost Averaging）：
    - 每隔 interval_days 天，投入固定金额 buy_amount 买入
    - 全程不卖出，最终在结束日计算总体收益
    """
    interval_days = int(params.get("interval_days", 7))  # 默认每 7 天一次
    buy_amount = float(params.get("buy_amount", 1000.0))

    if interval_days <= 0:
        raise ValueError("dca 策略中，interval_days 必须为正整数。")
    if buy_amount <= 0:
        raise ValueError("dca 策略中，buy_amount 必须大于 0。")

    cash = initial_cash
    shares = 0.0
    equity_list: List[Tuple[pd.Timestamp, float]] = []
    raw_trades: List[Dict[str, Any]] = []

    last_buy_date = None

    for i in range(len(df)):
        date = df.loc[i, "date"]
        price = df.loc[i, "close"]

        # 是否需要买入
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

    # 结束时按最后一天价格计算每笔定投的 pnl
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


# ========== 通用分发入口 ==========

def run_strategy(
    df: pd.DataFrame,
    strategy_config: Dict[str, Any],
    initial_cash: float = 10000.0,
) -> Dict[str, Any]:
    """
    通用策略入口：
    strategy_config 形如：
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
    else:
        raise ValueError(f"不支持的策略类型: {stype}")
