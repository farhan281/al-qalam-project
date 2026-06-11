# Shamela Scraper

A Python scraper for **shamela.ws** (Al-Maktaba Al-Shamela) — the world's largest
Arabic Islamic digital library with 10,000+ books across Quran tafseer, Hadith,
Fiqh, Aqeedah and more.

---

## Project Structure

```
shamela_project/
│
├── run.py                   ← Entry point — run this to start scraping
│
├── shamela/                 ← Main package (one file per responsibility)
│   ├── __init__.py          ← Exposes main()
│   ├── config.py            ← All settings + shared HTTP session
│   ├── helpers.py           ← Utilities: fetch, retry, progress load/save
│   ├── metadata.py          ← Extracts author, publisher, topics from book page
│   ├── discovery.py         ← Fetches category list and book list
│   ├── scraper.py           ← Core AJAX page-by-page download loop
│   ├── report.py            ← Generates report.csv
│   ├── git_sync.py          ← Auto-commits and pushes to GitHub after every book
│   └── main.py              ← Orchestrates the full run with tqdm bars
│
├── shamela_env/             ← Python virtual environment
│
└── shamela_output/          ← Created automatically on first run
    ├── progress.json        ← Per-book status, page count, metadata
    ├── report.csv           ← Master CSV summary of ALL books
    ├── العقيدة/
    │   ├── report.csv       ← CSV for this category only
    │   ├── الفقه_الأكبر.txt
    │   └── كتاب_الأصنام.txt
    ├── الفقه/
    │   ├── report.csv
    │   └── ...
    └── ...
```

---

## How It Works

### 1 — Category Discovery (`discovery.py`)
Parses the homepage `#cats` section to get every category name and ID.

```
shamela.ws  →  العقيدة (ID 1), الفقه (ID 2), الحديث (ID 3) ...
```

### 2 — Book Discovery (`discovery.py`)
For each category, fetches `/category/{id}` and collects all book links.

### 3 — Metadata Extraction (`metadata.py`)
Visits each book's landing page `/book/{id}` and reads the "betaka" card:

```
المؤلف        → author
الناشر        → publisher
الطبعة        → edition
عدد الصفحات  → total_pages
.betaka-index → topics (table of contents)
breadcrumb    → category name
```

### 4 — AJAX Page Download (`scraper.py`)
Shamela serves text through an AJAX endpoint. Pages form a **linked list** —
each page's JSON contains the ID of the next page.

```
GET /ajax/pageContent/{book_id}/{page_id}

Response:
{
  "nass":    "<p>page HTML</p>",
  "title":   "chapter name",
  "pageNum": "١٤",
  "nextId":  "10002"    ← null on the last page
}

10001 → 10002 → 10003 → ... → null  (book complete)
```

### 5 — Saved Output (`report.py`)
Each book is saved as a plain UTF-8 `.txt` file:

```
الكتاب: الفقه الأكبر
الرابط: https://shamela.ws/book/6388
============================================================

--- ص14: وحدانية الله تعالى ---
وَالله تَعَالَى وَاحِد ...
```

---

## Resume Feature

If the connection drops or you press Ctrl+C, **no work is lost**.

When a book is interrupted, `progress.json` stores:

```json
"1_6388": {
  "title": "الفقه الأكبر",
  "status": "partial",
  "pages": 45,
  "next_page_id": 10046,
  "author": "أبو حنيفة",
  "total_pages": "١٦٧"
}
```

On the next run:
1. `progress.json` is loaded
2. Books with `status: partial` resume from `next_page_id`
3. The existing `.txt` file is loaded and new pages are appended
4. On completion `status` becomes `complete` and `next_page_id` is removed

A book is only skipped when **both** conditions are true:
```
status == "complete"  AND  pages_scraped >= total_pages
```

---

## Retry Logic

Every HTTP request retries up to 5 times with increasing wait:

```
fail → wait 5s → retry
fail → wait 10s → retry
fail → wait 15s → retry
fail → wait 20s → retry
fail → wait 25s → save partial, move on
```

---

## Terminal Output

Three nested tqdm bars run simultaneously:

