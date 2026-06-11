# shamela/git_sync.py
# ─────────────────────────────────────────────
# Auto-pushes ALL scraped output to GitHub after
# every book completes.
#
# What gets committed in every push:
#   - The new .txt file for the book just scraped
#   - Any new category subfolder (e.g. shamela_output/الفقه/)
#   - Updated progress.json  (latest status of all books)
#   - Updated report.csv     (latest CSV summary)
#
# If nothing changed (e.g. a book failed), the commit
# is skipped silently — no empty commits in the history.

import subprocess
from tqdm import tqdm


def git_push(message="update: scraped data"):
    """
    Stage ALL changes under shamela_output/ and push to GitHub.
    Covers:
      - New .txt files (books just scraped)
      - New category subfolders
      - Updated progress.json and report.csv
    Errors are printed but never crash the scraper.
    """
    try:
        # Stage everything — new files, modified files, new folders
        subprocess.run(["git", "add", "--all", "shamela_output/"], check=True, capture_output=True)
        result = subprocess.run(["git", "commit", "-m", message], capture_output=True, text=True)
        # returncode 1 means nothing changed — skip push silently
        if result.returncode != 0:
            return
        subprocess.run(["git", "push", "origin", "master"], check=True, capture_output=True)
        tqdm.write("  📤 Pushed to GitHub")
    except Exception as e:
        tqdm.write(f"  [GIT] Push failed: {e}")
