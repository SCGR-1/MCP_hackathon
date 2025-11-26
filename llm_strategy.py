# llm_strategy.py

import os
import json
from typing import Any, Dict

import requests


"""
本地侧的职责：
- 把自然语言策略描述发给 Modal 的 HTTP 接口（GET + query）
- 拿回一个 JSON，结构为：
  {
    "type": "ma_cross" 或 "dca",
    "params": { ... }
  }

Modal 端会负责解析描述。
需要环境变量：
  MODAL_STRATEGY_URL = "你的 Modal endpoint URL"
"""


def llm_generate_strategy_config(description: str) -> Dict[str, Any]:
    """
    调用 Modal 暴露的 HTTP 接口，将自然语言策略描述解析成 strategy_config。
    """
    url = os.getenv("MODAL_STRATEGY_URL")
    if not url:
        raise RuntimeError("环境变量 MODAL_STRATEGY_URL 未设置，无法调用 Modal 策略解析服务。")

    params = {"description": description}

    try:
        resp = requests.get(url, params=params, timeout=30)
    except Exception as e:
        raise RuntimeError(f"调用 Modal 接口失败：{e}")

    if resp.status_code != 200:
        raise RuntimeError(
            f"Modal 接口返回非 200 状态码：{resp.status_code}, 内容：{resp.text[:500]}"
        )

    try:
        data = resp.json()
    except json.JSONDecodeError as e:
        raise ValueError(f"Modal 返回的内容不是合法 JSON：{e}\n原始内容：{resp.text[:500]}")

    if "error" in data:
        raise ValueError(f"Modal 解析错误：{data['error']}")

    stype = data.get("type")
    params = data.get("params")

    if stype not in ("ma_cross", "dca"):
        raise ValueError(f"Modal 生成的策略类型不受支持: {stype}")
    if not isinstance(params, dict):
        raise ValueError(f"Modal 生成的 params 不是对象: {params}")

    return {
        "type": stype,
        "params": params,
    }
