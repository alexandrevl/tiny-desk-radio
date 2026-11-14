"""Settings: command-line flag > environment variable > `tinydesk.toml` > built-in default."""

import os
import re
import tomllib
from dataclasses import dataclass, fields
from pathlib import Path

DEFAULT_SOURCE = "https://www.youtube.com/channel/UCFV9qv5deOsJ_AF7k_t4h3A/videos"
DEFAULT_MUSIC_DIR = "~/Music/Music/Media.localized/Automatically Add to Music.localized"
CONFIG_FILE = "tinydesk.toml"
ENV_PREFIX = "TINYDESK_"


class ConfigError(Exception):
    """An invalid setting; shown to the user without a traceback."""


@dataclass(frozen=True)
class Config:
    source: str = DEFAULT_SOURCE
    include: str = r"tiny desk (brasil|brazil)"
    exclude: str = r"premiere|tiny ?talks"
    title_pattern: str = r"^(?P<artist>.+?)\s*:\s*(?:npr music )?tiny desk\b"
    language: str = "pt"
    setlist_headers: tuple[str, ...] = (
        "setlist",
        "set list",
        "tracklist",
        "track list",
        "playlist",
        "músicas",
        "musicas",
        "repertório",
        "repertorio",
    )
    album: str = "Tiny Desk Radio"
    genre: str = "Tiny Desk"
    library: Path = Path("library")
    music_dir: Path = Path(DEFAULT_MUSIC_DIR)


SETTINGS = [f.name for f in fields(Config)]


def _convert(name: str, raw: object) -> object:
    if name == "setlist_headers":
        items = raw.split(",") if isinstance(raw, str) else raw
        if not isinstance(items, list | tuple) or not all(isinstance(i, str) for i in items):
            raise ConfigError("setlist_headers must be a list of strings (or a comma-separated string)")
        return tuple(i.strip() for i in items if i.strip())
    if name in ("library", "music_dir"):
        return Path(str(raw)).expanduser()
    if not isinstance(raw, str):
        raise ConfigError(f"{name} must be a string")
    return raw


def load_file(path: Path) -> dict[str, object]:
    try:
        data = tomllib.loads(path.read_text())
    except tomllib.TOMLDecodeError as error:
        raise ConfigError(f"{path}: {error}") from error
    unknown = sorted(set(data) - set(SETTINGS))
    if unknown:
        raise ConfigError(f"{path}: unknown setting(s) {', '.join(unknown)}; valid: {', '.join(SETTINGS)}")
    return data


def resolve(flags: dict[str, str | None], config_path: Path | None = None) -> Config:
    """Merge flags, environment and the TOML file over the defaults, and validate the result."""
    if config_path is not None and not config_path.is_file():
        raise ConfigError(f"config file not found: {config_path}")
    path = config_path or Path(CONFIG_FILE)
    from_file = load_file(path) if path.is_file() else {}
    values: dict[str, object] = {}
    for name in SETTINGS:
        env = os.environ.get(ENV_PREFIX + name.upper())
        for raw in (flags.get(name), env, from_file.get(name)):
            if raw is not None:
                values[name] = _convert(name, raw)
                break
    config = Config(**values)
    _validate(config)
    return config


def _validate(config: Config) -> None:
    for name in ("include", "exclude", "title_pattern"):
        try:
            compiled = re.compile(getattr(config, name))
        except re.error as error:
            raise ConfigError(f"{name} is not a valid regular expression: {error}") from error
        if name == "title_pattern" and "artist" not in compiled.groupindex:
            raise ConfigError("title_pattern must contain a named group (?P<artist>...)")
    if not config.setlist_headers:
        raise ConfigError("setlist_headers must not be empty")
