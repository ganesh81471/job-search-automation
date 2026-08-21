"""
linkedin_profile_watcher.py
-----------------------------
Watches a specific LinkedIn profile's activity feed and sends a Telegram
notification as soon as a new post shows up. Built for tracking people
who post job openings directly on LinkedIn (e.g. HireSetu's founder)
rather than through a job board — no scraping of HireSetu's own site
required, since he posts the same openings himself.

ONE-TIME SETUP:
    python linkedin_session_login.py
    (see that file's docstring — takes ~2 minutes)

RECURRING USE:
    python linkedin_profile_watcher.py
    Point a Windows Task Scheduler job at this, every 30 minutes, the
    same way main.py is scheduled for the 9am daily scan. See the
    "Watching a LinkedIn profile" section in README.md for exact steps.

Each run:
  1. Loads the saved login session (linkedin_session.json).
  2. Opens each watched profile's "recent activity" page.
  3. Reads the newest few posts and compares them against what's already
     been seen (tracked in watched_posts_seen.json, next to this file).
  4. Sends ONE Telegram notification per profile that has anything new,
     then records those posts as seen so they're never re-notified.

Checking the newest 5 posts (not just the latest 1) means a missed
30-minute window still gets caught on the next run instead of silently
skipping a post if he posts twice in quick succession.

Most runs will find nothing new — that's expected, and just prints
quietly rather than notifying.
"""

import asyncio
import hashlib
import json
import os
from pathlib import Path

from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

from telegram_notify import send_notification

SESSION_FILE = "linkedin_session.json"
SEEN_FILE = "watched_posts_seen.json"

# Add more profiles here later the same way if you want to watch others.
WATCHED_PROFILES = [
    {
        "name": "Prashanth Jakkula (HireSetu)",
        "url": "https://www.linkedin.com/in/prashanthjakkula/recent-activity/all/",
    },
]
POSTS_TO_CHECK_PER_RUN = 5


def _load_seen():
    if not os.path.exists(SEEN_FILE):
        return {}
    try:
        with open(SEEN_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _save_seen(seen):
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(seen, f, indent=2)


def _post_fingerprint(urn, text):
    """Prefer LinkedIn's own post ID (data-urn) when the markup exposes
    it — it's stable across runs and across markup tweaks. Fall back to
    hashing the text for posts where a urn isn't present, so dedup still
    works reasonably even then."""
    if urn:
        return urn
    return hashlib.sha1(text.encode("utf-8", errors="ignore")).hexdigest()


async def _fetch_recent_posts(page, profile_url):
    await page.goto(profile_url, wait_until="domcontentloaded", timeout=60000)
    await page.wait_for_timeout(3000)
    await page.evaluate("window.scrollBy(0, 1600)")
    await page.wait_for_timeout(2000)

    soup = BeautifulSoup(await page.content(), "html.parser")
    containers = soup.find_all("div", class_="feed-shared-update-v2")

    posts = []
    for c in containers[:POSTS_TO_CHECK_PER_RUN]:
        urn = c.get("data-urn", "")
        text_tag = c.find("div", class_="update-components-text")
        text = text_tag.get_text(strip=True) if text_tag else ""
        link_tag = c.find("a", class_="app-aware-link")
        link = link_tag["href"] if link_tag and link_tag.has_attr("href") else profile_url

        if not text and not urn:
            continue  # unparseable container — skip rather than risk a false notify

        posts.append({"urn": urn, "text": text, "link": link})
    return posts


async def check_profile(profile, seen):
    name, url = profile["name"], profile["url"]
    new_posts = []

    if not Path(SESSION_FILE).exists():
        print(f"[!] {SESSION_FILE} not found. Run linkedin_session_login.py first.")
        return new_posts

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            storage_state=SESSION_FILE,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        )
        page = await context.new_page()

        try:
            posts = await _fetch_recent_posts(page, url)
        except Exception as e:
            print(f"[!] Failed to check {name}: {e}")
            posts = []
        finally:
            await browser.close()

    if not posts:
        return new_posts

    profile_seen = set(seen.get(url, []))
    first_run_for_profile = url not in seen

    for post in posts:
        fp = _post_fingerprint(post["urn"], post["text"])
        if fp not in profile_seen:
            if not first_run_for_profile:
                new_posts.append(post)
            profile_seen.add(fp)

    # cap so the file doesn't grow forever
    seen[url] = list(profile_seen)[-200:]
    return new_posts


async def run_once():
    seen = _load_seen()
    any_new = False

    for profile in WATCHED_PROFILES:
        new_posts = await check_profile(profile, seen)
        if not new_posts:
            print(f"[.] No new posts from {profile['name']}.")
            continue

        any_new = True
        print(f"[+] {len(new_posts)} new post(s) from {profile['name']}!")

        lines = [f"New LinkedIn post from {profile['name']}:"]
        for post in new_posts:
            snippet = post["text"][:300] or "(no text extracted)"
            lines.append(f"\n{snippet}\n{post['link']}")
        send_notification("\n".join(lines))

    _save_seen(seen)
    if not any_new:
        print("[.] Run complete — nothing new this time.")


if __name__ == "__main__":
    asyncio.run(run_once())