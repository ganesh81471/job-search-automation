import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from url_builder import JobUrlBuilder

async def scrape_linkedin_jobs(keywords="Embedded Firmware", location="India"):
    # 1. Build search URL
    url_builder = JobUrlBuilder(keywords=keywords, location=location)
    target_url = url_builder.build_linkedin_url()
    print(f"[*] Navigating to LinkedIn URL: {target_url}\n")

    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        # 2. Open LinkedIn Jobs page
        await page.goto(target_url, wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)  # Wait 3s for job cards to render

        # 3. Scroll down slightly to trigger lazy-loading of job cards
        await page.evaluate("window.scrollBy(0, 1000)")
        await page.wait_for_timeout(2000)

        # 4. Extract raw HTML content
        content = await page.content()
        await browser.close()

        # 5. Parse HTML with BeautifulSoup
        soup = BeautifulSoup(content, "html.parser")
        job_cards = soup.find_all("div", class_="base-search-card")

        jobs = []
        for card in job_cards:
            # Extract Job Title
            title_tag = card.find("h3", class_="base-search-card__title")
            title = title_tag.get_text(strip=True) if title_tag else "N/A"

            # Extract Company Name
            company_tag = card.find("h4", class_="base-search-card__subtitle")
            company = company_tag.get_text(strip=True) if company_tag else "N/A"

            # Extract Location
            location_tag = card.find("span", class_="job-search-card__location")
            job_location = location_tag.get_text(strip=True) if location_tag else "N/A"

            # Extract Job Apply Link
            link_tag = card.find("a", class_="base-card__full-link")
            job_link = link_tag["href"] if link_tag and link_tag.has_attr("href") else "N/A"

            # Clean tracking params from URL if present
            if "?" in job_link:
                job_link = job_link.split("?")[0]

            jobs.append({
                "title": title,
                "company": company,
                "location": job_location,
                "link": job_link
            })

        return jobs

if __name__ == "__main__":
    print("=== Starting LinkedIn Job Scraper Test ===")
    scraped_jobs = asyncio.run(scrape_linkedin_jobs(keywords="Embedded Firmware", location="India"))
    
    print(f"\n[+] Total Jobs Found (Past 24 Hours): {len(scraped_jobs)}\n")
    for idx, job in enumerate(scraped_jobs[:5], 1):  # Display top 5
        print(f"{idx}. {job['title']} at {job['company']} ({job['location']})")
        print(f"   Apply Link: {job['link']}\n")