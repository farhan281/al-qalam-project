"""
================================================================================
Shamela.ws Full Scraper  —  shamela_scraper.py
================================================================================

WHAT THIS DOES:
  - Fetches all categories from shamela.ws (e.g. العقيدة, الفقه, الحديث)
  - For each category, scrapes every book page by page via AJAX API
  - Saves each book as a .txt file inside a category subfolder
  - Resumes from the last saved page if interrupted (Ctrl+C or timeout)
  - Tracks progress in progress.json so nothing is lost
  - Generates a full CSV report (report.csv) after every book

OUTPUT STRUCTURE:
  shamela_output/
  ├── progress.json         <- tracks status, page count, metadata per book
  ├── report.csv            <- summary of all books scraped so far
  ├── العقيدة/
  │   ├── الفقه_الأكبر.txt
  │   └── كتاب_الأصنام.txt
  └── ...

HOW TO RUN:
  source shamela_env/bin/activate
  python shamela_scraper.py

DEPENDENCIES:
  pip install requests beautifulsoup4 tqdm
"""

import requests, os, re, time, json, csv
from bs4 import BeautifulSoup
from tqdm import tqdm

# ── Settings ───────────────────────────────────────────────────────────────────

BASE_URL   = "https://shamela.ws"                        # website root URL
OUTPUT_DIR = "shamela_output"                            # all output goes here
DELAY      = 1.5                                         # seconds to wait between books (be polite to the server)
PROGRESS   = os.path.join(OUTPUT_DIR, "progress.json")  # resume/status file
REPORT     = os.path.join(OUTPUT_DIR, "report.csv")     # CSV summary file

# Reuse one HTTP session across all requests — faster and shares cookies/headers
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (compatible; shamela-scraper/2.0)",  # look like a browser
    "Accept-Language": "ar,en;q=0.9",                               # prefer Arabic content
})

# ── Helpers ────────────────────────────────────────────────────────────────────

