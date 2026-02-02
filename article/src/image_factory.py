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
    from .gen_config import GEMINI_TEXT_API_KEY, GEMINI_TEXT_BASE_URL, GEMINI_IMAGE_API_KEY, GEMINI_IMAGE_BASE_URL, GOOGLE_API_KEY, USE_OFFICIAL_GEMINI, ASSETS_DIR
except ImportError:
    import sys
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from gen_config import GEMINI_TEXT_API_KEY, GEMINI_TEXT_BASE_URL, GEMINI_IMAGE_API_KEY, GEMINI_IMAGE_BASE_URL, GOOGLE_API_KEY, USE_OFFICIAL_GEMINI, ASSETS_DIR

class ImageFactory:
    """
    Orchestrates the AI image generation workflow using custom providers.
    1. Text Reasoning: Gemini Pro (via aifuwu.icu) -> Visual Concept
    2. Image Generation: Gemini Image Preview (via apialt.mmw.ink) -> Image
    """

    def __init__(self):
        # Check which API to use
        self.use_official = USE_OFFICIAL_GEMINI
        
        if self.use_official:
            # Use official Google API
            self.official_key = GOOGLE_API_KEY
            print(f"✨ ImageFactory using Official Google Gemini API")
        else:
            # Use third-party proxies
            self.text_key = GEMINI_TEXT_API_KEY
            self.text_base = GEMINI_TEXT_BASE_URL
            self.image_key = GEMINI_IMAGE_API_KEY
            self.image_base = GEMINI_IMAGE_BASE_URL
            print(f"⚙️  ImageFactory using Third-party API proxies")

    def _get_visual_concept(self, news_content: str) -> dict:
        """
        Uses Gemini to generate professional cover image prompts (JSON format).
        Returns dict with 'prompt' and 'negative_prompt' fields.
        """
        if self.use_official:
            # Use official API
            if not self.official_key:
                print("⚠️ GOOGLE_API_KEY is missing!")
                return self._get_fallback_prompts()
            
            print(f"🧠 Generating cover prompts with Official Gemini API...")
            return self._generate_official_prompts(news_content)
        else:
            # Use third-party API (legacy)
            if not self.text_key:
                print("⚠️ GEMINI_TEXT_API_KEY is missing!")
                return self._get_fallback_prompts()
            
            print(f"🧠 Analyzing text using Third-party Gemini Pro ({self.text_base})...")
            return self._generate_legacy_prompts(news_content)
    
    def _generate_official_prompts(self, news_content: str) -> dict:
        """Generate prompts using official Google Gemini API"""
        import json
        
        system_instruction = """你是一个"新闻封面图提示词生成器"。
输入：一段当天日报（可能包含多条新闻摘要、标题、要点）。
输出：用于图像生成模型的单条英文提示词（prompt），用于生成一张 16:9 高质量黑白封面插画。
使用场景：用 gemini-3-pro-image-preview 生成封面图。
强制要求：输出必须只包含两个字段（JSON），不要包含任何解释性文字。

主题提炼与隐喻生成规则：

从日报中选择"最适合画成封面"的 1 个主题（优先：宏观趋势/科技/社会心理/经济变化/安全/注意力与信息过载；回避：血腥事故现场、未成年人、极端仇恨符号、明确政治宣传）。

把主题转成一个"象征性场景"（allegory）：用 1 个主角 + 1 个核心道具/空间 + 2–4 个外部威胁或对立元素来表现冲突。

场景必须"可读、单幅画讲清楚"，避免拼贴多新闻。

不要让模型在画面中出现可读文字；标题由后处理叠加。

风格（必须严格保持）：

Black-and-white only; high-contrast monochrome.

Intaglio etching / woodcut engraving / Victorian-era book illustration aesthetic.

Dense cross-hatching + stippling; crisp linework; no blur.

Dark humor + surreal symbolism, but not cute/cartoon.

No photorealism, no modern UI screenshots, no gradients.

构图与画面结构（必须严格保持）：

Aspect ratio: 16:9 horizontal cover illustration.

One clear focal point (main subject) slightly left-of-center.

Depth: foreground hint + midground action + background texture.

The entire frame should be highly detailed with dense cross-hatching and intricate linework.

约束/禁止项（必须写进 prompt）：

"NO readable text, NO letters, NO words, NO watermarks, NO logos, NO signatures, NO QR codes."

"No color. No photorealism. No modern brand marks."

Avoid depicting identifiable real persons; use generic silhouettes.

输出格式（必须严格遵守）：
只输出 JSON：

prompt: 一条英文 prompt（150–280 词），包含：主题隐喻、场景要素、构图要求、风格、禁止项。

negative_prompt: 一条英文 negative prompt（可短），进一步强调禁止项与避免的风格漂移。

不要输出代码块，不要输出多余字段，不要输出解释。

示例输出格式（注意：不要复用示例内容，只复用格式）：
{
"prompt": "...",
"negative_prompt": "..."
}

现在开始：基于我提供的日报文本生成封面图 prompt。"""

        try:
            client = genai.Client(api_key=self.official_key)
            response = client.models.generate_content(
                model="gemini-3-flash-preview",
                contents=f"{system_instruction}\n\n日报文本：\n<<<\n{news_content[:2000]}\n>>>"
            )
            
            result_text = response.text.strip()
            
            # Remove markdown code blocks if present
            if result_text.startswith("```json"):
                result_text = result_text[7:]
            if result_text.startswith("```"):
                result_text = result_text[3:]
            if result_text.endswith("```"):
                result_text = result_text[:-3]
            result_text = result_text.strip()
            
            prompt_data = json.loads(result_text)
            print(f"✅ Prompts generated: {len(prompt_data.get('prompt', ''))} chars")
            return prompt_data
            
        except json.JSONDecodeError as e:
            print(f"⚠️ JSON parse failed: {e}, using fallback")
            return self._get_fallback_prompts()
        except Exception as e:
            print(f"❌ Official API error: {e}")
            return self._get_fallback_prompts()
    
    def _generate_legacy_prompts(self, news_content: str) -> dict:
        """Generate prompts using legacy third-party API"""
        system_instruction = """
        You are an avant-garde Art Director. Your goal is to visualize abstract cryptocurrency news (volatility, regulations, whales) into a **Surreal, Monochrome Concept**.
        **Rules:**
        1. Use dark,mysterious metaphors (e.g., 'A stone maze floating in a void' for regulation).
        2. NO text, NO charts, NO coins.
        3. Keep the description concise and focused on the visual scene.
        """
        
        try:
            headers = {
                "Authorization": f"Bearer {self.text_key}",
                "Content-Type": "application/json"
            }
            url = f"{self.text_base}/v1/chat/completions"
            payload = {
                "model": "gemini-2.5-pro",
                "messages": [
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": f"News Content:\n{news_content[:2000]}"}
                ]
            }
            
            resp = httpx.post(url, headers=headers, json=payload, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                concept = data['choices'][0]['message']['content'].strip()
                
                # Convert to new format
                style_suffix = "High-contrast black and white ink illustration. Style of vintage woodcut, etching, and copperplate engraving. Use stippling and cross-hatching. No colors, strictly monochrome. Surreal, intricate details, mysterious atmosphere. Similar to M.C. Escher or Gustave Doré."
                
                return {
                    "prompt": f"{concept}. {style_suffix}",
                    "negative_prompt": "color, photorealism, text, letters, words, logos, watermarks"
                }
            
            print(f"⚠️ Legacy API failed {resp.status_code}")
            
        except Exception as e:
            print(f"❌ Legacy API error: {e}")
        
        return self._get_fallback_prompts()
    
    def _get_fallback_prompts(self) -> dict:
        """Return fallback prompts when API fails"""
        return {
            "prompt": "A surreal black and white engraving showing abstract cryptocurrency market volatility. Central figure: lone trader silhouette standing before cascading data streams. Dense cross-hatching, Victorian woodcut style. 16:9 horizontal. Entire frame highly detailed. NO text, NO letters, NO logos. High contrast monochrome only.",
            "negative_prompt": "color, photorealism, text, letters, words, logos, watermarks, signatures, modern UI, cartoon, cute style"
        }

    def _generate_image(self, prompt: str) -> bool:
        """
        Generates image using official or third-party API based on configuration.
        """
        if self.use_official:
            return self._generate_image_official(prompt)
        else:
            return self._generate_image_legacy(prompt)
    
    def _generate_image_official(self, prompt: str) -> bool:
        """Generate image using official Google Gemini API"""
        if not self.official_key:
            print("⚠️ GOOGLE_API_KEY is missing!")
            return False
        
        OUT_PATH = Path(ASSETS_DIR) / "cover.jpg"
        MODEL = "gemini-3-pro-image-preview"  # Official model
        IMAGE_SIZE = "2K"
        
        print(f"🖌️ Generating image with Official API...")
        print(f"   Model: {MODEL}")
        print(f"   Prompt: {prompt[:60]}...")
        
        try:
            client = genai.Client(api_key=self.official_key)
            
            contents = [types.Content(role="user", parts=[types.Part.from_text(text=prompt)])]
            config = types.GenerateContentConfig(
                response_modalities=["IMAGE", "TEXT"],
                image_config=types.ImageConfig(image_size=IMAGE_SIZE),
            )
            
            response = client.models.generate_content(
                model=MODEL,
                contents=contents,
                config=config
            )
            
            # Extract image bytes
            image_bytes = None
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
            
            if not image_bytes:
                print("   ❌ No image data returned")
                return False
            
            return self._save_and_process_image(image_bytes, OUT_PATH)
            
        except Exception as e:
            print(f"   ❌ Official API Error: {e}")
            return False
    
    def _generate_image_legacy(self, prompt: str) -> bool:
        """Generate image using third-party API (legacy)"""
        if not self.image_key:
            print("⚠️ GEMINI_IMAGE_API_KEY is missing!")
            return False

    def _save_and_process_image(self, image_bytes: bytes, output_path: Path) -> bool:
        """Shared method to save and post-process image (16:9 crop + B&W)"""
        try:
            from PIL import ImageOps
            
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Load image
            img = Image.open(io.BytesIO(image_bytes))
            
            # 1. Convert to grayscale (black & white)
            img_bw = img.convert('L')
            
            # 2. Enhance contrast for better B&W effect
            img_bw = ImageOps.autocontrast(img_bw, cutoff=2)
            
            # 3. Crop/resize to 16:9 aspect ratio
            width, height = img_bw.size
            target_ratio = 16 / 9  # 1.778
            current_ratio = width / height
            
            if current_ratio > target_ratio:
                # Image too wide, crop left/right
                new_width = int(height * target_ratio)
                left = (width - new_width) // 2
                img_bw = img_bw.crop((left, 0, left + new_width, height))
            elif current_ratio < target_ratio:
                # Image too tall, crop top/bottom
                new_height = int(width / target_ratio)
                top = (height - new_height) // 2
                img_bw = img_bw.crop((0, top, width, top + new_height))
            
            # Save with high quality
            img_bw.save(output_path, format="JPEG", quality=95)
            
            final_width, final_height = img_bw.size
            print(f"   ✅ Image Saved: {output_path}")
            print(f"   📐 Size: {final_width}x{final_height} (16:9)")
            print(f"   🎨 Effect: B&W + Contrast Enhanced")
            return True
        except Exception as e:
            print(f"   ❌ Save Error: {e}")
            return False
    
    def _generate_image_legacy_core(self, prompt: str) -> bool:
        """Core legacy image generation logic (preserve existing third-party API code)"""
        OUT_PATH = Path(ASSETS_DIR) / "cover.jpg"
        MODEL = "[A]gemini-3-pro-image-preview"
        IMAGE_SIZE = "2K"
        BASE_URL = self.image_base

        print(f"🖌️ Generating Image via {BASE_URL}...")
        print(f"   Prompt: {prompt[:50]}...")

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
        
        # Extract image bytes from response
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
        
        # Use shared save and process method
        return self._save_and_process_image(image_bytes, OUT_PATH)

    def generate_article_cover(self, news_content: str) -> str:
        """
        Main entry point.
        """
        # 1. Get Prompts (returns dict with 'prompt' and 'negative_prompt')
        prompt_data = self._get_visual_concept(news_content)
        
        # 2. Extract main prompt
        final_prompt = prompt_data.get("prompt", "")
        
        if not final_prompt:
            print("⚠️ No valid prompt generated")
            return ""
        
        # 3. Generate Image
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
