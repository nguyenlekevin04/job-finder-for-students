import json
from datetime import date
from urllib.parse import quote

import pytest

from fetcher import main
from fetcher.store import JsonFileStore
from fetcher.models import Job
from fetcher.sources import (
    amazon, arbeitnow, arbeitsagentur, bosch, fraunhofer, globalfoundries, hzdr, infineon, tu_dresden,
)


@pytest.fixture(autouse=True)
def allow_test_hosts(monkeypatch):
    """The made-up sources "A" and "B" below link to https://A/… and https://B/…."""
    monkeypatch.setitem(main.LINK_HOSTS, "A", ("a",))
    monkeypatch.setitem(main.LINK_HOSTS, "B", ("b",))


def raw(title, company="ACME GmbH", source="A", url=None, posted=None, description=""):
    return Job(source=source, source_id=title, title=title, company=company,
               url=url or f"https://{source}/{quote(title)}", posted_at=posted, description=description)


def test_norm_title_drops_gender_tags():
    assert main.norm_title("Werkstudent Software (m/w/d)") == main.norm_title("Werkstudent  Software (w/m/d)")
    assert main.norm_title("Werkstudent*in Software (all genders)") == "werkstudent software"


def test_strip_company_prefix():
    assert main.strip_company_prefix("ACME GmbH: Werkstudent IT", "ACME GmbH") == "Werkstudent IT"
    assert main.strip_company_prefix("Abschlussarbeit: Embedded Linux", "ACME GmbH") == "Abschlussarbeit: Embedded Linux"


def test_duplicates_are_merged_with_all_links():
    jobs = main.build_jobs([
        raw("Werkstudent Softwareentwicklung (m/w/d)", source="A", posted="2026-10-05"),
        raw("Werkstudent Softwareentwicklung (w/m/d)", company="ACME", source="B", posted="2026-10-01"),
        raw("Werkstudent Marketing", source="A"),
    ])
    assert len(jobs) == 1
    job = next(iter(jobs.values()))
    assert [l["source"] for l in job["links"]] == ["A", "B"]
    assert job["postedAt"] == "2026-10-05"  # the first (highest-priority) source's date wins


def test_later_copy_cannot_take_over_a_job():
    """A job-board copy with the same title/company can't replace the employer's text or link."""
    title, company = "Werkstudent Softwareentwicklung (m/w/d)", "Infineon"
    jobs = main.build_jobs([
        Job(source="Infineon", source_id="1", title=title, company=company,
            url="https://jobs.infineon.com/careers/job/1", posted_at="2026-10-20",
            description="Du entwickelst Software für Halbleiter in Dresden."),
        Job(source="Arbeitnow", source_id="x", title=title, company=company,
            url="javascript:alert(1)", posted_at="2026-01-01",
            description="Bewirb dich jetzt über unser Formular und gib deine Bankdaten an. " * 20),
        Job(source="Arbeitnow", source_id="y", title=title, company=company,
            url="https://evil.example/apply", posted_at="2026-01-01", description="Phishing " * 50),
    ])
    job = next(iter(jobs.values()))
    assert job["links"] == [{"source": "Infineon", "url": "https://jobs.infineon.com/careers/job/1"}]
    assert job["postedAt"] == "2026-10-20"
    assert job["snippet"].startswith("Du entwickelst Software")


def test_later_copy_fills_only_empty_fields():
    jobs = main.build_jobs([
        raw("Werkstudent Softwareentwicklung", source="A"),
        raw("Werkstudent Softwareentwicklung", source="B", posted="2026-10-01", description="Python " * 30),
    ])
    job = next(iter(jobs.values()))
    assert job["postedAt"] == "2026-10-01"
    assert [l["source"] for l in job["links"]] == ["A", "B"]


def test_snippet_and_english_flag_come_from_the_same_posting():
    jobs = main.build_jobs([
        raw("Werkstudent Softwareentwicklung", source="A"),
        raw("Werkstudent Softwareentwicklung", source="B",
            description="You will build Python services in our English-speaking team. " * 5),
    ])
    job = next(iter(jobs.values()))
    assert job["snippet"].startswith("You will build Python")
    assert job["englishFriendly"] is True


def test_future_posted_dates_are_ignored():
    jobs = main.build_jobs([
        raw("Werkstudent Softwareentwicklung", source="A", posted="2999-01-01"),
        raw("Werkstudent Softwareentwicklung", source="B", posted="2999-02-01"),
        raw("Werkstudent Data Science", source="A", posted="2999-01-01"),
        raw("Werkstudent Data Science", source="B", posted="2026-10-01"),
    ])
    assert sorted(str(j["postedAt"]) for j in jobs.values()) == ["2026-10-01", "None"]


