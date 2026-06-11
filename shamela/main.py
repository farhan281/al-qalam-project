# shamela/main.py
# ─────────────────────────────────────────────
# Orchestrator — ties all modules together and
# runs the full scraping pipeline.
#
# Flow:
#   1. Load previous progress (skip already-done books)
#   2. Fetch all categories from the homepage
#   3. For each category:
#        a. Fetch its book list
#        b. Skip complete books, collect pending ones
#        c. Scrape each pending book (resume if partial)
#        d. Save progress + regenerate CSV after every book
#   4. Final CSV write when everything is done

import os, time
from tqdm import tqdm
from .config import BASE_URL, OUTPUT_DIR, DELAY
from .helpers import load_progress, save_progress, safe_name, ar2int
from .discovery import get_categories, get_books
from .scraper import scrape_book
from .report import generate_report, india_now
from .git_sync import git_push


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    done       = load_progress()   # dict of all previously scraped books
    categories = get_categories()  # list of {id, name} from homepage

    # Outer bar — one tick per category
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
        time.sleep(DELAY)  # pause after fetching the category page

        # Split books into already-complete (skip) and still-pending (scrape)
        pending, skipped = [], 0
        for b in books:
            e     = done.get(f"{cat_id}_{b['id']}", {})
            total = ar2int(e.get("total_pages", "0"))
            sc    = e.get("pages", 0)
            # A book is truly done only when status=complete AND pages match total
            if e.get("status") == "complete" and (total == 0 or sc >= total):
                skipped += 1
            else:
                pending.append(b)

        tqdm.write(f"\n📁 {cat_name}  —  {len(books)} books  ({skipped} ✅ done, {len(pending)} to scrape)")

        # Middle bar — one tick per book inside this category
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

            # ── Resume setup ───────────────────────────────────────────────
            # If this book was partially scraped before, pick up where we left off
            resume_page_id = None
            existing_text  = ""
            existing_pages = 0
            known_total    = ar2int(entry.get("total_pages", "0"))

            if entry.get("status") == "partial":
                resume_page_id = entry.get("next_page_id")  # saved checkpoint page
                existing_pages = entry.get("pages", 0)
                if resume_page_id and os.path.exists(txt_file):
                    # Load already-saved text so scraper can append to it
                    with open(txt_file, encoding="utf-8") as f:
                        existing_text = f.read().rstrip()
                else:
                    resume_page_id = None  # checkpoint missing or file gone — restart

            # ── Scrape ────────────────────────────────────────────────────
            result = scrape_book(
                book_id, book_title,
                resume_page_id, existing_text, existing_pages, known_total
            )

            if not result:
                tqdm.write(f"    ❌ Failed: {book_title[:55]}")
                time.sleep(DELAY)
                continue

            text, pages, complete, next_page_id, meta = result

            # ── Save .txt file ────────────────────────────────────────────
            # Resume mode: existing_text is already inside `text` — write as-is
            # Fresh mode : prepend the header block (title + URL + separator)
            header = f"الكتاب: {book_title}\nالرابط: {BASE_URL}/book/{book_id}\n{'='*60}\n\n"
            with open(txt_file, "w", encoding="utf-8") as f:
                f.write(text if (resume_page_id and existing_text) else header + text)

            status_icon = "✅" if complete else "⚠️ partial"
            tqdm.write(f"    {status_icon}  {book_title[:55]}  ({pages} pages)")

            # ── Update progress ───────────────────────────────────────────
            new_entry = {
                "title":      book_title,
                "pages":      pages,
                "status":     "complete" if complete else "partial",
                "scraped_at": india_now(),  # Indian Standard Time timestamp
                **meta,
            }
            if not complete:
                # Save the exact page ID we stopped at so next run can resume
                new_entry["next_page_id"] = next_page_id

            if resume_page_id:
                # meta is empty in resume mode — keep the metadata from the old entry
                for k in ("author", "publisher", "edition", "total_pages", "topics", "category"):
                    if not new_entry.get(k):
                        new_entry[k] = entry.get(k, "")

            done[done_key] = new_entry
            save_progress(done)    # write progress.json immediately
            generate_report(done)  # keep report.csv in sync
            git_push(f"scraped: {book_title[:60]}")
            time.sleep(DELAY)

        book_bar.close()

    generate_report(done)
    tqdm.write(f"\n🎉 Done! Output in: {OUTPUT_DIR}/")
