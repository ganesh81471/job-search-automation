"""
ats_api_scraper.py
--------------------
Instead of scraping Google Jobs (fragile, heavily anti-bot-protected, and a
worse ToS situation than LinkedIn), this hits the OFFICIAL PUBLIC JSON APIs
that Greenhouse and Lever provide for embedding their job boards elsewhere.
These are meant to be machine-read — no browser, no bot-detection fight,
no HTML parsing to break when a site redesigns.

Limitation, honestly: this only covers companies that use Greenhouse or
Lever as their ATS. Big caps (Bosch, Qualcomm, TI) mostly run Workday or
SuccessFactors instead, which don't offer an equivalent open JSON feed —
those still need to go on the career_pages_scraper.py watchlist by hand.
This tool is strongest for mid-size/startup companies, which is exactly
where a lot of the genuine 0-2 yr embedded openings have been showing up
in our searches anyway (Cionlabs-style companies, not Bosch-style ones).

No Playwright needed here — these are plain HTTP GET requests.
"""

import requests

# Add Greenhouse board tokens here. Find a company's token by checking if
# https://boards.greenhouse.io/<token> exists — that <token> is what goes here.
GREENHOUSE_BOARDS = [
    # "example-company",
]

# Add Lever company slugs here. Find it from https://jobs.lever.co/<slug>
LEVER_BOARDS = [
    # "example-company",
]

KEYWORDS = ["embedded", "firmware", "esp32", "stm32", "iot", "robotics"]


def _matches_keywords(title):
    title_lower = title.lower()
    return any(kw in title_lower for kw in KEYWORDS)


def fetch_greenhouse_jobs(board_token):
    url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true"
    jobs = []
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        for j in data.get("jobs", []):
            title = j.get("title", "")
            if not _matches_keywords(title):
                continue
            jobs.append({
                "title": title,
                "company": board_token,
                "location": (j.get("location") or {}).get("name", "N/A"),
                "link": j.get("absolute_url", "N/A"),
                "description": j.get("content", ""),  # HTML — strip tags before display if needed
                "seniority_label": None,
            })
    except Exception as e:
        print(f"    [!] Greenhouse board '{board_token}' failed: {e}")
    return jobs


def fetch_lever_jobs(company_slug):
    url = f"https://api.lever.co/v0/postings/{company_slug}?mode=json"
    jobs = []
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        for j in data:
            title = j.get("text", "")
            if not _matches_keywords(title):
                continue
            jobs.append({
                "title": title,
                "company": company_slug,
                "location": (j.get("categories") or {}).get("location", "N/A"),
                "link": j.get("hostedUrl", "N/A"),
                "description": j.get("descriptionPlain", "") or j.get("description", ""),
                "seniority_label": None,
            })
    except Exception as e:
        print(f"    [!] Lever board '{company_slug}' failed: {e}")
    return jobs


def scrape_ats_boards():
    all_jobs = []
    for token in GREENHOUSE_BOARDS:
        print(f"[*] Checking Greenhouse: {token}")
        found = fetch_greenhouse_jobs(token)
        print(f"    [+] {len(found)} matching listings")
        all_jobs.extend(found)
    for slug in LEVER_BOARDS:
        print(f"[*] Checking Lever: {slug}")
        found = fetch_lever_jobs(slug)
        print(f"    [+] {len(found)} matching listings")
        all_jobs.extend(found)
    return all_jobs


if __name__ == "__main__":
    print("=== Checking ATS API watchlist (Greenhouse + Lever) ===")
    if not GREENHOUSE_BOARDS and not LEVER_BOARDS:
        print("No boards configured yet — add company tokens to GREENHOUSE_BOARDS / "
              "LEVER_BOARDS at the top of this file first.")
    else:
        jobs = scrape_ats_boards()
        for j in jobs:
            print(f"- {j['title']} ({j['company']}) -> {j['link']}")