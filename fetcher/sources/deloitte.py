"""Deloitte Germany: internships and working-student jobs (job.deloitte.com).

The site's student category lists every internship / Werkstudent posting, 10 per page, with
title and all cities; the board pages through all of it, so the feed is complete. A posting can
name many cities: it goes on the first board city in CITIES order and its location names every
board city it lists. The full posting (description, date) comes from the JobPosting data on its
own page, fetched only for tech-looking titles in our cities, so a run makes ~10 page requests
plus a handful of postings.
"""
from __future__ import annotations

import html
import json
import re
import time

import requests

from fetcher.classify import classify
from fetcher.models import CITIES, Job
from fetcher.net import clean_text, get_text, to_day

NAME = "Deloitte"

SITE = "https://job.deloitte.com"
LIST = f"{SITE}/praktikum-werkstudententaetigkeit-_jtc4"
MAX_PAGES = 30

ROW = re.compile(r'<li class="job-list-item-josi ')
LINK = re.compile(r'href="(/job-[a-z0-9-]+-_(\d+))"[^>]*>([^<]+)</a>')
CITY = re.compile(r'href="/search\?city=[^"]+"[^>]*>([^<]+)</a>')
LD_JSON = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.S)
BY_NAME = {name.lower(): key for key, name in CITIES.items()}


def parse_list(text: str) -> list[Job]:
    """Every posting on one list page, with its board cities ("" when it has none)."""
    jobs = []
    for row in ROW.split(text)[1:]:
        link = LINK.search(row)
        if not link:
            continue
        named = {c.strip().lower() for c in CITY.findall(row)}
        ours = [key for key in CITIES if CITIES[key].lower() in named]
        jobs.append(Job(
            source=NAME,
            source_id=link.group(2),
            title=html.unescape(link.group(3)).strip(),
            company="Deloitte",
            url=SITE + link.group(1),
            location=", ".join(CITIES[k] for k in ours),
            city=ours[0] if ours else "",
        ))
    return jobs


def parse_detail(text: str) -> tuple[str, str | None]:
    """(description, posted day) from the posting's JobPosting data."""
    for block in LD_JSON.findall(text):
        try:
            data = json.loads(block)
        except ValueError:
            continue
        if isinstance(data, dict) and data.get("@type") == "JobPosting":
            return clean_text(data.get("description"))[:4000], to_day(data.get("datePosted"))
    return "", None


def wanted(job: Job) -> bool:
    """In a board city and a tech title: worth fetching the full posting."""
    return bool(job.city) and classify(job) is not None


def fetch() -> list[Job]:
    by_id: dict[str, Job] = {}
    for page in range(1, MAX_PAGES + 1):
        try:
            found = parse_list(get_text(LIST, params={"page": page}))
        except requests.HTTPError as err:
            # The page after the last one answers 404; on the first page it's a real failure.
            if page > 1 and err.response is not None and err.response.status_code == 404:
                break
            raise
        new = [j for j in found if j.source_id not in by_id]
        for j in new:
            by_id[j.source_id] = j
        if not new:  # a repeated page also ends the list
            break
        time.sleep(0.4)
    else:  # a cut-off list would make the missing postings count as closed
        raise RuntimeError(f"{NAME}: more than {MAX_PAGES} pages; raise MAX_PAGES")
    if not by_id:
        raise RuntimeError(f"{NAME}: no postings found; the page layout may have changed")
    jobs = [j for j in by_id.values() if j.city]  # postings outside our cities never become jobs
    for job in jobs:
        if wanted(job):
            # A failure fails the source, so its postings count as unknown, not closed.
            job.description, posted = parse_detail(get_text(job.url))
            job.posted_at = posted or job.posted_at
            time.sleep(0.4)
    return jobs
