"""MP4 tags that make the songs sort and shuffle properly in Music."""

from pathlib import Path

from mutagen.mp4 import MP4, MP4Cover


def tag(
    path: Path,
    *,
    title: str,
    artist: str,
    album: str,
    genre: str,
    number: int,
    total: int,
    year: int,
    cover: bytes,
) -> None:
    audio = MP4(path)
    audio["\xa9nam"] = title
    audio["\xa9ART"] = artist
    audio["aART"] = artist
    audio["\xa9alb"] = album
    audio["\xa9gen"] = genre
    audio["\xa9day"] = str(year)
    audio["trkn"] = [(number, total)]
    audio["covr"] = [MP4Cover(cover, imageformat=MP4Cover.FORMAT_JPEG)]
    audio.save()
