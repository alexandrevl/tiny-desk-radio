"""From a YouTube video id to tagged per-song files in the library, and from there into Music."""

import json
import shutil
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

from tinydesk import catalog, segmentation, state, tagging, yamnet
from tinydesk.config import Config
from tinydesk.cut import Track, cut, track_path
from tinydesk.lyrics import Phrase, order_by_lyrics
from tinydesk.setlist import parse_artist, parse_setlist


class UserError(Exception):
    """A problem the user can fix; shown without a traceback."""


@dataclass(frozen=True)
class Workspace:
    """Where everything lives: `data/` under `root`, the library wherever the config says."""

    root: Path
    config: Config

    @property
    def audio(self) -> Path:
        return self.root / "data" / "audio"

    @property
    def review(self) -> Path:
        return self.root / "data" / "review"

    @property
    def transcripts(self) -> Path:
        return self.root / "data" / "transcripts"

    @property
    def models(self) -> Path:
        return self.root / "data" / "models"

    @property
    def database(self) -> Path:
        return self.root / "data" / "state.db"

    @property
    def library(self) -> Path:
        return self.root / self.config.library


@dataclass(frozen=True)
class Job:
    """Everything needed to turn one episode's audio into tagged tracks."""

    video_id: str
    title: str
    artist: str
    year: int
    thumbnail: str
    duration: float
    setlist: list[str]


def sync_episode(video_id: str, ws: Workspace, db: state.State) -> state.Row:
    """Process one episode: deliver nothing, but leave it `ok` in the library, `review`, or `skipped`."""
    _refuse_if_delivered(db, video_id)
    config = ws.config
    episode = catalog.fetch_episode(video_id, config)
    artist = parse_artist(episode.title, config)
    setlist = parse_setlist(episode.description, config)
    if not catalog.is_concert_title(episode.title, config):
        return _skip(db, episode, artist, "title does not match the include/exclude patterns")
    if artist is None:
        return _skip(db, episode, artist, "artist not found in the title (see title_pattern)")
    if not setlist:
        return _skip(db, episode, artist, "no setlist in the description")

    audio = catalog.download_audio(video_id, ws.audio, config)
    job = Job(video_id, episode.title, artist, episode.year, episode.thumbnail, episode.duration, setlist)
    samples = segmentation.decode(audio)
    if episode.chapters:
        spans = [segmentation.Span(c.start, c.end) for c in episode.chapters]
        detection = segmentation.Detection(spans, detected=len(spans))
    else:
        evidence = segmentation.gather_evidence(samples, yamnet.ensure_model(ws.models))
        detection = segmentation.locate_songs(evidence, len(setlist))
    phrases = _transcribe(ws, video_id, samples)
    found = segmentation.problems(detection, setlist)
    titles, note = setlist, None
    if len(detection.spans) == len(setlist):
        titles, unverified = order_by_lyrics(setlist, detection.spans, phrases)
        if unverified:
            found.append(
                f"lyrics suggest a different order than the setlist, but {', '.join(unverified)} could not be confirmed"
            )
        elif titles != setlist:
            note = "titles reordered to match the lyrics sung"
    tracks = [
        Track(titles[i] if i < len(titles) else "", span.start, span.end) for i, span in enumerate(detection.spans)
    ]
    if found:
        _write_review(ws, job, found, tracks, phrases)
        db.save(
            video_id,
            episode.title,
            state.REVIEW,
            artist=artist,
            reason="; ".join(found),
            setlist_count=len(setlist),
            detected_count=detection.detected,
        )
        return _existing(db, video_id)
    return _render(ws, db, job, tracks, detected=detection.detected, note=note)


def approve(video_id: str, ws: Workspace, db: state.State) -> state.Row:
    """Accept the cut proposed in the review report as it is."""
    _refuse_if_delivered(db, video_id)
    job, proposed = _read_review(ws, video_id)
    if len(proposed) != len(job.setlist) or not all(t.title for t in proposed):
        raise UserError(
            f"the proposed cut has {len(proposed)} tracks for a setlist of {len(job.setlist)}; "
            f"edit data/review/{video_id}.json and run `tinydesk apply {video_id} <file>`"
        )
    return _render(ws, db, job, proposed, detected=len(proposed))


def apply(video_id: str, times_file: Path, ws: Workspace, db: state.State) -> state.Row:
    """Cut the episode where the user says: a JSON list of {title, start, end}."""
    _refuse_if_delivered(db, video_id)
    job, _ = _read_review(ws, video_id)
    try:
        tracks = [
            Track(str(t["title"]), float(t["start"]), float(t["end"])) for t in json.loads(times_file.read_text())
        ]
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise UserError(f"{times_file} must be a JSON list of {{title, start, end}}: {error}") from error
    if not tracks:
        raise UserError(f"{times_file} has no tracks")
    previous_end = 0.0
    for t in tracks:
        if not t.title or not previous_end <= t.start < t.end <= job.duration:
            raise UserError(
                f"track {t.title!r} ({t.start}-{t.end}) is empty, out of order, or past {job.duration:.0f}s"
            )
        previous_end = t.end
    return _render(ws, db, job, tracks, detected=len(tracks))


