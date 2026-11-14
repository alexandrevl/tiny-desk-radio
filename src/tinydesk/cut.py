"""Cutting songs out of the episode audio without re-encoding."""

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

_UNSAFE = re.compile(r'[/\\:*?"<>|\x00-\x1f]')


@dataclass(frozen=True)
class Track:
    title: str
    start: float
    end: float


def safe_name(text: str) -> str:
    return _UNSAFE.sub("-", text).strip(" .") or "untitled"


def track_path(library: Path, artist: str, number: int, title: str) -> Path:
    return library / safe_name(artist) / f"{number:02d} - {safe_name(title)}.m4a"


def cut(source: Path, start: float, end: float, destination: Path) -> None:
    """Copy the AAC frames between `start` and `end` seconds into a new M4A."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-ss",
            f"{start:.3f}",
            "-to",
            f"{end:.3f}",
            "-i",
            str(source),
            "-vn",
            "-c",
            "copy",
            "-map_metadata",
            "-1",
            str(destination),
        ],
        check=True,
    )
