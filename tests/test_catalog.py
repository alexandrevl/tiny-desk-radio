import pytest

from tinydesk.catalog import is_concert_title, source_url
from tinydesk.config import Config

CONFIG = Config()


@pytest.mark.parametrize(
    "title",
    ["Marina Sena : Tiny Desk Brasil", "Marina Sena: Tiny Desk Brazil", "Don L : TINY DESK BRASIL"],
)
def test_concerts(title):
    assert is_concert_title(title, CONFIG)


@pytest.mark.parametrize(
    "title",
    [
        "Premiere : Tiny Desk Brasil",
        "Marina Sena : Tiny Talks Brasil",
        "AC TinyTalks MateusFazenoRock V02 Youtube",
        "Tiny Remix: Kathleen and Marcio Costta watch Giovani Cidreira",
        "Tiny Encore : Sandra Sá & Tássia Reis",
    ],
)
def test_not_concerts(title):
    assert not is_concert_title(title, CONFIG)


def test_other_sources_need_their_own_include_pattern():
    npr = Config(include=r"tiny desk", exclude=r"contest")
    assert is_concert_title("Tyler Childers: Tiny Desk Concert", npr)
    assert not is_concert_title("Tiny Desk Contest Winners", npr)
    assert not is_concert_title("Tyler Childers: Tiny Desk Concert", CONFIG)


def test_channel_root_points_at_the_videos_tab():
    assert source_url("https://www.youtube.com/@nprmusic") == "https://www.youtube.com/@nprmusic/videos"
    assert source_url("https://www.youtube.com/channel/UCabc/") == "https://www.youtube.com/channel/UCabc/videos"
    assert source_url("https://www.youtube.com/@nprmusic/videos") == "https://www.youtube.com/@nprmusic/videos"
    assert source_url("https://www.youtube.com/playlist?list=PL123") == "https://www.youtube.com/playlist?list=PL123"
