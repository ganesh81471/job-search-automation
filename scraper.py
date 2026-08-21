import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        # Launch browser in visible mode (headless=False) so you can see it working
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        print("Opening Google test page...")
        await page.goto("https://www.google.com")
        title = await page.title()
        print(f"Success! Page title is: '{title}'")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())