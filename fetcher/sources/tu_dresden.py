"""TU Dresden central job board.

Mostly staff and student-assistant (HiWi) posts, so few results survive the
student filter, but internship and thesis offers do appear now and then.
"""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

from fetcher.net import de_date, get_text
from fetcher.models import Job

NAME = "TU Dresden"

LIST = "https://tu-dresden.de/tu-dresden/arbeiten-an-der-tud/stellenangebote/stellenangebote"

# Faculty/unit filter id -> hint added to tags, so the classifier knows the area.
UNITS = {
    "fakinf": "Informatik",
    "fakeui": "Elektrotechnik Informationstechnik",
    "zentrein": "",
    "exzellenz": "",
    "sondfor": "",
    "fakmw": "",
    "fakphy": "",
}


def parse(html: str, unit_hint: str = "") -> list[Job]:
    soup = BeautifulSoup(html, "html.parser")
    jobs = []
    for a in soup.select('a[href*="StellAus/stelle.asp"]'):
        m = re.search(r"id=(\d+)", a.get("href", ""))
        if not m:
            continue
        job_id = m.group(1)
        title = re.sub(r"\s+", " ", a.get_text(" ")).strip()
        li = a.find_parent("li")
        li_text = li.get_text("\n") if li else ""
        lines = [s.strip() for s in li_text.split("\n") if s.strip()]
        title_parts = {s.strip() for s in a.get_text("\n").split("\n")}
        unit = next((l for l in lines if l not in title_parts and not l.startswith("(")
                     and not l.startswith("Bewerbungsschluss") and l != "*" and not l.startswith(", ")
                     and not re.match(r"^[,)]", l)), "")
        deadline = re.search(r"Bewerbungsschluss:\s*([\d.]+)", li_text)
        jobs.append(Job(
            source=NAME,
            source_id=job_id,
            title=title,
            company=f"TU Dresden – {unit}" if unit else "TU Dresden",
            url=f"https://www.verw.tu-dresden.de/StellAus/stelle.asp?id={job_id}&lang=de",
            deadline=de_date(deadline.group(1)) if deadline else None,
            tags=f"{unit} {unit_hint}".strip(),
        ))
    return jobs


def fetch() -> list[Job]:
    by_id: dict[str, Job] = {}
    for unit, hint in UNITS.items():
        html = get_text(LIST, params={"lang": "de", "style": "cms2", "suche": "1", "strukturId": unit})
        for job in parse(html, hint):
            by_id.setdefault(job.source_id, job)
    return list(by_id.values())
