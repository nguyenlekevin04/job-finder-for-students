"""Decide which jobs are still open, so closed ones leave the board the same day.

Every link of a job gets a state, then the job gets a verdict:

- A source with a complete feed (every employer and institute source) lists all its
  open postings, so listed = open and not listed = closed, as long as the source
  worked today.
- A source with a partial feed (the aggregators: Arbeitsagentur, Arbeitnow, Adzuna)
  only returns its top results, so a missing posting may still be open. Those
  sources set ``FEED = "partial"`` and may define ``check(url) -> state``, which asks
  the posting itself. A listed posting is open unless its check says closed.
- A source that failed or was skipped today knows nothing: its links are unknown.

Verdict: any open link keeps the job (lastSeen = today). All links closed removes it.
Otherwise the job is unconfirmed and stays for ``UNCONFIRMED_DAYS`` after it was last
confirmed open. A guard stops a broken source or checker from emptying the board.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Callable

OPEN, CLOSED, UNKNOWN = "open", "closed", "unknown"
UNCONFIRMED_DAYS = 2  # keep a job this long after its last confirmation when no source can tell
GUARD_SHARE = 0.5  # never remove more than this share of one source's jobs in one run
GUARD_MIN_JOBS = 3  # below this many jobs a source is too small for the share rule

Checker = Callable[[str, str], str]  # (source name, url) -> state


@dataclass
class Result:
    jobs: list[dict]  # everything that stays, with firstSeen / lastSeen set
    removed: set[str]  # ids to delete
    stats: dict[str, dict[str, int]] = field(default_factory=dict)  # source -> state -> link count
    problems: list[str] = field(default_factory=list)  # for the health alarm


def decide(
    previous: dict[str, dict],
    current: dict[str, dict],
    source_ok: dict[str, bool],
    partial: set[str],
    check: Checker,
    today: str,
) -> Result:
    """previous: jobs stored before this run. current: jobs built from today's feeds."""
    grace = (date.fromisoformat(today) - timedelta(days=UNCONFIRMED_DAYS)).isoformat()
    stats: dict[str, dict[str, int]] = {}
    verdicts: dict[str, str] = {}
    candidates: dict[str, dict] = {}

    def link_state(link: dict, listed: bool) -> str:
        src = link["source"]
        if listed:
            state = check(src, link["url"]) if src in partial else OPEN
            state = CLOSED if state == CLOSED else OPEN
        elif not source_ok.get(src, False):
            state = UNKNOWN
        elif src in partial:
            state = check(src, link["url"])
        else:
            state = CLOSED
        stats.setdefault(src, {OPEN: 0, CLOSED: 0, UNKNOWN: 0})[state] += 1
        return state

    for jid in previous.keys() | current.keys():
        before = previous.get(jid)
        job = dict(current.get(jid) or before)
        listed_urls = {l["url"] for l in current[jid]["links"]} if jid in current else set()
        links = list(job["links"])
        if jid in current and before:
            # Keep older links that today's feeds didn't return, so they get checked too.
            links += [l for l in before.get("links", []) if l["url"] not in listed_urls]
        states = [link_state(l, l["url"] in listed_urls) for l in links]

        if OPEN in states:
            verdict = OPEN
            job["links"] = [l for l, s in zip(links, states) if s != CLOSED]
        elif all(s == CLOSED for s in states):
            verdict = CLOSED
        else:
            last = (before or {}).get("lastSeen") or today
            verdict = UNKNOWN if last >= grace else CLOSED

        job["firstSeen"] = (before or {}).get("firstSeen") or today
        job["lastSeen"] = today if verdict == OPEN else (before or {}).get("lastSeen") or today
        verdicts[jid] = verdict
        candidates[jid] = job

    # Guard: a source whose jobs would mostly disappear at once is more likely broken
    # than emptied. Keep its jobs and raise the alarm instead.
    removed = {jid for jid, v in verdicts.items() if v == CLOSED and jid in previous}
    problems: list[str] = []
    for src in sorted({l["source"] for j in previous.values() for l in j.get("links", [])}):
        had = [jid for jid, j in previous.items() if any(l["source"] == src for l in j.get("links", []))]
        gone = [jid for jid in had if jid in removed]
        if len(had) >= GUARD_MIN_JOBS and len(gone) > GUARD_SHARE * len(had):
            problems.append(f"{src}: would remove {len(gone)} of {len(had)} jobs at once; kept them (check the source)")
            for jid in gone:
                removed.discard(jid)
                candidates[jid] = {**previous[jid]}
                verdicts[jid] = UNKNOWN

    # Closed jobs that were never stored (listed today, but their check says closed) are simply dropped.
    jobs = [j for jid, j in candidates.items() if verdicts[jid] != CLOSED]
    return Result(jobs=jobs, removed=removed, stats=stats, problems=problems)
