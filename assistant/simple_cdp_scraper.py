"""Simple CDP scraper to get all JS files from the browser."""

import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRAPED_DIR = REPO_ROOT / "scraped_drawback_chess"
SCRAPED_DIR.mkdir(exist_ok=True)

async def scrape_all_scripts():
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        print("[SCRAPER] Navigating to drawbackchess.com...")
        await page.goto("https://www.drawbackchess.com", timeout=60000)
        
        print("[SCRAPER] Waiting for page load...")
        await asyncio.sleep(5)
        
        print("[SCRAPER] Trying to start a game...")
        try:
            await page.locator("text=/Play|Quick Play/i").first.click(timeout=5000)
            await asyncio.sleep(10)
        except:
            print("[SCRAPER] Could not auto-start game, continuing anyway...")
        
        print("\n[SCRAPER] Extracting all script sources using evaluate...")
        
        script_data = await page.evaluate("""
            async () => {
                const scripts = [];
                const scriptElements = document.querySelectorAll('script[src]');
                
                for (const script of scriptElements) {
                    const src = script.src;
                    try {
                        const response = await fetch(src);
                        const content = await response.text();
                        scripts.push({
                            url: src,
                            content: content,
                            size: content.length
                        });
                    } catch (e) {
                        console.error('Failed to fetch:', src, e);
                    }
                }
                
                const inlineScripts = document.querySelectorAll('script:not([src])');
                inlineScripts.forEach((script, idx) => {
                    if (script.textContent.trim()) {
                        scripts.push({
                            url: `inline-script-${idx}`,
                            content: script.textContent,
                            size: script.textContent.length
                        });
                    }
                });
                
                return scripts;
            }
        """)
        
        print(f"[SCRAPER] Extracted {len(script_data)} scripts from page")
        
        js_files = {}
        for idx, script in enumerate(script_data):
            url = script["url"]
            content = script["content"]
            
            if url.startswith("inline-script-"):
                filename = f"{url}.js"
            else:
                filename = url.split("/")[-1].split("?")[0]
                if not filename.endswith(".js"):
                    filename = f"script_{idx}.js"
            
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
            
            print(f"[SAVED] {safe_filename} ({len(content)} bytes)")
        
        manifest_path = SCRAPED_DIR / "manifest.json"
        with manifest_path.open("w", encoding="utf-8") as f:
            json.dump(js_files, f, indent=2)
        
        print(f"\n{'='*60}")
        print(f"Saved {len(js_files)} files to {SCRAPED_DIR}")
        print(f"Manifest: {manifest_path}")
        print(f"{'='*60}\n")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(scrape_all_scripts())
