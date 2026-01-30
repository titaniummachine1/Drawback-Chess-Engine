"""Fetch the source map to get unminified source code."""

import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRAPED_DIR = REPO_ROOT / "scraped_drawback_chess"
SCRAPED_DIR.mkdir(exist_ok=True)

async def fetch_sourcemap():
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        sourcemap_url = "https://www.drawbackchess.com/static/js/main.fed58aff.js.map"
        
        print(f"[FETCH] Downloading source map from {sourcemap_url}")
        
        try:
            response = await page.request.get(sourcemap_url)
            
            if response.status == 200:
                content = await response.text()
                
                sourcemap_path = SCRAPED_DIR / "main.fed58aff.js.map"
                with sourcemap_path.open("w", encoding="utf-8") as f:
                    f.write(content)
                
                print(f"[SUCCESS] Saved source map ({len(content)} bytes)")
                print(f"[LOCATION] {sourcemap_path}")
                
                try:
                    sourcemap_data = json.loads(content)
                    
                    if "sources" in sourcemap_data:
                        print(f"\n[SOURCES] Found {len(sourcemap_data['sources'])} source files:")
                        for i, source in enumerate(sourcemap_data['sources'][:30]):
                            print(f"  {i+1}. {source}")
                        if len(sourcemap_data['sources']) > 30:
                            print(f"  ... and {len(sourcemap_data['sources']) - 30} more")
                    
                    if "sourcesContent" in sourcemap_data and sourcemap_data["sourcesContent"]:
                        print(f"\n[CONTENT] Source map includes embedded source code!")
                        print(f"[EXTRACTING] Saving individual source files...")
                        
                        sources_dir = SCRAPED_DIR / "sources"
                        sources_dir.mkdir(exist_ok=True)
                        
                        saved_count = 0
                        for source_path, source_content in zip(sourcemap_data["sources"], sourcemap_data["sourcesContent"]):
                            if not source_content:
                                continue
                            
                            safe_path = source_path.replace("../", "").replace("/", "_").replace("\\", "_")
                            if not safe_path.endswith(".js"):
                                safe_path += ".js"
                            
                            output_path = sources_dir / safe_path
                            
                            with output_path.open("w", encoding="utf-8") as f:
                                f.write(source_content)
                            
                            saved_count += 1
                            
                            if "GamePage" in source_path or "ChessPiece" in source_path or "socket" in source_path.lower():
                                print(f"  [SAVED] {safe_path}")
                        
                        print(f"\n[COMPLETE] Extracted {saved_count} source files to {sources_dir}")
                    else:
                        print("\n[WARNING] Source map does not include embedded source code")
                        
                except json.JSONDecodeError:
                    print("[ERROR] Source map is not valid JSON")
            else:
                print(f"[ERROR] HTTP {response.status}")
                
        except Exception as e:
            print(f"[ERROR] {e}")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(fetch_sourcemap())
