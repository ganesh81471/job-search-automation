import asyncio
import traceback
from database import init_db, save_jobs, get_all_jobs
from linkedin_scraper import scrape_linkedin_jobs
from indeed_scraper import scrape_indeed_jobs
from naukri_scraper import scrape_naukri_jobs
from career_pages_scraper import scrape_career_pages
from ats_api_scraper import scrape_ats_boards
from telegram_notify import send_notification

# Two tracks now, not one — you're targeting both embedded/firmware AND
# python/automation roles, and a single hardcoded "Embedded Firmware" string
# meant automation-track jobs never got searched for at all.
# (track_name, search_keywords)
KEYWORD_TRACKS = [
    ("embedded", "Embedded Firmware"),
    ("automation", "Python Automation Engineer"),
]
LOCATIONS = ["Bengaluru", "Hyderabad", "Chennai", "India"]  # "India" catches remote-tagged roles too
HOURS_WINDOW = 168  # 7 days, per your current rule. Set to 24 once daily supply improves.
# LinkedIn alone was returning 60 scraped cards per location but only checking
# 15 of them — the other 45 got silently treated as "unverified" and rejected
# under strict mode, even though we never actually looked at them. Raised
# this so more of what's scraped actually gets a fair check. Runs will take
# longer as a direct tradeoff.
MAX_DETAIL_FETCHES_PER_LOCATION = 40


async def _run_source(label, coro, min_domain_score=50, track="embedded"):
    """Runs one source, saves its results, and NEVER lets an exception here
    kill the rest of the pipeline. If Naukri's selectors break, LinkedIn's
    results already saved stay saved, and career pages / ATS-API still run
    after it. Returns a dict of stats for this source."""
    print(f"--- {label} ---")
    try:
        jobs = await coro
        added, rej_senior, rej_unverified, rej_domain = save_jobs(
            jobs, source_name=label, min_domain_score=min_domain_score, track=track
        )
        print(f"[+] {label}: {len(jobs)} scraped | {added} saved | "
              f"{rej_senior} rejected (confirmed 2+ yrs/senior title) | "
              f"{rej_unverified} rejected (no signal found, unverified) | "
              f"{rej_domain} rejected (off-domain)\n")
        return {"label": label, "ok": True, "scraped": len(jobs), "added": added,
                "rej_senior": rej_senior, "rej_unverified": rej_unverified, "rej_domain": rej_domain}
    except Exception as e:
        print(f"[!] {label} FAILED — skipping, moving to next source. Error: {e}")
        traceback.print_exc()
        print()
        return {"label": label, "ok": False, "error": str(e), "scraped": 0, "added": 0,
                "rej_senior": 0, "rej_unverified": 0, "rej_domain": 0}


async def run_pipeline():
    print("\n" + "=" * 55)
    print("STARTING JOB AGGREGATOR — LinkedIn + Indeed + Naukri + Career Pages + ATS APIs")
    print(f"Tracks: {', '.join(t[0] for t in KEYWORD_TRACKS)}")
    print("=" * 55 + "\n")

    init_db()
    results = []

    for track, keywords in KEYWORD_TRACKS:
        for loc in LOCATIONS:
            results.append(await _run_source(
                f"LinkedIn-{track}-{loc}",
                scrape_linkedin_jobs(keywords=keywords, location=loc, hours=HOURS_WINDOW,
                                      fetch_details=True, max_detail_fetches=MAX_DETAIL_FETCHES_PER_LOCATION),
                track=track,
            ))

        for loc in LOCATIONS:
            if loc == "India":
                continue
            results.append(await _run_source(
                f"Indeed-{track}-{loc}",
                scrape_indeed_jobs(keywords=keywords, location=loc, days=7,
                                    fetch_details=True, max_detail_fetches=MAX_DETAIL_FETCHES_PER_LOCATION),
                track=track,
            ))

        for loc in LOCATIONS:
            if loc == "India":
                continue
            results.append(await _run_source(
                f"Naukri-{track}-{loc}",
                scrape_naukri_jobs(keywords=keywords, location=loc,
                                    fetch_details=True, max_detail_fetches=MAX_DETAIL_FETCHES_PER_LOCATION),
                track=track,
            ))

    # Career pages and ATS-API aren't keyword-searched (they list everything
    # a company has open), so these run once, not once per track.
    results.append(await _run_source("CareerPage", scrape_career_pages()))

    print("--- ATS-API ---")
    try:
        ats_jobs = scrape_ats_boards()
        added, rej_senior, rej_unverified, rej_domain = save_jobs(
            ats_jobs, source_name="ATS-API", min_domain_score=0
        )
        print(f"[+] ATS-API: {len(ats_jobs)} scraped | {added} saved\n")
        results.append({"label": "ATS-API", "ok": True, "scraped": len(ats_jobs), "added": added,
                         "rej_senior": rej_senior, "rej_unverified": rej_unverified, "rej_domain": rej_domain})
    except Exception as e:
        print(f"[!] ATS-API FAILED: {e}\n")
        results.append({"label": "ATS-API", "ok": False, "error": str(e), "scraped": 0, "added": 0,
                         "rej_senior": 0, "rej_unverified": 0, "rej_domain": 0})

    total_added = sum(r["added"] for r in results)
    total_rej_senior = sum(r["rej_senior"] for r in results)
    total_rej_unverified = sum(r["rej_unverified"] for r in results)
    total_rej_domain = sum(r["rej_domain"] for r in results)
    failed_sources = [r["label"] for r in results if not r["ok"]]

    all_stored_jobs = get_all_jobs()
    print("=" * 55)
    print(f"RUN SUMMARY: {total_added} new jobs saved this run")
    print(f"  {total_rej_senior} rejected — confirmed 2+ yrs or senior-worded title")
    print(f"  {total_rej_unverified} rejected — no experience signal found, unverified (strict mode)")
    print(f"  {total_rej_domain} rejected — off-domain (not embedded/automation related)")
    if failed_sources:
        print(f"Sources that FAILED this run (check errors above): {', '.join(failed_sources)}")
    print(f"Total jobs in database: {len(all_stored_jobs)}")
    print("=" * 55 + "\n")

    msg_lines = [
        "🔍 Job scan complete.",
        f"{total_added} new jobs found — go check the dashboard and apply.",
        f"({total_rej_senior} too senior, {total_rej_unverified} unverified, "
        f"{total_rej_domain} off-domain)",
    ]
    if failed_sources:
        msg_lines.append(f"⚠️ These sources failed this run: {', '.join(failed_sources)}")
    send_notification("\n".join(msg_lines))

    return total_added, total_rej_senior, total_rej_domain, results


if __name__ == "__main__":
    asyncio.run(run_pipeline())