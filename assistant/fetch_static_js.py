"""Fetch all JS files from the static/js directory."""

import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRAPED_DIR = REPO_ROOT / "scraped_drawback_chess"
SCRAPED_DIR.mkdir(exist_ok=True)

async def fetch_static_js():
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        print("[FETCH] Loading drawbackchess.com...")
        await page.goto("https://www.drawbackchess.com", timeout=60000)
        await asyncio.sleep(3)
        
        print("[FETCH] Extracting all loaded script URLs...")
        
        script_urls = await page.evaluate("""
            () => {
                const scripts = Array.from(document.querySelectorAll('script[src]'));
                return scripts.map(s => s.src);
            }
        """)
        
        print(f"[FETCH] Found {len(script_urls)} script tags")
        
        base_url = "https://www.drawbackchess.com"
        
        js_filenames = [
            "AcceptChallengeDialog.js",
            "AddFriendDialog.js",
            "App.js",
            "ChessNotationText.js",
            "ChessPiece.js",
            "DrawbackGlossary.js",
            "EnrichedText.js",
            "ErrorBoundary.js",
            "GameOverDialog.js",
            "GamePage.js",
            "GeneratorPage.js",
            "Helpers.js",
            "HostGameDialog.js",
            "HowToPlayDialog.js",
            "LandingPage.js",
            "LeaderboardPage.js",
        ]
        
        print(f"\n[FETCH] Attempting to fetch {len(js_filenames)} known JS files from /static/js/...")
        
        js_files = {}
        
        for filename in js_filenames:
            url = f"{base_url}/static/js/{filename}"
            try:
                print(f"[TRYING] {filename}...", end=" ")
                
                response = await page.request.get(url)
                
                if response.status == 200:
                    content = await response.text()
                    
                    output_path = SCRAPED_DIR / filename
                    with output_path.open("w", encoding="utf-8") as f:
                        f.write(content)
                    
                    js_files[filename] = {
                        "url": url,
                        "size": len(content),
                        "path": str(output_path)
                    }
                    
                    print(f"✓ ({len(content)} bytes)")
                else:
                    print(f"✗ (HTTP {response.status})")
                    
            except Exception as e:
                print(f"✗ ({e})")
        
        for url in script_urls:
            if url not in [f"{base_url}/static/js/{f}" for f in js_filenames]:
                try:
                    filename = url.split("/")[-1].split("?")[0]
                    if not filename.endswith(".js"):
                        continue
                    
                    print(f"[EXTRA] {filename}...", end=" ")
                    
                    response = await page.request.get(url)
                    if response.status == 200:
                        content = await response.text()
                        
                        safe_filename = filename.replace("?", "_").replace("&", "_")
                        output_path = SCRAPED_DIR / safe_filename
                        
                        with output_path.open("w", encoding="utf-8") as f:
                            f.write(content)
                        
                        js_files[safe_filename] = {
                            "url": url,
                            "size": len(content),
                            "path": str(output_path)
                        }
                        
                        print(f"✓ ({len(content)} bytes)")
                    else:
                        print(f"✗ (HTTP {response.status})")
                except Exception as e:
                    print(f"✗ ({e})")
        
        manifest_path = SCRAPED_DIR / "manifest.json"
        with manifest_path.open("w", encoding="utf-8") as f:
            json.dump(js_files, f, indent=2)
        
        print(f"\n{'='*60}")
        print(f"Successfully saved {len(js_files)} JavaScript files")
        print(f"Location: {SCRAPED_DIR}")
        print(f"Manifest: {manifest_path}")
        print(f"{'='*60}\n")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(fetch_static_js())
