# Contributing

Thanks for helping! This is a small, young project and maintainers are wanted: if you would like to review
issues and pull requests regularly, say so in an issue.

By participating you agree to the [Code of Conduct](CODE_OF_CONDUCT.md).

## Development setup

You need Python 3.12, [uv](https://docs.astral.sh/uv/) and `ffmpeg`. A full `tinydesk sync` also needs an
Apple Silicon Mac (for `mlx-whisper`); everything else, including the whole test suite, works on Linux.

```sh
git clone https://github.com/alexandrevl/tiny-desk-radio.git
cd tiny-desk-radio
uv sync
uv run pytest
uv run ruff check
uv run ruff format --check
```

`uv run ruff format` fixes formatting. CI runs the same three commands on Ubuntu and macOS.

## Tests

- Tests must not need the network, `ffmpeg` output, model downloads or `mlx-whisper`. Test pure logic
  (parsing, scoring, reconciliation, configuration, state, delivery) with small inline fixtures.
- Real-world description excerpts make the best fixtures (see `tests/test_setlist.py`). Cut them down and
  keep only what the test needs. Do not commit audio, thumbnails or transcripts.
- A bug fix should come with a test that fails without it.

## Code style

- `ruff` decides formatting and lint (line length 120); do not fight it.
- Everything (code, comments, docs, commit messages) is in English; the Portuguese README is
  `README.pt-BR.md`, please keep both in sync when you change user-facing behaviour.
- Small modules with one job each (see `src/tinydesk/`). Prefer plain functions and dataclasses; add an
  abstraction when there are two real users of it, not before.
- No dead code, no speculative options. Comments explain *why*, not *what*.
- User-facing errors that the user can fix are `UserError` / `ConfigError` (printed without a traceback).

## Adding a source (profile)

Most "new sources" need no code. Copy [`examples/any-channel.toml`](examples/any-channel.toml), point it at
the channel or playlist, and tune `include`, `exclude`, `title_pattern`, `language` and
`setlist_headers` until `uv run tinydesk sync --dry-run --config yourfile.toml` lists exactly the full
concerts. Then run one episode with `--limit 1 --no-deliver` and check the tracks. If it works, send a PR
adding `examples/<name>.toml` and a one-line mention in the README.

If a source needs something the settings cannot express (a different setlist layout, for instance), open
an issue with a few real description excerpts first, and add them as test fixtures with the change.

## Reporting problems

Use the issue templates. For a song cut in the wrong place, the "Wrong split" template asks for the video
id, the setlist and the `data/review/<id>.json` file when there is one.

## Pull requests

1. Fork, branch from `main` (`feat/...`, `fix/...`, `docs/...`).
2. Keep the change focused; unrelated cleanups go in their own PR.
3. Run `uv run pytest`, `uv run ruff check` and `uv run ruff format --check`.
4. Update the README (both languages if user-facing) and [CHANGELOG.md](CHANGELOG.md) under *Unreleased*.
5. Fill in the PR template. A maintainer will review; CI must be green.

## Commit messages

[Conventional Commits](https://www.conventionalcommits.org/): `type(scope): summary` in the imperative,
at most about 72 characters, for example `fix(segmentation): keep quiet intros`. Types: `feat`, `fix`,
`docs`, `test`, `refactor`, `chore`, `ci`. Explain the *why* in the body when it is not obvious.

## Legal

Do not contribute, attach to issues or commit downloaded audio or other copyrighted media. See the legal
section of the README.
