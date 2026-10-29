"""Infineon careers (Eightfold), filtered to Dresden.

The list API has no descriptions, so the full posting is fetched only for
titles that look like student jobs (a handful of requests).
"""
from __future__ import annotations

import re
import time

from fetcher.classify import is_student_title
from fetcher.models import Job
from fetcher.net import clean_text, get_json, to_day

NAME = "Infineon"

BASE = "https://jobs.infineon.com"
SEARCH = f"{BASE}/api/pcsx/search"
DETAIL = f"{BASE}/api/pcsx/position_details"
PAGE = 10  # the API returns 10 positions per page
MAX_PAGES = 15
FEED_SLACK = 2  # postings that may close while paging

# Every description opens with the same slogan ("#WeAreIn … Are you in?").
INTRO = re.compile(r"^.{0,600}?Are you in\?\s*", re.S)
# …and end with the company profile and recruiter contact ("#WeAreIn for driving …").
OUTRO = re.compile(r"\s*#WeAreIn for driving\b.*$", re.S)


def parse_search(data: dict) -> list[Job]:
    jobs = []
    for p in (data.get("data") or {}).get("positions") or []:
        locations = p.get("locations") or []
        if not (p.get("id") and p.get("name")) or not any("dresden" in loc.lower() for loc in locations):
            continue
        jobs.append(Job(
            source=NAME,
            source_id=str(p["id"]),
            title=p["name"].strip(),
            company="Infineon",
            url=f"{BASE}/careers/job/{p['id']}",
            location="Dresden",
            posted_at=to_day(p.get("postedTs")),
        ))
    return jobs


def parse_detail(data: dict) -> str:
    """Description text of one posting, without the shared intro."""
    text = clean_text(((data.get("data") or {}).get("jobDescription")))
    return OUTRO.sub("", INTRO.sub("", text))[:4000]


def is_last_page(data: dict, page: int) -> bool:
    """True when page `page` (0-based) ends the feed: a short page or the reported count reached."""
    body = data.get("data") or {}
    count = body.get("count")
    return len(body.get("positions") or []) < PAGE or (count is not None and (page + 1) * PAGE >= count)


def fetch() -> list[Job]:
    jobs: list[Job] = []
    total = rows = 0
    for page in range(MAX_PAGES):
        data = get_json(SEARCH, params={"domain": "infineon.com", "query": "", "location": "Dresden",
                                        "start": page * PAGE, "filter_distance": 30})
        body = data.get("data") or {}
        total = total or body.get("count") or 0
        rows += len(body.get("positions") or [])
        jobs.extend(parse_search(data))
        if is_last_page(data, page):
            break
        time.sleep(0.4)
    else:  # a cut-off list would make the missing postings count as closed
        raise RuntimeError(f"{NAME}: more than {MAX_PAGES * PAGE} postings; raise MAX_PAGES")
    # An empty or short page before the reported end. A slack of 2 tolerates postings that
    # close while the pages are being fetched, so that alone never fails the source.
    if total and rows < min(total, MAX_PAGES * PAGE) - FEED_SLACK:
        raise RuntimeError(f"{NAME}: feed ended early: got {rows} of {total}")
    for job in jobs:
        if is_student_title(job.title):
            try:
                job.description = parse_detail(get_json(DETAIL, params={
                    "position_id": job.source_id, "domain": "infineon.com", "hl": "en"}))
            except Exception as err:  # a missing description is fine; keep the job
                print(f"  Infineon detail {job.source_id} failed: {err}")
            time.sleep(0.4)
    return jobs
