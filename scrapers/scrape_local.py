#!/usr/bin/env python3
"""
Run this LOCALLY to scrape ineedabookcover.com and save to a seed JSON file.

Strategy: Scrape designer profile pages instead of the /book-covers/ listing.
Each designer's page lists their covers, so designer attribution is
built-in (no need to visit each detail page separately).

Phase 1: Get list of all designer URLs from /designers/
Phase 2: Visit each designer's profile page, extract their covers
Phase 3 (optional): Also scrape /book-covers/ listings for additional covers
        where we can find detail page links

Usage:
    pip install playwright && playwright install chromium
    python scrapers/scrape_local.py

Options (edit at top of file):
    DEBUG_DOM = True    # Dumps DOM structure for first few items so you can
                          see what's actually there if things break
    HEADLESS = True     # Set False to watch what the browser is doing
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

# ─── Options ──────────────────────────────────────────────────────────
DEBUG_DOM = True
HEADLESS = True
MAX_DESIGNERS = None  # set to int for testing, e.g. 5
# ──────────────────────────────────────────────────────────────────────

BASE_URL = "https://ineedabookcover.com"
SEED_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
SEED_FILE = os.path.join(SEED_DIR, "covers_seed.json")

DESIGNERS_URL = "/designers/"

JUNK_TITLES = {
    "fiction", "nonfiction", "non-fiction", "literary fiction", "art",
    "biography", "memoir", "self-help", "fantasy", "thriller", "mystery",
    "romance", "science fiction", "sci-fi", "horror", "poetry", "history",
    "food", "children", "young adult", "ya", "social science",
    "all", "home", "book covers", "covers", "i need a book cover",
    "designers", "book cover designers", "about", "blog", "submit",
    "red", "orange", "yellow", "green", "blue", "purple", "pink",
    "black", "white", "brown", "grey", "gray",
}


def _abs(url):
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
    if not url:
        return False
    m = re.match(r"https?://(?:www\.)?ineedabookcover\.com/book-covers/([^/?#]+)/?$", url)
    if not m:
        return False
    slug = m.group(1)
    if slug.lower() in JUNK_TITLES:
        return False
    if re.match(r"^colors?-filter", slug, re.IGNORECASE):
        return False
    if re.match(r"^\d+-book-morph", slug, re.IGNORECASE):
        return False
    return True


def _is_designer_profile_url(url):
    if not url:
        return False
    m = re.match(r"https?://(?:www\.)?ineedabookcover\.com/designers/([^/?#]+)/?$", url)
    if not m:
        return False
    slug = m.group(1)
    if slug.lower() in ("", "all", "index"):
        return False
    return True


def _scroll_and_load(page, max_scrolls=30, label=""):
    """Aggressive scroll + click Load More until page stops growing."""
    prev_height = 0
    stable = 0
    for i in range(max_scrolls):
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(1.5)
        for btn_text in ["Load More", "Show More", "Load more", "Show more", "View More"]:
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


def _debug_dump_dom(page, label, sample_count=3):
    """Print DOM structure of a few cover-ish elements so we can see
    what the page actually looks like if parsing fails."""
    if not DEBUG_DOM:
        return

    print(f"\n  ── DEBUG DOM DUMP: {label} ──")

    # Count anchor tags pointing to book-covers pages
    try:
        all_anchors = page.query_selector_all("a[href]")
        book_cover_links = []
        designer_links = []
        for a in all_anchors:
            href = _abs(a.get_attribute("href") or "")
            if _is_detail_page_url(href):
                book_cover_links.append(href)
            elif _is_designer_profile_url(href):
                designer_links.append(href)
        print(f"    Total <a> tags: {len(all_anchors)}")
        print(f"    Links to /book-covers/<slug>/: {len(set(book_cover_links))}")
        print(f"    Links to /designers/<slug>/: {len(set(designer_links))}")
        if book_cover_links:
            print(f"    Sample cover links:")
            for u in list(set(book_cover_links))[:5]:
                print(f"      {u}")
        if designer_links:
            print(f"    Sample designer links:")
            for u in list(set(designer_links))[:5]:
                print(f"      {u}")
    except Exception as e:
        print(f"    [ERROR inspecting anchors] {e}")

    # Dump structure around first few images
    try:
        images = page.query_selector_all("img")
        real_imgs = [
            img for img in images
            if _is_real_cover_image(
                img.get_attribute("src") or img.get_attribute("data-src") or "",
                img.get_attribute("alt") or ""
            )
        ]
        print(f"    Total <img>: {len(images)}, real covers: {len(real_imgs)}")

        for i, img in enumerate(real_imgs[:sample_count]):
            outer = img.evaluate("""el => {
                const parent = el.parentElement;
                const grandparent = parent ? parent.parentElement : null;
                const closest_a = el.closest('a');
                return {
                    tag: el.tagName,
                    src: el.src || el.getAttribute('data-src'),
                    alt: el.alt,
                    parent_tag: parent ? parent.tagName : null,
                    parent_class: parent ? parent.className : null,
                    grandparent_tag: grandparent ? grandparent.tagName : null,
                    grandparent_class: grandparent ? grandparent.className : null,
                    closest_a_href: closest_a ? closest_a.href : null,
                    parent_html: parent ? parent.outerHTML.substring(0, 400) : null,
                };
            }""")
            print(f"\n    [Image {i+1}]")
            print(f"      src: {(outer['src'] or '')[:100]}")
            print(f"      alt: {outer['alt']}")
            print(f"      parent: <{outer['parent_tag']} class='{outer['parent_class']}'>")
            print(f"      grandparent: <{outer['grandparent_tag']} class='{outer['grandparent_class']}'>")
            print(f"      closest <a> href: {outer['closest_a_href']}")
            if outer['parent_html']:
                print(f"      parent outerHTML: {outer['parent_html']}")
    except Exception as e:
        print(f"    [ERROR inspecting images] {e}")

    print("  ── END DEBUG DUMP ──\n")


# ─────────────────────────────────────────────────────────────────────
# Phase 1: Get designer list
# ─────────────────────────────────────────────────────────────────────

def scrape_designer_list(page):
    """Get URLs of all individual designer profile pages."""
    print(f"\n  Fetching designer directory: {BASE_URL + DESIGNERS_URL}")
    try:
        page.goto(BASE_URL + DESIGNERS_URL, timeout=30000)
        page.wait_for_load_state("networkidle", timeout=15000)
    except Exception as e:
        print(f"  [ERROR] {e}")
        return []

    _scroll_and_load(page, label="designers directory")
    _debug_dump_dom(page, "designers directory", sample_count=2)

    designer_urls = set()
    try:
        anchors = page.query_selector_all("a[href]")
        for a in anchors:
            try:
                href = _abs(a.get_attribute("href") or "")
                if _is_designer_profile_url(href):
                    designer_urls.add(href.rstrip("/") + "/")
            except Exception:
                continue
    except Exception as e:
        print(f"  [ERROR reading anchors] {e}")

    designer_urls = sorted(designer_urls)
    print(f"  Found {len(designer_urls)} designer profile URLs")
    if designer_urls:
        print(f"  Samples:")
        for u in designer_urls[:5]:
            print(f"    {u}")
    return designer_urls


# ─────────────────────────────────────────────────────────────────────
# Phase 2: Scrape each designer page
# ─────────────────────────────────────────────────────────────────────

def scrape_designer_page(page, designer_url):
    """Visit a designer's profile page and extract all their covers."""
    try:
        page.goto(designer_url, timeout=25000)
        page.wait_for_load_state("domcontentloaded", timeout=10000)
        time.sleep(1)
    except Exception:
        return None, []

    # Get the designer name from h1 / title
    designer_name = ""
    try:
        h1 = page.locator("h1").first
        if h1.is_visible(timeout=1000):
            designer_name = h1.inner_text().strip()
    except Exception:
        pass
    if not designer_name:
        try:
            title = page.title() or ""
            # Patterns: "Jane Doe | I Need a Book Cover", "Jane Doe - Book Cover Designer"
            m = re.match(r"^(.+?)\s*[|\-–—]", title)
            if m:
                designer_name = m.group(1).strip()
                designer_name = re.sub(r"(?i)\b(book cover designer|designer)\b", "", designer_name).strip(" -\u2013\u2014")
        except Exception:
            pass

    # Derive from URL slug as last resort
    if not designer_name:
        slug = designer_url.rstrip("/").split("/")[-1]
        designer_name = slug.replace("-", " ").title()

    # Scroll to load all of this designer's covers
    _scroll_and_load(page, max_scrolls=10, label=f"designer: {designer_name}")

    # Find all cover images on this page
    covers = []
    seen_images = set()
    try:
        # First, map out all <a> tags pointing to detail pages — we'll use these
        # to associate images with detail URLs
        detail_anchors = []
        try:
            anchors = page.query_selector_all("a[href]")
            for a in anchors:
                href = _abs(a.get_attribute("href") or "")
                if _is_detail_page_url(href):
                    # Capture the anchor's bounding box and its image if any
                    info = a.evaluate("""el => {
                        const img = el.querySelector('img') || (
                            el.nextElementSibling && el.nextElementSibling.tagName === 'IMG'
                              ? el.nextElementSibling : null
                        );
                        const rect = el.getBoundingClientRect();
                        return {
                            href: el.href,
                            text: (el.innerText || '').trim().substring(0, 200),
                            img_src: img ? (img.src || img.getAttribute('data-src') || '') : '',
                            img_alt: img ? img.alt : '',
                            rect: {x: rect.left, y: rect.top, w: rect.width, h: rect.height}
                        };
                    }""")
                    detail_anchors.append(info)
        except Exception as e:
            print(f"      [warn] couldn't map anchors: {e}")

        # For each detail anchor, create a cover record
        for info in detail_anchors:
            img_src = info.get("img_src", "")
            if img_src and _is_real_cover_image(img_src, info.get("img_alt", "")):
                img_url = _abs(img_src)
                if img_url in seen_images:
                    continue
                seen_images.add(img_url)

                # Title: prefer anchor text (often the book title), then alt
                title = info.get("text", "").strip()
                if not title or title.lower() in JUNK_TITLES:
                    title = info.get("img_alt", "").strip()
                if not title or title.lower() in JUNK_TITLES:
                    # Derive from URL slug
                    slug = info["href"].rstrip("/").split("/")[-1]
                    title = slug.replace("-", " ").title()

                covers.append({
                    "title": title,
                    "designer": designer_name,
                    "image_url": img_url,
                    "source_url": info["href"].rstrip("/") + "/",
                    "source": "I Need a Book Cover",
                    "author": "",
                    "genre": "",
                })

        # Fallback: find images that weren't associated with any detail link
        # (still attribute them to this designer — we're on their page)
        images = page.query_selector_all("img")
        for img in images:
            try:
                src = img.get_attribute("src") or img.get_attribute("data-src") or ""
                alt = img.get_attribute("alt") or ""
                if not _is_real_cover_image(src, alt):
                    continue

                # Skip tiny images
                w = img.get_attribute("width")
                h = img.get_attribute("height")
                if w and w.isdigit() and int(w) < 100:
                    continue
                if h and h.isdigit() and int(h) < 100:
                    continue

                img_url = _abs(src)
                if img_url in seen_images:
                    continue
                seen_images.add(img_url)

                # Try to find a detail URL for this image
                detail_url = ""
                try:
                    detail_url = img.evaluate(
                        "el => { const a = el.closest('a'); return a && a.href ? a.href : ''; }"
                    )
                    detail_url = _abs(detail_url)
                    if not _is_detail_page_url(detail_url):
                        detail_url = ""
                except Exception:
                    pass

                title = alt.strip()
                if not title or title.lower() in JUNK_TITLES:
                    if detail_url:
                        slug = detail_url.rstrip("/").split("/")[-1]
                        title = slug.replace("-", " ").title()

                if not title or title.lower() in JUNK_TITLES:
                    continue

                covers.append({
                    "title": title,
                    "designer": designer_name,
                    "image_url": img_url,
                    "source_url": detail_url.rstrip("/") + "/" if detail_url else "",
                    "source": "I Need a Book Cover",
                    "author": "",
                    "genre": "",
                })
            except Exception:
                continue
    except Exception as e:
        print(f"    [ERROR extracting from {designer_url}] {e}")

    return designer_name, covers


