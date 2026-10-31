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
    # Engineering roles at chip fabs stay (real titles from 2026-10-29):
    ("Werkstudent/Praktikum - 3D-Druck und Microcontroller-Programmierung (w/m/div)", "werkstudent", "software"),
    ("Werkstudent Software für die Instandhaltungsplanung", "werkstudent", "software"),
    ("Werkstudent IT Consulting & Cloud Integration - SAP CI Umfeld", "werkstudent", "software"),
])
def test_keeps_student_tech_jobs(title, expected_type, expected_field):
    tags = classify(job(title))
    assert tags is not None
    assert tags["type"] == expected_type
    assert expected_field in tags["fields"]


@pytest.mark.parametrize("title", [
    "Werkstudent - Frontend Academy (w/m/div)",        # chip-fab "frontend", not web UI
    # Hands-on maintenance / repair / technician roles (real titles from 2026-10-29):
    "Praktikum Entwicklung eines TPM-Standards für die Instandhaltung im Halbleiterwerk",
    "Werkstudent*in im Bereich Global Repair Shop",
    "Werkstudent (m/w/d) im Kalibrierlabor",
    "Werkstudent Technische Ausrüstung - Elektro-/Energietechnik (m/w/d)",
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


def test_consulting_title_cannot_be_rescued_by_description():
    desc = "Python machine learning data analysis cloud software for climate risk models."
    assert classify(job("Working Student in Consulting | Climate Risk and Decarbonisation", description=desc)) is None


@pytest.mark.parametrize("title, description", [
    ("Werkstudent*in im Bereich Tape-Out Engineering",
     "Du unterstützt beim Chip-Design und automatisierst Abläufe mit Python-Skripten und Datenbanken."),
    ("Working Student - Digital Functional Verification (f/m/div)",
     "Verification of semiconductor IP: write testbenches, automate regressions in Python on Linux, analyse coverage."),
    ("Masterarbeit Predictive Maintenance",
     "Du entwickelst Machine-Learning-Modelle in Python zur Datenanalyse von Sensordaten und baust Software-Pipelines."),
    ("Werkstudent vorausschauende Wartung",
     "Du entwickelst Machine-Learning-Modelle in Python zur Datenanalyse von Sensordaten und baust Software-Pipelines."),
    ("Masterarbeit zur vorausschauenden Wartung",
     "Du entwickelst Machine-Learning-Modelle in Python zur Datenanalyse von Sensordaten und baust Software-Pipelines."),
    ("Masterarbeit Predictive-Maintenance",
     "Du entwickelst Machine-Learning-Modelle in Python zur Datenanalyse von Sensordaten und baust Software-Pipelines."),
])
def test_chip_fab_engineering_roles_stay(title, description):
    assert classify(job(title, description=description)) is not None



# --- Lena's false hits (2026-10-31): none of these may be tagged AI/ML ---

def not_ai(result):
    return result is None or "ai" not in result["fields"]


def test_climate_consulting_with_ai_category_tag_is_dropped():
    r = classify(job("Germany | Working Student in Consulting | Climate Risk and Decarbonisation",
                     tags="AI Software Development", description="Python and AI for climate models."))
    assert r is None


def test_one_passing_ai_mention_does_not_make_a_job_ai():
    desc = ("You verify digital chip designs with SystemVerilog and Python scripts, automate regression "
            "tests in Linux and work with the hardware team. We also explore AI in our tool chain.")
    r = classify(job("Working Student - Digital Functional Verification (f/m/div)", description=desc))
    assert r is not None and not_ai(r) and "hardware" in r["fields"]


def test_backoffice_operations_is_dropped():
    desc = "Du pflegst Daten im CRM, nutzt Software-Tools, Python-Skripte, SQL und KI-Assistenten."
    assert classify(job("Werkstudent Backoffice Operations (m/w/d) - deutschlandweit im Homeoffice",
                        description=desc)) is None


@pytest.mark.parametrize("title", [
    "Werkstudent (m/w/d) im Kalibrierlabor",
    "Werkstudent Elektrotechnik (m/w/d)",
    "Praktikant/Werkstudent Elektrotechnik",
])
def test_lab_and_electrical_roles_are_never_ai(title):
    assert not_ai(classify(job(title, description="Messtechnik, Elektronik, Prüfstände und KI.")))


@pytest.mark.parametrize("title", [
    "Studentische Hilfskraft mit anschließender Abschlussarbeit - Infrastrukturgestützte Lokalisierung",
    "Wissenschaftliche Hilfskraft (m/w/d) Machine Learning",
    "HiWi Masterarbeit Computer Vision",
])
def test_hiwi_posts_are_dropped_even_with_a_thesis(title):
    assert classify(job(title)) is None


def test_two_ai_terms_in_the_description_still_count():
    desc = "Du trainierst neuronale Netze mit PyTorch und evaluierst Large Language Models in Python."
    r = classify(job("Werkstudent (m/w/d) Forschung", description=desc))
    assert r is not None and "ai" in r["fields"]


def test_snippet_skips_the_company_intro():
    intro = "Who we are: True North Partners is a consultancy with offices in Amsterdam, Dubai and London. " * 3
    role = "Your tasks: You analyse climate risk data with Python and build dashboards for clients. " * 4
    s = classify(job("Working Student Data Analytics", description=intro + role))["snippet"]
    assert s.startswith("Your tasks")


def test_snippet_keeps_postings_without_a_role_heading():
    text = "Wir suchen eine*n Werkstudent*in für Softwareentwicklung in Python und Java. " * 5
    assert classify(job("Werkstudent Softwareentwicklung", description=text))["snippet"].startswith("Wir suchen")


def test_snippet_ignores_task_words_inside_a_sentence():
    text = "Bei uns warten spannende Aufgaben in der Softwareentwicklung mit Python und Java auf dich. " * 4
    assert classify(job("Werkstudent Softwareentwicklung", description=text))["snippet"].startswith("Bei uns")
