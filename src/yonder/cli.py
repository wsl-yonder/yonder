import argparse
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict

from . import __version__
from .collector import collect_sources, content_hash
from .config import load_settings, load_sources
from .db import (
    connect,
    init_db,
    insert_article,
    insert_digest,
    insert_processed_item,
    insert_push_history,
    mark_digest_sent,
    top_items_by_channel,
    unprocessed_articles,
    upsert_sources,
)
from .digest import CHANNEL_ORDER, build_digest, digest_title, write_preview
from .github_trending import update_github_cache
from .processor import process_row
from .static_export import export_static_site
from .web import serve_dashboard
from .wxpusher import send_message

LOGGER = logging.getLogger(__name__)


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(levelname)s %(message)s")


def command_init_db(args) -> None:
    settings = load_settings(project_root())
    sources = load_sources(settings.sources_path)
    with connect(settings.database_path) as conn:
        init_db(conn)
        upsert_sources(conn, sources)
    print(f"Initialized database: {settings.database_path}")
    print(f"Registered sources: {len(sources)}")


def command_collect(args) -> None:
    settings = load_settings(project_root())
    sources = load_sources(settings.sources_path)
    with connect(settings.database_path) as conn:
        init_db(conn)
        upsert_sources(conn, sources)
        items = collect_sources(sources, settings.max_items_per_source)
        inserted = 0
        for item in items:
            if insert_article(conn, item, content_hash(item.title, item.url)):
                inserted += 1
    print(f"Collected items: {len(items)}")
    print(f"New articles: {inserted}")


def command_process(args) -> None:
    settings = load_settings(project_root())
    with connect(settings.database_path) as conn:
        init_db(conn)
        rows = unprocessed_articles(conn, limit=args.limit)
        for row in rows:
            insert_processed_item(conn, process_row(row))
    print(f"Processed articles: {len(rows)}")


def generate_digest(settings) -> Dict[str, object]:
    now = datetime.now()
    title = digest_title(now)
    with connect(settings.database_path) as conn:
        init_db(conn)
        items_by_channel = {
            channel: top_items_by_channel(
                conn,
                channel,
                settings.digest_max_items_per_channel,
            )
            for channel in CHANNEL_ORDER
        }
        content = build_digest(title, items_by_channel)
        digest_id = insert_digest(conn, title, content)
    preview_path = write_preview(settings.output_dir, title, content)
    return {
        "id": digest_id,
        "title": title,
        "content": content,
        "preview_path": preview_path,
    }


def command_digest(args) -> None:
    settings = load_settings(project_root())
    result = generate_digest(settings)
    print(f"Digest draft: {result['preview_path']}")
    if args.print:
        print("")
        print(result["content"])


def command_send(args) -> None:
    settings = load_settings(project_root())
    result = generate_digest(settings)

    if not args.yes:
        print(f"Digest draft: {result['preview_path']}")
        print("Type SEND to push this digest through WxPusher.")
        confirmation = input("> ").strip()
        if confirmation != "SEND":
            print("Send cancelled.")
            return

    wx_result = send_message(
        settings.wxpusher_app_token,
        result["content"],
        result["title"],
        settings.wxpusher_uids,
        settings.wxpusher_topic_ids,
    )

    target = ",".join(settings.wxpusher_uids) or ",".join(str(x) for x in settings.wxpusher_topic_ids)
    with connect(settings.database_path) as conn:
        insert_push_history(conn, int(result["id"]), target, wx_result.success, wx_result.response_text)
        if wx_result.success:
            mark_digest_sent(conn, int(result["id"]))

    print(f"Digest draft: {result['preview_path']}")
    print(f"WxPusher success: {wx_result.success}")
    print(wx_result.response_text)


def command_run_once(args) -> None:
    command_collect(args)
    command_process(args)
    if args.send:
        command_send(args)
    else:
        command_digest(args)


def command_update_github(args) -> None:
    payload = update_github_cache(project_root(), limit=args.limit)
    print(f"Updated GitHub trending: {len(payload.get('items', []))} items")
    print(f"Fetched at: {payload.get('fetched_at')}")


