"""Arbeitnow – free public job board API for Germany.

Its terms ask for a link back to arbeitnow.com; the page footer provides it.
"""
from __future__ import annotations

import re
import time

from fetcher.net import clean_text, get_json, to_day
from fetcher.models import Job

NAME = "Arbeitnow"

API = "https://www.arbeitnow.com/api/job-board-api"
MAX_PAGES = 10


def parse(data: dict) -> list[Job]:
    """Keep only Dresden or fully remote postings."""
    jobs = []
    for j in data.get("data") or []:
        if not (j.get("slug") and j.get("title") and j.get("url")):
            continue
        location = j.get("location") or ""
        in_dresden = bool(re.search(r"dresden", location, re.I))
        if not in_dresden and not j.get("remote"):
            continue
        jobs.append(Job(
            source=NAME,
            source_id=j["slug"],
            title=j["title"],
            company=j.get("company_name") or "Unknown",
            url=j["url"],
            location=location or "Remote",
            remote=bool(j.get("remote")) and not in_dresden,
            posted_at=to_day(j.get("created_at")),
            tags=" ".join(j.get("tags") or []),
            description=clean_text(j.get("description"))[:4000],
        ))
    return jobs


def fetch() -> list[Job]:
    jobs: list[Job] = []
    for page in range(1, MAX_PAGES + 1):
        data = get_json(API, params={"page": page})
        jobs.extend(parse(data))
        if not data.get("data") or not (data.get("links") or {}).get("next"):
            break
        time.sleep(0.5)
    return jobs
