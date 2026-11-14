from pathlib import Path

import pytest

from tinydesk.config import DEFAULT_SOURCE, ConfigError, resolve


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch, tmp_path):
    for name in list(__import__("os").environ):
        if name.startswith("TINYDESK_"):
            monkeypatch.delenv(name)
    monkeypatch.chdir(tmp_path)


def test_defaults_target_tiny_desk_brasil():
    config = resolve({})
    assert config.source == DEFAULT_SOURCE
    assert config.language == "pt"
    assert config.album == "Tiny Desk Radio"


def test_flag_beats_env_beats_file_beats_default(tmp_path, monkeypatch):
    Path("tinydesk.toml").write_text('language = "es"\nalbum = "From File"\ngenre = "From File"\n')
    assert resolve({}).language == "es"
    monkeypatch.setenv("TINYDESK_LANGUAGE", "fr")
    monkeypatch.setenv("TINYDESK_ALBUM", "From Env")
    config = resolve({"language": "en"})
    assert (config.language, config.album, config.genre) == ("en", "From Env", "From File")


def test_explicit_config_file_and_list_settings(tmp_path):
    custom = tmp_path / "npr.toml"
    custom.write_text('source = "https://www.youtube.com/@nprmusic"\nsetlist_headers = ["set list", "songs"]\n')
    config = resolve({}, custom)
    assert config.source == "https://www.youtube.com/@nprmusic"
    assert config.setlist_headers == ("set list", "songs")


def test_paths_are_expanded():
    assert resolve({"music_dir": "~/Elsewhere"}).music_dir == Path.home() / "Elsewhere"


@pytest.mark.parametrize(
    "flags",
    [{"include": "("}, {"title_pattern": r"^(.+): tiny desk"}, {"setlist_headers": " , "}],
)
def test_invalid_settings_are_rejected(flags):
    with pytest.raises(ConfigError):
        resolve(flags)


def test_unknown_setting_in_file_is_rejected():
    Path("tinydesk.toml").write_text('sorce = "typo"\n')
    with pytest.raises(ConfigError, match="sorce"):
        resolve({})


def test_missing_explicit_config_file_is_rejected():
    with pytest.raises(ConfigError, match="not found"):
        resolve({}, Path("nope.toml"))


@pytest.mark.parametrize("example", sorted((Path(__file__).parent.parent / "examples").glob("*.toml")), ids=str)
def test_example_profiles_are_valid(example):
    assert resolve({}, example).source.startswith("https://www.youtube.com/")
