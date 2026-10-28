# Dresden Student Tech Jobs

Werkstudent, internship and thesis positions in **AI, ML, Computer Science and related fields** around Dresden (plus remote roles in Germany), collected every morning from several sources and shown on one searchable page.

- **Fetcher** (`fetcher/`, Python): pulls postings, keeps only student tech jobs, removes duplicates, and saves them to **Supabase** (or to `web/public/jobs.json` when no Supabase keys are set).
- **Database** (Supabase Postgres, `supabase/schema.sql`): `jobs` and `fetch_runs` tables. Visitors can only read.
- **Website** (`web/`, Next.js + Tailwind + Fuse.js): a static site hosted on **Render** that loads jobs from Supabase and does search, filters and bookmarks in the browser.
- **GitHub Action** (`.github/workflows/update-jobs.yml`): runs the fetcher every morning and writes to Supabase. The site picks up new jobs without a rebuild.

## Sources

| Source | How | Notes |
|---|---|---|
| Bundesagentur für Arbeit | Official Jobsuche API | Biggest source; ~18 searches within 30 km of Dresden |
| Arbeitnow | Public JSON API | Dresden + fully remote postings |
| Adzuna | API (free key) | Optional, skipped without a key |
| TU Dresden | HTML job board | Mostly staff/HiWi jobs, so few results get through |
| Fraunhofer | HTML job portal | All Dresden institutes |
| HZDR | HTML list | Internships and theses |

## Run it locally

You need Python 3.10+ and Node 20+.

```bash
pip install -r fetcher/requirements.txt
```

```bash
python fetcher/main.py
```

Without Supabase keys this writes `web/public/jobs.json`. With `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` in `.env` (see `.env.example`) it writes to Supabase instead.

```bash
cd web && npm install && npm run dev
```

Then open http://localhost:3000. To read from Supabase instead of `jobs.json`, copy `web/.env.example` to `web/.env.local` and fill in the URL and anon key. `npm run build` creates the static site in `web/out/`.

Run the tests:

```bash
python -m pytest fetcher/tests -q
```

## Deploy

### 1. Supabase

1. Create a project at https://supabase.com (region: Central EU / Frankfurt).
2. **SQL Editor** → paste `supabase/schema.sql` → **Run**.
3. **Project Settings → API Keys**: note the Project URL, the anon/publishable key (public, read-only) and the service_role/secret key (private, can write).

### 2. GitHub Actions (daily fetch)

**Settings → Secrets and variables → Actions → New repository secret**:

- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- optional: `ADZUNA_APP_ID`, `ADZUNA_APP_KEY` (free key from https://developer.adzuna.com)

Then **Actions → Update jobs → Run workflow** to fill the database. Pushes to `fetcher/` only run the tests; the schedule and the manual button fetch jobs.

### 3. Render (website)

**New → Blueprint** → pick this repo. Render reads `render.yaml` and asks for `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY`. It rebuilds automatically when `web/` changes on `main`. These values are baked in at build time, so after changing them use **Manual Deploy** on Render.

Free Supabase projects pause after a week without activity; the daily fetch keeps the project active.

## How filtering works

`fetcher/classify.py` decides what's kept, with keyword lists you can edit:

- **Type**: Werkstudent, Internship (Praktikum) or Thesis, from the title or the source's category. Student-assistant (HiWi), apprenticeship, PhD, senior and school-pupil posts are dropped.
- **Field**: AI/ML, Data, Software, Embedded/Hardware, Other CS. A title match is enough; the description alone needs at least 3 different tech terms, and can't rescue a clearly non-tech title (marketing, design, sales…).
- **English-friendly**: the text is mostly English, or it names English as the working language.
- **Duplicates**: same title and company (ignoring "(m/w/d)", "GmbH" and so on) are merged into one job with several "via" links.
- **History**: each job keeps the date it was first seen ("New" badge for 3 days). A job that disappears stays for up to 7 days.

## Add a source

Create `fetcher/sources/<name>.py` with `NAME = "..."` and a `fetch() -> list[Job]` function (see `hzdr.py` for a small example), then add it to `SOURCES` in `fetcher/main.py`. Save a sample response in `fetcher/tests/fixtures/` and add a parser test.