# ─────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────

def scrape():
    os.makedirs(SEED_DIR, exist_ok=True)
    all_covers = []

    print("=" * 60)
    print("  Scraping ineedabookcover.com")
    print("  Source: /designers/ (every cover has designer attribution)")
    print(f"  DEBUG_DOM={DEBUG_DOM}  HEADLESS={HEADLESS}")
    print("=" * 60)

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=HEADLESS,
            args=["--no-sandbox", "--disable-gpu"]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            viewport={"width": 1440, "height": 900},
        )
        page = context.new_page()

        # Phase 1: Get list of designers
        print("\n[Phase 1] Discovering designers...")
        designer_urls = scrape_designer_list(page)

        if MAX_DESIGNERS:
            designer_urls = designer_urls[:MAX_DESIGNERS]
            print(f"  (limited to first {MAX_DESIGNERS} for testing)")

        # Phase 2: Scrape each designer's page
        print(f"\n[Phase 2] Scraping {len(designer_urls)} designer profiles...")

        seen_images = set()
        for i, url in enumerate(designer_urls):
            if (i + 1) % 10 == 0 or i == 0:
                print(f"\n  [{i + 1}/{len(designer_urls)}] {len(all_covers)} covers collected so far...")

            name, covers = scrape_designer_page(page, url)
            new_for_designer = 0
            for c in covers:
                if c["image_url"] not in seen_images:
                    seen_images.add(c["image_url"])
                    all_covers.append(c)
                    new_for_designer += 1

            if name and (i < 5 or (i + 1) % 10 == 0):
                print(f"    {name}: {new_for_designer} new covers")

            time.sleep(0.4)

        print(f"\n[Phase 2 complete] {len(all_covers)} covers from {len(designer_urls)} designers")

        browser.close()

    # Save
    with open(SEED_FILE, "w") as f:
        json.dump(all_covers, f, indent=2)

    with_designer = sum(1 for c in all_covers if c.get("designer"))
    with_detail = sum(1 for c in all_covers if c.get("source_url"))
    print(f"\n{'=' * 60}")
    print(f"  Done! Saved {len(all_covers)} covers to {SEED_FILE}")
    print(f"  With designer data:  {with_designer}/{len(all_covers)}")
    print(f"  With source URL:     {with_detail}/{len(all_covers)}")
    print(f"")
    print(f"  Next steps:")
    print(f"    git add data/covers_seed.json")
    print(f"    git commit -m 'Update seed data with designer names'")
    print(f"    git push")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    scrape()
