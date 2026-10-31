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
from urllib.parse import urlsplit

import requests

from fetcher.availability import TOMBSTONE_DAYS

BATCH = 500


def _cutoff(today: str) -> str:
    return (date.fromisoformat(today) - timedelta(days=TOMBSTONE_DAYS)).isoformat()

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
    "hoursMin": "hours_min",
    "hoursMax": "hours_max",
    "payAmount": "pay_amount",
    "payUnit": "pay_unit",
}


def to_row(job: dict) -> dict:
    return {col: job.get(key) for key, col in COLUMNS.items()}


# ------------------------------------------------------------------ Supabase --
class SupabaseStore:
    name = "Supabase"

    def __init__(self, url: str, key: str, session: requests.Session | None = None):
        # Keep only scheme and host, so a URL pasted with "/rest/v1/" (or any path) still works.
        parts = urlsplit(url.strip())
        self.base = f"{parts.scheme}://{parts.netloc}/rest/v1"
        self.session = session or requests.Session()
        self.session.headers.update({"apikey": key, "Content-Type": "application/json"})
        # Legacy keys are JWTs and also go in Authorization; new "sb_secret_" keys don't.
        if key.startswith("eyJ"):
            self.session.headers["Authorization"] = f"Bearer {key}"

    def _check(self, res: requests.Response) -> requests.Response:
        if not res.ok:
            raise RuntimeError(f"Supabase {res.request.method} {res.url} -> {res.status_code}: {res.text[:300]}")
        return res

    def previous(self) -> dict[str, dict]:
        """Every stored job, keyed by id, with the same field names as jobs.json."""
        select = ",".join(key if key == col else f"{key}:{col}" for key, col in COLUMNS.items())
        jobs: dict[str, dict] = {}
        offset, page = 0, 1000  # Supabase caps each response (1000 rows by default)
        while True:
            res = self._check(self.session.get(
                f"{self.base}/jobs",
                params={"select": select, "order": "id", "limit": str(page), "offset": str(offset)},
                timeout=30,
            ))
            rows = res.json()
            jobs.update({r["id"]: r for r in rows})
            if len(rows) < page:
                return jobs
            offset += page

    def closed(self) -> dict[str, str] | None:
        """Tombstones of employer-closed jobs (id -> closed on), or None while the table is missing."""
        closed: dict[str, str] = {}
        offset, page = 0, 1000  # paged like previous(): Supabase caps each response
        while True:
            res = self.session.get(f"{self.base}/closed_jobs", timeout=30, params={
                "select": "id,closed_on", "order": "id", "limit": str(page), "offset": str(offset)})
            if res.status_code == 404:  # PGRST205: run supabase/schema.sql to create closed_jobs
                print("::warning title=closed_jobs missing::Run supabase/schema.sql; employer closures aren't remembered.")
                return None
            rows = self._check(res).json()
            closed.update({r["id"]: r["closed_on"] for r in rows})
            if len(rows) < page:
                return closed
            offset += page

    def save_closed(self, add: dict[str, str], drop: set[str], today: str) -> None:
        """Add new tombstones, drop reopened ones and those older than TOMBSTONE_DAYS."""
        if add:
            self._check(self.session.post(
                f"{self.base}/closed_jobs", params={"on_conflict": "id"},
                headers={"Prefer": "resolution=merge-duplicates,return=minimal"},
                data=json.dumps([{"id": k, "closed_on": v} for k, v in sorted(add.items())]).encode(), timeout=30,
            ))
        gone = sorted(drop - add.keys())
        for i in range(0, len(gone), 100):
            self._check(self.session.delete(
                f"{self.base}/closed_jobs", params={"id": f"in.({','.join(gone[i:i + 100])})"},
                headers={"Prefer": "return=minimal"}, timeout=30,
            ))
        self._check(self.session.delete(
            f"{self.base}/closed_jobs", params={"closed_on": f"lt.{_cutoff(today)}"},
            headers={"Prefer": "return=minimal"}, timeout=30,
        ))

    def save(self, jobs: list[dict], removed: set[str], status: dict, generated_at: str) -> int:
        rows = [to_row(j) for j in jobs]
        for i in range(0, len(rows), BATCH):
            self._check(self.session.post(
                f"{self.base}/jobs",
                params={"on_conflict": "id"},
                headers={"Prefer": "resolution=merge-duplicates,return=minimal"},
                data=json.dumps(rows[i:i + BATCH], ensure_ascii=False).encode(),
                timeout=60,
            ))
        # Closed jobs (see availability.py) are deleted by id.
        gone = sorted(removed)
        for i in range(0, len(gone), 100):
            self._check(self.session.delete(
                f"{self.base}/jobs", params={"id": f"in.({','.join(gone[i:i + 100])})"},
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

    def previous(self) -> dict[str, dict]:
        if not self.path.exists():
            return {}
        try:
            return {j["id"]: j for j in json.loads(self.path.read_text()).get("jobs", [])}
        except (json.JSONDecodeError, KeyError):
            print("! previous jobs.json unreadable, starting fresh")
            return {}

    def _read(self) -> dict:
        try:
            return json.loads(self.path.read_text()) if self.path.exists() else {}
        except json.JSONDecodeError:
            return {}

    def closed(self) -> dict[str, str] | None:
        return dict(self._read().get("closedJobs", {}))

    def save_closed(self, add: dict[str, str], drop: set[str], today: str) -> None:
        # Runs after save(), so it rewrites the file save() just wrote.
        payload = self._read()
        cut = _cutoff(today)
        kept = {k: v for k, v in payload.get("closedJobs", {}).items() if k not in drop and v >= cut}
        payload["closedJobs"] = {**kept, **add}
        self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=1))

    def save(self, jobs: list[dict], removed: set[str], status: dict, generated_at: str) -> int:
        closed = self._read().get("closedJobs", {})
        jobs = sorted((j for j in jobs if j["id"] not in removed),
                      key=lambda j: (j.get("postedAt") or j["firstSeen"], j["firstSeen"]), reverse=True)
        payload = {"generatedAt": generated_at, "sources": status, "count": len(jobs), "jobs": jobs,
                   "closedJobs": closed}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=1))
        return len(jobs)


def get_store(json_path: Path) -> SupabaseStore | JsonFileStore:
    url, key = os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if url and key:
        return SupabaseStore(url, key)
    return JsonFileStore(json_path)
