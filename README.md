# LLM-Powered Strategy Backtesting

A lightweight, modular backtesting application that converts **natural-language trading strategies** into structured executable strategies.  
Powered by:

- **Gradio** — interactive UI  
- **Modal** — cloud-hosted strategy parser endpoint  
- **Python** — pluggable backtesting engine  
- **AlphaVantage** — historical daily price data  
- **(Optional) LLMs** — Claude/Bedrock/OpenAI, or rule-based fallback

The system is designed as a foundation for **MCP-compatible tools** and AI agents.

---

## Features

### Natural-Language Strategy Parsing
Users can write free-form strategy descriptions such as:

- “Buy when the 10-day MA crosses above the 50-day MA.”
- “Invest $1000 every 7 days.”
- “Use 20/60 MA crossover.”

Modal endpoint converts text into a structured config:

```json
{
  "type": "ma_cross",
  "params": {"short_window": 10, "long_window": 50}
}
