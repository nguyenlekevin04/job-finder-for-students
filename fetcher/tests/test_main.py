import json

from fetcher import main
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


def test_history_keeps_first_seen_and_drops_old(tmp_path, monkeypatch):
    out = tmp_path / "jobs.json"
    monkeypatch.setattr(main, "OUTPUT", out)
    out.write_text(json.dumps({"jobs": [
        {"id": "still-here", "firstSeen": "2026-09-01", "lastSeen": "2026-10-27"},
        {"id": "recently-gone", "firstSeen": "2026-09-01", "lastSeen": "2026-10-25", "postedAt": None},
        {"id": "long-gone", "firstSeen": "2026-08-01", "lastSeen": "2026-10-01", "postedAt": None},
    ]}))
    current = {"still-here": {"id": "still-here", "postedAt": None},
               "brand-new": {"id": "brand-new", "postedAt": None}}
    merged = {j["id"]: j for j in main.merge_history(current, "2026-10-28")}

    assert merged["still-here"]["firstSeen"] == "2026-09-01"
    assert merged["still-here"]["lastSeen"] == "2026-10-28"
    assert merged["brand-new"]["firstSeen"] == "2026-10-28"
    assert "recently-gone" in merged
    assert "long-gone" not in merged
