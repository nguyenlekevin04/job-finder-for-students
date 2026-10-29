import json

from fetcher import main
from fetcher.store import JsonFileStore
from fetcher.models import Job


def raw(title, company="ACME GmbH", source="A", url=None, posted=None, description=""):
    return Job(source=source, source_id=title, title=title, company=company,
               url=url or f"https://{source}/{title}", posted_at=posted, description=description)


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
    assert job["postedAt"] == "2026-10-01"


def test_history_keeps_first_seen_and_drops_old(tmp_path):
    out = tmp_path / "jobs.json"
    out.write_text(json.dumps({"jobs": [
        {"id": "still-here", "firstSeen": "2026-09-01", "lastSeen": "2026-10-27"},
        {"id": "recently-gone", "firstSeen": "2026-09-01", "lastSeen": "2026-10-25", "postedAt": None},
        {"id": "long-gone", "firstSeen": "2026-08-01", "lastSeen": "2026-10-01", "postedAt": None},
    ]}))
    current = {"still-here": {"id": "still-here", "postedAt": None},
               "brand-new": {"id": "brand-new", "postedAt": None}}
    merged = {j["id"]: j for j in JsonFileStore(out).merge(current, "2026-10-28")}

    assert merged["still-here"]["firstSeen"] == "2026-09-01"
    assert merged["still-here"]["lastSeen"] == "2026-10-28"
    assert merged["brand-new"]["firstSeen"] == "2026-10-28"
    assert "recently-gone" in merged
    assert "long-gone" not in merged


def test_require_db_refuses_json_fallback(monkeypatch):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
    monkeypatch.setattr(main, "load_env", lambda: None)
    monkeypatch.setattr(main, "run_sources", lambda: (_ for _ in ()).throw(AssertionError("must not fetch")))
    assert main.main(["--require-db"]) == 2


def test_redact_hides_query_strings():
    msg = "404 for url: https://api.adzuna.com/v1/search/1?app_id=A&app_key=SECRET&what=x"
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

