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


def test_arbeitnow_keeps_only_board_cities_or_remote(fixture_text):
    data = json.loads(fixture_text("arbeitnow.json"))
    jobs = arbeitnow.parse(data)
    # The fixture has 8 remote postings, 4 on-site in Berlin (a board city) and 4 elsewhere.
    assert len(jobs) == 12
    assert all(j.remote or j.city == "berlin" for j in jobs)
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



def test_arbeitnow_tags_the_city_and_keeps_remote_cityless():
    from fetcher.sources import arbeitnow
    data = {"data": [
        {"slug": "a", "title": "Werkstudent Data", "url": "https://www.arbeitnow.com/a", "location": "Leipzig"},
        {"slug": "b", "title": "Working Student ML", "url": "https://www.arbeitnow.com/b", "location": "Munich", "remote": True},
        {"slug": "c", "title": "Werkstudent IT", "url": "https://www.arbeitnow.com/c", "location": "Hamburg"},
    ]}
    jobs = {j.source_id: j for j in arbeitnow.parse(data)}
    assert jobs["a"].city == "leipzig" and not jobs["a"].remote
    assert jobs["b"].city == "" and jobs["b"].remote
    assert "c" not in jobs


def test_arbeitsagentur_sets_the_searched_city():
    from fetcher.sources import arbeitsagentur
    data = {"ergebnisliste": [{"referenznummer": "1", "stellenangebotsTitel": "Werkstudent IT",
                               "stellenlokationen": [{"adresse": {"ort": "Markkleeberg"}}]}]}
    job = arbeitsagentur.parse(data, "leipzig")[0]
    assert job.city == "leipzig" and job.location == "Markkleeberg"


def test_greenhouse_keeps_berlin_postings_with_text(fixture_text):
    from fetcher.sources import greenhouse
    jobs = greenhouse.parse(json.loads(fixture_text("greenhouse.json")), "getyourguide", "GetYourGuide")
    assert len(jobs) == 4 and all(j.city == "berlin" and j.company == "GetYourGuide" for j in jobs)
    assert all(j.url.startswith("https://job-boards.greenhouse.io/getyourguide/jobs/") for j in jobs)
    assert all(j.description and "<" not in j.description and "&lt;" not in j.description for j in jobs)
    assert all(j.posted_at and len(j.posted_at) == 10 for j in jobs)


def test_smartrecruiters_keeps_berlin_only():
    from fetcher.sources import smartrecruiters
    data = {"content": [
        {"id": "1", "name": "Working Student Data", "location": {"city": "Berlin"}, "releasedDate": "2026-10-20T10:00:00Z"},
        {"id": "2", "name": "Working Student BI", "location": {"city": "Hamburg"}},
    ]}
    jobs = smartrecruiters.parse_list(data, "DeliveryHero", "Delivery Hero")
    assert [j.source_id for j in jobs] == ["DeliveryHero:1"]
    assert jobs[0].url == "https://jobs.smartrecruiters.com/DeliveryHero/1" and jobs[0].city == "berlin"


def test_smartrecruiters_reads_other_board_cities():
    from fetcher.sources import smartrecruiters
    data = {"content": [
        {"id": "7", "name": "Working Student (f/m/d) Cloud", "location": {"city": "Dresden"}},
        {"id": "8", "name": "Working Student Data", "location": {"city": "Walldorf"}},
    ]}
    jobs = smartrecruiters.parse_list(data, "SAPITBusinessSysteme", "SAP", "dresden")
    assert [(j.source_id, j.city, j.location, j.company) for j in jobs] == [
        ("SAPITBusinessSysteme:7", "dresden", "Dresden", "SAP")]


def test_deloitte_list_has_titles_and_board_cities(fixture_text):
    from fetcher.sources import deloitte
    jobs = deloitte.parse_list(fixture_text("deloitte_list.html"))
    assert len(jobs) == 10
    audit = jobs[0]
    assert audit.title == "Praktikant Audit (m/w/d)"
    assert audit.url.startswith("https://job.deloitte.com/job-praktikant-audit-mwd-_")
    assert audit.city == "dresden"  # first board city in CITIES order
    assert audit.location == "Dresden, Leipzig, Berlin"
    assert audit.cities == ["dresden", "leipzig", "berlin"]
    assert any(j.city == "" and j.location == "" for j in jobs)  # only cities outside our boards
    assert all("&amp;" not in j.title for j in jobs)


def test_deloitte_detail_reads_jobposting_data(fixture_text):
    from fetcher.sources import deloitte
    desc, posted = deloitte.parse_detail(fixture_text("deloitte_job.html"))
    assert posted == "2026-10-27"
    assert desc.startswith("Du willst im Bereich Consulting") and "<" not in desc
    assert deloitte.parse_detail("<html></html>") == ("", None)


def test_pwc_keeps_student_posts_in_board_cities(fixture_text):
    from fetcher.sources import pwc
    total, postings = pwc.parse_search(fixture_text("pwc_search.html"))
    assert total == 369 and len(postings) == 10
    jobs = [j for j in map(pwc.to_job, postings) if j]
    assert [j.source_id for j in jobs] == ["1527"]  # Düsseldorf-only and non-student posts are skipped
    j = jobs[0]
    assert j.url == "https://jobs.pwc.de/de/de/job/1527" and j.city == "berlin" and j.location == "Berlin"
    assert j.posted_at and len(j.posted_at) == 10 and j.description


def test_pwc_detail_has_the_full_description(fixture_text):
    from fetcher.sources import pwc
    desc = pwc.parse_detail(fixture_text("pwc_job.html"))
    assert len(desc) > 1000 and "<" not in desc


def test_deloitte_raises_instead_of_returning_a_short_list(monkeypatch, fixture_text):
    import pytest
    from fetcher.sources import deloitte
    pages = {1: fixture_text("deloitte_list.html"), 2: "<html>Too many requests</html>"}
    monkeypatch.setattr(deloitte, "get_text", lambda url, params=None: pages[params["page"]])
    monkeypatch.setattr(deloitte.time, "sleep", lambda s: None)
    with pytest.raises(RuntimeError, match="added no postings"):
        deloitte.fetch()


def test_pwc_rereads_when_a_posting_shifted_and_fails_if_still_short(monkeypatch):
    import pytest
    from fetcher.sources import pwc

    def page(ids, total):
        jobs = [{"jobId": i, "title": f"Job {i}", "multi_location": ["Hamburg, DEU"]} for i in ids]
        return '<script>phApp.ddo = {"eagerLoadRefineSearch": {"totalHits": %d, "data": {"jobs": %s}}}; phApp.x</script>' % (
            total, __import__("json").dumps(jobs))

    calls = []
    def short(url, params=None):
        calls.append(params["from"])
        return page(list(range(params["from"], params["from"] + 10))[:9], 20)  # always one missing per page
    monkeypatch.setattr(pwc, "get_text", short)
    monkeypatch.setattr(pwc.time, "sleep", lambda s: None)
    with pytest.raises(RuntimeError, match="feed ended early"):
        pwc.fetch()
    assert calls == [0, 10, 0, 10]  # read twice before giving up
