"""Job alerts by web push (fetcher/push.py). No network: the store and the sender are fakes."""
from fetcher import push

TODAY = "2026-11-03"


def job(jid, city="berlin", types=("werkstudent",), fields=("ai",), first=TODAY, remote=False):
    return {"id": jid, "title": f"Job {jid}", "city": city, "types": list(types), "fields": list(fields),
            "firstSeen": first, "remote": remote}


def sub(endpoint, board="berlin", types=(), fields=(), last_sent=None):
    return {"endpoint": endpoint, "p256dh": "k", "auth": "a", "board": board, "types": list(types),
            "fields": list(fields), "last_sent": last_sent}


class FakeStore:
    def __init__(self, subs):
        self.subs, self.sent_to, self.deleted = subs, [], []

    def all(self):
        return self.subs

    def sent(self, endpoint, today):
        self.sent_to.append(endpoint)

    def delete(self, endpoint):
        self.deleted.append(endpoint)


def test_matching_follows_board_types_and_fields():
    assert push.matches(job("a"), sub("x", types=["werkstudent"], fields=["ai"]))
    assert not push.matches(job("a"), sub("x", board="dresden"))
    assert not push.matches(job("a", fields=["data"]), sub("x", fields=["ai"]))
    assert push.matches(job("r", city="", remote=True), sub("x", board="remote"))
    assert not push.matches(job("r", city="", remote=True), sub("x", board="berlin"))
    assert push.matches(job("old", city=None), sub("x", board="dresden"))  # rows from before cities


def test_only_new_jobs_and_at_most_once_a_day(monkeypatch):
    monkeypatch.setenv("VAPID_PRIVATE_KEY", "test")
    store = FakeStore([sub("fresh"), sub("done", last_sent=TODAY), sub("dresden", board="dresden")])
    payloads = []
    counts = push.send_alerts([job("a"), job("b", first="2026-11-01")], TODAY, "", "", store=store,
                              send=lambda s, p: payloads.append((s["endpoint"], p)) or 201)
    assert counts == {"sent": 1, "removed": 0, "failed": 0}
    assert store.sent_to == ["fresh"]
    endpoint, payload = payloads[0]
    assert payload["title"] == "1 new student job in Berlin"
    assert payload["url"].startswith("https://dresden-jobs.vercel.app/berlin/?") and "new=1" in payload["url"]


def test_gone_subscriptions_are_removed_and_errors_counted(monkeypatch):
    monkeypatch.setenv("VAPID_PRIVATE_KEY", "test")
    store = FakeStore([sub("gone"), sub("broken")])
    status = {"gone": 410, "broken": 500}
    counts = push.send_alerts([job("a")], TODAY, "", "", store=store, send=lambda s, p: status[s["endpoint"]])
    assert counts == {"sent": 0, "removed": 1, "failed": 1}
    assert store.deleted == ["gone"] and store.sent_to == []


def test_nothing_happens_without_the_key(monkeypatch):
    monkeypatch.delenv("VAPID_PRIVATE_KEY", raising=False)
    assert push.send_alerts([job("a")], TODAY, "", "", store=FakeStore([sub("x")]), send=lambda s, p: 201) == {}


def test_message_wording():
    m = push.message([job(str(i)) for i in range(5)], sub("x", board="remote", types=["thesis"], fields=["ai"]))
    assert m["title"] == "5 new thesis jobs remote"
    assert m["body"].endswith("…")
    assert "type=thesis" in m["url"] and "field=ai" in m["url"] and m["url"].startswith("https://dresden-jobs.vercel.app/remote/")
