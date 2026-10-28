"""Bundesagentur für Arbeit – official Jobsuche API (public key).

Docs: https://jobsuche.api.bund.dev
"""
from __future__ import annotations

import time
from urllib.parse import quote

from fetcher.net import get_json, to_day
from fetcher.models import Job

NAME = "Arbeitsagentur"

API = "https://rest.arbeitsagentur.de/jobboerse/jobsuche-service/pc/v6/jobs"
HEADERS = {"X-API-Key": "jobboerse-jobsuche"}

# Broad search terms; the classifier filters the results afterwards.
QUERIES = [
    "Werkstudent Informatik",
    "Werkstudent Softwareentwicklung",
    "Werkstudent Data",
    "Werkstudent KI",
    "Werkstudent Machine Learning",
    "Werkstudent IT",
    "Werkstudent Elektrotechnik",
    "Werkstudent Embedded",
    "Working Student",
    "Praktikum Informatik",
    "Praktikum Softwareentwicklung",
    "Praktikum Data Science",
    "Praktikum Machine Learning",
    "Praktikum IT",
    "Praktikum Elektrotechnik",
    "Abschlussarbeit Informatik",
    "Masterarbeit",
    "Bachelorarbeit",
]


def parse(data: dict) -> list[Job]:
    jobs = []
    for j in data.get("ergebnisliste") or []:
        ref = j.get("referenznummer")
        if not ref or not j.get("stellenangebotsTitel"):
            continue
        addr = ((j.get("stellenlokationen") or [{}])[0] or {}).get("adresse") or {}
        jobs.append(Job(
            source=NAME,
            source_id=ref,
            title=j["stellenangebotsTitel"],
            company=j.get("firma") or "Unknown",
            url=f"https://www.arbeitsagentur.de/jobsuche/jobdetail/{quote(ref)}",
            location=addr.get("ort") or "Dresden",
            posted_at=to_day((j.get("veroeffentlichungszeitraum") or {}).get("von")
                             or j.get("datumErsteVeroeffentlichung")),
            tags=", ".join(b for b in dict.fromkeys([j.get("hauptberuf"), *(j.get("alleBerufe") or [])]) if b),
        ))
    return jobs


def fetch() -> list[Job]:
    by_ref: dict[str, Job] = {}
    for was in QUERIES:
        params = {"was": was, "wo": "Dresden", "umkreis": "30", "size": "100", "page": "1"}
        for job in parse(get_json(API, headers=HEADERS, params=params)):
            by_ref.setdefault(job.source_id, job)
        time.sleep(0.3)
    return list(by_ref.values())
