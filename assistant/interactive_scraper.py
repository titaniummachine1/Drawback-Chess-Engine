"""Interactive scraper - manually navigate and press Enter to save all JS files."""

import asyncio
import json
from pathlib import Path
from urllib.parse import urlparse
from playwright.async_api import async_playwright

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRAPED_DIR = REPO_ROOT / "scraped_drawback_chess"
SCRAPED_DIR.mkdir(exist_ok=True)

async def interactive_scrape():
    collected_scripts = []
    
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
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
                    print(f"[CAPTURED] {len(collected_scripts)}: {url.split('/')[-1][:50]}")
                except Exception as e:
                    print(f"[ERROR] {url}: {e}")
        
        page.on("response", handle_response)
        
        print("\n" + "="*60)
        print("INTERACTIVE JS SCRAPER")
        print("="*60)
        print("\nNavigating to https://www.drawbackchess.com...")
        
        await page.goto("https://www.drawbackchess.com", wait_until="domcontentloaded", timeout=60000)
        
        print("\n" + "="*60)
        print("INSTRUCTIONS:")
        print("1. Manually navigate to a game in the browser")
        print("2. Wait for the game to fully load")
        print("3. Press ENTER in this terminal to save all captured JS files")
        print("="*60 + "\n")
        
        input("Press ENTER when ready to save...")
        
        print(f"\n[SAVING] Captured {len(collected_scripts)} JavaScript files")
        
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
        print(f"[FOUND] {len(inline_scripts)} inline scripts")
        
        await context.close()
        await browser.close()
    
    js_files = {}
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
        
        counter = 1
        original_filename = safe_filename
        while (SCRAPED_DIR / safe_filename).exists():
            name, ext = original_filename.rsplit(".", 1) if "." in original_filename else (original_filename, "")
            safe_filename = f"{name}_{counter}.{ext}" if ext else f"{name}_{counter}"
            counter += 1
        
        output_path = SCRAPED_DIR / safe_filename
        
        with output_path.open("w", encoding="utf-8") as f:
            f.write(content)
        
        js_files[safe_filename] = {
            "url": url,
            "size": len(content),
            "path": str(output_path)
        }
        print(f"[SAVED] {safe_filename} ({len(content)} bytes)")
    
    manifest_path = SCRAPED_DIR / "manifest.json"
    with manifest_path.open("w", encoding="utf-8") as f:
        json.dump(js_files, f, indent=2)
    
    print(f"\n{'='*60}")
    print(f"COMPLETE: Saved {len(js_files)} files to {SCRAPED_DIR}")
    print(f"Manifest: {manifest_path}")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    asyncio.run(interactive_scrape())
