"""Which jobs stay on the board (fetcher/availability.py). No network."""
from fetcher.availability import CLOSED, MOVED, OPEN, UNKNOWN, decide
from fetcher.sources import arbeitnow, arbeitsagentur

TODAY = "2026-10-30"


def job(jid, *sources, last="2026-10-29", first="2026-10-01"):
    return {"id": jid, "title": jid, "firstSeen": first, "lastSeen": last,
            "links": [{"source": s, "url": f"https://{s}/{jid}"} for s in sources]}


def now(jid, *sources):
    """A job as today's feeds return it (no history fields yet)."""
    j = job(jid, *sources)
    del j["firstSeen"], j["lastSeen"]
    return j


def run(previous, current, ok=None, partial=(), checks=None, raw_urls=(), accept=(), today=TODAY):
    ok = ok or {s: True for j in [*previous, *current] for l in j["links"] for s in [l["source"]]}
    checks = checks or {}
    return decide(
        previous={j["id"]: j for j in previous},
        current={j["id"]: j for j in current},
        source_ok=ok,
        partial=set(partial),
        check=lambda src, url: checks.get(url, UNKNOWN),
        today=today,
        raw_urls={*raw_urls, *(l["url"] for j in current for l in j["links"])},
        accept=set(accept),
    )


def ids(result):
    return {j["id"] for j in result.jobs}


def test_complete_feed_listed_stays_and_missing_is_removed():
    r = run([job("a", "Bosch"), job("b", "Bosch"), job("c", "Bosch")], [now("a", "Bosch"), now("b", "Bosch")])
    assert ids(r) == {"a", "b"} and r.removed == {"c"}
    a = next(j for j in r.jobs if j["id"] == "a")
    assert a["firstSeen"] == "2026-10-01" and a["lastSeen"] == TODAY


def test_new_job_gets_today_as_first_seen():
    r = run([], [now("n", "Bosch")])
    assert r.jobs[0]["firstSeen"] == TODAY == r.jobs[0]["lastSeen"]


def test_failed_source_removes_nothing():
    r = run([job("a", "Bosch"), job("b", "HZDR")], [now("b", "HZDR")], ok={"Bosch": False, "HZDR": True})
    assert ids(r) == {"a", "b"} and not r.removed
    assert next(j for j in r.jobs if j["id"] == "a")["lastSeen"] == "2026-10-29"  # not confirmed today


def test_failed_source_job_goes_after_the_grace_period():
    r = run([job("a", "Bosch", last="2026-10-27")], [], ok={"Bosch": False})
    assert r.removed == {"a"}


def test_partial_feed_missing_job_uses_its_check():
    prev = [job("open", "Arbeitnow"), job("closed", "Arbeitnow"), job("unsure", "Arbeitnow"),
            job("stale", "Arbeitnow", last="2026-10-27"), job("x", "Bosch"), job("y", "Bosch"), job("z", "Bosch")]
    checks = {"https://Arbeitnow/open": OPEN, "https://Arbeitnow/closed": CLOSED}
    r = run(prev, [now("x", "Bosch"), now("y", "Bosch"), now("z", "Bosch")], partial={"Arbeitnow"}, checks=checks)
    assert r.removed == {"closed", "stale"}
    kept = {j["id"]: j for j in r.jobs}
    assert kept["open"]["lastSeen"] == TODAY
    assert kept["unsure"]["lastSeen"] == "2026-10-29"
    assert r.stats["Arbeitnow"] == {OPEN: 1, CLOSED: 1, UNKNOWN: 2, MOVED: 0}


def test_listed_partial_job_is_removed_when_its_check_says_closed():
    prev = [job("a", "Arbeitsagentur"), job("b", "Arbeitsagentur"), job("c", "Arbeitsagentur")]
    current = [now("a", "Arbeitsagentur"), now("b", "Arbeitsagentur"), now("c", "Arbeitsagentur"),
               now("new-but-closed", "Arbeitsagentur")]
    checks = {"https://Arbeitsagentur/a": CLOSED, "https://Arbeitsagentur/new-but-closed": CLOSED}
    r = run(prev, current, partial={"Arbeitsagentur"}, checks=checks)
    assert r.removed == {"a"}
    assert ids(r) == {"b", "c"}  # a closed new job is never stored


