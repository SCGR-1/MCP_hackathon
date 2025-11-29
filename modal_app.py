import os
import json
from typing import Dict, Any

import modal
from openai import OpenAI

# --- Image & secrets setup ----------------------------------------------------

# 1) Image with FastAPI + OpenAI client installed
image = (
    modal.Image.debian_slim()
    .pip_install("fastapi[standard]")
    .pip_install("openai")
)

# 2) Secret that provides OPENAI_API_KEY as an env var inside the container.
#    In Modal web UI, create a Secret named "openai-secret" with a key:
#      OPENAI_API_KEY = your_api_key_here
openai_secret = modal.Secret.from_name("openai-secret")

# 3) App binds that secret, so inside functions we can read os.environ["OPENAI_API_KEY"]
app = modal.App(
    "strategy-config-service",
    image=image,
    secrets=[openai_secret],
)


# --- LLM-based parser ---------------------------------------------------------

def llm_strategy_from_description(description: str) -> Dict[str, Any]:
    """
    Call OpenAI GPT to convert a natural-language description into a
    structured strategy_config JSON:

        {
          "type": "ma_cross" | "dca" | "buy_and_hold" | "other",
          "params": { ... },
          "initial_cash": number (optional)
        }
    """

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set in environment.")

    client = OpenAI(api_key=api_key)

    prompt = f"""You are a trading strategy parser. Analyze the user's description and determine the best matching strategy type.

Convert the user's natural-language description into a JSON object with this EXACT schema:

{{
  "type": "ma_cross" | "dca" | "buy_and_hold" | "other",
  "params": {{
    // strategy-specific parameters (see below)
  }},
  "initial_cash": number (optional, only include if mentioned in description)
}}

Supported strategy types:

1) "ma_cross" (moving average crossover)
   - Use when: User describes buying/selling based on moving average crossovers
   - params:
       - "short_window": integer > 0 (e.g., 10, 20)
       - "long_window": integer > short_window (e.g., 50, 60)
   - Examples: 
       * "Buy when 10-day MA crosses above 50-day MA, sell when it crosses below"
       * "Use 20/60 moving average crossover strategy"
       * "When short MA crosses long MA, enter position"

2) "dca" (dollar-cost averaging)
   - Use when: User describes investing fixed amounts at regular intervals
   - params:
       - "interval_days": integer > 0 (e.g., 7, 14, 30)
       - "buy_amount": float > 0 (e.g., 1000.0, 500.0)
   - Examples:
       * "Invest $1000 every 7 days"
       * "DCA $500 weekly"
       * "Buy $2000 every month"

3) "buy_and_hold"
   - Use when: User describes buying and holding long-term without selling
   - params:
       - "buy_fraction": float between 0 and 1 (default: 1.0 for 100%)
   - Examples:
       * "Buy and hold long term"
       * "Purchase and hold indefinitely"
       * "Long-term investment strategy"

4) "other"
   - Use when: The description does not clearly match any of the above strategies
   - params: {{}} (empty object)
   - Examples:
       * "Sell when price drops 10%"
       * "Buy on RSI oversold, sell on RSI overbought"
       * "Options trading strategy"
       * "Day trading with stop loss"

Additional fields:
- "initial_cash": Extract if mentioned (e.g., "$5000", "with 10000 dollars", "initial capital 20000", "starting with $15000"). Omit if not mentioned.

Requirements:
- Choose the MOST APPROPRIATE strategy type. If unsure or the strategy doesn't fit, use "other".
- Extract all relevant parameters from the description.
- Use reasonable defaults if parameters are partially mentioned (e.g., if only one MA window mentioned, infer the other).
- Extract initial_cash if mentioned.
- Output ONLY valid JSON. No explanations, no markdown fences, no comments.

User description:
\"\"\"{description}\"\"\"
    """.strip()

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "You are a trading strategy parser. Always return valid JSON only, no other text."
            },
            {
                "role": "user",
                "content": prompt,
            }
        ],
        temperature=0.1,
        max_tokens=500,
        response_format={"type": "json_object"}
    )

    text = response.choices[0].message.content.strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM returned invalid JSON: {e}\nRaw text: {text}")

    stype = data.get("type")
    params = data.get("params", {})

    if stype not in ("ma_cross", "dca", "buy_and_hold", "other"):
        raise ValueError(f"Invalid strategy type from LLM: {stype}")
    if not isinstance(params, dict):
        raise ValueError("params must be a JSON object")

    return data


# --- FastAPI endpoint exposed via Modal ---------------------------------------

@app.function(secrets=[openai_secret])
@modal.fastapi_endpoint()
def strategy_config_web(description: str = "") -> Dict[str, Any]:
    """
    GET endpoint:
    - Called as:  GET ?description=...
    - Returns:    { "type": "...", "params": { ... }, "initial_cash": number (optional) }   or { "error": "..." }
    """
    description = (description or "").strip()
    if not description:
        return {"error": "description is required"}

    try:
        cfg = llm_strategy_from_description(description)
    except Exception as e:
        # Return error as JSON so the caller (llm_strategy.py) can show it nicely
        return {"error": f"LLM error: {e}"}

    return cfg
