# backtest/metrics.py

from typing import Union

import pandas as pd


Number = Union[int, float]


def compute_max_drawdown(equity: pd.Series) -> float:
    """
    Calculate maximum drawdown (0-1) based on equity curve.
    """
    if equity.empty:
        return 0.0
    running_max = equity.cummax()
    drawdown = (equity - running_max) / running_max
    max_dd = drawdown.min()
    return abs(float(max_dd))


def annualized_return(equity: pd.Series) -> float:
    """
    Calculate annualized return, assuming 252 trading days per year.
    """
    if equity.empty:
        return 0.0
    total_return = equity.iloc[-1] / equity.iloc[0] - 1.0
    n_days = len(equity)
    if n_days <= 1:
        return float(total_return)
    ann_ret = (1.0 + total_return) ** (252.0 / n_days) - 1.0
    return float(ann_ret)
