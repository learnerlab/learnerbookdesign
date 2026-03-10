"""
Scraper for Open Library - free API with millions of book covers.
https://openlibrary.org/dev/docs/api/covers
"""
import requests
import time
from database import add_cover

BASE_URL = "https://openlibrary.org"
COVERS_URL = "https://covers.openlibrary.org"

CURATED_SUBJECTS = [
    "design", "graphic_design", "art", "fiction", "science_fiction",
    "fantasy", "mystery", "thriller", "romance", "horror",
    "literary_fiction", "poetry", "philosophy", "history",
    "architecture", "photography", "typography",
    "best_sellers", "award_winners", "classic_literature",
    "contemporary_fiction", "young_adult", "biography",
]


def get_cover_url(olid, size="L"):
    return f"{COVERS_URL}/b/olid/{olid}-{size}.jpg"


def scrape_subject(subject, limit=50):
    """Scrape covers from an Open Library subject."""
    added = 0
    offset = 0

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

            if cover_id:
                image_url = f"{COVERS_URL}/b/id/{cover_id}-L.jpg"
            else:
                image_url = get_cover_url(cover_edition_key)

            result = add_cover(
                title=title,
                author=authors,
                genre=subject.replace("_", " ").title(),
                image_url=image_url,
                source="Open Library",
                source_url=f"{BASE_URL}{work.get('key', '')}",
            )
            if result:
                added += 1
            if added >= limit:
                break

        offset += 50
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
