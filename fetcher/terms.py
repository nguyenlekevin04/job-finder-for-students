"""Hours per week and pay, taken from a posting only when it states them.

extract_terms() never guesses: no unit, a range of pay, a minimum-wage mention, a
benefit (ticket, subsidy) or values that disagree all give None. Pure functions, so
tests run on plain strings.

Hours: a single value gives hoursMin == hoursMax; "max. 20" / "bis zu 20" gives only
hoursMax; "mind. 10" / "ab 10" gives only hoursMin; "15-20" gives both.
Pay: EUR only, per hour or per month, as a single stated amount.
"""
from __future__ import annotations

import re

HOURS_RANGE = (1, 40)
PAY_RANGE = {"hour": (5, 60), "month": (200, 4000)}

EMPTY = {"hoursMin": None, "hoursMax": None, "payAmount": None, "payUnit": None}


def _clean(text: str) -> str:
    text = re.sub(r"[   ]", " ", text or "")
    text = re.sub(r"[‐-―−]", "-", text)  # en/em dashes, minus
    return re.sub(r"\s+", " ", text)


# ------------------------------------------------------------------ hours --
NUM = r"(?<![\d.,/])(\d{1,2})(?![\d]|[.,]\d)"
HOURS_NUM = NUM.replace("(\\d", "(?P<lo>\\d", 1) + r"(?:\s*(?:-|bis|to|und|and)\s*" + NUM.replace("(\\d", "(?P<hi>\\d", 1) + ")?"
H_UNIT = r"(?:h|hrs?\.?|hours?|std\.?|stunden?)(?![a-zäöü])"
PER_WEEK = r"\s*(?:(?:/|pro|per|a|je|in der|die)\s*(?:woche|week|wk)(?![a-z])|(?:wöchentlich|weekly)(?![a-z]))"

HOUR_TIERS = [
    # 1. "20 Std./Woche", "15-20 h/week", "max. 20 Stunden pro Woche", "20 hours a week"
    re.compile(HOURS_NUM + r"\s*-?\s*" + H_UNIT + PER_WEEK, re.I),
    # 2. "20 Wochenstunden", "eine 20-Stunden-Woche", "20-hour week"
    re.compile(HOURS_NUM + r"\s*-?\s*(?:wochenstunden|wochenarbeitsstunden|(?:stunden|h|hours?)[- ](?:woche|week))(?![a-z])", re.I),
    # 3. "wöchentliche Arbeitszeit von 20 Stunden", "weekly hours: 15-20"
    re.compile(r"(?:wöchentlichen?\s+arbeitszeit|wochenarbeitszeit|arbeitszeit\s+pro\s+woche|weekly\s+(?:working\s+)?hours"
               r"|working\s+hours\s+per\s+week)\W{0,5}(?:[a-zäöü]+\W+){0,4}?" + HOURS_NUM + r"(?:\s*" + H_UNIT + ")?", re.I),
    # 4. "Arbeitszeit 15-20 Stunden", "Teilzeit (20 Stunden)", "part-time (20 hours)"
    re.compile(r"(?:arbeitszeit|working\s+hours|teilzeit|part[- ]time|stundenumfang|zeitumfang|workload)\W{0,5}"
               r"(?:[a-zäöü]+\W+){0,4}?" + HOURS_NUM + r"\s*" + H_UNIT, re.I),
]
# 5. Title and tags only: "Werkstudent (20h)", "Werkstudent 20 Std."
TITLE_HOURS = re.compile(HOURS_NUM + r"\s*" + H_UNIT + r"(?!-)", re.I)  # not "24h-Service"

NOT_WEEKLY = re.compile(r"^\W{0,3}\s*(?:(?:/|pro|per|a|im|je|am|in\s+the|the|an)\s*)?(?:monat|month|tag|day|jahr|year|semester)"
                        r"|^\W{0,3}\s*(?:täglich|daily|monatlich|monthly|jährlich|yearly|annually)", re.I)
BREAK = re.compile(r"semesterferien|vorlesungsfrei|semester\s*break|semesterbreak|ferien|holidays?|vacations?|\bbreaks?\b", re.I)
MAX_BEFORE = re.compile(r"\b(?:max\.?|maximal|maximum|höchstens|bis\s+zu|up\s+to|no\s+more\s+than|nicht\s+mehr\s+als|at\s+most)"
                        r"(?:\s+(?:mit|of|von))?\s*$", re.I)
MIN_BEFORE = re.compile(r"\b(?:mind\.?|mindestens|min\.?|ab|at\s+least|minimum(?:\s+of)?|from)\s*$", re.I)
FULL_TIME = re.compile(r"vollzeit(?!stud)|full[- ]time(?!\s+stud)", re.I)  # "Arbeitszeit für Vollzeitbeschäftigte: 40 Stunden"
CLOCK_AFTER = re.compile(r"^\W{0,3}\s*(?:uhr|mittagspause|pause|break)", re.I)  # "9-17 Uhr", "2 h Mittagspause"
CLOCK_BEFORE = re.compile(r"gleitzeit|mo\.?\s*-\s*fr|\bmontags?\b", re.I)  # "Gleitzeit 7-19 h", "Mo-Fr 9-17 h"
TIER4_MIN = 5  # "Teilzeit, 2 h ..." is not a weekly figure


