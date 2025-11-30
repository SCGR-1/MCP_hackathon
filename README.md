---
title: Stock Backtest MCP
emoji: 📈
colorFrom: blue
colorTo: green
sdk: gradio
app_file: app.py
pinned: false
---

# LLM-Powered Strategy Backtesting

A lightweight, modular backtesting application that converts **natural-language trading strategies** into structured executable strategies using OpenAI GPT-4o-mini.

Powered by:
- **Gradio** — interactive web UI
- **Modal** — cloud-hosted LLM strategy parser endpoint
- **OpenAI GPT-4o-mini** — natural language understanding
- **Python** — pluggable backtesting engine
- **AlphaVantage** — historical daily price data (free tier: ~100 trading days)

---

## Features

### Natural-Language Strategy Parsing (LLM Mode)
Users can write free-form strategy descriptions, and the system automatically converts them into structured configurations:

**Examples:**
- "Buy when the 10-day MA crosses above the 50-day MA, sell when it crosses below"
- "Invest $1000 every 7 days with initial cash $5000"
- "DCA $500 weekly"
- "Buy and hold long term"

The LLM (OpenAI GPT-4o-mini) parses the description and returns a structured config:

```json
{
  "type": "ma_cross",
  "params": {"short_window": 10, "long_window": 50},
  "initial_cash": 5000
}
```

### Manual Mode
Alternatively, users can manually select a strategy type and set parameters directly through the UI.

### Supported Strategies

1. **Moving Average Crossover (ma_cross)**
   - Buy when short MA crosses above long MA
   - Sell when short MA crosses below long MA
   - Parameters: `short_window`, `long_window`

2. **Dollar-Cost Averaging (dca)**
   - Invest a fixed amount at regular intervals
   - Parameters: `interval_days`, `buy_amount`
   - Supports `initial_cash` extraction from LLM

3. **Buy and Hold**
   - Purchase at the start and hold until the end
   - Parameters: `buy_fraction` (default: 1.0)

### Backtesting Metrics
- Initial Cash / Final Equity
- Total Return / Annualized Return
- Maximum Drawdown
- Number of Trades / Win Rate
- Equity Curve Visualization

---

## Setup

### Prerequisites
- Python 3.8+
- Modal account (for LLM endpoint)
- OpenAI API key
- AlphaVantage API key (free tier available)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd "MCP Hackathon"
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   
   Create a `.env` file in the project root:
   ```env
   ALPHAVANTAGE_API_KEY=your_alphavantage_api_key
   MODAL_STRATEGY_URL=https://your-username--strategy-config-service-strategy-config-web.modal.run
   OPENAI_API_KEY=your_openai_api_key
   ```

4. **Deploy Modal endpoint**
   
   The Modal app hosts the LLM strategy parser. Deploy it with:
   ```bash
   modal deploy modal_app.py
   ```
   
   After deployment, Modal will provide a URL. Update `MODAL_STRATEGY_URL` in your `.env` file.

5. **Set up Modal Secret**
   
   In Modal web UI, create a Secret named `openai-secret` with:
   ```
   OPENAI_API_KEY=your_openai_api_key
   ```

### Running the Application

```bash
python app.py
```

The Gradio interface will be available at `http://127.0.0.1:7860`

---

## Usage

### LLM Mode (Recommended)

1. Select **"LLM"** from the Strategy Mode dropdown
2. Enter a natural language strategy description
3. Optionally specify initial cash in the description (e.g., "with initial cash $5000")
4. Click "Run Backtest"

**Example inputs:**
- "Buy when 10-day MA crosses above 50-day MA, sell when it crosses below"
- "DCA $1000 every 7 days, initial cash = 5000"
- "Invest $500 weekly with starting capital $10000"

### Manual Mode

1. Select **"Manual"** from the Strategy Mode dropdown
2. Choose a strategy type (ma_cross, dca, or buy_and_hold)
3. Set the required parameters
4. Set initial cash
5. Click "Run Backtest"

---

## Data Limitations

**AlphaVantage Free Tier:**
- Provides approximately 100 trading days of historical data
- 25 API requests per day
- Start date must be within the last 100 days

The UI includes validation to ensure dates are within the available range.

---

## Project Structure

```
.
├── app.py                 # Main Gradio UI application
├── llm_strategy.py        # Client-side LLM strategy parser (calls Modal)
├── modal_app.py           # Modal deployment: LLM endpoint (OpenAI GPT-4o-mini)
├── backtest/
│   ├── engine.py          # Backtest orchestrator
│   ├── strategies.py      # Strategy implementations (ma_cross, dca, buy_and_hold)
│   ├── data.py            # AlphaVantage data fetcher
│   └── metrics.py         # Performance metrics calculation
├── requirements.txt       # Python dependencies
└── README.md             # This file
```

---

## How It Works

1. **User Input** → Gradio UI (`app.py`)
2. **LLM Parsing** → Modal endpoint (`modal_app.py`) calls OpenAI GPT-4o-mini
3. **Strategy Config** → Structured JSON returned to client (`llm_strategy.py`)
4. **Data Fetching** → AlphaVantage API (`backtest/data.py`)
5. **Backtesting** → Strategy execution (`backtest/strategies.py`)
6. **Metrics & Visualization** → Results displayed in UI

---

## API Keys

### AlphaVantage
- Free tier: Get your API key from https://www.alphavantage.co/support/#api-key
- Rate limit: 25 requests per day

### OpenAI
- Get your API key from https://platform.openai.com/api-keys
- Used by Modal endpoint for strategy parsing

### Modal
- Sign up at https://modal.com
- Deploy the endpoint and get the URL for `MODAL_STRATEGY_URL`

---

## Troubleshooting

### "Modal endpoint returned non-200 status: 404"
- Ensure the Modal app is deployed: `modal deploy modal_app.py`
- Check that `MODAL_STRATEGY_URL` in `.env` matches the deployed endpoint URL

### "AlphaVantage API rate limit exceeded"
- Free tier allows 25 requests per day
- Wait 24 hours or upgrade to a premium plan

### "No data in specified date range"
- AlphaVantage free tier only provides ~100 trading days
- Use a start date within the last 100 days

### "LLM strategy parsing failed"
- Check that `OPENAI_API_KEY` is set in Modal Secret
- Verify the Modal endpoint is running
- Check network connectivity to Modal

---

## License

[Add your license here]
