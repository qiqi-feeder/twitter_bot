#!/usr/bin/env python3
import os
from dotenv import load_dotenv
from google import genai

load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")

print("Testing text generation...")
client = genai.Client(api_key=API_KEY)
response = client.models.generate_content(
    model="gemini-3-flash-preview",
    contents="Hello, respond with just 'OK'"
)
print(f"Result: {response.text}")
print("Success!")