def test_one_open_link_keeps_the_job_and_closed_links_are_dropped():
    prev = [job("a", "Arbeitsagentur", "Arbeitnow")]
    checks = {"https://Arbeitsagentur/a": CLOSED, "https://Arbeitnow/a": OPEN}
    r = run(prev, [], partial={"Arbeitsagentur", "Arbeitnow"}, checks=checks)
    assert ids(r) == {"a"}
    assert [l["source"] for l in r.jobs[0]["links"]] == ["Arbeitnow"]


def test_closed_employer_link_removes_the_job_despite_open_aggregator_copy():
    """Kevin's proof: the GlobalFoundries posting is gone from a working feed, the Arbeitnow copy is open."""
    prev = [job("a", "GlobalFoundries", "Arbeitnow"), job("b", "GlobalFoundries"), job("c", "GlobalFoundries")]
    r = run(prev, [now("a", "Arbeitnow"), now("b", "GlobalFoundries"), now("c", "GlobalFoundries")],
            partial={"Arbeitnow"}, checks={"https://Arbeitnow/a": OPEN})
    assert r.removed == {"a"} and ids(r) == {"b", "c"}


def test_employer_link_stays_first_when_its_source_failed():
    prev = [job("a", "GlobalFoundries", "Arbeitnow")]
    r = run(prev, [now("a", "Arbeitnow")], ok={"GlobalFoundries": False, "Arbeitnow": True},
            partial={"Arbeitnow"}, checks={"https://Arbeitnow/a": OPEN})
    assert ids(r) == {"a"}
    assert [l["source"] for l in r.jobs[0]["links"]] == ["GlobalFoundries", "Arbeitnow"]


def test_older_links_of_a_listed_job_are_checked_and_kept_if_open():
    prev = [job("a", "Bosch", "Arbeitnow")]
    r = run(prev, [now("a", "Bosch")], partial={"Arbeitnow"}, checks={"https://Arbeitnow/a": OPEN})
    assert [l["source"] for l in r.jobs[0]["links"]] == ["Bosch", "Arbeitnow"]


def test_guard_keeps_a_source_that_would_mostly_vanish():
    prev = [job(f"j{i}", "Infineon") for i in range(4)] + [job("k", "Bosch")]
    r = run(prev, [now("j0", "Infineon"), now("k", "Bosch")])
    assert not r.removed and ids(r) == {"j0", "j1", "j2", "j3", "k"}
    assert r.problems and "Infineon" in r.problems[0]
    assert next(j for j in r.jobs if j["id"] == "j1")["lastSeen"] == "2026-10-29"


def test_guard_allows_half_and_ignores_tiny_sources():
    half = [job(f"j{i}", "Infineon") for i in range(4)]
    r = run(half, [now("j0", "Infineon"), now("j1", "Infineon")])
    assert r.removed == {"j2", "j3"} and not r.problems
    tiny = [job("h1", "HZDR"), job("h2", "HZDR")]
    r = run(tiny, [], ok={"HZDR": True})
    assert r.removed == {"h1", "h2"}
    assert r.problems == ["HZDR: all 2 of its jobs closed in one run; check the source if that's unexpected."]


def test_source_emptied_in_one_run_is_removed_but_raises_the_alarm():
    prev = [job("h1", "HZDR"), job("h2", "HZDR"), job("a1", "Amazon"), job("b1", "Bosch"), job("b2", "Bosch")]
    r = run(prev, [now("b1", "Bosch")], ok={"HZDR": True, "Amazon": True, "Bosch": True})
    assert r.removed == {"h1", "h2", "a1", "b2"}
    assert r.problems == [
        "Amazon: all 1 of its jobs closed in one run; check the source if that's unexpected.",
        "HZDR: all 2 of its jobs closed in one run; check the source if that's unexpected.",
    ]
    r = run(prev, [now("b1", "Bosch")], ok={"HZDR": True, "Amazon": True, "Bosch": True}, accept={"HZDR"})
    assert r.problems == ["Amazon: all 1 of its jobs closed in one run; check the source if that's unexpected."]


