# mcp_client_http_final.py
import asyncio
from fastmcp import Client

SERVER_URL = "http://localhost:8000/mcp"

async def main():
    async with Client(SERVER_URL) as client:
        tools = await client.list_tools()
        print("Tools:", [t.name for t in tools])

        resp = await client.call_tool(
            "parse_strategy",
            {"description": "buy if price dips 5% then sell when price rises 10%"}
        )
        if resp.is_error:
            print("Protocol error:", resp.content)
            return

        out = resp.data
        inner = getattr(out, "result", None)
        print("Inner result:", inner)

        if not isinstance(inner, dict):
            print("Unexpected structure — not a dict:", type(inner))
            return

        if not inner.get("ok", False):
            print("parse_strategy failed:", inner.get("error"))
            return

        cfg = inner.get("strategy_config")
        if not cfg:
            print("No strategy_config")
            return

        print("strategy_config:", cfg)

        resp2 = await client.call_tool(
            "run_backtest_tool",
            {
                "symbol": "AAPL",
                "start_date": "2023-01-01",
                "end_date": "2023-12-31",
                "strategy_config": cfg,
                "initial_cash": 10000.0
            }
        )
        if resp2.is_error:
            print("Backtest protocol error:", resp2.content)
            return

        out2 = resp2.data
        inner2 = getattr(out2, "result", None)
        print("Backtest result:", inner2)

if __name__ == "__main__":
    asyncio.run(main())
