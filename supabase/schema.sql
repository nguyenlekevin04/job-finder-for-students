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

-- German level as the posting states it (fetcher/terms.py extract_german); null = not stated.
alter table public.jobs add column if not exists german_level text check (german_level in ('none', 'basic', 'fluent'));

-- The board's city (a key of fetcher.models.CITIES); empty for remote-only postings.
alter table public.jobs add column if not exists city text not null default 'dresden';
-- Every board city the job names (a job open in Leipzig and Berlin shows on both boards).
alter table public.jobs add column if not exists cities text[] not null default '{}';

-- No query needs this index: stale rows are deleted by id.
drop index if exists public.jobs_last_seen_idx;

-- One row per daily run: when it ran and how each source did.
create table if not exists public.fetch_runs (
  id           bigint generated always as identity primary key,
  generated_at timestamptz not null default now(),
  job_count    integer not null,
  sources      jsonb not null default '{}'
);

create index if not exists fetch_runs_generated_at_idx on public.fetch_runs (generated_at desc);

-- Employer closures (fetcher/availability.py): for 30 days a job-board copy of a job its
-- employer closed is rejected. Fetcher only: no public read, no public writes.
create table if not exists public.closed_jobs (
  id        text primary key,  -- the closed job's id
  closed_on date not null
);
alter table public.closed_jobs enable row level security;
revoke all on public.closed_jobs from anon, authenticated;
grant all on public.closed_jobs to service_role;

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

-- ---------------------------------------------------------------- Push alerts --
-- One browser push subscription per device, with the search it wants alerts for
-- (board + types + fields). Nobody can read or change the table directly; visitors
-- only call subscribe_push / unsubscribe_push, which validate everything. The daily
-- fetch (service_role) reads it and sends at most one notification per day.
create table if not exists public.push_subscriptions (
  endpoint   text primary key,             -- the browser's push URL; secret, only its owner knows it
  p256dh     text not null,
  auth       text not null,
  board      text not null check (board in ('dresden', 'leipzig', 'chemnitz', 'berlin', 'remote')),
  types      text[] not null default '{}',
  fields     text[] not null default '{}',
  created_at timestamptz not null default now(),
  last_sent  date
);
-- A sign-up counts only once a real "Alerts are on" push reached it (fetcher/push.py), so fake
-- sign-ups can't fill the table: unconfirmed rows have their own small cap and are gone within a day.
alter table public.push_subscriptions add column if not exists confirmed boolean not null default false;
alter table public.push_subscriptions enable row level security;
revoke all on public.push_subscriptions from anon, authenticated;
grant all on public.push_subscriptions to service_role;

create or replace function public.subscribe_push(
  p_endpoint text, p_p256dh text, p_auth text, p_board text, p_types text[], p_fields text[]
) returns void
language plpgsql security definer set search_path = '' as $$
begin
  -- Only the big browser push services, no whitespace or control characters; anything else
  -- could make the sender call arbitrary URLs.
  if p_endpoint is null or length(p_endpoint) > 1000 or p_endpoint ~ '[[:cntrl:][:space:]]' or p_endpoint !~
     '^https://(fcm\.googleapis\.com|updates\.push\.services\.mozilla\.com|web\.push\.apple\.com|wns2-[a-z0-9]+\.notify\.windows\.com)/' then
    raise exception 'invalid endpoint';
  end if;
  -- Browser keys are base64url: p256dh is 87 characters, auth 22.
  if p_p256dh !~ '^[A-Za-z0-9_-]{80,100}$' or p_auth !~ '^[A-Za-z0-9_-]{16,32}$' then
    raise exception 'invalid keys';
  end if;
  if p_board not in ('dresden', 'leipzig', 'chemnitz', 'berlin', 'remote') then raise exception 'invalid board'; end if;
  if cardinality(coalesce(p_types, '{}')) > 3 or cardinality(coalesce(p_fields, '{}')) > 6 then raise exception 'too many filters'; end if;
  if not (coalesce(p_types, '{}') <@ array['werkstudent', 'internship', 'thesis']) then raise exception 'invalid types'; end if;
  if not (coalesce(p_fields, '{}') <@ array['ai', 'data', 'software', 'hardware', 'business', 'other']) then raise exception 'invalid fields'; end if;
  if (select count(*) from public.push_subscriptions where confirmed) >= 20000 then raise exception 'full'; end if;
  if (select count(*) from public.push_subscriptions where not confirmed) >= 2000 then raise exception 'busy'; end if;
  insert into public.push_subscriptions (endpoint, p256dh, auth, board, types, fields)
  values (p_endpoint, p_p256dh, p_auth, p_board,
          array(select distinct unnest(coalesce(p_types, '{}'))), array(select distinct unnest(coalesce(p_fields, '{}'))))
  on conflict (endpoint) do update
    set p256dh = excluded.p256dh, auth = excluded.auth, board = excluded.board,
        types = excluded.types, fields = excluded.fields;
end $$;

create or replace function public.unsubscribe_push(p_endpoint text) returns void
language sql security definer set search_path = '' as $$
  delete from public.push_subscriptions where endpoint = p_endpoint;
$$;

revoke all on function public.subscribe_push(text, text, text, text, text[], text[]) from public;
revoke all on function public.unsubscribe_push(text) from public;
grant execute on function public.subscribe_push(text, text, text, text, text[], text[]) to anon, authenticated;
grant execute on function public.unsubscribe_push(text) to anon, authenticated;
