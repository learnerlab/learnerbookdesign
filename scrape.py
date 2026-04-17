#!/usr/bin/env python3
"""Populate the database with book covers.

Only runs the seed loader if the DB hasn't already been fully loaded.
Compares cover count against seed file size — if DB has >= seed count,
the previous load finished successfully and we skip (fast boot).
Otherwise, runs upsert to load/finish the import.

To force a full re-import, set FORCE_RESEED=true.
"""
import os
import json
from database import init_db, get_cover_count, wipe_all_data
from scrapers.seed_loader import load_seed_covers, SEED_FILE
from scrapers.openlibrary import scrape_openlibrary

init_db()

print("=" * 60)
print("  Book Cover Swiper - Loading Covers")
print("=" * 60)

# Wipe everything if requested (set WIPE_DATA=true on Render once, then remove)
if os.environ.get("WIPE_DATA", "").lower() in ("1", "true", "yes"):
    print("\n[!] WIPE_DATA=true — deleting ALL swipes and covers...")
    swipes, covers = wipe_all_data()
    print(f"    Deleted {swipes} swipes and {covers} covers.")
    print("    Remove the WIPE_DATA env var after this deploy to avoid re-wiping.")

cover_count = get_cover_count()
print(f"\nDatabase currently has {cover_count} covers")

# Count how many covers are in the seed file
seed_count = 0
seed_path = os.path.normpath(SEED_FILE)
if os.path.exists(seed_path):
    try:
        with open(seed_path) as f:
            seed_count = len(json.load(f))
    except Exception as e:
        print(f"Could not read seed file: {e}")

force = os.environ.get("FORCE_RESEED", "").lower() in ("1", "true", "yes")

if force:
    print("FORCE_RESEED set — running upsert regardless of current state")
    load_seed_covers()
elif seed_count > 0 and cover_count >= seed_count:
    print(f"DB already has {cover_count} covers (seed has {seed_count}). Skipping import.")
    print("Set FORCE_RESEED=true to re-import the seed file.")
elif seed_count > 0:
    print(f"Seed has {seed_count} covers, DB has {cover_count} — loading seed...")
    load_seed_covers()
elif cover_count == 0:
    print("\nNo seed data found and DB is empty. Fetching from Open Library API...")
    scrape_openlibrary()
else:
    print("No seed file and DB already populated. Nothing to do.")

final = get_cover_count()
print(f"\n{'=' * 60}")
print(f"  Covers in DB: {final}")
print(f"{'=' * 60}")
