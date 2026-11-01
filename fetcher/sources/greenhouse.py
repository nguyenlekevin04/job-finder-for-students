"""Berlin employers whose career sites run on Greenhouse (public job board API).

One request per company returns every open posting with its description, so the
feed is complete: a posting the board stops listing has closed. Only Berlin postings
are kept; the classifier decides which are student tech jobs. Links go to the
Greenhouse-hosted posting (job-boards.greenhouse.io), the employer's own job page.

Add a company: find its board token (the name in boards.greenhouse.io/<token>), check
https://boards-api.greenhouse.io/v1/boards/<token>/jobs answers, and add it below.
"""
from __future__ import annotations

import html
import time

from fetcher.models import Job
from fetcher.net import clean_text, get_json, to_day

NAME = "Greenhouse"

API = "https://boards-api.greenhouse.io/v1/boards/{token}/jobs"
SITE = "https://job-boards.greenhouse.io/{token}/jobs/{id}"

# Board token -> company name as students know it.
COMPANIES = {
    "hellofresh": "HelloFresh",
    "getyourguide": "GetYourGuide",
    "n26": "N26",
    "raisin": "Raisin",
    "traderepublicbank": "Trade Republic",
    "commercetools": "commercetools",
    "wolt": "Wolt",
    "contentful": "Contentful",
}


def parse(data: dict, token: str, company: str) -> list[Job]:
    jobs = []
    for p in data.get("jobs") or []:
        place = ((p.get("location") or {}).get("name") or "").strip()
        if not (p.get("id") and p.get("title")) or "berlin" not in place.lower():
            continue
        departments = ", ".join(d.get("name") or "" for d in p.get("departments") or [])
        jobs.append(Job(
            source=NAME,
            source_id=f"{token}:{p['id']}",
            title=p["title"].strip(),
            company=company,
            url=SITE.format(token=token, id=p["id"]),
            location="Berlin",
            city="berlin",
            posted_at=to_day(p.get("first_published") or p.get("updated_at")),
            tags=departments,  # e.g. "Engineering", "Data" (short and reliable, like a category)
            description=clean_text(html.unescape(p.get("content") or ""))[:4000],
        ))
    return jobs


def fetch() -> list[Job]:
    jobs: list[Job] = []
    for token, company in COMPANIES.items():
        # A failing board fails the whole source, so its postings count as unknown, not closed.
        jobs.extend(parse(get_json(API.format(token=token), params={"content": "true"}), token, company))
        time.sleep(0.3)
    return jobs
