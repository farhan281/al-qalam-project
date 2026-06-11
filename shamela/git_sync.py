# shamela/git_sync.py
# ─────────────────────────────────────────────
# Auto-pushes scraped output to GitHub after
# every book completes. Runs git add, commit,
# and push silently in the background.

import subprocess
from tqdm import tqdm


def git_push(message="update: scraped data"):
    """
    Stage all changes in shamela_output/ and push to GitHub.
    Errors are printed but never crash the scraper.
    """
    try:
        subprocess.run(["git", "add", "shamela_output/"], check=True, capture_output=True)
        result = subprocess.run(["git", "commit", "-m", message], capture_output=True, text=True)
        # If nothing changed git commit exits with code 1 — that's fine, skip push
        if result.returncode != 0:
            return
        subprocess.run(["git", "push", "origin", "master"], check=True, capture_output=True)
        tqdm.write("  📤 Pushed to GitHub")
    except Exception as e:
        tqdm.write(f"  [GIT] Push failed: {e}")
