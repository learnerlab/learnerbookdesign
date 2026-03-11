"""
Scraper for ineedabookcover.com — a curated directory of ~3,000 book covers
with designer credits. Requires Playwright (headless browser) because the
site blocks raw HTTP requests.

Install: pip install playwright && playwright install chromium

On Render: The build.sh script handles Chromium installation.
Chromium runs with --no-sandbox in containerized environments.
"""
import os
import subprocess
import time
import sys

# Ensure Playwright can find browsers installed by build.sh on Render.
# Also store browsers under the project dir so they persist across deploys.
_RENDER_PW_PATH = "/opt/render/project/.playwright"
if not os.environ.get("PLAYWRIGHT_BROWSERS_PATH"):
    if os.path.isdir(_RENDER_PW_PATH):
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = _RENDER_PW_PATH
    elif os.path.isdir("/opt/render"):
        # We're on Render but browsers haven't been installed yet
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = _RENDER_PW_PATH

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None


def _ensure_chromium_installed():
    """Install Chromium if it's missing. Needed when build.sh wasn't used."""
    pw_path = os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "")
    # Check if any chromium directory exists under the browsers path
    if pw_path and os.path.isdir(pw_path):
        entries = os.listdir(pw_path)
        if any("chromium" in e for e in entries):
            return True  # Already installed

    print("  [INFO] Chromium not found — installing now (one-time)...")
    try:
        result = subprocess.run(
            ["playwright", "install", "--with-deps", "chromium"],
            capture_output=True, text=True, timeout=300,
        )
        if result.returncode == 0:
            print("  [INFO] Chromium installed successfully.")
            return True
        else:
            print(f"  [ERROR] Chromium install failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"  [ERROR] Could not install Chromium: {e}")
        return False

from database import add_cover

BASE_URL = "https://ineedabookcover.com"
COVERS_URL = f"{BASE_URL}/book-covers/"

# Genre/category pages to scrape — the site uses these URL patterns
GENRE_PAGES = [
    # Main gallery (all covers)
    "/book-covers/",
    # Genre-specific pages (common URL patterns on the site)
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


def _extract_covers_from_page(page):
    """Extract cover data from the current Playwright page.

    Tries multiple CSS selector strategies to handle different page layouts.
    """
    covers = []

    # Strategy 1: Look for common WordPress gallery/grid item patterns
    # The site likely uses a grid of cover cards with images and metadata
    selectors_to_try = [
        # WordPress post/entry patterns
        "article", ".post", ".entry",
        # Gallery/grid patterns
        ".book-cover", ".cover-item", ".cover-card",
        ".gallery-item", ".grid-item", ".portfolio-item",
        # WooCommerce product patterns (some cover sites use this)
        ".product", ".woocommerce-loop-product",
        # Generic card/item patterns
        ".item", ".card",
        # Jetpack/WordPress tiled gallery
        ".tiled-gallery-item",
    ]

    # Find which selector matches actual cover items
    best_selector = None
    best_count = 0

    for selector in selectors_to_try:
        try:
            count = page.locator(selector).count()
            if count > best_count:
                best_count = count
                best_selector = selector
        except Exception:
            continue

    if not best_selector or best_count == 0:
        # Fallback: just grab all images that look like book covers
        # (large images, not icons/logos)
        images = page.query_selector_all("img")
        for img in images:
            try:
                src = img.get_attribute("src") or img.get_attribute("data-src") or ""
                alt = img.get_attribute("alt") or ""
                width = img.get_attribute("width")

                # Skip tiny images (icons, logos, spacers)
                if width and int(width) < 100:
                    continue
                if not src or "logo" in src.lower() or "icon" in src.lower():
                    continue
                # Skip if no meaningful alt text
                if not alt or len(alt) < 3:
                    continue

                covers.append({
                    "title": alt.strip(),
                    "author": "",
                    "designer": "",
                    "image_url": _make_absolute(src),
                    "source_url": page.url,
                    "genre": "",
                })
            except Exception:
                continue
        return covers

    # Extract data from matched elements
    elements = page.query_selector_all(best_selector)
    for el in elements:
        try:
            # Find the cover image
            img = el.query_selector("img")
            if not img:
                continue

            src = img.get_attribute("src") or img.get_attribute("data-src") or ""
            if not src or "logo" in src.lower() or "icon" in src.lower():
                continue

            # Title: try heading, then link text, then img alt
            title = ""
            for title_sel in ["h2", "h3", "h4", ".title", ".book-title", ".entry-title"]:
                title_el = el.query_selector(title_sel)
                if title_el:
                    title = title_el.inner_text().strip()
                    break
            if not title:
                title = (img.get_attribute("alt") or "").strip()
            if not title:
                # Try link text
                link = el.query_selector("a")
                if link:
                    title = link.get_attribute("title") or ""
            if not title:
                continue

            # Designer credit
            designer = ""
            for des_sel in [".designer", ".credit", ".author-name", ".meta",
                            '[class*="designer"]', '[class*="credit"]']:
                des_el = el.query_selector(des_sel)
                if des_el:
                    designer = des_el.inner_text().strip()
                    # Clean up common prefixes
                    for prefix in ["Design by ", "Designed by ", "Cover by ",
                                   "Designer: ", "Cover design: "]:
                        if designer.startswith(prefix):
                            designer = designer[len(prefix):]
                    break

            # Author
            author = ""
            for auth_sel in [".author", ".book-author", '[class*="author"]']:
                auth_el = el.query_selector(auth_sel)
                if auth_el:
                    author = auth_el.inner_text().strip()
                    for prefix in ["by ", "By ", "Author: "]:
                        if author.startswith(prefix):
                            author = author[len(prefix):]
                    break

            # Source URL (link to detail page)
            source_url = ""
            link = el.query_selector("a")
            if link:
                href = link.get_attribute("href") or ""
                source_url = _make_absolute(href)

            # Genre from category/tag elements
            genre = ""
            for genre_sel in [".category", ".genre", ".tag", '[class*="genre"]',
                              '[class*="category"]']:
                genre_el = el.query_selector(genre_sel)
                if genre_el:
                    genre = genre_el.inner_text().strip()
                    break

            covers.append({
                "title": title,
                "author": author,
                "designer": designer,
                "image_url": _make_absolute(src),
                "source_url": source_url or page.url,
                "genre": genre,
            })
        except Exception:
            continue

    return covers


def _make_absolute(url):
    """Convert relative URLs to absolute."""
    if not url:
        return ""
    if url.startswith("//"):
        return "https:" + url
    if url.startswith("/"):
        return BASE_URL + url
    if not url.startswith("http"):
        return BASE_URL + "/" + url
    return url


def _scroll_to_load_all(page, max_scrolls=50):
    """Scroll down to trigger infinite scroll / lazy loading."""
    prev_height = 0
    stable_count = 0

    for i in range(max_scrolls):
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(1.5)

        # Check for "Load More" buttons and click them
        for btn_sel in ["button.load-more", ".load-more", "a.load-more",
                        "#load-more", '[class*="load-more"]',
                        "button:has-text('Load More')",
                        "button:has-text('Show More')",
                        "a:has-text('Load More')"]:
            try:
                btn = page.locator(btn_sel).first
                if btn.is_visible():
                    btn.click()
                    time.sleep(2)
            except Exception:
                continue

        cur_height = page.evaluate("document.body.scrollHeight")
        if cur_height == prev_height:
            stable_count += 1
            if stable_count >= 3:
                break
        else:
            stable_count = 0
        prev_height = cur_height


def _scrape_paginated(page, base_url, max_pages=20):
    """Handle traditional pagination (page/2/, page/3/, etc.)."""
    all_covers = []
    seen_urls = set()

    for page_num in range(1, max_pages + 1):
        if page_num == 1:
            url = base_url
        else:
            # Try common WordPress pagination patterns
            sep = "&" if "?" in base_url else "?"
            url = f"{base_url}{sep}paged={page_num}"

        try:
            page.goto(url, timeout=20000)
            page.wait_for_load_state("networkidle", timeout=10000)
        except Exception:
            break

        # Scroll to load lazy images
        _scroll_to_load_all(page, max_scrolls=5)

        covers = _extract_covers_from_page(page)
        if not covers:
            break

        # Deduplicate within this run
        new_covers = []
        for c in covers:
            if c["image_url"] not in seen_urls:
                seen_urls.add(c["image_url"])
                new_covers.append(c)

        if not new_covers:
            break

        all_covers.extend(new_covers)
        print(f"    Page {page_num}: found {len(new_covers)} covers "
              f"(total: {len(all_covers)})")
        time.sleep(2)

    return all_covers


def scrape_ineedabookcover(max_pages_per_genre=10):
    """Scrape book covers from ineedabookcover.com using Playwright.

    Returns the number of covers added to the database.
    """
    if sync_playwright is None:
        print("  [SKIP] Playwright not installed. "
              "Install with: pip install playwright && playwright install chromium")
        return 0

    if not _ensure_chromium_installed():
        return 0

    total = 0

    try:
        with sync_playwright() as p:
            # --no-sandbox is required in containerized environments (Render,
            # Docker) where Chrome can't create its sandbox namespace.
            # --disable-gpu avoids GPU-related crashes on headless servers.
            launch_args = ["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"]

            # Use PLAYWRIGHT_CHROMIUM_PATH if set, otherwise let Playwright find it
            executable = os.environ.get("PLAYWRIGHT_CHROMIUM_PATH")

            browser = p.chromium.launch(
                headless=True,
                args=launch_args,
                executable_path=executable,
            )
            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/131.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1440, "height": 900},
            )
            page = context.new_page()

            seen_images = set()

            def _store_covers(covers, genre_override=None):
                """Save a batch of covers to DB immediately. Returns count added."""
                nonlocal total
                added = 0
                for cover in covers:
                    if cover["image_url"] in seen_images:
                        continue
                    seen_images.add(cover["image_url"])
                    genre = cover["genre"] or genre_override or ""
                    result = add_cover(
                        title=cover["title"],
                        author=cover["author"],
                        designer=cover["designer"],
                        genre=genre,
                        image_url=cover["image_url"],
                        source="I Need a Book Cover",
                        source_url=cover["source_url"],
                    )
                    if result:
                        added += 1
                        total += 1
                return added

            # Scrape all genre pages (including main gallery)
            for genre_path in GENRE_PAGES:
                genre_name = genre_path.split("=")[-1] if "=" in genre_path else "all"
                print(f"  Scraping {genre_name}...")

                genre_url = BASE_URL + genre_path
                try:
                    page.goto(genre_url, timeout=30000)
                    page.wait_for_load_state("networkidle", timeout=15000)
                except Exception as e:
                    print(f"    [ERROR] Could not load {genre_name}: {e}")
                    continue

                # Scroll to load lazy images (limited scrolls per page)
                _scroll_to_load_all(page, max_scrolls=10)
                covers = _extract_covers_from_page(page)
                added = _store_covers(
                    covers,
                    genre_override=genre_name.replace("-", " ").title() if genre_name != "all" else None,
                )
                print(f"    -> {added} new covers (total: {total})")

                # Also follow pagination for this genre
                paginated = _scrape_paginated(page, genre_url, max_pages=max_pages_per_genre)
                added = _store_covers(
                    paginated,
                    genre_override=genre_name.replace("-", " ").title() if genre_name != "all" else None,
                )
                if added:
                    print(f"    -> {added} more from pagination (total: {total})")

                time.sleep(1)

            browser.close()

    except Exception as e:
        print(f"  [ERROR] Scraper failed: {e}")
        # Common Render issue: Chromium binary not found
        if "Executable doesn't exist" in str(e):
            print("  [HINT] Chromium not installed. On Render, make sure "
                  "build.sh runs: playwright install --with-deps chromium")
            print(f"  [HINT] PLAYWRIGHT_BROWSERS_PATH = "
                  f"{os.environ.get('PLAYWRIGHT_BROWSERS_PATH', '(not set)')}")

    return total