```
📚 Fetching categories...
  ✅ 42 categories found

📁 العقيدة  —  38 books  (2 ✅ done, 36 to scrape)

📁 العقيدة           ██░░░░░░░░  1/42 categories [00:05<03:20]
  📚 الفقه الأكبر    ████░░░░░░  3/36 books      [01:10<09:40]
    ص27: القول في الصفات ████████░░ 92/167 [00:45<01:20 1.2pg/s]

    ✅  الفقه الأكبر  (167 pages)
    ⚠️  كتاب الأصنام  (45 pages)   ← partial (timed out)
    ❌  Failed: ...
```

| Bar | Tracks |
|-----|--------|
| Outer | Categories processed out of total |
| Middle | Books done within the current category |
| Inner | Pages downloaded for the current book (with live chapter title) |

---

## Output Files

### `shamela_output/<category>/<book>.txt`
Plain text, UTF-8, one file per book.

### `shamela_output/report.csv`
Master report — every book from every category in one file.

### `shamela_output/<category>/report.csv`
Per-category report — only the books inside that folder.
Updated automatically after every book in that category.

### `shamela_output/progress.json`
```json
{
  "1_6388": {
    "title": "الفقه الأكبر",
    "pages": 167,
    "status": "complete",
    "author": "أبو حنيفة النعمان (ت ١٥٠هـ)",
    "publisher": "مكتبة الفرقان",
    "edition": "الأولى، ١٤١٩هـ",
    "total_pages": "١٦٧",
    "topics": "بيان أصول الإيمان | وحدانية الله تعالى | ...",
    "category": "العقيدة"
  }
}
```

### `shamela_output/report.csv`

| Column | Description |
|--------|-------------|
| category | Category folder name |
| book | Book title |
| book_id | Shamela numeric ID |
| author | Author name with death year |
| publisher | Publisher name |
| edition | Edition and year |
| total_pages | Total printed pages (Arabic numerals) |
| pages_scraped | Pages actually downloaded |
| status | `complete` or `partial` |
| topics | Chapter headings, pipe-separated |
| url | Shamela book URL |
| file | Local .txt file path |

---

## GitHub Auto-Sync (`git_sync.py`)

After every book completes, the scraper automatically:
1. `git add --all shamela_output/` — stages the new `.txt`, updated `progress.json` and `report.csv`, and any new category folder
2. `git commit -m "scraped: <book title>"`
3. `git push origin master`

Each commit in the GitHub history represents one fully scraped book.
If a book fails or nothing changed, the push is skipped silently — no empty commits.

What each commit contains:
```
shamela_output/العقيدة/الفقه_الأكبر.txt   ← new book text
shamela_output/progress.json               ← updated status
shamela_output/report.csv                  ← updated summary
```

When the repo gets too large, create a new repo and update `origin`:
```bash
git remote set-url origin https://github.com/<user>/<new-repo>.git
git push origin master
```

---

## How to Run

```bash
cd /home/ubuntu/shamela_project
source shamela_env/bin/activate
python run.py
```

Interrupted? Just run again — it resumes automatically.

### Install dependencies
```bash
pip install requests beautifulsoup4 tqdm
```

---

## Settings (`shamela/config.py`)

| Variable | Default | Purpose |
|----------|---------|---------|
| `BASE_URL` | `https://shamela.ws` | Website root |
| `OUTPUT_DIR` | `shamela_output` | Where files are saved |
| `DELAY` | `1.5s` | Wait between books |
| `RETRIES` | `5` | Max retries per request |
| `TIMEOUT` | `35s` | Request timeout |
| `PAGE_DELAY` | `0.3s` | Wait between pages inside a book |

---

## Common Issues

| Error | Cause | Fix |
|-------|-------|-----|
| `ModuleNotFoundError: tqdm` | Not installed in venv | `pip install tqdm` |
| `Read timed out` | Server is slow | Auto-retries handle it |
| `pages_scraped < total_pages` | Previous timeout | Set `status: partial` in progress.json, re-run |
| Arabic text garbled | Wrong encoding | Open the file as UTF-8 |