def test_emptied_alarm_skips_guarded_and_expired_sources():
    r = run([job(f"j{i}", "Infineon") for i in range(4)], [])
    assert len(r.problems) == 1 and "would remove" in r.problems[0]
    r = run([job("j0", "Bosch", last="2026-10-27")], [], ok={"Bosch": False})
    assert r.removed == {"j0"} and not r.problems


def test_multi_link_job_keeps_the_unknown_link_and_drops_the_closed_one():
    prev = [job("a", "Bosch", "Arbeitsagentur")]
    closed = {"https://Arbeitsagentur/a": CLOSED}
    ok = {"Bosch": False, "Arbeitsagentur": True}
    r = run(prev, [now("a", "Arbeitsagentur")], ok=ok, partial={"Arbeitsagentur"}, checks=closed)
    assert ids(r) == {"a"} and not r.removed
    assert [l["source"] for l in r.jobs[0]["links"]] == ["Bosch"]
    assert r.jobs[0]["lastSeen"] == "2026-10-29"
    # Next day: Bosch still failing, Arbeitsagentur still lists it as closed, still within grace.
    r = run(r.jobs, [now("a", "Arbeitsagentur")], ok=ok, partial={"Arbeitsagentur"}, checks=closed,
            today="2026-10-31")
    assert ids(r) == {"a"} and not r.removed
    assert [l["source"] for l in r.jobs[0]["links"]] == ["Bosch"]


def test_guard_lets_a_few_real_closures_through():
    prev = [job(f"j{i}", "HZDR") for i in range(3)]
    r = run(prev, [now("j0", "HZDR")])
    assert r.removed == {"j1", "j2"} and not r.problems


def test_guard_blocks_until_the_owner_accepts():
    prev = [job(f"j{i}", "Infineon") for i in range(6)]
    current = [now("j0", "Infineon"), now("j1", "Infineon")]
    r = run(prev, current)
    assert not r.removed and len(r.jobs) == 6
    assert r.problems == ["Infineon: would remove 4 of 6 jobs at once; kept them. "
                          "If they really closed, run 'Update jobs' with accept_removals=Infineon."]
    r = run(prev, current, accept={"Infineon"})
    assert r.removed == {"j2", "j3", "j4", "j5"} and not r.problems


def test_guard_never_blocks_grace_period_removals():
    prev = [job(f"j{i}", "Bosch", last="2026-10-27") for i in range(4)]
    r = run(prev, [], ok={"Bosch": False})
    assert r.removed == {"j0", "j1", "j2", "j3"} and not r.problems


def test_listed_but_unclassified_posting_is_unknown_not_closed():
    prev = [job("a", "HZDR"), job("b", "HZDR"), job("c", "HZDR")]
    current = [now("b", "HZDR"), now("c", "HZDR")]
    r = run(prev, current, raw_urls={"https://HZDR/a"})
    assert ids(r) == {"a", "b", "c"} and not r.removed
    assert next(j for j in r.jobs if j["id"] == "a")["lastSeen"] == "2026-10-29"
    assert r.stats["HZDR"] == {OPEN: 2, CLOSED: 0, UNKNOWN: 1, MOVED: 0}
    later = run(r.jobs, current, raw_urls={"https://HZDR/a"}, today="2026-11-01")
    assert later.removed == {"a"}


def test_stats_count_links_of_jobs_kept_by_the_guard_as_unknown():
    prev = [job(f"j{i}", "Infineon") for i in range(4)]
    r = run(prev, [now("j0", "Infineon")])
    assert r.problems
    assert r.stats["Infineon"] == {OPEN: 1, CLOSED: 0, UNKNOWN: 3, MOVED: 0}


