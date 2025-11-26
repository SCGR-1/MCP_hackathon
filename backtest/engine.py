# backtest/engine.py

from typing import Any, Dict

from .data import fetch_price_history
from .strategies import run_strategy


def run_backtest(
    symbol: str,
    start_date: str,
    end_date: str,
    strategy_config: Dict[str, Any],
    initial_cash: float,
) -> Dict[str, Any]:
    """
    通用回测入口：
    - symbol / 日期区间：标的和时间
    - strategy_config：策略配置（type + params）
    - initial_cash：初始资金
    """
    df = fetch_price_history(symbol, start_date, end_date)
    res = run_strategy(df, strategy_config, initial_cash)

    # 增加一些元信息
    res["symbol"] = symbol.upper()
    res["start_date"] = start_date
    res["end_date"] = end_date
    res["strategy_config"] = strategy_config
    return res


def run_backtest_for_symbol(
    symbol: str,
    start_date: str,
    end_date: str,
    short_window: int,
    long_window: int,
    initial_cash: float,
) -> Dict[str, Any]:
    """
    兼容旧版：专门针对均线交叉的封装
    """
    strategy_config: Dict[str, Any] = {
        "type": "ma_cross",
        "params": {
            "short_window": int(short_window),
            "long_window": int(long_window),
        },
    }
    return run_backtest(symbol, start_date, end_date, strategy_config, initial_cash)
