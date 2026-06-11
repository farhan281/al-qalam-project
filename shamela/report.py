# shamela/report.py
# ─────────────────────────────────────────────
# Generates two levels of CSV reports:
#
#   1. shamela_output/report.csv
#      Master report — every book from every category in one file.
#
#   2. shamela_output/<category>/report.csv
#      Per-category report — only the books in that folder.
#      Written whenever a book in that category is saved.
#
# Both CSVs share the same columns and UTF-8-sig encoding
# so Excel opens Arabic text correctly.

import os, re, csv
from datetime import datetime
import pytz
from .config import OUTPUT_DIR, REPORT

INDIA_TZ = pytz.timezone("Asia/Kolkata")

FIELDS = ["category", "book", "book_id", "author", "publisher", "edition",
          "total_pages", "pages_scraped", "status", "scraped_at", "topics", "url", "file"]


def india_now():
    """Return current Indian Standard Time as a readable string (DD-MM-YYYY HH:MM:SS IST)."""
    return datetime.now(INDIA_TZ).strftime("%d-%m-%Y %H:%M:%S IST")


def _book_row(fpath, cat, by_id):
    """Build one CSV row from a single .txt file and the progress lookup."""
    url, book_id = "", ""
    with open(fpath, encoding="utf-8") as f:
        for line in f:
            if line.startswith("الرابط:"):
                url     = line.split("الرابط:")[-1].strip()
                book_id = url.rstrip("/").split("/")[-1]
                break

    # Count chapter separator lines as a proxy for pages scraped
    # Use the same `with` block to avoid opening the file twice
    with open(fpath, encoding="utf-8") as f:
        content = f.read()
    pages_scraped = len(re.findall(r"^--- ص", content, re.MULTILINE))

    e = by_id.get(book_id, {})
    return {
        "category":      cat,
        "book":          os.path.basename(fpath).replace(".txt", "").replace("_", " "),
        "book_id":       book_id,
        "author":        e.get("author", ""),
        "publisher":     e.get("publisher", ""),
        "edition":       e.get("edition", ""),
        "total_pages":   e.get("total_pages", ""),
        "pages_scraped": pages_scraped,
        "status":        e.get("status", "partial"),
        "scraped_at":    e.get("scraped_at", ""),  # saved at scrape time in Indian time
        "topics":        e.get("topics", ""),
        "url":           url,
        "file":          fpath,
    }


def _write_csv(path, rows):
    """Write rows to a CSV file with UTF-8-sig encoding."""
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def generate_report(done):
    """
    Regenerate both the master report and every per-category report.

    Master  → shamela_output/report.csv            (all books, all categories)
    Per-cat → shamela_output/<category>/report.csv (books in that category only)

    Called after every book so both CSVs stay in sync.
    """
    by_id      = {k.split("_")[1]: v for k, v in done.items()}
    all_rows   = []

    for cat in sorted(os.listdir(OUTPUT_DIR)):
        cat_path = os.path.join(OUTPUT_DIR, cat)
        # Resolve real path and confirm it stays inside OUTPUT_DIR (prevent path traversal)
        real_base = os.path.realpath(OUTPUT_DIR)
        real_cat  = os.path.realpath(cat_path)
        if not real_cat.startswith(real_base + os.sep):
            continue
        if not os.path.isdir(cat_path):
            continue  # skip top-level files like progress.json

        cat_rows = []
        for fname in sorted(os.listdir(cat_path)):
            # Skip the per-category report itself
            if not fname.endswith(".txt"):
                continue
            row = _book_row(os.path.join(cat_path, fname), cat, by_id)
            cat_rows.append(row)
            all_rows.append(row)

        # Write per-category CSV inside the category folder — named after the category
        if cat_rows:
            _write_csv(os.path.join(cat_path, f"{cat}.csv"), cat_rows)

    # Write master CSV at the top level
    _write_csv(REPORT, all_rows)
