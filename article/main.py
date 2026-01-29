import sys
from playwright.sync_api import sync_playwright
from src.browser_manager import BrowserFactory
from src.content_loader import ContentLoader
from src.publisher_bot import XArticleBot
import time

def main():
    print("Initializing X Article Automation System (Attach Mode)...")

    # 1. Initialize Content
    loader = ContentLoader()
    article_data = loader.get_next_article()
    print(f"Loaded Article: {article_data['title']}")

    # 2. Initialize Browser
    # Default to 'attach' to solve the detection issue
    try:
        browser_strategy = BrowserFactory.get_strategy("attach")
    except Exception as e:
        print(f"Configuration Error: {e}")
        return

    with sync_playwright() as p:
        try:
            browser_context = browser_strategy.start(p)
        except RuntimeError as e:
            print("="*60)
            print("CRITICAL ERROR: Could not connect to Chrome.")
            print("Please ensure you have launched Chrome manually with the following command:")
            print(r'  "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:\chrome_debug_profile"')
            print("="*60)
            print(f"Details: {e}")
            return
        
        # Get existing pages or create new
        if not browser_context.pages:
            page = browser_context.new_page()
        else:
            # Usually the user has a tab open. Let's use the active one or first one.
            page = browser_context.pages[0]

        # 3. Initialize Bot
        bot = XArticleBot(page)

        # 4. Execute Workflow
        bot.go_to_editor()

        # Check login
        if not bot.is_logged_in():
            print("User is NOT logged in. Since you are in Attach Mode, please Log In manually properly.")
            print("Script will pause for 60 seconds...")
            page.wait_for_timeout(60000) 

        if bot.is_logged_in():
            print("User is logged in. Proceeding...")
            bot.draft_article(
                title=article_data['title'],
                body=article_data['body'],
                cover_image_path=article_data['cover_image']
            )
            # bot.publish() # Uncomment to enable actual publishing

        print("Workflow completed.")
        
        # Cleanup
        browser_strategy.stop(browser_context)
        print("Done.")

if __name__ == "__main__":
    main()
