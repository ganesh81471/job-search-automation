"""
run_all.py
-----------
Single entry point for the ONE Task Scheduler task, triggered every 30
minutes, that does both jobs this project needs:

  1. EVERY run (every 30 min): checks Prashanth Jakkula's LinkedIn
     profile for a new post, notifies via Telegram if there is one.
     (linkedin_profile_watcher.py — cheap, one page, safe at 30-min cadence.)

  2. ONCE PER DAY, on the first run at/after 9am: runs the full job
     scan (main.py's run_pipeline — LinkedIn/Indeed/Naukri/career pages/
     ATS APIs) and sends the morning digest.
     Deliberately NOT run every 30 min — that's a much heavier scrape
     across 3 sites and would raise ToS/rate-limit risk for no benefit,
     since new junior openings don't appear every half hour anyway.

State for "have we already run today's full scan" lives in
last_scan_state.json (gitignored, next to this file) — safe to delete
any time to force the next run to do a full scan regardless of time.

SETUP:
  Point ONE Windows Task Scheduler task at:
    venv\\Scripts\\python.exe run_all.py
  Trigger: repeat every 30 minutes, all day, indefinitely.

  This replaces having two separate scheduled tasks — main.py and
  linkedin_profile_watcher.py are still runnable standalone (e.g. for
  manual testing) but the scheduler should only call this file.
"""

import asyncio
import json
import os
from datetime import date, datetime

from main import run_pipeline
from linkedin_profile_watcher import run_once as check_profile_posts

STATE_FILE = "last_scan_state.json"
FULL_SCAN_TARGET_HOUR = 9  # run the full job scan once per day, at/after this hour


def _load_state():
    if not os.path.exists(STATE_FILE):
        return {}
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def _should_run_full_scan(state):
    today = date.today().isoformat()
    if state.get("last_full_scan_date") == today:
        return False  # already ran today
    return datetime.now().hour >= FULL_SCAN_TARGET_HOUR


async def main_async():
    state = _load_state()

    # --- Part 1: full job scan, once per day ---
    if _should_run_full_scan(state):
        print("[*] First check at/after 9am today — running full job scan...\n")
        await run_pipeline()
        state["last_full_scan_date"] = date.today().isoformat()
        _save_state(state)
    else:
        print("[.] Full job scan already done today (or it's before 9am) — skipping.\n")

    # --- Part 2: profile watcher, every run ---
    print("[*] Checking Prashanth Jakkula's LinkedIn profile for new posts...")
    await check_profile_posts()


if __name__ == "__main__":
    asyncio.run(main_async())