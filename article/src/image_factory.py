import os
import time
import io
import re
import httpx
from pathlib import Path
from PIL import Image

# New Google GenAI SDK (For Image)
from google import genai
from google.genai import types

# Old Google GenerativeAI SDK (For Text - Kept for compatibility if needed, or switched to OpenAI if easier)
# Actually, let's use the new SDK for both if possible, OR stick to requests for Text if simple.
# For now, I'll use google.generativeai for text as before, but allow custom endpoint.
import google.generativeai as genai_old

try:
    from .gen_config import GEMINI_TEXT_API_KEY, GEMINI_TEXT_BASE_URL, GEMINI_IMAGE_API_KEY, GEMINI_IMAGE_BASE_URL, ASSETS_DIR
except ImportError:
    import sys
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from gen_config import GEMINI_TEXT_API_KEY, GEMINI_TEXT_BASE_URL, GEMINI_IMAGE_API_KEY, GEMINI_IMAGE_BASE_URL, ASSETS_DIR

class ImageFactory:
    """
    Orchestrates the AI image generation workflow using custom providers.
    1. Text Reasoning: Gemini Pro (via aifuwu.icu) -> Visual Concept
    2. Image Generation: Gemini Image Preview (via apialt.mmw.ink) -> Image
    """

    def __init__(self):
        self.text_key = GEMINI_TEXT_API_KEY
        self.text_base = GEMINI_TEXT_BASE_URL
        
        self.image_key = GEMINI_IMAGE_API_KEY
        self.image_base = GEMINI_IMAGE_BASE_URL
        
        # Configure Text Model (Old SDK or OpenAI compatible?)
        # Since 'api.aifuwu.icu' is likely an OpenAI-compatible proxy for Gemini, 
        # using the standard google-generativeai with custom client_options might be tricky if the path isn't standard.
        # However, let's try to use the NEW SDK for text as well if it supports it?
        # Or just use the old one with transport overrides.
        # For safety/simplicity, I will use the NEW SDK for Image (as provided) and Old SDK for Text (standard configure).
        # IF text_base is set, we try to use it.
        
        if self.text_key:
            # Note: Configure for custom endpoint in old SDK is not always straightforward.
            # We'll try standard config first. If user provided a URL, maybe they expect OpenAI client?
            # Let's assume standard Gemini behavior for now, or use OpenAI client for text if needed.
            # But creating ImageFactory shouldn't crash.
            pass

    def _get_visual_concept(self, news_content: str) -> str:
        """
        Uses Gemini (Text) to extract a surreal, monochrome visual concept.
        """
        if not self.text_key:
            print("⚠️ GEMINI_TEXT_API_KEY is missing!")
            return "Abstract crypto digital network, high contrast monochrome."

        print(f"🧠 Analyzing text using Gemini Pro ({self.text_base})...")
        
        system_instruction = """
        You are an avant-garde Art Director. Your goal is to visualize abstract cryptocurrency news (volatility, regulations, whales) into a **Surreal, Monochrome Concept**.
        **Rules:**
        1. Use dark, mysterious metaphors (e.g., 'A stone maze floating in a void' for regulation).
        2. NO text, NO charts, NO coins.
        3. Keep the description concise and focused on the visual scene.
        """
        
        prompt = f"{system_instruction}\n\nNews Content:\n{news_content[:2000]}"
        
        # Using OpenAI Client for Text Reasoning if the URL is custom (Aifuwu usually mimics OpenAI)
        # OR using generic requests to be safe.
        # Let's try requests to the chat/completions endpoint if it follows OpenAI format, 
        # OR use google.generativeai if it's a real Google proxy.
        # Given "api.aifuwu.icu" usually serves OpenAI-compatible APIs for various models:
        
        try:
            # Attempt using the NEW SDK for text as well?
            # client = genai.Client(api_key=self.text_key, http_options=types.HttpOptions(base_url=self.text_base))
            # But the model name might be 'gemini-1.5-pro'
            
            # Let's try standard requests to be robust against SDK version issues for the custom proxy.
            headers = {
                "Authorization": f"Bearer {self.text_key}",
                "Content-Type": "application/json"
            }
            # Assuming OpenAI compatible endpoint
            url = f"{self.text_base}/v1/chat/completions" 
            payload = {
                "model": "gemini-2.5-pro", # Updated based on user's available model list
                "messages": [
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": f"News Content:\n{news_content[:2000]}"}
                ]
            }
            
            # Fallback if it's actually Google native proxy?
            # Let's try OpenAI format first as it's common for 3rd party aggregators.
            
            resp = httpx.post(url, headers=headers, json=payload, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                return data['choices'][0]['message']['content'].strip()
            
            # If that failed, maybe it IS a Google native proxy?
            # Let's try the Old SDK with client_options.
            # genai_old.configure(api_key=self.text_key, client_options={"api_endpoint": self.text_base})
            # model = genai_old.GenerativeModel('gemini-1.5-pro')
            # res = model.generate_content(prompt)
            # return res.text
            
            print(f"⚠️ Text Gen Failed {resp.status_code}: {resp.text}")
            
        except Exception as e:
            print(f"❌ Text Gen Error: {e}")
            
        return "Surreal black and white digital landscape, abstract financial structures."

    def _generate_image(self, prompt: str) -> bool:
        """
        Generates image using the User's Provided Code Snippet (adapted).
        """
        if not self.image_key:
            print("⚠️ GEMINI_IMAGE_API_KEY is missing!")
            return False

        OUT_PATH = Path(ASSETS_DIR) / "cover.jpg"
        MODEL = "[A]gemini-3-pro-image-preview" # As requested
        IMAGE_SIZE = "2K"
        BASE_URL = self.image_base

        print(f"🖌️ Generating Image via {BASE_URL}...")
        print(f"   Prompt: {prompt[:50]}...")

        # Construct Content
        contents = [types.Content(role="user", parts=[types.Part.from_text(text=prompt)])]
        config = types.GenerateContentConfig(
            response_modalities=["IMAGE", "TEXT"],
            image_config=types.ImageConfig(image_size=IMAGE_SIZE),
        )

        def call(*, bearer: bool) -> object:
            if bearer:
                client = genai.Client(
                    vertexai=True,
                    http_options=types.HttpOptions(
                        base_url=BASE_URL,
                        timeout=300000,
                        headers={"Authorization": f"Bearer {self.image_key}"},
                    ),
                )
            else:
                client = genai.Client(
                    api_key=self.image_key,
                    http_options=types.HttpOptions(base_url=BASE_URL or None, timeout=300000),
                )
            return client.models.generate_content(model=MODEL, contents=contents, config=config)

        try:
            response = call(bearer=False)
        except Exception as e:
            print(f"   ⚠️ Standard Auth failed ({e}), trying Bearer...")
            try:
                response = call(bearer=True)
            except Exception as e2:
                print(f"   ❌ Image Gen Failed: {e2}")
                return False

        image_bytes: bytes | None = None
        texts: list[str] = []
        candidates = getattr(response, "candidates", None) or []
        for cand in candidates:
            content = getattr(cand, "content", None)
            if content is None:
                continue
            parts = getattr(content, "parts", None) or []
            for part in parts:
                inline = getattr(part, "inline_data", None)
                if inline is not None:
                    data = getattr(inline, "data", None)
                    if data and image_bytes is None:
                        image_bytes = data
                text = getattr(part, "text", None)
                if isinstance(text, str) and text.strip():
                    texts.append(text)

        # Fallback to URL download if no inline bytes
        if image_bytes is None:
            urls = re.findall(r"https?://[^\s)]+", "\n".join(texts))
            urls = list(dict.fromkeys([u.strip() for u in urls if u.strip()]))
            if not urls:
                print("   ❌ Model returned no inline image and no image URL.")
                return False
                
            timeout = httpx.Timeout(connect=10.0, read=60.0, write=60.0, pool=10.0)
            with httpx.Client(timeout=timeout, follow_redirects=True) as client:
                for url in urls[:6]:
                    resp = client.get(url)
                    if resp.status_code != 200:
                        continue
                    data = bytes(resp.content or b"")
                    if not data:
                        continue
                    image_bytes = data
                    break
            if image_bytes is None:
                print("   ❌ Downloaded URLs, but got empty data.")
                return False

        # Save Image
        try:
            OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
            # Resize/Crop to 5:2 if possible?
            # 2K is likely 2048x2048 or 2048xSomething.
            # User workflow asks for 5:2 coverage.
            # Let's just save it first. Crop logic can be added if needed.
            Image.open(io.BytesIO(image_bytes)).save(OUT_PATH, format="JPEG")
            print(f"   ✅ Image Saved: {OUT_PATH}")
            return True
        except Exception as e:
            print(f"   ❌ Save Error: {e}")
            return False

    def generate_article_cover(self, news_content: str) -> str:
        """
        Main entry point.
        """
        # 1. Get Concept
        concept = self._get_visual_concept(news_content)
        
        # 2. Add Style Suffix
        style_suffix = "High-contrast black and white ink illustration. Style of vintage woodcut, etching, and copperplate engraving. Use stippling and cross-hatching. No colors, strictly monochrome. Surreal, intricate details, mysterious atmosphere. Similar to M.C. Escher or Gustave Doré."
        final_prompt = f"{concept}. {style_suffix}"
        
        # 3. Generate
        success = self._generate_image(final_prompt)
        
        target_path = ASSETS_DIR / "cover.jpg"
        if success:
            return str(target_path)
        else:
            return ""

# Singleton
image_factory = ImageFactory()

if __name__ == "__main__":
    # Test
    test_news = "Bitcoin whales are accumulating while regulation fears loom over the defi market."
    image_factory.generate_article_cover(test_news)
