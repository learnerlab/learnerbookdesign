#!/usr/bin/env python3
"""
Run this LOCALLY to scrape ineedabookcover.com and save to a seed JSON file.
The seed file gets committed and deployed — no Playwright needed on Render.

Usage:
    pip install playwright && playwright install chromium
    python scrapers/scrape_local.py
"""
import json
import os
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


def _scroll_and_load(page, max_scrolls=15):
    prev_height = 0
    stable = 0
    for _ in range(max_scrolls):
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(1.5)
        for btn_text in ["Load More", "Show More"]:
            try:
                btn = page.locator(f"button:has-text('{btn_text}'), a:has-text('{btn_text}')").first
                if btn.is_visible():
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


def _extract_covers(page):
    covers = []
    images = page.query_selector_all("img")
    for img in images:
        try:
            src = img.get_attribute("src") or img.get_attribute("data-src") or ""
            alt = img.get_attribute("alt") or ""
            width = img.get_attribute("width")
            if width and width.isdigit() and int(width) < 100:
                continue
            if not src or "logo" in src.lower() or "icon" in src.lower():
                continue
            if not alt or len(alt) < 3:
                continue
            # Try to find parent link
            source_url = ""
            parent = img.evaluate_handle("el => el.closest('a')")
            if parent:
                try:
                    href = parent.get_attribute("href")
                    if href:
                        source_url = _make_absolute(href)
                except Exception:
                    pass
            covers.append({
                "title": alt.strip(),
                "image_url": _make_absolute(src),
                "source_url": source_url or page.url,
            })
        except Exception:
            continue
    return covers


def scrape():
    os.makedirs(SEED_DIR, exist_ok=True)
    all_covers = []
    seen_urls = set()

    print("=" * 60)
    print("  Scraping ineedabookcover.com (local)")
    print("=" * 60)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-gpu"])
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            viewport={"width": 1440, "height": 900},
        )
        page = context.new_page()

        for genre_path in GENRE_PAGES:
            genre_name = genre_path.split("=")[-1] if "=" in genre_path else "all"
            print(f"\n  Scraping {genre_name}...")

            try:
                page.goto(BASE_URL + genre_path, timeout=30000)
                page.wait_for_load_state("networkidle", timeout=15000)
            except Exception as e:
                print(f"    [ERROR] {e}")
                continue

            _scroll_and_load(page)
            covers = _extract_covers(page)

            added = 0
            for c in covers:
                if c["image_url"] not in seen_urls:
                    seen_urls.add(c["image_url"])
                    c["genre"] = genre_name.replace("-", " ").title() if genre_name != "all" else ""
                    c["author"] = ""
                    c["designer"] = ""
                    c["source"] = "I Need a Book Cover"
                    all_covers.append(c)
                    added += 1

            print(f"    -> {added} new covers (total: {len(all_covers)})")
            time.sleep(2)

        browser.close()

    with open(SEED_FILE, "w") as f:
        json.dump(all_covers, f, indent=2)

    print(f"\n{'=' * 60}")
    print(f"  Saved {len(all_covers)} covers to {SEED_FILE}")
    print(f"  Commit this file and deploy to Render.")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    scrape()
