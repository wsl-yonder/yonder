from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class Source:
    name: str
    url: str
    type: str
    channel: str
    credibility_score: float
    enabled: bool = True


@dataclass(frozen=True)
class FeedItem:
    source_name: str
    source_url: str
    channel: str
    credibility_score: float
    title: str
    url: str
    published_at: Optional[datetime]
    raw_summary: str


@dataclass(frozen=True)
class ProcessedItem:
    article_id: int
    channel: str
    title: str
    url: str
    source_name: str
    published_at: Optional[str]
    one_liner: str
    bullet_points: str
    importance: str
    uncertainty: str
    score: float
