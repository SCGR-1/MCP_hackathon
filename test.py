import os
import requests
import pprint

print("脚本启动了。")  # 调试：确认脚本确实在执行

API_KEY = os.getenv("ALPHAVANTAGE_API_KEY", "")
print("读到的 API_KEY:", "存在" if API_KEY else "空")

if not API_KEY:
    print("环境变量 ALPHAVANTAGE_API_KEY 没有设置，退出。")
    raise SystemExit(1)

url = "https://www.alphavantage.co/query"
params = {
    "function": "TIME_SERIES_DAILY_ADJUSTED",
    "symbol": "AAPL",
    "apikey": API_KEY,
    "outputsize": "compact",
    "datatype": "json",
}

print("即将请求 AlphaVantage ...")
try:
    resp = requests.get(url, params=params, timeout=10)  # 加了 timeout，防止一直卡住
except Exception as e:
    print("请求阶段直接报错：", repr(e))
    raise SystemExit(1)

print("HTTP 状态码:", resp.status_code)
print("原始响应前 500 字符：")
print(resp.text[:500])

print("\n尝试解析为 JSON：")
try:
    data = resp.json()
    pprint.pprint(data)
except Exception as e:
    print("解析 JSON 失败：", repr(e))
