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

import subprocess, re, shutil
from tqdm import tqdm

# Resolve full path to git at import time — avoids partial-path execution risk
GIT = shutil.which("git") or "/usr/bin/git"


def _safe_message(msg):
    """
    Sanitise the commit message so no shell-special characters can
    interfere with git argument parsing. Strips control characters and
    common shell metacharacters, caps at 200 chars.
    """
    return re.sub(r"[\x00-\x1f\x7f`$|;&<>]", "", msg)[:200]


def git_push(message="update: scraped data"):
    """
    Stage ALL changes under shamela_output/ and push to GitHub.
    Covers:
      - New .txt files (books just scraped)
      - New category subfolders
      - Updated progress.json and report.csv
    The commit message is sanitised before use.
    Errors are printed but never crash the scraper.
    """
    safe_msg = _safe_message(message)
    try:
        # Stage everything — new files, modified files, new folders
        subprocess.run([GIT, "add", "--all", "shamela_output/"], check=True, capture_output=True)
        result = subprocess.run([GIT, "commit", "-m", safe_msg], capture_output=True, text=True)
        # returncode 1 means nothing changed — skip push silently
        if result.returncode != 0:
            return
        subprocess.run([GIT, "push", "origin", "master"], check=True, capture_output=True)
        tqdm.write("  📤 Pushed to GitHub")
    except Exception as e:
        tqdm.write(f"  [GIT] Push failed: {e}")
