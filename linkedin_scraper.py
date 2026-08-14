import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from url_builder import JobUrlBuilder


async def _fetch_job_detail(context, job_url):
    """Opens a single job's page to pull full description + seniority label.
    This is what lets experience_filter.classify_experience() actually work —
    the card view alone never has enough text to judge seniority."""
    page = await context.new_page()
    description, seniority_label = "", None
    try:
        await page.goto(job_url, wait_until="domcontentloaded", timeout=15000)
        await page.wait_for_timeout(1200)
        content = await page.content()
        soup = BeautifulSoup(content, "html.parser")

        desc_tag = soup.find("div", class_="show-more-less-html__markup")
        if desc_tag:
            description = desc_tag.get_text(" ", strip=True)

        for li in soup.find_all("li", class_="description__job-criteria-item"):
            label = li.find("h3", class_="description__job-criteria-subheader")
            value = li.find("span", class_="description__job-criteria-text")
            if label and value and "seniority" in label.get_text(strip=True).lower():
                seniority_label = value.get_text(strip=True)
    except Exception as e:
        print(f"    [!] Could not load detail page ({job_url}): {e}")
    finally:
        await page.close()
    return description, seniority_label


async def scrape_linkedin_jobs(keywords="Embedded Firmware", location="India",
                                hours=24, fetch_details=True, max_detail_fetches=20):
    """
    hours: freshness window passed to LinkedIn's own f_TPR filter (24, 48, 168 for a week...)
    fetch_details: if True, visits each job's own page to get full description +
                    seniority label (slower, but required for real experience filtering)
    max_detail_fetches: cap on how many detail pages to open per run, so a broad
                    search doesn't take forever or hammer LinkedIn too hard
    """
    url_builder = JobUrlBuilder(keywords=keywords, location=location, hours=hours)
    target_url = url_builder.build_linkedin_url()
    print(f"[*] Navigating to LinkedIn URL: {target_url}\n")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        await page.goto(target_url, wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)
        await page.evaluate("window.scrollBy(0, 1500)")
        await page.wait_for_timeout(2000)

        content = await page.content()
        soup = BeautifulSoup(content, "html.parser")
        job_cards = soup.find_all("div", class_="base-search-card")

        jobs = []
        for card in job_cards:
            title_tag = card.find("h3", class_="base-search-card__title")
            company_tag = card.find("h4", class_="base-search-card__subtitle")
            location_tag = card.find("span", class_="job-search-card__location")
            link_tag = card.find("a", class_="base-card__full-link")

            title = title_tag.get_text(strip=True) if title_tag else "N/A"
            company = company_tag.get_text(strip=True) if company_tag else "N/A"
            job_location = location_tag.get_text(strip=True) if location_tag else "N/A"
            job_link = link_tag["href"] if link_tag and link_tag.has_attr("href") else None
            if job_link and "?" in job_link:
                job_link = job_link.split("?")[0]

            if not job_link:
                continue

            jobs.append({
                "title": title, "company": company, "location": job_location,
                "link": job_link, "description": "", "seniority_label": None,
            })

        # Fetch full descriptions for real experience-level filtering.
        if fetch_details:
            to_fetch = jobs[:max_detail_fetches]
            print(f"[*] Fetching detail pages for {len(to_fetch)} jobs "
                  f"(needed for experience filtering)...")
            for i, job in enumerate(to_fetch, 1):
                desc, seniority = await _fetch_job_detail(context, job["link"])
                job["description"] = desc
                job["seniority_label"] = seniority
                print(f"    [{i}/{len(to_fetch)}] {job['title'][:50]}")
                await page.wait_for_timeout(600)  # be polite, don't hammer LinkedIn

        await browser.close()
        return jobs


if __name__ == "__main__":
    print("=== Starting LinkedIn Job Scraper Test ===")
    scraped_jobs = asyncio.run(scrape_linkedin_jobs(keywords="Embedded Firmware", location="India"))
    print(f"\n[+] Total Jobs Found: {len(scraped_jobs)}\n")
    for idx, job in enumerate(scraped_jobs[:5], 1):
        print(f"{idx}. {job['title']} at {job['company']} ({job['location']})")
        print(f"   Apply Link: {job['link']}\n")