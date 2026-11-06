"""Job alerts by web push (fetcher/push.py). No network: the store and the sender are fakes."""
from fetcher import push

TODAY = "2026-11-03"


def job(jid, city="berlin", types=("werkstudent",), fields=("ai",), first=TODAY, remote=False):
    return {"id": jid, "title": f"Job {jid}", "city": city, "types": list(types), "fields": list(fields),
            "firstSeen": first, "remote": remote}


def sub(endpoint, board="berlin", types=(), fields=(), last_sent=None, confirmed=True):
    return {"endpoint": endpoint, "p256dh": "k", "auth": "a", "board": board, "types": list(types),
            "fields": list(fields), "last_sent": last_sent, "confirmed": confirmed}


class FakeStore:
    def __init__(self, subs):
        self.subs, self.sent_to, self.deleted, self.confirmed = subs, [], [], []

    def all(self):
        return self.subs

    def sent(self, endpoint, today):
        self.sent_to.append(endpoint)

    def confirm(self, endpoint):
        self.confirmed.append(endpoint)

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
    assert counts == {"sent": 1, "confirmed": 0, "removed": 0, "failed": 0}
    assert store.sent_to == ["fresh"]
    endpoint, payload = payloads[0]
    assert payload["title"] == "1 new student job in Berlin"
    assert payload["url"].startswith("https://dresden-jobs.vercel.app/berlin/?") and "new=1" in payload["url"]


def test_gone_subscriptions_are_removed_and_errors_counted(monkeypatch):
    monkeypatch.setenv("VAPID_PRIVATE_KEY", "test")
    store = FakeStore([sub("gone"), sub("broken")])
    status = {"gone": 410, "broken": 500}
    counts = push.send_alerts([job("a")], TODAY, "", "", store=store, send=lambda s, p: status[s["endpoint"]])
    assert counts == {"sent": 0, "confirmed": 0, "removed": 1, "failed": 1}
    assert store.deleted == ["gone"] and store.sent_to == []


def test_nothing_happens_without_the_key(monkeypatch):
    monkeypatch.delenv("VAPID_PRIVATE_KEY", raising=False)
    assert push.send_alerts([job("a")], TODAY, "", "", store=FakeStore([sub("x")]), send=lambda s, p: 201) == {}


def test_message_wording():
    m = push.message([job(str(i)) for i in range(5)], sub("x", board="remote", types=["thesis"], fields=["ai"]))
    assert m["title"] == "5 new thesis jobs remote"
    assert m["body"].endswith("…")
    assert "type=thesis" in m["url"] and "field=ai" in m["url"] and m["url"].startswith("https://dresden-jobs.vercel.app/remote/")


def test_one_broken_subscription_never_stops_the_others(monkeypatch):
    monkeypatch.setenv("VAPID_PRIVATE_KEY", "test")
    store = FakeStore([sub("0-broken"), sub("1-real"), sub("2-bad-request")])

    def send(s, p):
        if s["endpoint"] == "0-broken":
            raise ValueError("Unsupported elliptic curve point type")
        return 400 if s["endpoint"] == "2-bad-request" else 201

    counts = push.send_alerts([job("a")], TODAY, "", "", store=store, send=send)
    assert store.sent_to == ["1-real"] and sorted(store.deleted) == ["0-broken", "2-bad-request"]
    assert counts["sent"] == 1 and counts["removed"] == 2


def test_new_signups_must_receive_the_welcome_before_they_count(monkeypatch):
    monkeypatch.setenv("VAPID_PRIVATE_KEY", "test")
    store = FakeStore([sub("real", confirmed=False), sub("fake", confirmed=False)])
    sent = []
    counts = push.send_alerts([job("a")], TODAY, "", "", store=store,
                              send=lambda s, p: sent.append((s["endpoint"], p["title"])) or (201 if s["endpoint"] == "real" else 404))
    assert store.confirmed == ["real"] and store.deleted == ["fake"]
    assert ("real", "Alerts are on") in sent
    assert not any(title != "Alerts are on" for _, title in sent)  # job alerts start with the next run
    assert counts["confirmed"] == 1 and counts["removed"] == 1


def test_a_multi_city_job_is_on_each_of_its_boards():
    from fetcher.push import on_board
    job = {"city": "leipzig", "cities": ["leipzig", "berlin"]}
    assert on_board(job, "leipzig") and on_board(job, "berlin") and not on_board(job, "dresden")
    assert on_board({"city": "dresden"}, "dresden")  # saved before cities existed
    assert not on_board({"city": "", "cities": [], "remote": True}, "berlin")
