import asyncio
import urllib.parse
import streamlit as st
from database import get_all_jobs, update_job_status, get_stats, init_db
from main import run_pipeline

# Safe to call every time — CREATE TABLE IF NOT EXISTS + migration check.
# Without this, opening the dashboard before ever running main.py crashes
# with "no such table: jobs", since only main.py used to call this.
init_db()

st.set_page_config(page_title="Embedded Job Matcher", page_icon="⚡", layout="wide")
st.title("⚡ Embedded Firmware Job Search Companion")
st.caption(
    "Domain-matched to your Embedded C, ESP32, STM32, KiCad, and protocol skills — "
    "and experience-filtered against the actual job description AND title, not just LinkedIn's tag."
)

# ---- Run a fresh scan without touching a terminal ----
run_clicked = st.button("🔄 Run New Scan Now", type="primary")
if run_clicked:
    with st.spinner("Scanning LinkedIn + Indeed + Naukri + career pages + ATS APIs... "
                     "this takes a few minutes since each job gets opened individually "
                     "to check the real experience requirement."):
        added, rej_senior, rej_domain, results = asyncio.run(run_pipeline())
    failed = [r["label"] for r in results if not r["ok"]]
    st.success(
        f"Done — {added} new jobs saved. "
        f"Filtered out {rej_senior} for being too senior and {rej_domain} for being off-domain."
    )
    if failed:
        st.warning(f"These sources failed this run and were skipped (others still ran fine): "
                   f"{', '.join(failed)}. Check your terminal for the full error.")
    st.rerun()

st.divider()

# ---- Summary metrics ----
stats = get_stats()
m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Total in database", stats["total"])
m2.metric("New", stats["by_status"].get("NEW", 0))
m3.metric("Applied", stats["by_status"].get("APPLIED", 0))
m4.metric("Saved", stats["by_status"].get("SAVED", 0))
m5.metric("Discarded", stats["by_status"].get("DISCARDED", 0))

with st.expander("Source health (which sources are actually finding jobs)"):
    if stats["by_source"]:
        for source, count in stats["by_source"]:
            st.write(f"**{source}**: {count} jobs saved all-time")
    else:
        st.write("No jobs saved yet — run a scan first.")
    st.caption(
        f"Experience verdicts across everything saved: "
        f"FIT = {stats['by_verdict'].get('FIT', 0)}, "
        f"STRETCH (unverified) = {stats['by_verdict'].get('STRETCH', 0)}"
    )

st.divider()

# ---- Filters ----
st.sidebar.header("Filter & Settings")
status_filter = st.sidebar.selectbox(
    "Application Status",
    ["ALL", "NEW", "APPLIED", "SAVED", "DISCARDED", "ALL_INCLUDING_DISCARDED"],
    format_func=lambda x: "ALL (active only)" if x == "ALL"
        else ("ALL (incl. discarded)" if x == "ALL_INCLUDING_DISCARDED" else x),
)
verdict_filter = st.sidebar.selectbox(
    "Experience Fit", ["ALL", "FIT", "STRETCH"],
    help="FIT = clearly 0-2 yrs (JD, title, or LinkedIn tag confirms it). "
         "STRETCH = no clear signal either way, verify manually. "
         "Senior-titled or 3+ yr jobs are rejected before they're ever saved."
)
city_filter = st.sidebar.selectbox("City", ["ALL", "Bengaluru", "Hyderabad", "Chennai", "India/Remote"])
search_text = st.sidebar.text_input("Search title/company", "")
sort_by = st.sidebar.selectbox("Sort by", ["score", "newest", "company"],
                                format_func=lambda x: {"score": "Best match",
                                                        "newest": "Freshest",
                                                        "company": "Company A-Z"}[x])

jobs = get_all_jobs(status_filter=status_filter, verdict_filter=verdict_filter,
                     search_text=search_text or None, sort_by=sort_by)

if city_filter != "ALL":
    key = "India" if city_filter == "India/Remote" else city_filter
    jobs = [j for j in jobs if key.lower() in (j[4] or "").lower() or key.lower() in (j[1] or "").lower()]

st.subheader(f"Listings: {len(jobs)}")

if not jobs:
    st.info("No jobs match this filter yet. Click **Run New Scan Now** above to fetch fresh listings, "
            "or loosen a filter in the sidebar.")
else:
    for job in jobs:
        (job_id, source, title, company, loc, link, score,
         exp_verdict, exp_reason, status, min_years, max_years, date_found) = job

        verdict_color = {"FIT": "green", "STRETCH": "orange"}.get(exp_verdict, "gray")
        years_display = ""
        if min_years is not None:
            years_display = f" (~{min_years}{'+' if max_years and max_years >= 99 else f'-{max_years}' if max_years else ''} yrs)"

        with st.container(border=True):
            col1, col2, col3 = st.columns([4, 2, 2])
            with col1:
                st.markdown(f"### {title}")
                st.markdown(f"**Company:** {company} | **Location:** {loc}")
                st.markdown(
                    f"**Source:** `{source}` | **Domain Match:** :green[{score}%] | "
                    f"**Experience:** :{verdict_color}[{exp_verdict}]{years_display}"
                )
                st.caption(exp_reason)
                st.caption(f"Found: {date_found}")
            with col2:
                st.markdown(f"[🔗 Open listing]({link})")
                company_encoded = urllib.parse.quote(f'"{company}"')
                recruiter_url = (
                    f"https://www.linkedin.com/search/results/people/"
                    f"?keywords={company_encoded}%20%22Embedded%22%20OR%20%22Firmware%22%20OR%20%22Recruiter%22"
                )
                st.markdown(f"[🎯 Find HR/Embedded lead at {company}]({recruiter_url})")
            with col3:
                st.write(f"**Status:** `{status}`")
                b1, b2, b3 = st.columns(3)
                with b1:
                    if st.button("Applied", key=f"apply_{job_id}"):
                        update_job_status(job_id, "APPLIED")
                        st.rerun()
                with b2:
                    if st.button("Save", key=f"save_{job_id}"):
                        update_job_status(job_id, "SAVED")
                        st.rerun()
                with b3:
                    if st.button("🗑️ Discard", key=f"discard_{job_id}"):
                        update_job_status(job_id, "DISCARDED")
                        st.rerun()