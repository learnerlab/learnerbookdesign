"""
Load book covers from a pre-scraped seed JSON file.

This avoids needing Playwright/Chromium on Render. To generate the seed file,
run the Playwright scraper locally:

    python scrapers/scrape_local.py

This creates data/covers_seed.json which gets committed and deployed.
"""
import json
import os

from database import add_cover

SEED_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "covers_seed.json")


def load_seed_covers():
    """Load covers from the seed JSON file into the database.

    Returns the number of covers added.
    """
    seed_path = os.path.normpath(SEED_FILE)
    if not os.path.exists(seed_path):
        print(f"  [WARN] No seed file at {seed_path}")
        print("  [HINT] Run locally: python scrapers/scrape_local.py")
        return 0

    with open(seed_path, "r") as f:
        covers = json.load(f)

    print(f"  Loading {len(covers)} covers from seed file...")
    total = 0
    for cover in covers:
        result = add_cover(
            title=cover.get("title", ""),
            author=cover.get("author", ""),
            designer=cover.get("designer", ""),
            genre=cover.get("genre", ""),
            image_url=cover.get("image_url", ""),
            source=cover.get("source", "I Need a Book Cover"),
            source_url=cover.get("source_url", ""),
        )
        if result:
            total += 1

    return total
