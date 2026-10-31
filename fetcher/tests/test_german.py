"""German level, only as stated (fetcher/terms.py extract_german)."""
import pytest

from fetcher.terms import extract_german


@pytest.mark.parametrize("text, level", [
    ("Sehr gute Deutsch- und Englischkenntnisse runden dein Profil ab.", "fluent"),
    ("Du sprichst fließend Deutsch und Englisch.", "fluent"),
    ("Deutschkenntnisse auf C1-Niveau", "fluent"),
    ("verhandlungssichere Deutschkenntnisse", "fluent"),
    ("Fluent German and English are required.", "fluent"),
    ("German (C1) and English", "fluent"),
    ("Gute Deutschkenntnisse (mind. B2)", "basic"),
    ("Deutsch auf Niveau B2", "basic"),
    ("Good German skills are a plus.", "basic"),
    ("Grundlegende Deutschkenntnisse", "basic"),
    ("No German required – our working language is English.", "none"),
    ("Deutschkenntnisse sind nicht erforderlich.", "none"),
    ("Our team language is English.", "none"),
    ("Du arbeitest mit Python und SQL.", None),
    ("We are a German company in Dresden.", None),
    ("Sehr gute Englischkenntnisse", None),
])
def test_german_level(text, level):
    assert extract_german("", text) == level