def deliver(row: state.Row, ws: Workspace, music_dir: Path, db: state.State) -> bool:
    """Copy an `ok` episode's files into Music's auto-add folder, once. False if it was already delivered."""
    if row.delivered:
        return False
    for relative in row.files:
        source = ws.library / relative
        name = f"{Path(relative).parent.name} - {Path(relative).name}"
        partial = music_dir / f".{name}.part"  # Music must never see a half-copied file
        shutil.copy2(source, partial)
        partial.replace(music_dir / name)
    db.mark_delivered(row.video_id)
    return True


def _refuse_if_delivered(db: state.State, video_id: str) -> None:
    """Cutting an episode again would put a second copy of every song into Music."""
    row = db.get(video_id)
    if row and row.delivered:
        raise UserError(
            f"{video_id} was already delivered to Music; re-cutting it would add duplicate songs. "
            "Remove its songs from Music first, then reset it by deleting its row from data/state.db"
        )


def _render(
    ws: Workspace, db: state.State, job: Job, tracks: list[Track], detected: int, note: str | None = None
) -> state.Row:
    _refuse_if_delivered(db, job.video_id)
    previous = db.get(job.video_id)
    for relative in previous.files if previous else []:
        (ws.library / relative).unlink(missing_ok=True)
    audio = ws.audio / f"{job.video_id}.m4a"
    cover = urllib.request.urlopen(job.thumbnail).read()
    files = []
    for number, track in enumerate(tracks, start=1):
        path = track_path(ws.library, job.artist, number, track.title)
        cut(audio, track.start, track.end, path)
        tagging.tag(
            path,
            title=track.title,
            artist=job.artist,
            album=ws.config.album,
            genre=ws.config.genre,
            number=number,
            total=len(tracks),
            year=job.year,
            cover=cover,
        )
        files.append(str(path.relative_to(ws.library)))
    (ws.review / f"{job.video_id}.json").unlink(missing_ok=True)
    db.save(
        job.video_id,
        job.title,
        state.OK,
        artist=job.artist,
        reason=note,
        setlist_count=len(job.setlist),
        detected_count=detected,
        files=files,
    )
    return _existing(db, job.video_id)


def _skip(db: state.State, episode: catalog.Episode, artist: str | None, reason: str) -> state.Row:
    db.save(episode.id, episode.title, state.SKIPPED, artist=artist, reason=reason)
    return _existing(db, episode.id)


def _existing(db: state.State, video_id: str) -> state.Row:
    row = db.get(video_id)
    assert row is not None
    return row


def _transcribe(ws: Workspace, video_id: str, samples: np.ndarray) -> list[Phrase]:
    """What is sung and said in the episode, transcribed once and cached."""
    path = ws.transcripts / f"{video_id}.json"
    if not path.exists():
        from tinydesk import speech  # imports the speech model stack, only needed here

        try:
            phrases = speech.transcribe(samples, ws.config.language)
        except RuntimeError as error:
            raise UserError(str(error)) from error
        ws.transcripts.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps([asdict(p) for p in phrases], ensure_ascii=False))
    return [Phrase(**p) for p in json.loads(path.read_text())]


def _write_review(ws: Workspace, job: Job, problems: list[str], tracks: list[Track], phrases: list[Phrase]) -> None:
    """Report with the proposed cut and what is said between the proposed songs, to decide quickly."""
    edges = [0.0] + [edge for t in tracks for edge in (t.start, t.end)] + [job.duration]
    report = {
        **asdict(job),
        "problems": problems,
        "proposed": [asdict(t) for t in tracks],
        "between_songs": [
            {
                "start": a,
                "end": b,
                "transcript": " ".join(p.text for p in phrases if a <= (p.start + p.end) / 2 < b),
            }
            for a, b in zip(edges[::2], edges[1::2], strict=True)
            if b > a
        ],
    }
    ws.review.mkdir(parents=True, exist_ok=True)
    (ws.review / f"{job.video_id}.json").write_text(json.dumps(report, indent=2, ensure_ascii=False))


def _read_review(ws: Workspace, video_id: str) -> tuple[Job, list[Track]]:
    path = ws.review / f"{video_id}.json"
    if not path.exists():
        raise UserError(
            f"{video_id} has no review report ({path}); only episodes in `review` can be approved or applied"
        )
    report = json.loads(path.read_text())
    job = Job(**{key: report[key] for key in Job.__dataclass_fields__})
    return job, [Track(**t) for t in report["proposed"]]
