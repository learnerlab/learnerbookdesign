"""
Scraper for The Book Cover Archive (bookcoverarchive.com).
Features curated, high-quality book cover designs with designer credits.
"""
import requests
from bs4 import BeautifulSoup
import time
from database import add_cover

BASE_URL = "https://bookcoverarchive.com"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def scrape_page(url):
    """Scrape a single page of book covers."""
    covers = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except requests.RequestException:
        return covers

    soup = BeautifulSoup(resp.text, "lxml")

    # Look for book cover entries - the site uses various structures
    # Try common patterns for book listing sites
    for item in soup.select(".book, .cover, .entry, article, .post"):
        title_el = item.select_one("h2, h3, .title, .book-title")
        img_el = item.select_one("img")
        designer_el = item.select_one(".designer, .credit, .meta")
        author_el = item.select_one(".author, .book-author")
        link_el = item.select_one("a")

        if not img_el:
            continue

        img_src = img_el.get("src", "") or img_el.get("data-src", "")
        if not img_src:
            continue
        if img_src.startswith("/"):
            img_src = BASE_URL + img_src

        title = ""
        if title_el:
            title = title_el.get_text(strip=True)
        elif img_el.get("alt"):
            title = img_el["alt"]

        if not title:
            continue

        designer = designer_el.get_text(strip=True) if designer_el else ""
        author = author_el.get_text(strip=True) if author_el else ""
        source_url = ""
        if link_el and link_el.get("href"):
            href = link_el["href"]
            source_url = href if href.startswith("http") else BASE_URL + href

        covers.append({
            "title": title,
            "author": author,
            "designer": designer,
            "image_url": img_src,
            "source_url": source_url,
        })

    return covers


def scrape_all(max_pages=10):
    """Scrape multiple pages from Book Cover Archive."""
    total = 0

    # Try main page and paginated pages
    urls = [BASE_URL] + [f"{BASE_URL}/page/{i}" for i in range(2, max_pages + 1)]

    for url in urls:
        covers = scrape_page(url)
        for cover in covers:
            result = add_cover(
                title=cover["title"],
                author=cover["author"],
                designer=cover["designer"],
                image_url=cover["image_url"],
                source="Book Cover Archive",
                source_url=cover["source_url"],
            )
            if result:
                total += 1
        time.sleep(1)

    return total