def test_rejected_postings_are_counted_and_reported():
    status = {"A": {"ok": True, "count": 2}, "B": {"ok": True, "count": 1}}
    main.build_jobs([
        raw("Werkstudent Softwareentwicklung", source="A", url="https://evil.example/1"),
        raw("Werkstudent Data Science", source="A", url="javascript:alert(1)"),
        raw("Werkstudent Embedded", source="B"),
    ], status)
    assert status["A"]["rejected"] == 2
    assert "rejected" not in status["B"]
    assert main.health_problems(status, [_Src("A"), _Src("B")]) == [
        "A: 2 postings had a link outside its allowed hosts (LINK_HOSTS); check if the source moved"]


def test_stored_unsafe_links_are_dropped_and_linkless_jobs_removed(monkeypatch, tmp_path):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
    monkeypatch.setattr(main, "load_env", lambda: None)
    out = tmp_path / "jobs.json"
    monkeypatch.setattr(main, "OUTPUT", out)
    good = main.build_jobs([raw("Werkstudent Softwareentwicklung", source="A")])
    jid = next(iter(good))
    stored = {
        **good[jid], "firstSeen": "2026-10-01", "lastSeen": date.today().isoformat(),
        # Bosch and Arbeitnow didn't run today, so only safe_link can drop their links.
        "links": [*good[jid]["links"], {"source": "Bosch", "url": "https://evil.example/x"}],
    }
    bad = {**stored, "id": "bad", "title": "Werkstudent Phishing",
           "links": [{"source": "Arbeitnow", "url": "javascript:alert(1)"}]}
    closed = {**stored, "id": "closed", "title": "Werkstudent Alt", "links": [{"source": "A", "url": "https://a/alt"}]}
    out.write_text(json.dumps({"jobs": [stored, bad, closed]}))
    status = {"A": {"ok": True, "count": 1}, "B": {"ok": True, "count": 1}}
    # B's posting is rejected (https://a/ isn't B's host): it must not count as "still listed".
    monkeypatch.setattr(main, "run_sources", lambda: (
        [raw("Werkstudent Softwareentwicklung", source="A"),
         raw("Werkstudent Alt", source="B", url="https://a/alt")], status))
    main.main([])
    saved = {j["id"]: j for j in json.loads(out.read_text())["jobs"]}
    assert set(saved) == {jid}
    assert saved[jid]["links"] == good[jid]["links"]


def test_safe_link():
    assert main.safe_link("Arbeitnow", "https://www.arbeitnow.com/jobs/x")
    assert main.safe_link("Arbeitnow", "https://arbeitnow.com/jobs/x")
    assert main.safe_link("TU Dresden", "https://www.verw.tu-dresden.de/StellAus/stelle.asp?id=1&lang=de")
    assert not main.safe_link("Arbeitnow", "http://www.arbeitnow.com/jobs/x")
    assert not main.safe_link("Arbeitnow", "javascript:alert(1)")
    assert not main.safe_link("Arbeitnow", "https://arbeitnow.com.evil.example/jobs/x")
    assert not main.safe_link("Arbeitnow", "https://evilarbeitnow.com/jobs/x")
    assert not main.safe_link("Arbeitnow", "https://www.arbeitnow.com@evil.example/")
    assert not main.safe_link("Arbeitnow", "https://evil.example\\@www.arbeitnow.com/")
    assert not main.safe_link("Arbeitnow", "https://jobs.infineon.com/careers/job/1")  # another source's host
    assert not main.safe_link("Unknown source", "https://www.arbeitnow.com/jobs/x")


def test_every_fixture_link_passes_safe_link(fixture_text):
    def load(name):
        return json.loads(fixture_text(name))
    parsed = [
        *tu_dresden.parse(fixture_text("tu_dresden.html"), "Informatik"),
        *fraunhofer.parse_list(fixture_text("fraunhofer_list.html")),
        *hzdr.parse(fixture_text("hzdr.html")),
        *infineon.parse_search(load("infineon.json")),
        *globalfoundries.parse_list(load("globalfoundries.json")),
        *bosch.parse_list(load("bosch.json")),
        *amazon.parse(load("amazon.json")),
        *arbeitsagentur.parse(load("arbeitsagentur.json")),
        *arbeitnow.parse(load("arbeitnow.json")),
    ]
    assert {j.source for j in parsed} == {s.NAME for s in main.SOURCES}
    assert [j.url for j in parsed if not main.safe_link(j.source, j.url)] == []


def test_json_store_round_trip_drops_removed(tmp_path):
    out = tmp_path / "jobs.json"
    store = JsonFileStore(out)
    jobs = [{"id": "a", "firstSeen": "2026-09-01", "lastSeen": "2026-10-28", "postedAt": None},
            {"id": "b", "firstSeen": "2026-10-28", "lastSeen": "2026-10-28", "postedAt": "2026-10-20"}]
    assert store.save(jobs, {"b"}, {"A": {"ok": True, "count": 1}}, "2026-10-28T05:00:00+00:00") == 1
    assert set(store.previous()) == {"a"}
    assert json.loads(out.read_text())["sources"] == {"A": {"ok": True, "count": 1}}


