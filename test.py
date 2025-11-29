import os
import requests
import pprint

print("Script started.")

API_KEY = os.getenv("ALPHAVANTAGE_API_KEY", "")
print("API_KEY:", "exists" if API_KEY else "empty")

if not API_KEY:
    print("ALPHAVANTAGE_API_KEY environment variable not set, exiting.")
    raise SystemExit(1)

url = "https://www.alphavantage.co/query"
params = {
    "function": "TIME_SERIES_DAILY_ADJUSTED",
    "symbol": "AAPL",
    "apikey": API_KEY,
    "outputsize": "compact",
    "datatype": "json",
}

print("Requesting AlphaVantage...")
try:
    resp = requests.get(url, params=params, timeout=10)
except Exception as e:
    print("Request failed:", repr(e))
    raise SystemExit(1)

print("HTTP status code:", resp.status_code)
print("First 500 characters of response:")
print(resp.text[:500])

print("\nAttempting to parse as JSON:")
try:
    data = resp.json()
    pprint.pprint(data)
except Exception as e:
    print("JSON parsing failed:", repr(e))
