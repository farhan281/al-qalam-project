# run.py
# ─────────────────────────────────────────────
# Entry point. Run this file to start the scraper:
#
#   python run.py              -> scrape all categories
#   python run.py --cat 1      -> scrape only category 1 (العقيدة)
#   python run.py --cat 14     -> scrape only category 14 (الفقه الحنفي)

import sys
from shamela import main

if __name__ == "__main__":
    category_id = None
    
    # Parse --cat or --category argument
    if len(sys.argv) > 1:
        if sys.argv[1] in ("--cat", "--category") and len(sys.argv) > 2:
            category_id = sys.argv[2]
    
    main(category_id=category_id)
