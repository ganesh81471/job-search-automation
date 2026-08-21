"""
experience_filter.py
---------------------
Shared logic for deciding whether a job posting is genuinely a 0-2 yr fit.

Why this exists: LinkedIn's "Entry level" tag is unreliable — plenty of roles
tagged Entry level actually ask for 2-8 years once you read the JD. This
module reads the full job description text (not just the title) and makes an
honest call, the same way we did manually earlier: look for explicit
"X years of experience" patterns and LinkedIn's own "Seniority level"
criteria field, and only pass jobs that clearly fit 0-2 yrs.

Returns a dict: {"verdict": "FIT" | "STRETCH" | "REJECT", "reason": str,
                  "min_years": int|None, "max_years": int|None}
"""

import re

# Patterns like "2-5 years", "3+ years", "0-2 yrs", "minimum 3 years"
_RANGE_RE = re.compile(
    r"(\d{1,2})\s*(?:-|to|–)\s*(\d{1,2})\s*\+?\s*(?:years?|yrs?)",
    re.IGNORECASE,
)
_PLUS_RE = re.compile(r"(\d{1,2})\s*\+\s*(?:years?|yrs?)", re.IGNORECASE)
_MIN_RE = re.compile(
    r"(?:minimum|at least|min\.?)\s*(\d{1,2})\s*(?:years?|yrs?)",
    re.IGNORECASE,
)
_SINGLE_NEAR_EXP_RE = re.compile(
    r"(\d{1,2})\s*(?:years?|yrs?)\s*(?:of\s*)?experience", re.IGNORECASE
)

_FRESHER_WORDS = re.compile(
    r"\b(fresher|entry.?level|no experience required|recent graduate|"
    r"final.?year student|0\s*-\s*1\s*year|0\s*-\s*2\s*year)\b",
    re.IGNORECASE,
)

# If the TITLE itself says senior/staff/principal/lead/etc, that's a strong,
# always-available signal — it doesn't depend on the description scrape
# succeeding at all. This catches cases like "Sr. Embedded Firmware Engineer"
# even when LinkedIn's guest view returns a thin/truncated description with
# no explicit year number in it (which is common — full JDs are often
# behind a login wall for non-members).
_SENIOR_TITLE_WORDS = re.compile(
    r"\b(senior|sr\.?|staff|principal|principle|lead|director|architect|"
    r"head of|manager|advanced|expert)\b",
    re.IGNORECASE,
)

# LinkedIn's own criteria field, when we have it from the job detail page
_SENIOR_SENIORITY_LABELS = {"mid-senior level", "director", "executive", "associate"}
_JUNIOR_SENIORITY_LABELS = {"internship", "entry level"}


def _extract_year_bounds(text: str):
    """Return (min_years, max_years) found anywhere in the text, or (None, None)."""
    bounds = []
    for m in _RANGE_RE.finditer(text):
        lo, hi = int(m.group(1)), int(m.group(2))
        bounds.append((lo, hi))
    for m in _PLUS_RE.finditer(text):
        lo = int(m.group(1))
        bounds.append((lo, 99))
    for m in _MIN_RE.finditer(text):
        lo = int(m.group(1))
        bounds.append((lo, 99))
    for m in _SINGLE_NEAR_EXP_RE.finditer(text):
        # "3 years experience" with no range = treat as a floor
        lo = int(m.group(1))
        bounds.append((lo, lo))

    if not bounds:
        return None, None
    # Be conservative: take the toughest (highest) floor mentioned anywhere,
    # since a JD that says "0-2 yrs, but 3+ preferred for X" really wants 3+.
    min_years = min(b[0] for b in bounds)
    max_years = max(b[1] for b in bounds)
    return min_years, max_years


def classify_experience(description_text: str, seniority_label: str = None, title: str = ""):
    """
    description_text: full job description (the more complete, the better)
    seniority_label: LinkedIn's own "Seniority level" criteria text, if scraped
    title: job title, used only as a weak secondary signal
    """
    text = description_text or ""
    min_years, max_years = _extract_year_bounds(text)

    # 1) Explicit year requirement is the strongest signal — trust it first.
    # STRICT 0-1 yr mode: both floor AND ceiling must be within range. A
    # "0-2 years" posting used to pass because the floor (0) qualified —
    # now the ceiling (2) correctly rejects it, since you asked for
    # strictly 0-1, not "0 or more, up to whatever."
    if min_years is not None:
        if min_years <= 1 and max_years <= 1:
            max_display = f"{max_years}" if max_years < 99 else "+"
            range_display = f"{min_years}-{max_display}" if max_years < 99 else f"{min_years}+"
            return {
                "verdict": "FIT",
                "reason": f"JD states {range_display} yrs — within strict 0-1 yr range.",
                "min_years": min_years,
                "max_years": max_years,
            }
        else:
            max_display = f"{max_years}" if max_years < 99 else "+"
            range_display = f"{min_years}-{max_display}" if max_years < 99 else f"{min_years}+"
            return {
                "verdict": "REJECT",
                "reason": f"JD explicitly wants {range_display} yrs despite any 'entry-level' tag.",
                "min_years": min_years,
                "max_years": max_years,
            }

    # 2) TITLE says senior/staff/principal/lead — reject immediately, don't
    # wait on description quality. This is the fix for jobs like "Sr. Embedded
    # Firmware Engineer" slipping through as STRETCH when LinkedIn's guest
    # view returns a thin description with no year number in it.
    if _SENIOR_TITLE_WORDS.search(title or ""):
        matched_word = _SENIOR_TITLE_WORDS.search(title).group(0)
        return {
            "verdict": "REJECT",
            "reason": f"Title contains '{matched_word}' — treating as senior regardless of JD text quality.",
            "min_years": None,
            "max_years": None,
        }

    # 3) No explicit year number, no senior title — fall back to LinkedIn's own label.
    if seniority_label:
        label = seniority_label.strip().lower()
        if label in _JUNIOR_SENIORITY_LABELS:
            return {
                "verdict": "FIT",
                "reason": f"No year number in JD, but LinkedIn seniority tag is '{seniority_label}'.",
                "min_years": None,
                "max_years": None,
            }
        if label in _SENIOR_SENIORITY_LABELS:
            return {
                "verdict": "REJECT",
                "reason": f"LinkedIn seniority tag is '{seniority_label}' — not a fresher fit.",
                "min_years": None,
                "max_years": None,
            }

    # 4) Nothing explicit anywhere — weakest signal, use fresher-friendly wording.
    if _FRESHER_WORDS.search(text) or _FRESHER_WORDS.search(title):
        return {
            "verdict": "STRETCH",
            "reason": "No explicit year requirement found, but fresher-friendly wording present. Verify manually.",
            "min_years": None,
            "max_years": None,
        }

    return {
        "verdict": "STRETCH",
        "reason": "No experience signal found at all — unverified, include with caution.",
        "min_years": None,
        "max_years": None,
    }