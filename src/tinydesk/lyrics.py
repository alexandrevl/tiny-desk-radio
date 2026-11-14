"""Matching setlist titles to detected songs by what is sung: a song's title is usually in its own lyrics.

Descriptions do not always list the songs in the order they were played, so titles are assigned to
tracks by lyric evidence, keeping the setlist order wherever the evidence does not say otherwise.
"""

import re
import unicodedata
from dataclasses import dataclass
from itertools import permutations

from tinydesk.segmentation import Span

_MIN_TITLE_CHARS = 5


@dataclass(frozen=True)
class Phrase:
    """A stretch of transcribed audio."""

    start: float
    end: float
    text: str


def normalize(text: str) -> str:
    plain = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return " ".join(re.findall(r"[a-z0-9]+", plain.lower()))


def order_by_lyrics(titles: list[str], spans: list[Span], phrases: list[Phrase]) -> tuple[list[str], list[str]]:
    """The titles arranged so that as many as possible are sung inside the track they are assigned to.

    Among arrangements that fit the lyrics equally well, the one closest to the setlist order wins,
    so titles that are never heard (or too short to search for) stay where the setlist puts them.
    Also returns the titles that had to move to another track without being heard there.
    """
    heard = [(normalize(p.text), (p.start + p.end) / 2) for p in phrases]
    wanted = [normalize(title) for title in titles]
    sung = [
        [
            len(want) >= _MIN_TITLE_CHARS
            and any(span.start <= moment <= span.end and want in text for text, moment in heard)
            for want in wanted
        ]
        for span in spans
    ]

    def fit(order: tuple[int, ...]) -> tuple[int, int]:
        matches = sum(sung[track][title] for track, title in enumerate(order))
        return matches, -sum(track != title for track, title in enumerate(order))

    best = max(permutations(range(len(titles))), key=fit)
    unverified = [titles[title] for track, title in enumerate(best) if title != track and not sung[track][title]]
    return [titles[i] for i in best], unverified
