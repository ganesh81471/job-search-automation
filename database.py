import sqlite3
import re
from experience_filter import classify_experience

DB_NAME = "jobs.db"

# Resume Skills Baseline for Keyword Matching
RESUME_KEYWORDS = [
    "esp32", "esp-idf", "stm32", "stm32cubeide", "microcontroller", "mcu", "firmware", "embedded",
    "embedded c", "c++", "cpp", "c/c++", "python",
    "uart", "spi", "i2c", "pwm", "adc", "imu", "mpu6050", "gps", "gsm", "servo", "actuator",
    "interrupt", "sensor driver",
    "linux", "bash", "cmake", "makefile", "git", "vs code",
    "pid", "real-time", "board bring-up", "hardware-software", "serial debug",
    "pcb", "kicad", "schematic", "layout", "prototyping",
]

CORE_DOMAIN_TERMS = ["embedded", "firmware", "esp32", "stm32", "c++", "c/c++", "iot"]


def calculate_domain_score(text):
    """Keyword-overlap score against the resume skill list. This measures
    DOMAIN relevance only (is this an embedded/firmware-ish job at all) —
    it is NOT a seniority judgment. Seniority is handled separately by
    experience_filter.classify_experience()."""
    if not text:
        return 0
    text_lower = text.lower()
    matched = sum(
        1 for kw in RESUME_KEYWORDS
        if re.search(r"\b" + re.escape(kw) + r"\b", text_lower)
    )
    # Slightly gentler denominator than before (was /4.0, maxed out too easily)
    score = min(100, int((matched / 6.0) * 100))
    return score


def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            title TEXT NOT NULL,
            company TEXT NOT NULL,
            location TEXT,
            link TEXT UNIQUE NOT NULL,
            score INTEGER DEFAULT 0,
            experience_verdict TEXT DEFAULT 'UNKNOWN',
            experience_reason TEXT DEFAULT '',
            min_years INTEGER,
            max_years INTEGER,
            status TEXT DEFAULT 'NEW',
            date_found TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def save_jobs(job_list, source_name, min_domain_score=50, allow_stretch=True):
    """
    Saves jobs that are BOTH domain-relevant AND experience-appropriate.

    job dicts should include (when available):
      title, company, location, link, description (full JD text),
      seniority_label (LinkedIn's own tag, if scraped)

    Returns (added_count, rejected_senior_count, rejected_domain_count)
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    added_count = 0
    rejected_senior = 0
    rejected_domain = 0

    for job in job_list:
        title = job.get("title", "")
        company = job.get("company", "")
        description = job.get("description", "") or f"{title} {company}"
        seniority_label = job.get("seniority_label")

        combined_text = f"{title} {company} {description}"
        domain_score = calculate_domain_score(combined_text)
        if any(term in combined_text.lower() for term in CORE_DOMAIN_TERMS):
            domain_score = max(domain_score, 70)

        if domain_score < min_domain_score:
            rejected_domain += 1
            continue

        exp = classify_experience(description, seniority_label, title)

        if exp["verdict"] == "REJECT":
            rejected_senior += 1
            continue
        if exp["verdict"] == "STRETCH" and not allow_stretch:
            rejected_senior += 1
            continue

        try:
            cursor.execute("""
                INSERT INTO jobs
                (source, title, company, location, link, score,
                 experience_verdict, experience_reason, min_years, max_years)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                source_name, title, company, job.get("location", "N/A"),
                job.get("link", "N/A"), domain_score,
                exp["verdict"], exp["reason"], exp["min_years"], exp["max_years"],
            ))
            added_count += 1
        except sqlite3.IntegrityError:
            pass  # duplicate link, already have it

    conn.commit()
    conn.close()
    return added_count, rejected_senior, rejected_domain


def get_all_jobs(status_filter=None, verdict_filter=None):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    query = """SELECT id, source, title, company, location, link, score,
                      experience_verdict, experience_reason, status
               FROM jobs WHERE 1=1"""
    params = []
    if status_filter and status_filter != "ALL":
        query += " AND status = ?"
        params.append(status_filter)
    if verdict_filter and verdict_filter != "ALL":
        query += " AND experience_verdict = ?"
        params.append(verdict_filter)
    query += " ORDER BY score DESC, id DESC"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return rows


def update_job_status(job_id, new_status):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE jobs SET status = ? WHERE id = ?", (new_status, job_id))
    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    print("[+] Database module loaded and initialized.")