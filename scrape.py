#!/usr/bin/env python3
"""Run scraper to populate the database with book covers from ineedabookcover.com."""
from database import init_db, get_cover_count
from scrapers.ineedabookcover import scrape_ineedabookcover

init_db()

existing = get_cover_count()
if existing > 0:
    print(f"Database already has {existing} covers — skipping scrape.")
    raise SystemExit(0)

print("=" * 60)
print("  Book Cover Swiper - Scraper")
print("  Source: ineedabookcover.com (~3,000 curated covers)")
print("=" * 60)

print("\nScraping I Need a Book Cover (designer directory)...")
total = scrape_ineedabookcover()

print(f"\n{'=' * 60}")
print(f"  Total covers added: {total}")
print(f"{'=' * 60}")
