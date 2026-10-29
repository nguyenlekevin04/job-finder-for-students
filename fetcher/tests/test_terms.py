import json

import pytest

from fetcher.sources import fraunhofer, globalfoundries, infineon
from fetcher.terms import extract_hours, extract_pay, extract_terms, parse_amount

W = "Werkstudent Softwareentwicklung (m/w/d)"


@pytest.mark.parametrize("title,desc,expected", [
    # stated hours
    (W, "Arbeitszeit: 20 Std./Woche, flexibel einteilbar.", (20, 20)),
    (W, "Du arbeitest max. 20 Stunden pro Woche neben dem Studium.", (None, 20)),
    ("Working Student Data Science", "Workload: 15–20 h/week, remote possible.", (15, 20)),
    (W, "Eine Tätigkeit von bis zu 20 Wochenstunden ist möglich.", (None, 20)),
    ("Werkstudent IT-Support (20h)", "", (20, 20)),
    (W, "Wir bieten eine Stelle in Teilzeit (20 Stunden).", (20, 20)),
    ("Working Student ML", "You will work 16 hours a week in our Dresden office.", (16, 16)),
    ("Working Student ML", "Part-time (12 hours), flexible schedule.", (12, 12)),
    (W, "Die wöchentliche Arbeitszeit beträgt 18 Stunden.", (18, 18)),
    (W, "Mindestens 10 Stunden pro Woche, gern mehr.", (10, None)),
    (W, "Du arbeitest zwischen 10 und 20 Stunden pro Woche.", (10, 20)),
    ("Working Student Software", "at least 12 hours per week during the semester", (12, None)),
    (W, "Wir bieten eine 20-Stunden-Woche mit Gleitzeit.", (20, 20)),
    # GlobalFoundries wording: lecture-period hours win over semester-break hours
    (W, "Arbeitszeit 15-20 Stunden während der Vorlesungszeit, max. 40 Stunden in den Semesterferien", (15, 20)),
    (W, "Während des Semesters 20 h/Woche, in den Semesterferien bis zu 40 h/Woche.", (20, 20)),
    # Infineon boilerplate cap plus a specific value under it: the specific one wins
    (W, "maximal mit 20 Stunden pro Woche möglich. Wir suchen dich für 16 Stunden pro Woche.", (16, 16)),
    # not stated / not weekly / implausible
    (W, "Flexible Arbeitszeiten (ab 25 h / Monat) mit attraktiver Vergütung", (None, None)),
    (W, "Unser Team aus 20 Mitarbeitern seit 2015 in Dresden.", (None, None)),
    ("Sales Director", "You are expected to work from that office 3 days per week.", (None, None)),
    ("Working Student", "Compensation as a student research assistant (working hours to be agreed)", (None, None)),
    ("Working Student", "Working hours: 8 hours per day on site.", (None, None)),
    ("Praktikum Chemie", "Praktikumsdauer mind. 4 Wochen, mit möglichst täglicher Anwesenheit", (None, None)),
    (W, "Vollzeit mit 45 Stunden pro Woche.", (None, None)),
    (W, "20 Std./Woche oder 30 Std./Woche nach Absprache", (None, None)),  # conflicting values
    ("Werkstudent 24h-Service", "Kundenservice rund um die Uhr", (None, None)),
])
def test_hours(title, desc, expected):
    assert extract_hours(title, "", desc) == expected


@pytest.mark.parametrize("desc,expected", [
    ("Vergütung: 15,50 €/Std.", (15.5, "hour")),
    ("We pay €15 per hour.", (15.0, "hour")),
    ("Praktikumsvergütung 1.200 € brutto/Monat", (1200.0, "month")),
    ("Stundenlohn: 14 Euro", (14.0, "hour")),
    ("monthly stipend of EUR 1,500", (1500.0, "month")),
    ("Wir zahlen 16 € pro Stunde.", (16.0, "hour")),
    ("Vergütung: 1.800 EUR monatlich", (1800.0, "month")),
    ("Stundenlohn 15 € (ca. 1.300 € im Monat bei 20 h)", (15.0, "hour")),  # hour beats month
    # not stated or not the pay
    ("Bezahlung nach Mindestlohn", (None, None)),
    ("Vergütung über dem Mindestlohn von 12,82 €/Stunde", (None, None)),
    ("Klassischer 520-Euro-Job / Minijob", (None, None)),
    ("Attraktive Vergütung und flexible Arbeitszeiten", (None, None)),
    ("Vergütung: 1.200 €", (None, None)),  # no unit
    ("14-16 €/h je nach Erfahrung", (None, None)),  # a range isn't one stated amount
    ("Deutschlandticket-Zuschuss von 49 €/Monat", (None, None)),
    ("Fahrtkostenzuschuss bis zu 250 €/Monat", (None, None)),
    ("$25 per hour", (None, None)),
    ("CHF 30 pro Stunde", (None, None)),
    ("Jahresgehalt 55.000 € pro Jahr", (None, None)),
    ("Vergütung: 5.500 €/Monat", (None, None)),  # outside the student range
    ("Bis zu 18 €/Std.", (None, None)),  # a cap, not the pay
    ("We raised >€10m in funding in the first 2 years", (None, None)),
    ("Payment includes the standard expense allowance", (None, None)),
    ("15 €/h oder 17 €/h für Masterstudierende", (None, None)),  # conflicting
])
def test_pay(desc, expected):
    assert extract_pay("Werkstudent Data (m/w/d)", "", desc) == expected


@pytest.mark.parametrize("raw,value", [
    ("15,50", 15.5), ("15.50", 15.5), ("1.200", 1200.0), ("1,200", 1200.0),
    ("1.200,50", 1200.5), ("1,200.50", 1200.5), ("15,-", 15.0), ("2000", 2000.0),
])
def test_parse_amount(raw, value):
    assert parse_amount(raw) == value


def test_extract_terms_shape():
    assert extract_terms("Werkstudent (m/w/d)", "", "") == {
        "hoursMin": None, "hoursMax": None, "payAmount": None, "payUnit": None}
    assert extract_terms(W, "", "15-20 h/Woche, 15 €/h") == {
        "hoursMin": 15, "hoursMax": 20, "payAmount": 15.0, "payUnit": "hour"}


def test_fixture_postings(fixture_text):
    gf, _ = globalfoundries.parse_detail(json.loads(fixture_text("globalfoundries_detail.json")))
    assert extract_hours("", "", gf) == (15, 20)
    ifx = infineon.parse_detail(json.loads(fixture_text("infineon_detail.json")))
    assert extract_hours("", "", ifx) == (None, 20)
    fh, _ = fraunhofer.parse_detail(fixture_text("fraunhofer_detail.html"))
    assert extract_terms("", "", fh) == {"hoursMin": None, "hoursMax": None, "payAmount": None, "payUnit": None}
