"""Fraunhofer job portal, filtered to Dresden (IWS, IIS/EAS, IKTS, IPMS, IVI, ...)."""
from __future__ import annotations

import re
import time

from bs4 import BeautifulSoup

from fetcher.net import clean_text, de_date, get_text
from fetcher.models import Job

NAME = "Fraunhofer"

BASE = "https://jobs.fraunhofer.de"
PAGE_SIZE = 25
MAX_ROWS = 400

# Only titles like these are worth opening for the full description.
STUDENT_HINT = re.compile(
    r"werkstudent|praktik|intern|thesis|abschlussarbeit|bachelor|master|diplom|studienarbeit|student", re.I)


def parse_list(html: str) -> list[Job]:
    soup = BeautifulSoup(html, "html.parser")
    jobs = []
    for row in soup.select("tr.data-row"):
        a = row.select_one("span.jobTitle.hidden-phone a.jobTitle-link") or row.select_one("a.jobTitle-link")
        if not a or not a.get("href"):
            continue
        href = a["href"]
        m = re.search(r"/(\d+)/?$", href)
        facility = row.select_one("td.colFacility .jobFacility")
        place = row.select_one("td.colShifttype .jobShifttype")
        jobs.append(Job(
            source=NAME,
            source_id=m.group(1) if m else href,
            title=a.get_text(strip=True),
            company=f"Fraunhofer {facility.get_text(strip=True)}" if facility else "Fraunhofer",
            url=BASE + href,
            location=place.get_text(strip=True) if place else "Dresden",
        ))
    return jobs


def parse_detail(html: str) -> tuple[str, str | None]:
    """Return (description text, posted date) from a job detail page."""
    soup = BeautifulSoup(html, "html.parser")
    body = soup.select_one(".jobdescription") or soup.select_one('[itemprop="description"]')
    date_el = soup.select_one('[data-careersite-propertyid="date"]')
    date = de_date(date_el.get_text(strip=True)) if date_el else None
    return (clean_text(str(body))[:4000] if body else ""), date


def is_last_page(page: list[Job]) -> bool:
    """The portal has no total; a page shorter than PAGE_SIZE is the last one."""
    return len(page) < PAGE_SIZE


def fetch() -> list[Job]:
    jobs: list[Job] = []
    for start in range(0, MAX_ROWS, PAGE_SIZE):
        html = get_text(f"{BASE}/search/", params={"q": "", "locationsearch": "Dresden", "startrow": start})
        page = parse_list(html)
        jobs.extend(page)
        if is_last_page(page):
            break
        time.sleep(0.4)
    else:  # a cut-off list would make the missing postings count as closed
        raise RuntimeError(f"{NAME}: more than {MAX_ROWS} postings; raise MAX_ROWS")

    for job in (j for j in jobs if STUDENT_HINT.search(j.title)):
        try:
            job.description, job.posted_at = parse_detail(get_text(job.url))
        except Exception:  # keep the title-only job if the detail page fails
            pass
        time.sleep(0.25)
    return jobs
