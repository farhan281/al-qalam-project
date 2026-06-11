# shamela/helpers.py
# ─────────────────────────────────────────────
# Small utility functions used across all modules:
#   - Arabic numeral conversion
#   - Safe filename creation
#   - HTTP fetch with retry
#   - BeautifulSoup shortcut
#   - progress.json load / save

import os, re, time, json
from bs4 import BeautifulSoup
from tqdm import tqdm
from .config import session, PROGRESS, RETRIES, TIMEOUT


def ar2int(s):
    """
    Convert Arabic-Indic digit string to a Python int.
    Shamela stores page counts as Arabic numerals e.g. '١٦٧' -> 167.
    Returns 0 on any failure so callers never have to handle exceptions.
    """
    try:
        return int(str(s).translate(str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")))
    except Exception:
        return 0


def safe_name(s):
    """
    Sanitise a string for use as a file or folder name.
    - Strips characters the OS won't allow: \\ / * ? " < > |
    - Replaces spaces with underscores
    - Truncates to 100 characters to avoid path-too-long errors
    Example: 'الفقه الأكبر' -> 'الفقه_الأكبر'
    """
    s = re.sub(r'[\\/*?"<>|]', "", s).strip().replace(" ", "_")
    return s[:100]


def fetch(url):
    """
    GET a URL and return the Response, or None if every retry fails.

    Retry schedule (from config.RETRIES and config.TIMEOUT):
      attempt 1 fail -> wait 5s  -> retry
      attempt 2 fail -> wait 10s -> retry
      ...
      attempt N fail -> give up, return None

    Uses tqdm.write so messages don't clobber progress bars.
    """
    for i in range(RETRIES):
        try:
            r = session.get(url, timeout=TIMEOUT)
            r.encoding = "utf-8"
            return r
        except Exception as e:
            wait = 5 * (i + 1)
            tqdm.write(f"  [RETRY {i+1}/{RETRIES}] {e} — wait {wait}s")
            time.sleep(wait)
    return None


def get_soup(url):
    """Fetch a URL and return a BeautifulSoup object, or None on failure."""
    r = fetch(url)
    return BeautifulSoup(r.text, "html.parser") if r else None


def load_progress():
    """
    Read progress.json and return the saved state as a dict.
    Returns {} on first run (file does not exist yet).
    Keys look like "1_6388" (cat_id + _ + book_id).
    """
    if os.path.exists(PROGRESS):
        with open(PROGRESS, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_progress(done):
    """
    Write the current state dict to progress.json.
    Called after every book so a crash or Ctrl+C loses at most one book.
    """
    with open(PROGRESS, "w", encoding="utf-8") as f:
        json.dump(done, f, ensure_ascii=False, indent=2)
