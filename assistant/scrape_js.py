"""Scrape all JavaScript files from Drawback Chess website."""

import asyncio
import json
from pathlib import Path
from urllib.parse import urljoin, urlparse
from playwright.async_api import async_playwright

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRAPED_DIR = REPO_ROOT / "scraped_drawback_chess"
SCRAPED_DIR.mkdir(exist_ok=True)

async def scrape_js_files(url: str):
    js_files = {}
    
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        collected_scripts = []
        
        async def handle_response(response):
            url = response.url
            content_type = response.headers.get("content-type", "")
            
            if "javascript" in content_type or url.endswith(".js"):
                try:
                    body = await response.text()
                    collected_scripts.append({
                        "url": url,
                        "content": body,
                        "content_type": content_type
                    })
                    print(f"[SCRAPED] {url}")
                except Exception as e:
                    print(f"[ERROR] Failed to capture {url}: {e}")
        
        page.on("response", handle_response)
        
        print(f"[SCRAPER] Navigating to {url}")
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        
        print("[SCRAPER] Waiting for lobby to load...")
        await asyncio.sleep(3)
        
        print("[SCRAPER] Looking for 'Play' or 'New Game' button...")
        try:
            play_button = page.locator("text=/Play|New Game|Quick Play/i").first
            if await play_button.count() > 0:
                print("[SCRAPER] Clicking play button...")
                await play_button.click()
                await asyncio.sleep(5)
                print("[SCRAPER] Waiting for game to load...")
                await page.wait_for_selector(".board, [class*='board'], [class*='Board']", timeout=15000)
                await asyncio.sleep(5)
            else:
                print("[SCRAPER] No play button found, staying on main page")
        except Exception as e:
            print(f"[SCRAPER] Could not enter game: {e}")
            print("[SCRAPER] Continuing with current page...")
        
        print("[SCRAPER] Waiting for additional resources...")
        await asyncio.sleep(5)
        
        inline_scripts = await page.evaluate("""
            () => {
                const scripts = Array.from(document.querySelectorAll('script'));
                return scripts
                    .filter(s => !s.src && s.textContent.trim())
                    .map((s, idx) => ({
                        url: `inline-script-${idx}`,
                        content: s.textContent,
                        content_type: 'text/javascript'
                    }));
            }
        """)
        
        collected_scripts.extend(inline_scripts)
        print(f"[SCRAPER] Found {len(inline_scripts)} inline scripts")
        
        await context.close()
        await browser.close()
    
    print(f"\n[SCRAPER] Total scripts collected: {len(collected_scripts)}")
    
    for idx, script in enumerate(collected_scripts):
        url = script["url"]
        content = script["content"]
        
        if url.startswith("inline-script-"):
            filename = f"{url}.js"
        else:
            parsed = urlparse(url)
            path_parts = parsed.path.strip("/").split("/")
            if path_parts[-1].endswith(".js"):
                filename = path_parts[-1]
            else:
                filename = f"script_{idx}.js"
        
        safe_filename = filename.replace("?", "_").replace("&", "_").replace("=", "_")
        output_path = SCRAPED_DIR / safe_filename
        
        with output_path.open("w", encoding="utf-8") as f:
            f.write(content)
        
        js_files[safe_filename] = {
            "url": url,
            "size": len(content),
            "path": str(output_path)
        }
    
    manifest_path = SCRAPED_DIR / "manifest.json"
    with manifest_path.open("w", encoding="utf-8") as f:
        json.dump(js_files, f, indent=2)
    
    print(f"\n[SCRAPER] Saved {len(js_files)} files to {SCRAPED_DIR}")
    print(f"[SCRAPER] Manifest: {manifest_path}")
    
    return js_files

async def main():
    url = "https://www.drawbackchess.com"
    await scrape_js_files(url)

if __name__ == "__main__":
    asyncio.run(main())
