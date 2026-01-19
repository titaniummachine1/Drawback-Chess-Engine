import asyncio
from playwright.async_api import async_playwright


async def check_ls():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto("https://www.drawbackchess.com")
        await page.wait_for_timeout(2000)
        ls = await page.evaluate("() => JSON.stringify(localStorage)")
        print(f"LOCAL STORAGE: {ls}")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(check_ls())
