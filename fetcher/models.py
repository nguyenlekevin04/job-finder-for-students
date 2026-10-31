"""Data shape shared by every source."""
from __future__ import annotations

from dataclasses import dataclass

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
    remote: bool = False
    posted_at: str | None = None  # YYYY-MM-DD
    deadline: str | None = None  # YYYY-MM-DD
    # Short, reliable context (job category, occupation names). Treated like the title.
    tags: str = ""
    # Longer free text. Used for tagging with stricter rules.
    description: str = ""
