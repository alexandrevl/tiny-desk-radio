# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres
to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-11-14

### Added

- `tinydesk sync` turns a Tiny Desk YouTube channel or playlist into one tagged M4A per song, cut from the
  AAC stream without re-encoding, organised as `library/<Artist>/<NN> - <Title>.m4a`.
- Setlist parsing from video descriptions, with configurable header words; YouTube chapters are used for
  boundaries when present.
- Audio analysis that locates the songs (bass energy, loudness, tonality and YAMNet's music probability)
  and leaves applause and stage talk out.
- Local Whisper transcription (`mlx-whisper`) used to match titles to songs by lyrics when the setlist
  order differs from the performance order.
- Review gate: `review` state, `data/review/<id>.json` reports, `tinydesk approve` and `tinydesk apply`.
- Delivery to Apple Music's auto-add folder, once per episode, with atomic copies.
- `tinydesk list`, `sync --limit`, `sync --video`, `sync --no-deliver`, `sync --dry-run`.
- Configurable source and behaviour: flags, `TINYDESK_*` environment variables and `tinydesk.toml`
  (source, include/exclude and title patterns, language, setlist headers, album, genre, library and
  Music folder); example profiles in `examples/`.
- MP4 tags: title, artist, album artist, album, genre, year, track number and cover art.
- English and Brazilian Portuguese documentation, contribution guide, issue templates and CI.

### Notes

- A full `sync` currently requires macOS on Apple Silicon (`mlx-whisper`).

[Unreleased]: https://github.com/alexandrevl/tiny-desk-radio/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/alexandrevl/tiny-desk-radio/releases/tag/v0.1.0
