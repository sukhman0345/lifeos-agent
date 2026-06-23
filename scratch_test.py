import os
import asyncio
from google.genai import Client
from dotenv import load_dotenv

load_dotenv()
api_key = os.environ.get("GOOGLE_API_KEY")
print(f"API Key: {api_key[:10]}...")

client = Client(api_key=api_key)

async def test_model(model_name):
    try:
        response = await client.aio.models.generate_content(
            model=model_name,
            contents="Say hello"
        )
        print(f"✅ Model {model_name} succeeded: {response.text}")
        return True
    except Exception as e:
        print(f"❌ Model {model_name} failed: {e}")
        return False

async def main():
    models = [
        "gemini-2.5-flash",
        "gemini-2.0-flash",
        "gemini-1.5-flash",
        "gemini-1.5-pro",
        "gemini-2.0-flash-lite",
        "gemini-2.0-pro-exp",
    ]
    for model in models:
        await test_model(model)

if __name__ == "__main__":
    asyncio.run(main())
