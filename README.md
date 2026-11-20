# Travel Trak

US-focused visit tracker. Earn points for visiting counties, parks, routes, regional foods, and other POIs. Climb the leaderboard.

## Current Status
- Data collection in progress (parks for 13 states, landmarks, foods, restaurants)
- Interactive HTML prototype in `/prototype`
- See `DATA_INDEX.md` for full data catalog

## Prototype
Open `prototype/index.html` in a browser. Tabs: Home (state tile map), Explore (search and filter, mark places visited), Nearby (by your location), Profile (leaderboard).
If the `pois` table is empty the app falls back to bundled sample places and saves stamps in the browser only. Run `supabase/schema.sql`, then `supabase/001_fix_profiles_and_points.sql`, then `supabase/import_pois.py` to go live.