def test_checker_turns_errors_into_unknown(monkeypatch):
    class Broken:
        NAME = "B"

        @staticmethod
        def check(url):
            raise TimeoutError("slow")
    monkeypatch.setattr(main.time, "sleep", lambda s: None)
    check = main.make_checker([Broken])
    assert check("B", "https://x") == "unknown"
    assert check("No such source", "https://x") == "unknown"


def test_require_db_refuses_json_fallback(monkeypatch):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
    monkeypatch.setattr(main, "load_env", lambda: None)
    monkeypatch.setattr(main, "run_sources", lambda: (_ for _ in ()).throw(AssertionError("must not fetch")))
    assert main.main(["--require-db"]) == 2


def test_redact_hides_query_strings():
    msg = "404 for url: https://api.example.com/v1/search/1?app_id=A&app_key=SECRET&what=x"
    assert "SECRET" not in main.redact(msg)
    assert "SECRET" not in main.redact("Max retries exceeded with url: /v1/search?app_key=SECRET (Caused by x)")
    assert main.redact("did the site change?") == "did the site change?"


class _Src:
    def __init__(self, name, may_be_empty=False):
        self.NAME = name
        if may_be_empty:
            self.MAY_BE_EMPTY = True


def test_health_problems_flags_failed_and_empty_sources():
    status = {
        "Good": {"ok": True, "count": 12},
        "Broken": {"ok": False, "count": 0, "error": "HTTP 500"},
        "Empty": {"ok": True, "count": 0},
        "Small": {"ok": True, "count": 0},
        "NoKey": {"ok": False, "count": 0, "skipped": True},
    }
    problems = main.health_problems(status, [_Src("Good"), _Src("Broken"), _Src("Empty"), _Src("Small", True)])
    assert problems == ["Broken failed: HTTP 500", "Empty returned no postings (did the site change?)"]


def test_main_saves_then_fails_when_a_source_is_broken(monkeypatch, tmp_path):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
    monkeypatch.setattr(main, "load_env", lambda: None)
    monkeypatch.setattr(main, "OUTPUT", tmp_path / "jobs.json")
    status = {"Good": {"ok": True, "count": 1}, "Broken": {"ok": False, "count": 0, "error": "boom"}}
    monkeypatch.setattr(main, "run_sources", lambda: ([raw("Werkstudent Softwareentwicklung")], status))
    assert main.main([]) == 3
    saved = json.loads((tmp_path / "jobs.json").read_text())
    assert saved["count"] == 1  # the healthy source's jobs were still saved


