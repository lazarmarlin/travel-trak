#!/usr/bin/env python3
"""
Import all Travel Trak CSVs into Supabase pois table.
Usage:
  export SUPABASE_URL="https://nwptxncvixkfapbizdgg.supabase.co"
  export SUPABASE_SERVICE_KEY="sb_secret_..."
  python supabase/import_pois.py
"""
import os
import csv
import sys
from pathlib import Path

try:
    from supabase import create_client
except ImportError:
    print("pip install supabase")
    sys.exit(1)

URL = os.environ.get("SUPABASE_URL", "https://nwptxncvixkfapbizdgg.supabase.co")
KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
if not KEY:
    print("Set SUPABASE_SERVICE_KEY")
    sys.exit(1)

sb = create_client(URL, KEY)
BASE = Path(__file__).parent.parent / "data" / "processed"

def make_id(state, name):
    base = f"{state.lower()}-{name.lower()}" if state else name.lower()
    return base.replace(" ", "-").replace("/", "-")[:60]

def import_file(path, category, points, name_col="name", state_col="state"):
    path = Path(path)
    if not path.exists():
        print(f"  Missing: {path.name}")
        return 0
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            name = r.get(name_col) or r.get("landmark") or r.get("brand") or r.get("food")
            if not name:
                continue
            state = r.get(state_col, "")
            rows.append({
                "id": make_id(state, name),
                "name": name,
                "category": category,
                "subcategory": r.get("category") or r.get("poi_type") or "",
                "state": state,
                "lat": float(r["lat"]) if r.get("lat") else None,
                "lon": float(r["lon"]) if r.get("lon") else None,
                "points": points,
                "source": "csv",
            })
    if not rows:
        return 0
    for i in range(0, len(rows), 100):
        sb.table("pois").upsert(rows[i:i+100]).execute()
    print(f"  {len(rows):4d}  {path.name}")
    return len(rows)

def main():
    total = 0
    print("Importing...")
    total += import_file(BASE / "parks_all.csv", "park", 50)
    cats = [
        ("categories/regional_foods.csv", "food", 20, "food"),
        ("categories/regional_chains.csv", "food", 20, "brand"),
        ("categories/museums.csv", "museum", 30),
        ("categories/zoos_aquariums.csv", "zoo", 30),
        ("categories/breweries.csv", "brewery", 15),
        ("categories/historic_sites.csv", "historic", 40),
        ("categories/stadiums.csv", "stadium", 25),
        ("categories/beaches.csv", "beach", 20),
        ("categories/lighthouses.csv", "lighthouse", 20),
        ("categories/state_capitols.csv", "capitol", 30),
        ("categories/covered_bridges.csv", "bridge", 15),
        ("categories/botanical_gardens.csv", "garden", 25),
        ("categories/amusement_parks.csv", "amusement", 40),
        ("categories/wildlife_refuges.csv", "refuge", 30),
        ("iconic_landmarks.csv", "landmark", 25, "landmark"),
        ("parks/state_high_points.csv", "high_point", 50, "high_point"),
    ]
    for item in cats:
        path, cat, pts = item[0], item[1], item[2]
        name_col = item[3] if len(item) > 3 else "name"
        total += import_file(BASE / path, cat, pts, name_col)
    print(f"\nTotal upserted: {total}")

if __name__ == "__main__":
    main()
