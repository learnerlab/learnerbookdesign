#!/usr/bin/env python3
"""Populate the database with book covers.

Always runs the seed loader in upsert mode — inserts new covers and
backfills designer/title/etc. on existing covers. User swipes are preserved.

Falls back to Open Library API only if the seed file is missing AND
the DB has no covers yet.
"""
from database import init_db, get_cover_count
from scrapers.seed_loader import load_seed_covers
from scrapers.openlibrary import scrape_openlibrary

init_db()

print("=" * 60)
print("  Book Cover Swiper - Loading Covers")
print("=" * 60)

before = get_cover_count()
print(f"\nDatabase currently has {before} covers")

# Always upsert from seed file (preserves existing swipes, backfills data)
print("Loading seed data from ineedabookcover.com...")
processed = load_seed_covers()

after = get_cover_count()

if processed == 0 and before == 0:
    print("\nNo seed data found. Fetching from Open Library API...")
    scrape_openlibrary()
    after = get_cover_count()

print(f"\n{'=' * 60}")
print(f"  Covers in DB: {after}  (was {before})")
print(f"{'=' * 60}")
