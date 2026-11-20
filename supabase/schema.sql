-- Travel Trak Supabase Schema
-- Run this in the Supabase SQL Editor

-- Users (extends Supabase auth.users)
create table if not exists public.profiles (
  id uuid references auth.users on delete cascade primary key,
  username text unique,
  display_name text,
  total_points integer default 0,
  visited_count integer default 0,
  created_at timestamptz default now()
);

-- POIs (points of interest)
create table if not exists public.pois (
  id text primary key,
  name text not null,
  category text not null,
  subcategory text,
  state text,
  county text,
  lat double precision,
  lon double precision,
  points integer default 10,
  source text,
  source_id text,
  created_at timestamptz default now()
);

-- Visits
create table if not exists public.visits (
  id uuid default gen_random_uuid() primary key,
  user_id uuid references public.profiles(id) on delete cascade,
  poi_id text references public.pois(id),
  points_awarded integer not null,
  visited_at timestamptz default now(),
  notes text,
  unique(user_id, poi_id)
);

-- Indexes
create index if not exists idx_visits_user on public.visits(user_id);
create index if not exists idx_visits_poi on public.visits(poi_id);
create index if not exists idx_pois_state on public.pois(state);
create index if not exists idx_pois_category on public.pois(category);

-- Row Level Security
alter table public.profiles enable row level security;
alter table public.visits enable row level security;
alter table public.pois enable row level security;

-- Policies
create policy "Public profiles are viewable" on public.profiles for select using (true);
create policy "Users can update own profile" on public.profiles for update using (auth.uid() = id);
create policy "POIs are public" on public.pois for select using (true);
create policy "Users can view own visits" on public.visits for select using (auth.uid() = user_id);
create policy "Users can insert own visits" on public.visits for insert with check (auth.uid() = user_id);

-- Function to update points on visit
create or replace function public.handle_new_visit()
returns trigger as $$
begin
  update public.profiles
  set total_points = total_points + new.points_awarded,
      visited_count = visited_count + 1
  where id = new.user_id;
  return new;
end;
$$ language plpgsql security definer;

create trigger on_visit_created
  after insert on public.visits
  for each row execute function public.handle_new_visit();
