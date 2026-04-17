#!/usr/bin/env python3
"""
Run this LOCALLY to scrape ineedabookcover.com and save to a seed JSON file.
The seed file gets committed and deployed — no Playwright needed on Render.

This scraper:
1. Collects links to individual cover detail pages from genre listings
2. Visits each detail page to extract designer, title, author, genre
3. Skips junk entries (filter buttons, color swatches, category labels)

Usage:
    pip install playwright && playwright install chromium
    python scrapers/scrape_local.py
"""
import json
import os
import re
import sys
import time

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("Playwright not installed. Run: pip install playwright && playwright install chromium")
    sys.exit(1)

BASE_URL = "https://ineedabookcover.com"
SEED_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
SEED_FILE = os.path.join(SEED_DIR, "covers_seed.json")

GENRE_PAGES = [
    "/book-covers/",
    "/book-covers/?_genre=fiction",
    "/book-covers/?_genre=literary-fiction",
    "/book-covers/?_genre=nonfiction",
    "/book-covers/?_genre=memoir",
    "/book-covers/?_genre=biography",
    "/book-covers/?_genre=self-help",
    "/book-covers/?_genre=fantasy",
    "/book-covers/?_genre=thriller",
    "/book-covers/?_genre=mystery",
    "/book-covers/?_genre=romance",
    "/book-covers/?_genre=science-fiction",
    "/book-covers/?_genre=horror",
    "/book-covers/?_genre=poetry",
    "/book-covers/?_genre=history",
    "/book-covers/?_genre=food",
    "/book-covers/?_genre=art",
    "/book-covers/?_genre=children",
    "/book-covers/?_genre=young-adult",
]

# Junk entries to skip — filter buttons, color swatches, category labels
JUNK_TITLES = {
    "fiction", "nonfiction", "non-fiction", "literary fiction", "art",
    "biography", "memoir", "self-help", "fantasy", "thriller", "mystery",
    "romance", "science fiction", "sci-fi", "horror", "poetry", "history",
    "food", "children", "young adult", "ya", "social science",
    "all", "home", "book covers", "covers", "i need a book cover",
}

JUNK_SLUG_PATTERNS = [
    r"^colors?-filter",
    r"^(red|orange|yellow|green|blue|purple|pink|black|white|brown|grey|gray)$",
    r"^\d+-book-morph",
    r"^_genre=",
]


def _make_absolute(url):
    if not url:
        return ""
    if url.startswith("//"):
        return "https:" + url
    if url.startswith("/"):
        return BASE_URL + url
    if not url.startswith("http"):
        return BASE_URL + "/" + url
    return url


def _is_junk_url(url):
    """Check if a URL points to a filter, color swatch, or other non-cover page."""
    slug = url.rstrip("/").split("/")[-1]
    if not slug:
        return True
    for pat in JUNK_SLUG_PATTERNS:
        if re.match(pat, slug, re.IGNORECASE):
            return True
    if "?" in url and "_genre=" in url:
        return True
    return False


def _is_real_image(url):
    if not url:
        return False
    if "data:image" in url or "svg+xml" in url:
        return False
    if "logo" in url.lower() or "icon" in url.lower() or "avatar" in url.lower():
        return False
    if "placeholder" in url.lower():
        return False
    return True


def _scroll_and_load(page, max_scrolls=20):
    """Scroll down and click 'Load More' to reveal all covers."""
    prev_height = 0
    stable = 0
    for _ in range(max_scrolls):
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(1.5)
        for btn_text in ["Load More", "Show More", "Load more", "Show more"]:
            try:
                btn = page.locator(f"button:has-text('{btn_text}'), a:has-text('{btn_text}')").first
                if btn.is_visible(timeout=500):
                    btn.click()
                    time.sleep(2)
            except Exception:
                pass
        cur_height = page.evaluate("document.body.scrollHeight")
        if cur_height == prev_height:
            stable += 1
            if stable >= 3:
                break
        else:
            stable = 0
        prev_height = cur_height


def _collect_cover_links(page):
    """Find all links to individual cover detail pages from a listing page."""
    links = set()
    anchors = page.query_selector_all("a[href]")
    for a in anchors:
        try:
            href = a.get_attribute("href") or ""
            href = _make_absolute(href)
            # Match individual cover pages: /book-covers/some-slug/
            if re.match(r"https://ineedabookcover\.com/book-covers/[a-z0-9][a-z0-9\-]+/?$", href):
                clean = href.rstrip("/") + "/"
                if not _is_junk_url(clean):
                    links.add(clean)
        except Exception:
            continue
    return links


