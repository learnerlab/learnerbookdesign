"""
Scraper for Open Library - free API with millions of book covers.
https://openlibrary.org/dev/docs/api/covers
"""
import requests
import time
from database import add_cover

BASE_URL = "https://openlibrary.org"
COVERS_URL = "https://covers.openlibrary.org"

# Minimum publish year for filtering — focus on modern books
MIN_YEAR = 2015

# Nonfiction-heavy subjects with design-forward covers
CURATED_SUBJECTS = [
    # Nonfiction core
    "popular_science", "science", "neuroscience", "psychology",
    "sociology", "economics", "politics", "climate_change",
    "technology", "artificial_intelligence",
    "memoir", "biography", "autobiography",
    "history", "american_history", "world_history",
    "philosophy", "essays", "journalism",
    "health", "self_help", "business",
    "nature", "environment",
    "food", "travel",
    # Design & visual culture
    "design", "graphic_design", "architecture", "photography",
    "typography", "art", "visual_arts",
    # Modern fiction (smaller portion)
    "contemporary_fiction", "literary_fiction",
]


def get_cover_url(olid, size="L"):
    return f"{COVERS_URL}/b/olid/{olid}-{size}.jpg"


def scrape_subject(subject, limit=50):
    """Scrape covers from an Open Library subject, filtering for modern books (post-2015)."""
    added = 0
    offset = 0
    skipped_old = 0

    while added < limit:
        url = f"{BASE_URL}/subjects/{subject}.json?limit=50&offset={offset}"
        try:
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except (requests.RequestException, ValueError):
            break

        works = data.get("works", [])
        if not works:
            break

        for work in works:
            title = work.get("title", "")
            authors = ", ".join(a.get("name", "") for a in work.get("authors", []))
            cover_id = work.get("cover_id")
            cover_edition_key = work.get("cover_edition_key", "")

            if not cover_id and not cover_edition_key:
                continue

            # Filter by year — skip books published before MIN_YEAR
            first_publish_year = work.get("first_publish_year")
            if first_publish_year and first_publish_year < MIN_YEAR:
                skipped_old += 1
                continue

            if cover_id:
                image_url = f"{COVERS_URL}/b/id/{cover_id}-L.jpg"
            else:
                image_url = get_cover_url(cover_edition_key)

            year_str = str(first_publish_year) if first_publish_year else ""

            result = add_cover(
                title=title,
                author=authors,
                genre=subject.replace("_", " ").title(),
                image_url=image_url,
                source="Open Library",
                source_url=f"{BASE_URL}{work.get('key', '')}",
                year=year_str,
            )
            if result:
                added += 1
            if added >= limit:
                break

        offset += 50
        # Stop if we're mostly hitting old books (diminishing returns)
        if skipped_old > 150:
            break
        time.sleep(0.5)

    return added


def scrape_all(covers_per_subject=30):
    """Scrape covers from all curated subjects."""
    total = 0
    for subject in CURATED_SUBJECTS:
        count = scrape_subject(subject, limit=covers_per_subject)
        total += count
        print(f"  [{subject}] Added {count} covers")
        time.sleep(1)
    return total
