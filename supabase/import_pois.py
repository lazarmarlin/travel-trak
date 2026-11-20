#!/usr/bin/env python3
"""
Import all Travel Trak CSVs into Supabase pois table.
Deduplicates by ID before upserting.
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
    return "".join(c if c.isalnum() or c == "-" else "-" for c in base)[:60]

def import_file(path, category, points, name_col="name", state_col="state"):
    path = Path(path)
    if not path.exists():
        print(f"  Missing: {path.name}")
        return 0
    seen = set()
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            name = r.get(name_col) or r.get("landmark") or r.get("brand") or r.get("food")
            if not name:
                continue
            state = r.get(state_col, "")
            poi_id = make_id(state, name)
            if poi_id in seen:
                continue
            seen.add(poi_id)
            rows.append({
                "id": poi_id,
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
    for p in sorted((BASE / "parks").glob("*_parks.csv")):
        total += import_file(p, "park", 50)
    items = [
        (BASE / "categories/regional_foods.csv", "food", 20, "food"),
        (BASE / "categories/regional_chains.csv", "food", 20, "brand"),
        (BASE / "categories/museums.csv", "museum", 30),
        (BASE / "categories/zoos_aquariums.csv", "zoo", 30),
        (BASE / "categories/breweries.csv", "brewery", 15),
        (BASE / "categories/historic_sites.csv", "historic", 40),
        (BASE / "categories/stadiums.csv", "stadium", 25),
        (BASE / "categories/beaches.csv", "beach", 20),
        (BASE / "categories/lighthouses.csv", "lighthouse", 20),
        (BASE / "categories/state_capitols.csv", "capitol", 30),
        (BASE / "categories/covered_bridges.csv", "bridge", 15),
        (BASE / "categories/botanical_gardens.csv", "garden", 25),
        (BASE / "categories/amusement_parks.csv", "amusement", 40),
        (BASE / "categories/wildlife_refuges.csv", "refuge", 30),
        (BASE / "iconic_landmarks.csv", "landmark", 25, "landmark"),
        (BASE / "parks/state_high_points.csv", "high_point", 50, "high_point"),
    ]
    for item in items:
        path, cat, pts = item[0], item[1], item[2]
        name_col = item[3] if len(item) > 3 else "name"
        total += import_file(path, cat, pts, name_col)
    print(f"\nTotal upserted: {total}")

if __name__ == "__main__":
    main()
