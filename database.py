import sqlite3
import re
from experience_filter import classify_experience

DB_NAME = "jobs.db"

# Resume Skills Baseline for Keyword Matching — embedded/hardware track
RESUME_KEYWORDS = [
    "esp32", "esp-idf", "stm32", "stm32cubeide", "microcontroller", "mcu", "firmware", "embedded",
    "embedded c", "c++", "cpp", "c/c++", "python",
    "uart", "spi", "i2c", "pwm", "adc", "imu", "mpu6050", "gps", "gsm", "servo", "actuator",
    "interrupt", "sensor driver",
    "linux", "bash", "cmake", "makefile", "git", "vs code",
    "pid", "real-time", "board bring-up", "hardware-software", "serial debug",
    "pcb", "kicad", "schematic", "layout", "prototyping",
]

# Python/automation track — separate list since these roles won't mention
# embedded-specific terms at all, and shouldn't be penalized for that.
AUTOMATION_KEYWORDS = [
    "python", "automation", "playwright", "selenium", "pytest", "test automation",
    "qa automation", "sqlite", "sql", "streamlit", "api", "rest api", "scripting",
    "web scraping", "etl", "pipeline", "ci/cd", "git", "linux", "bash", "cron",
    "scheduler", "data pipeline", "flask", "django", "pandas",
]

CORE_DOMAIN_TERMS = ["embedded", "firmware", "esp32", "stm32", "c++", "c/c++", "iot"]
CORE_AUTOMATION_TERMS = ["automation", "python developer", "test automation", "qa automation", "sdet"]


def calculate_domain_score(text, track="embedded"):
    """Keyword-overlap score against the relevant skill list for the given
    track. This measures DOMAIN relevance only (is this an embedded/firmware
    job, or a python/automation job) — it is NOT a seniority judgment.
    Seniority is handled separately by experience_filter.classify_experience()."""
    if not text:
        return 0
    text_lower = text.lower()
    keyword_list = AUTOMATION_KEYWORDS if track == "automation" else RESUME_KEYWORDS
    matched = sum(
        1 for kw in keyword_list
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
            status TEXT DEFAULT 'NEW',
            date_found TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()

    # --- Auto-migration: add any columns this version needs that an older
    # jobs.db (from before this update) won't have yet. CREATE TABLE IF NOT
    # EXISTS only fires on a brand-new file — it does nothing to a table that
    # already exists, which is exactly what broke on your run. This makes
    # future schema changes safe too, not just this one. ---
    required_columns = {
        "score": "INTEGER DEFAULT 0",
        "experience_verdict": "TEXT DEFAULT 'UNKNOWN'",
        "experience_reason": "TEXT DEFAULT ''",
        "min_years": "INTEGER",
        "max_years": "INTEGER",
    }
    cursor.execute("PRAGMA table_info(jobs)")
    existing_columns = {row[1] for row in cursor.fetchall()}
    for col_name, col_def in required_columns.items():
        if col_name not in existing_columns:
            print(f"[migrate] Adding missing column '{col_name}' to jobs table...")
            cursor.execute(f"ALTER TABLE jobs ADD COLUMN {col_name} {col_def}")
    conn.commit()
    conn.close()


def save_jobs(job_list, source_name, min_domain_score=50, allow_stretch=False, track="embedded"):
    """
    Saves jobs that are BOTH domain-relevant AND experience-appropriate.

    job dicts should include (when available):
      title, company, location, link, description (full JD text),
      seniority_label (LinkedIn's own tag, if scraped)

    track: "embedded" or "automation" — picks which keyword list domain
    scoring uses. A Python/automation job shouldn't be penalized for not
    mentioning ESP32.

    Returns (added_count, rejected_senior_count, rejected_unverified_count, rejected_domain_count)
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    added_count = 0
    rejected_senior = 0       # confirmed 2+ yrs or senior-worded title
    rejected_unverified = 0   # no clear signal either way, blocked by strict mode
    rejected_domain = 0
    core_terms = CORE_AUTOMATION_TERMS if track == "automation" else CORE_DOMAIN_TERMS

    for job in job_list:
        title = job.get("title", "")
        company = job.get("company", "")
        description = job.get("description", "") or f"{title} {company}"
        seniority_label = job.get("seniority_label")

        combined_text = f"{title} {company} {description}"
        domain_score = calculate_domain_score(combined_text, track=track)
        if any(term in combined_text.lower() for term in core_terms):
            domain_score = max(domain_score, 70)

        if domain_score < min_domain_score:
            rejected_domain += 1
            continue

        exp = classify_experience(description, seniority_label, title)

        if exp["verdict"] == "REJECT":
            rejected_senior += 1
            continue
        if exp["verdict"] == "STRETCH" and not allow_stretch:
            rejected_unverified += 1
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
    return added_count, rejected_senior, rejected_unverified, rejected_domain


def get_all_jobs(status_filter=None, verdict_filter=None, search_text=None, sort_by="score"):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    query = """SELECT id, source, title, company, location, link, score,
                      experience_verdict, experience_reason, status,
                      min_years, max_years, date_found
               FROM jobs WHERE 1=1"""
    params = []

    if status_filter and status_filter == "ALL":
        # "ALL" means all *active* jobs — discarded ones are hidden unless
        # explicitly requested, so they don't clutter the main view forever.
        query += " AND status != 'DISCARDED'"
    elif status_filter and status_filter != "ALL_INCLUDING_DISCARDED":
        query += " AND status = ?"
        params.append(status_filter)

    if verdict_filter and verdict_filter != "ALL":
        query += " AND experience_verdict = ?"
        params.append(verdict_filter)

    if search_text:
        query += " AND (title LIKE ? OR company LIKE ?)"
        like = f"%{search_text}%"
        params.extend([like, like])

    sort_map = {
        "score": "score DESC, id DESC",
        "newest": "date_found DESC",
        "company": "company ASC",
    }
    query += f" ORDER BY {sort_map.get(sort_by, 'score DESC, id DESC')}"

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


def get_stats():
    """Summary counts for the dashboard header — total, by status, by
    experience verdict, and per-source breakdown so you can actually see
    whether a source is contributing anything or silently failing."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM jobs")
    total = cursor.fetchone()[0]

    cursor.execute("SELECT status, COUNT(*) FROM jobs GROUP BY status")
    by_status = dict(cursor.fetchall())

    cursor.execute("SELECT experience_verdict, COUNT(*) FROM jobs GROUP BY experience_verdict")
    by_verdict = dict(cursor.fetchall())

    cursor.execute("SELECT source, COUNT(*) FROM jobs GROUP BY source ORDER BY COUNT(*) DESC")
    by_source = cursor.fetchall()

    conn.close()
    return {
        "total": total,
        "by_status": by_status,
        "by_verdict": by_verdict,
        "by_source": by_source,
    }


if __name__ == "__main__":
    init_db()
    print("[+] Database module loaded and initialized.")