def ar2int(s):
    """
    Convert Arabic-Indic digits to a regular integer.
    Shamela stores page counts in Arabic numerals e.g. '١٦٧' -> 167.
    Used to compare pages_scraped vs total_pages correctly.
    """
    try:
        return int(str(s).translate(str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")))
    except Exception:
        return 0

def safe_name(s):
    """
    Make a string safe to use as a file/folder name.
    Removes special characters, replaces spaces with underscores, caps at 100 chars.
    Example: 'الفقه الأكبر' -> 'الفقه_الأكبر'
    """
    s = re.sub(r'[\\/*?"<>|]', "", s).strip().replace(" ", "_")
    return s[:100]

def fetch(url, retries=5, timeout=35):
    """
    GET a URL with automatic retry on failure.
    Waits longer after each failed attempt: 5s, 10s, 15s, 20s, 25s.
    Returns the Response object, or None if all retries fail.
    Uses tqdm.write so retry messages don't break the progress bars.
    """
    for i in range(retries):
        try:
            r = session.get(url, timeout=timeout)
            r.encoding = "utf-8"
            return r
        except Exception as e:
            wait = 5 * (i + 1)
            tqdm.write(f"  [RETRY {i+1}/{retries}] {e} — wait {wait}s")
            time.sleep(wait)
    return None

def soup(url):
    """Fetch a URL and return a BeautifulSoup object for HTML parsing."""
    r = fetch(url)
    return BeautifulSoup(r.text, "html.parser") if r else None

def load_progress():
    """
    Load the saved progress from progress.json.
    Returns an empty dict if this is the first run.
    Structure: { "cat_id_book_id": { title, pages, status, author, ... } }
    """
    if os.path.exists(PROGRESS):
        with open(PROGRESS, encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_progress(done):
    """
    Write the current progress dict to progress.json.
    Called after every book so a crash never loses more than one book's work.
    """
    with open(PROGRESS, "w", encoding="utf-8") as f:
        json.dump(done, f, ensure_ascii=False, indent=2)

# ── Metadata ───────────────────────────────────────────────────────────────────

def fetch_meta(book_soup):
    """
    Extract book metadata from a parsed book page.

    Shamela shows a 'betaka' (book card) above the table of contents with:
      المؤلف        -> author
      الناشر        -> publisher
      الطبعة        -> edition
      عدد الصفحات  -> total pages (in Arabic numerals)

    The table of contents links inside .betaka-index give us topics.
    The breadcrumb trail gives us the category name.

    Returns a dict with keys: author, publisher, edition, total_pages, topics, category
    """
    meta = {k: "" for k in ("author", "publisher", "edition", "total_pages", "topics", "category")}

    bi = book_soup.select_one(".betaka-index")
    if bi:
        # Book info sits in the siblings just before .betaka-index in the DOM
        for sib in bi.previous_siblings:
            t = sib.get_text(strip=True) if hasattr(sib, "get_text") else str(sib).strip()
            if   t.startswith("المؤلف:"):       meta["author"]      = t[len("المؤلف:"):].strip()
            elif t.startswith("الناشر:"):       meta["publisher"]   = t[len("الناشر:"):].strip()
            elif t.startswith("الطبعة:"):       meta["edition"]     = t[len("الطبعة:"):].strip()
            elif t.startswith("عدد الصفحات:"): meta["total_pages"] = t[len("عدد الصفحات:"):].strip()

        # All <a> tags inside .betaka-index are the chapter/topic headings
        meta["topics"] = " | ".join(a.get_text(strip=True) for a in bi.select("a"))

    # Breadcrumb: الرئيسية > أقسام الكتب > العقيدة  -> last item is the category
    bc = book_soup.select(".breadcrumb li")
    if len(bc) >= 3:
        meta["category"] = bc[-1].get_text(strip=True)

    return meta

# ── Discovery ──────────────────────────────────────────────────────────────────

def get_categories():
    """
    Scrape all categories from the homepage.
    They live inside #cats as <a class="cat_title"> links.
    Strips the badge count and any leading number from the name.
    Returns a list of { id, name } dicts.
    """
    tqdm.write("📚 Fetching categories...")
    s = soup(BASE_URL)
    if not s:
        return []

    cats = []
    for a in s.select("#cats a.cat_title"):
        href  = a.get("href", "")
        name  = a.get_text(strip=True)

        # Remove the badge number (e.g. "42") appended inside the link text
        badge = a.select_one(".badge")
        if badge:
            name = name.replace(badge.get_text(), "").strip()

        # Remove leading "1. " style numbering
        name = re.sub(r"^\d+\.\s*", "", name).strip()

        # Category ID is the last segment of the href: /category/1 -> "1"
        cat_id = href.rstrip("/").split("/")[-1]
        if cat_id.isdigit():
            cats.append({"id": cat_id, "name": name})

    tqdm.write(f"  ✅ {len(cats)} categories found\n")
    return cats

def get_books(cat_id):
    """
    Fetch all books listed on a category page.
    Each book is an <a class="book_title"> link.
    Returns a list of { id, title } dicts.
    """
    s = soup(f"{BASE_URL}/category/{cat_id}")
    if not s:
        return []

    books = []
    for a in s.select("a.book_title"):
        href  = a.get("href", "")
        title = a.get_text(strip=True)
        bid   = href.rstrip("/").split("/")[-1]  # /book/6388 -> "6388"
        if bid.isdigit():
            books.append({"id": bid, "title": title})
    return books

# ── Scraper ────────────────────────────────────────────────────────────────────

def scrape_book(book_id, book_title, resume_page_id=None, existing_text="", existing_pages=0, known_total=0):
    """
    Download the full text of one book via Shamela's AJAX page API.

    HOW THE API WORKS:
      GET /ajax/pageContent/{book_id}/{page_id}
      Response JSON:
        {
          "nass":    "<html> page text </html>",
          "title":   "chapter name",
          "pageNum": "١٤",
          "nextId":  "10002"   <- ID of next page; null on last page
        }
      Pages form a linked list: each page points to the next one.
      We follow nextId until it is null -> book is complete.

    RESUME MODE:
      If resume_page_id is given, we skip fetching the book page and jump
      straight to that page ID. existing_text and existing_pages carry
      what was already saved from the previous run.

    Args:
      book_id        : Shamela numeric book ID
      book_title     : Used for display only
      resume_page_id : Page ID to restart from (None = fresh start)
      existing_text  : Already scraped content (prepended when resuming)
      existing_pages : Already scraped page count (sets progress bar start)
      known_total    : Total pages for the progress bar max value

    Returns:
      (text, page_count, complete, next_page_id, meta)
      - text          : Full text of the book (existing + newly scraped)
      - page_count    : Total pages scraped in this run + previous
      - complete      : True if we reached the last page (nextId was null)
      - next_page_id  : Where we stopped (saved for resume if partial)
      - meta          : Metadata dict (empty when in resume mode)
    """
    meta       = {}
    all_text   = []
    page_count = existing_pages

    if resume_page_id:
        # Jump straight to the checkpoint page, carry forward saved text
        page_id = resume_page_id
        if existing_text:
            all_text = [existing_text]
        tqdm.write(f"    ↩  Resuming {book_title[:50]} — page_id {page_id} ({existing_pages} pages done)")
    else:
        # Fresh start: load the book page to get metadata and first page ID
        s = soup(f"{BASE_URL}/book/{book_id}")
        if not s:
            return None

        meta        = fetch_meta(s)
        known_total = ar2int(meta.get("total_pages", "0"))

        # First link in the table of contents = first page of the book
        link = s.select_one("div.betaka-index a[href]")
        if link:
            m       = re.search(r"/book/\d+/(\d+)", link.get("href", ""))
            page_id = int(m.group(1)) if m else 1
        else:
            page_id = 1  # fallback if no TOC found

    # Progress bar for this book's pages
    # total=known_total shows percentage; initial=existing_pages starts from where we left off
    pbar = tqdm(
        total=known_total or None,
        initial=existing_pages,
        unit="pg",
        dynamic_ncols=True,
        leave=False,  # hide bar after book finishes
        bar_format="    {desc:<35} {bar} {n}/{total} [{elapsed}<{remaining} {rate_fmt}]",
    )

    complete = False
    try:
        while page_id is not None:
            r = fetch(f"{BASE_URL}/ajax/pageContent/{book_id}/{page_id}")
            if not r:
                # All retries failed — save what we have and resume later
                tqdm.write(f"    [ERROR] page {page_id}: giving up after retries")
                break

            try:
                data = r.json()
            except Exception as e:
                tqdm.write(f"    [ERROR] page {page_id}: bad JSON — {e}")
                break

            nass = data.get("nass", "")
            if nass:
                sp = BeautifulSoup(nass, "html.parser")

                # Remove copy buttons (UI elements, not content)
                for a in sp.find_all("a", class_="btn_tag"):
                    a.decompose()

                text       = sp.get_text("\n", strip=True)
                page_num   = data.get("pageNum", "")
                page_title = data.get("title", "")

                if page_title:
                    # Insert a chapter heading separator line
                    all_text.append(f"\n--- ص{page_num}: {page_title} ---\n")
                    # Show current chapter name live in the progress bar
                    pbar.set_description(f"ص{page_num}: {page_title[:28]}")

                all_text.append(text)

            page_count += 1
            pbar.update(1)

            # Follow the linked list to the next page
            next_id = data.get("nextId")
            page_id = int(next_id) if next_id else None

            time.sleep(0.3)  # small delay between pages to avoid hammering the server

        # If page_id is None we naturally reached the end -> book is complete
        complete = (page_id is None)

    finally:
        pbar.close()

    return "\n".join(all_text), page_count, complete, page_id, meta

# ── Report ─────────────────────────────────────────────────────────────────────

def generate_report(done):
    """
    Walk all .txt files in the output folder and write report.csv.

    For each file:
      - Reads the header line to get the URL and book_id
      - Counts '--- ص' patterns to get pages_scraped
      - Looks up the rest of the metadata from progress.json (done dict)

    UTF-8-sig encoding ensures Arabic text displays correctly in Excel.
    """
    by_id = {k.split("_")[1]: v for k, v in done.items()}  # book_id -> entry lookup
    rows  = []

    for cat in sorted(os.listdir(OUTPUT_DIR)):
        cat_path = os.path.join(OUTPUT_DIR, cat)
        if not os.path.isdir(cat_path):
            continue  # skip progress.json and report.csv

        for fname in sorted(os.listdir(cat_path)):
            if not fname.endswith(".txt"):
                continue

            fpath = os.path.join(cat_path, fname)

            # Extract URL and book_id from the file header
            url, book_id = "", ""
            with open(fpath, encoding="utf-8") as f:
                for line in f:
                    if line.startswith("الرابط:"):
                        url     = line.split("الرابط:")[-1].strip()
                        book_id = url.rstrip("/").split("/")[-1]
                        break

            # Count scraped pages by counting chapter separator lines
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

# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    """
    Entry point — orchestrates the full scraping run.

    Flow:
      1. Create output folder
      2. Load previous progress (so already-done books are skipped)
      3. Fetch all categories from the homepage
      4. For each category:
         a. Fetch its book list
         b. Split books into pending vs already complete
         c. Scrape each pending book (with resume if it was partial before)
         d. Save progress.json and regenerate report.csv after each book
      5. Final report after all categories are done
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    done       = load_progress()
    categories = get_categories()

    # Outer bar — tracks how many categories have been processed
    overall = tqdm(
        categories, unit="cat", dynamic_ncols=True,
        bar_format="📁 {desc:<25} {bar} {n}/{total} categories [{elapsed}<{remaining}]"
    )

    for cat in overall:
        cat_id, cat_name = cat["id"], cat["name"]
        overall.set_description(cat_name[:25])

        cat_folder = os.path.join(OUTPUT_DIR, safe_name(cat_name))
        os.makedirs(cat_folder, exist_ok=True)

        books = get_books(cat_id)
        time.sleep(DELAY)

        # Separate books into: already complete (skip) vs needs scraping (pending)
        pending, skipped = [], 0
        for b in books:
            e     = done.get(f"{cat_id}_{b['id']}", {})
            total = ar2int(e.get("total_pages", "0"))
            sc    = e.get("pages", 0)
            # Only skip if status=complete AND pages scraped actually match total
            if e.get("status") == "complete" and (total == 0 or sc >= total):
                skipped += 1
            else:
                pending.append(b)

        tqdm.write(f"\n📁 {cat_name}  —  {len(books)} books  ({skipped} ✅ done, {len(pending)} to scrape)")

        # Middle bar — tracks books within this category
        book_bar = tqdm(
            pending, unit="book", dynamic_ncols=True, leave=True,
            bar_format="  📚 {desc:<40} {bar} {n}/{total} books [{elapsed}<{remaining}]"
        )

        for book in book_bar:
            book_id, book_title = book["id"], book["title"]
            done_key = f"{cat_id}_{book_id}"
            entry    = done.get(done_key, {})
            txt_file = os.path.join(cat_folder, safe_name(book_title) + ".txt")

            book_bar.set_description(book_title[:40])

            # Check if this book was partially scraped in a previous run
            resume_page_id = None
            existing_text  = ""
            existing_pages = 0
            known_total    = ar2int(entry.get("total_pages", "0"))

            if entry.get("status") == "partial":
                resume_page_id = entry.get("next_page_id")   # page where we stopped
                existing_pages = entry.get("pages", 0)
                if resume_page_id and os.path.exists(txt_file):
                    # Load the already-saved text so we can append to it
                    with open(txt_file, encoding="utf-8") as f:
                        existing_text = f.read().rstrip()
                else:
                    resume_page_id = None  # no valid checkpoint, restart fresh

            result = scrape_book(book_id, book_title, resume_page_id, existing_text, existing_pages, known_total)

            if not result:
                tqdm.write(f"    ❌ Failed: {book_title[:55]}")
                time.sleep(DELAY)
                continue

            text, pages, complete, next_page_id, meta = result

            # Write the .txt file
            # Resume mode: text already contains existing_text, write as-is
            # Fresh mode: prepend the book header (title + URL + separator)
            header = f"الكتاب: {book_title}\nالرابط: {BASE_URL}/book/{book_id}\n{'='*60}\n\n"
            with open(txt_file, "w", encoding="utf-8") as f:
                f.write(text if (resume_page_id and existing_text) else header + text)

            status_icon = "✅" if complete else "⚠️ partial"
            tqdm.write(f"    {status_icon}  {book_title[:55]}  ({pages} pages)")

            # Build the progress.json entry for this book
            new_entry = {
                "title":  book_title,
                "pages":  pages,
                "status": "complete" if complete else "partial",
                **meta,  # spreads in author, publisher, edition, total_pages, topics, category
            }
            if not complete:
                # Save the page ID where we stopped so next run can resume from here
                new_entry["next_page_id"] = next_page_id

            if resume_page_id:
                # In resume mode meta is empty — keep the metadata from the previous entry
                for k in ("author", "publisher", "edition", "total_pages", "topics", "category"):
                    if not new_entry.get(k):
                        new_entry[k] = entry.get(k, "")

            done[done_key] = new_entry
            save_progress(done)
            generate_report(done)
            time.sleep(DELAY)

        book_bar.close()

    generate_report(done)
    tqdm.write(f"\n🎉 Done! Output in: {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
