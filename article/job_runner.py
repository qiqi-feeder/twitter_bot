import os
import sys
import time
import asyncio
from datetime import datetime, timedelta
import pytz

# Ensure project root is in path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.append(project_root)

# Imports
from playwright.sync_api import sync_playwright
from article.src.browser_manager import BrowserFactory
from article.src.publisher_bot import XArticleBot
from article.src.image_factory import ImageFactory
from get_data.main import generate_article_content, CN_TZ
from history.history_manager import history_manager

def run_production_job():
    """
    Main entry point for the scheduled job.
    1. Generate Content (approx 2-3 mins)
    2. Generate Image (approx 30s)
    3. Draft in Browser (approx 1 min)
    4. Wait for exact hour (Precision Timing)
    5. Publish
    """
    print(f"🚀 [Job] Started at {datetime.now(CN_TZ)}")
    
    # --- 1. PREPARE CONTENT ---
    try:
        # Determine strict title based on Next Hour (since we start at :55)
        # If running at 07:55, target is 08:00 (Morning)
        # If running at 19:55, target is 20:00 (Evening)
        
        now = datetime.now(CN_TZ)
        target_time = now + timedelta(minutes=10) # Look ahead to determine type
        
        if target_time.hour < 12:
            title_prefix = "币圈早报（深度版）"
        else:
            title_prefix = "币圈晚报（深度版）"
            
        print(f"📅 Target Title: {title_prefix} (for around {target_time.hour}:00)")
        
        # Generate Fresh Content (Always fresh for production job)
        print("⚡️ Generating Fresh Long-form Content...")
        full_title, body_content = asyncio.run(generate_article_content(hours=12))
        
        if not body_content or "No events" in body_content:
            print("❌ No content generated.")
            return

        # Save to history
        job_id = f"article_auto_{int(time.time())}"
        history_manager.add_record(
            job_id=job_id,
            content=body_content,
            scheduled_time=datetime.now(pytz.utc).isoformat(),
            status='generated', 
            source='article_bot',
            mode='production',
            content_type='article'
        )
        
    except Exception as e:
        print(f"❌ Content Gen Error: {e}")
        return

    # --- 2. GENERATE IMAGE ---
    cover_image_path = ""
    try:
        print("🎨 Generating Cover Image...")
        factory = ImageFactory()
        cover_image_path = factory.generate_article_cover(body_content)
        if cover_image_path and os.path.exists(cover_image_path):
            print(f"✅ Cover Image: {cover_image_path}")
        else:
            print("⚠️ Image Gen Failed, will publish without cover.")
    except Exception as e:
        print(f"❌ Image Gen Error: {e}")

    # --- 3. BROWSER AUTOMATION (DRAFTING) ---
    print("🚀 Starting Browser Automation...")
    
    # Early Proxy Setup
    target_ip = "100.103.97.106"
    if target_ip not in os.environ.get("no_proxy", ""):
        os.environ["no_proxy"] = f"{os.environ.get('no_proxy', '')},{target_ip}" if os.environ.get("no_proxy") else target_ip

    browser_strategy = BrowserFactory.get_strategy("attach")
    
    with sync_playwright() as p:
        try:
            print("CONNECTING to Browser...")
            context = browser_strategy.start(p)
            
            if context.pages:
                page = context.pages[0]
            else:
                page = context.new_page()
                
            bot = XArticleBot(page)
            bot.go_to_editor()
            
            if not bot.is_logged_in():
                print("❌ Not logged in. Aborting.")
                return

            # DRAFT
            print(f"✍️ Drafting: {full_title}")
            bot.draft_article(full_title, body_content, cover_image_path)
            
            # --- 4. WAIT FOR PRECISE TIME ---
            # Calculate seconds until the next full hour
            # e.g. 07:58:30 -> Wait 90s until 08:00:00
            now_wait = datetime.now()
            # Round to next hour
            next_hour = (now_wait.replace(second=0, microsecond=0, minute=0) + timedelta(hours=1))
            
            # Safety: If we are more than 10 mins away, don't wait (something is wrong or manual run)
            # If we are already past the hour (e.g. took too long, 08:01), waiting for 09:00 is wrong.
            # So check if difference is reachable.
            
            seconds_to_wait = (next_hour - now_wait).total_seconds()
            
            if 0 < seconds_to_wait < 1200: # Wait only if < 20 mins
                print(f"⏳ Waiting {seconds_to_wait:.1f}s for exact hour ({next_hour.strftime('%H:%M:%S')})...")
                time.sleep(seconds_to_wait)
                print("⏰ Time reached! Publishing...")
            else:
                print(f"⏩ Not waiting (Gap is {seconds_to_wait:.1f}s). Publishing immediately.")

            # --- 5. PUBLISH ---
            bot.publish()
            print("🎉 Job Completed Successfully!")
            
        except Exception as e:
            print(f"❌ Browser Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            try:
                browser_strategy.stop(context)
            except:
                pass

if __name__ == "__main__":
    run_production_job()
