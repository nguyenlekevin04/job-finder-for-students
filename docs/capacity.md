# Capacity: what 5,000 users cost, and when to change the setup

Measured on 2026-10-29 with 40 jobs. Free-tier limits come from the official pricing pages on the same day.

## Per visit

| What | Size (gzip) | Served by |
|---|---|---|
| First visit: HTML + JS/CSS + fonts | ~263 KB, 13 requests | Vercel CDN (assets cached in the browser for a year after that) |
| Repeat visit: HTML | ~4 KB, 1–3 requests | Vercel CDN |
| Job list | ~230 bytes per job (9 KB at 40 jobs) on every visit | Supabase REST |

## 5,000 users × ~20 visits a month (100,000 visits)

| Service | Free limit | Our use | Share |
|---|---|---|---|
| Vercel bandwidth | 100 GB / month | ~1.8 GB | ~2% |
| Vercel CDN requests | 1M / month | ~350k | ~35% |
| Supabase egress | 5 GB / month | ~0.9 GB at 40 jobs | ~18% |
| Supabase projects | 2 active | production + staging | full |

Concurrency is not a concern. Peaks of a few dozen users at once are trivial for a CDN and for a 40-row read on Supabase. Supabase's free plan allows unlimited API requests.

## When to change

**Switch to serving the job list from the CDN** at **100 jobs**, or earlier if the Supabase dashboard shows more than **2.5 GB of egress in a month** (half the free limit).

At 100,000 visits a month, egress is about 0.023 GB per job, so 100 jobs uses about 2.3 GB. More cities would pass 100 jobs quickly, so do this before launching a second city.

The change: the daily fetch triggers a Vercel deploy hook; the build writes the job list as a static file, and the site loads that file instead of calling Supabase. Supabase is then read once a day, not once per visit.

Other triggers:
- **Vercel requests above 700k a month:** check how many requests a first visit makes before anything else.
- **Any wish to monetize** (ads, paid listings): Vercel Hobby is for non-commercial use only, so move to Vercel Pro ($20/month) first.
- **Free Supabase projects pause after 7 days without activity.** The daily fetch writes to both projects, so neither pauses as long as the GitHub Action runs.
