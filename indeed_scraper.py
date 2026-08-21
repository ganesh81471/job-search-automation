import asyncio
import urllib.parse
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup


async def _fetch_indeed_detail(context, job_url):
    page = await context.new_page()
    description = ""
    try:
        await page.goto(job_url, wait_until="domcontentloaded", timeout=15000)
        await page.wait_for_timeout(1200)
        content = await page.content()
        soup = BeautifulSoup(content, "html.parser")
        desc_tag = soup.find("div", id="jobDescriptionText")
        if desc_tag:
            description = desc_tag.get_text(" ", strip=True)
    except Exception as e:
        print(f"    [!] Could not load Indeed detail page ({job_url}): {e}")
    finally:
        await page.close()
    return description


async def scrape_indeed_jobs(keywords="Embedded Firmware Engineer", location="Bengaluru",
                              days=1, fetch_details=True, max_detail_fetches=20):
    """
    days: Indeed's own freshness filter (fromage=N, N in days). Use 1 for
          "last 24 hours", 3, 7, etc.
    """
    encoded_kw = urllib.parse.quote(keywords)
    encoded_loc = urllib.parse.quote(location)
    target_url = (f"https://in.indeed.com/jobs?q={encoded_kw}&l={encoded_loc}"
                  f"&fromage={days}&sort=date")
    print(f"[*] Navigating to Indeed URL: {target_url}\n")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        await page.goto(target_url, wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)

        content = await page.content()
        soup = BeautifulSoup(content, "html.parser")
        # Indeed's markup changes fairly often — this selector may need updating.
        cards = soup.find_all("div", class_="job_seen_beacon")

        if not cards or all(
            not c.find("h2", class_="jobTitle") for c in cards
        ):
            debug_path = f"debug_indeed_{location}.html"
            with open(debug_path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"    [!] Indeed selectors found nothing usable — dumped raw response "
                  f"to {debug_path}. Open it in a browser: if it shows real job listings, "
                  f"our CSS selectors are stale. If it shows a CAPTCHA/'verify you're human' "
                  f"page, Indeed is blocking the scraper and selectors won't fix it.")

        jobs = []
        for card in cards:
            title_tag = card.find("h2", class_="jobTitle")
            company_tag = card.find("span", class_="companyName")
            location_tag = card.find("div", class_="companyLocation")
            link_tag = card.find("a", href=True)

            title = title_tag.get_text(strip=True) if title_tag else "N/A"
            company = company_tag.get_text(strip=True) if company_tag else "N/A"
            job_location = location_tag.get_text(strip=True) if location_tag else location
            job_link = None
            if link_tag and link_tag.get("href", "").startswith("/rc/clk"):
                job_link = "https://in.indeed.com" + link_tag["href"]

            if not job_link:
                continue

            jobs.append({
                "title": title, "company": company, "location": job_location,
                "link": job_link, "description": "", "seniority_label": None,
            })

        if fetch_details:
            to_fetch = jobs[:max_detail_fetches]
            print(f"[*] Fetching detail pages for {len(to_fetch)} Indeed jobs...")
            for i, job in enumerate(to_fetch, 1):
                desc = await _fetch_indeed_detail(context, job["link"])
                job["description"] = desc
                print(f"    [{i}/{len(to_fetch)}] {job['title'][:50]}")
                await page.wait_for_timeout(600)

        await browser.close()
        return jobs


if __name__ == "__main__":
    print("=== Starting Indeed Job Scraper Test ===")
    scraped_jobs = asyncio.run(scrape_indeed_jobs())
    print(f"\n[+] Total Jobs Found: {len(scraped_jobs)}\n")
    for idx, job in enumerate(scraped_jobs[:5], 1):
        print(f"{idx}. {job['title']} at {job['company']} ({job['location']})")