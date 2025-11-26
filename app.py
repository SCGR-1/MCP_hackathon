# app.py

from typing import Tuple
import datetime as dt

import matplotlib.pyplot as plt
import pandas as pd
import gradio as gr

from backtest import run_backtest
from llm_strategy import llm_generate_strategy_config


# ======== 默认日期：最近 90 天 ========

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
    Gradio 的主逻辑：
    1. 若 use_llm=True + description 非空 → 调 Modal LLM
    2. 否则 → 走手动参数
    """
    # ----- Step 1: 生成策略配置 -----
    if use_llm and strategy_description.strip():
        try:
            strategy_config = llm_generate_strategy_config(strategy_description.strip())
        except Exception as e:
            return f"LLM 解析策略失败：\n{e}", "", plt.figure()
    else:
        # 手动模式
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
        else:
            return f"不支持的策略类型：{strategy_type}", "", plt.figure()

    # ----- Step 2: 回测 -----
    try:
        result = run_backtest(
            symbol=symbol.strip(),
            start_date=start_date.strip(),
            end_date=end_date.strip(),
            strategy_config=strategy_config,
            initial_cash=initial_cash,
        )
    except Exception as e:
        return f"回测失败：{e}", "", plt.figure()

    metrics = result["metrics"]
    trades = result["trades"]
    equity_curve = result["equity_curve"]

    # ----- Step 3: 指标文本 -----
    metrics_text = (
        f"标的: {result['symbol']}\n"
        f"区间: {result['start_date']} ~ {result['end_date']}\n"
        f"策略: {result['strategy_config']['type']}\n"
        f"参数: {result['strategy_config']['params']}\n\n"
        f"初始资金: {metrics['initial_cash']:.2f}\n"
        f"结束市值: {metrics['final_equity']:.2f}\n"
        f"总收益率: {metrics['total_return']*100:.2f}%\n"
        f"年化收益率: {metrics['annualized_return']*100:.2f}%\n"
        f"最大回撤: {metrics['max_drawdown']*100:.2f}%\n"
        f"交易次数: {metrics['num_trades']}\n"
        f"胜率: {metrics['win_rate']*100:.2f}%\n"
    )

    # ----- Step 4: 交易摘要 -----
    if trades:
        lines = []
        for t in trades[:10]:
            lines.append(
                f"{t['entry_date']} → {t['exit_date']} | "
                f"{t['entry_price']:.2f} → {t['exit_price']:.2f} | "
                f"shares={t['shares']:.4f} | pnl={t['pnl']:.2f}"
            )
        trades_text = "前 10 笔交易：\n" + "\n".join(lines)
    else:
        trades_text = "无交易（策略未产生信号）"

    # ----- Step 5: 资金曲线 -----
    dates = [pd.to_datetime(p["date"]) for p in equity_curve]
    equity = [p["equity"] for p in equity_curve]

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(dates, equity)
    ax.set_title(f"资金曲线 - {result['symbol']}")
    ax.set_xlabel("日期")
    ax.set_ylabel("市值")
    fig.autofmt_xdate()

    return metrics_text, trades_text, fig


# ====================================
# =========== Gradio UI ==============
# ====================================

with gr.Blocks(title="LLM 驱动通用策略回测") as demo:
    gr.Markdown(
        f"""
        # 通用股票策略回测（支持自然语言策略）

        你可以选择两种方式定义策略：

        ### 1. 自然语言（推荐）
        - 勾选“使用 LLM 解析策略”
        - 输入策略描述（中文/英文）
        - 示例：
            - “当 10 日均线上穿 50 日均线时买入，下穿时卖出”
            - “每 7 天投入 1000 美元定投 AAPL”

        ### 2. 手动参数
        - 关闭 LLM
        - 手动选择策略类型和参数
        """
    )

    with gr.Row():
        with gr.Column():
            symbol = gr.Textbox(label="股票代码", value="AAPL")
            start_date = gr.Textbox(label="开始日期 (YYYY-MM-DD)", value=str(default_start))
            end_date = gr.Textbox(label="结束日期 (YYYY-MM-DD)", value=str(default_end))

            use_llm = gr.Checkbox(label="使用 LLM 解析自然语言策略", value=True)

            strategy_description = gr.Textbox(
                label="策略自然语言描述（开启 LLM 时生效）",
                lines=4,
                placeholder="例如：当 10 日均线上穿 50 日均线时买入，下穿时卖出；或：每 7 天投入 1000 美元定投。",
            )

            strategy_type = gr.Dropdown(
                label="策略类型（手动模式）",
                choices=["ma_cross", "dca"],
                value="ma_cross",
            )

            gr.Markdown("### ma_cross 参数（手动）")
            short_window = gr.Slider(5, 60, value=20, label="短期均线窗口")
            long_window = gr.Slider(20, 200, value=60, label="长期均线窗口")

            gr.Markdown("### dca 参数（手动）")
            dca_interval_days = gr.Slider(3, 30, value=7, label="定投间隔（日）")
            dca_amount = gr.Number(value=1000, label="每次定投金额")

            initial_cash = gr.Number(value=10000, label="初始资金")

            run_btn = gr.Button("运行回测")

        with gr.Column():
            metrics_out = gr.Textbox(label="回测指标", lines=14)
            trades_out = gr.Textbox(label="交易记录摘要", lines=14)
            equity_plot = gr.Plot(label="资金曲线")

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
