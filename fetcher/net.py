"""Small HTTP and text helpers shared by all sources."""
from __future__ import annotations

import html
import re
import math
import time
from datetime import datetime, timezone

import requests

USER_AGENT = "Mozilla/5.0 (compatible; DresdenStudentJobs/1.0) python-requests"

_session = requests.Session()
# Ask for gzip only: some servers (amazon.jobs) answer requests' default "zstd" offer
# with a body urllib3 then fails to decode.
_session.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "de,en;q=0.8",
                         "Accept-Encoding": "gzip, deflate"})


def _request(url: str, *, headers: dict | None = None, params: dict | None = None,
         json_body: dict | None = None, retries: int = 2, timeout: int = 25) -> requests.Response:
    """GET (or POST when json_body is given) with a few retries."""
    last_err: Exception | None = None
    for attempt in range(retries + 1):
        try:
            if json_body is not None:
                res = _session.post(url, headers=headers, params=params, json=json_body, timeout=timeout, stream=True)
            else:
                res = _session.get(url, headers=headers, params=params, timeout=timeout, stream=True)
            res.raise_for_status()
            _read_capped(res, deadline=time.monotonic() + READ_SECONDS)
            return res
        except requests.RequestException as err:
            last_err = err
            if attempt < retries:
                time.sleep(_backoff(err, attempt))
    raise last_err  # type: ignore[misc]


MAX_BYTES = 15_000_000  # the largest real reply is ~2 MB; a giant one must not exhaust the runner's memory
READ_SECONDS = 60  # a reply that drips in slower than this is cut off (the timeout only bounds gaps)


class TooLarge(requests.RequestException):
    """A reply over MAX_BYTES or slower than READ_SECONDS (Kevin, attacks #4–#5)."""


def _read_capped(res: requests.Response, deadline: float) -> None:
    """Reads the streamed body into res, so .text/.json() work as usual, within size and time."""
    declared = res.headers.get("Content-Length")
    if declared and declared.isdigit() and int(declared) > MAX_BYTES:
        res.close()
        raise TooLarge(f"reply of {declared} bytes is over the {MAX_BYTES} limit")
    body = bytearray()
    for chunk in res.iter_content(64 * 1024):
        body += chunk
        if len(body) > MAX_BYTES:
            res.close()
            raise TooLarge(f"reply over the {MAX_BYTES} byte limit")
        if time.monotonic() > deadline:
            res.close()
            raise TooLarge(f"reply took longer than {READ_SECONDS}s")
    res._content = bytes(body)  # what requests itself fills in when it reads the body


BUSY = {429, 502, 503, 504}  # "too many requests" or a gateway hiccup: worth a longer pause
BUSY_WAIT_MAX = 15.0  # one pause at most
BUSY_BUDGET = 180.0  # all long pauses of one run together: a throttling site can't stall the 20-min Action
_busy_waited = 0.0


def _backoff(err: Exception, attempt: int) -> float:
    """Seconds to wait before the next try: the server's Retry-After (capped) when it is busy,
    while this run's budget for long pauses lasts; otherwise the short default."""
    global _busy_waited
    short = 1.0 + attempt
    res = getattr(err, "response", None)
    if res is None or res.status_code not in BUSY or _busy_waited >= BUSY_BUDGET:
        return short
    try:
        wait = float(res.headers.get("Retry-After", ""))
        if not math.isfinite(wait):
            raise ValueError
    except ValueError:  # missing, an HTTP date or junk: our own pause
        wait = 5.0 * (attempt + 1)
    wait = min(max(wait, short), BUSY_WAIT_MAX, BUSY_BUDGET - _busy_waited)
    _busy_waited += wait
    return wait


def status_code(url: str, *, headers: dict | None = None, timeout: int = 15) -> int | None:
    """HTTP status of a single GET without following redirects; None when unreachable.

    Used to ask whether one posting still exists, so errors are not raised.
    """
    try:
        return _session.get(url, headers=headers, timeout=timeout, allow_redirects=False).status_code
    except requests.RequestException:
        return None


def _json(url: str, **kw):
    """The JSON reply; an empty or broken body (seen from Workday, 2026-11-14) gets one more try."""
    try:
        return _request(url, **kw).json()
    except ValueError:
        time.sleep(3)
        return _request(url, **kw).json()


def get_json(url: str, **kw):
    return _json(url, **kw)


def post_json(url: str, body: dict, **kw):
    """POST a JSON body and return the JSON reply (search APIs like Workday need this)."""
    return _json(url, json_body=body, **kw)


def get_text(url: str, **kw) -> str:
    res = _request(url, **kw)
    # requests assumes ISO-8859-1 for text/* without a charset; guess instead.
    if "charset" not in res.headers.get("content-type", "").lower():
        res.encoding = res.apparent_encoding or "utf-8"
    return res.text


def clean_text(value: str | None) -> str:
    """Strip HTML tags, decode entities and squeeze whitespace."""
    if not value:
        return ""
    text = re.sub(r"<(script|style)[\s\S]*?</\1>", " ", str(value), flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def to_day(value) -> str | None:
    """Turn a unix timestamp or ISO-ish string into YYYY-MM-DD."""
    if value in (None, ""):
        return None
    try:
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value, tz=timezone.utc).strftime("%Y-%m-%d")
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).strftime("%Y-%m-%d")
    except ValueError:
        m = re.search(r"\d{4}-\d{2}-\d{2}", str(value))
        return m.group(0) if m else None


def de_date(value: str | None) -> str | None:
    """'30.10.2026' -> '2026-10-30'."""
    m = re.search(r"(\d{2})\.(\d{2})\.(\d{4})", value or "")
    return f"{m.group(3)}-{m.group(2)}-{m.group(1)}" if m else None
