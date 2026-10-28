"""Fetch every source, keep student tech jobs, merge with history, write jobs.json.

Run from the repo root:  python fetcher/main.py
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
import traceback
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from fetcher.classify import classify  # noqa: E402
from fetcher.sources import adzuna, arbeitnow, arbeitsagentur, fraunhofer, hzdr, tu_dresden  # noqa: E402

OUTPUT = ROOT / "web" / "public" / "jobs.json"
KEEP_MISSING_DAYS = 7  # keep a job this long after it stops appearing

SOURCES = [arbeitsagentur, arbeitnow, adzuna, tu_dresden, fraunhofer, hzdr]


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
            status[name] = {"ok": False, "count": 0, "error": str(err)[:200]}
            print(f"✗ {name}: FAILED – {err}")
            traceback.print_exc()
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
            j["fields"] = sorted(set(j["fields"]) | set(tags["fields"]), key=["ai", "data", "software", "hardware", "other"].index)
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


def merge_history(current: dict[str, dict], today: str) -> list[dict]:
    previous = {}
    if OUTPUT.exists():
        try:
            previous = {j["id"]: j for j in json.loads(OUTPUT.read_text()).get("jobs", [])}
        except (json.JSONDecodeError, KeyError):
            print("! previous jobs.json unreadable, starting fresh")

    cutoff = (date.fromisoformat(today) - timedelta(days=KEEP_MISSING_DAYS)).isoformat()
    merged = []
    for jid, job in current.items():
        prev = previous.get(jid)
        job["firstSeen"] = prev["firstSeen"] if prev else today
        job["lastSeen"] = today
        merged.append(job)
    for jid, prev in previous.items():
        if jid not in current and prev.get("lastSeen", today) >= cutoff:
            merged.append(prev)  # temporarily missing; keep for a while
    merged.sort(key=lambda j: (j.get("postedAt") or j["firstSeen"], j["firstSeen"]), reverse=True)
    return merged


def main() -> int:
    load_env()
    today = date.today().isoformat()
    raw, status = run_sources()
    current = build_jobs(raw)
    jobs = merge_history(current, today)

    ok_sources = [s for s in status.values() if s["ok"]]
    if not ok_sources:
        print("All sources failed – keeping the old jobs.json untouched.")
        return 1

    payload = {
        "generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sources": status,
        "count": len(jobs),
        "jobs": jobs,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=1))
    print(f"\nKept {len(current)} of {len(raw)} postings today; {len(jobs)} jobs written to {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