def _parse_title_designer_from_meta(page):
    """
    Page titles on ineedabookcover.com follow patterns like:
      "Tyler Comrie's design for 'Carnality' by Lina Wolff"
      "Chip Kidd's design for 'Dry' by Augusten Burroughs"
      "Keith Hayes' design for 'The Goldfinch' by Donna Tartt"
      "Blink | I Need a Book Cover"
      "Cujo | I Need a Book Cover"
    """
    title_tag = ""
    try:
        title_tag = page.title() or ""
    except Exception:
        pass

    designer = ""
    book_title = ""
    author = ""

    # Pattern: "Designer's design for 'Title' by Author"
    # Also handles: "Designer's design for "Title" by Author"
    m = re.match(
        r"^(.+?)(?:'s|'s)\s+design\s+for\s+[\"'"'\u201c\u201d](.+?)[\"'"'\u201c\u201d](?:\s+by\s+(.+?))?(?:\s*\||\s*–|\s*$)",
        title_tag, re.IGNORECASE
    )
    if m:
        designer = m.group(1).strip()
        book_title = m.group(2).strip()
        author = (m.group(3) or "").strip()
        # Clean up trailing " | I Need a Book Cover"
        author = re.sub(r"\s*\|.*$", "", author).strip()
        return book_title, designer, author

    # Pattern: "Title | I Need a Book Cover"
    m = re.match(r"^(.+?)\s*\|\s*I Need a Book Cover", title_tag)
    if m:
        book_title = m.group(1).strip()

    # Pattern: "Title - designer information from INeedABookCover.com"
    m = re.match(r"^(.+?)\s+(?:cover art|book cover|information)\s+", title_tag, re.IGNORECASE)
    if m:
        book_title = m.group(1).strip()

    return book_title, designer, author


def _scrape_detail_page(page, url):
    """Visit an individual cover page and extract structured data."""
    try:
        page.goto(url, timeout=25000)
        page.wait_for_load_state("domcontentloaded", timeout=10000)
        time.sleep(1.5)
    except Exception as e:
        print(f"      [SKIP] Could not load {url}: {e}")
        return None

    cover = {
        "title": "",
        "image_url": "",
        "source_url": url,
        "genre": "",
        "author": "",
        "designer": "",
        "source": "I Need a Book Cover",
    }

    # --- Extract from page <title> (most reliable for designer) ---
    title_text, designer_from_title, author_from_title = _parse_title_designer_from_meta(page)
    cover["designer"] = designer_from_title
    cover["author"] = author_from_title
    if title_text:
        cover["title"] = title_text

    # --- Extract <h1> for the cover/book name ---
    try:
        h1 = page.locator("h1").first
        if h1.is_visible(timeout=1000):
            h1_text = h1.inner_text().strip()
            if h1_text and h1_text.lower() not in JUNK_TITLES:
                cover["title"] = h1_text
    except Exception:
        pass

    # --- If no title yet, derive from URL slug ---
    if not cover["title"]:
        slug = url.rstrip("/").split("/")[-1]
        cover["title"] = slug.replace("-", " ").title()

    # Skip if title looks like junk
    if cover["title"].lower().strip() in JUNK_TITLES:
        return None

    # --- Extract the main cover image ---
    try:
        images = page.query_selector_all("img")
        best_img = None
        best_area = 0
        for img in images:
            src = img.get_attribute("src") or img.get_attribute("data-src") or ""
            if not _is_real_image(src):
                continue
            try:
                box = img.bounding_box()
                if box:
                    area = box["width"] * box["height"]
                    if area > best_area:
                        best_area = area
                        best_img = src
            except Exception:
                if not best_img:
                    best_img = src
        if best_img:
            cover["image_url"] = _make_absolute(best_img)
    except Exception:
        pass

    if not cover["image_url"]:
        return None

    # --- Extract designer from page body if not found in title ---
    if not cover["designer"]:
        try:
            body_text = page.inner_text("body")
            for pattern in [
                r"(?:Cover\s+)?[Dd]esign(?:er|ed)?\s*(?:by|:)\s*([A-Z][A-Za-z\s\.\-''\u2019]+?)(?:\n|\.|,|\||–|—|$)",
                r"[Aa]rt\s+(?:[Dd]irection|[Dd]irector)\s*(?:by|:)\s*([A-Z][A-Za-z\s\.\-''\u2019]+?)(?:\n|\.|,|\||–|—|$)",
            ]:
                m = re.search(pattern, body_text)
                if m:
                    name = m.group(1).strip().rstrip(".,;:")
                    if 2 < len(name) < 50 and not any(w in name.lower() for w in [
                        "book", "cover", "genre", "price", "cart", "publish",
                        "page", "print", "copyright", "edition",
                    ]):
                        cover["designer"] = name
                        break
        except Exception:
            pass

    # --- Extract designer from links to /designers/ pages ---
    if not cover["designer"]:
        try:
            designer_links = page.locator("a[href*='/designers/']").all()
            for link in designer_links:
                try:
                    text = link.inner_text().strip()
                    href = link.get_attribute("href") or ""
                    if text and 2 < len(text) < 50 and "/designers/" in href:
                        if text.lower() not in ("designers", "book cover designers", "all designers"):
                            cover["designer"] = text
                            break
                except Exception:
                    continue
        except Exception:
            pass

    # --- Extract author from page body if not found in title ---
    if not cover["author"]:
        try:
            body_text = page.inner_text("body") if "body_text" not in dir() else body_text
            for pattern in [
                r"(?:by|[Aa]uthor)\s*:\s*([A-Z][A-Za-z\s\.\-''\u2019]+?)(?:\n|\.|,|\||–|—|$)",
            ]:
                m = re.search(pattern, body_text)
                if m:
                    name = m.group(1).strip().rstrip(".,;:")
                    if 2 < len(name) < 50 and name.lower() != cover.get("designer", "").lower():
                        cover["author"] = name
                        break
        except Exception:
            pass

    # --- Extract genre from breadcrumbs, tags, or category links ---
    try:
        for sel in [
            "a[href*='_genre=']",
            ".breadcrumb a", "nav.breadcrumbs a",
            "[rel='tag']", ".tag a", ".category a",
        ]:
            elements = page.locator(sel).all()
            for el in elements:
                try:
                    text = el.inner_text().strip()
                    if text and text.lower() not in ("home", "book covers", "covers", "all", "") and len(text) < 40:
                        cover["genre"] = text
                        break
                except Exception:
                    continue
            if cover["genre"]:
                break
    except Exception:
        pass

    return cover


