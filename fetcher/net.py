"""Small HTTP and text helpers shared by all sources."""
from __future__ import annotations

import html
import re
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
                res = _session.post(url, headers=headers, params=params, json=json_body, timeout=timeout)
            else:
                res = _session.get(url, headers=headers, params=params, timeout=timeout)
            res.raise_for_status()
            return res
        except requests.RequestException as err:
            last_err = err
            if attempt < retries:
                time.sleep(1 + attempt)
    raise last_err  # type: ignore[misc]


def status_code(url: str, *, headers: dict | None = None, timeout: int = 15) -> int | None:
    """HTTP status of a single GET without following redirects; None when unreachable.

    Used to ask whether one posting still exists, so errors are not raised.
    """
    try:
        return _session.get(url, headers=headers, timeout=timeout, allow_redirects=False).status_code
    except requests.RequestException:
        return None


def get_json(url: str, **kw):
    return _request(url, **kw).json()


def post_json(url: str, body: dict, **kw):
    """POST a JSON body and return the JSON reply (search APIs like Workday need this)."""
    return _request(url, json_body=body, **kw).json()


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
