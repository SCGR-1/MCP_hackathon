import os
from dotenv import load_dotenv
load_dotenv()

from typing import Tuple
import datetime as dt

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import gradio as gr

from backtest import run_backtest
from llm_strategy import llm_generate_strategy_config


today = dt.date.today()
default_end = today
default_start = today - dt.timedelta(days=90)


def backtest_interface(
    symbol: str,
    start_date: str,
    end_date: str,
    mode: str,
    strategy_description: str,
    strategy_type: str,
    short_window: int,
    long_window: int,
    dca_interval_days: int,
    dca_amount: float,
    initial_cash: float,
) -> Tuple[str, str, plt.Figure]:
    # ---------------- 日期校验 ----------------
    try:
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)
        max_days_ago = today - dt.timedelta(days=100)

        if start_dt.date() < max_days_ago:
            return (
                f"Error: Start date cannot be more than 100 days ago.\n"
                f"AlphaVantage free API only provides ~100 trading days of data.\n"
                f"Please use a start date after {max_days_ago.strftime('%Y-%m-%d')}",
                "",
                plt.figure(),
            )

        if start_dt > end_dt:
            return ("Error: Start date must be before end date.", "", plt.figure())
    except Exception as e:
        return (f"Error: Invalid date format. Please use YYYY-MM-DD.\n{e}", "", plt.figure())

    symbol = symbol.strip()
    if not symbol:
        return ("Error: Stock symbol cannot be empty.", "", plt.figure())

    if initial_cash is None or initial_cash <= 0:
        return ("Error: Initial cash must be a positive number.", "", plt.figure())

    # ---------------- LLM / Manual 分支 ----------------
    use_llm = (mode == "LLM")

    if use_llm:
        if not strategy_description.strip():
            return ("Error: Please enter a strategy description.", "", plt.figure())
        try:
            strategy_config = llm_generate_strategy_config(strategy_description.strip())
            # Use initial_cash from LLM if provided, otherwise use UI value
            if "initial_cash" in strategy_config:
                initial_cash = float(strategy_config.pop("initial_cash"))
        except Exception as e:
            return (f"LLM strategy parsing failed:\n{e}", "", plt.figure())
    else:
        # Manual 模式
        if strategy_type == "ma_cross":
            if short_window <= 0 or long_window <= 0:
                return ("Error: MA windows must be > 0.", "", plt.figure())
            if short_window >= long_window:
                return ("Error: Short MA window must be < long MA window.", "", plt.figure())
            strategy_config = {
                "type": "ma_cross",
                "params": {
                    "short_window": int(short_window),
                    "long_window": int(long_window),
                },
            }
        elif strategy_type == "dca":
            if dca_interval_days <= 0:
                return ("Error: DCA interval days must be > 0.", "", plt.figure())
            if dca_amount <= 0:
                return ("Error: DCA amount must be > 0.", "", plt.figure())
            strategy_config = {
                "type": "dca",
                "params": {
                    "interval_days": int(dca_interval_days),
                    "buy_amount": float(dca_amount),
                },
            }
        elif strategy_type == "buy_and_hold":
            strategy_config = {
                "type": "buy_and_hold",
                "params": {"buy_fraction": 1.0},
            }
        else:
            return (f"Unsupported strategy type: {strategy_type}", "", plt.figure())

    # ---------------- 回测 ----------------
    try:
        result = run_backtest(
            symbol=symbol,
            start_date=start_date.strip(),
            end_date=end_date.strip(),
            strategy_config=strategy_config,
            initial_cash=float(initial_cash),
        )
    except Exception as e:
        return (f"Backtest failed: {e}", "", plt.figure())

    metrics = result["metrics"]
    trades = result["trades"]
    equity_curve = result["equity_curve"]

    metrics_text = (
        f"Symbol: {result['symbol']}\n"
        f"Period: {result['start_date']} ~ {result['end_date']}\n"
        f"Strategy: {result['strategy_config']['type']}\n"
        f"Params: {result['strategy_config']['params']}\n\n"
        f"Initial Cash: {metrics['initial_cash']:.2f}\n"
        f"Final Equity: {metrics['final_equity']:.2f}\n"
        f"Total Return: {metrics['total_return']*100:.2f}%\n"
        f"Annualized Return: {metrics['annualized_return']*100:.2f}%\n"
        f"Max Drawdown: {metrics['max_drawdown']*100:.2f}%\n"
        f"Number of Trades: {metrics['num_trades']}\n"
        f"Win Rate: {metrics['win_rate']*100:.2f}%\n"
    )

    if trades:
        lines = []
        for t in trades[:10]:
            lines.append(
                f"{t['entry_date']} → {t['exit_date']} | "
                f"{t['entry_price']:.2f} → {t['exit_price']:.2f} | "
                f"shares={t['shares']:.4f} | pnl={t['pnl']:.2f}"
            )
        trades_text = "Top 10 trades:\n" + "\n".join(lines)
    else:
        trades_text = "No trades (strategy generated no signals)"

    if not equity_curve:
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.text(0.5, 0.5, "No equity curve data available", ha="center", va="center", transform=ax.transAxes)
        ax.set_title(f"Equity Curve - {result['symbol']}")
        return metrics_text, trades_text, fig

    dates = [pd.to_datetime(p["date"]) for p in equity_curve]
    equity = [p["equity"] for p in equity_curve]

    plt.close("all")
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(dates, equity, linewidth=1.5)
    ax.set_title(f"Equity Curve - {result['symbol']}")
    ax.set_xlabel("Date")
    ax.set_ylabel("Equity")
    ax.grid(True, alpha=0.3)

    start_dt = pd.to_datetime(result["start_date"])
    end_dt = pd.to_datetime(result["end_date"])
    ax.set_xlim([start_dt, end_dt])

    date_range = (end_dt - start_dt).days
    if date_range <= 30:
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d"))
        ax.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, date_range // 10)))
    elif date_range <= 365:
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
        ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))
    else:
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=max(1, date_range // 365)))

    fig.autofmt_xdate(rotation=45)

    return metrics_text, trades_text, fig


with gr.Blocks(title="LLM-Powered Strategy Backtesting") as demo:
    gr.Markdown(
        """
        # Stock Strategy Backtesting

        Choose a strategy mode:
        - **LLM**: Describe your strategy in natural language
        - **Manual**: Select a strategy type and set parameters
        """
    )

    with gr.Row():
        with gr.Column():
            symbol = gr.Textbox(label="Stock Symbol", value="AAPL")
            start_date = gr.Textbox(label="Start Date (YYYY-MM-DD)", value=str(default_start))
            end_date = gr.Textbox(label="End Date (YYYY-MM-DD)", value=str(default_end))

            mode = gr.Dropdown(
                label="Strategy Mode",
                choices=["LLM", "Manual"],
                value="LLM",
            )

            strategy_description = gr.Textbox(
                label="Strategy Description (for LLM mode)",
                lines=4,
                placeholder="Example: Buy when 10-day MA crosses above 50-day MA; or invest $1000 every 7 days.",
            )

            strategy_type = gr.Dropdown(
                label="Manual Strategy Type",
                choices=["ma_cross", "dca", "buy_and_hold"],
                value="ma_cross",
            )

            gr.Markdown("### MA Cross Parameters (used when Manual + ma_cross)")
            short_window = gr.Slider(5, 60, value=20, step=1, label="Short MA Window")
            long_window = gr.Slider(20, 200, value=60, step=1, label="Long MA Window")

            gr.Markdown("### DCA Parameters (used when Manual + dca)")
            dca_interval_days = gr.Slider(3, 30, value=7, step=1, label="DCA Interval (Days)")
            dca_amount = gr.Number(value=1000, label="DCA Amount per Period")

            gr.Markdown("### Buy and Hold Parameters (used when Manual + buy_and_hold)")
            gr.Markdown("No extra parameters. Strategy uses 100% of initial cash to buy and hold.")

            initial_cash = gr.Number(value=10000, label="Initial Cash (USD)")

            run_btn = gr.Button("Run Backtest", variant="primary")

        with gr.Column():
            metrics_out = gr.Textbox(label="Backtest Metrics", lines=14)
            trades_out = gr.Textbox(label="Trade Summary", lines=14)
            equity_plot = gr.Plot(label="Equity Curve")

    run_btn.click(
        backtest_interface,
        [
            symbol, start_date, end_date,
            mode, strategy_description,
            strategy_type, short_window, long_window,
            dca_interval_days, dca_amount,
            initial_cash,
        ],
        [metrics_out, trades_out, equity_plot],
    )


if __name__ == "__main__":
    demo.launch()
