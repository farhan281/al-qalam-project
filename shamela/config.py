# shamela/config.py
# ─────────────────────────────────────────────
# Central place for all settings and the shared
# HTTP session. Every other module imports from
# here so changing a setting takes one edit.

import requests

# ── URLs & paths ──────────────────────────────
BASE_URL   = "https://shamela.ws"
OUTPUT_DIR = "shamela_output"
PROGRESS   = f"{OUTPUT_DIR}/progress.json"
REPORT     = f"{OUTPUT_DIR}/report.csv"

# ── Scraping behaviour ────────────────────────
DELAY      = 1.5   # seconds to wait between books (keeps us polite to the server)
RETRIES    = 5     # how many times to retry a failed request
TIMEOUT    = 35    # seconds before a request is considered timed out
PAGE_DELAY = 0.3   # seconds to wait between individual page fetches inside a book

# ── Shared HTTP session ───────────────────────
# One session is reused for the whole run.
# This shares cookies, keeps connections alive, and sets headers once.
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (compatible; shamela-scraper/2.0)",  # look like a browser
    "Accept-Language": "ar,en;q=0.9",                               # request Arabic content
})
