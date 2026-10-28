"""Where jobs are saved: Supabase (production) or web/public/jobs.json (local fallback).

Supabase is used when SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are set.
It talks to Supabase's REST API (PostgREST) with plain requests, so no extra
dependency is needed. Table layout: supabase/schema.sql.
"""
from __future__ import annotations

import json
import os
from datetime import date, timedelta
from pathlib import Path

import requests

KEEP_MISSING_DAYS = 7  # keep a job this long after it stops appearing
BATCH = 500

# jobs.json / web field name -> database column
COLUMNS = {
    "id": "id",
    "title": "title",
    "company": "company",
    "location": "location",
    "remote": "remote",
    "type": "type",
    "types": "types",
    "fields": "fields",
    "englishFriendly": "english_friendly",
    "postedAt": "posted_at",
    "deadline": "deadline",
    "firstSeen": "first_seen",
    "lastSeen": "last_seen",
    "links": "links",
    "snippet": "snippet",
}


def cutoff_day(today: str) -> str:
    return (date.fromisoformat(today) - timedelta(days=KEEP_MISSING_DAYS)).isoformat()


def stamp_history(current: dict[str, dict], first_seen: dict[str, str], today: str) -> list[dict]:
    """Give each current job its firstSeen (kept from before) and lastSeen = today."""
    for jid, job in current.items():
        job["firstSeen"] = first_seen.get(jid, today)
        job["lastSeen"] = today
    return list(current.values())


def to_row(job: dict) -> dict:
    return {col: job.get(key) for key, col in COLUMNS.items()}


# ------------------------------------------------------------------ Supabase --
class SupabaseStore:
    name = "Supabase"

    def __init__(self, url: str, key: str, session: requests.Session | None = None):
        self.base = url.rstrip("/") + "/rest/v1"
        self.session = session or requests.Session()
        self.session.headers.update({"apikey": key, "Content-Type": "application/json"})
        # Legacy keys are JWTs and also go in Authorization; new "sb_secret_" keys don't.
        if key.startswith("eyJ"):
            self.session.headers["Authorization"] = f"Bearer {key}"

    def _check(self, res: requests.Response) -> requests.Response:
        if not res.ok:
            raise RuntimeError(f"Supabase {res.request.method} {res.url} -> {res.status_code}: {res.text[:300]}")
        return res

    def first_seen(self) -> dict[str, str]:
        # Supabase caps each response (1000 rows by default), so page through.
        seen: dict[str, str] = {}
        offset, page = 0, 1000
        while True:
            res = self._check(self.session.get(
                f"{self.base}/jobs",
                params={"select": "id,first_seen", "order": "id", "limit": str(page), "offset": str(offset)},
                timeout=30,
            ))
            rows = res.json()
            seen.update({r["id"]: r["first_seen"] for r in rows})
            if len(rows) < page:
                return seen
            offset += page

    def save(self, current: dict[str, dict], status: dict, generated_at: str, today: str) -> int:
        jobs = stamp_history(current, self.first_seen(), today)
        rows = [to_row(j) for j in jobs]
        for i in range(0, len(rows), BATCH):
            self._check(self.session.post(
                f"{self.base}/jobs",
                params={"on_conflict": "id"},
                headers={"Prefer": "resolution=merge-duplicates,return=minimal"},
                data=json.dumps(rows[i:i + BATCH], ensure_ascii=False).encode(),
                timeout=60,
            ))
        # Jobs missing for too long are removed; recently missing ones stay.
        self._check(self.session.delete(
            f"{self.base}/jobs", params={"last_seen": f"lt.{cutoff_day(today)}"},
            headers={"Prefer": "return=minimal"}, timeout=30,
        ))
        total = int(self._check(self.session.get(
            f"{self.base}/jobs", params={"select": "id"},
            headers={"Prefer": "count=exact", "Range": "0-0"}, timeout=30,
        )).headers.get("Content-Range", "*/0").split("/")[-1])
        self._check(self.session.post(
            f"{self.base}/fetch_runs",
            headers={"Prefer": "return=minimal"},
            data=json.dumps({"generated_at": generated_at, "job_count": total, "sources": status}).encode(),
            timeout=30,
        ))
        return total


# ----------------------------------------------------------------- JSON file --
class JsonFileStore:
    name = "jobs.json"

    def __init__(self, path: Path):
        self.path = path

    def _previous(self) -> dict[str, dict]:
        if not self.path.exists():
            return {}
        try:
            return {j["id"]: j for j in json.loads(self.path.read_text()).get("jobs", [])}
        except (json.JSONDecodeError, KeyError):
            print("! previous jobs.json unreadable, starting fresh")
            return {}

    def merge(self, current: dict[str, dict], today: str) -> list[dict]:
        previous = self._previous()
        jobs = stamp_history(current, {jid: p["firstSeen"] for jid, p in previous.items()}, today)
        cutoff = cutoff_day(today)
        jobs += [p for jid, p in previous.items() if jid not in current and p.get("lastSeen", today) >= cutoff]
        jobs.sort(key=lambda j: (j.get("postedAt") or j["firstSeen"], j["firstSeen"]), reverse=True)
        return jobs

    def save(self, current: dict[str, dict], status: dict, generated_at: str, today: str) -> int:
        jobs = self.merge(current, today)
        payload = {"generatedAt": generated_at, "sources": status, "count": len(jobs), "jobs": jobs}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=1))
        return len(jobs)


def get_store(json_path: Path) -> SupabaseStore | JsonFileStore:
    url, key = os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if url and key:
        return SupabaseStore(url, key)
    return JsonFileStore(json_path)
