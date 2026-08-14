import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from url_builder import JobUrlBuilder

async def scrape_linkedin_posts(keywords="Embedded Firmware", location="India"):
    url_builder = JobUrlBuilder(keywords=keywords, location=location)
    target_url = url_builder.build_linkedin_posts_url()
    print(f"[*] Searching LinkedIn Hiring Posts from: {target_url}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        try:
            await page.goto(target_url, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(4000)

            await page.evaluate("window.scrollBy(0, 1200)")
            await page.wait_for_timeout(2000)

            content = await page.content()
        finally:
            await browser.close()

        soup = BeautifulSoup(content, "html.parser")
        post_containers = soup.find_all("div", class_="feed-shared-update-v2")

        posts = []
        for post in post_containers[:10]:
            text_tag = post.find("div", class_="update-components-text")
            text = text_tag.get_text(strip=True) if text_tag else "N/A"

            actor_tag = post.find("span", class_="update-components-actor__title")
            author = actor_tag.get_text(strip=True) if actor_tag else "Recruiter/Founder"

            link_tag = post.find("a", class_="app-aware-link")
            post_link = link_tag["href"] if link_tag and link_tag.has_attr("href") else target_url

            posts.append({
                "title": f"Hiring Post by {author}",
                "company": author,
                "location": location,
                "experience": "N/A",
                "link": post_link,
                "snippet": text[:150]
            })

        return posts

if __name__ == "__main__":
    found_posts = asyncio.run(scrape_linkedin_posts("Embedded Firmware", "India"))
    print(f"[+] Found {len(found_posts)} hiring posts.")