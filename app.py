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
    use_llm: bool,
    strategy_description: str,
    strategy_type: str,
    short_window: int,
    long_window: int,
    dca_interval_days: int,
    dca_amount: float,
    initial_cash: float,
) -> Tuple[str, str, plt.Figure]:
    """
    Main Gradio logic:
    1. If use_llm=True + description provided → call Modal LLM
    2. Otherwise → use manual parameters
    """
    # Validate date range (AlphaVantage free tier only provides ~100 trading days)
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
                plt.figure()
            )
        
        if start_dt > end_dt:
            return (
                "Error: Start date must be before end date.",
                "",
                plt.figure()
            )
    except Exception as e:
        return (
            f"Error: Invalid date format. Please use YYYY-MM-DD format.\n{e}",
            "",
            plt.figure()
        )
    
    if use_llm and strategy_description.strip():
        try:
            strategy_config = llm_generate_strategy_config(strategy_description.strip())
            
            # Check if LLM returned "other" strategy type
            if strategy_config.get("type") == "other":
                return (
                    "Error: The strategy description does not match any supported strategy types.\n\n"
                    "Supported strategies:\n"
                    "- Moving Average Crossover (ma_cross): Buy/sell based on MA crossovers\n"
                    "- Dollar-Cost Averaging (dca): Invest fixed amounts at regular intervals\n"
                    "- Buy and Hold: Purchase and hold long-term\n\n"
                    "Please describe one of these strategies, or use manual parameter mode.",
                    "",
                    plt.figure()
                )
            
            # If LLM parsed initial_cash from description, use it instead of UI input
            if "initial_cash" in strategy_config:
                initial_cash = strategy_config.pop("initial_cash")
        except Exception as e:
            return f"LLM strategy parsing failed:\n{e}", "", plt.figure()
    else:
        if strategy_type == "ma_cross":
            strategy_config = {
                "type": "ma_cross",
                "params": {
                    "short_window": int(short_window),
                    "long_window": int(long_window),
                },
            }
        elif strategy_type == "dca":
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
                "params": {
                    "buy_fraction": 1.0
                },
            }
        else:
            return f"Unsupported strategy type: {strategy_type}", "", plt.figure()

    try:
        result = run_backtest(
            symbol=symbol.strip(),
            start_date=start_date.strip(),
            end_date=end_date.strip(),
            strategy_config=strategy_config,
            initial_cash=initial_cash,
        )
    except Exception as e:
        return f"Backtest failed: {e}", "", plt.figure()

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

    dates = [pd.to_datetime(p["date"]) for p in equity_curve]
    equity = [p["equity"] for p in equity_curve]

    # Clear any previous figure state
    plt.close('all')
    fig, ax = plt.subplots(figsize=(10, 5))
    
    # Plot the data
    ax.plot(dates, equity, linewidth=1.5)
    ax.set_title(f"Equity Curve - {result['symbol']}")
    ax.set_xlabel("Date")
    ax.set_ylabel("Equity")
    ax.grid(True, alpha=0.3)
    
    # Set x-axis range to full start_date to end_date range
    start_dt = pd.to_datetime(result['start_date'])
    end_dt = pd.to_datetime(result['end_date'])
    ax.set_xlim([start_dt, end_dt])
    
    # Format dates based on the full date range
    date_range = (end_dt - start_dt).days
    if date_range <= 30:
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
        ax.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, date_range // 10)))
    elif date_range <= 365:
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))
    else:
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=max(1, date_range // 365)))
    
    fig.autofmt_xdate(rotation=45)

    return metrics_text, trades_text, fig


with gr.Blocks(title="LLM-Powered Strategy Backtesting") as demo:
    gr.Markdown(
        """
        # Stock Strategy Backtesting (Natural Language Supported)

        You can define strategies in two ways:

        ### 1. Natural Language (Recommended)
        - Check "Use LLM to parse strategy"
        - Enter strategy description (English/Chinese)
        - Examples:
            - "Buy when 10-day MA crosses above 50-day MA, sell when it crosses below"
            - "Invest $1000 every 7 days in AAPL"

        ### 2. Manual Parameters
        - Disable LLM
        - Manually select strategy type and parameters
        """
    )

    with gr.Row():
        with gr.Column():
            symbol = gr.Textbox(label="Stock Symbol", value="AAPL")
            start_date = gr.Textbox(
                label="Start Date (YYYY-MM-DD)", 
                value=str(default_start),
                placeholder=f"Must be within last 100 days (after {(today - dt.timedelta(days=100)).strftime('%Y-%m-%d')})"
            )
            end_date = gr.Textbox(label="End Date (YYYY-MM-DD)", value=str(default_end))
            gr.Markdown(
                f"<small>⚠️ Note: AlphaVantage free API provides ~100 trading days of data. "
                f"Start date should be after {(today - dt.timedelta(days=100)).strftime('%Y-%m-%d')}</small>"
            )

            use_llm = gr.Checkbox(label="Use LLM to parse natural language strategy", value=True)

            strategy_description = gr.Textbox(
                label="Strategy Description (when LLM is enabled)",
                lines=4,
                placeholder="Example: Buy when 10-day MA crosses above 50-day MA, sell when it crosses below; or: Invest $1000 every 7 days.",
            )

            strategy_type = gr.Dropdown(
                label="Strategy Type (Manual Mode)",
                choices=["ma_cross", "dca","buy_and_hold"],
                value="ma_cross",
            )

            gr.Markdown("### ma_cross Parameters (Manual)")
            short_window = gr.Slider(5, 60, value=20, label="Short MA Window")
            long_window = gr.Slider(20, 200, value=60, label="Long MA Window")

            gr.Markdown("### dca Parameters (Manual)")
            dca_interval_days = gr.Slider(3, 30, value=7, label="DCA Interval (Days)")
            dca_amount = gr.Number(value=1000, label="DCA Amount per Period")

            initial_cash = gr.Number(value=10000, label="Initial Cash")

            run_btn = gr.Button("Run Backtest")

        with gr.Column():
            metrics_out = gr.Textbox(label="Backtest Metrics", lines=14)
            trades_out = gr.Textbox(label="Trade Summary", lines=14)
            equity_plot = gr.Plot(label="Equity Curve")

    run_btn.click(
        backtest_interface,
        [
            symbol, start_date, end_date,
            use_llm, strategy_description,
            strategy_type, short_window, long_window,
            dca_interval_days, dca_amount,
            initial_cash
        ],
        [metrics_out, trades_out, equity_plot]
    )


if __name__ == "__main__":
    demo.launch()
