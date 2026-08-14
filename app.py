import streamlit as st
import urllib.parse
from database import get_all_jobs, update_job_status

st.set_page_config(page_title="Embedded Job Matcher", page_icon="⚡", layout="wide")

st.title("⚡ Tailored Embedded Firmware Job Dashboard")
st.caption("Only showing jobs matching 75%+ of your Embedded C, ESP32, STM32, KiCad, and Protocol skills.")

st.sidebar.header("Filter & Settings")
status_filter = st.sidebar.selectbox("Filter by Status", ["ALL", "NEW", "APPLIED", "SAVED"])

jobs = get_all_jobs(status_filter=status_filter)

st.subheader(f"Relevant High-Match Listings: {len(jobs)}")

if not jobs:
    st.info("No high-matching jobs (>= 75%) found for this filter. Run 'python main.py' to fetch fresh jobs!")
else:
    for job in jobs:
        job_id, source, title, company, loc, link, score, status = job
        
        with st.container():
            col1, col2, col3 = st.columns([4, 2, 2])
            
            with col1:
                st.markdown(f"### **{title}**")
                st.markdown(f"**Company:** {company} | **Location:** {loc}")
                st.markdown(f"**Source:** `{source}` | **Match Score:** :green[**{score}% Match**]")
            
            with col2:
                st.markdown(f"[🔗 Apply on {source}]({link})")
                
                # Target HR / Embedded Leads for this specific company
                company_encoded = urllib.parse.quote(f'"{company}"')
                recruiter_search_url = f"https://www.linkedin.com/search/results/people/?keywords={company_encoded}%20%22Embedded%22%20OR%20%22Firmware%22%20OR%20%22Recruiter%22"
                
                st.markdown(f"[🎯 Find Embedded Lead / HR at {company}]({recruiter_search_url})")

            with col3:
                st.write(f"**Status:** `{status}`")
                btn_col1, btn_col2 = st.columns(2)
                with btn_col1:
                    if st.button("Mark Applied", key=f"apply_{job_id}"):
                        update_job_status(job_id, "APPLIED")
                        st.rerun()
                with btn_col2:
                    if st.button("Save Job", key=f"save_{job_id}"):
                        update_job_status(job_id, "SAVED")
                        st.rerun()

            st.divider()