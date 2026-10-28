"""Parser tests against saved real responses (fixtures/)."""
import json

from fetcher.sources import arbeitnow, arbeitsagentur, fraunhofer, hzdr, tu_dresden


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
