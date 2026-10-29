"""Bosch careers via the public SmartRecruiters API, filtered to Dresden.

The list has no descriptions, so the full posting is fetched only for titles
that look like student jobs.
"""
from __future__ import annotations

import time

from fetcher.classify import is_student_title
from fetcher.models import Job
from fetcher.net import clean_text, get_json, to_day

NAME = "Bosch"

API = "https://api.smartrecruiters.com/v1/companies/BoschGroup/postings"
SITE = "https://jobs.smartrecruiters.com/BoschGroup"
PAGE = 100
MAX_PAGES = 5


def _label(value) -> str:
    value = value or {}
    return "" if value.get("id") == "not_applicable" else value.get("label") or ""


def parse_list(data: dict) -> list[Job]:
    jobs = []
    for p in data.get("content") or []:
        loc = p.get("location") or {}
        if not (p.get("id") and p.get("name")) or (loc.get("city") or "").lower() != "dresden":
            continue
        jobs.append(Job(
            source=NAME,
            source_id=str(p["id"]),
            title=p["name"].strip(),
            company="Bosch",
            url=f"{SITE}/{p['id']}",
            location="Dresden",
            posted_at=to_day(p.get("releasedDate")),
            # "Internship" here helps spot internships whose title doesn't say so.
            tags=" ".join(filter(None, [_label(p.get("experienceLevel")), _label(p.get("function"))])),
        ))
    return jobs


def parse_detail(data: dict) -> str:
    """Role and requirements text (skips the generic company blurb)."""
    sections = ((data.get("jobAd") or {}).get("sections")) or {}
    parts = [clean_text((sections.get(k) or {}).get("text")) for k in ("jobDescription", "qualifications")]
    return " ".join(p for p in parts if p)[:4000]


def fetch() -> list[Job]:
    jobs: list[Job] = []
    for page in range(MAX_PAGES):
        data = get_json(API, params={"city": "Dresden", "limit": PAGE, "offset": page * PAGE})
        jobs.extend(parse_list(data))
        if (page + 1) * PAGE >= (data.get("totalFound") or 0):
            break
        time.sleep(0.4)
    for job in jobs:
        if is_student_title(f"{job.title} {job.tags}"):
            try:
                job.description = parse_detail(get_json(f"{API}/{job.source_id}"))
            except Exception as err:  # a missing description is fine; keep the job
                print(f"  Bosch detail {job.source_id} failed: {err}")
            time.sleep(0.4)
    return jobs
