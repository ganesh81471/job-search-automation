"""
career_pages_scraper.py
------------------------
Company career pages are far more trustworthy than aggregators (a listing
that's gone gets removed from the page; aggregators keep indexing dead
listings for months — we proved this directly with ARTPARK vs Instahyre).

The tradeoff: every company's site has different HTML, so this can't be
fully generic. Instead, it's a WATCHLIST you grow over time — add a company
here once, and it gets checked on every run forever.

Add companies you care about to WATCHLIST below. Each entry needs a
`parse` function tailored to that specific site's markup.
"""

import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

# Text that shows up in nav/footer links containing "/careers/" but isn't
# an actual job posting. The old version matched ANY link with "/careers/"
# in the href — which caught this stuff too. That's the bug: "none of the
# JD is matching" was because half of what got saved wasn't a job at all.
_NON_JOB_LINK_TEXT = {
    "careers", "career", "join us", "about", "about us", "home",
    "contact", "contact us", "apply", "apply now", "life at artpark",
    "back", "back to careers", "view all", "see all", "all openings",
    "current openings", "open positions", "startups", "read more",
    "read more →", "featured",
}


async def _fetch_page(context, url):
    page = await context.new_page()
    html = ""
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=15000)
        await page.wait_for_timeout(1000)
        html = await page.content()
    except Exception as e:
        print(f"    [!] Could not load {url}: {e}")
    finally:
        await page.close()
    return html


async def _fetch_generic_detail_text(context, url):
    """Career pages don't have a shared markup pattern the way LinkedIn/Indeed
    do, so there's no single CSS selector that works everywhere. This grabs
    all visible body text as a fallback — noisier than a targeted selector,
    but it's what lets the strict experience filter actually find "0-1 years"
    style phrases on an arbitrary company site instead of getting nothing."""
    page = await context.new_page()
    text = ""
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=15000)
        await page.wait_for_timeout(800)
        content = await page.content()
        soup = BeautifulSoup(content, "html.parser")
        for tag in soup(["script", "style", "nav", "header", "footer"]):
            tag.decompose()
        text = soup.get_text(" ", strip=True)
    except Exception as e:
        print(f"    [!] Could not load detail page ({url}): {e}")
    finally:
        await page.close()
    return text


def _parse_artpark(html, base_url):
    """ARTPARK @ IISc careers listing page.
    Note: their URL path changed from /careers/ to /careers-1/ at some
    point after we first built this — matching on "/career" (no trailing
    slash) instead of the exact old path so a future rename like this
    doesn't silently break it again."""
    soup = BeautifulSoup(html, "html.parser")
    jobs = []
    seen_links = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = a.get_text(strip=True)
        if "/career" not in href.lower() or not text:
            continue
        if "?" in href:  # category/tag filter links, e.g. ?category=STARTUPS
            continue
        path_after = href.lower().split("/career", 1)[-1].strip("-1/")
        if not path_after:
            continue
        if text.strip().lower() in _NON_JOB_LINK_TEXT:
            continue
        if len(text) < 8:  # "Careers", "Apply" etc are short; real titles aren't
            continue

        full_url = href if href.startswith("http") else f"https://www.artpark.in{href}"
        if full_url in seen_links:
            continue
        seen_links.add(full_url)

        jobs.append({
            "title": text, "company": "ARTPARK @ IISc",
            "location": "Bengaluru", "link": full_url,
            "description": "", "seniority_label": None,
        })
    return jobs


# Add more companies here as you find ones worth watching regularly.
# Each entry: (display_name, listing_url, parser_function)
WATCHLIST = [
    ("ARTPARK @ IISc", "https://www.artpark.in/careers", _parse_artpark),
    # ("Cionlabs", "https://cionlabs.com/careers", _parse_cionlabs),  # add when you have one
]


async def scrape_career_pages(fetch_details=True, max_detail_fetches=15):
    """fetch_details now defaults to True — without real description text,
    the strict experience filter has nothing to check and rejects
    everything by default, which is exactly what you were seeing."""
    all_jobs = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        for name, url, parser in WATCHLIST:
            print(f"[*] Checking {name} ({url})...")
            html = await _fetch_page(context, url)
            if not html:
                continue
            jobs = parser(html, url)
            print(f"    [+] Found {len(jobs)} actual job links on {name}'s careers page "
                  f"(nav/footer links filtered out).")

            if fetch_details:
                to_fetch = jobs[:max_detail_fetches]
                for i, job in enumerate(to_fetch, 1):
                    job["description"] = await _fetch_generic_detail_text(context, job["link"])
                    print(f"    [{i}/{len(to_fetch)}] fetched: {job['title'][:50]}")
                    await page.wait_for_timeout(500)

            all_jobs.extend(jobs)
        await browser.close()
    return all_jobs


if __name__ == "__main__":
    print("=== Checking career page watchlist ===")
    jobs = asyncio.run(scrape_career_pages())
    for j in jobs:
        print(f"- {j['title']} ({j['company']}) -> {j['link']}")