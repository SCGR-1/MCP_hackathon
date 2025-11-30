# mcp_server.py

from dotenv import load_dotenv
load_dotenv()

from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from mcp.server.fastmcp import FastMCP

from backtest import run_backtest
from llm_strategy import llm_generate_strategy_config

@dataclass
class ParseStrategyResult:
    ok: bool
    strategy_config: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

@dataclass
class BacktestSummary:
    symbol: str
    start_date: str
    end_date: str
    strategy_config: Dict[str, Any]
    metrics: Dict[str, Any]
    trades_sample: List[Any]
    equity_sample: List[Any]

@dataclass
class BacktestResult:
    ok: bool
    result: Optional[BacktestSummary] = None
    error: Optional[str] = None

mcp = FastMCP("stock-backtest-mcp", json_response=True)

@mcp.tool()
def parse_strategy(description: str) -> ParseStrategyResult:
    description = (description or "").strip()
    if not description:
        return ParseStrategyResult(ok=False, error="description is empty")
    try:
        cfg = llm_generate_strategy_config(description)
        return ParseStrategyResult(ok=True, strategy_config=cfg)
    except Exception as e:
        return ParseStrategyResult(ok=False, error=f"parse_strategy failed: {e}")

@mcp.tool()
def run_backtest_tool(
    symbol: str,
    start_date: str,
    end_date: str,
    strategy_config: Dict[str, Any],
    initial_cash: float = 10000.0,
) -> BacktestResult:
    symbol = (symbol or "").strip()
    if not symbol:
        return BacktestResult(ok=False, error="symbol is empty")
    try:
        result = run_backtest(
            symbol=symbol,
            start_date=start_date.strip(),
            end_date=end_date.strip(),
            strategy_config=strategy_config,
            initial_cash=float(initial_cash),
        )
    except Exception as e:
        return BacktestResult(ok=False, error=f"run_backtest failed: {e}")

    trades = result.get("trades", [])
    equity_curve = result.get("equity_curve", [])

    summary = BacktestSummary(
        symbol=result.get("symbol"),
        start_date=result.get("start_date"),
        end_date=result.get("end_date"),
        strategy_config=result.get("strategy_config"),
        metrics=result.get("metrics"),
        trades_sample=trades[:10],
        equity_sample=equity_curve[:50],
    )

    return BacktestResult(ok=True, result=summary)

if __name__ == "__main__":
    mcp.run()
