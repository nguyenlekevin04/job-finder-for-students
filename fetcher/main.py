"""Fetch every source, keep student tech jobs, merge with history, save them.

Saves to Supabase when SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are set,
otherwise to web/public/jobs.json (see fetcher/store.py).

Run from the repo root:  python fetcher/main.py [--require-db]
"""
from __future__ import annotations

import hashlib
import os
import re
import sys
import time
import traceback
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from fetcher.classify import FIELD_LABELS, classify  # noqa: E402
from fetcher.sources import (  # noqa: E402
    adzuna, amazon, arbeitnow, arbeitsagentur, bosch, fraunhofer, globalfoundries, hzdr, infineon, tu_dresden,
)
from fetcher.store import JsonFileStore, get_store  # noqa: E402

OUTPUT = ROOT / "web" / "public" / "jobs.json"  # local fallback when Supabase isn't configured

# The live site's Supabase project (public: it's also in the site's code). Only the
# scheduled GitHub Action may write to it; it sets ALLOW_PRODUCTION_WRITE=1. Local
# runs and staging use the staging project, so a buggy test run can't reach students.
PRODUCTION_PROJECT_REF = "ywurtulsjybbdfzqfowq"

# Direct employer sources come first: the first link of a merged job is its "Apply now"
# button, and the employer's own page beats a job-board copy.
SOURCES = [
    tu_dresden, fraunhofer, hzdr, infineon, globalfoundries, bosch, amazon,
    arbeitsagentur, arbeitnow, adzuna,
]


def load_env(path: Path = ROOT / ".env") -> None:
    """Minimal .env reader (KEY=value lines). Real env vars win."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip().strip('"').strip("'")
        if value and not os.environ.get(key.strip()):
            os.environ[key.strip()] = value


GENDER = re.compile(r"\((?:[mwfdx*]\s*/\s*){1,3}[mwfdx*]\)|\(all genders?\)|\(gn\)|\(d/w/m\)|\*(?:in|innen)\b", re.I)
LEGAL = re.compile(r"\b(gmbh|ag|se|kg|co|mbh|ug|e\.?\s?v|haftungsbeschränkt|inc|ltd)\b\.?", re.I)


def norm_title(title: str) -> str:
    t = GENDER.sub(" ", title.lower())
    t = re.sub(r"[^\wäöüß+#]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def norm_company(company: str) -> str:
    c = LEGAL.sub(" ", company.lower())
    c = re.sub(r"[^\wäöüß]+", " ", c)
    return re.sub(r"\s+", " ", c).strip()


def strip_company_prefix(title: str, company: str) -> str:
    """'ACME GmbH: Werkstudent X' -> 'Werkstudent X' when the prefix is the company."""
    m = re.match(r"^\s*([^:]{2,80}):\s+(.+)$", title)
    if not m:
        return title
    prefix, rest = norm_company(m.group(1)), norm_company(company)
    if prefix and rest and (prefix in rest or rest in prefix):
        return m.group(2)
    return title


def job_id(title: str, company: str) -> str:
    key = f"{norm_title(title)}|{norm_company(company)}"
    return hashlib.sha1(key.encode()).hexdigest()[:12]


def redact(text: str) -> str:
    """Drop URL query strings: they can hold API keys (Adzuna). Errors are saved to the
    public fetch_runs table and printed in CI logs."""
    return re.sub(r"\?[^\s'\"]*=[^\s'\"]*", "?…", text)


def safe_error(err: Exception) -> str:
    return redact(str(err))[:200]


def health_problems(status: dict, sources: list = SOURCES) -> list[str]:
    """Sources that look broken: they failed, or found nothing although they normally do.

    A scraper whose site changed usually returns 0 postings instead of failing, so an
    empty result counts too, unless the source sets MAY_BE_EMPTY.
    """
    may_be_empty = {s.NAME for s in sources if getattr(s, "MAY_BE_EMPTY", False)}
    problems = []
    for name, s in status.items():
        if s.get("skipped"):
            continue
        if not s["ok"]:
            problems.append(f"{name} failed: {s.get('error', '')}")
        elif s["count"] == 0 and name not in may_be_empty:
            problems.append(f"{name} returned no postings (did the site change?)")
    return problems


def run_sources() -> tuple[list, dict]:
    raw, status = [], {}
    for src in SOURCES:
        name = src.NAME
        if hasattr(src, "is_enabled") and not src.is_enabled():
            status[name] = {"ok": False, "count": 0, "skipped": True, "error": "No API key set"}
            print(f"- {name}: skipped (no API key)")
            continue
        started = time.time()
        try:
            jobs = src.fetch()
            raw.extend(jobs)
            status[name] = {"ok": True, "count": len(jobs)}
            print(f"✓ {name}: {len(jobs)} postings ({time.time() - started:.0f}s)")
        except Exception as err:  # one broken source must not stop the rest
            status[name] = {"ok": False, "count": 0, "error": safe_error(err)}
            print(f"✗ {name}: FAILED – {safe_error(err)}")
            print(redact(traceback.format_exc()))
    return raw, status


def build_jobs(raw: list) -> dict[str, dict]:
    """Classify and merge duplicates. Returns id -> job dict."""
    jobs: dict[str, dict] = {}
    for r in raw:
        r.title = re.sub(r"\s+", " ", strip_company_prefix(r.title, r.company)).strip()
        tags = classify(r)
        if not tags:
            continue
        jid = job_id(r.title, r.company)
        link = {"source": r.source, "url": r.url}
        if jid in jobs:
            j = jobs[jid]
            if all(l["url"] != r.url for l in j["links"]):
                j["links"].append(link)
            if r.posted_at and (not j["postedAt"] or r.posted_at < j["postedAt"]):
                j["postedAt"] = r.posted_at
            if len(tags["snippet"]) > len(j["snippet"]):
                j["snippet"] = tags["snippet"]
            j["englishFriendly"] = j["englishFriendly"] or tags["englishFriendly"]
            j["fields"] = sorted(set(j["fields"]) | set(tags["fields"]), key=list(FIELD_LABELS).index)
            continue
        jobs[jid] = {
            "id": jid,
            "title": re.sub(r"\s+", " ", r.title).strip(),
            "company": r.company.strip(),
            "location": r.location,
            "remote": r.remote,
            **{k: tags[k] for k in ("type", "types", "fields", "englishFriendly")},
            "postedAt": r.posted_at,
            "deadline": r.deadline,
            "links": [link],
            "snippet": tags["snippet"],
        }
    return jobs


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    load_env()
    store = get_store(OUTPUT)
    if "--require-db" in argv and isinstance(store, JsonFileStore):
        print("SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY are not set – refusing to fall back to jobs.json.")
        return 2
    if PRODUCTION_PROJECT_REF in os.environ.get("SUPABASE_URL", "") and os.environ.get("ALLOW_PRODUCTION_WRITE") != "1":
        print("Refusing to write to the production database: only the scheduled GitHub Action does that.\n"
              "Point SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY in .env at the staging project.")
        return 4

    today = date.today().isoformat()
    raw, status = run_sources()
    current = build_jobs(raw)

    if not any(s["ok"] for s in status.values()):
        print(f"All sources failed – leaving {store.name} untouched.")
        return 1

    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    total = store.save(current, status, generated_at, today)
    print(f"\nKept {len(current)} of {len(raw)} postings today; {total} jobs now in {store.name}")

    problems = health_problems(status)
    if problems:
        for p in problems:
            print(f"::error title=Job source problem::{p}")  # shows up as an annotation in GitHub Actions
        print("The other sources were saved. Failing the run so GitHub sends an alert email.")
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
