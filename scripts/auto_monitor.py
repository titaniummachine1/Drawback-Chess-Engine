"""
Auto-Scaling Drawback Chess Monitor

1. Starts on the lobby.
2. Detects if you enter a game (e.g., /game/ID/white).
3. Automatically opens the opposite side (/black) in a new window.
4. Logs ALL packets from ALL windows into a single research file.
"""

import asyncio
import json
import os
import re
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright

# Internal imports
from src.interface.packet_parser import PacketParser
from src.db.data_handler import DataHandler


class AutoMonitor:
    def __init__(self, start_url: str):
        self.start_url = start_url
        self.log_dir = Path("logs/traffic")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.log_dir / \
            f"live_monitor_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        self.processed_urls = set()
        self.browser = None
        self.context = None
        self.data_handler = DataHandler()

    def log_packet(self, direction: str, payload: str, source: str):
        """Log packet with identifying source (WHITE/BLACK/LOBBY)."""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]

        try:
            data = json.loads(payload)
            pretty_payload = json.dumps(data, indent=2)
            msg_type = data.get("type", "unknown")
        except:
            pretty_payload = payload
            msg_type = "raw"

        log_entry = f"[{timestamp}] [{source}] [{direction}] [{msg_type}]\n{pretty_payload}\n{'-'*40}\n"

        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(log_entry)
                f.flush()  # Ensure it's written immediately
        except Exception as e:
            print(f"[ERROR] Failed to write to log: {e}")

        # Optional: Print raw activity to console for verification
        # print(f"[{timestamp}] Logged {len(payload)} bytes from {source}")

        # Console highlights
        if "reveal" in payload.lower() or "drawback" in payload.lower():
            print(f"\n[REVEAL] [{source}] DRAWBACK REVEAL!")
            print(pretty_payload)
        elif "legal_moves" in payload.lower():
            # Don't print every legal_moves to avoid spam, just log them
            pass
        elif '"type":"init"' in payload.lower():
            print(f"\n[GAME] [{source}] GAME STARTED")

    async def attach_listeners(self, page, name: str):
        """Attach exhaustive listeners to catch any possible move traffic."""
        print(f"[*] Monitoring ALL network activity for {name}...")

        # 1. Standard WebSockets
        page.on("socket", lambda ws: self.handle_socket(ws, name))

        # 2. HTTP Requests (Catch Polling/Fetch/XHR)
        page.on("request", lambda req: self.handle_request(req, name))
        page.on("response", lambda res: asyncio.create_task(
            self.handle_response(res, name)))

        # 3. URL Changes
        page.on("framenavigated", lambda frame: asyncio.create_task(
            self.check_url(page)))

    def handle_request(self, request, source):
        """Log HTTP requests to see if moves are sent via POST/GET."""
        url = request.url
        # Filter out static noise (images, css, js files)
        if any(ext in url for ext in [".js", ".css", ".png", ".jpg", ".svg", ".woff"]):
            return

        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        log_entry = f"[{timestamp}] [{source}] [HTTP] [{request.method}] {url}\n"

        # If it's a POST, log the body
        post_data = request.post_data
        if post_data:
            log_entry += f"Body: {post_data}\n"

        log_entry += f"{'-'*40}\n"

        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(log_entry)
            f.flush()

        # Console hint to show it's alive
        if "api" in url or "game" in url or post_data:
            print(f"[NET] {source}: {request.method} {url}")

        # Parse outgoing moves
        if post_data and "/move" in url:
            parsed = PacketParser.parse_move_request(post_data)
            if parsed:
                self.data_handler.process_parsed_data(parsed)

    async def handle_response(self, response, source):
        """Log HTTP responses to capture the 'Reveals' and 'Legal Moves'."""
        url = response.url
        if any(ext in url for ext in [".js", ".css", ".png", ".jpg", ".svg", ".woff"]):
            return

        # We are only interested in JSON/Text responses from the app endpoints
        try:
            content_type = response.headers.get("content-type", "")
            if "application/json" in content_type or "text/plain" in content_type:
                body = await response.text()

                timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                log_entry = f"[{timestamp}] [{source}] [RESP] {url}\nBody: {body}\n{'-'*40}\n"

                with open(self.log_file, "a", encoding="utf-8") as f:
                    f.write(log_entry)
                    f.flush()

                # Highlight significant game data in console
                if '"moves"' in body or '"drawback"' in body.lower() or '"reveal"' in body.lower():
                    print(f"\n[DATA] {source} RECEIVED JSON (Saved to DB)")
                    try:
                        parsed = json.loads(body)
                        # Process for database
                        game_data = PacketParser.parse_game_state(parsed)
                        self.data_handler.process_parsed_data(game_data)

                        # Print summary
                        print(f" - Game ID: {game_data['game_id']}")
                        print(
                            f" - Side: {game_data['turn']} (Ply {game_data['ply']})")
                        print(
                            f" - Drawback: {game_data['white_drawback'] if game_data['turn'] == 'white' else game_data['black_drawback']}")
                    except Exception as e:
                        print(f"[ERROR] DB Storage failed: {e}")
                    print("="*60)
        except Exception as e:
            # Responses can be tricky (already closed, etc)
            pass

    def handle_socket(self, ws, source):
        print(f"[*] WebSocket OPENED on {source}!")
        ws.on("framereceived", lambda payload: self.log_packet(
            "RECV", payload, source))
        ws.on("framesent", lambda payload: self.log_packet(
            "SENT", payload, source))

    async def check_url(self, page):
        """Check if the current URL is a game that needs a dual instance."""
        url = page.url
        if "/game" in url and url not in self.processed_urls:

            # Pattern 1: .../game/ID/color
            match1 = re.search(r"/game/([a-z0-9]+)/(white|black)", url)
            # Pattern 2: .../game?id=ID&color=color
            match2 = re.search(
                r"/game\?id=([a-z0-9]+)&color=(white|black)", url)

            match = match1 or match2
            if match:
                self.processed_urls.add(url)
                game_id = match.group(1)
                current_color = match.group(2)
                opposite_color = "black" if current_color == "white" else "white"

                # Construct opposite URL
                if match1:
                    opposite_url = url.replace(
                        f"/{current_color}", f"/{opposite_color}")
                else:
                    opposite_url = url.replace(
                        f"color={current_color}", f"color={opposite_color}")

                if opposite_url not in self.processed_urls:
                    print(f"\n[LINK] Detected game: {game_id}")
                    print(
                        f"[LINK] Auto-launching opposite side: {opposite_color}")
                    self.processed_urls.add(opposite_url)
                    await self.launch_opposite(opposite_url, opposite_color.upper())

    async def launch_opposite(self, url, name):
        """Launch the other side of the game in a completely new session (context)."""
        # Create a SEPARATE context so the second window has its own cookies
        new_context = await self.browser.new_context()
        await new_context.clear_cookies()

        new_page = await new_context.new_page()
        await self.attach_listeners(new_page, name)

        print(f"[*] Navigating {name} to {url} in a fresh session...")
        await new_page.goto(url)

    async def run(self):
        async with async_playwright() as p:
            self.browser = await p.chromium.launch(headless=False)
            self.context = await self.browser.new_context()

            # ATTACH TO CONTEXT: This is more reliable for catching sockets
            # as soon as they are created in any page.
            self.context.on(
                "socket", lambda ws: self.handle_socket(ws, "BROWSER"))

            # Explicitly clear everything for a fresh session
            await self.context.clear_cookies()

            main_page = await self.context.new_page()
            # We still attach to page for navigation events
            await self.attach_listeners(main_page, "MAIN")

            print(f"[*] Navigating to {self.start_url}")
            await main_page.goto(self.start_url)

            print("\n" + "="*50)
            print("AUTO-MONITOR ACTIVE")
            print(f"Log file: {self.log_file}")
            print("1. Host a game or join one.")
            print("2. When you enter /white or /black, I will auto-open the other side.")
            print("3. All traffic for BOTH sides will be recorded.")
            print("="*50 + "\n")

            try:
                while True:
                    await asyncio.sleep(1)
            except asyncio.CancelledError:
                pass
            finally:
                await self.browser.close()


if __name__ == "__main__":
    import sys
    start_url = sys.argv[1] if len(
        sys.argv) > 1 else "https://www.drawbackchess.com"
    monitor = AutoMonitor(start_url)
    try:
        asyncio.run(monitor.run())
    except KeyboardInterrupt:
        print("\nMonitor stopped.")