def test_aggregator_status_codes():
    for mod in (arbeitsagentur, arbeitnow):
        assert mod.state_from_status(200) == OPEN
        assert mod.state_from_status(404) == CLOSED
        assert mod.state_from_status(410) == CLOSED
        for code in (None, 301, 403, 429, 500, 503):
            assert mod.state_from_status(code) == UNKNOWN


def test_arbeitsagentur_check_asks_the_detail_api(monkeypatch):
    seen = {}
    monkeypatch.setattr(arbeitsagentur, "status_code", lambda url, headers=None: seen.setdefault("url", url) and 404)
    assert arbeitsagentur.check("https://www.arbeitsagentur.de/jobsuche/jobdetail/10001-1001916728-S") == CLOSED
    assert seen["url"].endswith("/pc/v4/jobdetails/MTAwMDEtMTAwMTkxNjcyOC1T")


def test_renamed_job_closes_its_old_id_at_once():
    # The employer edited the title: same URL, new id. main.py leaves such URLs out of raw_urls.
    old = job("old-id", "Bosch")
    renamed = {**now("new-id", "Bosch"), "links": old["links"]}
    r = decide(previous={"old-id": old}, current={"new-id": renamed}, source_ok={"Bosch": True}, partial=set(),
               check=lambda s, u: UNKNOWN, today=TODAY, raw_urls=set())
    assert r.removed == {"old-id"} and ids(r) == {"new-id"}


def test_accept_ignores_case():
    prev = [job(f"j{i}", "Infineon") for i in range(6)]
    r = decide(previous={j["id"]: j for j in prev}, current={}, source_ok={"Infineon": True}, partial=set(),
               check=lambda s, u: UNKNOWN, today=TODAY, raw_urls=set(), accept={"infineon"})
    assert len(r.removed) == 6 and not r.problems


def test_renaming_the_only_job_of_a_source_raises_no_alarm():
    old = job("old-id", "Bosch")
    renamed = {**now("new-id", "Bosch"), "links": [{"source": "Bosch", "url": "https://Bosch/new-url"}]}
    r = decide(previous={"old-id": old}, current={"new-id": renamed}, source_ok={"Bosch": True}, partial=set(),
               check=lambda s, u: UNKNOWN, today=TODAY, raw_urls=set())
    assert r.removed == {"old-id"} and not r.problems


def test_job_without_links_is_removed():
    linkless = {**job("a"), "links": []}
    r = run([linkless, job("b", "Bosch")], [now("b", "Bosch")])
    assert ids(r) == {"b"}
    assert r.removed == {"a"}
    assert r.problems == []


def test_a_link_that_moved_to_another_job_closes_the_stale_duplicate():
    # Yesterday the cut-off Arbeitsagentur copy was its own job; today it merges into the
    # employer's job. Its link is still open at the Arbeitsagentur, but it belongs elsewhere now.
    stale = job("cut", "Arbeitsagentur")
    employer = {**now("full", "GlobalFoundries"), "links": [
        {"source": "GlobalFoundries", "url": "https://GlobalFoundries/full"},
        {"source": "Arbeitsagentur", "url": "https://Arbeitsagentur/cut"},
    ]}
    r = run([stale], [employer], partial={"Arbeitsagentur"},
            checks={"https://Arbeitsagentur/cut": OPEN})
    assert r.removed == {"cut"} and ids(r) == {"full"}


def test_a_mass_retitle_is_moved_not_closed_and_skips_the_guard():
    # An aggregator re-titled all its postings: same URLs, new ids. That's no closure.
    prev = [job(f"old{i}", "Arbeitnow") for i in range(4)]
    current = [{**now(f"new{i}", "Arbeitnow"), "links": prev[i]["links"]} for i in range(4)]
    r = decide(previous={j["id"]: j for j in prev}, current={j["id"]: j for j in current},
               source_ok={"Arbeitnow": True}, partial={"Arbeitnow"}, check=lambda s, u: OPEN,
               today=TODAY, raw_urls=set())
    assert r.removed == {f"old{i}" for i in range(4)} and not r.problems
    assert r.stats["Arbeitnow"] == {OPEN: 4, CLOSED: 0, UNKNOWN: 0, MOVED: 4}


