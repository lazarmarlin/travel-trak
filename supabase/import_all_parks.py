#!/usr/bin/env python3
"""
Import data/processed/parks/all_parks.csv into the Supabase pois table.

Usage (from the supabase/ folder):
  python3 import_all_parks.py --dry-run            # validate and summarize, touch nothing
  python3 import_all_parks.py                      # import
  python3 import_all_parks.py path/to/file.csv     # use a different file

Needs:  pip install supabase
Env:    SUPABASE_SERVICE_KEY (service role key). SUPABASE_URL is optional.

Expected columns (names are matched loosely, case-insensitive):
  state            2-letter code or full state name        required
  name             park name                               required
  poi_type         e.g. national_park, state_park, ...     optional (default "park")
  lat, lon         decimal degrees                         optional
  osm_type, osm_id OpenStreetMap reference                 optional
  county           county name                             optional

IDs use the same scheme as import_pois.py (state-name), so running both
scripts will not create duplicates. OpenStreetMap often splits one park into
several shapes, so rows with the same state and name within 5 miles are merged
into one. A same-named park farther away is kept separately, with its OSM id
appended to the id.
"""
import argparse
import csv
import os
import sys
from collections import Counter
from pathlib import Path

DEFAULT_URL = "https://nwptxncvixkfapbizdgg.supabase.co"
DEFAULT_FILE = Path(__file__).resolve().parent.parent / "data" / "processed" / "parks" / "all_parks.csv"
POINTS = 50

ALIASES = {
    "name": ["name", "park", "park_name", "park name"],
    "state": ["state", "state_abbr", "state_code", "st"],
    "poi_type": ["poi_type", "type", "park_type", "category"],
    "lat": ["lat", "latitude", "y"],
    "lon": ["lon", "lng", "long", "longitude", "x"],
    "osm_type": ["osm_type"],
    "osm_id": ["osm_id", "id"],
    "county": ["county"],
}

STATES = {"AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas", "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware", "DC": "District of Columbia", "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland", "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi", "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada", "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York", "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina", "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah", "VT": "Vermont", "VA": "Virginia", "WA": "Washington", "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming"}
BY_NAME = {v.lower(): k for k, v in STATES.items()}


def norm_state(raw):
    s = (raw or "").strip()
    if s.upper() in STATES:
        return s.upper()
    return BY_NAME.get(s.lower())


def num(raw):
    try:
        return float(str(raw).strip())
    except (TypeError, ValueError):
        return None


def decimals(raw):
    s = str(raw).strip()
    return len(s.split(".")[1]) if "." in s else 0


def miles(a, b):
    from math import asin, cos, radians, sin, sqrt
    h = sin(radians(b[0] - a[0]) / 2) ** 2 + cos(radians(a[0])) * cos(radians(b[0])) * sin(radians(b[1] - a[1]) / 2) ** 2
    return 2 * 3958.8 * asin(sqrt(h))


MERGE_MILES = 5  # same state + same name within this distance = one park split into several OSM shapes


def make_id(state, name):
    return f"{state.lower()}-{name.lower().replace(' ', '-')[:40]}"


