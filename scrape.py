#!/usr/bin/env python3
"""Populate the database with book covers.

Priority:
1. Load from seed file (pre-scraped from ineedabookcover.com locally)
2. Fall back to Open Library API (no browser needed)
"""
from database import init_db, get_cover_count
from scrapers.seed_loader import load_seed_covers
from scrapers.openlibrary import scrape_openlibrary

init_db()

existing = get_cover_count()
if existing > 0:
    print(f"Database already has {existing} covers — skipping scrape.")
    raise SystemExit(0)

print("=" * 60)
print("  Book Cover Swiper - Loading Covers")
print("=" * 60)

# Try seed data first (from ineedabookcover.com, scraped locally)
print("\nChecking for seed data from ineedabookcover.com...")
total = load_seed_covers()

if total == 0:
    # Fall back to Open Library API
    print("\nNo seed data found. Fetching from Open Library API...")
    total = scrape_openlibrary()

print(f"\n{'=' * 60}")
print(f"  Total covers loaded: {total}")
print(f"{'=' * 60}")
