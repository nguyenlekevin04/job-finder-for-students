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
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from fetcher.classify import FIELD_LABELS, classify  # noqa: E402
from fetcher.sources import (  # noqa: E402
    amazon, arbeitnow, arbeitsagentur, bosch, fraunhofer, globalfoundries, hzdr, infineon, tu_dresden,
)
from fetcher.availability import UNKNOWN, decide  # noqa: E402
from fetcher.store import JsonFileStore, get_store  # noqa: E402
from fetcher.terms import extract_terms  # noqa: E402

OUTPUT = ROOT / "web" / "public" / "jobs.json"  # local fallback when Supabase isn't configured

# The live site's Supabase project (public: it's also in the site's code). Only the
# scheduled GitHub Action may write to it; it sets ALLOW_PRODUCTION_WRITE=1. Local
# runs and staging use the staging project, so a buggy test run can't reach students.
PRODUCTION_PROJECT_REF = "ywurtulsjybbdfzqfowq"

# Direct employer sources come first: the first link of a merged job is its "Apply now"
# button, and the employer's own page beats a job-board copy.
SOURCES = [
    tu_dresden, fraunhofer, hzdr, infineon, globalfoundries, bosch, amazon,
    arbeitsagentur, arbeitnow,
]

# Hosts each source's posting links may point to (the host or a subdomain of it), taken
# from the URL each module builds. Links become "Apply now" buttons, so a link outside its
# source's host (or a source missing here) is rejected and its posting skipped.
LINK_HOSTS = {
    "TU Dresden": ("tu-dresden.de",),
    "Fraunhofer": ("jobs.fraunhofer.de",),
    "HZDR": ("hzdr.de",),
    "Infineon": ("jobs.infineon.com",),
    # Workday and SmartRecruiters domains are shared by all their customers: allow only these.
    "GlobalFoundries": ("globalfoundries.wd1.myworkdayjobs.com",),
    "Bosch": ("jobs.smartrecruiters.com",),
    "Amazon": ("amazon.jobs",),
    "Arbeitsagentur": ("arbeitsagentur.de",),
    # Arbeitnow links to its country sites too (seen live: .fr, .ch, .nl, .co.uk).
    "Arbeitnow": ("arbeitnow.com", "arbeitnow.de", "arbeitnow.fr", "arbeitnow.ch", "arbeitnow.nl", "arbeitnow.co.uk"),
}


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


def is_globalfoundries(company: str) -> bool:
    c = norm_company(company)
    return c == "globalfoundries" or c.startswith("globalfoundries ")


TWIN_MIN_TITLE = 40  # shorter titles are too generic to match by prefix
TWIN_SOURCE = "Arbeitsagentur"  # the only source that cuts titles off; others could pad a title to match


def truncated_twin(jobs: dict[str, dict], title: str, company: str, source: str) -> str | None:
    """Id of the one GlobalFoundries job this posting duplicates, else None.

    The Arbeitsagentur lists GlobalFoundries postings as "GlobalFoundries Management Services
    GmbH & Co. KG" with titles cut off ("... Machine Learning & Virt"), so job_id() differs from
    the employer's own posting. A match needs the same company, one normalized title equal to
    or a prefix of the other, the shorter one at least TWIN_MIN_TITLE characters, and exactly
    one such job. Only postings from TWIN_SOURCE match, and only into jobs that started from
    another source, so two real roles with prefix titles stay two jobs. Job ids stay as they are.
    """
    if source != TWIN_SOURCE or not is_globalfoundries(company):
        return None
    t = norm_title(title)
    matches = []
    for jid, j in jobs.items():
        # Skip jobs that started from this same source: two Arbeitsagentur postings are two jobs.
        # A GlobalFoundries-feed job may already carry an Arbeitsagentur link (the full title is
        # listed there too), and its cut-off copy must still merge into it.
        if not is_globalfoundries(j["company"]) or j["links"][0]["source"] == source:
            continue
        other = norm_title(j["title"])
        # The Arbeitsagentur only cuts titles off, never adds words: its title must be the prefix.
        if len(t) >= TWIN_MIN_TITLE and other.startswith(t):
            matches.append(jid)
    return matches[0] if len(matches) == 1 else None