def read_rows(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        headers = {h.strip().lower(): h for h in (reader.fieldnames or [])}
        col = {}
        for key, names in ALIASES.items():
            col[key] = next((headers[n] for n in names if n in headers), None)
        missing = [k for k in ("name", "state") if not col[k]]
        if missing:
            sys.exit(f"Missing required column(s): {', '.join(missing)}\nFound columns: {', '.join(reader.fieldnames or [])}")
        print(f"Columns matched: " + ", ".join(f"{k}={v}" for k, v in col.items() if v))
        return [{k: (r.get(v) or "").strip() if v else "" for k, v in col.items()} for r in reader]


def build(rows):
    stats = Counter()
    seen_osm, used_ids, out = set(), set(), []
    placed = {}  # (state, lowercase name) -> coordinates of parks already kept
    fake_coords = 0
    for r in sorted(rows, key=lambda r: (r["state"].upper(), r["name"].lower(), r["osm_id"])):
        state = norm_state(r["state"])
        if not r["name"]:
            stats["skipped: no name"] += 1
            continue
        if not state:
            stats[f"skipped: unknown state '{r['state']}'"] += 1
            continue
        key = (state, r["name"].lower(), r["osm_id"]) if r["osm_id"] else None
        if key and key in seen_osm:
            stats["skipped: duplicate row"] += 1
            continue
        if key:
            seen_osm.add(key)
        lat, lon = num(r["lat"]), num(r["lon"])
        if lat is not None and lon is not None:
            if not (17 <= lat <= 72 and (-180 <= lon <= -64 or lon >= 170)):
                stats["coords outside the US, set to empty"] += 1
                lat = lon = None
            elif decimals(r["lat"]) <= 1 and decimals(r["lon"]) <= 1:
                fake_coords += 1
        else:
            lat = lon = None
        same = placed.setdefault((state, r["name"].lower()), [])
        if same and (lat is None or any(c is None or miles((lat, lon), c) < MERGE_MILES for c in same)):
            stats[f"merged: same name within {MERGE_MILES} miles (one park, several OSM shapes)"] += 1
            continue
        same.append((lat, lon) if lat is not None else None)
        pid = make_id(state, r["name"])
        if pid in used_ids:
            pid = f"{pid[:40]}-{r['osm_id'] or len(used_ids)}"
            stats["same name far apart (kept as separate parks, id suffixed)"] += 1
        used_ids.add(pid)
        ptype = r["poi_type"] or "park"
        ref = f"{r['osm_type']}/{r['osm_id']}" if r["osm_type"] and r["osm_id"] else r["osm_id"]
        out.append({
            "id": pid, "name": r["name"], "category": ptype, "subcategory": ptype,
            "state": state, "county": r["county"] or None, "lat": lat, "lon": lon,
            "points": POINTS, "source": "osm" if r["osm_id"] else "csv", "source_id": ref,
        })
    return out, stats, fake_coords


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file", nargs="?", default=str(DEFAULT_FILE))
    ap.add_argument("--dry-run", action="store_true", help="validate and summarize without writing")
    args = ap.parse_args()

    path = Path(args.file)
    if not path.exists():
        sys.exit(f"File not found: {path}")
    rows = read_rows(path)
    pois, stats, fake = build(rows)

    print(f"\nRead {len(rows)} rows, {len(pois)} ready to import")
    for k, v in stats.items():
        print(f"  {v:>5}  {k}")
    if fake:
        print(f"  {fake:>5}  rows have coordinates rounded to 1 decimal or less (placeholder?). Check these before relying on Nearby.")
    print("\nBy type:  " + ", ".join(f"{t} {n}" for t, n in Counter(p["category"] for p in pois).most_common()))
    print("By state: " + ", ".join(f"{s} {n}" for s, n in sorted(Counter(p["state"] for p in pois).items())))
    states_missing = sorted(set(STATES) - {p["state"] for p in pois})
    print(f"No parks for {len(states_missing)} states: {', '.join(states_missing)}")

    if args.dry_run:
        print("\nDry run only. Nothing was written.")
        return
    if not pois:
        sys.exit("Nothing to import.")

    key = os.environ.get("SUPABASE_SERVICE_KEY", "")
    if not key:
        sys.exit("\nSet SUPABASE_SERVICE_KEY (service role key) first, or use --dry-run.")
    try:
        from supabase import create_client
    except ImportError:
        sys.exit("\nInstall the client first: pip install supabase")

    sb = create_client(os.environ.get("SUPABASE_URL", DEFAULT_URL), key)
    done = 0
    try:
        for i in range(0, len(pois), 200):
            sb.table("pois").upsert(pois[i:i + 200]).execute()
            done += len(pois[i:i + 200])
            print(f"  upserted {done}/{len(pois)}", end="\r", flush=True)
    except Exception as e:
        print(f"\n\nStopped after {done} rows: {e}")
        if "42501" in str(e):
            print("The service role has no access to public.pois. Run the grants from supabase/002_grants.sql.")
        sys.exit(1)
    print(f"\nDone. {done} parks upserted.")


if __name__ == "__main__":
    main()
