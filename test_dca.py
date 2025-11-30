import pandas as pd
from backtest.strategies import run_dca_strategy

# Create test data
dates = pd.date_range('2024-01-01', periods=30, freq='D')
df = pd.DataFrame({
    'date': dates,
    'open': [100.0] * 30,
    'high': [105.0] * 30,
    'low': [95.0] * 30,
    'close': [100.0 + i * 0.5 for i in range(30)],  # Price increases over time
    'volume': [1000000] * 30
})

# Test DCA strategy
params = {
    'interval_days': 7,
    'buy_amount': 1000.0
}

initial_cash = 10000.0

print(f"Initial cash: {initial_cash}")
print(f"Buy amount: {params['buy_amount']}")
print(f"Interval: {params['interval_days']} days")
print(f"Data range: {df['date'].min()} to {df['date'].max()}")
print(f"Total days: {(df['date'].max() - df['date'].min()).days}")
print()

result = run_dca_strategy(df, params, initial_cash)

print(f"Number of trades: {result['metrics']['num_trades']}")
print(f"Initial cash: {result['metrics']['initial_cash']}")
print(f"Final equity: {result['metrics']['final_equity']}")
print(f"Total return: {result['metrics']['total_return']*100:.2f}%")
print()

if result['trades']:
    print("Trades:")
    for i, trade in enumerate(result['trades'][:5], 1):
        print(f"  {i}. {trade['entry_date']}: Buy {trade['shares']:.4f} shares @ ${trade['entry_price']:.2f}")
else:
    print("No trades executed!")

print()
print(f"Equity curve (first 5 and last 5):")
for i, eq in enumerate(result['equity_curve'][:5]):
    print(f"  {eq['date']}: ${eq['equity']:.2f}")
print("  ...")
for eq in result['equity_curve'][-5:]:
    print(f"  {eq['date']}: ${eq['equity']:.2f}")

