"""Parsing of the YouTube title and description of a concert video."""

import re

from tinydesk.config import Config

_QUOTES = "\"'“”‘’«»"  # noqa: RUF001 - typographic quotes are the point


def parse_artist(title: str, config: Config) -> str | None:
    """'Marina Sena : Tiny Desk Brasil' -> 'Marina Sena', using the configured title pattern."""
    match = re.search(config.title_pattern, title.strip(), re.IGNORECASE)
    artist = match["artist"].strip() if match else ""
    return artist or None


def _header(config: Config) -> re.Pattern[str]:
    words = "|".join(r"\s*".join(map(re.escape, word.split())) for word in config.setlist_headers)
    return re.compile(rf"^[\s*#_-]*(?:{words})\s*:?[\s*#_-]*$", re.IGNORECASE)


def parse_setlist(description: str, config: Config) -> list[str]:
    """Song titles listed under a setlist header line, one per line, up to the next blank line.

    Lines ending in a full stop are credits sentences, not titles; quotes around a title are dropped.
    """
    header = _header(config)
    lines = description.splitlines()
    for i, line in enumerate(lines):
        if header.match(line):
            titles: list[str] = []
            for entry in lines[i + 1 :]:
                entry = " ".join(entry.split()).strip(_QUOTES + " ")
                if not entry:
                    if titles:
                        break
                    continue
                if not entry.endswith("."):
                    titles.append(entry)
            return titles
    return []
