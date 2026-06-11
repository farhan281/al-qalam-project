# shamela/metadata.py
# ─────────────────────────────────────────────
# Extracts book metadata from a parsed book page.
#
# Shamela shows a "betaka" (book card) above the
# table of contents with author, publisher, edition,
# and total page count. The TOC links give us topics.
# The breadcrumb gives us the category name.

from .helpers import get_soup


def fetch_meta(book_soup):
    """
    Pull structured metadata out of an already-parsed book page.

    Where the data lives on the page:
      .betaka-index previous siblings  -> author, publisher, edition, total_pages
      .betaka-index <a> links          -> table of contents topics
      .breadcrumb li (last item)       -> category name

    Returns a dict with keys:
      author, publisher, edition, total_pages, topics, category
    All values are strings; missing fields default to "".
    """
    meta = {k: "" for k in ("author", "publisher", "edition", "total_pages", "topics", "category")}

    bi = book_soup.select_one(".betaka-index")
    if bi:
        # Book info is stored in the sibling elements that appear just before .betaka-index
        for sib in bi.previous_siblings:
            t = sib.get_text(strip=True) if hasattr(sib, "get_text") else str(sib).strip()
            if   t.startswith("المؤلف:"):       meta["author"]      = t[len("المؤلف:"):].strip()
            elif t.startswith("الناشر:"):       meta["publisher"]   = t[len("الناشر:"):].strip()
            elif t.startswith("الطبعة:"):       meta["edition"]     = t[len("الطبعة:"):].strip()
            elif t.startswith("عدد الصفحات:"): meta["total_pages"] = t[len("عدد الصفحات:"):].strip()

        # Every <a> inside .betaka-index is a chapter/topic heading
        meta["topics"] = " | ".join(a.get_text(strip=True) for a in bi.select("a"))

    # Breadcrumb: الرئيسية > أقسام الكتب > العقيدة  -> last li = category
    bc = book_soup.select(".breadcrumb li")
    if len(bc) >= 3:
        meta["category"] = bc[-1].get_text(strip=True)

    return meta
