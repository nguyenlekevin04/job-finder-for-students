"""Adzuna – free job search API.

Needs a free key from https://developer.adzuna.com. Set ADZUNA_APP_ID and
ADZUNA_APP_KEY in .env (local) or as GitHub secrets. Skipped when missing.
"""
from __future__ import annotations

import os
import re
import time

from fetcher.net import clean_text, get_json, to_day
from fetcher.models import Job

NAME = "Adzuna"

API = "https://api.adzuna.com/v1/api/jobs/de/search/1"

# (what, where). where=None means a Germany-wide search kept only if remote.
QUERIES = [
    ("werkstudent", "Dresden"),
    ("praktikum", "Dresden"),
    ("abschlussarbeit", "Dresden"),
    ("masterarbeit", "Dresden"),
    ("internship", "Dresden"),
    ("working student", "Dresden"),
    ("werkstudent remote", None),
    ("working student remote", None),
]

REMOTE = re.compile(r"remote|home.?office|mobiles arbeiten|100 ?% mobil", re.I)


def is_enabled() -> bool:
    return bool(os.environ.get("ADZUNA_APP_ID") and os.environ.get("ADZUNA_APP_KEY"))


def parse(data: dict, *, local: bool) -> list[Job]:
    jobs = []
    for j in data.get("results") or []:
        title = clean_text(j.get("title"))
        desc = clean_text(j.get("description"))
        location = (j.get("location") or {}).get("display_name") or ""
        remote = bool(REMOTE.search(f"{title} {desc}"))
        if not local and not remote:
            continue
        jobs.append(Job(
            source=NAME,
            source_id=str(j["id"]),
            title=title,
            company=(j.get("company") or {}).get("display_name") or "Unknown",
            url=j["redirect_url"],
            location=location,
            remote=remote and not re.search(r"dresden", location, re.I),
            posted_at=to_day(j.get("created")),
            tags=(j.get("category") or {}).get("label") or "",
            description=desc,
        ))
    return jobs


def fetch() -> list[Job]:
    by_id: dict[str, Job] = {}
    for what, where in QUERIES:
        params = {
            "app_id": os.environ["ADZUNA_APP_ID"],
            "app_key": os.environ["ADZUNA_APP_KEY"],
            "results_per_page": "50",
            "what": what,
        }
        if where:
            params.update(where=where, distance="30")
        for job in parse(get_json(API, params=params), local=bool(where)):
            by_id.setdefault(job.source_id, job)
        time.sleep(0.4)
    return list(by_id.values())
