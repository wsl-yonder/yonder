import email.utils
import html
import hashlib
import logging
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Iterable, List, Optional

from .models import FeedItem, Source
from .text import clean_text

LOGGER = logging.getLogger(__name__)


def content_hash(title: str, url: str) -> str:
    normalized = f"{title.strip().lower()}|{url.strip().lower()}"
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def fetch_url(url: str, timeout: int = 20, attempts: int = 3, accept: str = "") -> bytes:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "KnowledgeRadar/0.1 (+https://local)",
            "Accept": accept or "application/rss+xml, application/atom+xml, application/xml, text/xml",
        },
    )
    last_error = None
    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read()
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_error = exc
            if attempt < attempts:
                time.sleep(0.5 * attempt)
    raise last_error


def parse_datetime(value: str) -> Optional[datetime]:
    value = (value or "").strip()
    if not value:
        return None

    try:
        parsed_tuple = email.utils.parsedate_to_datetime(value)
        if parsed_tuple:
            if parsed_tuple.tzinfo is None:
                return parsed_tuple.replace(tzinfo=timezone.utc)
            return parsed_tuple
    except (TypeError, ValueError):
        pass

    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _child_text(element: ET.Element, names: Iterable[str]) -> str:
    wanted = set(names)
    for child in list(element):
        tag = child.tag.rsplit("}", 1)[-1]
        if tag in wanted:
            return clean_text(child.text or "")
    return ""


def _entry_link(element: ET.Element) -> str:
    direct = _child_text(element, ["link"])
    if direct:
        return direct

    for child in list(element):
        tag = child.tag.rsplit("}", 1)[-1]
        if tag != "link":
            continue
        href = child.attrib.get("href", "")
        rel = child.attrib.get("rel", "alternate")
        if href and rel == "alternate":
            return href
    return ""


def parse_feed(payload: bytes, source: Source) -> List[FeedItem]:
    root = ET.fromstring(payload)
    root_tag = root.tag.rsplit("}", 1)[-1].lower()

    if root_tag == "rss":
        entries = root.findall("./channel/item")
    elif root_tag == "feed":
        entries = root.findall("./{*}entry")
    else:
        entries = root.findall(".//item") or root.findall(".//{*}entry")

    items: List[FeedItem] = []
    for entry in entries:
        title = _child_text(entry, ["title"])
        url = _entry_link(entry)
        published_raw = _child_text(entry, ["pubDate", "published", "updated", "date"])
        summary = _child_text(entry, ["description", "summary", "content", "encoded"])

        if not title or not url:
            continue

        items.append(
            FeedItem(
                source_name=source.name,
                source_url=source.url,
                channel=source.channel,
                credibility_score=source.credibility_score,
                title=title,
                url=url,
                published_at=parse_datetime(published_raw),
                raw_summary=summary,
            )
        )
    return items


def _strip_tags(value: str) -> str:
    return clean_text(re.sub(r"<[^>]+>", " ", html.unescape(value or "")))


def _absolute_url(url: str, source_url: str) -> str:
    return urllib.parse.urljoin(source_url, html.unescape(url or "").strip())


def _parse_relative_time(value: str) -> Optional[datetime]:
    value = clean_text(value or "")
    now = datetime.now(timezone.utc)
    if not value:
        return now
    if "分钟前" in value:
        match = re.search(r"(\d+)", value)
        if match:
            return now
    if "小时前" in value or "今天" in value or "刚刚" in value:
        return now
    match = re.search(r"(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})", value)
    if match:
        year, month, day = (int(part) for part in match.groups())
        return datetime(year, month, day, tzinfo=timezone.utc)
    return now


def parse_html_list(payload: bytes, source: Source) -> List[FeedItem]:
    document = payload.decode("utf-8", "ignore")
    items: List[FeedItem] = []

    if "finance.sina.cn" in source.url:
        pattern = re.compile(
            r'<a[^>]+href="(?P<url>[^"]+)"[^>]*>\s*<dl class="carditems_list">.*?'
            r'<h3[^>]*>(?P<title>.*?)</h3>.*?'
            r'<span[^>]*class="[^"]*time_num[^"]*"[^>]*>(?P<time>.*?)</span>',
            re.S,
        )
        for match in pattern.finditer(document):
            title = _strip_tags(match.group("title"))
            url = _absolute_url(match.group("url"), source.url)
            if not title or not url:
                continue
            items.append(
                FeedItem(
                    source_name=source.name,
                    source_url=source.url,
                    channel=source.channel,
                    credibility_score=source.credibility_score,
                    title=title,
                    url=url,
                    published_at=_parse_relative_time(match.group("time")),
                    raw_summary=f"{source.name} 最新滚动：{title}",
                )
            )
        return items

    seen = set()
    seen_urls = set()
    anchor_pattern = re.compile(r'<a[^>]+href="(?P<url>[^"]+)"[^>]*>(?P<body>.*?)</a>', re.S)
    for match in anchor_pattern.finditer(document):
        url = _absolute_url(match.group("url"), source.url)
        body = match.group("body")
        title = _strip_tags(body)
        if not title or len(title) < 8:
            continue
        if "36kr.com" in source.url and "/p/" not in url:
            continue
        if "36kr.com" in source.url and url in seen_urls:
            continue
        key = (title, url)
        if key in seen:
            continue
        seen.add(key)
        seen_urls.add(url)
        items.append(
            FeedItem(
                source_name=source.name,
                source_url=source.url,
                channel=source.channel,
                credibility_score=source.credibility_score,
                title=title,
                url=url,
                published_at=datetime.now(timezone.utc),
                raw_summary=f"{source.name} 最新文章：{title}",
            )
        )
    return items


def collect_source(source: Source, limit: int) -> List[FeedItem]:
    if source.type not in {"rss", "html_list"}:
        LOGGER.warning("Skipping unsupported source type: %s (%s)", source.name, source.type)
        return []

    try:
        if source.type == "html_list":
            payload = fetch_url(source.url, accept="text/html,application/xhtml+xml")
            return parse_html_list(payload, source)[:limit]
        payload = fetch_url(source.url)
        return parse_feed(payload, source)[:limit]
    except (ET.ParseError, urllib.error.URLError, TimeoutError) as exc:
        LOGGER.warning("Failed to collect %s: %s", source.name, exc)
        return []


def collect_sources(sources: Iterable[Source], limit_per_source: int) -> List[FeedItem]:
    items: List[FeedItem] = []
    for source in sources:
        if not source.enabled:
            continue
        source_items = collect_source(source, limit_per_source)
        LOGGER.info("Collected %s items from %s", len(source_items), source.name)
        items.extend(source_items)
    return items
