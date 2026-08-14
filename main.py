import asyncio
from database import init_db, save_jobs, get_all_jobs
from linkedin_scraper import scrape_linkedin_jobs
from linkedin_posts_local import scrape_linkedin_posts

async def run_pipeline(keywords="Embedded Firmware", location="India"):
    print("\n==================================================")
    print("🚀 STARTING PLAYWRIGHT AUTOMATED JOB AGGREGATOR")
    print("==================================================\n")

    # 1. Initialize SQLite Database
    init_db()

    # 2. Run LinkedIn Job Listing Scraper
    print("--- [1/2] Scraping Public LinkedIn Job Portal ---")
    jobs = await scrape_linkedin_jobs(keywords=keywords, location=location)
    new_jobs_count = save_jobs(jobs, source_name="LinkedIn-Jobs")
    print(f"[+] LinkedIn Jobs: {len(jobs)} fetched | {new_jobs_count} new entries saved.\n")

    # 3. Run LinkedIn Hiring Posts Scraper
    print("--- [2/2] Scraping LinkedIn Hiring Posts & Feeds ---")
    posts = await scrape_linkedin_posts(keywords=keywords, location=location)
    new_posts_count = save_jobs(posts, source_name="LinkedIn-Posts")
    print(f"[+] LinkedIn Posts: {len(posts)} fetched | {new_posts_count} new entries saved.\n")

    # 4. Final DB Summary
    all_stored_jobs = get_all_jobs()
    print("==================================================")
    print(f"📊 SUMMARY: Total Unique Listings in Database: {len(all_stored_jobs)}")
    print("==================================================\n")

    print("Top 5 Recent Entries in Database:")
    for idx, entry in enumerate(all_stored_jobs[:5], 1):
        job_id, source, title, company, loc, link, status = entry
        print(f"{idx}. [{source}] {title} at {company} ({loc}) - Status: {status}")
        print(f"   Link: {link}\n")

if __name__ == "__main__":
    asyncio.run(run_pipeline(keywords="Embedded Firmware", location="India"))