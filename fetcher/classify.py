"""Decide whether a posting is a student tech job, and tag it.

classify(job) returns a dict of tags, or None when the job should be dropped.
All matching is keyword-based; tune the lists below to change what gets in.
"""
from __future__ import annotations

import re

from fetcher.models import Job

# ---------------------------------------------------------------- job type --
# Order matters only for picking the primary type when several match.
TYPE_PATTERNS: dict[str, re.Pattern] = {
    "werkstudent": re.compile(
        r"werkstudent|werk-student|working[- ]student|studentische[rn]? (mitarbeit|aushilf)|studentenjob",
        re.I),
    "internship": re.compile(
        r"praktik(um|ant|anti|antin)|pflichtpraktik|internship|\binterns?\b|\bpraxissemester|studentenpraktik",
        re.I),
    "thesis": re.compile(
        r"abschlussarbeit|bachelorarbeit|masterarbeit|diplomarbeit|studienarbeit|bachelor-?arbeit|master-?arbeit"
        r"|\bthes[ie]s\b|bachelor'?s? thes|master'?s? thes|abschlussthema",
        re.I),
}

# Postings that are never what we want, even if a type keyword appears.
EXCLUDE = re.compile(
    r"\bausbildung\b|auszubildende|\bazubi|duales? studium|dualer student|schüler|\bpupils?\b"
    r"|doktorand|\bph\.? ?d\b|postdoc|professur|\bsenior\b|\bteam ?lead|gruppenleit|abteilungsleit",
    re.I)

# --------------------------------------------------------------- tech field --
FIELD_PATTERNS: dict[str, re.Pattern] = {
    "ai": re.compile(
        r"\b(ai|ki)\b|\bki-|künstliche[rn]? intelligenz|artificial intelligence|machine[- ]learning"
        r"|maschinelle[sn]? lernen|deep[- ]learning|\bml\b|\bmlops|neural|neuronale|\bllms?\b|large language"
        r"|\bnlp\b|natural language|computer[- ]vision|bildverarbeitung|image processing|genai|generative"
        r"|reinforcement learning|neuromorph|sprachmodell|chatbot",
        re.I),
    "data": re.compile(
        r"data[- ]scien|data[- ]analy|data[- ]engineer|datenanaly|datenwissenschaft|datenbank|datenmanagement"
        r"|big data|\banalytics\b|business intelligence|power ?bi|\bsql\b|tableau|data warehouse"
        r"|\betl\b|statistik|statistics|data[- ]driven|daten-?science",
        re.I),
    "software": re.compile(
        r"software|informatik|computer science|programmier|programming|\bcoding\b"
        r"|(web|app|frontend|front-end|backend|back-end|full-?stack|spiele|game)[- ]?(entwickl|develop|engineer)"
        # Bare "frontend" is left out: at chip makers it means the wafer fab, not web UI.
        r"|backend|back-end|full-?stack|devops|cloud|\bpython\b|\bjava\b|javascript"
        r"|typescript|c\+\+|\bc#|\.net\b|\breact\b|angular|\bgolang\b|\brust\b|kubernetes|\blinux\b"
        r"|testautomat|test automation|qa engineer|anwendungsentwickl|fachinformatik|it-?entwickl"
        r"|developer|softwareentwickl|webentwickl|app-entwickl|plug-?in-entwickl|\bapi\b|algorithm",
        re.I),
    "hardware": re.compile(
        r"embedded|fpga|\basic\b|vlsi|mikroelektronik|microelectronic|halbleiter|semiconductor"
        r"|chip[- ]?design|elektrotechnik|electrical engineering|elektronik|electronics|hardware"
        r"|robotik|robotics|roboter|mechatronik|mechatronics|firmware|signalverarbeitung|signal processing"
        r"|informationstechnik|nachrichtentechnik|schaltungsentw|circuit design|integrated circuit",
        re.I),
    "other": re.compile(
        r"it[- ]?security|cyber[- ]?security|it-sicherheit|informationssicherheit|\bhpc\b"
        r"|high[- ]performance computing|quantum computing|quantencomput|computational|bioinformatik"
        r"|wirtschaftsinformatik|systemadministr|netzwerktechn|network engineer|it[- ]support"
        r"|it[- ]administr|it[- ]infrastru|it[- ]consult|it[- ]projekt|\bsap\b",
        re.I),
}
# "IT" only as a capitalised word, so "it" in English sentences doesn't count.
IT_WORD = re.compile(r"\bIT\b|\bIT-")
BI_WORD = re.compile(r"\bBI\b(?!-)")

# Titles with these words are non-tech roles; their descriptions alone can't make them tech.
NON_TECH_TITLE = re.compile(
    r"design|grafik|graphic|marketing|social media|content|redaktion|editor|sales|vertrieb|verkauf"
    r"|übersetz|translat|sprachprüf|analyst - investment|investment|finance|finanz|buchhalt|accounting"
    r"|controlling|\bhr\b|human resources|personal|recruit|legal|recht|jurist|einkauf|procurement"
    r"|kunden|customer success|assistenz|event|kommunikation|communication|\bpr\b|logistik"
    r"|metal|flotation|chemi|recycling|biolog|medizin|pharma|oxide|werkstoff|keramik|korrosion"
    r"|consulting|beratung",
    re.I)
MIN_DESC_HITS = 3

