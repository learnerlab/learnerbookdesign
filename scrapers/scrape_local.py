#!/usr/bin/env python3
"""
Run this LOCALLY to scrape ineedabookcover.com and save to a seed JSON file.
The seed file gets committed and deployed — no Playwright needed on Render.

This scraper:
1. Finds cover images on listing pages (proven approach from old scraper)
2. Extracts detail page URLs from parent <a> tags around each image
3. Visits each detail page to extract designer, title, author, genre
4. Falls back to image alt text / URL slug when no detail page exists

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

JUNK_TITLES = {
    "fiction", "nonfiction", "non-fiction", "literary fiction", "art",
    "biography", "memoir", "self-help", "fantasy", "thriller", "mystery",
    "romance", "science fiction", "sci-fi", "horror", "poetry", "history",
    "food", "children", "young adult", "ya", "social science",
    "all", "home", "book covers", "covers", "i need a book cover",
    "red", "orange", "yellow", "green", "blue", "purple", "pink",
    "black", "white", "brown", "grey", "gray",
}


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


def _is_real_cover_image(src, alt=""):
    """Filter out non-cover images: logos, icons, SVGs, placeholders, tiny imgs."""
    if not src:
        return False
    if "data:image" in src or "svg+xml" in src:
        return False
    low = src.lower()
    if any(x in low for x in ["logo", "icon", "avatar", "placeholder", "gravatar"]):
        return False
    if alt.lower().strip() in JUNK_TITLES:
        return False
    return True


def _is_detail_page_url(url):
    """Check if a URL points to an individual cover detail page."""
    if not url:
        return False
    # Must be on the site, under /book-covers/, with an actual slug
    m = re.match(r"https?://(?:www\.)?ineedabookcover\.com/book-covers/([^/?#]+)/?$", url)
    if not m:
        return False
    slug = m.group(1)
    # Skip genre filter pages, color filters, morph animations
    if slug.lower() in JUNK_TITLES:
        return False
    if re.match(r"^colors?-filter", slug, re.IGNORECASE):
        return False
    if re.match(r"^\d+-book-morph", slug, re.IGNORECASE):
        return False
    return True


def _scroll_and_load(page, max_scrolls=20):
    """Scroll down and click 'Load More' to reveal all covers."""
    prev_height = 0
    stable = 0
    for i in range(max_scrolls):
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(1.5)
        # Try clicking load-more buttons
        for btn_text in ["Load More", "Show More", "Load more", "Show more"]:
            try:
                btn = page.locator(f"button:has-text('{btn_text}'), a:has-text('{btn_text}')").first
                if btn.is_visible(timeout=500):
                    btn.click()
                    time.sleep(2)
                    stable = 0
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


def _extract_covers_from_listing(page, genre_name):
    """
    Extract cover entries from a listing page using images (proven approach).
    For each image, also try to get the parent <a> href as a detail page URL.
    """
    entries = []
    images = page.query_selector_all("img")

    for img in images:
        try:
            src = img.get_attribute("src") or img.get_attribute("data-src") or ""
            alt = img.get_attribute("alt") or ""

            if not _is_real_cover_image(src, alt):
                continue

            # Skip tiny images (icons, buttons)
            width = img.get_attribute("width")
            height = img.get_attribute("height")
            if width and width.isdigit() and int(width) < 80:
                continue
            if height and height.isdigit() and int(height) < 80:
                continue

            image_url = _make_absolute(src)

            # Try to find the parent <a> link (detail page URL)
            detail_url = ""
            try:
                href = img.evaluate(
                    "el => { const a = el.closest('a'); return a ? a.href : ''; }"
                )
                if href:
                    href = _make_absolute(href)
                    if _is_detail_page_url(href):
                        detail_url = href.rstrip("/") + "/"
            except Exception:
                pass

            # Also check if the image itself is wrapped in an onclick or data attr
            if not detail_url:
                try:
                    data_link = img.get_attribute("data-link") or img.get_attribute("data-href") or ""
                    if data_link:
                        data_link = _make_absolute(data_link)
                        if _is_detail_page_url(data_link):
                            detail_url = data_link.rstrip("/") + "/"
                except Exception:
                    pass

            entries.append({
                "image_url": image_url,
                "detail_url": detail_url,
                "alt_text": alt.strip(),
                "genre": genre_name,
            })
        except Exception:
            continue

    return entries


def _parse_title_designer_from_meta(page):
    """
    Page titles on ineedabookcover.com follow patterns like:
      "Tyler Comrie's design for 'Carnality' by Lina Wolff"
      "Chip Kidd's design for "Dry" by Augusten Burroughs"
      "Keith Hayes' design for "The Goldfinch" by Donna Tartt"
      "Blink | I Need a Book Cover"
      "Lapvona cover art | I Need a Book Cover"
      "Big Swiss book cover information from INeedABookCover.com"
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
    m = re.match(
        r"""^(.+?)(?:'s|'s|\u2019s)\s+design\s+for\s+[\"'"'\u201c\u201d](.+?)[\"'"'\u201c\u201d](?:\s+by\s+(.+?))?(?:\s*\||\s*–|\s*-|\s*$)""",
        title_tag, re.IGNORECASE
    )
    if m:
        designer = m.group(1).strip()
        book_title = m.group(2).strip()
        author = (m.group(3) or "").strip()
        author = re.sub(r"\s*\|.*$", "", author).strip()
        author = re.sub(r"\s*–.*$", "", author).strip()
        return book_title, designer, author

    # Pattern: "Title | I Need a Book Cover"
    m = re.match(r"^(.+?)\s*\|\s*I Need a Book Cover", title_tag, re.IGNORECASE)
    if m:
        book_title = m.group(1).strip()
        # Remove suffixes like "cover art", "book cover information"
        book_title = re.sub(r"\s+(?:cover art|book cover.*)", "", book_title, flags=re.IGNORECASE).strip()

    # Pattern: "Title book cover information from INeedABookCover.com"
    if not book_title:
        m = re.match(r"^(.+?)\s+(?:cover art|book cover|information)\s+", title_tag, re.IGNORECASE)
        if m:
            book_title = m.group(1).strip()

    return book_title, designer, author


