import os
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables from .env file
load_dotenv()

# Get API key from environment
api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    print("❌ ERROR: OPENAI_API_KEY not found in environment variables")
    print("Please make sure:")
    print("1. You have a .env file in the project root")
    print("2. The .env file contains: OPENAI_API_KEY=your_key_here")
    exit(1)

print(f"✓ Found OPENAI_API_KEY (length: {len(api_key)} characters)")
print(f"  Key starts with: {api_key[:10]}...")

# Test the API key
print("\n🔍 Testing OpenAI API connection...")
try:
    client = OpenAI(api_key=api_key)
    
    # Make a simple test call
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "user", "content": "Say 'API key is working' if you can read this."}
        ],
        max_tokens=20
    )
    
    result = response.choices[0].message.content
    print(f"✅ SUCCESS! OpenAI API is working.")
    print(f"   Response: {result}")
    print(f"\n✓ Your API key is valid and ready to use!")
    
except Exception as e:
    print(f"❌ ERROR: Failed to connect to OpenAI API")
    print(f"   Error: {e}")
    print("\nPossible issues:")
    print("1. Invalid API key")
    print("2. No internet connection")
    print("3. API key has insufficient credits")
    print("4. OpenAI service is down")
    exit(1)

