import sqlite3
import re

DB_NAME = "jobs.db"

# Resume Skills Baseline for Keyword Matching
RESUME_KEYWORDS = [
    # Microcontrollers & Frameworks
    "esp32", "esp-idf", "stm32", "stm32cubeide", "microcontroller", "mcu", "firmware", "embedded",
    # Languages
    "embedded c", "c++", "cpp", "c/c++", "python",
    # Protocols & Hardware Interfacing
    "uart", "spi", "i2c", "pwm", "adc", "imu", "mpu6050", "gps", "gsm", "servo", "actuator",
    "interrupt", "sensor driver",
    # Linux & Tooling
    "linux", "bash", "cmake", "makefile", "git", "vs code",
    # Debugging & Control
    "pid", "real-time", "board bring-up", "hardware-software", "serial debug",
    # Hardware & PCB
    "pcb", "kicad", "schematic", "layout", "prototyping"
]

def calculate_match_score(text):
    """Calculates match percentage based on skills in job title/text."""
    if not text:
        return 0
    
    text_lower = text.lower()
    matched = 0

    for kw in RESUME_KEYWORDS:
        if re.search(r'\b' + re.escape(kw) + r'\b', text_lower):
            matched += 1

    # Base score calculation
    score = min(100, int((matched / 4.0) * 100))
    return score

def init_db():
    """Initializes SQLite database with score column."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            title TEXT NOT NULL,
            company TEXT NOT NULL,
            location TEXT,
            experience TEXT DEFAULT 'N/A',
            link TEXT UNIQUE NOT NULL,
            score INTEGER DEFAULT 0,
            status TEXT DEFAULT 'NEW',
            date_found TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()

def save_jobs(job_list, source_name, min_score_threshold=75):
    """Saves jobs meeting or exceeding min_score_threshold (>= 75%)."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    added_count = 0
    filtered_out = 0

    for job in job_list:
        combined_text = f"{job.get('title', '')} {job.get('company', '')}"
        score = calculate_match_score(combined_text)
        
        # Boost score if primary embedded terms are directly in title/company
        if any(term in combined_text.lower() for term in ["embedded", "firmware", "esp32", "stm32", "c++", "c/c++"]):
            score = max(score, 80)

        if score >= min_score_threshold:
            try:
                cursor.execute("""
                    INSERT INTO jobs (source, title, company, location, experience, link, score)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    source_name,
                    job.get("title", "N/A"),
                    job.get("company", "N/A"),
                    job.get("location", "N/A"),
                    job.get("experience", "N/A"),
                    job.get("link", "N/A"),
                    score
                ))
                added_count += 1
            except sqlite3.IntegrityError:
                pass  # Skip existing duplicate links
        else:
            filtered_out += 1

    conn.commit()
    conn.close()
    return added_count, filtered_out

def get_all_jobs(status_filter=None):
    """Retrieves stored jobs ordered by highest match score."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    if status_filter and status_filter != "ALL":
        cursor.execute("SELECT id, source, title, company, location, link, score, status FROM jobs WHERE status = ? ORDER BY score DESC", (status_filter,))
    else:
        cursor.execute("SELECT id, source, title, company, location, link, score, status FROM jobs ORDER BY score DESC, id DESC")
        
    rows = cursor.fetchall()
    conn.close()
    return rows

def update_job_status(job_id, new_status):
    """Updates job status (e.g. APPLIED, SAVED, REJECTED)."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE jobs SET status = ? WHERE id = ?", (new_status, job_id))
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("[+] Database module loaded and initialized.")