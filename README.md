# Dresden Student Tech Jobs

Werkstudent, internship and thesis positions in **AI, ML, Computer Science and related fields** around Dresden (plus remote roles in Germany), collected every morning from several sources and shown on one searchable page.

- **Fetcher** (`fetcher/`, Python): pulls postings, keeps only student tech jobs, removes duplicates, writes `web/public/jobs.json`.
- **Website** (`web/`, Next.js + Tailwind + Fuse.js): a static site that loads `jobs.json` and does search, filters and bookmarks in the browser.
- **GitHub Action** (`.github/workflows/update-jobs.yml`): runs the fetcher daily, commits the new data, builds the site and publishes it to GitHub Pages. No server, no database, no cost.

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

```bash
cd web && npm install && npm run dev
```

Then open http://localhost:3000. `npm run build` creates the static site in `web/out/`.

Run the tests:

```bash
python -m pytest fetcher/tests -q
```

## Adzuna key (optional)

1. Get a free key at https://developer.adzuna.com.
2. Locally: put `ADZUNA_APP_ID` and `ADZUNA_APP_KEY` in `.env` (see `.env.example`; `.env` is git-ignored).
3. On GitHub: **Settings → Secrets and variables → Actions → New repository secret**, same two names.

## Deploy to GitHub Pages

1. Push this folder to a GitHub repository (public, for free Pages).
2. **Settings → Pages → Build and deployment → Source: GitHub Actions**.
3. **Actions → Update jobs & deploy → Run workflow** (or wait for the daily run).
4. The site appears at `https://<your-username>.github.io/<repo-name>/`.

## How filtering works

`fetcher/classify.py` decides what's kept, with keyword lists you can edit:

- **Type**: Werkstudent, Internship (Praktikum) or Thesis, from the title or the source's category. Student-assistant (HiWi), apprenticeship, PhD, senior and school-pupil posts are dropped.
- **Field**: AI/ML, Data, Software, Embedded/Hardware, Other CS. A title match is enough; the description alone needs at least 3 different tech terms, and can't rescue a clearly non-tech title (marketing, design, sales…).
- **English-friendly**: the text is mostly English, or it names English as the working language.
- **Duplicates**: same title and company (ignoring "(m/w/d)", "GmbH" and so on) are merged into one job with several "via" links.
- **History**: each job keeps the date it was first seen ("New" badge for 3 days). A job that disappears stays for up to 7 days.

## Add a source

Create `fetcher/sources/<name>.py` with `NAME = "..."` and a `fetch() -> list[Job]` function (see `hzdr.py` for a small example), then add it to `SOURCES` in `fetcher/main.py`. Save a sample response in `fetcher/tests/fixtures/` and add a parser test.
