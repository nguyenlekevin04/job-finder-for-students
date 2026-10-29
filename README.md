# Dresden Student Tech Jobs

Werkstudent, internship and thesis positions in **AI, ML, Computer Science and related fields** around Dresden (plus remote roles in Germany), collected every morning from several sources and shown on one searchable page.

**Live:** https://dresden-jobs.vercel.app

- **Fetcher** (`fetcher/`, Python): pulls postings, keeps only student tech jobs, removes duplicates, and saves them to **Supabase** (or to `web/public/jobs.json` when no Supabase keys are set).
- **Database** (Supabase Postgres, `supabase/schema.sql`): `jobs` and `fetch_runs` tables. Visitors can only read.
- **Website** (`web/`, Next.js + Tailwind + Fuse.js): a static site hosted on **Vercel** that loads jobs from Supabase and does search, filters and bookmarks in the browser.
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
| Infineon | Careers search API (Eightfold) | Dresden site; details fetched only for student-looking titles |
| GlobalFoundries | Careers search API (Workday) | Dresden fab; details fetched only for student-looking titles |
| Bosch | SmartRecruiters public API | Dresden semiconductor fab |
| Amazon | amazon.jobs search feed | Dresden office (AWS); may be empty some days |

If a source fails or suddenly finds nothing, the daily run still saves the other sources' jobs, then fails so GitHub emails the repo owner.

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

Then open http://localhost:3000. To read from Supabase instead of `jobs.json`, copy `web/.env.example` to `web/.env.local` and fill in the **staging** project's URL and anon key. `npm run build` creates the static site in `web/out/`.

Local fetches must use the staging project too: the fetcher refuses to write to the production database unless it runs as the scheduled GitHub Action.

Run the tests:

```bash
python -m pytest fetcher/tests -q
```

```bash
cd web && npm test
```

## Environments and workflow

| | Website | Database | Deploys from |
|---|---|---|---|
| **dev** | `npm run dev` on your machine | staging Supabase project | – |
| **staging** | Vercel preview at the `staging` branch URL (orange STAGING banner, hidden from search engines) | staging Supabase project | `staging` branch, and every pull request gets its own preview |
| **production** | Vercel production deployment | production Supabase project | `main` |

1. Create a branch from `staging`, then open a pull request into `staging`.
2. CI runs the fetcher tests, plus the website's lint, type check, unit tests and build. Vercel posts a preview link.
3. After merging, check the staging URL.
4. Open a pull request from `staging` into `main`. Merging it puts the change live.

`main` and `staging` are protected: changes only land through pull requests with passing checks.

See `docs/capacity.md` for what 5,000 users cost on the free tiers, and when the setup has to change.

## Deploy

### 1. Supabase (two projects: production and staging)

1. Create each project at https://supabase.com (region: Central EU / Frankfurt).
2. **SQL Editor** → paste `supabase/schema.sql` → **Run**.
3. **Project Settings → API Keys**: note the Project URL, the anon/publishable key (public, read-only) and the service_role/secret key (private, can write).

### 2. GitHub Actions (daily fetch)

**Settings → Secrets and variables → Actions → New repository secret**:

- `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`: production
- `STAGING_SUPABASE_URL`, `STAGING_SUPABASE_SERVICE_ROLE_KEY`: staging
- optional: `ADZUNA_APP_ID`, `ADZUNA_APP_KEY` (free key from https://developer.adzuna.com)

The schedule fills both databases every morning. **Actions → Update jobs → Run workflow** fills the one you pick. If the staging secrets are missing, the staging run fails instead of falling back to production.

### 3. Vercel (website)

**Add New → Project** → import this repo. Set **Root Directory** to `web`. Vercel detects Next.js; `web/vercel.json` adds headers and skips builds when `web/` didn't change. Environment variables:

| Variable | Production | Preview (staging + pull requests) |
|---|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | production project URL | staging project URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | production anon key | staging anon key |
| `NEXT_PUBLIC_DEPLOY_ENV` | (leave unset) | `staging` |

These values are baked in at build time, so redeploy after changing them. The old Render site (`render.yaml`) stays only to forward its address to Vercel.

Free Supabase projects pause after a week without activity; the daily fetch keeps the project active.

## How filtering works

`fetcher/classify.py` decides what's kept, with keyword lists you can edit:

- **Type**: Werkstudent, Internship (Praktikum) or Thesis, from the title or the source's category. Student-assistant (HiWi), apprenticeship, PhD, senior and school-pupil posts are dropped.
- **Field**: AI/ML, Data, Software, Embedded/Hardware, Other CS. A title match is enough; the description alone needs at least 3 different tech terms, and can't rescue a clearly non-tech title (marketing, design, sales…).
- **English-friendly**: the text is mostly English, or it names English as the working language.
- **Duplicates**: same title and company (ignoring "(m/w/d)", "GmbH" and so on) are merged into one job with several "via" links.
- **History**: each job keeps the date it was first seen ("New" badge for 3 days). A job that disappears stays for up to 7 days.

## Add a source

Create `fetcher/sources/<name>.py` with `NAME = "..."` and a `fetch() -> list[Job]` function (see `hzdr.py` or `amazon.py` for small examples), then add it to `SOURCES` in `fetcher/main.py`. Set `MAY_BE_EMPTY = True` if zero postings on some days is normal. Save a sample response in `fetcher/tests/fixtures/` and add a parser test.
