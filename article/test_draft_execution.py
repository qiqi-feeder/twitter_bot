from playwright.sync_api import sync_playwright
from src.browser_manager import BrowserFactory
from src.publisher_bot import XArticleBot
import time
import sys

def test_remote_draft():
    test_title = "Generation Skipped"
    test_body = "Skipped"
    cover_image = "assets/cover.jpg"

    # --- 1. PREPARE CONTENT (HISTORY CACHE OR GEN) ---
    print("🔄 Preparing Content...")
    try:
        # Add project root to path
        import os
        import asyncio
        from datetime import datetime, timedelta, timezone
        import pytz
        import uuid
        
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if project_root not in sys.path:
            sys.path.append(project_root)
        
        from get_data.main import fetch_rank_fuse_pipeline, assemble_daily_briefing, generate_article_content, CN_TZ
        from history.history_manager import history_manager

        # Determine Target Title Prefix
        now_cn = datetime.now(CN_TZ)
        if now_cn.hour < 12:
            title_prefix = "币圈早报（深度版）"
        else:
            title_prefix = "币圈晚报（深度版）"
        
        target_title_date = now_cn.strftime('%Y/%m/%d')
        test_title = f"{title_prefix} - {target_title_date}"
        print(f"📅 Target: {test_title}")

        # Step A: Check History (Last 12 Hours) for ARTICLE
        print("🔍 Checking history for existing ARTICLE...")
        history_items = history_manager.get_history(limit=20)
        found_cached = None
        
        now_utc = datetime.now(timezone.utc)
        
        for item in history_items:
            # Check ID/Content Type
            is_article = item.get('content_type') == 'article' or "深度版" in item.get('content', '')
            
            if is_article:
                try:
                    created_at_str = item.get('created_at')
                    created_at = datetime.fromisoformat(created_at_str)
                    if created_at.tzinfo is None:
                        created_at = created_at.replace(tzinfo=timezone.utc)
                    
                    if (now_utc - created_at) < timedelta(hours=12):
                        found_cached = item
                        break
                except:
                    continue
        
        if found_cached:
            print(f"✅ Found cached ARTICLE (ID: {found_cached.get('id')})")
            test_body = found_cached.get('content')
            test_title = f"{title_prefix} - {target_title_date}" # Enforce title format
        else:
            print("⚡️ No recent ARTICLE cache found. Generating FRESH Long-form Content (Top 60)...")
            
            # Step B: Generate Fresh (Top 60)
            full_title, test_body = asyncio.run(generate_article_content(hours=12))
            
            if test_body and "No events" not in test_body:
                test_title = full_title
                
                # Step C: Sync to Web (History) as ARTICLE
                job_id = f"article_gen_{int(time.time())}"
                history_manager.add_record(
                    job_id=job_id,
                    content=test_body,
                    scheduled_time=datetime.now(timezone.utc).isoformat(),
                    status='generated', 
                    source='article_bot',
                    mode='live',
                    content_type='article' # <--- KEY CHANGE
                )
                print(f"💾 Saved ARTICLE to History (ID: {job_id})")
            else:
                print("⚠️ No events found in pipeline.")
                test_title = f"{test_title} (Empty)"
                test_body = "No news events found for this period."

    except Exception as e:
        print(f"❌ Error preparing content: {e}")
        import traceback
        traceback.print_exc()
        test_title = "Generation Failed"
        test_body = f"Error: {e}"

    print("-" * 50)

    # Step B: Generate Cover Image (New Integration)
    print("🎨 Generating Cover Image...")
    try:
         # Add src path to find image_factory
        src_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src')
        if src_path not in sys.path:
            sys.path.append(src_path)
        
        from image_factory import image_factory
        
        # Use the "content" we just prepared
        cover_path = image_factory.generate_article_cover(test_body)
        if cover_path and os.path.exists(cover_path):
            print(f"✅ Cover Image Ready: {cover_path}")
            cover_image = cover_path # Use Absolute Path
        else:
            print("⚠️ Cover Generation failed, using default/fallback.")
    except Exception as e:
        print(f"❌ Cover Gen Error: {e}")

    # --- 2. BROWSER AUTOMATION ---
    print("🚀 Starting Browser Automation...")

    # Initialize Browser Strategy (Attach Mode)
    try:
        browser_strategy = BrowserFactory.get_strategy("attach")
        print(f"👉 Strategy: {browser_strategy.__class__.__name__}")
    except Exception as e:
        print(f"❌ Configuration Error: {e}")
        return

    # SET PROXY BYPASS EARLY (Before Playwright Starts)
    import os
    current_no_proxy = os.environ.get("no_proxy", "")
    target_ip = "100.103.97.106" # Tailscale IP
    if target_ip not in current_no_proxy:
        print(f"DEBUG: Adding {target_ip} to no_proxy (Early)")
        os.environ["no_proxy"] = f"{current_no_proxy},{target_ip}" if current_no_proxy else target_ip

    # Connect and Run
    with sync_playwright() as p:
        try:
            print("CONNECTING to Remote Browser...")
            browser_context = browser_strategy.start(p)
            print("✅ CONNECTED!")
            
            # Use active page or create new
            if browser_context.pages:
                page = browser_context.pages[0]
                print(f"📄 Attached to existing page: {page.title()}")
            else:
                page = browser_context.new_page()
                print("📄 Created new page")

            # Initialize Bot
            bot = XArticleBot(page)

            # Test Navigation
            print("\n--- TEST: Navigation ---")
            bot.go_to_editor()
            
            # Check Login
            if bot.is_logged_in():
                 print("✅ User is logged in.")
            else:
                 print("⚠️ User NOT logged in. Functionality limited.")
            
            # Drafting
            print("\n--- TEST: Drafting ---")
            
            # Skip image if not exists
            if not os.path.exists(cover_image):
                 print(f"⚠️ Cover image {cover_image} not found, skipping image upload test.")
                 cover_image = "dummy.jpg"

            print(f"✍️ Drafting Article: {test_title}")
            bot.draft_article(test_title, test_body, cover_image)
            
            print("\n🎉 TEST COMPLETED SUCCESSFULLY!")
            
        except Exception as e:
            print(f"\n❌ ERROR during execution: {e}")
            import traceback
            traceback.print_exc()
        finally:
            try:
                browser_strategy.stop(browser_context)
                print("🔌 Disconnected.")
            except:
                pass

if __name__ == "__main__":
    test_remote_draft()
