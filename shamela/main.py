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


def main(category_id=None):
    """
    Scrape Shamela books.
    If category_id is provided, scrape only that category.
    Otherwise, scrape all categories.
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    done       = load_progress()   # dict of all previously scraped books
    all_cats   = get_categories()  # list of {id, name} from homepage
    
    # Filter by category if specified
    if category_id:
        categories = [c for c in all_cats if c["id"] == str(category_id)]
        if not categories:
            tqdm.write(f"❌ Category ID {category_id} not found")
            return
    else:
        categories = all_cats

    # Resume cursor: keep track of where we left off across runs
    cursor = done.get("_cursor", {})
    start_cat = int(cursor.get("cat_index", 0)) if cursor.get("cat_index") is not None else 0

    # Outer bar — one tick per category. Start from saved cursor so UI reflects resume point.
    overall = tqdm(
        total=len(categories), unit="cat", dynamic_ncols=True, initial=start_cat,
        bar_format="📁 {desc:<25} {bar} {n}/{total} categories [{elapsed}<{remaining}]"
    )

    for idx in range(start_cat, len(categories)):
        cat = categories[idx]
        cat_id, cat_name = cat["id"], cat["name"]
        overall.set_description(cat_name[:25])
        # update cursor at category start
        done["_cursor"] = {"cat_index": idx, "cat_id": cat_id, "book_index": 0}
        save_progress(done)

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

        # Support resuming at the book-level within this category
        start_book = int(cursor.get("book_index", 0)) if (idx == start_cat and cursor) else 0
        pending_full = pending
        if start_book >= len(pending_full):
            start_book = 0

        # Middle bar — one tick per book inside this category
        book_bar = tqdm(
            total=len(pending_full), unit="book", dynamic_ncols=True, leave=True, initial=start_book,
            bar_format="  📚 {desc:<40} {bar} {n}/{total} books [{elapsed}<{remaining}]"
        )

        for bi in range(start_book, len(pending_full)):
            book = pending_full[bi]
            book_id, book_title = book["id"], book["title"]
            done_key = f"{cat_id}_{book_id}"
            entry    = done.get(done_key, {})
            txt_file = os.path.join(cat_folder, safe_name(book_title) + ".txt")

            # update cursor at book start
            done["_cursor"] = {"cat_index": idx, "cat_id": cat_id, "book_index": bi, "book_id": book_id}
            save_progress(done)

            book_bar.set_description(book_title[:40])

            # ── Resume setup ───────────────────────────────────────────────
            # Resume when there is a saved next_page_id and the text file exists.
            resume_page_id = None
            existing_text  = ""
            existing_pages = 0
            known_total    = ar2int(entry.get("total_pages", "0"))

            if entry.get("next_page_id") and os.path.exists(txt_file):
                resume_page_id = entry.get("next_page_id")
                existing_pages = entry.get("pages", 0)
                with open(txt_file, encoding="utf-8") as f:
                    existing_text = f.read().rstrip()
                if not existing_text:
                    resume_page_id = None
            elif entry.get("status") == "partial":
                resume_page_id = entry.get("next_page_id")  # saved checkpoint page
                existing_pages = entry.get("pages", 0)
                if resume_page_id and os.path.exists(txt_file):
                    with open(txt_file, encoding="utf-8") as f:
                        existing_text = f.read().rstrip()
                else:
                    resume_page_id = None  # checkpoint missing or file gone — restart

            # Prepare output file for append mode on resume or write mode for new book
            if resume_page_id and os.path.exists(txt_file):
                mode = "a"
            else:
                mode = "w"
                header = f"الكتاب: {book_title}\nالرابط: {BASE_URL}/book/{book_id}\n{'='*60}\n\n"

            def checkpoint_page(next_page_id, page_count, page_chunk, complete):
                """Write page chunk and save progress for the current book, and save cursor."""
                if page_chunk:
                    with open(txt_file, "a", encoding="utf-8") as f:
                        f.write(page_chunk)

                new_entry = {
                    "title":      book_title,
                    "pages":      page_count,
                    "status":     "complete" if complete else "partial",
                    "scraped_at": india_now(),
                    **entry,
                }
                if not complete:
                    new_entry["next_page_id"] = next_page_id
                else:
                    new_entry.pop("next_page_id", None)

                done[done_key] = new_entry
                # Update cursor with current page so we can resume at exact page
                done["_cursor"] = {"cat_index": idx, "cat_id": cat_id, "book_index": bi, "book_id": book_id, "page_id": next_page_id}
                save_progress(done)

            # ── Scrape ────────────────────────────────────────────────────
            if mode == "w":
                with open(txt_file, "w", encoding="utf-8") as f:
                    f.write(header)

            result = scrape_book(
                book_id, book_title,
                resume_page_id, existing_text, existing_pages, known_total,
                checkpoint_func=checkpoint_page
            )

            if not result:
                tqdm.write(f"    ❌ Failed: {book_title[:55]}")
                time.sleep(DELAY)
                book_bar.update(1)
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
                "scraped_at": india_now(),
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
            # advance cursor to next book
            done["_cursor"] = {"cat_index": idx, "cat_id": cat_id, "book_index": bi + 1}
            save_progress(done)
            generate_report(done)
            if result.complete:
                git_push(f"scraped: {book_title[:60]}")
            time.sleep(DELAY)
            book_bar.update(1)

        book_bar.close()
        overall.update(1)

    generate_report(done)
    # Clear cursor on full completion
    if "_cursor" in done:
        done.pop("_cursor", None)
        save_progress(done)
    tqdm.write(f"\n🎉 Done! Output in: {OUTPUT_DIR}/")
