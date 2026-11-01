"""Berlin employers on SmartRecruiters (public postings API), e.g. Delivery Hero.

Same API as the Bosch source, filtered to Berlin. The list has no descriptions, so the
full posting is fetched only for titles that look like student jobs. Each company's
Berlin list must fit in one page, or the source fails (a cut-off list would make the
missing postings count as closed).
"""
from __future__ import annotations

import time

from fetcher.classify import is_student_title
from fetcher.models import Job
from fetcher.net import get_json, to_day
from fetcher.sources.bosch import _label, parse_detail

NAME = "SmartRecruiters"

API = "https://api.smartrecruiters.com/v1/companies/{company}/postings"
SITE = "https://jobs.smartrecruiters.com/{company}/{id}"
PAGE = 100

# SmartRecruiters company id -> name as students know it.
COMPANIES = {
    "DeliveryHero": "Delivery Hero",
    "Vattenfall": "Vattenfall",
}


def parse_list(data: dict, company_id: str, company: str) -> list[Job]:
    jobs = []
    for p in data.get("content") or []:
        loc = p.get("location") or {}
        if not (p.get("id") and p.get("name")) or (loc.get("city") or "").lower() != "berlin":
            continue
        jobs.append(Job(
            source=NAME,
            source_id=f"{company_id}:{p['id']}",
            title=p["name"].strip(),
            company=company,
            url=SITE.format(company=company_id, id=p["id"]),
            location="Berlin",
            city="berlin",
            posted_at=to_day(p.get("releasedDate")),
            tags=" ".join(filter(None, [_label(p.get("experienceLevel")), _label(p.get("function"))])),
        ))
    return jobs


def fetch() -> list[Job]:
    jobs: list[Job] = []
    for company_id, company in COMPANIES.items():
        data = get_json(API.format(company=company_id), params={"city": "Berlin", "limit": PAGE})
        if (data.get("totalFound") or 0) > PAGE:
            raise RuntimeError(f"{NAME}: {company} has more than {PAGE} Berlin postings; add paging")
        jobs.extend(parse_list(data, company_id, company))
        time.sleep(0.3)
    for job in jobs:
        if is_student_title(f"{job.title} {job.tags}"):
            company_id, posting = job.source_id.split(":", 1)
            try:
                job.description = parse_detail(get_json(f"{API.format(company=company_id)}/{posting}"))
            except Exception as err:  # a missing description is fine; keep the job
                print(f"  {NAME} detail {job.source_id} failed: {err}")
            time.sleep(0.3)
    return jobs
