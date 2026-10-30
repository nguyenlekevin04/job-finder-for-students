"""Decide which jobs are still open, so closed ones leave the board the same day.

Every link of a job gets a state, then the job gets a verdict:

- A source with a complete feed (every employer and institute source) lists all its
  open postings, so listed = open and not listed = closed, as long as the source
  worked today.
- A source with a partial feed (the aggregators: Arbeitsagentur, Arbeitnow)
  only returns its top results, so a missing posting may still be open. Those
  sources set ``FEED = "partial"`` and may define ``check(url) -> state``, which asks
  the posting itself. A listed posting is open unless its check says closed.
- A source that failed or was skipped today knows nothing: its links are unknown.
- A posting the source still lists but that didn't make it into today's jobs (its
  detail page timed out, or it was reclassified) is unknown too, not closed.

A link that now belongs to another of today's jobs (a renamed title, a cut-off copy merged
into its employer posting) is moved: it removes its old job like a closed link, but it isn't a
closure, so it neither counts toward the guard nor as closed in the stats.

Verdict: any open link keeps the job (lastSeen = today). All links closed or moved removes it.
Complete-feed links are ordered before aggregator links, and when a job's first link comes
from a complete feed and is closed, its aggregator links don't count: the employer decides.
Otherwise the job is unconfirmed and stays for ``UNCONFIRMED_DAYS`` after it was last
confirmed open. Closed links are dropped from every job that stays.

Employer closures are remembered: a job removed because its employer's (complete-feed) link
closed gets a tombstone. For ``TOMBSTONE_DAYS`` a job with that id that only aggregators list
is rejected, so a job-board copy can't bring it back as "New". When a complete feed lists the
id again, the employer reopened it: the job is back and the tombstone goes.

A guard stops a broken source or checker from emptying the board: when a source's own
closed links would remove at least ``GUARD_MIN_REMOVALS`` and more than ``GUARD_SHARE``
of its jobs in one run, those jobs are kept and the alarm is raised. Removals after the
grace period are never blocked. Sources in ``accept`` (owner-approved for this run,
``ACCEPT_REMOVALS`` in main.py) skip the guard. A source whose own closed links remove
all of its jobs (too few for the guard) is still removed, but raises the alarm too.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Callable

OPEN, CLOSED, UNKNOWN, MOVED = "open", "closed", "unknown", "moved"
GONE = (CLOSED, MOVED)  # link states that no longer keep a job open
UNCONFIRMED_DAYS = 2  # keep a job this long after its last confirmation when no source can tell
GUARD_SHARE = 0.5  # never remove more than this share of one source's jobs in one run
GUARD_MIN_JOBS = 3  # below this many jobs a source is too small for the share rule
GUARD_MIN_REMOVALS = 3  # removing fewer jobs than this at once never trips the guard
TOMBSTONE_DAYS = 30  # how long an employer closure blocks aggregator copies of the same job

Checker = Callable[[str, str], str]  # (source name, url) -> state


@dataclass
class Result:
    jobs: list[dict]  # everything that stays, with firstSeen / lastSeen set
    removed: set[str]  # ids to delete
    stats: dict[str, dict[str, int]] = field(default_factory=dict)  # source -> state -> link count
    problems: list[str] = field(default_factory=list)  # for the health alarm
    closed_add: dict[str, str] = field(default_factory=dict)  # new tombstones: id -> closed on
    closed_drop: set[str] = field(default_factory=set)  # tombstones of jobs the employer reopened
    rejected: set[str] = field(default_factory=set)  # aggregator-only copies of tombstoned jobs


def decide(
    previous: dict[str, dict],
    current: dict[str, dict],
    source_ok: dict[str, bool],
    partial: set[str],
    check: Checker,
    today: str,
    raw_urls: set[str],
    accept: set[str] = frozenset(),
    closed: dict[str, str] | None = None,
) -> Result:
    """previous: jobs stored before this run. current: jobs built from today's feeds.
    raw_urls: every posting URL the sources listed today, classified or not.
    accept: sources whose large removal the owner approved for this run (skip the guard).
    closed: tombstones, id -> the day its employer closed it (older ones are ignored)."""
    grace = (date.fromisoformat(today) - timedelta(days=UNCONFIRMED_DAYS)).isoformat()
    since = (date.fromisoformat(today) - timedelta(days=TOMBSTONE_DAYS)).isoformat()
    tombstoned = {jid for jid, day in (closed or {}).items() if day >= since}
    rejected = {jid for jid in tombstoned if jid in current and jid not in previous
                and all(l["source"] in partial for l in current[jid]["links"])}
    reopened = {jid for jid in tombstoned if jid in current
                and any(l["source"] not in partial for l in current[jid]["links"])}
    listed_today = current  # rejected copies still own their URLs, so an old job using one is moved
    current = {jid: j for jid, j in current.items() if jid not in rejected}
    verdicts: dict[str, str] = {}
    candidates: dict[str, dict] = {}
    link_states: dict[str, list[tuple[str, str]]] = {}  # job id -> (source, state) per link
    expired: set[str] = set()  # removed only because the grace period ran out
    by_employer: set[str] = set()  # closed because the employer's own link closed

    # Today's job for every listed URL. A stored job whose link now belongs to another job
    # (a cut-off copy merged into its employer posting, or a renamed title) is a stale duplicate.
    owner = {l["url"]: jid for jid, j in listed_today.items() for l in j["links"]}

    def link_state(link: dict, listed: bool, jid: str) -> str:
        src = link["source"]
        if listed:
            state = check(src, link["url"]) if src in partial else OPEN
            return CLOSED if state == CLOSED else OPEN
        if owner.get(link["url"], jid) != jid:
            return MOVED  # belongs to another job today
        if link["url"] in raw_urls:
            return UNKNOWN  # still listed, just not in today's jobs (e.g. detail page timed out)
        if not source_ok.get(src, False):
            return UNKNOWN
        if src in partial:
            return check(src, link["url"])
        return CLOSED

    for jid in previous.keys() | current.keys():
        before = previous.get(jid)
        job = dict(current.get(jid) or before)
        listed_urls = {l["url"] for l in current[jid]["links"]} if jid in current else set()
        links = list(job["links"])
        if jid in current and before:
            # Keep older links that today's feeds didn't return, so they get checked too.
            links += [l for l in before.get("links", []) if l["url"] not in listed_urls]
        # Complete-feed (employer) links stay ahead of aggregator links, so an aggregator copy
        # never becomes the "Apply now" link of an employer's job.
        links.sort(key=lambda l: l["source"] in partial)
        states = [link_state(l, l["url"] in listed_urls, jid) for l in links]
        link_states[jid] = [(l["source"], s) for l, s in zip(links, states)]

        # The employer is authoritative: when the job's first link comes from a complete feed and
        # that feed says closed, aggregator copies can't keep the job open.
        employer_closed = bool(links) and links[0]["source"] not in partial and states[0] in GONE
        if employer_closed and states[0] == CLOSED:
            by_employer.add(jid)
        judged = [s for l, s in zip(links, states) if not (employer_closed and l["source"] in partial)]
        if OPEN in judged:
            verdict = OPEN
        elif all(s in GONE for s in judged):
            verdict = CLOSED
        else:
            last = (before or {}).get("lastSeen") or today
            verdict = UNKNOWN if last >= grace else CLOSED
            if verdict == CLOSED:
                expired.add(jid)
        if verdict != CLOSED:
            job["links"] = [l for l, s in zip(links, states) if s not in GONE]

        job["firstSeen"] = (before or {}).get("firstSeen") or today
        job["lastSeen"] = today if verdict == OPEN else (before or {}).get("lastSeen") or today
        verdicts[jid] = verdict
        candidates[jid] = job

    # Guard: a source whose own links would remove most of its jobs at once is more
    # likely broken than emptied. Keep those jobs and raise the alarm instead.
    removed = {jid for jid, v in verdicts.items() if v == CLOSED and jid in previous}
    restored: set[str] = set()
    problems: list[str] = []
    accepted = {a.lower() for a in accept}
    for src in sorted({l["source"] for j in previous.values() for l in j.get("links", [])}):
        if src.lower() in accepted:
            continue
        had = [jid for jid, j in previous.items() if any(l["source"] == src for l in j.get("links", []))]
        gone = [jid for jid in had if jid in removed and jid not in expired
                and (src, CLOSED) in link_states[jid]]
        if len(had) >= GUARD_MIN_JOBS and len(gone) >= GUARD_MIN_REMOVALS and len(gone) > GUARD_SHARE * len(had):
            problems.append(f"{src}: would remove {len(gone)} of {len(had)} jobs at once; kept them. "
                            f"If they really closed, run 'Update jobs' with accept_removals={src}.")
            for jid in gone:
                removed.discard(jid)
                restored.add(jid)
                candidates[jid] = {**previous[jid]}
                verdicts[jid] = UNKNOWN

    # A source whose own closed links removed every one of its jobs (too few for the guard)
    # is let through, but is worth a look: it may be broken rather than empty.
    for src in sorted({l["source"] for j in previous.values() for l in j.get("links", [])}):
        if src.lower() in accepted:
            continue
        had = [jid for jid, j in previous.items() if any(l["source"] == src for l in j.get("links", []))]
        still_listed = any(verdicts[jid] != CLOSED and any(l["source"] == src for l in j["links"])
                           for jid, j in candidates.items())
        if not still_listed and all(jid in removed and jid not in expired and (src, CLOSED) in link_states[jid]
                                    for jid in had):
            problems.append(f"{src}: all {len(had)} of its jobs closed in one run; "
                            "check the source if that's unexpected.")

    # Per-source link counts of the final outcome: restored jobs' closed links count as unknown.
    stats: dict[str, dict[str, int]] = {}
    for jid, pairs in link_states.items():
        for src, state in pairs:
            if jid in restored and state == CLOSED:
                state = UNKNOWN
            stats.setdefault(src, {OPEN: 0, CLOSED: 0, UNKNOWN: 0, MOVED: 0})[state] += 1

    # Closed jobs that were never stored (listed today, but their check says closed) are simply dropped.
    jobs = [j for jid, j in candidates.items() if verdicts[jid] != CLOSED]
    closed_add = {jid: today for jid in removed & by_employer}
    return Result(jobs=jobs, removed=removed, stats=stats, problems=problems,
                  closed_add=closed_add, closed_drop=reopened, rejected=rejected)
