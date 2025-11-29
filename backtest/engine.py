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
    Generic backtest entry point.
    """
    df = fetch_price_history(symbol, start_date, end_date)
    res = run_strategy(df, strategy_config, initial_cash)

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
    Legacy compatibility wrapper for MA crossover strategy.
    """
    strategy_config: Dict[str, Any] = {
        "type": "ma_cross",
        "params": {
            "short_window": int(short_window),
            "long_window": int(long_window),
        },
    }
    return run_backtest(symbol, start_date, end_date, strategy_config, initial_cash)