def redact(text: str) -> str:
    """Drop URL query strings: they can hold API keys. Errors are saved to the
    public fetch_runs table and printed in CI logs."""
    return re.sub(r"\?[^\s'\"]*=[^\s'\"]*", "?…", text)


def safe_error(err: Exception) -> str:
    return redact(str(err))[:200]


def safe_link(source: str, url: str) -> bool:
    """True if url is https:// on a host allowed for this source (see LINK_HOSTS)."""
    allowed = LINK_HOSTS.get(source)
    if not allowed or not isinstance(url, str):
        return False
    # Browsers read a backslash as "/" and ignore tabs/newlines, so such URLs can open another host
    # than urlsplit sees. Postings never need them; neither do they need user:pass@.
    if "\\" in url or any(ord(c) <= 32 for c in url):
        return False
    try:
        parts = urlsplit(url)
        host = parts.hostname or ""
    except ValueError:
        return False
    if parts.scheme != "https" or "@" in parts.netloc:
        return False
    return any(host == h or host.endswith("." + h) for h in allowed)


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
        if s.get("rejected"):
            problems.append(f"{name}: {s['rejected']} postings had a link outside its allowed hosts "
                            "(LINK_HOSTS); check if the source moved")
    return problems


def run_sources() -> tuple[list, dict]:
    raw, status = [], {}
    for src in SOURCES:
        name = src.NAME
        if hasattr(src, "is_enabled") and not src.is_enabled():
            status[name] = {"ok": False, "count": 0, "skipped": True, "error": "Disabled"}
            print(f"- {name}: skipped (disabled)")
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


def build_jobs(raw: list, status: dict | None = None) -> dict[str, dict]:
    """Classify and merge duplicates. Returns id -> job dict.

    Postings with a link outside their source's LINK_HOSTS are skipped and counted in
    status[source]["rejected"] (when status is given), so the health alarm reports them."""
    jobs: dict[str, dict] = {}
    rejected: Counter[str] = Counter()
    today = date.today().isoformat()
    for r in raw:
        if not safe_link(r.source, r.url):
            rejected[r.source] += 1
            continue
        r.title = re.sub(r"\s+", " ", strip_company_prefix(r.title, r.company)).strip()
        tags = classify(r)
        if not tags:
            continue
        jid = job_id(r.title, r.company)
        if jid not in jobs:
            jid = truncated_twin(jobs, r.title, r.company, r.source) or jid
        link = {"source": r.source, "url": r.url}
        posted_at = r.posted_at if r.posted_at and r.posted_at <= today else None  # a future date would sort first
        terms = extract_terms(r.title, r.tags, r.description)  # full description, before the snippet cut
        if jid in jobs:
            # raw arrives in SOURCES order, so the first posting is the most trusted one: a later
            # copy (e.g. an aggregator's) only fills an empty date or snippet and can't replace its text.
            j = jobs[jid]
            if all(l["url"] != r.url for l in j["links"]):
                j["links"].append(link)
            if not j["postedAt"]:
                j["postedAt"] = posted_at
            if not j["snippet"] and tags["snippet"]:
                # Flag and snippet come from the same posting.
                j["snippet"], j["englishFriendly"] = tags["snippet"], tags["englishFriendly"]
            # Hours and pay come only from the first posting: a later copy could invent them.
            j["fields"] = sorted(set(j["fields"]) | set(tags["fields"]), key=list(FIELD_LABELS).index)
            continue
        jobs[jid] = {
            "id": jid,
            "title": re.sub(r"\s+", " ", r.title).strip(),
            "company": r.company.strip(),
            "location": r.location,
            "remote": r.remote,
            **{k: tags[k] for k in ("type", "types", "fields", "englishFriendly")},
            "postedAt": posted_at,
            "deadline": r.deadline,
            "links": [link],
            "snippet": tags["snippet"],
            **terms,
        }
    for source, n in rejected.items():
        print(f"  ! {source}: skipped {n} postings with a link outside its allowed hosts")
        if status is not None and source in status:
            status[source]["rejected"] = n
    return jobs