def _scrape_detail_page(page, url):
    """Visit an individual cover page and extract designer, title, author, genre."""
    try:
        page.goto(url, timeout=25000)
        page.wait_for_load_state("domcontentloaded", timeout=10000)
        time.sleep(1)
    except Exception as e:
        return None

    result = {"title": "", "designer": "", "author": "", "genre": "", "image_url": ""}

    # --- 1. Parse <title> tag (most reliable for designer) ---
    title_text, designer, author = _parse_title_designer_from_meta(page)
    result["designer"] = designer
    result["author"] = author
    if title_text:
        result["title"] = title_text

    # --- 2. Get <h1> for the book name ---
    try:
        h1 = page.locator("h1").first
        if h1.is_visible(timeout=1000):
            h1_text = h1.inner_text().strip()
            if h1_text and h1_text.lower() not in JUNK_TITLES:
                result["title"] = h1_text
    except Exception:
        pass

    # --- 3. Get main cover image ---
    try:
        images = page.query_selector_all("img")
        best_img = None
        best_area = 0
        for img in images:
            src = img.get_attribute("src") or img.get_attribute("data-src") or ""
            if not _is_real_cover_image(src):
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
            result["image_url"] = _make_absolute(best_img)
    except Exception:
        pass

    # --- 4. Extract designer from body text if not in title ---
    if not result["designer"]:
        try:
            body_text = page.inner_text("body")
            for pattern in [
                r"(?:Cover\s+)?[Dd]esign(?:er|ed)?\s*(?:by|:)\s*([A-Z][A-Za-z\s\.\-''\u2019]+?)(?:\n|\.|,|\||–|—|\(|$)",
                r"[Aa]rt\s+(?:[Dd]irection|[Dd]irector)\s*(?:by|:)\s*([A-Z][A-Za-z\s\.\-''\u2019]+?)(?:\n|\.|,|\||–|—|\(|$)",
                r"[Jj]acket\s+(?:design|art)\s*(?:by|:)\s*([A-Z][A-Za-z\s\.\-''\u2019]+?)(?:\n|\.|,|\||–|—|\(|$)",
            ]:
                m = re.search(pattern, body_text)
                if m:
                    name = m.group(1).strip().rstrip(".,;:")
                    if 2 < len(name) < 50 and not any(w in name.lower() for w in [
                        "book", "cover", "genre", "price", "cart", "publish",
                        "page", "print", "copyright", "edition", "click",
                    ]):
                        result["designer"] = name
                        break
        except Exception:
            pass

    # --- 5. Extract designer from links to /designers/ profile pages ---
    if not result["designer"]:
        try:
            designer_links = page.locator("a[href*='/designers/']").all()
            for link in designer_links:
                try:
                    text = link.inner_text().strip()
                    href = link.get_attribute("href") or ""
                    # Must be an individual designer page, not the directory
                    if (text and 2 < len(text) < 50 and
                            re.search(r"/designers/[a-z0-9]", href) and
                            text.lower() not in ("designers", "book cover designers", "all designers")):
                        result["designer"] = text
                        break
                except Exception:
                    continue
        except Exception:
            pass

    # --- 6. Extract genre from links ---
    try:
        genre_links = page.locator("a[href*='_genre=']").all()
        for el in genre_links:
            try:
                text = el.inner_text().strip()
                if text and text.lower() not in ("home", "book covers", "covers", "all", "") and len(text) < 40:
                    result["genre"] = text
                    break
            except Exception:
                continue
    except Exception:
        pass

    return result


