"""Employers on SmartRecruiters (public postings API): Delivery Hero and Vattenfall in Berlin,
SAP in Dresden and Berlin (SAP moved its careers site to SmartRecruiters in 2026).

Same API as the Bosch source, filtered to each company's board cities. The list has no descriptions, so the
full posting is fetched only for titles that look like student jobs. Each company's
list per city must fit in one page, or the source fails (a cut-off list would make the
missing postings count as closed).
"""
from __future__ import annotations

import time

from fetcher.classify import is_student_title
from fetcher.models import CITIES, Job
from fetcher.net import get_json, to_day
from fetcher.sources.bosch import _label, parse_detail

NAME = "SmartRecruiters"

API = "https://api.smartrecruiters.com/v1/companies/{company}/postings"
SITE = "https://jobs.smartrecruiters.com/{company}/{id}"
PAGE = 100

# SmartRecruiters company id -> (name as students know it, board cities to read).
COMPANIES: dict[str, tuple[str, tuple[str, ...]]] = {
    "DeliveryHero": ("Delivery Hero", ("berlin",)),
    "Vattenfall": ("Vattenfall", ("berlin",)),
    "SAPITBusinessSysteme": ("SAP", ("dresden", "berlin")),
}


def parse_list(data: dict, company_id: str, company: str, city: str = "berlin") -> list[Job]:
    jobs = []
    for p in data.get("content") or []:
        loc = p.get("location") or {}
        if not (p.get("id") and p.get("name")) or (loc.get("city") or "").lower() != CITIES[city].lower():
            continue
        jobs.append(Job(
            source=NAME,
            source_id=f"{company_id}:{p['id']}",
            title=p["name"].strip(),
            company=company,
            url=SITE.format(company=company_id, id=p["id"]),
            location=CITIES[city],
            city=city,
            posted_at=to_day(p.get("releasedDate")),
            tags=" ".join(filter(None, [_label(p.get("experienceLevel")), _label(p.get("function"))])),
        ))
    return jobs


def fetch() -> list[Job]:
    jobs: list[Job] = []
    for company_id, (company, cities) in COMPANIES.items():
        for city in cities:
            data = get_json(API.format(company=company_id), params={"city": CITIES[city], "limit": PAGE})
            if (data.get("totalFound") or 0) > PAGE:
                raise RuntimeError(f"{NAME}: {company} has more than {PAGE} postings in {CITIES[city]}; add paging")
            jobs.extend(parse_list(data, company_id, company, city))
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
