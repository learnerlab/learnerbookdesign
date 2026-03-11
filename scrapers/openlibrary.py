"""
Fallback scraper for Open Library — free API with millions of book covers.
Used only when no seed data is available from ineedabookcover.com.
No browser needed, just HTTP requests.
"""
import time
import urllib.request
import urllib.error
import json

from database import add_cover

SUBJECTS = [
    "fiction", "literary_fiction", "fantasy", "science_fiction",
    "mystery", "thriller", "romance", "horror",
    "biography", "memoir", "history", "poetry",
    "self-help", "philosophy", "art", "design",
    "cooking", "travel", "young_adult", "graphic_novels",
]

COVER_URL_TEMPLATE = "https://covers.openlibrary.org/b/id/{cover_id}-L.jpg"
SUBJECTS_API = "https://openlibrary.org/subjects/{subject}.json?limit={limit}&offset={offset}"


def _fetch_json(url, retries=3):
    headers = {"User-Agent": "BookCoverSwiper/1.0 (educational project)"}
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode())
        except (urllib.error.URLError, urllib.error.HTTPError, OSError) as e:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
            else:
                print(f"    [ERROR] Failed to fetch {url}: {e}")
                return None


def scrape_openlibrary(covers_per_subject=50):
    total = 0
    for subject in SUBJECTS:
        print(f"  Fetching {subject}...")
        url = SUBJECTS_API.format(subject=subject, limit=covers_per_subject, offset=0)
        data = _fetch_json(url)
        if not data or "works" not in data:
            continue

        added = 0
        for work in data["works"]:
            cover_id = work.get("cover_id")
            if not cover_id:
                continue
            title = work.get("title", "").strip()
            if not title:
                continue
            authors = work.get("authors", [])
            author = authors[0]["name"] if authors else ""
            genre = subject.replace("_", " ").title()
            image_url = COVER_URL_TEMPLATE.format(cover_id=cover_id)
            source_url = f"https://openlibrary.org{work.get('key', '')}"
            result = add_cover(
                title=title, author=author, designer="", genre=genre,
                image_url=image_url, source="Open Library",
                source_url=source_url,
            )
            if result:
                added += 1
                total += 1
        print(f"    -> {added} covers (total: {total})")
        time.sleep(1)
    return total
