"""SupabaseStore against a fake HTTP session (no network)."""
import json

import requests

from fetcher.store import SupabaseStore, get_store, JsonFileStore, to_row


class FakeResponse:
    def __init__(self, method, url, status=200, body=None, headers=None):
        self.ok = status < 400
        self.status_code = status
        self._body = body if body is not None else []
        self.headers = headers or {}
        self.text = json.dumps(self._body)
        self.url = url
        self.request = type("R", (), {"method": method})()

    def json(self):
        return self._body


class FakeSession(requests.Session):
    def __init__(self, existing=None, total=3):
        super().__init__()
        self.calls = []
        self.existing = existing or []
        self.total = total

    def request(self, method, url, params=None, headers=None, data=None, **kw):
        self.calls.append({"method": method, "url": url, "params": params or {}, "headers": headers or {},
                           "body": json.loads(data) if data else None})
        if method == "GET" and (params or {}).get("select") == "id,first_seen":
            return FakeResponse(method, url, body=self.existing)
        if method == "GET":
            return FakeResponse(method, url, status=206, headers={"Content-Range": f"0-0/{self.total}"})
        return FakeResponse(method, url, status=201)


def job(jid):
    return {"id": jid, "title": "Werkstudent Software", "company": "ACME", "location": "Dresden", "remote": False,
            "type": "werkstudent", "types": ["werkstudent"], "fields": ["software"], "englishFriendly": True,
            "postedAt": None, "deadline": None, "links": [{"source": "A", "url": "https://a"}], "snippet": ""}


def test_save_upserts_keeps_first_seen_prunes_and_logs_run():
    session = FakeSession(existing=[{"id": "old", "first_seen": "2026-09-01"}])
    store = SupabaseStore("https://abc.supabase.co/", "sb_secret_x", session=session)
    total = store.save({"old": job("old"), "new": job("new")}, {"A": {"ok": True, "count": 2}},
                       "2026-10-28T05:00:00+00:00", "2026-10-28")
    assert total == 3

    upsert = next(c for c in session.calls if c["method"] == "POST" and c["url"].endswith("/jobs"))
    assert upsert["url"] == "https://abc.supabase.co/rest/v1/jobs"
    assert upsert["params"] == {"on_conflict": "id"}
    assert "merge-duplicates" in upsert["headers"]["Prefer"]
    rows = {r["id"]: r for r in upsert["body"]}
    assert rows["old"]["first_seen"] == "2026-09-01"
    assert rows["new"]["first_seen"] == "2026-10-28"
    assert rows["new"]["last_seen"] == "2026-10-28"
    assert rows["new"]["english_friendly"] is True

    delete = next(c for c in session.calls if c["method"] == "DELETE")
    assert delete["params"] == {"last_seen": "lt.2026-10-21"}

    run = next(c for c in session.calls if c["url"].endswith("/fetch_runs"))
    assert run["body"] == {"generated_at": "2026-10-28T05:00:00+00:00", "job_count": 3,
                           "sources": {"A": {"ok": True, "count": 2}}}


def test_auth_header_only_for_jwt_keys():
    assert "Authorization" not in SupabaseStore("https://x.supabase.co", "sb_secret_abc", session=FakeSession()).session.headers
    legacy = SupabaseStore("https://x.supabase.co", "eyJhbGciOi.payload.sig", session=FakeSession())
    assert legacy.session.headers["Authorization"] == "Bearer eyJhbGciOi.payload.sig"
    assert legacy.session.headers["apikey"] == "eyJhbGciOi.payload.sig"


def test_errors_are_raised():
    class Failing(FakeSession):
        def request(self, method, url, **kw):
            return FakeResponse(method, url, status=401, body={"message": "Invalid API key"})
    store = SupabaseStore("https://x.supabase.co", "bad", session=Failing())
    try:
        store.first_seen()
    except RuntimeError as err:
        assert "401" in str(err)
    else:
        raise AssertionError("expected RuntimeError")


def test_row_mapping_covers_every_column():
    row = to_row({**job("a"), "firstSeen": "2026-10-28", "lastSeen": "2026-10-28"})
    assert set(row) == {"id", "title", "company", "location", "remote", "type", "types", "fields",
                        "english_friendly", "posted_at", "deadline", "first_seen", "last_seen", "links", "snippet"}


def test_get_store_picks_backend(monkeypatch, tmp_path):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
    assert isinstance(get_store(tmp_path / "j.json"), JsonFileStore)
    monkeypatch.setenv("SUPABASE_URL", "https://x.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "sb_secret_x")
    assert isinstance(get_store(tmp_path / "j.json"), SupabaseStore)


def test_base_url_accepts_rest_suffix():
    for url in ["https://x.supabase.co", "https://x.supabase.co/", "https://x.supabase.co/rest/v1",
                "https://x.supabase.co/rest/v1/", " https://x.supabase.co/rest/v1// ",
                "https://x.supabase.co/rest/v1/jobs?select=id"]:
        assert SupabaseStore(url, "sb_secret_x", session=FakeSession()).base == "https://x.supabase.co/rest/v1"
