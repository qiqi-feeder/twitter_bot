from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError
from . import gen_config as config
import time

class XArticleBot:
    def __init__(self, page: Page):
        self.page = page

    def go_to_editor(self):
        """Navigates to the X Article Editor."""
        print(f"Navigating to {config.X_ARTICLE_EDITOR_URL}...")
        self.page.goto(config.X_ARTICLE_EDITOR_URL, wait_until="domcontentloaded", timeout=60000)
        
        # Wait for page to load
        print("Waiting for page to fully render...")
        self.page.wait_for_timeout(3000)
        
        # Click the "Write" button to enter editor
        print("Looking for 'Write' button...")
        try:
            write_btn = self.page.get_by_role("button", name="Write")
            if write_btn.is_visible(timeout=5000):
                print("Clicking 'Write' button...")
                write_btn.click()
                # Wait for editor to load
                self.page.wait_for_timeout(3000)
                print("✓ Entered article editor!")
            else:
                # Try alternative selectors
                alt_selectors = [
                    'button:has-text("Write")',
                    'a:has-text("Write")',
                    '[aria-label*="Write" i]'
                ]
                for selector in alt_selectors:
                    try:
                        elem = self.page.locator(selector).first
                        if elem.is_visible(timeout=2000):
                            elem.click()
                            self.page.wait_for_timeout(3000)
                            print(f"✓ Clicked Write button with selector: {selector}")
                            break
                    except:
                        continue
        except Exception as e:
            print(f"⚠ Could not find Write button: {e}")
            print("Assuming already in editor...")
        
        print("Ready to draft.")


    def is_logged_in(self) -> bool:
        """
        Checks if the user is logged in.
        """
        try:
            # Look for common logged-in indicator
            self.page.wait_for_selector('a[href="/home"]', timeout=3000)
            return True
        except:
            return False

    def draft_article(self, title: str, body: str, cover_image_path: str):
        """
        Fills in the article details.
        X Article editor structure: Title is usually the first contenteditable div.
        """
        print("Drafting article...")
        
        # Give time for editor to fully load
        self.page.wait_for_timeout(2000)
        
        # Strategy: Get all contenteditable divs
        # Title is typically the first one, body is the second
        print("Looking for title and body fields...")
        
        try:
            # Title is actually a <textarea>, not contenteditable div
            print("Looking for title textarea...")
            title_textarea = self.page.locator('textarea').first
            if title_textarea.is_visible(timeout=3000):
                print("Found title textarea!")
                title_textarea.click()
                self.page.wait_for_timeout(500)
                # Clear and type
                title_textarea.fill('')  # Clear first
                title_textarea.type(title, delay=50)
                print("✓ Title set!")
            else:
                print("⚠ Title textarea not visible")
                
            # Body is contenteditable div
            editable_divs = self.page.locator('div[contenteditable="true"]')
            count = editable_divs.count()
            print(f"Found {count} contenteditable div(s) for body")
            
            if count >= 1:
                # Body editor
                print("Setting body content...")
                body_div = editable_divs.first  # Usually the first or only one after title
                body_div.click()
                self.page.wait_for_timeout(500)
                body_div.fill(body)
                print("✓ Body set!")
            else:
                print("⚠ No contenteditable div found for body")
                
        except Exception as e:
            print(f"⚠ Error filling article: {e}")
            # Save debug info
            with open("debug_page_source.html", "w", encoding="utf-8") as f:
                f.write(self.page.content())
            print("DEBUG: Saved page HTML")
        
        # Cover image upload (if file exists)
        import os
        if os.path.exists(cover_image_path):
            print(f"Uploading cover image: {cover_image_path}")
            try:
                # Step 1: Click "Add photo" button
                print("Looking for 'Add photo' button...")
                add_photo_selectors = [
                    'button:has-text("Add photo")',
                    'button:has-text("Add cover")',
                    '[aria-label*="Add photo" i]',
                    '[aria-label*="Add cover" i]'
                ]
                
                add_photo_clicked = False
                for selector in add_photo_selectors:
                    try:
                        btn = self.page.locator(selector).first
                        if btn.is_visible(timeout=2000):
                            btn.click()
                            print(f"✓ Clicked: {selector}")
                            self.page.wait_for_timeout(1000)
                            add_photo_clicked = True
                            break
                    except:
                        continue
                
                if not add_photo_clicked:
                    print("⚠ Could not find 'Add photo' button")
                    raise Exception("Add photo button not found")
                
                # Step 2: Click "Upload" option
                print("Looking for 'Upload' option...")
                upload_selectors = [
                    'button:has-text("Upload")',
                    'div:has-text("Upload")',
                    '[role="menuitem"]:has-text("Upload")'
                ]
                
                upload_clicked = False
                for selector in upload_selectors:
                    try:
                        upload_btn = self.page.locator(selector).first
                        if upload_btn.is_visible(timeout=2000):
                            upload_btn.click()
                            print(f"✓ Clicked Upload: {selector}")
                            self.page.wait_for_timeout(500)
                            upload_clicked = True
                            break
                    except:
                        continue
                
                if not upload_clicked:
                    print("⚠ Could not find 'Upload' option")
                    raise Exception("Upload option not found")
                
                # Step 3: Set the file directly on the input element
                # After clicking Upload, the input should be ready
                print("Setting file on input element...")
                self.page.wait_for_timeout(500)  # Brief wait for input to be ready
                
                try:
                    # Find the file input (usually hidden)
                    file_input = self.page.locator('input[type="file"]').first
                    file_input.set_input_files(cover_image_path)
                    print("✓ File set on input element!")
                except Exception as e:
                    print(f"Error setting file: {e}")
                    raise
                
                self.page.wait_for_timeout(2000)  # Wait for upload to process
                
                # Wait for "Edit media" dialog to appear
                print("Waiting for 'Edit media' dialog...")
                try:
                    # Wait for the dialog to be visible
                    self.page.wait_for_selector('text="Edit media"', timeout=5000)
                    print("✓ Edit media dialog appeared")
                    self.page.wait_for_timeout(1000)  # Give it a moment to fully render
                except:
                    print("⚠ Edit media dialog not detected, continuing anyway...")
                
                # Click Apply button (inside the dialog)
                print("Looking for 'Apply' button in dialog...")
                apply_clicked = False
                
                # Strategy 1: Find button by role and text
                try:
                    apply_btn = self.page.get_by_role("button", name="Apply")
                    if apply_btn.is_visible(timeout=3000):
                        apply_btn.click()
                        print("✓ Clicked Apply button!")
                        self.page.wait_for_timeout(1000)
                        apply_clicked = True
                except Exception as e:
                    print(f"Strategy 1 failed: {e}")
                
                # Strategy 2: Find button with text "Apply"
                if not apply_clicked:
                    try:
                        apply_btn = self.page.locator('button:has-text("Apply")').first
                        if apply_btn.is_visible(timeout=2000):
                            apply_btn.click()
                            print("✓ Clicked Apply button (strategy 2)!")
                            self.page.wait_for_timeout(1000)
                            apply_clicked = True
                    except Exception as e:
                        print(f"Strategy 2 failed: {e}")
                
                # Strategy 3: Find any visible button containing "Apply"
                if not apply_clicked:
                    try:
                        buttons = self.page.locator('button')
                        for i in range(buttons.count()):
                            btn = buttons.nth(i)
                            try:
                                if btn.is_visible() and "Apply" in btn.inner_text():
                                    btn.click()
                                    print("✓ Clicked Apply button (strategy 3)!")
                                    self.page.wait_for_timeout(1000)
                                    apply_clicked = True
                                    break
                            except:
                                continue
                    except Exception as e:
                        print(f"Strategy 3 failed: {e}")
                
                if not apply_clicked:
                    print("⚠ Could not find Apply button automatically.")
                    print("DEBUG: Saving page HTML to check Apply button...")
                    with open("debug_apply_button.html", "w", encoding="utf-8") as f:
                        f.write(self.page.content())
                    print("You may need to click Apply manually or check debug_apply_button.html")
                
            except Exception as e:
                print(f"⚠ Could not upload cover image: {e}")
                print("Continuing without cover image...")
        else:
            print(f"⚠ Cover image not found at: {cover_image_path}")
        
        print("Draft completed. Waiting to see results...")
        self.page.wait_for_timeout(3000)

    def publish(self):
        """Clicks the publish button."""
        print("Attempting to publish...")
        try:
            publish_btn = self.page.get_by_role("button", name="Publish")
            if publish_btn.is_visible():
                publish_btn.click()
                print("✓ Publish button clicked!")
            else:
                print("⚠ Publish button not found.")
        except Exception as e:
            print(f"Error publishing: {e}")
