# llm_strategy.py

import os
import json
from typing import Any, Dict

import requests


def llm_generate_strategy_config(description: str) -> Dict[str, Any]:
    """
    Calls Modal HTTP endpoint to parse natural language strategy description into strategy_config.
    Requires environment variable: MODAL_STRATEGY_URL
    """
    url = os.getenv("MODAL_STRATEGY_URL")
    if not url:
        raise RuntimeError("MODAL_STRATEGY_URL environment variable not set")

    params = {"description": description}

    try:
        resp = requests.get(url, params=params, timeout=30)
    except Exception as e:
        raise RuntimeError(f"Failed to call Modal endpoint: {e}")

    if resp.status_code != 200:
        raise RuntimeError(
            f"Modal endpoint returned non-200 status: {resp.status_code}, content: {resp.text[:500]}"
        )

    try:
        data = resp.json()
    except json.JSONDecodeError as e:
        raise ValueError(f"Modal response is not valid JSON: {e}\nContent: {resp.text[:500]}")

    if "error" in data:
        raise ValueError(f"Modal parsing error: {data['error']}")

    stype = data.get("type")
    params = data.get("params")

    if stype not in ("ma_cross", "dca", "buy_and_hold", "other"):
        raise ValueError(f"Invalid strategy type from Modal: {stype}")
    if not isinstance(params, dict):
        raise ValueError(f"Modal params is not a dict: {params}")

    result = {
        "type": stype,
        "params": params,
    }
    
    # Include initial_cash if present
    if "initial_cash" in data:
        result["initial_cash"] = data["initial_cash"]
    
    return result
