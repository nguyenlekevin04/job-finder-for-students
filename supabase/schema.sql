-- Dresden Student Tech Jobs – database setup.
-- Paste into Supabase → SQL Editor → Run. Safe to run again.
--
-- Visitors (anon key) can only read. The daily fetcher writes with the
-- service_role / secret key, which bypasses row level security.

create table if not exists public.jobs (
  id               text primary key,          -- hash of normalized title + company
  title            text not null,
  company          text not null,
  location         text not null default '',
  remote           boolean not null default false,
  type             text not null,             -- primary type: werkstudent | internship | thesis
  types            text[] not null default '{}',
  fields           text[] not null default '{}',
  english_friendly boolean not null default false,
  posted_at        date,
  deadline         date,
  first_seen       date not null,
  last_seen        date not null,
  links            jsonb not null default '[]', -- [{source, url}]
  snippet          text not null default ''
);

-- Hours per week and pay, only when the posting states them (fetcher/terms.py).
alter table public.jobs add column if not exists hours_min  smallint;
alter table public.jobs add column if not exists hours_max  smallint;
alter table public.jobs add column if not exists pay_amount numeric(8,2);
alter table public.jobs add column if not exists pay_unit   text check (pay_unit in ('hour', 'month'));

create index if not exists jobs_last_seen_idx on public.jobs (last_seen);

-- One row per daily run: when it ran and how each source did.
create table if not exists public.fetch_runs (
  id           bigint generated always as identity primary key,
  generated_at timestamptz not null default now(),
  job_count    integer not null,
  sources      jsonb not null default '{}'
);

create index if not exists fetch_runs_generated_at_idx on public.fetch_runs (generated_at desc);

-- Row level security: public read, no public writes.
alter table public.jobs enable row level security;
alter table public.fetch_runs enable row level security;

drop policy if exists "Anyone can read jobs" on public.jobs;
create policy "Anyone can read jobs" on public.jobs
  for select to anon, authenticated using (true);

drop policy if exists "Anyone can read fetch runs" on public.fetch_runs;
create policy "Anyone can read fetch runs" on public.fetch_runs
  for select to anon, authenticated using (true);

grant select on public.jobs, public.fetch_runs to anon, authenticated;
revoke insert, update, delete, truncate on public.jobs, public.fetch_runs from anon, authenticated;
grant all on public.jobs, public.fetch_runs to service_role;
