# Travel Trak — Data Index

Last updated: 2026-11-20

## Structure

```
data/
├── raw/                  # Original downloads
└── processed/            # Cleaned data for the app
    ├── regional_foods_starter.csv
    ├── regional_restaurants.csv
    ├── iconic_landmarks.csv
    └── parks/
        ├── *_parks.csv   # 13 states so far
        └── state_high_points.csv
```

## Processed Data Catalog

| File | Description | Rows | Status |
|------|-------------|------|--------|
| `regional_foods_starter.csv` | Signature regional foods by state | ~70 | Starter |
| `regional_restaurants.csv` | Regional restaurant chains | 26 | Expanded |
| `iconic_landmarks.csv` | One iconic landmark per state + DC | 51 | Complete |
| `parks/state_high_points.csv` | Highest point in each state + DC | 51 | Complete |
| `parks/*_parks.csv` | State & national parks/monuments | 13 states | In progress |

### Park coverage so far
AL, CA, FL, GA, KS, LA, NC, NY, OH, PA, TN, TX, VA

## Next Priorities
1. Finish remaining states for parks
2. Add county parks
3. Expand regional foods with more entries
4. Numbered routes / interstates (from OpenInterstate data)
