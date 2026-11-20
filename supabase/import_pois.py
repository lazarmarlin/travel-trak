#!/usr/bin/env python3
"""
Import Travel Trak CSVs into Supabase pois table.
Requires: pip install supabase
Set SUPABASE_URL and SUPABASE_SERVICE_KEY env vars (use service role key).
"""
import os
import csv
import sys
from pathlib import Path

try:
    from supabase import create_client
except ImportError:
    print("Install: pip install supabase")
    sys.exit(1)

URL = os.environ.get("SUPABASE_URL", "https://nwptxncvixkfapbizdgg.supabase.co")
KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")  # service role key

if not KEY:
    print("Set SUPABASE_SERVICE_KEY environment variable")
    sys.exit(1)

sb = create_client(URL, KEY)
BASE = Path(__file__).parent.parent / "data" / "processed"

def import_csv(path, category_map=None, points_default=25):
    path = Path(path)
    if not path.exists():
        print(f"  Skip (missing): {path}")
        return 0
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            name = r.get("name") or r.get("landmark") or r.get("brand") or r.get("high_point")
            if not name:
                continue
            state = r.get("state", "")
            cat = category_map(r) if category_map else r.get("poi_type") or r.get("category") or "other"
            poi_id = f"{state.lower()}-{name.lower().replace(' ', '-')[:40]}" if state else name.lower().replace(" ", "-")[:50]
            rows.append({
                "id": poi_id,
                "name": name,
                "category": cat,
                "subcategory": r.get("poi_type") or r.get("category") or "",
                "state": state,
                "lat": float(r["lat"]) if r.get("lat") else None,
                "lon": float(r["lon"]) if r.get("lon") else None,
                "points": int(r.get("points") or points_default),
                "source": "csv",
                "source_id": r.get("osm_id") or "",
            })
    if not rows:
        return 0
    for i in range(0, len(rows), 100):
        batch = rows[i:i+100]
        sb.table("pois").upsert(batch).execute()
    print(f"  Imported {len(rows)} from {path.name}")
    return len(rows)

def main():
    total = 0
    print("Importing parks...")
    parks_dir = BASE / "parks"
    if parks_dir.exists():
        for p in sorted(parks_dir.glob("*_parks.csv")):
            total += import_csv(p, points_default=50)

    print("Importing landmarks...")
    total += import_csv(BASE / "iconic_landmarks.csv",
                        category_map=lambda r: "landmark",
                        points_default=25)

    print("Importing restaurants...")
    total += import_csv(BASE / "regional_restaurants.csv",
                        category_map=lambda r: "food",
                        points_default=20)

    print("Importing high points...")
    total += import_csv(BASE / "parks" / "state_high_points.csv",
                        category_map=lambda r: "landmark",
                        points_default=50)

    print(f"\nDone. Total POIs upserted: {total}")

if __name__ == "__main__":
    main()
