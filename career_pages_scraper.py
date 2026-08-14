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


def _parse_artpark(html, base_url):
    """ARTPARK @ IISc careers listing page."""
    soup = BeautifulSoup(html, "html.parser")
    jobs = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = a.get_text(strip=True)
        if "/careers/" in href and text and len(text) > 3:
            full_url = href if href.startswith("http") else f"https://www.artpark.in{href}"
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


async def scrape_career_pages(fetch_details=False, max_detail_fetches=10):
    """Note: fetch_details is off by default here — each career page has
    different detail-page markup, so full-description extraction would need
    a per-company parser too. For now these get an UNKNOWN/STRETCH experience
    verdict unless the listing title/URL itself says 'intern' etc. — treat
    career-page results as a shortlist to manually verify, same as we did
    with ARTPARK by hand."""
    all_jobs = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        for name, url, parser in WATCHLIST:
            print(f"[*] Checking {name} ({url})...")
            html = await _fetch_page(context, url)
            if not html:
                continue
            jobs = parser(html, url)
            print(f"    [+] Found {len(jobs)} listings on {name}'s careers page.")
            all_jobs.extend(jobs)
        await browser.close()
    return all_jobs


if __name__ == "__main__":
    print("=== Checking career page watchlist ===")
    jobs = asyncio.run(scrape_career_pages())
    for j in jobs:
        print(f"- {j['title']} ({j['company']}) -> {j['link']}")