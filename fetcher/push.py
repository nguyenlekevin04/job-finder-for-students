"""Send job alerts by browser push after the daily fetch.

Each subscription (table push_subscriptions, filled by the website through the
subscribe_push function) names a board and optional types and fields. A subscriber gets
at most one notification a day, and only when jobs first seen today match. Subscriptions
the push service reports as gone (404/410) or not ours (403) are deleted.

Runs only when VAPID_PRIVATE_KEY is set (the production job of the Action). A failure here
never fails the fetch: the jobs are already saved.
"""
from __future__ import annotations

import json
import os
import time
from urllib.parse import urlencode

import requests

SITE = "https://dresden-jobs.vercel.app"
BOARD_NAMES = {"dresden": "Dresden", "leipzig": "Leipzig", "chemnitz": "Chemnitz", "berlin": "Berlin", "remote": "remote"}
TYPE_NAMES = {"werkstudent": "Werkstudent", "internship": "internship", "thesis": "thesis"}
# The push service says the subscription is gone (404/410), not ours (403) or malformed (400);
# -1 = it couldn't be sent at all (bad keys, unknown host). All of these are deleted.
GONE = {-1, 400, 403, 404, 410}
TIME_BUDGET = 15 * 60  # seconds; a slow push service must not hold up the Action
WELCOME = {"title": "Alerts are on", "body": "You'll get one notification a day when new jobs match.", "url": "/"}


def on_board(job: dict, board: str) -> bool:
    """Same rule as the website's inCity(): a city's own jobs, or only remote jobs on "remote"."""
    if board == "remote":
        return bool(job.get("remote"))
    return not job.get("remote") and (job.get("city") or "dresden") == board


def matches(job: dict, sub: dict) -> bool:
    return (
        on_board(job, sub["board"])
        and (not sub.get("types") or bool(set(job.get("types") or []) & set(sub["types"])))
        and (not sub.get("fields") or bool(set(job.get("fields") or []) & set(sub["fields"])))
    )


def board_url(sub: dict) -> str:
    path = "/" if sub["board"] == "dresden" else f"/{sub['board']}/"
    params = {k: ",".join(sub[k2]) for k, k2 in (("type", "types"), ("field", "fields")) if sub.get(k2)}
    params["new"] = "1"  # open on "Fresh this week", so the new jobs are on top
    return f"{SITE}{path}?{urlencode(params)}"


def message(new: list[dict], sub: dict) -> dict:
    n = len(new)
    where = "remote" if sub["board"] == "remote" else f"in {BOARD_NAMES[sub['board']]}"
    kind = " / ".join(TYPE_NAMES[t] for t in sub.get("types") or []) or "student"
    titles = "; ".join(j["title"] for j in new[:3]) + (" …" if n > 3 else "")
    return {
        "title": f"{n} new {kind} job{'s' if n != 1 else ''} {where}",
        "body": titles[:180],
        "url": board_url(sub),
    }


def due(subs: list[dict], new_jobs: list[dict], today: str) -> list[tuple[dict, dict]]:
    """(subscription, notification) for everyone with matching new jobs who wasn't notified today."""
    out = []
    for sub in subs:
        if sub.get("last_sent") == today:
            continue
        hits = [j for j in new_jobs if matches(j, sub)]
        if hits:
            out.append((sub, message(hits, sub)))
    return out


class PushStore:
    """push_subscriptions over PostgREST with the service key (bypasses RLS)."""

    def __init__(self, base: str, key: str, session: requests.Session | None = None):
        self.base = base.rstrip("/") + "/rest/v1/push_subscriptions"
        self.session = session or requests.Session()
        self.session.headers.update({"apikey": key, "Content-Type": "application/json"})
        if key.startswith("eyJ"):
            self.session.headers["Authorization"] = f"Bearer {key}"

    def all(self) -> list[dict]:
        rows, offset = [], 0
        while True:
            res = self.session.get(self.base, params={
                "select": "endpoint,p256dh,auth,board,types,fields,last_sent,confirmed", "order": "endpoint",
                "limit": "1000", "offset": str(offset)}, timeout=30)
            res.raise_for_status()
            page = res.json()
            rows += page
            if len(page) < 1000:
                return rows
            offset += 1000

    def sent(self, endpoint: str, today: str) -> None:
        self.session.patch(self.base, params={"endpoint": f"eq.{endpoint}"},
                           data=json.dumps({"last_sent": today}), timeout=30).raise_for_status()

    def confirm(self, endpoint: str) -> None:
        self.session.patch(self.base, params={"endpoint": f"eq.{endpoint}"},
                           data=json.dumps({"confirmed": True}), timeout=30).raise_for_status()

    def delete(self, endpoint: str) -> None:
        self.session.delete(self.base, params={"endpoint": f"eq.{endpoint}"}, timeout=30).raise_for_status()


def send_alerts(jobs: list[dict], today: str, base: str, key: str, store: PushStore | None = None,
                send=None) -> dict[str, int]:
    """Send today's alerts. `send(sub, payload)` returns the push service's HTTP status."""
    vapid = os.environ.get("VAPID_PRIVATE_KEY", "").strip()
    if not vapid:
        return {}
    store = store or PushStore(base, key)
    if send is None:
        from pywebpush import WebPushException, webpush

        def send(sub: dict, payload: dict) -> int:
            try:
                res = webpush(
                    {"endpoint": sub["endpoint"], "keys": {"p256dh": sub["p256dh"], "auth": sub["auth"]}},
                    json.dumps(payload), vapid_private_key=vapid, vapid_claims={"sub": SITE}, ttl=86400, timeout=15)
                return res.status_code
            except WebPushException as err:
                return err.response.status_code if err.response is not None else -1
            except Exception:  # bad keys, unknown host, …: one broken row must not stop everyone's alerts
                return -1

    def safe_send(sub: dict, payload: dict) -> int:
        try:
            return send(sub, payload)
        except Exception:
            return -1

    new_jobs = [j for j in jobs if j.get("firstSeen") == today]
    counts = {"sent": 0, "confirmed": 0, "removed": 0, "failed": 0}
    deadline = time.monotonic() + TIME_BUDGET
    subs = store.all()
    # New sign-ups first get "Alerts are on". Only a real browser receives it; anything else is
    # deleted, so fake sign-ups can't pile up (Kevin, 2026-11-03).
    for sub in [s for s in subs if not s.get("confirmed")]:
        if time.monotonic() > deadline:
            break
        status = safe_send(sub, WELCOME)
        if 200 <= status < 300:
            store.confirm(sub["endpoint"])
            counts["confirmed"] += 1
        else:
            store.delete(sub["endpoint"])
            counts["removed"] += 1
    for sub, payload in due([s for s in subs if s.get("confirmed")], new_jobs, today):
        if time.monotonic() > deadline:
            break
        status = safe_send(sub, payload)
        if 200 <= status < 300:
            store.sent(sub["endpoint"], today)
            counts["sent"] += 1
        elif status in GONE:
            store.delete(sub["endpoint"])
            counts["removed"] += 1
        else:
            counts["failed"] += 1
    return counts
