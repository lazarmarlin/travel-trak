-- Travel Trak migration 001: profile creation, server-side points, locked-down profiles
-- Run in the Supabase SQL Editor AFTER schema.sql. Safe to re-run.

-- 1. Profiles: only these columns may be written by clients ---------------------
-- total_points / visited_count can then only change through the visit triggers.
revoke insert, update on public.profiles from anon, authenticated;
grant insert (id, username, display_name) on public.profiles to authenticated;
grant update (username, display_name)     on public.profiles to authenticated;

drop policy if exists "Users can insert own profile" on public.profiles;
create policy "Users can insert own profile" on public.profiles
  for insert with check (auth.uid() = id);

-- 2. Auto-create a profile whenever someone signs up ----------------------------
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
declare
  base text := coalesce(nullif(split_part(new.email, '@', 1), ''), 'traveler');
  uname text := base;
begin
  if exists (select 1 from public.profiles where username = uname) then
    uname := base || '-' || substr(new.id::text, 1, 4);
  end if;
  insert into public.profiles (id, username)
  values (new.id, uname)
  on conflict (id) do nothing;
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- Backfill any existing users that have no profile yet
insert into public.profiles (id, username)
select u.id,
       case when exists (select 1 from public.profiles p
                         where p.username = coalesce(nullif(split_part(u.email, '@', 1), ''), 'traveler'))
            then coalesce(nullif(split_part(u.email, '@', 1), ''), 'traveler') || '-' || substr(u.id::text, 1, 4)
            else coalesce(nullif(split_part(u.email, '@', 1), ''), 'traveler') end
from auth.users u
where not exists (select 1 from public.profiles p where p.id = u.id)
on conflict do nothing;

-- 3. Visits: points come from the POI, never from the client -------------------
alter table public.visits alter column points_awarded set default 0;
alter table public.visits alter column user_id set default auth.uid();

create or replace function public.set_visit_points()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  select points into new.points_awarded from public.pois where id = new.poi_id;
  if new.points_awarded is null then
    raise exception 'Unknown POI: %', new.poi_id;
  end if;
  new.visited_at := now();
  return new;
end;
$$;

drop trigger if exists before_visit_insert on public.visits;
create trigger before_visit_insert
  before insert on public.visits
  for each row execute function public.set_visit_points();

-- 4. Allow un-checking a visit, and keep totals in sync ------------------------
drop policy if exists "Users can delete own visits" on public.visits;
create policy "Users can delete own visits" on public.visits
  for delete using (auth.uid() = user_id);

create or replace function public.handle_deleted_visit()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  update public.profiles
  set total_points  = greatest(total_points  - old.points_awarded, 0),
      visited_count = greatest(visited_count - 1, 0)
  where id = old.user_id;
  return old;
end;
$$;

drop trigger if exists on_visit_deleted on public.visits;
create trigger on_visit_deleted
  after delete on public.visits
  for each row execute function public.handle_deleted_visit();

-- Make the original insert trigger safe too (pinned search_path)
alter function public.handle_new_visit() set search_path = public;

-- 5. Recompute totals once, in case anything was tampered with ------------------
update public.profiles p
set total_points  = coalesce(v.pts, 0),
    visited_count = coalesce(v.cnt, 0)
from (select user_id, sum(points_awarded)::int pts, count(*)::int cnt
      from public.visits group by user_id) v
where p.id = v.user_id;

update public.profiles
set total_points = 0, visited_count = 0
where id not in (select user_id from public.visits);
