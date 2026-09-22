import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("GEMINI_API_KEY not found in .env")

client = genai.Client(api_key=api_key)

try:
    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents="Explain AI scheduling in 2 simple sentences."
    )

    print("\nGemini says:")
    print(response.text)

except Exception as e:
    print("\nGemini API error:")
    print(e)