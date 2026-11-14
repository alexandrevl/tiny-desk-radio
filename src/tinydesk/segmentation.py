"""Locating the songs of a concert recording, leaving out applause and stage talk.

Each 0.25 s step of the recording gets a score in [-1, 1] (positive = music) averaged from four
independent cues: low-frequency energy, loudness, tonality and YAMNet's 'Music' probability.
Applause and talk drop all four; no single cue is enough (rap lowers YAMNet's, noisy guitars lower
tonality, quiet intros lower the energy ones). The setlist says how many songs to expect, so the
songs are the N disjoint stretches with the highest total score; their edges are then widened
through adjacent stretches YAMNet still hears as music.
"""

import subprocess
from dataclasses import dataclass
from itertools import pairwise
from pathlib import Path

import numpy as np

from tinydesk import yamnet

SAMPLE_RATE = yamnet.SAMPLE_RATE
_FRAME = 4096
_HOP = 4000
STEP_S = _HOP / SAMPLE_RATE
_FRAME_CENTRE_S = _FRAME / 2 / SAMPLE_RATE
_SMOOTH_STEPS = 9
_MUSIC_SMOOTH_STEPS = 13
_MIN_SONG_S = 60.0
_MAX_GROWTH_S = 15.0
MIN_TRACK_S = 90.0
MAX_TRACK_S = 600.0
MIN_BREAK_S = 3.0


@dataclass(frozen=True)
class Span:
    start: float
    end: float

    @property
    def duration(self) -> float:
        return self.end - self.start


@dataclass(frozen=True)
class Detection:
    """`spans` holds one song per setlist entry; `detected` counts those a real break (applause, talk) tells apart."""

    spans: list[Span]
    detected: int


@dataclass(frozen=True)
class Evidence:
    """What the recording says about each step: music score, 'YAMNet hears music', and raw loudness."""

    score: np.ndarray
    music: np.ndarray
    level_db: np.ndarray


def decode(path: Path) -> np.ndarray:
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(SAMPLE_RATE), "-f", "f32le", "-"],
        capture_output=True,
        check=True,
    ).stdout
    return np.frombuffer(raw, dtype=np.float32)


def gather_evidence(samples: np.ndarray, model: Path) -> Evidence:
    count = (len(samples) - _FRAME) // _HOP + 1
    window = np.hanning(_FRAME)
    freqs = np.fft.rfftfreq(_FRAME, 1 / SAMPLE_RATE)
    tonal_band = (freqs > 200) & (freqs < 4000)
    bass_band = (freqs >= 40) & (freqs < 250)
    tonality, bass, level = (np.empty(count) for _ in range(3))
    for first in range(0, count, 1000):
        rows = np.arange(first, min(first + 1000, count))
        chunk = samples[rows[:, None] * _HOP + np.arange(_FRAME)[None, :]]
        power = np.abs(np.fft.rfft(chunk * window, axis=1)) ** 2 + 1e-12
        band = power[:, tonal_band]
        tonality[rows] = 10 * np.log10(np.exp(np.log(band).mean(axis=1)) / band.mean(axis=1))
        bass[rows] = 10 * np.log10(power[:, bass_band].sum(axis=1))
        level[rows] = 10 * np.log10((chunk**2).mean(axis=1) + 1e-12)

    probability, centres = yamnet.music_probability(samples, model)
    steps = np.arange(count) * STEP_S + _FRAME_CENTRE_S
    probability = np.interp(steps, centres, probability)

    bass, level, tonality = (_median(values, _SMOOTH_STEPS) for values in (bass, level, tonality))
    cues = [
        (bass - (np.percentile(bass, 80) - 8)) / 6,
        (level - (np.percentile(level, 80) - 10)) / 5,
        (-12 - tonality) / 4,
        (probability - 0.5) * 2,
    ]
    score = np.clip(cues, -1, 1).mean(axis=0)
    music = _median((probability > 0.5).astype(float), _MUSIC_SMOOTH_STEPS) > 0.5  # ignore dips of a second or so
    return Evidence(score, music, level)


def _median(values: np.ndarray, size: int) -> np.ndarray:
    padded = np.pad(values, size // 2, mode="edge")
    return np.median(np.lib.stride_tricks.sliding_window_view(padded, size), axis=1)


def _best_stretches(score: np.ndarray, count: int, min_steps: int) -> list[tuple[int, int]]:
    """`count` disjoint stretches of at least `min_steps` steps with the highest total score, in order."""
    total = np.concatenate(([0.0], np.cumsum(score)))  # total[t] = sum of score[:t]
    steps = len(total)
    best = np.zeros((count + 1, steps))  # best[k][t]: k stretches inside the first t steps
    last_end = np.zeros((count + 1, steps), dtype=int)  # where the k-th stretch of best[k][t] ends
    first_start = np.zeros((count + 1, steps), dtype=int)  # start of the k-th stretch if it ends at t
    index = np.arange(steps)
    for k in range(1, count + 1):
        before = best[k - 1] - total
        running = np.maximum.accumulate(before)
        first_start[k - 1] = np.maximum.accumulate(np.where(before >= running, index, 0))
        ending_at = np.full(steps, -np.inf)
        ending_at[min_steps:] = running[: steps - min_steps] + total[min_steps:]
        best[k] = np.maximum.accumulate(ending_at)
        last_end[k] = np.maximum.accumulate(np.where(ending_at >= best[k], index, 0))
    stretches = []
    t = steps - 1
    for k in range(count, 0, -1):
        end = last_end[k][t]
        start = first_start[k - 1][end - min_steps]
        stretches.append((int(start), int(end)))
        t = start
    return stretches[::-1]


def _widen(stretches: list[tuple[int, int]], evidence: Evidence) -> list[tuple[int, int]]:
    """Extend the edges between songs through steps YAMNet hears as music.

    Where two songs meet, cut at the quietest step.
    """
    music, limit = evidence.music, int(_MAX_GROWTH_S / STEP_S)
    widened = [list(s) for s in stretches]
    for left, right in pairwise(widened):
        end = left[1]
        while end < min(left[1] + limit, right[0]) and music[end]:
            end += 1
        start = right[0]
        while start > max(right[0] - limit, left[1]) and music[start - 1]:
            start -= 1
        if end >= start:
            end = start = left[1] + int(np.argmin(evidence.level_db[left[1] : right[0] + 1]))
        left[1], right[0] = end, start
    return [(s, e) for s, e in widened]


def locate_songs(evidence: Evidence, count: int) -> Detection:
    stretches = _best_stretches(evidence.score, count, int(_MIN_SONG_S / STEP_S))
    breaks = sum((right[0] - left[1]) * STEP_S >= MIN_BREAK_S for left, right in pairwise(stretches))
    spans = [Span(round(s * STEP_S, 2), round(e * STEP_S, 2)) for s, e in _widen(stretches, evidence)]
    return Detection(spans, detected=1 + breaks)


def problems(detection: Detection, titles: list[str]) -> list[str]:
    """Reasons the detected songs cannot be trusted as the setlist's songs; empty when they can."""
    found = []
    if detection.detected != len(titles):
        found.append(
            f"setlist has {len(titles)} songs, but only {detection.detected} are separated by applause or talk"
        )
    for number, span in enumerate(detection.spans, start=1):
        if not MIN_TRACK_S <= span.duration <= MAX_TRACK_S:
            found.append(f"track {number} lasts {span.duration:.0f}s")
    return found