def drop_unsafe_links(previous: dict[str, dict]) -> dict[str, dict]:
    """Stored jobs without links that fail safe_link (e.g. saved before LINK_HOSTS existed).
    A job left with no links gets an empty list, so decide() removes it."""
    return {jid: {**j, "links": [l for l in j.get("links", []) if safe_link(l.get("source"), l.get("url"))]}
            for jid, j in previous.items()}


def make_checker(sources=SOURCES):
    """(source name, url) -> open/closed/unknown, using each partial-feed source's check()."""
    checks = {s.NAME: s.check for s in sources if hasattr(s, "check")}

    def check(source: str, url: str) -> str:
        fn = checks.get(source)
        if not fn:
            return UNKNOWN
        try:
            state = fn(url)
        except Exception as err:  # a broken check must never remove a job
            print(f"  ! {source} check failed for {redact(url)}: {safe_error(err)}")
            return UNKNOWN
        time.sleep(0.2)  # be gentle: one request per posting
        return state

    return check


def accepted_removals() -> set[str]:
    """Sources whose large removal the owner approved for this run (ACCEPT_REMOVALS="HZDR,Bosch")."""
    return {n.strip() for n in os.environ.get("ACCEPT_REMOVALS", "").split(",") if n.strip()}


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    load_env()
    store = get_store(OUTPUT)
    if "--require-db" in argv and isinstance(store, JsonFileStore):
        print("SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY are not set – refusing to fall back to jobs.json.")
        return 2
    if PRODUCTION_PROJECT_REF in os.environ.get("SUPABASE_URL", "").lower() and os.environ.get("ALLOW_PRODUCTION_WRITE") != "1":
        print("Refusing to write to the production database: only the scheduled GitHub Action does that.\n"
              "Point SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY in .env at the staging project.")
        return 4

    today = date.today().isoformat()
    raw, status = run_sources()
    current = build_jobs(raw, status)

    if not any(s["ok"] for s in status.values()):
        print(f"All sources failed – leaving {store.name} untouched.")
        return 1

    result = decide(
        previous=drop_unsafe_links(store.previous()),
        current=current,
        source_ok={name: s["ok"] for name, s in status.items()},
        partial={s.NAME for s in SOURCES if getattr(s, "FEED", "complete") == "partial"},
        check=make_checker(),
        today=today,
        # Postings listed today that didn't become a job (e.g. not classified). A URL that moved
        # to another job (title edited, new id) isn't here, so its old job closes at once.
        raw_urls={r.url for r in raw if safe_link(r.source, r.url)} - {l["url"] for j in current.values() for l in j["links"]},
        accept=accepted_removals(),
    )
    for name, counts in result.stats.items():
        if name in status:
            status[name]["links"] = counts  # open / closed / unknown, stored in fetch_runs
        print(f"  {name}: {counts['open']} open, {counts['closed']} closed, {counts['unknown']} unconfirmed")

    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    total = store.save(result.jobs, result.removed, status, generated_at)
    print(f"\nKept {len(current)} of {len(raw)} postings today; removed {len(result.removed)} closed; "
          f"{total} jobs now in {store.name}")

    problems = health_problems(status) + result.problems
    if problems:
        for p in problems:
            print(f"::error title=Job source problem::{p}")  # shows up as an annotation in GitHub Actions
        print("The other sources were saved. Failing the run so GitHub sends an alert email.")
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
