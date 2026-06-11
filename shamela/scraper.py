# shamela/scraper.py
# ─────────────────────────────────────────────
# Core scraping logic for a single book.
#
# Shamela serves book text via an AJAX endpoint.
# Pages form a linked list — each page's JSON
# contains the ID of the next page. We follow
# that chain until nextId is null (end of book).
#
# API:  GET /ajax/pageContent/{book_id}/{page_id}
# Response JSON:
#   {
#     "nass":    "<html> page text </html>",
#     "title":   "chapter name",
#     "pageNum": "١٤",
#     "nextId":  "10002"   <- null on last page
#   }

import re, time
from collections import namedtuple
from bs4 import BeautifulSoup
from tqdm import tqdm
from .config import BASE_URL, PAGE_DELAY
from .helpers import fetch, get_soup, ar2int
from .metadata import fetch_meta

# Named return type — clearer than a raw 5-tuple and prevents unpacking mistakes
ScrapeResult = namedtuple("ScrapeResult", ["text", "page_count", "complete", "next_page_id", "meta"])


def scrape_book(book_id, book_title, resume_page_id=None,
                existing_text="", existing_pages=0, known_total=0,
                checkpoint_func=None):
    """
    Download the full text of one book, page by page.

    NORMAL (fresh) mode:
      1. Fetch the book's landing page to get metadata and the first page ID
      2. Loop: fetch each page via AJAX, extract text, follow nextId
      3. Stop when nextId is null -> book is complete

    RESUME mode (resume_page_id is not None):
      - Skip the landing page fetch entirely
      - Start the AJAX loop from resume_page_id
      - Prepend existing_text so the final output is the full book

    Args:
      book_id         : Shamela numeric book ID string (e.g. "6388")
      book_title      : Human-readable title, used for display only
      resume_page_id  : AJAX page ID to restart from; None = fresh start
      existing_text   : Text already saved from a previous partial run
      existing_pages  : Page count already done (sets the progress bar start)
      known_total     : Total pages expected (sets the progress bar maximum)
      checkpoint_func : optional callback(next_page_id, page_count, page_text, complete)
                        called after each page is processed or on failure.

    Returns ScrapeResult(text, page_count, complete, next_page_id, meta):
      text          : Complete book text (existing + newly scraped)
      page_count    : Total pages scraped across all runs
      complete      : True if we reached the last page naturally
      next_page_id  : The page ID where we stopped (used to resume later)
      meta          : Metadata dict; empty dict when in resume mode
    """
    meta       = {}
    all_text   = []
    page_count = existing_pages

    if resume_page_id:
        # Resume: jump straight to the saved checkpoint
        page_id = resume_page_id
        if existing_text:
            all_text = [existing_text]  # carry forward what was already saved
        tqdm.write(f"    ↩  Resuming {book_title[:50]} — page_id {page_id} ({existing_pages} pages done)")
    else:
        # Fresh: fetch the book landing page first
        s = get_soup(f"{BASE_URL}/book/{book_id}")
        if not s:
            return None

        meta        = fetch_meta(s)
        known_total = ar2int(meta.get("total_pages", "0"))

        # First link in the table of contents = first AJAX page ID
        link = s.select_one("div.betaka-index a[href]")
        if link:
            m       = re.search(r"/book/\d+/(\d+)", link.get("href", ""))
            page_id = int(m.group(1)) if m else 1
        else:
            page_id = 1  # fallback when no TOC is present

    # Inner progress bar — one tick per page
    # known_total gives the % complete; existing_pages sets the starting position
    pbar = tqdm(
        total=known_total or None,
        initial=existing_pages,
        unit="pg",
        dynamic_ncols=True,
        leave=False,  # bar disappears after the book finishes
        bar_format="    {desc:<35} {bar} {n}/{total} [{elapsed}<{remaining} {rate_fmt}]",
    )

    complete = False
    try:
        while page_id is not None:
            r = fetch(f"{BASE_URL}/ajax/pageContent/{book_id}/{page_id}")
            if not r:
                # All retries exhausted — save partial and resume next run
                tqdm.write(f"    [ERROR] page {page_id}: giving up after retries")
                if checkpoint_func:
                    checkpoint_func(page_id, page_count, "", False)
                break

            try:
                data = r.json()
            except Exception as e:
                tqdm.write(f"    [ERROR] page {page_id}: bad JSON — {e}")
                if checkpoint_func:
                    checkpoint_func(page_id, page_count, "", False)
                break

            page_chunk = ""
            nass = data.get("nass", "")
            if nass:
                sp = BeautifulSoup(nass, "html.parser")

                # Remove copy-to-clipboard buttons — they are UI, not content
                for a in sp.find_all("a", class_="btn_tag"):
                    a.decompose()

                text       = sp.get_text("\n", strip=True)
                page_num   = data.get("pageNum", "")
                page_title = data.get("title", "")

                if page_title:
                    page_chunk = f"\n--- ص{page_num}: {page_title} ---\n{text}"
                    # Update the progress bar description with the current chapter
                    pbar.set_description(f"ص{page_num}: {page_title[:28]}")
                else:
                    page_chunk = text

                all_text.append(page_chunk)

            page_count += 1
            pbar.update(1)

            # Follow the linked list: nextId=null means this was the last page
            next_id = data.get("nextId")
            next_page_id = int(next_id) if next_id else None
            if checkpoint_func:
                checkpoint_func(next_page_id, page_count, page_chunk, False)
            page_id = next_page_id

            time.sleep(PAGE_DELAY)  # be gentle with the server between pages

        complete = (page_id is None)  # True only if we reached the natural end

    finally:
        pbar.close()  # always close the bar, even if an exception occurred

    return ScrapeResult(
        text="\n".join(all_text),
        page_count=page_count,
        complete=complete,
        next_page_id=page_id,
        meta=meta,
    )
