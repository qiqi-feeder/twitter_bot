
import os
import sys
from google import genai
from google.genai import types

# Config
PROXY_URL = "socks5://032bd1fc:59138690@us25.kookeey.info:22448"
API_KEY = os.getenv("GEMINI_IMAGE_API_KEY", "dummy_key")
BASE_URL = "https://apialt.mmw.ink"

# Set Proxy Env Vars
os.environ['HTTP_PROXY'] = PROXY_URL
os.environ['HTTPS_PROXY'] = PROXY_URL
os.environ['ALL_PROXY'] = PROXY_URL

print(f"Testing connection to {BASE_URL} via {PROXY_URL}")

try:
    client = genai.Client(
        api_key=API_KEY,
        http_options=types.HttpOptions(base_url=BASE_URL, timeout=10000),
    )
    
    # We just want to see if we can connect. A 401 or 403 is fine (auth error), 
    # but a Connection Error means proxy failed.
    # We utilize a simple dry run or model list if possible, but generate_content is what fails.
    
    MODEL = "gemini-3-pro-image-preview"
    contents = [types.Content(role="user", parts=[types.Part.from_text(text="test")])]
    config = types.GenerateContentConfig(
        response_modalities=["TEXT"],
    )

    print("Attempting request...")
    response = client.models.generate_content(model=MODEL, contents=contents, config=config)
    print("Success (unexpected if key is dummy, but connection worked)")
    
except Exception as e:
    print(f"Caught Exception: {e}")
