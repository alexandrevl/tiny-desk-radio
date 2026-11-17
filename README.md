# Tiny Desk Radio

**English** | [Português (pt-BR)](README.pt-BR.md)

`tinydesk` turns a Tiny Desk YouTube channel or playlist into **one tagged M4A file per song** and hands
them to Apple Music, so you can shuffle every artist like a radio station.

It ships configured for the [Tiny Desk Brasil](https://www.youtube.com/channel/UCFV9qv5deOsJ_AF7k_t4h3A)
channel, and works with any other channel or playlist that publishes full concerts with a setlist in the
description (NPR Music's Tiny Desk Concerts, other countries, ...).

> **Disclaimer.** This is a personal-use tool. You are responsible for complying with YouTube's Terms of
> Service and with copyright law in your country. See [Legal](#legal).

## Features

- **Per-song files, no re-encoding**: songs are cut from YouTube's AAC stream with `ffmpeg -c copy`.
  Applause and stage talk are left out.
- **Finds the songs by itself**: the setlist comes from the video description; the boundaries come from
  YouTube chapters when they exist, otherwise from audio analysis (bass energy, loudness, tonality and
  [YAMNet](https://www.tensorflow.org/hub/tutorials/yamnet)'s music detector).
- **Lyric check**: a local Whisper model listens to the concert and confirms which song is which, because
  descriptions do not always list songs in the order they were played.
- **Review gate**: when the detection does not add up, nothing is delivered. The episode goes to a review
  queue with a report, a proposed cut and a transcript of what is said between songs.
- **Proper tags**: title, artist, album artist, album, genre, year, track number and cover art.
- **Incremental**: `sync` only processes new videos; state lives in a local SQLite file.
- **Configurable source**: flag, environment variable or `tinydesk.toml`.
- Runs entirely on your machine; no accounts and no API keys.

## Requirements

| What | Needed for | Platform |
| --- | --- | --- |
| Python 3.12 and [uv](https://docs.astral.sh/uv/) | everything | any |
| [`ffmpeg`](https://ffmpeg.org) on your `PATH` | cutting and decoding | any |
| [`mlx-whisper`](https://github.com/ml-explore/mlx-examples/tree/main/whisper) | lyric check and review transcripts | **macOS on Apple Silicon only** |
| Apple Music (or Music.app) | the delivery folder | macOS |

What is macOS-specific: `mlx-whisper` (installed only on macOS/arm64 through an environment marker) and the
Apple Music auto-add folder. Everything else (listing, downloading, audio analysis, cutting, tagging,
tests) is plain Python and runs on Linux too, but `sync` currently needs the transcription step, so a full
run is only supported on Apple Silicon Macs. On other systems you can use `sync --dry-run`, the tests and
the library code. A pluggable transcription backend is on the [roadmap](#roadmap).

## Install

```sh
brew install ffmpeg            # macOS; use your package manager elsewhere
git clone https://github.com/alexandrevl/tiny-desk-radio.git
cd tiny-desk-radio
uv sync
```

The first real run downloads two models: YAMNet (4 MB) and Whisper large-v3-turbo (about 1.6 GB, from
Hugging Face). Disk use afterwards: about 20 MB of cached audio per concert, kept in `data/audio` so reruns
are fast.

## Quick start

```sh
uv run tinydesk sync --dry-run            # see which videos the source matches; downloads nothing
uv run tinydesk sync --limit 1 --no-deliver   # process one episode into ./library, touch nothing else
uv run tinydesk list                      # status of every episode
uv run tinydesk sync                      # whole catalog; delivers `ok` episodes to Music
```

Songs land in `./library/<Artist>/<NN> - <Title>.m4a`. For episodes in the `ok` state they are also copied
into Music's auto-add folder (`~/Music/Music/Media.localized/Automatically Add to Music.localized`), once.

### Another channel or playlist (NPR Tiny Desk Concerts)

```sh
uv run tinydesk sync --dry-run \
  --source "https://www.youtube.com/playlist?list=PL1B627337ED6F55F0" \
  --include "tiny desk" --exclude "contest|behind the scenes" --language en
```

Or keep it in a `tinydesk.toml` next to where you run the command (see [`examples/`](examples)):

```toml
source = "https://www.youtube.com/playlist?list=PL1B627337ED6F55F0"
include = "tiny desk"
exclude = "contest|behind the scenes"
language = "en"
```

A generic "any channel" setup needs three things: the channel or playlist URL, an `include` regex that
matches the titles of the full concerts (and only those), and a `title_pattern` that extracts the artist
if titles are not shaped like `Artist: Tiny Desk ...`. Use `sync --dry-run` to check the filter before
downloading anything. A channel's root URL (`https://www.youtube.com/@name`) is read as its Videos tab.

## Command reference

| Command | What it does |
| --- | --- |
| `tinydesk sync` | Process the episodes of the source that are not in the state database yet, then deliver `ok` ones. |
| `tinydesk sync --limit N` | Process at most `N` new episodes. |
| `tinydesk sync --video ID` | (Re)process one video. |
| `tinydesk sync --no-deliver` | Build `./library` only. |
| `tinydesk sync --dry-run` | List matched videos and their status; download nothing. |
| `tinydesk list` | Table of every known episode: status, setlist count, detected count, delivered, reason. |
| `tinydesk approve ID` | Accept the proposed cut of a `review` episode and deliver it. |
| `tinydesk apply ID times.json` | Cut a `review` episode where you say and deliver it. |

`sync`, `approve` and `apply` accept all the settings flags below and `--no-deliver`.

Episode states: `ok` (cut, tagged, in the library), `review` (needs a human, see below), `skipped` (no
setlist, or the artist could not be read from the title).

## Configuration

Precedence: **flag > environment variable > `tinydesk.toml` > default**. The TOML file is read from the
current directory, or from `--config FILE`. Unknown keys are an error.

| Setting (TOML key) | Flag | Environment | Default |
| --- | --- | --- | --- |
| `source` | `--source` | `TINYDESK_SOURCE` | the Tiny Desk Brasil channel |
| `include` | `--include` | `TINYDESK_INCLUDE` | `tiny desk (brasil\|brazil)` |
| `exclude` | `--exclude` | `TINYDESK_EXCLUDE` | `premiere\|tiny ?talks` |
| `title_pattern` | `--title-pattern` | `TINYDESK_TITLE_PATTERN` | `^(?P<artist>.+?)\s*:\s*(?:npr music )?tiny desk\b` |
| `language` | `--language` | `TINYDESK_LANGUAGE` | `pt` |
| `setlist_headers` | `--setlist-headers a,b` | `TINYDESK_SETLIST_HEADERS` | `setlist, set list, tracklist, track list, playlist, músicas, musicas, repertório, repertorio` |
| `album` | `--album` | `TINYDESK_ALBUM` | `Tiny Desk Radio` |
| `genre` | `--genre` | `TINYDESK_GENRE` | `Tiny Desk` |
| `cookies_from_browser` | `--cookies-from-browser` | `TINYDESK_COOKIES_FROM_BROWSER` | none; set to `chrome` if YouTube asks to confirm you're not a bot |
| `library` | `--library` | `TINYDESK_LIBRARY` | `library` |
| `music_dir` | `--music-dir` | `TINYDESK_MUSIC_DIR` | Music's auto-add folder |

Notes:

- `include`, `exclude` and `title_pattern` are case-insensitive regular expressions. `title_pattern` must
  contain a named group `(?P<artist>...)`.
- `language` is the Whisper language code of the lyrics (`pt`, `en`, `es`, ...).
- A setlist is the block of lines after a header line (the whole line must be one of the header words),
  one title per line, up to the first blank line. Quotes around titles are removed.
- The state database (`data/state.db`) is keyed by video id, so you can switch sources freely: episodes
  already processed are skipped, whichever source they came from. Changing filters does not re-evaluate
  episodes that are already recorded; use `sync --video ID` for those.
- Switching `music_dir`/`library` between runs is fine, but an episode is delivered once and remembered.

## How an episode is split

1. **Setlist.** The titles under the setlist header of the description (episodes without one are skipped).
2. **Boundaries.** YouTube chapters if the video has them. Otherwise every 0.25 s of audio gets a
   "music" score from four independent cues that all drop during applause and talk: bass energy, loudness,
   spectral tonality, and YAMNet's music probability. Knowing there are exactly *N* songs, the tool picks
   the *N* disjoint stretches with the best total score, then widens their edges through quiet passages
   YAMNet still hears as music.
3. **Titles.** Matched in setlist order, unless Whisper hears a title sung in a different song, in which
   case the titles follow the lyrics.
4. **Cut and tag.** `ffmpeg -c copy`, then tags and cover art (the video thumbnail) with mutagen.

### Review gate

An episode goes to `review` (nothing is delivered) when:

- fewer songs are separated by applause or talk than the setlist lists (songs played back to back);
- a track is shorter than 90 s or longer than 10 min;
- the lyrics suggest a different order than the setlist but one of the moved titles cannot be confirmed;
- the setlist and the chapters disagree.

`data/review/<video_id>.json` then holds the problems, the proposed cut (`proposed`, with times in seconds)
and a transcript of what is said between the proposed songs. Then either:

```sh
uv run tinydesk approve <video_id>            # the proposal is right
uv run tinydesk apply <video_id> times.json   # fix it: [{"title": "...", "start": 7.7, "end": 150.0}, ...]
```

An episode that was already delivered cannot be cut again (that would put duplicate songs in Music); the
command says so and does nothing.

## Smart playlist in Music

Every song has album **Tiny Desk Radio** (or your `album` setting) and genre **Tiny Desk**. In Music:
*File ▸ New ▸ Smart Playlist…*, set **Album** **is** `Tiny Desk Radio`, keep *Live updating* on, name it
and press shuffle. New episodes join it as soon as `tinydesk sync` delivers them.

## Troubleshooting

- **`ffmpeg: command not found`**: install ffmpeg and make sure it is on your `PATH`.
- **yt-dlp warnings about a JavaScript challenge**: usually harmless. If downloads fail, update yt-dlp
  (`uv lock --upgrade-package yt-dlp && uv sync`); installing `deno` can help.
- **`transcription needs mlx-whisper`**: a full `sync` needs macOS on Apple Silicon (see Requirements).
- **`Music auto-add folder not found`**: set `music_dir` / `--music-dir`, or use `--no-deliver`.
- **Songs do not appear in Music**: Music imports from the auto-add folder while it is running; open it
  once. Files it cannot import are moved to a "Not Added" folder next to the auto-add folder.
- **Titles in the wrong order or an episode in `review`**: see the report in `data/review/`.
- **Start over for one episode**: `sync --video ID` (not possible once delivered).

## Limitations

- The audio is whatever YouTube serves: AAC at roughly 128-160 kbps. Songs are not re-encoded, so quality
  equals the source; it is not lossless.
- The audio analysis is heuristic. Songs played back to back, long spoken introductions over music and
  very quiet intros can be cut a second or three off, or merged. The review gate catches many, not all:
  spot-check what you deliver. Tracks have no fades.
- Setlists are parsed from free text; descriptions that do not follow the "header, then one title per
  line" shape are skipped.
- Whisper can mishear lyrics; it is only used as a cross-check and for review transcripts.
- Full runs require Apple Silicon today (see Requirements).

## Roadmap

Maintainers and contributors are very welcome; see [CONTRIBUTING.md](CONTRIBUTING.md).

- Pluggable transcription backend (`faster-whisper` or `whisper.cpp`) so full runs work on Linux and Intel.
- A `--no-lyrics` mode that relies on audio analysis only.
- Better splitting of songs that run together without applause (use lyric repeats and chord changes).
- Optional crossfade or short fades at the cut points.
- Output to other targets (plain folders, Plex/Jellyfin naming, other players' import folders).
- Packaging on PyPI and Homebrew.

Good first issues:

1. Add a ready-made profile in `examples/` for another Tiny Desk channel, verified with `--dry-run`.
2. Add more setlist header words and real-world description samples to `tests/test_setlist.py`.
3. A `tinydesk review` command that prints the review reports as a readable summary.
4. A `tinydesk forget ID` command that resets one episode in the state database.
5. Translate the README to another language.

## Development

```sh
uv sync
uv run pytest
uv run ruff check
uv run ruff format --check
```

Tests need neither network nor Whisper. More in [CONTRIBUTING.md](CONTRIBUTING.md). Changes are listed in
[CHANGELOG.md](CHANGELOG.md).

## Support

Questions and ideas: open a GitHub Discussion or issue. Bugs: use the bug template. A song cut in the
wrong place: use the "Wrong split" template and attach the review JSON. Security issues: see
[SECURITY.md](SECURITY.md).

## Legal

- This project is a **personal-use tool**. It downloads audio from YouTube **on your machine**, for you.
  **You** are responsible for complying with the
  [YouTube Terms of Service](https://www.youtube.com/t/terms) and with copyright law where you live.
  Make sure you have the right to download and keep the content you process.
- **No content is distributed by this repository.** It contains only source code. Downloaded audio,
  transcripts, the state database and the generated library live in `data/` and `library/`, which are
  git-ignored; do not commit or share them.
- This project is **not affiliated with, endorsed by or sponsored by** NPR, Tiny Desk, Anonymous Content,
  YouTube, Google or Apple. All trademarks and names belong to their respective owners.
- The software is provided "as is", without warranty. See [LICENSE](LICENSE) (MIT).

Third-party components: [yt-dlp](https://github.com/yt-dlp/yt-dlp) (Unlicense),
[mutagen](https://github.com/quodlibet/mutagen) (GPL-2.0-or-later; used as a library),
[mlx-whisper](https://github.com/ml-explore/mlx-examples) and OpenAI Whisper models (MIT),
[YAMNet](https://github.com/tensorflow/models/tree/master/research/audioset/yamnet) (Apache-2.0, model
downloaded at first run), [ai-edge-litert](https://pypi.org/project/ai-edge-litert/) (Apache-2.0),
[NumPy](https://numpy.org) (BSD-3-Clause).

## License

[MIT](LICENSE) © 2026 Alexandre Lima
