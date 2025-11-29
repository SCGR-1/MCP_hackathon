import os
from dotenv import load_dotenv
from openai import OpenAI
import json

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("❌ OPENAI_API_KEY not found")
    exit(1)

client = OpenAI(api_key=api_key)

# Test the exact description the user used
test_description = "buy and hold initial cash = 5000"

print(f"Testing description: '{test_description}'\n")

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

2) "dca" (dollar-cost averaging)
   - Use when: User describes investing fixed amounts at regular intervals
   - params:
       - "interval_days": integer > 0 (e.g., 7, 14, 30)
       - "buy_amount": float > 0 (e.g., 1000.0, 500.0)

3) "buy_and_hold"
   - Use when: User describes buying and holding long-term without selling
   - params:
       - "buy_fraction": float between 0 and 1 (default: 1.0 for 100%)

4) "other"
   - Use when: The description does not clearly match any of the above strategies
   - params: {{}} (empty object)

Additional fields:
- "initial_cash": Extract if mentioned (e.g., "$5000", "with 10000 dollars", "initial capital 20000", "initial cash = 5000"). Omit if not mentioned.

Requirements:
- Choose the MOST APPROPRIATE strategy type. If unsure or the strategy doesn't fit, use "other".
- Extract all relevant parameters from the description.
- Use reasonable defaults if parameters are partially mentioned.
- Extract initial_cash if mentioned.
- Output ONLY valid JSON. No explanations, no markdown fences, no comments.

User description:
\"\"\"{test_description}\"\"\"
""".strip()

try:
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
    print("Raw LLM response:")
    print(text)
    print("\n" + "="*50 + "\n")
    
    data = json.loads(text)
    
    print("Parsed JSON:")
    print(json.dumps(data, indent=2))
    print("\n" + "="*50 + "\n")
    
    if "initial_cash" in data:
        print(f"✅ SUCCESS: initial_cash extracted = {data['initial_cash']}")
    else:
        print("❌ WARNING: initial_cash NOT found in response")
        print("   This means LLM didn't extract it from the description")
    
except Exception as e:
    print(f"❌ Error: {e}")

