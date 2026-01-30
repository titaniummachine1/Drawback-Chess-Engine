"""Scrape all JavaScript files using Chrome DevTools Protocol."""

import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRAPED_DIR = REPO_ROOT / "scraped_drawback_chess"
SCRAPED_DIR.mkdir(exist_ok=True)

async def scrape_with_cdp():
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        cdp = await page.context.new_cdp_session(page)
        await cdp.send("Debugger.enable")
        
        print("[CDP] Navigating to https://www.drawbackchess.com")
        await page.goto("https://www.drawbackchess.com", wait_until="domcontentloaded", timeout=60000)
        
        print("[CDP] Waiting for initial load...")
        await asyncio.sleep(5)
        
        print("[CDP] Looking for Play button...")
        try:
            play_button = page.locator("text=/Play|New Game|Quick Play/i").first
            if await play_button.count() > 0:
                print("[CDP] Clicking Play...")
                await play_button.click()
                await asyncio.sleep(8)
        except Exception as e:
            print(f"[CDP] Could not click play: {e}")
        
        print("[CDP] Fetching all script sources from debugger...")
        
        scripts_response = await cdp.send("Debugger.getScriptSource", {"scriptId": "0"})
        
        result = await cdp.send("Page.getResourceTree")
        frame_tree = result.get("frameTree", {})
        
        all_resources = []
        
        def extract_resources(node):
            resources = node.get("resources", [])
            all_resources.extend(resources)
            
            for child in node.get("childFrames", []):
                extract_resources(child)
        
        extract_resources(frame_tree)
        
        print(f"[CDP] Found {len(all_resources)} resources")
        
        js_files = {}
        saved_count = 0
        
        for resource in all_resources:
            url = resource.get("url", "")
            resource_type = resource.get("type", "")
            
            if resource_type != "Script" and not url.endswith(".js"):
                continue
            
            try:
                content_response = await cdp.send("Page.getResourceContent", {
                    "frameId": frame_tree["frame"]["id"],
                    "url": url
                })
                
                content = content_response.get("content", "")
                
                if not content:
                    continue
                
                filename = url.split("/")[-1].split("?")[0]
                if not filename or filename == "":
                    filename = f"script_{saved_count}.js"
                
                safe_filename = filename.replace("?", "_").replace("&", "_").replace("=", "_")
                
                counter = 1
                original_filename = safe_filename
                while (SCRAPED_DIR / safe_filename).exists():
                    name_parts = original_filename.rsplit(".", 1)
                    if len(name_parts) == 2:
                        safe_filename = f"{name_parts[0]}_{counter}.{name_parts[1]}"
                    else:
                        safe_filename = f"{original_filename}_{counter}"
                    counter += 1
                
                output_path = SCRAPED_DIR / safe_filename
                
                with output_path.open("w", encoding="utf-8") as f:
                    f.write(content)
                
                js_files[safe_filename] = {
                    "url": url,
                    "size": len(content),
                    "path": str(output_path)
                }
                
                saved_count += 1
                print(f"[SAVED] {saved_count}: {safe_filename} ({len(content)} bytes)")
                
            except Exception as e:
                print(f"[ERROR] Failed to get content for {url}: {e}")
        
        manifest_path = SCRAPED_DIR / "manifest.json"
        with manifest_path.open("w", encoding="utf-8") as f:
            json.dump(js_files, f, indent=2)
        
        print(f"\n{'='*60}")
        print(f"COMPLETE: Saved {saved_count} JavaScript files")
        print(f"Location: {SCRAPED_DIR}")
        print(f"Manifest: {manifest_path}")
        print(f"{'='*60}\n")
        
        await context.close()
        await browser.close()

if __name__ == "__main__":
    asyncio.run(scrape_with_cdp())
