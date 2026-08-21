import asyncio
import urllib.parse
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup


async def _fetch_naukri_detail(context, job_url):
    page = await context.new_page()
    description = ""
    try:
        await page.goto(job_url, wait_until="domcontentloaded", timeout=15000)
        await page.wait_for_timeout(1200)
        content = await page.content()
        soup = BeautifulSoup(content, "html.parser")
        desc_tag = soup.find("div", class_="styles_JDC__dang-inner-html__h0K4t") \
            or soup.find("section", class_="job-desc")
        if desc_tag:
            description = desc_tag.get_text(" ", strip=True)
    except Exception as e:
        print(f"    [!] Could not load Naukri detail page ({job_url}): {e}")
    finally:
        await page.close()
    return description


async def scrape_naukri_jobs(keywords="Embedded Firmware Engineer", location="Bengaluru",
                              fetch_details=True, max_detail_fetches=20):
    """
    Naukri's search URL pattern uses hyphenated keyword-jobs-in-location slugs.
    Naukri doesn't have as clean a "posted in last N days" URL param as LinkedIn/Indeed —
    freshness has to be read off each listing's own "X days ago" text instead.
    """
    kw_slug = urllib.parse.quote(keywords.replace(" ", "-"))
    loc_slug = urllib.parse.quote(location.replace(" ", "-"))
    target_url = f"https://www.naukri.com/{kw_slug}-jobs-in-{loc_slug}"
    print(f"[*] Navigating to Naukri URL: {target_url}\n")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        await page.goto(target_url, wait_until="domcontentloaded")
        await page.wait_for_timeout(3500)

        content = await page.content()
        soup = BeautifulSoup(content, "html.parser")
        # Naukri's markup changes often — this is the current class as of last check.
        # If this returns 0 jobs, inspect the page manually and update the selector.
        cards = soup.find_all("div", class_="cust-job-tuple")

        if not cards:
            debug_path = f"debug_naukri_{location}.html"
            with open(debug_path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"    [!] Naukri found 0 job cards — dumped raw response to {debug_path}. "
                  f"Open it in a browser: real listings with different markup means stale "
                  f"selectors; a CAPTCHA/block page means Naukri is blocking the scraper.")

        jobs = []
        for card in cards:
            title_tag = card.find("a", class_="title")
            company_tag = card.find("a", class_="comp-name")
            location_tag = card.find("span", class_="locWdth")
            posted_tag = card.find("span", class_="job-post-day")

            title = title_tag.get_text(strip=True) if title_tag else "N/A"
            company = company_tag.get_text(strip=True) if company_tag else "N/A"
            job_location = location_tag.get_text(strip=True) if location_tag else location
            posted_text = posted_tag.get_text(strip=True) if posted_tag else ""
            job_link = title_tag["href"] if title_tag and title_tag.has_attr("href") else None

            if not job_link:
                continue

            jobs.append({
                "title": title, "company": company, "location": job_location,
                "link": job_link, "description": "", "seniority_label": None,
                "posted_text": posted_text,
            })

        if fetch_details:
            to_fetch = jobs[:max_detail_fetches]
            print(f"[*] Fetching detail pages for {len(to_fetch)} Naukri jobs...")
            for i, job in enumerate(to_fetch, 1):
                desc = await _fetch_naukri_detail(context, job["link"])
                job["description"] = desc
                print(f"    [{i}/{len(to_fetch)}] {job['title'][:50]} (posted: {job['posted_text']})")
                await page.wait_for_timeout(600)

        await browser.close()
        return jobs


if __name__ == "__main__":
    print("=== Starting Naukri Job Scraper Test ===")
    scraped_jobs = asyncio.run(scrape_naukri_jobs())
    print(f"\n[+] Total Jobs Found: {len(scraped_jobs)}\n")
    for idx, job in enumerate(scraped_jobs[:5], 1):
        print(f"{idx}. {job['title']} at {job['company']} ({job['location']}) — {job['posted_text']}")