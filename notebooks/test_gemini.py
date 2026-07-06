import os
from google import genai
from dotenv import load_dotenv

load_dotenv()
client = genai.Client()

for model_name in ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]:
    try:
        response = client.models.generate_content(
            model=model_name,
            contents="Hello, this is a test.",
        )
        print(f"Success with model {model_name}: {response.text}")
        break
    except Exception as e:
        print(f"Failed with model {model_name}: {e}")