def _clause_before(text: str, start: int) -> str:
    """Text before start back to the last clause break (or 40 chars)."""
    before = text[max(0, start - 40):start]
    cut = max(before.rfind(c) for c in ",;:(!?")
    stop = re.search(r"\.\s+[A-ZÄÖÜ]", before)  # sentence end, not "max. 20"
    if stop:
        cut = max(cut, stop.start())
    return before[cut + 1:] if cut >= 0 else before


def _clause_after(text: str, end: int) -> str:
    after = text[end:end + 40]
    m = re.search(r"[,;)(!?]|\.\s", after)
    return after[:m.start()] if m else after


def _hour_candidate(text: str, m: re.Match, weekly: bool = True, min_hours: int = HOURS_RANGE[0]
                    ) -> tuple[int | None, int | None] | None:
    """weekly=False for patterns without a weekly unit (tier 4, title), where a range may be a time of day."""
    if NOT_WEEKLY.search(text[m.end():m.end() + 25]):
        return None
    # Same clause only: "Vollzeitstudium" in an earlier sentence must not wipe out real hours.
    if FULL_TIME.search(_clause_before(text, m.start("lo"))) or FULL_TIME.search(_clause_after(text, m.end())):
        return None  # full-time boilerplate, not the student's hours
    if CLOCK_AFTER.search(text[m.end():m.end() + 20]) or CLOCK_BEFORE.search(_clause_before(text, m.start("lo"))):
        return None  # a time of day or a break, not hours per week
    if BREAK.search(_clause_after(text, m.end())) or BREAK.search(_clause_before(text, m.start())):
        return None  # semester-break hours; the lecture-period value is the one that matters
    lo, hi = int(m.group("lo")), m.group("hi")
    if hi is not None:
        hi = int(hi)
        if hi < lo:
            return None
        # The unit written after the range: "8-20 Stunden" is a weekly range, "9-17 h" may be office hours.
        spelled_out = re.match(r"\s*(?:stunden|std|hours?\b)", text[m.end("hi"):], re.I)
        if not weekly and not spelled_out and 6 <= lo <= 9 and hi >= 17:
            return None  # "9 to 17 h" is office hours; "15-20 h" and "10-20 h" stay
        lo_v, hi_v = lo, hi
    else:
        before = text[max(0, m.start("lo") - 25):m.start("lo")]
        if MAX_BEFORE.search(before):
            lo_v, hi_v = None, lo
        elif MIN_BEFORE.search(before):
            lo_v, hi_v = lo, None
        else:
            lo_v = hi_v = lo
    lo_ok, hi_ok = min_hours, HOURS_RANGE[1]
    if any(v is not None and not lo_ok <= v <= hi_ok for v in (lo_v, hi_v)):
        return None
    return lo_v, hi_v


def _pick_hours(cands: list[tuple[int | None, int | None]]) -> tuple[int | None, int | None] | None:
    """One value, or a specific value under a stated cap; anything else is a conflict (None)."""
    distinct = list(dict.fromkeys(cands))
    if len(distinct) == 1:
        return distinct[0]
    caps = [c for c in distinct if c[0] is None]
    specific = [c for c in distinct if c[0] is not None]
    if len(specific) == 1 and specific[0][1] is not None and all(specific[0][1] <= c[1] for c in caps) \
            and len(caps) + 1 == len(distinct):
        return specific[0]
    return None


def extract_hours(title: str, tags: str, description: str) -> tuple[int | None, int | None]:
    head = _clean(f"{title} . {tags}")
    full = _clean(f"{title} . {tags} . {description}")
    for pattern in HOUR_TIERS:
        args = (False, TIER4_MIN) if pattern is HOUR_TIERS[-1] else ()
        cands = [c for m in pattern.finditer(full) if (c := _hour_candidate(full, m, *args))]
        if cands:
            return _pick_hours(cands) or (None, None)
    cands = [c for m in TITLE_HOURS.finditer(head) if (c := _hour_candidate(head, m, False))]
    if cands:
        return _pick_hours(cands) or (None, None)
    return None, None


# -------------------------------------------------------------------- pay --
AMT = r"(?<![\d.,])(?P<amt>\d{1,3}(?:[.,]\d{3})+(?:[.,]\d{1,2})?|\d{1,5}(?:[.,]\d{1,2})?)(?:,-|\.-)?(?![\d])"
CUR = r"(?:€|\beur\b|\beuro\b)"
GROSS = r"(?:\s*\(?\s*(?:brutto|gross|netto|net)\s*\)?)?"
HOUR_U = (r"(?:/\s*(?:std|stunde|h|hr|hour)(?![a-zäöü])\.?|(?:pro|per|je|die|an?)\s+(?:stunde|hour|std)(?![a-zäöü])\.?"
          r"|stündlich|hourly|in\s+der\s+stunde)")
