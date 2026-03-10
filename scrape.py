#!/usr/bin/env python3
"""Run scrapers to populate the database with book covers."""
import sys
from database import init_db

init_db()

print("=" * 60)
print("  Book Cover Swiper - Scraper")
print("  Focus: Modern books (2015+), nonfiction,")
print("  design-forward publishers (Penguin, Norton, Knopf)")
print("=" * 60)

sources = sys.argv[1:] if len(sys.argv) > 1 else ["bestsellers", "openlibrary"]

total = 0

if "bestsellers" in sources or "all" in sources:
    print("\n[1/3] Scraping modern bestsellers, award winners & design publishers...")
    from scrapers.bestsellers import scrape_bestsellers
    count = scrape_bestsellers()
    print(f"  -> Added {count} covers from modern bestsellers & publishers")
    total += count

if "openlibrary" in sources or "all" in sources:
    print("\n[2/3] Scraping Open Library (modern nonfiction subjects, 2015+)...")
    from scrapers.open_library import scrape_all as scrape_ol
    count = scrape_ol(covers_per_subject=20)
    print(f"  -> Added {count} covers from Open Library")
    total += count

if "archive" in sources or "all" in sources:
    print("\n[3/3] Scraping Book Cover Archive...")
    from scrapers.book_cover_archive import scrape_all as scrape_bca
    count = scrape_bca()
    print(f"  -> Added {count} covers from Book Cover Archive")
    total += count

print(f"\n{'=' * 60}")
print(f"  Total covers added: {total}")
print(f"{'=' * 60}")
print("\nRun the app with: python app.py")
