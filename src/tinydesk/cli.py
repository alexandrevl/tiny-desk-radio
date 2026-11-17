"""`tinydesk` command line."""

import argparse
import sys
from importlib.metadata import version
from pathlib import Path

from tinydesk import catalog, config, pipeline, state


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        settings = args.settings(args)
        ws = pipeline.Workspace(Path.cwd(), settings)
        return args.run(args, ws, state.State(ws.database))
    except (pipeline.UserError, config.ConfigError) as error:
        print(f"tinydesk: {error}", file=sys.stderr)
        return 1


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tinydesk",
        description="Turn a Tiny Desk YouTube channel or playlist into per-song files for Apple Music.",
        epilog="Settings are read from flags, then TINYDESK_* environment variables, then tinydesk.toml.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {version('tiny-desk-radio')}")
    commands = parser.add_subparsers(dest="command", required=True)

    settings = argparse.ArgumentParser(add_help=False)
    group = settings.add_argument_group("settings (see the README for the full table)")
    group.add_argument("--config", type=Path, metavar="FILE", help=f"settings file (default: ./{config.CONFIG_FILE})")
    group.add_argument("--source", help="YouTube channel or playlist URL")
    group.add_argument("--include", metavar="REGEX", help="only titles matching this (case-insensitive) are concerts")
    group.add_argument("--exclude", metavar="REGEX", help="skip titles matching this")
    group.add_argument("--title-pattern", metavar="REGEX", help="regex with a (?P<artist>...) group, applied to titles")
    group.add_argument("--language", help="language of the lyrics for Whisper, e.g. pt, en, es")
    group.add_argument("--setlist-headers", metavar="A,B", help="words that introduce the setlist in descriptions")
    group.add_argument("--album", help="album tag")
    group.add_argument("--genre", help="genre tag")
    group.add_argument("--library", help="where the per-song files are kept")
    group.add_argument("--music-dir", help="Music's auto-add folder")
    group.add_argument(
        "--cookies-from-browser", metavar="BROWSER", help="let yt-dlp use this browser's YouTube login, e.g. chrome"
    )

    delivery = argparse.ArgumentParser(add_help=False)
    delivery.add_argument("--no-deliver", action="store_true", help="only build the library, do not copy into Music")

    sync = commands.add_parser(
        "sync", parents=[settings, delivery], help="process new episodes and deliver the good ones"
    )
    sync.add_argument("--limit", type=int, metavar="N", help="process at most N new episodes")
    sync.add_argument("--video", metavar="ID", help="(re)process this video only")
    sync.add_argument("--dry-run", action="store_true", help="list the episodes the source matches; download nothing")
    sync.set_defaults(run=_sync, settings=_settings)

    commands.add_parser("list", help="status of every episode").set_defaults(run=_list, settings=_defaults)

    approve = commands.add_parser(
        "approve", parents=[settings, delivery], help="accept the proposed cut of a review episode"
    )
    approve.add_argument("video_id")
    approve.set_defaults(run=_approve, settings=_settings)

    apply = commands.add_parser(
        "apply", parents=[settings, delivery], help="cut a review episode at the times in a JSON file"
    )
    apply.add_argument("video_id")
    apply.add_argument("times", type=Path, help="JSON list of {title, start, end} in seconds")
    apply.set_defaults(run=_apply, settings=_settings)
    return parser


def _settings(args: argparse.Namespace) -> config.Config:
    flags = {name: getattr(args, name) for name in config.SETTINGS}
    return config.resolve(flags, args.config)


def _defaults(args: argparse.Namespace) -> config.Config:
    return config.Config()


def _require_music_dir(args: argparse.Namespace, ws: pipeline.Workspace) -> None:
    if not args.no_deliver and not ws.config.music_dir.is_dir():
        raise pipeline.UserError(
            f"Music auto-add folder not found: {ws.config.music_dir} (set music_dir / --music-dir, or use --no-deliver)"
        )


def _sync(args: argparse.Namespace, ws: pipeline.Workspace, db: state.State) -> int:
    if args.dry_run:
        return _dry_run(args, ws, db)
    _require_music_dir(args, ws)
    if args.video:
        ids = [args.video]
    else:
        ids = [i for i, _ in catalog.list_concerts(ws.config) if db.get(i) is None][: args.limit]
    failed = 0
    for video_id in ids:
        print(f"{video_id}: processing", flush=True)
        try:
            row = pipeline.sync_episode(video_id, ws, db)
        except pipeline.UserError:
            raise
        except Exception as error:  # one broken video must not stop the rest; it is retried next sync
            failed += 1
            print(f"{video_id}: failed: {error!r}", file=sys.stderr)
            continue
        print(f"{video_id}: {_describe(row)}", flush=True)
    if not args.no_deliver:
        targets = [db.get(args.video)] if args.video else db.all()
        for row in targets:
            if row and row.status == state.OK and pipeline.deliver(row, ws, ws.config.music_dir, db):
                print(f"{row.video_id}: delivered {len(row.files)} tracks to {ws.config.music_dir}")
    return 1 if failed else 0


def _dry_run(args: argparse.Namespace, ws: pipeline.Workspace, db: state.State) -> int:
    if args.video:
        raise pipeline.UserError("--dry-run lists a whole source; it cannot be combined with --video")
    concerts = catalog.list_concerts(ws.config)
    print(f"source: {catalog.source_url(ws.config.source)}")
    new = 0
    for video_id, title in concerts:
        row = db.get(video_id)
        label = row.status if row else "new"
        new += row is None
        print(f"{video_id}  {label:8}  {title}")
    selected = min(new, args.limit) if args.limit is not None else new
    print(f"{len(concerts)} concerts matched, {new} new; `sync` would process {selected}")
    return 0


def _finish(args: argparse.Namespace, ws: pipeline.Workspace, db: state.State, row: state.Row) -> int:
    print(f"{row.video_id}: {_describe(row)}")
    if not args.no_deliver and pipeline.deliver(row, ws, ws.config.music_dir, db):
        print(f"{row.video_id}: delivered {len(row.files)} tracks to {ws.config.music_dir}")
    return 0


def _approve(args: argparse.Namespace, ws: pipeline.Workspace, db: state.State) -> int:
    _require_music_dir(args, ws)
    return _finish(args, ws, db, pipeline.approve(args.video_id, ws, db))


def _apply(args: argparse.Namespace, ws: pipeline.Workspace, db: state.State) -> int:
    _require_music_dir(args, ws)
    return _finish(args, ws, db, pipeline.apply(args.video_id, args.times, ws, db))


def _list(args: argparse.Namespace, ws: pipeline.Workspace, db: state.State) -> int:
    print(f"{'video':11}  {'artist':32}  {'status':8}  {'setlist':>7}  {'found':>5}  {'delivered':9}  reason")
    for row in db.all():
        delivered = "yes" if row.delivered else "no"
        print(
            f"{row.video_id:11}  {(row.artist or '-')[:32]:32}  {row.status:8}  "
            f"{_count(row.setlist_count):>7}  {_count(row.detected_count):>5}  {delivered:9}  {row.reason or ''}"
        )
    return 0


def _count(value: int | None) -> str:
    return "-" if value is None else str(value)


def _describe(row: state.Row) -> str:
    detail = f" ({row.reason})" if row.reason else ""
    return f"{row.status}, setlist {_count(row.setlist_count)} / detected {_count(row.detected_count)}{detail}"
