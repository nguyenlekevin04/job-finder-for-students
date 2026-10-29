"""Employer feeds must fail loudly instead of stopping silently at their page cap.

A cut-off list would make the missing postings count as closed (availability.py),
so fetch() raises when it reaches the cap without the feed signalling its end.
"""
import pytest

from fetcher.sources import amazon, bosch, fraunhofer, globalfoundries, infineon


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda _s: None)


# Titles that is_student_title() ignores, so fetch() makes no detail requests.
def _title(i: int) -> str:
    return f"Process Engineer {i}"


# --- Infineon (Eightfold: 10 per page, `count` = total) ---

def _infineon_page(n: int, count: int | None, start: int = 0) -> dict:
    positions = [{"id": start + i + 1, "name": _title(start + i), "locations": ["Dresden, Germany"]} for i in range(n)]
    data = {"positions": positions}
    if count is not None:
        data["count"] = count
    return {"data": data}


def test_infineon_is_last_page():
    assert infineon.is_last_page(_infineon_page(3, 23), 2)       # short page
    assert infineon.is_last_page(_infineon_page(10, 20), 1)      # count reached
    assert not infineon.is_last_page(_infineon_page(10, 21), 1)
    assert not infineon.is_last_page(_infineon_page(10, None), 1)


def test_infineon_raises_past_the_cap(monkeypatch):
    total = infineon.MAX_PAGES * infineon.PAGE + 1
    monkeypatch.setattr(infineon, "get_json",
                        lambda url, params: _infineon_page(infineon.PAGE, total, params["start"]))
    with pytest.raises(RuntimeError, match="Infineon: more than 150 postings"):
        infineon.fetch()


def test_infineon_feed_ending_early_is_fine(monkeypatch):
    calls = []

    def get_json(url, params):
        calls.append(params["start"])
        start = params["start"]
        return _infineon_page(min(infineon.PAGE, 25 - start), 25, start)

    monkeypatch.setattr(infineon, "get_json", get_json)
    assert len(infineon.fetch()) == 25
    assert calls == [0, 10, 20]


def test_infineon_exact_multiple_stops_on_count(monkeypatch):
    monkeypatch.setattr(infineon, "get_json",
                        lambda url, params: _infineon_page(infineon.PAGE, 20, params["start"]))
    assert len(infineon.fetch()) == 20


def test_infineon_empty_page_before_count_raises(monkeypatch):
    monkeypatch.setattr(infineon, "get_json", lambda url, params: _infineon_page(
        infineon.PAGE if params["start"] == 0 else 0, 60, params["start"]))
    with pytest.raises(RuntimeError, match="Infineon: feed ended early: got 10 of 60"):
        infineon.fetch()


def test_infineon_short_page_before_count_raises(monkeypatch):
    monkeypatch.setattr(infineon, "get_json", lambda url, params: _infineon_page(
        infineon.PAGE if params["start"] == 0 else 4, 60, params["start"]))
    with pytest.raises(RuntimeError, match="Infineon: feed ended early: got 14 of 60"):
        infineon.fetch()


# --- GlobalFoundries (Workday: 20 per page, `total` only on the first page) ---

def _gf_page(offset: int, n: int, total: int) -> dict:
    return {"total": total if offset == 0 else 0, "jobPostings": [
        {"title": _title(offset + i), "externalPath": f"/job/Dresden/x_{offset + i}",
         "locationsText": "Dresden", "bulletFields": [f"JR-{offset + i}"]} for i in range(n)]}


def test_globalfoundries_is_last_page():
    assert globalfoundries.is_last_page(_gf_page(40, 3, 43), 2, 43)
    assert not globalfoundries.is_last_page(_gf_page(20, 20, 43), 1, 43)
    assert globalfoundries.is_last_page({"jobPostings": []}, 1, 43)  # empty page ends it


def test_globalfoundries_raises_past_the_cap(monkeypatch):
    total = globalfoundries.MAX_PAGES * globalfoundries.PAGE + 1
    monkeypatch.setattr(globalfoundries, "post_json",
                        lambda url, body: _gf_page(body["offset"], globalfoundries.PAGE, total))
    with pytest.raises(RuntimeError, match="GlobalFoundries: more than 200 postings"):
        globalfoundries.fetch()


def test_globalfoundries_reads_every_page_although_later_totals_are_zero(monkeypatch):
    # Live Workday answers total=0 after the first page; the old loop stopped after 40 of 43.
    monkeypatch.setattr(globalfoundries, "post_json",
                        lambda url, body: _gf_page(body["offset"], min(20, 43 - body["offset"]), 43))
    assert len(globalfoundries.fetch()) == 43


def test_globalfoundries_empty_page_before_total_raises(monkeypatch):
    monkeypatch.setattr(globalfoundries, "post_json", lambda url, body: _gf_page(
        body["offset"], globalfoundries.PAGE if body["offset"] == 0 else 0, 60))
    with pytest.raises(RuntimeError, match="GlobalFoundries: feed ended early: got 20 of 60"):
        globalfoundries.fetch()


def test_globalfoundries_exact_multiple_is_fine(monkeypatch):
    monkeypatch.setattr(globalfoundries, "post_json",
                        lambda url, body: _gf_page(body["offset"], globalfoundries.PAGE, 60))
    assert len(globalfoundries.fetch()) == 60


