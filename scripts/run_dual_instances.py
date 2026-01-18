"""
Launch Dual Instances of Drawback Chess

Launches two browser windows side-by-side: one for White, one for Black.
Useful for observing AI vs AI games or packet analysis of both sides.
"""

import asyncio
from playwright.async_api import async_playwright
# from playwright_stealth import stealth

async def launch_instance(p, url, name, x_pos):
    browser = await p.chromium.launch(headless=False, args=[f"--window-position={x_pos},0", "--window-size=800,900"])
    context = await browser.new_context()
    page = await context.new_page()
    # await stealth(page)
    
    print(f"[{name}] Navigating to {url}...")
    await page.goto(url)
    
    # In a real use case, we would add the socket interceptor here too
    return browser

async def main():
    game_id = "c7c012a5e9857eaf9cfae6e9815d29be" # Example from user
    white_url = f"https://www.drawbackchess.com/game/{game_id}/white"
    black_url = f"https://www.drawbackchess.com/game/{game_id}/black"
    
    async with async_playwright() as p:
        # Launch White on the left
        white_browser = await launch_instance(p, white_url, "WHITE", 0)
        
        # Launch Black on the right
        black_browser = await launch_instance(p, black_url, "BLACK", 810)
        
        print("\n--- Both instances launched ---")
        print("Keep this terminal open to keep browsers alive.")
        
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("\nShutting down browsers...")
            await white_browser.close()
            await black_browser.close()

if __name__ == "__main__":
    asyncio.run(main())
