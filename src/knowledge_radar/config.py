import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

from .models import Source


@dataclass(frozen=True)
class Settings:
    database_path: Path
    sources_path: Path
    output_dir: Path
    wxpusher_app_token: str
    wxpusher_uids: List[str]
    wxpusher_topic_ids: List[int]
    digest_timezone: str
    digest_max_items_per_channel: int
    max_items_per_source: int


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def _split_csv(value: str) -> List[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


def _split_int_csv(value: str) -> List[int]:
    ids: List[int] = []
    for part in _split_csv(value):
        try:
            ids.append(int(part))
        except ValueError:
            raise ValueError(f"Expected integer topic id, got: {part}") from None
    return ids


def load_settings(project_root: Path) -> Settings:
    load_dotenv(project_root / ".env")

    database_path = Path(os.environ.get("DATABASE_PATH", "data/knowledge_radar.sqlite3"))
    sources_path = Path(os.environ.get("SOURCES_PATH", "config/sources.json"))
    output_dir = Path(os.environ.get("OUTPUT_DIR", "out"))

    if not database_path.is_absolute():
        database_path = project_root / database_path
    if not sources_path.is_absolute():
        sources_path = project_root / sources_path
    if not output_dir.is_absolute():
        output_dir = project_root / output_dir

    return Settings(
        database_path=database_path,
        sources_path=sources_path,
        output_dir=output_dir,
        wxpusher_app_token=os.environ.get("WXPUSHER_APP_TOKEN", ""),
        wxpusher_uids=_split_csv(os.environ.get("WXPUSHER_UIDS", "")),
        wxpusher_topic_ids=_split_int_csv(os.environ.get("WXPUSHER_TOPIC_IDS", "")),
        digest_timezone=os.environ.get("DIGEST_TIMEZONE", "Asia/Shanghai"),
        digest_max_items_per_channel=int(os.environ.get("DIGEST_MAX_ITEMS_PER_CHANNEL", "5")),
        max_items_per_source=int(os.environ.get("MAX_ITEMS_PER_SOURCE", "20")),
    )


def load_sources(path: Path) -> List[Source]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    sources: List[Source] = []
    for item in payload:
        sources.append(
            Source(
                name=item["name"],
                url=item["url"],
                type=item.get("type", "rss"),
                channel=item["channel"],
                credibility_score=float(item.get("credibility_score", 0.7)),
                enabled=bool(item.get("enabled", True)),
            )
        )
    return sources


def channel_labels() -> Dict[str, str]:
    return {
        "ai": "AI",
        "finance": "金融",
        "tech": "科技",
    }
