import asyncio
import urllib.parse
import streamlit as st
from database import get_all_jobs, update_job_status
from main import run_pipeline

st.set_page_config(page_title="Embedded Job Matcher", page_icon="⚡", layout="wide")
st.title("⚡ Embedded Firmware Job Search Companion")
st.caption(
    "Domain-matched to your Embedded C, ESP32, STM32, KiCad, and protocol skills — "
    "and experience-filtered against the actual job description, not just LinkedIn's tag."
)

# ---- Run a fresh scan without touching a terminal ----
col_run, col_status = st.columns([1, 4])
with col_run:
    run_clicked = st.button("🔄 Run New Scan Now", type="primary")
if run_clicked:
    with st.spinner("Scanning LinkedIn + Indeed + career pages... this takes a few minutes "
                     "since we open each job individually to check the real experience requirement."):
        added, rej_senior, rej_domain = asyncio.run(run_pipeline())
    st.success(
        f"Done — {added} new jobs saved. "
        f"Filtered out {rej_senior} for being too senior and {rej_domain} for being off-domain."
    )
    st.rerun()

st.divider()

# ---- Filters ----
st.sidebar.header("Filter & Settings")
status_filter = st.sidebar.selectbox("Application Status", ["ALL", "NEW", "APPLIED", "SAVED"])
verdict_filter = st.sidebar.selectbox(
    "Experience Fit", ["ALL", "FIT", "STRETCH"],
    help="FIT = clearly 0-2 yrs. STRETCH = no explicit signal found, verify manually. "
         "REJECTed jobs (3+ yrs) are never saved to begin with."
)
city_filter = st.sidebar.selectbox("City", ["ALL", "Bengaluru", "Hyderabad", "Chennai", "India/Remote"])

jobs = get_all_jobs(status_filter=status_filter, verdict_filter=verdict_filter)

if city_filter != "ALL":
    key = "India" if city_filter == "India/Remote" else city_filter
    jobs = [j for j in jobs if key.lower() in (j[4] or "").lower() or key.lower() in (j[1] or "").lower()]

st.subheader(f"Listings: {len(jobs)}")

if not jobs:
    st.info("No jobs match this filter yet. Click **Run New Scan Now** above to fetch fresh listings.")
else:
    for job in jobs:
        job_id, source, title, company, loc, link, score, exp_verdict, exp_reason, status = job

        verdict_color = {"FIT": "green", "STRETCH": "orange"}.get(exp_verdict, "gray")

        with st.container():
            col1, col2, col3 = st.columns([4, 2, 2])
            with col1:
                st.markdown(f"### {title}")
                st.markdown(f"**Company:** {company} | **Location:** {loc}")
                st.markdown(
                    f"**Source:** `{source}` | **Domain Match:** :green[{score}%] | "
                    f"**Experience:** :{verdict_color}[{exp_verdict}]"
                )
                st.caption(exp_reason)
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
                btn_col1, btn_col2 = st.columns(2)
                with btn_col1:
                    if st.button("Mark Applied", key=f"apply_{job_id}"):
                        update_job_status(job_id, "APPLIED")
                        st.rerun()
                with btn_col2:
                    if st.button("Save", key=f"save_{job_id}"):
                        update_job_status(job_id, "SAVED")
                        st.rerun()
        st.divider()