# --- Bosch (SmartRecruiters: 100 per page, `totalFound`) ---

def _bosch_page(offset: int, n: int, total: int) -> dict:
    return {"offset": offset, "totalFound": total, "content": [
        {"id": str(offset + i), "name": _title(offset + i), "location": {"city": "Dresden"}} for i in range(n)]}


def test_bosch_is_last_page():
    assert bosch.is_last_page(_bosch_page(0, 42, 42), 0)
    assert not bosch.is_last_page(_bosch_page(0, 100, 142), 0)
    assert bosch.is_last_page(_bosch_page(100, 0, 142), 1)  # empty page ends it


def test_bosch_raises_past_the_cap(monkeypatch):
    total = bosch.MAX_PAGES * bosch.PAGE + 1
    monkeypatch.setattr(bosch, "get_json",
                        lambda url, params: _bosch_page(params["offset"], bosch.PAGE, total))
    with pytest.raises(RuntimeError, match="Bosch: more than 500 postings"):
        bosch.fetch()


def test_bosch_feed_ending_early_is_fine(monkeypatch):
    monkeypatch.setattr(bosch, "get_json",
                        lambda url, params: _bosch_page(params["offset"], min(100, 142 - params["offset"]), 142))
    assert len(bosch.fetch()) == 142


def test_bosch_empty_page_before_total_raises(monkeypatch):
    monkeypatch.setattr(bosch, "get_json", lambda url, params: _bosch_page(
        params["offset"], bosch.PAGE if params["offset"] == 0 else 0, 160))
    with pytest.raises(RuntimeError, match="Bosch: feed ended early: got 100 of 160"):
        bosch.fetch()


def test_bosch_short_page_before_total_raises(monkeypatch):
    monkeypatch.setattr(bosch, "get_json", lambda url, params: _bosch_page(params["offset"], 30, 60))
    with pytest.raises(RuntimeError, match="Bosch: feed ended early: got 30 of 60"):
        bosch.fetch()


def test_bosch_exact_multiple_is_fine(monkeypatch):
    monkeypatch.setattr(bosch, "get_json",
                        lambda url, params: _bosch_page(params["offset"], min(100, 200 - params["offset"]), 200))
    assert len(bosch.fetch()) == 200


# --- Fraunhofer (HTML portal: 25 rows per page, no total) ---

def test_fraunhofer_is_last_page(fixture_text):
    full = fraunhofer.parse_list(fixture_text("fraunhofer_list.html"))
    assert not fraunhofer.is_last_page(full)
    assert fraunhofer.is_last_page(full[:3])
    assert fraunhofer.is_last_page([])


def _fraunhofer_get_text(list_html: str, last_start: int | None):
    def get_text(url, params=None):
        if params is None:  # a detail page
            return "<html></html>"
        if last_start is not None and params["startrow"] >= last_start:
            return "<html><table></table></html>"
        return list_html
    return get_text


def test_fraunhofer_raises_past_the_cap(monkeypatch, fixture_text):
    monkeypatch.setattr(fraunhofer, "get_text", _fraunhofer_get_text(fixture_text("fraunhofer_list.html"), None))
    with pytest.raises(RuntimeError, match="Fraunhofer: more than 400 postings"):
        fraunhofer.fetch()


def test_fraunhofer_feed_ending_early_is_fine(monkeypatch, fixture_text):
    monkeypatch.setattr(fraunhofer, "get_text", _fraunhofer_get_text(fixture_text("fraunhofer_list.html"), 50))
    assert len(fraunhofer.fetch()) == 50


# --- Amazon (one request, `hits` = total) ---

def _amazon(hits: int, n: int) -> dict:
    return {"hits": hits, "jobs": [
        {"id_icims": str(i), "title": _title(i), "job_path": f"/en/jobs/{i}", "city": "Dresden"} for i in range(n)]}


def test_amazon_check_complete():
    amazon.check_complete(_amazon(9, 9))
    amazon.check_complete({"jobs": []})
    with pytest.raises(RuntimeError, match="Amazon: more than 100 postings"):
        amazon.check_complete(_amazon(101, 100))


def test_amazon_fetch_raises_past_the_limit(monkeypatch):
    monkeypatch.setattr(amazon, "get_json", lambda url, params: _amazon(params["result_limit"] + 5,
                                                                        params["result_limit"]))
    with pytest.raises(RuntimeError):
        amazon.fetch()


def test_amazon_fetch_complete_feed(monkeypatch, fixture_text):
    import json
    data = json.loads(fixture_text("amazon.json"))
    monkeypatch.setattr(amazon, "get_json", lambda url, params: data)
    assert amazon.fetch() == amazon.parse(data)


def test_globalfoundries_without_total_ends_on_a_short_page():
    from fetcher.sources import globalfoundries as gf
    full = {"jobPostings": [{}] * gf.PAGE}
    short = {"jobPostings": [{}] * 3}
    assert not gf.is_last_page(full, 0, 0)
    assert gf.is_last_page(short, 1, 0)
    assert gf.is_last_page({"jobPostings": []}, 2, 0)
