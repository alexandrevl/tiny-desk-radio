"""The YouTube source (channel or playlist): which videos are concerts, and their metadata."""

import re
from dataclasses import dataclass
from pathlib import Path

from yt_dlp import YoutubeDL

from tinydesk.config import Config

_CHANNEL_ROOT = re.compile(r"^(https?://(?:www\.)?youtube\.com/(?:@[^/?]+|channel/[^/?]+|c/[^/?]+|user/[^/?]+))/?$")


@dataclass(frozen=True)
class Chapter:
    title: str
    start: float
    end: float


@dataclass(frozen=True)
class Episode:
    id: str
    title: str
    description: str
    duration: float
    year: int
    thumbnail: str
    chapters: list[Chapter]


def is_concert_title(title: str, config: Config) -> bool:
    return bool(re.search(config.include, title, re.IGNORECASE)) and not re.search(config.exclude, title, re.IGNORECASE)


def source_url(source: str) -> str:
    """A channel's root page lists tabs, not videos: point it at the Videos tab."""
    root = _CHANNEL_ROOT.match(source.strip())
    return f"{root[1]}/videos" if root else source.strip()


def list_concerts(config: Config) -> list[tuple[str, str]]:
    """(video id, title) of the concert videos in the source, as listed (newest first on channels)."""
    with YoutubeDL({"quiet": True, "extract_flat": "in_playlist"}) as ydl:
        listing = ydl.extract_info(source_url(config.source), download=False)
    return [
        (entry["id"], entry["title"])
        for entry in listing.get("entries") or []
        if entry and entry.get("title") and is_concert_title(entry["title"], config)
    ]


def fetch_episode(video_id: str) -> Episode:
    with YoutubeDL({"quiet": True, "skip_download": True}) as ydl:
        info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
    jpgs = [t for t in info["thumbnails"] if t["url"].endswith(".jpg")]
    return Episode(
        id=video_id,
        title=info["title"],
        description=info.get("description") or "",
        duration=float(info["duration"]),
        year=int(info["upload_date"][:4]),
        thumbnail=max(jpgs, key=lambda t: t.get("preference") or 0)["url"],
        chapters=[
            Chapter(c["title"], float(c["start_time"]), float(c["end_time"])) for c in info.get("chapters") or []
        ],
    )


def download_audio(video_id: str, directory: Path) -> Path:
    """Best AAC-in-M4A audio stream, cached in `directory`."""
    path = directory / f"{video_id}.m4a"
    if not path.exists():
        directory.mkdir(parents=True, exist_ok=True)
        options = {
            "quiet": True,
            "noprogress": True,
            "format": "bestaudio[ext=m4a]",
            "outtmpl": str(directory / "%(id)s.%(ext)s"),
        }
        with YoutubeDL(options) as ydl:
            ydl.download([f"https://www.youtube.com/watch?v={video_id}"])
    return path
