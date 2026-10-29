"""Parser tests against saved real responses (fixtures/)."""
import json

import requests

from fetcher import net
from datetime import date

from fetcher.sources import (
    amazon, arbeitnow, arbeitsagentur, bosch, fraunhofer, globalfoundries, hzdr, infineon, tu_dresden,
)


def test_arbeitsagentur(fixture_text):
    jobs = arbeitsagentur.parse(json.loads(fixture_text("arbeitsagentur.json")))
    assert len(jobs) == 2
    j = jobs[0]
    assert j.title == "Werkstudent Softwareentwicklung"
    assert j.company == "OneXip GmbH"
    assert j.location == "Dresden"
    assert j.url.startswith("https://www.arbeitsagentur.de/jobsuche/jobdetail/")
    assert j.posted_at == "2026-10-08"
    assert "Informatiker/in" in j.tags


def test_arbeitnow_keeps_only_dresden_or_remote(fixture_text):
    data = json.loads(fixture_text("arbeitnow.json"))
    jobs = arbeitnow.parse(data)
    assert len(jobs) == 8  # fixture has 8 remote + 8 on-site elsewhere
    assert all(j.remote for j in jobs)
    assert all(j.url.startswith("https://www.arbeitnow.com/") for j in jobs)
    assert all(j.posted_at and len(j.posted_at) == 10 for j in jobs)


def test_fraunhofer_list(fixture_text):
    jobs = fraunhofer.parse_list(fixture_text("fraunhofer_list.html"))
    assert len(jobs) == 25
    j = jobs[0]
    assert j.title == "Studentische Hilfskraft zur Softwareentwicklung-Backend"
    assert j.company == "Fraunhofer IVI - Verkehrs- und Infrastruktursysteme"
    assert j.location == "Dresden"
    assert j.source_id == "1408727133"
    assert j.url.startswith("https://jobs.fraunhofer.de/job/")


def test_fraunhofer_detail(fixture_text):
    text, date = fraunhofer.parse_detail(fixture_text("fraunhofer_detail.html"))
    assert date == "2026-10-20"
    assert len(text) > 200


def test_hzdr(fixture_text):
    jobs = hzdr.parse(fixture_text("hzdr.html"))
    assert len(jobs) == 10
    j = jobs[0]
    assert j.source_id == "499"
    assert "(Id" not in j.title
    assert j.tags.startswith("Master theses")
    assert j.company == "HZDR – Processing"
    assert j.url.endswith("#BId499")


def test_tu_dresden(fixture_text):
    jobs = tu_dresden.parse(fixture_text("tu_dresden.html"), "Informatik")
    assert len(jobs) == 3
    j = jobs[0]
    assert j.source_id == "13027"
    assert j.company == "TU Dresden – Professur für Algebraische und logische Grundlagen der Informatik"
    assert j.deadline == "2026-10-30"
    assert "Informatik" in j.tags


def test_arbeitnow_skips_malformed_records():
    data = {"data": [
        {"title": "No slug", "url": "https://x", "remote": True},
        {"slug": "ok", "title": "Werkstudent", "url": "https://www.arbeitnow.com/ok", "remote": True},
    ]}
    assert [j.source_id for j in arbeitnow.parse(data)] == ["ok"]


def _response(body: bytes, content_type: str) -> requests.Response:
    res = requests.Response()
    res._content = body
    res.headers["Content-Type"] = content_type
    res.encoding = requests.utils.get_encoding_from_headers(res.headers)
    return res


def test_get_text_detects_utf8_without_charset(monkeypatch):
    body = "Werkstudent für Prüfstände und Messtechnik in Dresden".encode()
    monkeypatch.setattr(net, "_request", lambda url, **kw: _response(body, "text/html"))
    assert "für Prüfstände" in net.get_text("https://x")


def test_get_text_respects_declared_charset(monkeypatch):
    body = "Prüfung".encode("latin-1")
    monkeypatch.setattr(net, "_request", lambda url, **kw: _response(body, "text/html; charset=ISO-8859-1"))
    assert net.get_text("https://x") == "Prüfung"


# ------------------------------------------------------- employer career sites --

def test_infineon_search_keeps_dresden_jobs(fixture_text):
    jobs = infineon.parse_search(json.loads(fixture_text("infineon.json")))
    assert len(jobs) == 10
    j = jobs[0]
    assert j.company == "Infineon" and j.location == "Dresden"
    assert j.url == "https://jobs.infineon.com/careers/job/563808970723894"
    assert j.posted_at == "2026-06-01"


def test_infineon_detail_drops_the_shared_intro(fixture_text):
    text = infineon.parse_detail(json.loads(fixture_text("infineon_detail.json")))
    assert text.startswith("Deine Rolle")
    assert "#WeAreIn" not in text and "<" not in text


def test_globalfoundries_list_and_relative_dates(fixture_text):
    jobs = globalfoundries.parse_list(json.loads(fixture_text("globalfoundries.json")), date(2026, 10, 29))
    assert len(jobs) == 20
    assert all(j.url.startswith("https://globalfoundries.wd1.myworkdayjobs.com/External/job/") for j in jobs)
    assert jobs[0].source_id == "JR-2404067"
    assert globalfoundries.posted_on("Posted Today", date(2026, 10, 29)) == "2026-10-29"
    assert globalfoundries.posted_on("Posted Yesterday", date(2026, 10, 29)) == "2026-10-28"
    assert globalfoundries.posted_on("Posted 3 Days Ago", date(2026, 10, 29)) == "2026-10-26"
    assert globalfoundries.posted_on("Posted 30+ Days Ago", date(2026, 10, 29)) is None


def test_globalfoundries_detail(fixture_text):
    text, posted = globalfoundries.parse_detail(json.loads(fixture_text("globalfoundries_detail.json")))
    assert posted == "2026-10-13"
    assert text.startswith("Über den Bereich")  # the "Über GF … www.gf.com" blurb is gone
    assert "Bauelementsimulation" in text


def test_bosch_list_and_detail(fixture_text):
    jobs = bosch.parse_list(json.loads(fixture_text("bosch.json")))
    assert len(jobs) == 10
    j = jobs[0]
    assert j.title.startswith("Werkstudent Entwicklung")
    assert j.company == "Bosch" and not j.remote
    assert j.url == "https://jobs.smartrecruiters.com/BoschGroup/744000155231104"
    assert j.tags == "Manufacturing"  # "Not Applicable" placeholders are dropped
    text = bosch.parse_detail(json.loads(fixture_text("bosch_detail.json")))
    assert text.startswith("Während deiner Werkstudententätigkeit")


def test_amazon_keeps_only_dresden(fixture_text):
    jobs = amazon.parse(json.loads(fixture_text("amazon.json")))
    assert len(jobs) == 7  # fixture also has Berlin and Gera
    intern = next(j for j in jobs if "Internship" in j.title)
    assert intern.url.startswith("https://www.amazon.jobs/en/jobs/")
    assert intern.posted_at == "2025-11-21"
    assert amazon.us_date("October  8, 2026") == "2026-10-08"
    assert amazon.us_date("soon") is None


def test_student_jobs_from_employers_get_classified(fixture_text):
    from fetcher.classify import classify
    ifx = infineon.parse_search(json.loads(fixture_text("infineon.json")))
    assert not any(classify(j) for j in ifx if j.title.startswith(("Senior", "Ausbildung")))
    amz = amazon.parse(json.loads(fixture_text("amazon.json")))
    kept = [j.title for j in amz if classify(j)]
    assert kept == ["Software Dev Engineer Internship - Embedded Development (Linux)"]

