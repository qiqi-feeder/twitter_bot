from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from playwright.sync_api import sync_playwright, BrowserContext, Playwright
import os
import shutil
import urllib.request
import json
from . import gen_config as config

class BrowserStrategy(ABC):
    """
    Abstract Base Class for Browser Initialization Strategies.
    """
    @abstractmethod
    def start(self, playwright: Playwright) -> BrowserContext:
        """
        Starts the browser and returns a BrowserContext.
        """
        pass

    @abstractmethod
    def stop(self, context: BrowserContext):
        """
        Closes the browser context and performs cleanup.
        """
        pass

class LocalChromeStrategy(BrowserStrategy):
    """
    Strategy for launching a local Google Chrome instance with persistent user data.
    """
    def __init__(self, user_data_dir: str = str(config.USER_DATA_DIR), headless: bool = config.HEADLESS):
        self.user_data_dir = user_data_dir
        self.headless = headless
        self._ensure_user_data_dir()

    def _ensure_user_data_dir(self):
        if not os.path.exists(self.user_data_dir):
            os.makedirs(self.user_data_dir)

    def start(self, playwright: Playwright) -> BrowserContext:
        print(f"Launching Local Chrome with User Data Dir: {self.user_data_dir}")
        executable_path = config.CHROME_EXECUTABLE_PATH
        if not os.path.exists(executable_path):
            print(f"Warning: Chrome not found at {executable_path}, using Playwright Chromium.")
            executable_path = None

        context = playwright.chromium.launch_persistent_context(
            user_data_dir=self.user_data_dir,
            executable_path=executable_path,
            headless=self.headless,
            viewport=config.DEFAULT_VIEWPORT,
            args=["--start-maximized", "--disable-infobars"]
        )
        return context

    def stop(self, context: BrowserContext):
        print("Closing Local Chrome Context...")
        context.close()

class AttachChromeStrategy(BrowserStrategy):
    """
    Strategy for connecting to an existing Chrome instance via CDP (Carbon DevTools Protocol).
    Required: Chrome must be started with --remote-debugging-port=9222
    """
    def __init__(self, port: int = config.CHROME_DEBUG_PORT):
        self.port = port
        self.base_url = f"http://{config.CHROME_DEBUGGER_ADDRESS}:{self.port}"

    def _get_ws_endpoint(self) -> str:
        """
        Manually fetch the endpoint to avoid Playwright's automatic discovery issues.
        """
        try:
            url = f"{self.base_url}/json/version"
            print(f"DEBUG: Fetching WebSocket URL from {url}")
            
            # Create an opener that ignores proxies (since we are connecting to local/tailscale)
            proxy_handler = urllib.request.ProxyHandler({})
            opener = urllib.request.build_opener(proxy_handler)
            
            with opener.open(url) as response:
                data = json.loads(response.read().decode())
                print(f"DEBUG: Browser Response: {data}")
                return data['webSocketDebuggerUrl']
        except Exception as e:
             raise RuntimeError(f"Could not fetch WebSocket endpoint from {url}. Is Chrome running? Error: {e}")

    def start(self, playwright: Playwright) -> BrowserContext:
        print(f"Connecting to existing Chrome on port {self.port}...")
        
        # 1. Manually resolve the WebSocket URL
        ws_url = self._get_ws_endpoint()
        print(f"Resolved WS URL: {ws_url}")

        # 2. Connect using the specific WS URL
        try:
            # FORCE NO_PROXY for this IP
            current_no_proxy = os.environ.get("no_proxy", "")
            target_ip = config.CHROME_DEBUGGER_ADDRESS
            if target_ip not in current_no_proxy:
                print(f"DEBUG: Adding {target_ip} to no_proxy")
                os.environ["no_proxy"] = f"{current_no_proxy},{target_ip}" if current_no_proxy else target_ip
                
            browser = playwright.chromium.connect_over_cdp(ws_url)
            
            if not browser.contexts:
                return browser.new_context()
            return browser.contexts[0]
        except Exception as e:
            raise RuntimeError(
                f"Failed to connect to Chrome at {ws_url}. Error: {e}"
            )

    def stop(self, context: BrowserContext):
        print("Disconnecting from Chrome (leaving it open)...")
        # For attach strategy, we generally don't want to close the browser, just disconnect.
        context.close()

class BrowserFactory:
    """
    Factory to create browser strategies.
    """
    @staticmethod
    def get_strategy(strategy_type: str = "attach") -> BrowserStrategy:
        if strategy_type == "local":
            return LocalChromeStrategy()
        elif strategy_type == "attach":
            return AttachChromeStrategy()
        else:
            raise ValueError(f"Unknown browser strategy: {strategy_type}")
