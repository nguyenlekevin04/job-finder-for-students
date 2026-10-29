"""Which jobs stay on the board (fetcher/availability.py). No network."""
from fetcher.availability import CLOSED, OPEN, UNKNOWN, decide
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


def run(previous, current, ok=None, partial=(), checks=None):
    ok = ok or {s: True for j in [*previous, *current] for l in j["links"] for s in [l["source"]]}
    checks = checks or {}
    return decide(
        previous={j["id"]: j for j in previous},
        current={j["id"]: j for j in current},
        source_ok=ok,
        partial=set(partial),
        check=lambda src, url: checks.get(url, UNKNOWN),
        today=TODAY,
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
    assert r.stats["Arbeitnow"] == {OPEN: 1, CLOSED: 1, UNKNOWN: 2}


def test_listed_partial_job_is_removed_when_its_check_says_closed():
    prev = [job("a", "Arbeitsagentur"), job("b", "Arbeitsagentur"), job("c", "Arbeitsagentur")]
    current = [now("a", "Arbeitsagentur"), now("b", "Arbeitsagentur"), now("c", "Arbeitsagentur"),
               now("new-but-closed", "Arbeitsagentur")]
    checks = {"https://Arbeitsagentur/a": CLOSED, "https://Arbeitsagentur/new-but-closed": CLOSED}
    r = run(prev, current, partial={"Arbeitsagentur"}, checks=checks)
    assert r.removed == {"a"}
    assert ids(r) == {"b", "c"}  # a closed new job is never stored


def test_one_open_link_keeps_the_job_and_closed_links_are_dropped():
    prev = [job("a", "Bosch", "Arbeitnow")]
    r = run(prev, [], partial={"Arbeitnow"}, checks={"https://Arbeitnow/a": OPEN})
    assert ids(r) == {"a"}
    assert [l["source"] for l in r.jobs[0]["links"]] == ["Arbeitnow"]


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
    assert r.removed == {"h1", "h2"} and not r.problems


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