def test_production_writes_need_the_ci_flag(monkeypatch):
    monkeypatch.setattr(main, "load_env", lambda: None)
    monkeypatch.setenv("SUPABASE_URL", f"https://{main.PRODUCTION_PROJECT_REF}.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "test-key")
    monkeypatch.delenv("ALLOW_PRODUCTION_WRITE", raising=False)
    monkeypatch.setattr(main, "run_sources", lambda: (_ for _ in ()).throw(AssertionError("must not fetch")))
    assert main.main(["--require-db"]) == 4


def test_production_guard_ignores_url_case(monkeypatch):
    monkeypatch.setattr(main, "load_env", lambda: None)
    monkeypatch.setenv("SUPABASE_URL", f"https://{main.PRODUCTION_PROJECT_REF.upper()}.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "test-key")
    monkeypatch.delenv("ALLOW_PRODUCTION_WRITE", raising=False)
    monkeypatch.setattr(main, "run_sources", lambda: (_ for _ in ()).throw(AssertionError("must not fetch")))
    assert main.main(["--require-db"]) == 4


def test_production_flag_lets_the_scheduled_run_through(monkeypatch):
    monkeypatch.setattr(main, "load_env", lambda: None)
    monkeypatch.setenv("SUPABASE_URL", f"https://{main.PRODUCTION_PROJECT_REF}.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "test-key")
    monkeypatch.setenv("ALLOW_PRODUCTION_WRITE", "1")
    monkeypatch.setattr(main, "run_sources", lambda: ([], {"A": {"ok": False, "count": 0, "error": "x"}}))
    assert main.main(["--require-db"]) == 1  # got past the guard; all sources "failed", so nothing is written



def test_accepted_removals_from_env(monkeypatch):
    monkeypatch.setenv("ACCEPT_REMOVALS", " HZDR, Bosch ,,")
    assert main.accepted_removals() == {"HZDR", "Bosch"}
    monkeypatch.setenv("ACCEPT_REMOVALS", "")
    assert main.accepted_removals() == set()


def test_arbeitnow_country_sites_are_allowed():
    for host in ("www.arbeitnow.fr", "www.arbeitnow.ch", "www.arbeitnow.nl", "www.arbeitnow.co.uk"):
        assert main.safe_link("Arbeitnow", f"https://{host}/jobs/companies/x/y-1")
    assert not main.safe_link("Arbeitnow", "https://www.arbeitnow.evil/jobs/x")


def test_hours_and_pay_are_extracted_and_filled_as_pairs():
    jobs = main.build_jobs([
        raw("Werkstudent Softwareentwicklung (m/w/d)", source="A", description="Software, Python, Git. 15 €/Std."),
        raw("Werkstudent Softwareentwicklung (w/m/d)", source="B",
            description="Python, Git. 10-20 h/Woche, 1.200 €/Monat"),
    ])
    (job,) = jobs.values()
    # The first posting has pay but no hours: hours come from the second, pay stays the first's.
    assert (job["hoursMin"], job["hoursMax"]) == (10, 20)
    assert (job["payAmount"], job["payUnit"]) == (15.0, "hour")


def test_hours_and_pay_default_to_none():
    (job,) = main.build_jobs([raw("Werkstudent Softwareentwicklung", source="A")]).values()
    assert [job[k] for k in ("hoursMin", "hoursMax", "payAmount", "payUnit")] == [None] * 4


GF_COMPANY_BA = "GlobalFoundries Management Services GmbH & Co. KG"


def gf(title):
    return raw(title, company="GlobalFoundries", source="GlobalFoundries",
               url=f"https://globalfoundries.wd1.myworkdayjobs.com/External/job/{quote(title)}")


def ba(title, company=GF_COMPANY_BA):
    return raw(title, company=company, source="Arbeitsagentur",
               url=f"https://www.arbeitsagentur.de/jobsuche/jobdetail/{quote(title)}")


@pytest.mark.parametrize("full,cut", [
    # Real staging pairs (GlobalFoundries feed vs. Arbeitsagentur's cut-off copy).
    ("Werkstudent*in im Bereich Machine Learning & Virtual Metrology", "Werkstudent*in im Bereich Machine Learning & Virt"),
    ("Werkstudent*in im Bereich TCAD – Machine Learning & KI", "Werkstudent*in im Bereich TCAD – Machine Learning"),
])
def test_globalfoundries_cut_off_copy_merges_into_full_posting(full, cut):
    jobs = main.build_jobs([gf(full), ba(cut)])
    (job,) = jobs.values()
    assert job["id"] == main.job_id(full, "GlobalFoundries")  # ids don't change
    assert job["title"] == full and job["company"] == "GlobalFoundries"
    assert [l["source"] for l in job["links"]] == ["GlobalFoundries", "Arbeitsagentur"]


def test_globalfoundries_twin_needs_one_long_prefix_match():
    # Shorter than 40 characters: too generic to merge.
    jobs = main.build_jobs([gf("Werkstudent*in Machine Learning KI"), ba("Werkstudent*in Machine Learning")])
    assert len(jobs) == 2
    # Two candidates share the prefix: ambiguous, no merge.
    jobs = main.build_jobs([
        gf("Werkstudent*in im Bereich TCAD – Machine Learning & KI"),
        gf("Werkstudent*in im Bereich TCAD – Machine Learning & Data"),
        ba("Werkstudent*in im Bereich TCAD – Machine Learning"),
    ])
    assert len(jobs) == 3
    # Another company with the same cut-off title isn't merged.
    jobs = main.build_jobs([
        gf("Werkstudent*in im Bereich TCAD – Machine Learning & KI"),
        ba("Werkstudent*in im Bereich TCAD – Machine Learning", company="Infineon Technologies Dresden GmbH"),
    ])
    assert len(jobs) == 2


def test_globalfoundries_twin_needs_another_source():
    # One feed doesn't list a posting twice: same-source prefix titles are two jobs.
    jobs = main.build_jobs([
        gf("Working Student Machine Learning for Process Control"),
        gf("Working Student Machine Learning for Process Control and Yield"),
    ])
    assert len(jobs) == 2
    # Arbeitsagentur's cut-off copies of two jobs still merge with their own feed posting.
    jobs = main.build_jobs([
        gf("Werkstudent*in im Bereich Machine Learning & Virtual Metrology"),
        gf("Werkstudent*in im Bereich TCAD – Machine Learning & KI"),
        ba("Werkstudent*in im Bereich Machine Learning & Virt"),
    ])
    assert len(jobs) == 2
    assert sum(len(j["links"]) for j in jobs.values()) == 3


def test_is_globalfoundries():
    assert main.is_globalfoundries("GlobalFoundries")
    assert main.is_globalfoundries(GF_COMPANY_BA)
    assert not main.is_globalfoundries("GlobalFoundriesX GmbH")