def command_daily_update(args) -> None:
    settings = load_settings(project_root())
    sources = load_sources(settings.sources_path)
    with connect(settings.database_path) as conn:
        init_db(conn)
        upsert_sources(conn, sources)
        items = collect_sources(sources, settings.max_items_per_source)
        inserted = 0
        for item in items:
            if insert_article(conn, item, content_hash(item.title, item.url)):
                inserted += 1
        rows = unprocessed_articles(conn, limit=args.limit)
        for row in rows:
            insert_processed_item(conn, process_row(row))

    github_payload = update_github_cache(project_root(), limit=args.github_limit)
    print(f"Collected items: {len(items)}")
    print(f"New articles: {inserted}")
    print(f"Processed articles: {len(rows)}")
    print(f"Updated GitHub trending: {len(github_payload.get('items', []))} items")


def _seconds_until_run(hour: int, minute: int) -> float:
    now = datetime.now()
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    return max((target - now).total_seconds(), 1.0)


def command_auto_update(args) -> None:
    hour, minute = (int(part) for part in args.time.split(":", 1))
    print(f"Auto update is running. Daily refresh time: {hour:02d}:{minute:02d}")
    while True:
        wait_seconds = _seconds_until_run(hour, minute)
        next_run = datetime.now() + timedelta(seconds=wait_seconds)
        print(f"Next update: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
        time.sleep(wait_seconds)
        command_daily_update(args)


def command_web(args) -> None:
    serve_dashboard(project_root(), host=args.host, port=args.port)


def command_export_static(args) -> None:
    output_dir = Path(args.output)
    if not output_dir.is_absolute():
        output_dir = project_root() / output_dir
    result = export_static_site(project_root(), output_dir=output_dir, clean=not args.no_clean)
    print(f"Static site exported: {result['output_root']}")
    print(f"HTML pages: {len(result['pages'])}")
    print(f"Static assets: {result['static_root']}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="yonder")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("-v", "--verbose", action="store_true")

    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init-db", help="Create database tables and register sources.")
    init_parser.set_defaults(func=command_init_db)

    collect_parser = subparsers.add_parser("collect", help="Collect RSS items into the database.")
    collect_parser.set_defaults(func=command_collect)

    process_parser = subparsers.add_parser("process", help="Process unprocessed articles.")
    process_parser.add_argument("--limit", type=int, default=500)
    process_parser.set_defaults(func=command_process)

    digest_parser = subparsers.add_parser("digest", help="Generate a Markdown digest draft.")
    digest_parser.add_argument("--print", action="store_true")
    digest_parser.set_defaults(func=command_digest)

    send_parser = subparsers.add_parser("send", help="Generate and send a digest through WxPusher.")
    send_parser.add_argument("--yes", action="store_true", help="Send without interactive confirmation.")
    send_parser.set_defaults(func=command_send)

    run_parser = subparsers.add_parser("run-once", help="Collect, process, and generate a digest.")
    run_parser.add_argument("--limit", type=int, default=500)
    run_parser.add_argument("--send", action="store_true")
    run_parser.add_argument("--yes", action="store_true", help="Send without interactive confirmation.")
    run_parser.add_argument("--print", action="store_true")
    run_parser.set_defaults(func=command_run_once)

    github_parser = subparsers.add_parser("update-github", help="Refresh recent GitHub high-star projects.")
    github_parser.add_argument("--limit", type=int, default=50)
    github_parser.set_defaults(func=command_update_github)

    daily_parser = subparsers.add_parser("daily-update", help="Refresh all dashboard data once.")
    daily_parser.add_argument("--limit", type=int, default=500)
    daily_parser.add_argument("--github-limit", type=int, default=50)
    daily_parser.set_defaults(func=command_daily_update)

    auto_parser = subparsers.add_parser("auto-update", help="Run the dashboard refresh every day.")
    auto_parser.add_argument("--time", default="08:30", help="Local daily refresh time, HH:MM.")
    auto_parser.add_argument("--limit", type=int, default=500)
    auto_parser.add_argument("--github-limit", type=int, default=50)
    auto_parser.set_defaults(func=command_auto_update)

    web_parser = subparsers.add_parser("web", help="Start the local Yonder dashboard.")
    web_parser.add_argument("--host", default="127.0.0.1")
    web_parser.add_argument("--port", type=int, default=8765)
    web_parser.set_defaults(func=command_web)

    export_parser = subparsers.add_parser("export-static", help="Export the dashboard to static HTML files.")
    export_parser.add_argument("--output", default="dist", help="Output directory for the static site.")
    export_parser.add_argument("--no-clean", action="store_true", help="Do not delete the output directory first.")
    export_parser.set_defaults(func=command_export_static)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    configure_logging(args.verbose)
    args.func(args)


if __name__ == "__main__":
    main()
