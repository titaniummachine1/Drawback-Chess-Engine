import asyncio
from playwright.async_api import async_playwright
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

SERVER_URL = "https://drawbackchess.com"


async def stick_sniff():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        logger.info(
            "Browser launched. Navigate to the game and create a host manually.")
        logger.info(
            "I will log all POST requests to 'sniffed_packets.jsonl'...")

        # Open file to write packets
        with open("sniffed_packets.jsonl", "w", encoding="utf-8") as f:

            async def log_request(request):
                if request.method == "POST" and "drawbackchess.com" in request.url:
                    try:
                        post_data = request.post_data
                        # Try to parse JSON if possible for cleaner log
                        try:
                            if post_data:
                                json_body = json.loads(post_data)
                                post_data = json_body
                        except:
                            pass

                        entry = {
                            "url": request.url,
                            "method": request.method,
                            "headers": request.headers,
                            "payload": post_data
                        }

                        line = json.dumps(entry)
                        f.write(line + "\n")
                        f.flush()
                        print(
                            f"\n[CAPTURED] {request.url}\nPayload: {post_data}\n")
                    except Exception as e:
                        logger.error(f"Failed to log request: {e}")

            page.on("request", log_request)

            await page.goto(SERVER_URL)

            # Keep script alive for user to interact
            print("Press Ctrl+C to stop sniffing after you have hosted the game.")
            try:
                await asyncio.Future()  # run forever
            except KeyboardInterrupt:
                pass

if __name__ == "__main__":
    try:
        asyncio.run(stick_sniff())
    except KeyboardInterrupt:
        pass