def scrape():
    os.makedirs(SEED_DIR, exist_ok=True)
    all_covers = []
    seen_urls = set()
    seen_images = set()
    detail_links = set()

    print("=" * 60)
    print("  Scraping ineedabookcover.com")
    print("  Phase 1: Collecting cover links from listing pages")
    print("=" * 60)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-gpu"])
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            viewport={"width": 1440, "height": 900},
        )
        page = context.new_page()

        # Phase 1: Collect all individual cover page URLs
        for genre_path in GENRE_PAGES:
            genre_name = genre_path.split("=")[-1] if "=" in genre_path else "all"
            print(f"\n  Scanning {genre_name}...")

            try:
                page.goto(BASE_URL + genre_path, timeout=30000)
                page.wait_for_load_state("networkidle", timeout=15000)
            except Exception as e:
                print(f"    [ERROR] {e}")
                continue

            _scroll_and_load(page)
            links = _collect_cover_links(page)
            new_links = links - detail_links
            detail_links.update(new_links)
            print(f"    -> {len(new_links)} new cover links (total: {len(detail_links)})")
            time.sleep(1)

        # Phase 2: Visit each detail page
        print(f"\n{'=' * 60}")
        print(f"  Phase 2: Scraping {len(detail_links)} cover detail pages")
        print(f"  (this may take a while — ~1 second per page)")
        print(f"{'=' * 60}")

        sorted_links = sorted(detail_links)
        for i, link in enumerate(sorted_links):
            if link in seen_urls:
                continue

            if (i + 1) % 25 == 0 or i == 0:
                designers_found = sum(1 for c in all_covers if c.get("designer"))
                print(f"\n  [{i + 1}/{len(sorted_links)}] {len(all_covers)} covers scraped, {designers_found} with designers...")

            cover = _scrape_detail_page(page, link)
            if cover and cover["image_url"] not in seen_images:
                seen_images.add(cover["image_url"])
                seen_urls.add(link)
                all_covers.append(cover)

            time.sleep(0.5)

        browser.close()

    # Save
    with open(SEED_FILE, "w") as f:
        json.dump(all_covers, f, indent=2)

    designers_found = sum(1 for c in all_covers if c.get("designer"))
    print(f"\n{'=' * 60}")
    print(f"  Done! Saved {len(all_covers)} covers to {SEED_FILE}")
    print(f"  Covers with designer data: {designers_found}/{len(all_covers)}")
    print(f"")
    print(f"  Next steps:")
    print(f"    git add data/covers_seed.json")
    print(f"    git commit -m 'Update seed data with designer names'")
    print(f"    git push")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    scrape()