MONTH_U = r"(?:/\s*(?:monat|mon|mtl|month|mo)(?![a-zäöü])\.?|(?:pro|per|im|je|a)\s+(?:monat|month)(?![a-zäöü])|monatlich|monthly)"
UNIT = rf"\s*(?:(?P<hour>{HOUR_U})|(?P<month>{MONTH_U}))"

PAY_PATTERNS = [
    re.compile(AMT + r"\s*" + CUR + GROSS + UNIT, re.I),  # "15,50 €/Std.", "1.200 € brutto/Monat"
    re.compile(CUR + r"\s*" + AMT + GROSS + UNIT, re.I),  # "€15 per hour", "EUR 1,200 per month"
]
PAY_KEY = (r"(?:(?P<hour>stundenlohn|stundensatz|stundenvergütung|hourly\s+(?:rate|wage|pay|salary))"
           r"|(?P<month>monatsgehalt|monatsvergütung|monatliche\s+vergütung|monthly\s+(?:salary|pay|stipend|allowance)))"
           r"[^\d€.;]{0,25}")
PAY_KEYWORDS = [  # "Stundenlohn: 15 €", "monthly stipend of EUR 1,200"
    re.compile(PAY_KEY + CUR + r"\s*" + AMT, re.I),
    re.compile(PAY_KEY + AMT + r"\s*" + CUR, re.I),
]

# Amounts that aren't the pay: minimum wage, benefits, caps and starting salaries.
NOT_PAY = re.compile(r"mindestlohn|minimum\s+wage|zuschuss|zulage|ticket|jobrad|fahrtkosten|\bessen|kantine|prämie|bonus"
                     r"|subsid|budget|guthaben|gutschein|voucher|mitgliedschaft|membership|rabatt|discount|altersvorsorge"
                     r"|pension|umzug|relocation|einstieg|starting\s+salary|after\s+graduation|nach\s+(?:dem|deinem|ihrem)\s+studium"
                     r"|vollzeit|full[- ]time|überstunden|overtime|zzgl|zuzüglich", re.I)
QUALIFIED = re.compile(r"\b(?:bis\s+zu|up\s+to|max\.?|maximal|höchstens|ab|from|mind\.?|mindestens|at\s+least|ca\.?|circa|approx\.?|about|rund|etwa)\s*(?:€|eur|euro)?\s*$", re.I)
RANGE_BEFORE = re.compile(r"\d\s*(?:€|eur|euro)?\s*(?:-|bis|to)\s*(?:€|eur|euro)?\s*$", re.I)
RANGE_AFTER = re.compile(r"^\s*(?:€|eur|euro)?\s*(?:-|bis|to)\s*(?:€|eur|euro)?\s*\d", re.I)


def parse_amount(s: str) -> float:
    s = s.rstrip("-").rstrip(",.")
    if re.fullmatch(r"\d{1,3}(?:[.,]\d{3})+(?:[.,]\d{1,2})?", s):
        m = re.search(r"[.,](\d{1,2})$", s)
        dec = m.group(1) if m else ""
        whole = re.sub(r"[.,]", "", s[:m.start()] if m else s)
        return float(f"{whole}.{dec}" if dec else whole)
    return float(s.replace(",", "."))


def _pay_candidate(text: str, m: re.Match) -> tuple[float, str] | None:
    unit = "hour" if m.group("hour") else "month"
    if NOT_PAY.search(text[max(0, m.start() - 60):m.start()]) or NOT_PAY.search(text[m.start():m.end()]):
        return None
    before = text[max(0, m.start("amt") - 20):m.start("amt")]
    if QUALIFIED.search(before) or RANGE_BEFORE.search(before):
        return None
    after_amt = text[m.end("amt"):m.end("amt") + 15]
    if RANGE_AFTER.search(after_amt):
        return None
    amount = parse_amount(m.group("amt"))
    lo, hi = PAY_RANGE[unit]
    if not lo <= amount <= hi:
        return None
    return round(amount, 2), unit


def extract_pay(title: str, tags: str, description: str) -> tuple[float | None, str | None]:
    text = _clean(f"{title} . {tags} . {description}")
    cands = [c for p in PAY_PATTERNS + PAY_KEYWORDS for m in p.finditer(text) if (c := _pay_candidate(text, m))]
    by_unit: dict[str, set[float]] = {}
    for amount, unit in cands:
        by_unit.setdefault(unit, set()).add(amount)
    for unit in ("hour", "month"):  # an hourly rate is the base figure when both are given
        values = by_unit.get(unit)
        if values:
            return (values.pop(), unit) if len(values) == 1 else (None, None)
    return None, None


def extract_terms(title: str, tags: str, description: str) -> dict:
    """{"hoursMin", "hoursMax", "payAmount", "payUnit"}; None for anything not stated."""
    hours_min, hours_max = extract_hours(title or "", tags or "", description or "")
    pay, unit = extract_pay(title or "", tags or "", description or "")
    return {"hoursMin": hours_min, "hoursMax": hours_max, "payAmount": pay, "payUnit": unit}