# Hands-on maintenance, repair, technician and building-services roles. Chip fabs post
# many of these; they aren't jobs for CS/AI students (Otto, 2026-10-29). Engineering
# work (design, automation, test, firmware, process/yield analysis) stays in. A title
# that also names software/data/AI work keeps the job. "Predictive maintenance" /
# "vorausschauende Wartung" is a data/ML topic, not hands-on work, so it stays in.
HANDS_ON_TITLE = re.compile(
    r"instandhalt|(?<!vorausschauende )wartung|reparatur|\brepair|(?<!predictive )maintenance|servicetechni|mechatroniker|\btechniker|technician"
    r"|kalibrier|calibration|facility|gebäude(technik|management)|technische ausrüstung|\btga\b",
    re.I)

# Phrases that look techy but aren't (removed before matching).
# Phrases that contain tech words but say nothing about the role ("Adobe Creative Cloud",
# "Software-Tools wie PowerPoint").
NOISE = re.compile(r"business develop\w*|sales develop\w*|personalentwickl\w*|organisationsentwickl\w*"
                   r"|creative cloud|software[- ]?tools?\b", re.I)

FIELD_LABELS = {
    "ai": "AI / ML",
    "data": "Data",
    "software": "Software",
    "hardware": "Embedded / Hardware",
    "other": "Other CS",
}

# ------------------------------------------------------------------ language --
EN_WORDS = re.compile(r"\b(the|and|you|your|we|our|with|for|of|to|are|will|is|in|on|as|this|team)\b", re.I)
DE_WORDS = re.compile(r"\b(und|der|die|das|wir|sie|du|dich|mit|für|ist|ein|eine|zu|bei|auf|von|deine?|unser)\b", re.I)
EN_REQUIRED = re.compile(
    r"(working|work|team|company|office) language[^.]{0,30}english|arbeitssprache[^.]{0,30}englisch"
    r"|english[- ]speaking|no german (is )?(required|needed)|german (is )?not required"
    r"|deutschkenntnisse (sind )?nicht (erforderlich|notwendig)|english only", re.I)
EN_TITLE = re.compile(r"working student|intern(ship)?\b|thes[ie]s|engineer|developer|scientist|research", re.I)
DE_TITLE = re.compile(r"werkstudent|praktik|arbeit\b|entwickl|informatik|studentische|m/w/d|w/m/d", re.I)

SNIPPET_LEN = 700


def _types(text: str) -> list[str]:
    found = []
    for name, pat in TYPE_PATTERNS.items():
        m = pat.search(text)
        if m:
            found.append((m.start(), name))
    return [name for _, name in sorted(found)]


def _fields(text: str) -> set[str]:
    text = NOISE.sub(" ", text)
    found = {name for name, pat in FIELD_PATTERNS.items() if pat.search(text)}
    if IT_WORD.search(text):
        found.add("other")
    if BI_WORD.search(text):
        found.add("data")
    return found


def _field_hits(text: str) -> int:
    """Number of distinct tech keywords in free text (used for weaker evidence)."""
    text = NOISE.sub(" ", text)
    hits = set()
    for pat in FIELD_PATTERNS.values():
        hits.update(m.group(0).lower() for m in pat.finditer(text))
    return len(hits)


def is_english(title: str, description: str) -> bool:
    if EN_REQUIRED.search(description):
        return True
    if len(description) >= 200:
        en, de = len(EN_WORDS.findall(description)), len(DE_WORDS.findall(description))
        return en >= 8 and en > de * 1.5
    # Little text: judge by the title alone.
    return bool(EN_TITLE.search(title)) and not DE_TITLE.search(title)


def snippet(job: Job) -> str:
    text = job.description or job.tags
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= SNIPPET_LEN:
        return text
    cut = text[:SNIPPET_LEN].rsplit(" ", 1)[0]
    return cut.rstrip(" ,.;:-") + "…"


def is_student_title(title: str) -> bool:
    """Cheap pre-check: is this title worth fetching details for?

    Company career feeds list every role; sources use this to request the
    full posting only for likely student jobs. classify() still decides.
    """
    return bool(_types(title)) and not EXCLUDE.search(title)


def classify(job: Job) -> dict | None:
    strong = f"{job.title} {job.tags}"  # title + reliable short context

    if EXCLUDE.search(job.title):
        return None

    # Type: from title or source category; description only as a fallback for
    # werkstudent/internship, never thesis (descriptions often mention theses in passing).
    types = _types(strong)
    if not types:
        desc_types = [t for t in _types(job.description[:600]) if t != "thesis"]
        types = desc_types[:1]
    if not types:
        return None

    # Field: title/tags are enough. Free text alone needs several distinct tech
    # terms, and can't rescue a title that is clearly a non-tech role.
    fields = _fields(strong)
    if (not fields and not NON_TECH_TITLE.search(job.title)
            and _field_hits(job.description) >= MIN_DESC_HITS):
        fields = _fields(job.description)
    if not fields:
        return None
    if HANDS_ON_TITLE.search(job.title) and not (_fields(job.title) & {"ai", "data", "software"}):
        return None

    order = list(FIELD_LABELS)
    return {
        "type": types[0],
        "types": types,
        "fields": sorted(fields, key=order.index),
        "englishFriendly": is_english(job.title, job.description),
        "snippet": snippet(job),
    }
