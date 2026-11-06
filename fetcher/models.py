"""Data shape shared by every source."""
from __future__ import annotations

from dataclasses import dataclass, field

# The cities the board covers: key -> name as job sites spell it. Dresden is the default.
CITIES = {"dresden": "Dresden", "leipzig": "Leipzig", "chemnitz": "Chemnitz", "berlin": "Berlin"}


@dataclass
class Job:
    """A raw posting as a source returns it, before classification."""

    source: str
    source_id: str
    title: str
    company: str
    url: str
    location: str = "Dresden"
    # The board's city, a key of CITIES. Empty for remote-only postings.
    city: str = "dresden"
    # Every board city the posting names, when it names several ("Leipzig, Berlin"); empty = just `city`.
    cities: list[str] = field(default_factory=list)
    remote: bool = False
    posted_at: str | None = None  # YYYY-MM-DD
    deadline: str | None = None  # YYYY-MM-DD
    # Short, reliable context (job category, occupation names). Treated like the title.
    tags: str = ""
    # Longer free text. Used for tagging with stricter rules.
    description: str = ""
