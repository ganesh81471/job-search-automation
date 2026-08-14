import asyncio
from database import init_db, save_jobs, get_all_jobs
from linkedin_scraper import scrape_linkedin_jobs
from indeed_scraper import scrape_indeed_jobs
from naukri_scraper import scrape_naukri_jobs
from career_pages_scraper import scrape_career_pages
from ats_api_scraper import scrape_ats_boards

# Edit these to match your actual target search.
KEYWORDS = "Embedded Firmware"
LOCATIONS = ["Bengaluru", "Hyderabad", "Chennai", "India"]  # "India" catches remote-tagged roles too
HOURS_WINDOW = 168  # 7 days, per your current rule. Set to 24 once daily supply improves.
MAX_DETAIL_FETCHES_PER_LOCATION = 15  # caps how many job pages we open per city, per run


async def run_pipeline():
    print("\n" + "=" * 55)
    print("STARTING JOB AGGREGATOR — LinkedIn + Indeed + Career Pages")
    print("=" * 55 + "\n")

    init_db()
    total_added = total_rejected_senior = total_rejected_domain = 0

    # ---- LinkedIn, per city ----
    for loc in LOCATIONS:
        print(f"--- LinkedIn: {KEYWORDS} in {loc} ---")
        jobs = await scrape_linkedin_jobs(
            keywords=KEYWORDS, location=loc, hours=HOURS_WINDOW,
            fetch_details=True, max_detail_fetches=MAX_DETAIL_FETCHES_PER_LOCATION,
        )
        added, rej_senior, rej_domain = save_jobs(jobs, source_name=f"LinkedIn-{loc}")
        total_added += added
        total_rejected_senior += rej_senior
        total_rejected_domain += rej_domain
        print(f"[+] {loc}: {len(jobs)} scraped | {added} saved | "
              f"{rej_senior} rejected (too senior) | {rej_domain} rejected (off-domain)\n")

    # ---- Indeed, per city ----
    for loc in LOCATIONS:
        if loc == "India":
            continue  # Indeed needs a real city, skip the remote catch-all here
        print(f"--- Indeed: {KEYWORDS} in {loc} ---")
        jobs = await scrape_indeed_jobs(
            keywords=f"{KEYWORDS} Engineer", location=loc, days=7,
            fetch_details=True, max_detail_fetches=MAX_DETAIL_FETCHES_PER_LOCATION,
        )
        added, rej_senior, rej_domain = save_jobs(jobs, source_name=f"Indeed-{loc}")
        total_added += added
        total_rejected_senior += rej_senior
        total_rejected_domain += rej_domain
        print(f"[+] {loc}: {len(jobs)} scraped | {added} saved | "
              f"{rej_senior} rejected (too senior) | {rej_domain} rejected (off-domain)\n")

    # ---- Naukri, per city ----
    for loc in LOCATIONS:
        if loc == "India":
            continue
        print(f"--- Naukri: {KEYWORDS} in {loc} ---")
        jobs = await scrape_naukri_jobs(
            keywords=f"{KEYWORDS} Engineer", location=loc,
            fetch_details=True, max_detail_fetches=MAX_DETAIL_FETCHES_PER_LOCATION,
        )
        added, rej_senior, rej_domain = save_jobs(jobs, source_name=f"Naukri-{loc}")
        total_added += added
        total_rejected_senior += rej_senior
        total_rejected_domain += rej_domain
        print(f"[+] {loc}: {len(jobs)} scraped | {added} saved | "
              f"{rej_senior} rejected (too senior) | {rej_domain} rejected (off-domain)\n")

    # ---- Career page watchlist ----
    print("--- Career page watchlist ---")
    jobs = await scrape_career_pages()
    added, rej_senior, rej_domain = save_jobs(jobs, source_name="CareerPage", min_domain_score=0)
    total_added += added
    total_rejected_senior += rej_senior
    total_rejected_domain += rej_domain
    print(f"[+] Career pages: {len(jobs)} scraped | {added} saved\n")

    # ---- ATS APIs (Greenhouse/Lever watchlist) ----
    print("--- ATS API watchlist (Greenhouse + Lever) ---")
    jobs = scrape_ats_boards()  # not async — plain HTTP requests
    added, rej_senior, rej_domain = save_jobs(jobs, source_name="ATS-API", min_domain_score=0)
    total_added += added
    total_rejected_senior += rej_senior
    total_rejected_domain += rej_domain
    print(f"[+] ATS API boards: {len(jobs)} scraped | {added} saved\n")

    all_stored_jobs = get_all_jobs()
    print("=" * 55)
    print(f"RUN SUMMARY: {total_added} new jobs saved this run | "
          f"{total_rejected_senior} rejected for seniority | "
          f"{total_rejected_domain} rejected off-domain")
    print(f"Total jobs in database: {len(all_stored_jobs)}")
    print("=" * 55 + "\n")

    return total_added, total_rejected_senior, total_rejected_domain


if __name__ == "__main__":
    asyncio.run(run_pipeline())