def test_a_moved_employer_link_still_closes_aggregator_copies():
    # The employer link of the old job now belongs to a new job; the aggregator copy can't keep it.
    old = job("old", "Bosch", "Arbeitnow")
    new = {**now("new", "Bosch"), "links": [old["links"][0]]}
    r = run([old], [new], partial={"Arbeitnow"}, checks={"https://Arbeitnow/old": OPEN})
    assert r.removed == {"old"} and ids(r) == {"new"}


# --- Employer closures are remembered (tombstones) ---

def test_employer_closure_leaves_a_tombstone():
    r = run([job("a", "Bosch", "Arbeitnow"), job("b", "Bosch"), job("c", "Bosch")],
            [now("b", "Bosch"), now("c", "Bosch")], partial={"Arbeitnow"}, checks={"https://Arbeitnow/a": OPEN})
    assert r.removed == {"a"} and r.closed_add == {"a": TODAY}


def test_aggregator_copy_of_a_closed_job_is_rejected():
    copy = now("a", "Arbeitnow")
    r = decide(previous={}, current={"a": copy}, source_ok={"Arbeitnow": True}, partial={"Arbeitnow"},
               check=lambda s, u: OPEN, today=TODAY, raw_urls=set(), closed={"a": "2026-10-20"})
    assert ids(r) == set() and r.rejected == {"a"} and not r.closed_drop
    assert "Arbeitnow" not in r.stats


def test_tombstone_expires_after_30_days():
    r = decide(previous={}, current={"a": now("a", "Arbeitnow")}, source_ok={"Arbeitnow": True},
               partial={"Arbeitnow"}, check=lambda s, u: OPEN, today=TODAY, raw_urls=set(),
               closed={"a": "2026-09-29"})
    assert ids(r) == {"a"} and not r.rejected


def test_employer_listing_the_job_again_reopens_it():
    r = decide(previous={}, current={"a": now("a", "Bosch")}, source_ok={"Bosch": True}, partial=set(),
               check=lambda s, u: UNKNOWN, today=TODAY, raw_urls=set(), closed={"a": "2026-10-20"})
    assert ids(r) == {"a"} and r.closed_drop == {"a"} and not r.rejected


def test_aggregator_only_closures_and_moves_leave_no_tombstone():
    # Closed on the job board only, and a renamed employer job (moved, not closed).
    r = run([job("agg", "Arbeitnow"), job("old", "Bosch")],
            [{**now("new", "Bosch"), "links": job("old", "Bosch")["links"]}],
            partial={"Arbeitnow"}, checks={"https://Arbeitnow/agg": CLOSED})
    assert r.removed == {"agg", "old"} and r.closed_add == {}


def test_guard_kept_jobs_leave_no_tombstone():
    prev = [job(f"j{i}", "Infineon") for i in range(4)]
    r = run(prev, [now("j0", "Infineon")])
    assert not r.removed and r.closed_add == {}


def test_old_job_whose_link_moved_to_a_rejected_copy_still_closes():
    # The board re-titled X so its URL now maps to tombstoned id T: T is rejected and X must go.
    x = job("x", "Arbeitnow")
    t = {**now("t", "Arbeitnow"), "links": x["links"]}
    r = decide(previous={"x": x}, current={"t": t}, source_ok={"Arbeitnow": True}, partial={"Arbeitnow"},
               check=lambda s, u: OPEN, today=TODAY, raw_urls=set(), closed={"t": "2026-10-20"})
    assert r.removed == {"x"} and ids(r) == set() and r.rejected == {"t"}
