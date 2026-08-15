import asyncio
import traceback
from database import init_db, save_jobs, get_all_jobs
from linkedin_scraper import scrape_linkedin_jobs
from indeed_scraper import scrape_indeed_jobs
from naukri_scraper import scrape_naukri_jobs
from career_pages_scraper import scrape_career_pages
from ats_api_scraper import scrape_ats_boards
from telegram_notify import send_notification

# Edit these to match your actual target search.
KEYWORDS = "Embedded Firmware"
LOCATIONS = ["Bengaluru", "Hyderabad", "Chennai", "India"]  # "India" catches remote-tagged roles too
HOURS_WINDOW = 168  # 7 days, per your current rule. Set to 24 once daily supply improves.
MAX_DETAIL_FETCHES_PER_LOCATION = 15  # caps how many job pages we open per city, per run


async def _run_source(label, coro, min_domain_score=50):
    """Runs one source, saves its results, and NEVER lets an exception here
    kill the rest of the pipeline. If Naukri's selectors break, LinkedIn's
    results already saved stay saved, and career pages / ATS-API still run
    after it. Returns a dict of stats for this source."""
    print(f"--- {label} ---")
    try:
        jobs = await coro
        added, rej_senior, rej_domain = save_jobs(
            jobs, source_name=label, min_domain_score=min_domain_score
        )
        print(f"[+] {label}: {len(jobs)} scraped | {added} saved | "
              f"{rej_senior} rejected (too senior) | {rej_domain} rejected (off-domain)\n")
        return {"label": label, "ok": True, "scraped": len(jobs),
                "added": added, "rej_senior": rej_senior, "rej_domain": rej_domain}
    except Exception as e:
        print(f"[!] {label} FAILED — skipping, moving to next source. Error: {e}")
        traceback.print_exc()
        print()
        return {"label": label, "ok": False, "error": str(e),
                "scraped": 0, "added": 0, "rej_senior": 0, "rej_domain": 0}


async def run_pipeline():
    print("\n" + "=" * 55)
    print("STARTING JOB AGGREGATOR — LinkedIn + Indeed + Naukri + Career Pages + ATS APIs")
    print("=" * 55 + "\n")

    init_db()
    results = []

    for loc in LOCATIONS:
        results.append(await _run_source(
            f"LinkedIn-{loc}",
            scrape_linkedin_jobs(keywords=KEYWORDS, location=loc, hours=HOURS_WINDOW,
                                  fetch_details=True, max_detail_fetches=MAX_DETAIL_FETCHES_PER_LOCATION),
        ))

    for loc in LOCATIONS:
        if loc == "India":
            continue
        results.append(await _run_source(
            f"Indeed-{loc}",
            scrape_indeed_jobs(keywords=f"{KEYWORDS} Engineer", location=loc, days=7,
                                fetch_details=True, max_detail_fetches=MAX_DETAIL_FETCHES_PER_LOCATION),
        ))

    for loc in LOCATIONS:
        if loc == "India":
            continue
        results.append(await _run_source(
            f"Naukri-{loc}",
            scrape_naukri_jobs(keywords=f"{KEYWORDS} Engineer", location=loc,
                                fetch_details=True, max_detail_fetches=MAX_DETAIL_FETCHES_PER_LOCATION),
        ))

    results.append(await _run_source("CareerPage", scrape_career_pages(), min_domain_score=0))

    # ATS API is sync (plain requests), not async — wrap it the same way by hand.
    print("--- ATS-API ---")
    try:
        ats_jobs = scrape_ats_boards()
        added, rej_senior, rej_domain = save_jobs(ats_jobs, source_name="ATS-API", min_domain_score=0)
        print(f"[+] ATS-API: {len(ats_jobs)} scraped | {added} saved\n")
        results.append({"label": "ATS-API", "ok": True, "scraped": len(ats_jobs),
                         "added": added, "rej_senior": rej_senior, "rej_domain": rej_domain})
    except Exception as e:
        print(f"[!] ATS-API FAILED: {e}\n")
        results.append({"label": "ATS-API", "ok": False, "error": str(e),
                         "scraped": 0, "added": 0, "rej_senior": 0, "rej_domain": 0})

    total_added = sum(r["added"] for r in results)
    total_rejected_senior = sum(r["rej_senior"] for r in results)
    total_rejected_domain = sum(r["rej_domain"] for r in results)
    failed_sources = [r["label"] for r in results if not r["ok"]]

    all_stored_jobs = get_all_jobs()
    print("=" * 55)
    print(f"RUN SUMMARY: {total_added} new jobs saved this run | "
          f"{total_rejected_senior} rejected for seniority | "
          f"{total_rejected_domain} rejected off-domain")
    if failed_sources:
        print(f"Sources that FAILED this run (check errors above): {', '.join(failed_sources)}")
    print(f"Total jobs in database: {len(all_stored_jobs)}")
    print("=" * 55 + "\n")

    # Send the "go apply" nudge to your phone.
    msg_lines = [
        "🔍 Job scan complete.",
        f"{total_added} new jobs found — go check the dashboard and apply.",
        f"({total_rejected_senior} filtered out for being too senior, "
        f"{total_rejected_domain} off-domain)",
    ]
    if failed_sources:
        msg_lines.append(f"⚠️ These sources failed this run: {', '.join(failed_sources)}")
    send_notification("\n".join(msg_lines))

    return total_added, total_rejected_senior, total_rejected_domain, results


if __name__ == "__main__":
    asyncio.run(run_pipeline())