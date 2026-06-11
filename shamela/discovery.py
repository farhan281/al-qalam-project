# shamela/discovery.py
# ─────────────────────────────────────────────
# Fetches the list of categories and books from
# the website. No scraping logic here — just
# discovery / navigation.

import re
from tqdm import tqdm
from .config import BASE_URL
from .helpers import get_soup


def get_categories():
    """
    Scrape all categories from the Shamela homepage.

    They live inside the #cats section as <a class="cat_title"> elements.
    Each link href ends with the numeric category ID: /category/1

    Cleans up the display name by:
      - Removing the badge (book count number) appended in the link text
      - Stripping leading "1. " style numbering

    Returns a list of dicts: [{ "id": "1", "name": "العقيدة" }, ...]
    """
    tqdm.write("📚 Fetching categories...")
    s = get_soup(BASE_URL)
    if not s:
        return []

    cats = []
    for a in s.select("#cats a.cat_title"):
        href  = a.get("href", "")
        name  = a.get_text(strip=True)

        # Strip the badge number (e.g. "42") that appears inside the link
        badge = a.select_one(".badge")
        if badge:
            name = name.replace(badge.get_text(), "").strip()

        # Strip leading "1. " numbering
        name = re.sub(r"^\d+\.\s*", "", name).strip()

        # Category ID is the last path segment: /category/1 -> "1"
        cat_id = href.rstrip("/").split("/")[-1]
        if cat_id.isdigit():
            cats.append({"id": cat_id, "name": name})

    tqdm.write(f"  ✅ {len(cats)} categories found\n")
    return cats


def get_books(cat_id):
    """
    Fetch all books listed on a single category page.

    Each book appears as <a class="book_title"> with href="/book/{id}".

    Returns a list of dicts: [{ "id": "6388", "title": "الفقه الأكبر" }, ...]
    """
    s = get_soup(f"{BASE_URL}/category/{cat_id}")
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
