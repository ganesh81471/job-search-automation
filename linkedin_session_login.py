"""
linkedin_session_login.py
--------------------------
ONE-TIME SETUP for linkedin_profile_watcher.py.

Watching a specific person's activity feed (as opposed to a public job
search) requires being logged in — LinkedIn blocks guest access to
individual profiles' "recent activity" pages. This script opens a real
browser window, lets you log in by hand, then saves that session so the
watcher can reuse it silently in the background afterward.

Run once:
    python linkedin_session_login.py

A Chrome window opens on LinkedIn's login page.
  1. Log in normally — enter your password, complete any 2FA/security
     check LinkedIn asks for.
  2. Once you can see your own LinkedIn feed, come back to this terminal
     and press Enter.
  3. Your session is saved to linkedin_session.json (next to this file).

Re-run this any time LinkedIn logs the session out — the watcher will
print a clear warning telling you to do so when that happens.

linkedin_session.json contains live login cookies. It's already excluded
via .gitignore — never commit it.
"""

import asyncio
from playwright.async_api import async_playwright

SESSION_FILE = "linkedin_session.json"


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        await page.goto("https://www.linkedin.com/login", wait_until="domcontentloaded")

        print("\n[*] A browser window has opened on LinkedIn's login page.")
        print("[*] Log in normally, wait until you see your own feed, then come back here.")
        input("[*] Press Enter once you're logged in and can see your feed... ")

        await context.storage_state(path=SESSION_FILE)
        print(f"[+] Session saved to {SESSION_FILE}.")
        print("[+] You can now run linkedin_profile_watcher.py (or let the scheduler run it).")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())