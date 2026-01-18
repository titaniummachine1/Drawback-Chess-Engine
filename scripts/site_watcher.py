"""
Drawback Chess Site Watcher & Packet Interceptor

Uses Playwright to connect to Drawback Chess, monitor WebSocket traffic,
and log packets for analysis. This is the first step to building the 
automated data collector.
"""

import asyncio
import json
import os
import time
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright
# from playwright_stealth import stealth

class DrawbackWatcher:
    def __init__(self, game_url: str):
        self.game_url = game_url
        self.log_dir = Path("logs/traffic")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.log_dir / f"traffic_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        
    def log_packet(self, direction: str, payload: str):
        """Log packet to file and pretty-print to console."""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        
        # Try to parse as JSON for pretty printing
        try:
            data = json.loads(payload)
            pretty_payload = json.dumps(data, indent=2)
            # Shorten if it's just a move or ping to keep console clean
            msg_type = data.get("type", "unknown")
        except:
            pretty_payload = payload
            msg_type = "raw"

        # Highlight specific patterns in console
        important = False
        if "reveal" in payload.lower():
            print("\n💎 DRAWBACK REVEAL DETECTED!")
            important = True
        if "legal_moves" in payload.lower():
            print("\n🛡️ LEGAL MOVES PACKET RECEIVED")
            # important = True # Keep this off to avoid spam unless needed
        if '"type":"init"' in payload.lower() or '"type":"game"' in payload.lower():
            print("\n🎮 GAME SESSION INITIALIZED")
            important = True
            
        if important:
            print(f"[{timestamp}] [{direction}]")
            print(pretty_payload)
            print("="*60)

    async def watch(self):
        async with async_playwright() as p:
            print(f"Starting browser for: {self.game_url}")
            browser = await p.chromium.launch(headless=False) # Headless=False so user can interact
            context = await browser.new_context()
            page = await context.new_page()
            
            # Apply stealth
            # await stealth(page)
            
            # Intercept WebSockets
            page.on("socket", lambda ws: self.handle_socket(ws))
            
            print(f"Navigating to {self.game_url}...")
            await page.goto(self.game_url)
            
            print("--- WATCHER ACTIVE ---")
            print("Interact with the site. All packets are being logged to:")
            print(self.log_file)
            print("Press Ctrl+C in this terminal to stop.")
            
            # Keep script running
            try:
                while True:
                    await asyncio.sleep(1)
            except asyncio.CancelledError:
                pass
            finally:
                await browser.close()

    def handle_socket(self, ws):
        print(f"WebSocket connected: {ws.url}")
        
        ws.on("framereceived", lambda payload: self.log_packet("RECV", payload))
        ws.on("framesent", lambda payload: self.log_packet("SENT", payload))

async def main():
    import sys
    url = sys.argv[1] if len(sys.argv) > 1 else "https://www.drawbackchess.com"
    watcher = DrawbackWatcher(url)
    await watcher.watch()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nWatcher stopped by user.")
