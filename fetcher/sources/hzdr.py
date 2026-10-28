"""HZDR (Helmholtz-Zentrum Dresden-Rossendorf): internships, theses, student jobs."""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

from fetcher.net import clean_text, get_text
from fetcher.models import Job

NAME = "HZDR"

LIST = "https://www.hzdr.de/db/!ContMan.Angebote.Liste?pSelAnzeige=1&pSelMenu=0&pNid=3234&pLang=en"


def parse(html: str) -> list[Job]:
    soup = BeautifulSoup(html, "html.parser")
    jobs = []
    for h2 in soup.select('h2[id^="BId"]'):
        job_id = h2["id"].removeprefix("BId")
        # Everything between this <h2> and the next <hr> belongs to the posting.
        parts = []
        for sib in h2.find_next_siblings():
            if sib.name in ("hr", "h2"):
                break
            parts.append(sib)
        kind = next((p.get_text(" ", strip=True) for p in parts if p.name == "h3"), "")
        text = clean_text(" ".join(str(p) for p in parts))
        dept = re.search(r"Department:\s*(.+?)\s+Contact:", text)
        jobs.append(Job(
            source=NAME,
            source_id=job_id,
            title=re.sub(r"\s*\(Id \d+\)\s*$", "", h2.get_text(" ", strip=True)),
            company=f"HZDR – {dept.group(1).strip()}" if dept else "HZDR",
            url=f"{LIST}#BId{job_id}",
            tags=kind,  # e.g. "Master theses / Compulsory internship"
            description=text[:4000],
        ))
    return jobs


def fetch() -> list[Job]:
    return parse(get_text(LIST))
