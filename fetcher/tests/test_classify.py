import pytest

from fetcher.classify import SNIPPET_LEN, classify, is_english, is_student_title
from fetcher.models import Job


def job(title, tags="", description=""):
    return Job(source="Test", source_id="1", title=title, company="ACME", url="https://x",
               tags=tags, description=description)


@pytest.mark.parametrize("title, expected_type, expected_field", [
    ("Werkstudent Softwareentwicklung (m/w/d)", "werkstudent", "software"),
    ("Working Student – Data Scientist (m/f/d)", "werkstudent", "data"),
    ("Werkstudent AI Engineer (m/w/d)", "werkstudent", "ai"),
    ("Praktikum Machine Learning im Bereich Computer Vision", "internship", "ai"),
    ("Pflichtpraktikum Informatik (Webprogrammierung)", "internship", "software"),
    ("Masterarbeit: Embedded Linux auf FPGA", "thesis", "hardware"),
    ("Bachelorarbeit Cyber Security", "thesis", "other"),
    ("Werkstudent*in IT Support (m/w/d)", "werkstudent", "other"),
    ("Working Student Frontend Developer (f/m/d)", "werkstudent", "software"),
    ("Werkstudent Frontend-Entwicklung", "werkstudent", "software"),
])
def test_keeps_student_tech_jobs(title, expected_type, expected_field):
    tags = classify(job(title))
    assert tags is not None
    assert tags["type"] == expected_type
    assert expected_field in tags["fields"]


@pytest.mark.parametrize("title", [
    "Werkstudent - Frontend Academy (w/m/div)",        # chip-fab "frontend", not web UI
    "Werkstudent Marketing (m/w/d)",                   # not tech
    "Senior Software Engineer (m/w/d)",                # not a student job
    "Software Engineer (m/w/d)",                       # no student type
    "Ausbildung Fachinformatiker Anwendungsentwicklung",  # vocational training
    "Betriebspraktikum für Schüler:innen (m/w/d)",      # school pupils
    "Doktorand Machine Learning",                      # PhD
    "Studentische Hilfskraft Softwareentwicklung",     # HiWi (excluded on purpose)
    "Werkstudent*in im Sales Development",             # 'development' but sales
])
def test_drops_other_jobs(title):
    assert classify(job(title)) is None


def test_type_from_source_category_tags():
    tags = classify(job("Deep learning for plasma diagnostics", tags="Master theses / Compulsory internship"))
    assert tags["types"] == ["thesis", "internship"]
    assert tags["fields"] == ["ai"]


def test_description_needs_several_terms():
    one_term = "Wir nutzen Software für unsere Kunden."
    assert classify(job("Werkstudent (m/w/d)", description=one_term)) is None
    many = "Python, SQL und Machine Learning für Datenanalysen mit Cloud-Infrastruktur."
    assert classify(job("Werkstudent (m/w/d)", description=many)) is not None


def test_description_cannot_rescue_non_tech_title():
    text = "AI tools, Python scripts, cloud software and machine learning are part of our stack."
    assert classify(job("Werkstudent Social Media und Content", description=text)) is None


def test_bi_and_it_are_case_sensitive():
    assert classify(job("Masterarbeit: Co-Bi catalyst recovery")) is None
    assert "data" in classify(job("Werkstudent BI Reporting"))["fields"]


@pytest.mark.parametrize("title, description, expected", [
    ("Working Student Data Engineer", "", True),
    ("Werkstudent Softwareentwicklung (m/w/d)", "", False),
    ("Werkstudent", "Die Arbeitssprache im Team ist Englisch.", True),
    ("Werkstudent", "Wir sind ein Team und suchen dich für die Entwicklung von Software " * 6, False),
    ("Intern", "You will join our team and work with the latest tools in the cloud. " * 4, True),
])
def test_english_detection(title, description, expected):
    assert is_english(title, description) is expected


def test_snippet_is_trimmed():
    tags = classify(job("Werkstudent Software", description="word " * 200))
    assert len(tags["snippet"]) <= SNIPPET_LEN + 1
    assert tags["snippet"].endswith("…")


def test_is_student_title():
    assert is_student_title("Werkstudent*in im Bereich TCAD")
    assert is_student_title("Internship - Data and Workflows for AI")
    assert not is_student_title("Senior Staff Engineer Digital IP")
    assert not is_student_title("Ausbildung Mechatroniker (w/m/d) 2027")


def test_office_and_design_tools_are_not_tech_evidence():
    desc = ("Du bearbeitest Foto- und Videomaterial mit Software-Tools wie PowerPoint, Adobe Creative Cloud "
            "und Camtasia. Du studierst Mediendesign, Psychologie, (Wirtschafts-)Informatik oder Ähnliches.")
    assert classify(job("Werkstudent - Frontend Academy (w/m/div)", description=desc)) is None

