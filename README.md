<div align="center">

# ⚡ Embedded Firmware Job Search Companion

**A multi-source job aggregator that doesn't trust "Entry level" tags — it reads the actual job description.**

![Python](https://img.shields.io/badge/python-3.10%2B-blue?logo=python&logoColor=white)
![Playwright](https://img.shields.io/badge/playwright-automation-45ba4b?logo=playwright&logoColor=white)
![Streamlit](https://img.shields.io/badge/streamlit-dashboard-ff4b4b?logo=streamlit&logoColor=white)
![SQLite](https://img.shields.io/badge/sqlite-storage-07405e?logo=sqlite&logoColor=white)
![Status](https://img.shields.io/badge/status-active-brightgreen)

</div>

---

> **Why this exists:** LinkedIn's "Entry level" tag is unreliable — plenty of roles tagged Entry level actually want 2–8 years once you read the JD. Manually checking that, job by job, across five sites, every single day during a job search isn't sustainable. This automates the verification so the only thing left for a human to decide is *whether to apply.*
>
> Built while running my own 0–2 yr embedded firmware search across Bengaluru, Hyderabad, and Chennai.

## 📋 Table of Contents

- [What it does](#-what-it-does)
- [Architecture](#️-architecture)
- [Setup](#-setup)
- [Usage](#-usage)
- [Known limitations](#️-known-limitations)
- [Roadmap](#-roadmap)

## ✨ What it does

| | |
|---|---|
| 🔍 **5 sources, 1 run** | LinkedIn, Indeed, Naukri, a configurable career-page watchlist, and Greenhouse/Lever's official public job APIs |
| 🧠 **Real experience filtering** | Every job's title *and* description are checked for explicit year requirements, senior-sounding titles get hard-rejected even with a thin JD, and LinkedIn's own seniority tag is used as a fallback — jobs wanting 3+ years never even get saved |
| 🖱️ **One-click dashboard** | Streamlit app with a **Run New Scan Now** button — no terminal required for daily use |
| 📱 **Telegram notifications** | "X new jobs found" pinged straight to my phone on scan completion |
| ⏰ **Fully scheduled** | Windows Task Scheduler runs it every morning at 9am, unattended |
| 🛡️ **Resilient by design** | Each source runs in isolated error handling — one broken selector doesn't take down the other four |
| 🗂️ **Status tracking** | Mark jobs Applied / Saved / Discarded right from the dashboard |

## 🏗️ Architecture

```
main.py                      orchestrates all sources, isolates failures per-source
├── linkedin_scraper.py      Playwright — LinkedIn's public guest job search
├── indeed_scraper.py        Playwright — Indeed
├── naukri_scraper.py        Playwright — Naukri
├── career_pages_scraper.py  config-driven watchlist of direct company career pages
├── ats_api_scraper.py       plain HTTP — Greenhouse & Lever's official public JSON APIs
├── experience_filter.py     the core seniority-detection logic, used by every source
├── database.py              SQLite persistence, auto-migrates schema on startup
├── telegram_notify.py       sends the "scan done" message to my phone
└── app.py                   Streamlit dashboard — the actual daily-use interface
```

<details>
<summary><b>Why Greenhouse/Lever instead of scraping Google Jobs?</b></summary>
<br>

Google Search has much stronger anti-bot detection than any single job board, and the Jobs panel is a heavy JS widget, not static HTML. Greenhouse and Lever both publish official, documented public JSON APIs meant for embedding — reading those isn't fragile scraping, it's consuming a real feed. The tradeoff: this only covers companies using those two specific ATS platforms.

</details>

## 🚀 Setup

```bash
git clone https://github.com/ganesh81471/job-search-automation.git
cd job-search-automation
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
playwright install chromium
```

<details>
<summary><b>Configure Telegram notifications (optional, ~3 min)</b></summary>
<br>

1. Message `@BotFather` on Telegram, send `/newbot`, follow the prompts.
2. Paste the token it gives you into `BOT_TOKEN` in `telegram_notify.py`.
3. Message your new bot once (anything), then run `python telegram_notify.py --get-chat-id`.
4. Paste the printed chat ID into `CHAT_ID` in the same file.

</details>

<details>
<summary><b>Configure your target search</b></summary>
<br>

Edit the constants at the top of `main.py`:

```python
KEYWORDS = "Embedded Firmware"
LOCATIONS = ["Bengaluru", "Hyderabad", "Chennai", "India"]
HOURS_WINDOW = 168  # freshness window in hours
```

</details>

## 📱 Usage

Double-click **`start_dashboard.bat`** (Windows) or run `./start_dashboard.sh` (Mac/Linux) — opens the dashboard in your browser. Click **Run New Scan Now** for an on-demand scan, or let the scheduled run handle it and just watch for the Telegram ping.

**For the automated daily scan:** set up a Windows Task Scheduler task pointing at `venv\Scripts\python.exe` with argument `main.py`, triggered daily at your preferred time.

## ⚠️ Known limitations

Being upfront about these rather than pretending they don't exist:

- [ ] **HTML scrapers (LinkedIn/Indeed/Naukri) are inherently fragile** — these sites change their markup periodically; a broken selector returns 0 jobs from that source until updated. The pipeline tolerates this (other sources keep running), but it needs occasional maintenance.
- [ ] **ATS-API source only covers Greenhouse and Lever** — many Indian startups actually use Zoho Recruit instead, which isn't covered yet.
- [ ] **Career-page watchlist is manually configured**, one parser per company — doesn't generically handle arbitrary company websites.
- [ ] **Scraping LinkedIn/Indeed/Naukri technically runs against their Terms of Service.** Built and run for personal, low-frequency, local use — not deployed at scale.
- [ ] **Naukri doesn't expose a clean "posted in last N days" filter** like LinkedIn/Indeed — freshness is read off each listing's relative-date text instead.

## 🔭 Roadmap

- [ ] Multi-resume matching — score each job against several resume variants (embedded / IoT / automation-focused) and surface which one fits best per listing
- [ ] Zoho Recruit API investigation, to extend ATS-API coverage of Indian startups
- [ ] Desktop notification as a lighter-weight alternative to Telegram

---

<div align="center">

Built with Python, Playwright, BeautifulSoup, SQLite, Streamlit, and the Telegram Bot API.

</div>
