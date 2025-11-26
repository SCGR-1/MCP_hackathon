import re
from typing import Dict, Any

import modal

# 使用新的 App API
image = modal.Image.debian_slim().pip_install("fastapi[standard]")
app = modal.App("strategy-config-service", image=image)


def simple_rule_based_strategy(description: str) -> Dict[str, Any]:
    """
    简单规则解析器（“假 LLM”）：
    - 包含“定投”/DCA/“每 X 天” → dca 策略
    - 否则 → 均线策略 ma_cross，尽量从文本中抓两个数字作为短/长均线
    """
    text = description.lower()

    # 判断定投
    if ("定投" in description) or ("dca" in text) or ("每" in description and "天" in description):
        return {
            "type": "dca",
            "params": {
                "interval_days": 7,
                "buy_amount": 1000.0,
            },
        }

    # 否则默认均线交叉
    numbers = re.findall(r"\d+", description)
    short_window = 10
    long_window = 50
    if len(numbers) >= 2:
        short_window = int(numbers[0])
        long_window = int(numbers[1])
        if short_window >= long_window:
            short_window, long_window = long_window, short_window

    return {
        "type": "ma_cross",
        "params": {
            "short_window": short_window,
            "long_window": long_window,
        },
    }


@app.function()
@modal.fastapi_endpoint()  # 默认 GET
def strategy_config_web(description: str = "") -> Dict[str, Any]:
    """
    GET 端点：
    - 通过 query string 接收 ?description=...
    - 返回策略配置 JSON
    """
    description = (description or "").strip()
    if not description:
        return {"error": "description is required"}

    cfg = simple_rule_based_strategy(description)

    stype = cfg.get("type")
    params = cfg.get("params", {})

    if stype not in ("ma_cross", "dca"):
        return {"error": f"unsupported strategy type: {stype}"}
    if not isinstance(params, dict):
        return {"error": "params must be a dict"}

    return cfg
