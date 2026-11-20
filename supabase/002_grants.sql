-- Table privileges for the Supabase API roles. Safe to re-run.
-- Newer projects do not grant these automatically on tables created in SQL.
grant usage on schema public to anon, authenticated, service_role;

-- importer scripts
grant select, insert, update, delete on public.pois, public.profiles, public.visits to service_role;

-- the app
grant select on public.pois     to anon, authenticated;
grant select on public.profiles to anon, authenticated;
grant select, insert, delete on public.visits to authenticated;
-- profiles insert/update stay column-limited (see 001_fix_profiles_and_points.sql)
