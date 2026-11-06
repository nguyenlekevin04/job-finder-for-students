"""PwC Germany careers (jobs.pwc.de, a Phenom career site).

The search page embeds its results as JSON (phApp.ddo). Without a keyword it lists every PwC
Germany posting, 10 per page; the board pages through all of them, so the feed is complete.
Kept: internships and working-student posts (entry level "Praktikum, Werkstudium", or a student
title) in a board city. A posting can name many cities: it goes on the first board city in
CITIES order and its location names every board city it lists. The full description comes
from the posting's own page, fetched only for tech-looking titles.
"""
from __future__ import annotations

import json
import re
import time

from fetcher.classify import classify, is_student_title
from fetcher.models import CITIES, Job
from fetcher.net import clean_text, get_text, to_day

NAME = "PwC"

SITE = "https://jobs.pwc.de/de/de"
PAGE = 10  # the site's page size
MAX_PAGES = 100
STUDENT_LEVEL = "Praktikum, Werkstudium"

DDO = re.compile(r"phApp\.ddo\s*=\s*(\{.*?\});\s*phApp", re.S)


def _ddo(text: str) -> dict:
    m = DDO.search(text)
    if not m:
        raise ValueError(f"{NAME}: no embedded data; the page layout may have changed")
    return json.loads(m.group(1))


def parse_search(text: str) -> tuple[int, list[dict]]:
    """(total hits, postings on this page)."""
    found = _ddo(text).get("eagerLoadRefineSearch") or {}
    return int(found.get("totalHits") or 0), list((found.get("data") or {}).get("jobs") or [])


def to_job(p: dict) -> Job | None:
    """A student posting in a board city, else None."""
    title = (p.get("title") or "").strip()
    if not (p.get("jobId") and title):
        return None
    if p.get("entryLevel") != STUDENT_LEVEL and not is_student_title(title):
        return None
    places = " | ".join(p.get("multi_location") or [p.get("city") or ""]).lower()
    ours = [key for key, name in CITIES.items() if name.lower() in places]
    if not ours:
        return None
    return Job(
        source=NAME,
        source_id=str(p["jobId"]),
        title=title,
        company="PwC",
        url=f"{SITE}/job/{p['jobId']}",
        location=", ".join(CITIES[k] for k in ours),
        city=ours[0],
        cities=ours,
        posted_at=to_day(p.get("postedDate")),
        description=clean_text(p.get("descriptionTeaser")),
    )


def parse_detail(text: str) -> str:
    job = ((_ddo(text).get("jobDetail") or {}).get("data") or {}).get("job") or {}
    return clean_text(job.get("description"))[:4000]


def _read_all(jobs: dict[str, Job], seen: set[str]) -> int:
    """One pass over every search page; returns the reported total."""
    total = 0
    for page in range(MAX_PAGES):
        hits, postings = parse_search(get_text(f"{SITE}/search-results", params={"from": page * PAGE, "s": 1}))
        total = total or hits
        for p in postings:
            seen.add(str(p.get("jobId")))
            job = to_job(p)
            if job:
                jobs[job.source_id] = job
        if not postings or (page + 1) * PAGE >= total:
            return total
        time.sleep(0.3)
    # a cut-off list would make the missing postings count as closed
    raise RuntimeError(f"{NAME}: more than {MAX_PAGES * PAGE} postings; raise MAX_PAGES")


def fetch() -> list[Job]:
    jobs: dict[str, Job] = {}
    seen: set[str] = set()
    total = _read_all(jobs, seen)
    if len(seen) < total:
        # Paging is by offset: a posting closing mid-run shifts the rest, so one can be skipped.
        # A second pass fills the gap; still short means the list really is incomplete.
        total = _read_all(jobs, seen)
    if not total or len(seen) < total:
        raise RuntimeError(f"{NAME}: feed ended early: got {len(seen)} of {total}")
    for job in jobs.values():
        if classify(job) is not None:
            # A failure fails the source, so its postings count as unknown, not closed.
            job.description = parse_detail(get_text(job.url)) or job.description
            time.sleep(0.3)
    return list(jobs.values())
