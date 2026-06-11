# shamela/report.py
# ─────────────────────────────────────────────
# Generates report.csv from the output folder.
#
# Walks every .txt file on disk (ground truth for
# what was actually saved), counts pages, then
# merges in metadata from the progress dict.

import os, re, csv
from .config import OUTPUT_DIR, REPORT


def generate_report(done):
    """
    Write (or overwrite) report.csv summarising every scraped book.

    Data sources:
      .txt file header line  -> url, book_id
      .txt file content      -> pages_scraped  (count of '--- ص' separators)
      progress dict (done)   -> author, publisher, edition, total_pages,
                                topics, status

    The file is UTF-8-sig encoded so Excel opens Arabic text correctly
    without needing to manually set the encoding.

    Called after every book finishes so the CSV is always up to date.
    """
    # Build a quick lookup: book_id -> progress entry
    by_id = {k.split("_")[1]: v for k, v in done.items()}
    rows  = []

    for cat in sorted(os.listdir(OUTPUT_DIR)):
        cat_path = os.path.join(OUTPUT_DIR, cat)
        if not os.path.isdir(cat_path):
            continue  # skip progress.json and report.csv at the top level

        for fname in sorted(os.listdir(cat_path)):
            if not fname.endswith(".txt"):
                continue

            fpath = os.path.join(cat_path, fname)

            # Read just the header lines to get the URL (and from it, book_id)
            url, book_id = "", ""
            with open(fpath, encoding="utf-8") as f:
                for line in f:
                    if line.startswith("الرابط:"):
                        url     = line.split("الرابط:")[-1].strip()
                        book_id = url.rstrip("/").split("/")[-1]
                        break

            # Count '--- ص' separator lines as a proxy for pages scraped
            content       = open(fpath, encoding="utf-8").read()
            pages_scraped = len(re.findall(r"^--- ص", content, re.MULTILINE))

            e = by_id.get(book_id, {})
            rows.append({
                "category":      cat,
                "book":          fname.replace(".txt", "").replace("_", " "),
                "book_id":       book_id,
                "author":        e.get("author", ""),
                "publisher":     e.get("publisher", ""),
                "edition":       e.get("edition", ""),
                "total_pages":   e.get("total_pages", ""),
                "pages_scraped": pages_scraped,
                "status":        e.get("status", "partial"),
                "topics":        e.get("topics", ""),
                "url":           url,
                "file":          fpath,
            })

    fields = ["category", "book", "book_id", "author", "publisher", "edition",
              "total_pages", "pages_scraped", "status", "topics", "url", "file"]

    with open(REPORT, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
