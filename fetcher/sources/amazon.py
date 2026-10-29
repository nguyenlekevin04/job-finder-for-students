"""Amazon jobs (amazon.jobs search feed), filtered to Dresden (AWS / Amazon Linux)."""
from __future__ import annotations

import re
from datetime import datetime

from fetcher.models import Job
from fetcher.net import clean_text, get_json

NAME = "Amazon"

API = "https://www.amazon.jobs/en/search.json"
SITE = "https://www.amazon.jobs"

# The Dresden office is small, so a day with no openings is normal (no alarm).
MAY_BE_EMPTY = True


def us_date(value: str | None) -> str | None:
    """'October  8, 2026' -> '2026-10-08'."""
    try:
        return datetime.strptime(re.sub(r"\s+", " ", value or "").strip(), "%B %d, %Y").strftime("%Y-%m-%d")
    except ValueError:
        return None


def parse(data: dict) -> list[Job]:
    jobs = []
    for j in data.get("jobs") or []:
        if (j.get("city") or "").lower() != "dresden" or not (j.get("id_icims") and j.get("title") and j.get("job_path")):
            continue
        jobs.append(Job(
            source=NAME,
            source_id=str(j["id_icims"]),
            title=j["title"].strip(),
            company="Amazon",
            url=f"{SITE}{j['job_path']}",
            location="Dresden",
            posted_at=us_date(j.get("posted_date")),
            tags=j.get("job_category") or "",
            description=clean_text(f"{j.get('description') or ''} {j.get('basic_qualifications') or ''}")[:4000],
        ))
    return jobs


def fetch() -> list[Job]:
    return parse(get_json(API, params={"normalized_city_name[]": "Dresden", "result_limit": 100, "base_query": ""}))
