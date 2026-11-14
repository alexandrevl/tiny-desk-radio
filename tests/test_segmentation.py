import numpy as np

from tinydesk.segmentation import STEP_S, Detection, Evidence, Span, locate_songs, problems


def steps(seconds: float) -> int:
    return round(seconds / STEP_S)


def evidence(*parts: tuple[float, float, bool]) -> Evidence:
    """Concert made of (seconds, score, YAMNet hears music) parts."""
    score = np.concatenate([np.full(steps(s), v) for s, v, _ in parts])
    music = np.concatenate([np.full(steps(s), m) for s, _, m in parts])
    level = np.concatenate([np.full(steps(s), -20.0 if v > 0 else -50.0) for s, v, _ in parts])
    return Evidence(score, music, level)


def test_songs_are_the_stretches_between_talk():
    concert = evidence(
        (10, -1, False),
        (120, 0.8, True),
        (30, -1, False),
        (150, 0.8, True),
        (25, -1, False),
        (100, 0.8, True),
        (20, -1, False),
    )
    detection = locate_songs(concert, 3)
    assert detection.detected == 3
    assert [(round(s.start), round(s.end)) for s in detection.spans] == [(10, 130), (160, 310), (335, 435)]


def test_the_setlist_picks_which_breaks_split_songs():
    # A brief quiet dip inside the second song is not a break when the setlist has two songs...
    concert = evidence((100, 0.8, True), (20, -1, False), (80, 0.8, True), (6, -0.5, False), (80, 0.8, True))
    detection = locate_songs(concert, 2)
    assert [round(s.start) for s in detection.spans] == [0, 120]
    # ...and is the break once the setlist has three.
    assert [round(s.start) for s in locate_songs(concert, 3).spans] == [0, 120, 206]


def test_songs_that_merge_without_a_break_are_reported_as_fewer_detected():
    concert = evidence((100, 0.8, True), (1, -0.1, False), (100, 0.8, True), (20, -1, False), (100, 0.8, True))
    detection = locate_songs(concert, 3)
    assert detection.detected == 2
    assert problems(detection, ["a", "b", "c"]) == ["setlist has 3 songs, but only 2 are separated by applause or talk"]


def test_edges_widen_through_quiet_music_the_score_missed():
    # The second song opens with 10 s the score calls non-music, but YAMNet hears as music.
    concert = evidence((120, 0.8, True), (30, -0.5, False), (10, -0.5, True), (120, 0.8, True))
    first, second = locate_songs(concert, 2).spans
    assert round(second.start) == 150
    assert round(first.end) == 120


def test_suspicious_track_lengths_need_review():
    detection = Detection([Span(0, 40), Span(50, 200), Span(210, 900)], detected=3)
    assert problems(detection, ["a", "b", "c"]) == ["track 1 lasts 40s", "track 3 lasts 690s"]
