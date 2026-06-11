# shamela/git_sync.py
# ─────────────────────────────────────────────
# Auto-pushes scraped output to GitHub after
# every book completes. Runs git add, commit,
# and push silently in the background.

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
