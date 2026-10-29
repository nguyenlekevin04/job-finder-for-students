"""GlobalFoundries careers (Workday), filtered to the Dresden fab.

The list has no descriptions or dates, so the full posting is fetched only
for titles that look like student jobs.
"""
from __future__ import annotations

import re
import time
from datetime import date, timedelta

from fetcher.classify import is_student_title
from fetcher.models import Job
from fetcher.net import clean_text, get_json, post_json, to_day

NAME = "GlobalFoundries"

SITE = "https://globalfoundries.wd1.myworkdayjobs.com/External"
API = "https://globalfoundries.wd1.myworkdayjobs.com/wday/cxs/globalfoundries/External"
PAGE = 20  # Workday's maximum page size
MAX_PAGES = 10

# Descriptions open with a standard company blurb ("Über GF … www.gf.com.").
INTRO = re.compile(r"^(Über|About) GF\b.{0,1500}?www\.gf\.com\s*\.?\s*", re.S)


def posted_on(text: str | None, today: date | None = None) -> str | None:
    """'Posted Today' / 'Posted Yesterday' / 'Posted 3 Days Ago' -> YYYY-MM-DD ('30+' is unknown)."""
    today = today or date.today()
    text = (text or "").lower()
    if "today" in text:
        return today.isoformat()
    if "yesterday" in text:
        return (today - timedelta(days=1)).isoformat()
    m = re.search(r"(\d+)\s+days? ago", text)
    if m and "+" not in text:
        return (today - timedelta(days=int(m.group(1)))).isoformat()
    return None


def parse_list(data: dict, today: date | None = None) -> list[Job]:
    jobs = []
    for p in data.get("jobPostings") or []:
        path = p.get("externalPath") or ""
        if not (p.get("title") and path):
            continue
        if "dresden" not in (p.get("locationsText") or "").lower() and not path.lower().startswith("/job/dresden"):
            continue
        jobs.append(Job(
            source=NAME,
            source_id=(p.get("bulletFields") or [path])[0],
            title=p["title"].strip(),
            company="GlobalFoundries",
            url=f"{SITE}{path}",
            location="Dresden",
            posted_at=posted_on(p.get("postedOn"), today),
        ))
    return jobs


def parse_detail(data: dict) -> tuple[str, str | None]:
    """(description, posted day) of one posting."""
    info = data.get("jobPostingInfo") or {}
    return INTRO.sub("", clean_text(info.get("jobDescription")))[:4000], to_day(info.get("startDate"))


def is_last_page(data: dict, page: int, total: int) -> bool:
    """True when page `page` (0-based) ends the feed.

    Workday reports `total` only on the first page (later pages say 0), so the
    caller passes the first page's total.
    """
    return not data.get("jobPostings") or (page + 1) * PAGE >= total


def fetch() -> list[Job]:
    jobs: list[Job] = []
    total = 0
    for page in range(MAX_PAGES):
        data = post_json(f"{API}/jobs", {"appliedFacets": {}, "limit": PAGE, "offset": page * PAGE,
                                         "searchText": "Dresden"})
        total = total or data.get("total") or 0
        jobs.extend(parse_list(data))
        if is_last_page(data, page, total):
            break
        time.sleep(0.4)
    else:  # a cut-off list would make the missing postings count as closed
        raise RuntimeError(f"{NAME}: more than {MAX_PAGES * PAGE} postings; raise MAX_PAGES")
    for job in jobs:
        if is_student_title(job.title):
            try:
                desc, posted = parse_detail(get_json(f"{API}{job.url.removeprefix(SITE)}"))
                job.description = desc
                job.posted_at = posted or job.posted_at
            except Exception as err:  # a missing description is fine; keep the job
                print(f"  GlobalFoundries detail {job.source_id} failed: {err}")
            time.sleep(0.4)
    return jobs
