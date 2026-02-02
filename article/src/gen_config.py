import os
from pathlib import Path
from dotenv import load_dotenv

# Load Env
load_dotenv()

# Image Generation Settings
# 1. Text Reasoning (Gemini Pro via aifuwu)
GEMINI_TEXT_API_KEY = os.getenv("GEMINI_TEXT_API_KEY") # Orig: GOOGLE_API_KEY
GEMINI_TEXT_BASE_URL = os.getenv("GEMINI_TEXT_BASE_URL", "https://api.aifuwu.icu/").rstrip("/")

# 2. Image Generation (Banana via mmw)
GEMINI_IMAGE_API_KEY = os.getenv("GEMINI_IMAGE_API_KEY") # Orig: BANANA_API_KEY
GEMINI_IMAGE_BASE_URL = os.getenv("GEMINI_IMAGE_BASE_URL", "https://apialt.mmw.ink").rstrip("/")

# 3. Official Google Gemini API (Direct)
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")  # Official API key
USE_OFFICIAL_GEMINI = os.getenv("USE_OFFICIAL_GEMINI", "true").lower() == "true"  # Toggle: true=official, false=third-party

# Project Base Paths
BASE_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = BASE_DIR / "assets"
USER_DATA_DIR = BASE_DIR / "user_data"

# X (Twitter) URLs
X_HOME_URL = "https://x.com/home"
X_COMPOSE_URL = "https://x.com/compose/post" 
X_ARTICLE_EDITOR_URL = "https://x.com/compose/articles"

# Browser Settings
CHROME_EXECUTABLE_PATH = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
HEADLESS = False
DEFAULT_VIEWPORT = {"width": 1280, "height": 720}
CHROME_DEBUG_PORT = 9222
CHROME_DEBUGGER_ADDRESS = "100.103.97.106"

# Bot Settings
IMPLICIT_WAIT = 5000  # ms