def scrape():
    os.makedirs(SEED_DIR, exist_ok=True)
    all_covers = []
    seen_images = set()
    listing_entries = []

    print("=" * 60)
    print("  Scraping ineedabookcover.com")
    print("  Phase 1: Finding cover images on listing pages")
    print("=" * 60)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-gpu"])
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            viewport={"width": 1440, "height": 900},
        )
        page = context.new_page()

        # Phase 1: Find all cover images and their detail page links
        for genre_path in GENRE_PAGES:
            genre_name = genre_path.split("=")[-1].replace("-", " ").title() if "=" in genre_path else ""
            display_name = genre_name or "all"
            print(f"\n  Scanning {display_name}...")

            try:
                page.goto(BASE_URL + genre_path, timeout=30000)
                page.wait_for_load_state("networkidle", timeout=15000)
            except Exception as e:
                print(f"    [ERROR] {e}")
                continue

            _scroll_and_load(page)
            entries = _extract_covers_from_listing(page, genre_name)

            new_count = 0
            for entry in entries:
                if entry["image_url"] not in seen_images:
                    seen_images.add(entry["image_url"])
                    listing_entries.append(entry)
                    new_count += 1

            detail_count = sum(1 for e in entries if e["detail_url"] and e["image_url"] in seen_images)
            print(f"    -> {new_count} new images found, {detail_count} with detail page links (total: {len(listing_entries)})")
            time.sleep(1)

        # Collect unique detail page URLs to visit
        detail_urls = {}
        for entry in listing_entries:
            if entry["detail_url"] and entry["detail_url"] not in detail_urls:
                detail_urls[entry["detail_url"]] = entry

        # Also scan ALL <a> tags from the last loaded page for any missed links
        try:
            all_anchors = page.query_selector_all("a[href]")
            for a in all_anchors:
                try:
                    href = _make_absolute(a.get_attribute("href") or "")
                    if _is_detail_page_url(href):
                        url = href.rstrip("/") + "/"
                        if url not in detail_urls:
                            detail_urls[url] = None
                except Exception:
                    pass
        except Exception:
            pass

        print(f"\n{'=' * 60}")
        print(f"  Phase 1 complete: {len(listing_entries)} cover images found")
        print(f"  Detail pages to visit: {len(detail_urls)}")
        print(f"{'=' * 60}")

        # Phase 2: Visit detail pages to get designer info
        if detail_urls:
            print(f"\n  Phase 2: Scraping {len(detail_urls)} detail pages for designer info...")
            print(f"  (est. {len(detail_urls) // 2} minutes)")

            detail_data = {}
            sorted_urls = sorted(detail_urls.keys())

            for i, url in enumerate(sorted_urls):
                if (i + 1) % 50 == 0 or i == 0:
                    designers_so_far = sum(1 for d in detail_data.values() if d and d.get("designer"))
                    print(f"    [{i + 1}/{len(sorted_urls)}] {designers_so_far} designers found so far...")

                data = _scrape_detail_page(page, url)
                if data:
                    detail_data[url] = data

                time.sleep(0.5)

            print(f"    Done. Got data from {len(detail_data)} detail pages.")
        else:
            detail_data = {}
            print("\n  No detail pages found — covers will be saved without designer info.")

        browser.close()

    # Phase 3: Merge listing entries with detail page data
    print(f"\n  Phase 3: Merging data...")

    for entry in listing_entries:
        detail_url = entry.get("detail_url", "")
        detail = detail_data.get(detail_url, {}) if detail_url else {}

        # Use detail page image if available (usually higher quality)
        image_url = detail.get("image_url") or entry["image_url"]

        # Title: prefer detail page, fall back to alt text, then slug from URL
        title = detail.get("title", "")
        if not title:
            alt = entry.get("alt_text", "")
            if alt and alt.lower() not in JUNK_TITLES:
                title = alt
        if not title and detail_url:
            slug = detail_url.rstrip("/").split("/")[-1]
            title = slug.replace("-", " ").title()
        if not title:
            continue
        if title.lower().strip() in JUNK_TITLES:
            continue

        cover = {
            "title": title,
            "designer": detail.get("designer", ""),
            "author": detail.get("author", ""),
            "genre": detail.get("genre", "") or entry.get("genre", ""),
            "image_url": image_url,
            "source_url": detail_url or "",
            "source": "I Need a Book Cover",
        }
        all_covers.append(cover)

    # Save
    with open(SEED_FILE, "w") as f:
        json.dump(all_covers, f, indent=2)

    designers_found = sum(1 for c in all_covers if c.get("designer"))
    with_detail = sum(1 for c in all_covers if c.get("source_url"))
    print(f"\n{'=' * 60}")
    print(f"  Done! Saved {len(all_covers)} covers to {SEED_FILE}")
    print(f"  With designer data:  {designers_found}/{len(all_covers)}")
    print(f"  With detail page:    {with_detail}/{len(all_covers)}")
    print(f"")
    print(f"  Next steps:")
    print(f"    git add data/covers_seed.json")
    print(f"    git commit -m 'Update seed data with designer names'")
    print(f"    git push")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    scrape()
