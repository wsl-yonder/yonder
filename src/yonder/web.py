import html
import json
import logging
import mimetypes
import re
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .config import channel_labels, load_settings, load_sources
from .db import connect, dashboard_items, dashboard_stats, init_db, latest_digest
from .github_trending import load_github_projects
from .ai_news import AI_NEWS_FETCHED_AT, AI_ARTICLES

LOGGER = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[2]
GUTENDEX_API = "https://gutendex.com/books/"


def _escape(value) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def _fetch_json_url(url: str):
    request = urllib.request.Request(url, headers={"User-Agent": "KnowledgeRadar/0.1"})
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.load(response)


def _fetch_text_url(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "KnowledgeRadar/0.1"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", "ignore")


def _gutenberg_text_url(formats: dict) -> str:
    preferred = [
        "text/plain; charset=utf-8",
        "text/plain; charset=us-ascii",
        "text/plain",
    ]
    for key in preferred:
        value = formats.get(key)
        if value and not value.endswith(".zip"):
            return value
    for key, value in formats.items():
        if key.startswith("text/plain") and value and not value.endswith(".zip"):
            return value
    return ""


def _gutenberg_category(book: dict) -> str:
    subjects = " ".join(book.get("subjects", [])).lower()
    title = book.get("title", "")
    if "poetry" in subjects or "詩" in title or "诗" in title:
        return "诗词"
    if "history" in subjects or "史" in title:
        return "历史"
    if "fiction" in subjects or "記" in title or "记" in title or "演義" in title or "演义" in title:
        return "古典小说"
    return "公版"


def _simplify_gutenberg_book(book: dict) -> dict:
    authors = book.get("authors") or []
    author = authors[0].get("name", "佚名") if authors else "佚名"
    subjects = book.get("subjects") or []
    summary = " / ".join(subjects[:2]) or "Project Gutenberg 中文公版书，可作为真实书源接入阅读器。"
    return {
        "id": f"gutenberg-{book.get('id')}",
        "externalId": book.get("id"),
        "title": book.get("title", "未命名公版书"),
        "author": author,
        "gender": "公版",
        "category": _gutenberg_category(book),
        "status": "公版",
        "words": max(10000, int(book.get("download_count", 0)) * 180),
        "hot": int(book.get("download_count", 0)),
        "updated": "Project Gutenberg",
        "tags": ["公版", "Project Gutenberg", "可替换书源"],
        "colors": ["#5f4b32", "#b88a55"],
        "summary": summary,
        "source": "gutenberg",
        "sourceName": "Project Gutenberg",
        "sourceUrl": f"https://www.gutenberg.org/ebooks/{book.get('id')}",
        "needsLoad": True,
        "chapters": [],
    }


def _clean_gutenberg_text(text: str) -> str:
    text = text.replace("\ufeff", "")
    start = re.search(r"\*\*\*\s*START OF (?:THE|THIS) PROJECT GUTENBERG EBOOK.*?\*\*\*", text, re.I | re.S)
    end = re.search(r"\*\*\*\s*END OF (?:THE|THIS) PROJECT GUTENBERG EBOOK.*?\*\*\*", text, re.I | re.S)
    if start:
        text = text[start.end():]
    if end:
        text = text[:end.start()]
    return text.strip()


def _split_gutenberg_chapters(text: str, limit: int = 12) -> list[dict]:
    text = _clean_gutenberg_text(text)
    lines = [line.strip() for line in text.splitlines()]
    chapters = []
    current_title = ""
    current_lines = []
    chapter_pattern = re.compile(r"^第[一二三四五六七八九十百千零〇○两]+[回章節节].{0,40}$")
    for line in lines:
        if not line:
            continue
        if chapter_pattern.match(line):
            if current_title and current_lines:
                chapters.append({"title": current_title, "content": current_lines[:24]})
                if len(chapters) >= limit:
                    return chapters
            current_title = line
            current_lines = []
        elif current_title:
            current_lines.append(line)
    if current_title and current_lines and len(chapters) < limit:
        chapters.append({"title": current_title, "content": current_lines[:24]})
    if chapters:
        return chapters
    paragraphs = [line for line in lines if len(line) > 8]
    chunk_size = 12
    for index in range(0, min(len(paragraphs), limit * chunk_size), chunk_size):
        chapters.append({
            "title": f"选读 第{len(chapters) + 1}章",
            "content": paragraphs[index:index + chunk_size],
        })
    return chapters[:limit]


def gutenberg_books_payload(query: str = "") -> dict:
    params = {
        "languages": "zh",
        "copyright": "false",
        "page_size": "24",
    }
    if query:
        params["search"] = query
    url = f"{GUTENDEX_API}?{urllib.parse.urlencode(params)}"
    payload = _fetch_json_url(url)
    books = [_simplify_gutenberg_book(book) for book in payload.get("results", []) if _gutenberg_text_url(book.get("formats", {}))]
    return {
        "source": "gutenberg",
        "name": "Project Gutenberg 中文公版书",
        "count": payload.get("count", len(books)),
        "books": books,
    }


def gutenberg_book_detail_payload(book_id: str) -> dict:
    if not book_id.isdigit():
        raise ValueError("Invalid Gutenberg book id")
    book = _fetch_json_url(f"{GUTENDEX_API}{book_id}")
    simplified = _simplify_gutenberg_book(book)
    text_url = _gutenberg_text_url(book.get("formats", {}))
    if not text_url:
        raise ValueError("No plain text format found")
    simplified["chapters"] = _split_gutenberg_chapters(_fetch_text_url(text_url))
    simplified["needsLoad"] = False
    simplified["textUrl"] = text_url
    return simplified


def _active(current: str, value: str) -> str:
    return "active" if current == value else ""


def _format_date(value) -> str:
    if not value:
        return "时间未知"
    return str(value).replace("T", " ")[:16]


def _short_cn(value, max_chars: int = 72) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip("，。；、 ") + "…"


def _tech_chips(items) -> str:
    return "".join(f"<span>{_escape(item)}</span>" for item in items)


def _markdown_to_html(markdown: str) -> str:
    lines = []
    for raw_line in markdown.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("# "):
            lines.append(f"<h2>{_escape(line[2:])}</h2>")
        elif line.startswith("## "):
            lines.append(f"<h3>{_escape(line[3:])}</h3>")
        elif line.startswith("---"):
            lines.append("<hr>")
        else:
            linked = _escape(line)
            if "原文：" in line:
                prefix, url = line.split("原文：", 1)
                linked = f"{_escape(prefix)}原文：<a href=\"{_escape(url)}\" target=\"_blank\">{_escape(url)}</a>"
            lines.append(f"<p>{linked}</p>")
    return "\n".join(lines)


def render_dashboard(settings, channel: str, query: str) -> str:
    labels = channel_labels()
    valid_channel = channel if channel in labels else ""

    with connect(settings.database_path) as conn:
        init_db(conn)
        stats = dashboard_stats(conn)
        items = dashboard_items(conn, channel=valid_channel or None, query=query, limit=200)
        digest = latest_digest(conn)

    cards = []
    for item in items:
        label = labels.get(item["channel"], item["channel"])
        score = item["score"] if item["score"] is not None else 0
        one_liner = item["one_liner"] or "暂无摘要，运行 process 后会生成看点。"
        importance = item["importance"] or "暂无重要性说明。"
        cards.append(
            f"""
            <article class="item-card">
              <div class="item-meta">
                <span class="badge">{_escape(label)}</span>
                <span class="source">{_escape(item["source_name"])}</span>
                <span>{_escape(_format_date(item["published_at"] or item["created_at"]))}</span>
                <span class="score">Score {_escape(score)}</span>
              </div>
              <h2><a href="{_escape(item["url"])}" target="_blank">{_escape(item["title"])}</a></h2>
              <p class="one-liner">{_escape(one_liner)}</p>
              <p class="importance">{_escape(importance)}</p>
              <a class="read-link" href="{_escape(item["url"])}" target="_blank">阅读原文</a>
            </article>
            """
        )

    digest_html = (
        _markdown_to_html(digest["content_markdown"])
        if digest
        else "<p>还没有日报草稿。先运行 run-once 生成一份。</p>"
    )

    total = stats["total_articles"] or 0
    ai_count = stats["ai_count"] or 0
    finance_count = stats["finance_count"] or 0
    tech_count = stats["tech_count"] or 0
    last_collected = _format_date(stats["last_collected_at"])
    query_escaped = _escape(query)

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="theme-color" content="#ffffff">
  <title>Yonder Dashboard</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Newsreader:wght@500;600;700&family=Nunito:wght@400;500;600;700;800&display=swap" rel="stylesheet">
  <style>
    :root {{
      color-scheme: light;
      --sky-top: #b9dff2;
      --sky-low: #f7e8bd;
      --grass: #7da873;
      --hill: #bfd29a;
      --panel: rgba(255, 252, 244, 0.88);
      --panel-strong: #fffaf0;
      --text: #243126;
      --muted: #667260;
      --line: rgba(77, 103, 68, 0.22);
      --accent: #2f6f56;
      --accent-deep: #1f4f3d;
      --accent-soft: #e2efd0;
      --gold: #d89a35;
      --clay: #b46b45;
      --shadow: 0 18px 50px rgba(55, 73, 53, 0.16);
    }}
    * {{ box-sizing: border-box; }}
    html {{ min-height: 100%; }}
    body {{
      margin: 0;
      min-height: 100vh;
      overflow-x: hidden;
      font-family: "Nunito", ui-sans-serif, system-ui, sans-serif;
      background:
        radial-gradient(circle at 16% 14%, rgba(255, 238, 168, 0.92) 0 7rem, transparent 7.4rem),
        radial-gradient(ellipse at 18% 88%, rgba(108, 150, 92, 0.42) 0 20rem, transparent 20.5rem),
        radial-gradient(ellipse at 78% 94%, rgba(80, 130, 95, 0.32) 0 25rem, transparent 25.5rem),
        linear-gradient(180deg, var(--sky-top) 0%, #d9edf2 42%, var(--sky-low) 76%, #f5dec0 100%);
      color: var(--text);
    }}
    body::before {{
      content: "";
      position: fixed;
      inset: 0;
      pointer-events: none;
      background:
        radial-gradient(ellipse at 86% 12%, rgba(255,255,255,0.82) 0 4rem, transparent 4.4rem),
        radial-gradient(ellipse at 74% 17%, rgba(255,255,255,0.58) 0 5rem, transparent 5.5rem),
        radial-gradient(ellipse at 9% 72%, rgba(255,255,255,0.32) 0 18rem, transparent 18.6rem),
        linear-gradient(165deg, transparent 0 54%, rgba(126, 164, 101, 0.32) 54.2% 68%, transparent 68.3%),
        linear-gradient(16deg, transparent 0 59%, rgba(181, 151, 94, 0.18) 59.2% 69%, transparent 69.4%);
      mix-blend-mode: soft-light;
    }}
    body::after {{
      content: "";
      position: fixed;
      inset: auto 0 0;
      height: 34vh;
      pointer-events: none;
      background:
        radial-gradient(ellipse at 8% 100%, rgba(56, 112, 73, 0.48) 0 18rem, transparent 18.4rem),
        radial-gradient(ellipse at 52% 108%, rgba(79, 133, 79, 0.38) 0 30rem, transparent 30.5rem),
        radial-gradient(ellipse at 102% 104%, rgba(151, 116, 74, 0.24) 0 18rem, transparent 18.5rem);
      opacity: 0.86;
    }}
    a {{ color: inherit; }}
    header {{
      position: relative;
      z-index: 1;
      max-width: 1280px;
      margin: 0 auto;
      padding: 36px 24px 18px;
      color: var(--text);
    }}
    header h1 {{
      margin: 0;
      font-family: "Newsreader", Georgia, serif;
      font-size: clamp(38px, 6vw, 82px);
      font-weight: 700;
      line-height: 1.15;
      letter-spacing: 0;
    }}
    header p {{
      max-width: 680px;
      margin: 8px 0 0;
      color: #495b45;
      line-height: 1.6;
      font-size: 17px;
    }}
    main {{
      position: relative;
      z-index: 1;
      max-width: 1280px;
      margin: 0 auto;
      padding: 12px 24px 36px;
    }}
    .stats {{
      display: grid;
      grid-template-columns: repeat(5, minmax(120px, 1fr));
      gap: 14px;
      margin-bottom: 20px;
    }}
    .stat {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 15px 16px;
      min-height: 88px;
      box-shadow: 0 10px 28px rgba(77, 92, 61, 0.08);
      backdrop-filter: blur(16px);
    }}
    .stat strong {{
      display: block;
      font-family: "Newsreader", Georgia, serif;
      font-size: 30px;
      line-height: 1.2;
      color: var(--accent-deep);
    }}
    .stat span {{
      display: block;
      color: var(--muted);
      font-size: 13px;
      font-weight: 700;
      margin-top: 6px;
    }}
    .toolbar {{
      display: flex;
      gap: 12px;
      align-items: center;
      justify-content: space-between;
      margin: 20px 0;
      flex-wrap: wrap;
    }}
    .tabs {{
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
    }}
    .tabs a, button {{
      display: inline-flex;
      align-items: center;
      height: 36px;
      padding: 0 14px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: rgba(255, 250, 240, 0.72);
      color: var(--text);
      text-decoration: none;
      font-size: 14px;
      font-weight: 800;
      cursor: pointer;
      box-shadow: 0 8px 22px rgba(77, 92, 61, 0.08);
      transition: transform 180ms ease-out, border-color 180ms ease-out, background 180ms ease-out;
    }}
    .tabs a:hover, button:hover {{
      border-color: rgba(47, 111, 86, 0.5);
      transform: translateY(-1px);
    }}
    .tabs a.active {{
      border-color: var(--accent);
      background: var(--accent-soft);
      color: var(--accent-deep);
    }}
    form {{
      display: flex;
      gap: 8px;
      align-items: center;
    }}
    input {{
      width: min(320px, 68vw);
      height: 36px;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 0 12px;
      font-size: 14px;
      font-family: inherit;
      color: var(--text);
      background: rgba(255, 252, 244, 0.86);
      box-shadow: 0 8px 22px rgba(77, 92, 61, 0.08);
    }}
    input:focus, button:focus, .tabs a:focus, .read-link:focus {{
      outline: 3px solid rgba(216, 154, 53, 0.35);
      outline-offset: 2px;
    }}
    .layout {{
      display: grid;
      grid-template-columns: minmax(0, 1.48fr) minmax(320px, 0.86fr);
      gap: 20px;
      align-items: start;
    }}
    .section-title {{
      margin: 6px 0 12px;
      font-family: "Newsreader", Georgia, serif;
      font-size: 24px;
      font-weight: 700;
      letter-spacing: 0;
    }}
    .items {{
      display: grid;
      gap: 14px;
    }}
    .item-card, .digest-panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: var(--shadow);
      backdrop-filter: blur(18px);
    }}
    .item-card {{
      padding: 18px 19px;
      position: relative;
      overflow: hidden;
      transition: transform 200ms ease-out, box-shadow 200ms ease-out, border-color 200ms ease-out;
    }}
    .item-card::before {{
      content: "";
      position: absolute;
      inset: 0 auto 0 0;
      width: 5px;
      background: linear-gradient(180deg, var(--grass), var(--gold));
      opacity: 0.82;
    }}
    .item-card:hover {{
      transform: translateY(-2px);
      border-color: rgba(47, 111, 86, 0.38);
      box-shadow: 0 22px 56px rgba(55, 73, 53, 0.2);
    }}
    .item-meta {{
      display: flex;
      gap: 10px;
      align-items: center;
      flex-wrap: wrap;
      color: var(--muted);
      font-size: 12px;
      font-weight: 800;
    }}
    .badge {{
      color: var(--accent-deep);
      background: var(--accent-soft);
      border: 1px solid rgba(47, 111, 86, 0.22);
      border-radius: 999px;
      padding: 4px 9px;
    }}
    .source {{
      color: #41553f;
    }}
    .score {{
      color: var(--clay);
    }}
    .item-card h2 {{
      margin: 13px 0 8px;
      font-family: "Newsreader", Georgia, serif;
      font-size: clamp(20px, 2.4vw, 28px);
      line-height: 1.14;
      font-weight: 700;
      letter-spacing: 0;
    }}
    .item-card a {{
      color: #1e4e52;
      text-decoration: none;
    }}
    .item-card a:hover {{ text-decoration: underline; }}
    .one-liner, .importance {{
      margin: 8px 0 0;
      color: #37483a;
      line-height: 1.6;
      font-size: 15px;
    }}
    .importance {{
      color: #596554;
    }}
    .read-link {{
      display: inline-flex;
      align-items: center;
      height: 34px;
      margin-top: 14px;
      padding: 0 12px;
      border: 1px solid rgba(47, 111, 86, 0.22);
      border-radius: 8px;
      background: rgba(226, 239, 208, 0.72);
      color: var(--accent-deep);
      font-size: 13px;
      font-weight: 800;
      cursor: pointer;
      transition: background 180ms ease-out, transform 180ms ease-out;
    }}
    .read-link:hover {{
      background: rgba(226, 239, 208, 0.95);
      transform: translateY(-1px);
    }}
    .digest-panel {{
      position: sticky;
      top: 16px;
      max-height: calc(100vh - 32px);
      overflow: auto;
      padding: 18px;
    }}
    .digest-panel h2 {{
      margin: 0 0 12px;
      font-family: "Newsreader", Georgia, serif;
      font-size: 24px;
      letter-spacing: 0;
    }}
    .digest-content h2 {{
      font-family: "Newsreader", Georgia, serif;
      font-size: 20px;
      margin: 18px 0 10px;
      letter-spacing: 0;
    }}
    .digest-content h3 {{
      font-size: 16px;
      margin: 16px 0 8px;
      color: var(--accent-deep);
    }}
    .digest-content p {{
      color: #3e4f3f;
      font-size: 13px;
      line-height: 1.55;
      margin: 7px 0;
    }}
    .empty {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 22px;
      color: var(--muted);
    }}
    @media (prefers-reduced-motion: reduce) {{
      *, *::before, *::after {{
        animation: none !important;
        transition: none !important;
        scroll-behavior: auto !important;
      }}
    }}
    @media (max-width: 920px) {{
      header {{ padding: 24px 20px; }}
      main {{ padding: 18px; }}
      .stats {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      .layout {{ grid-template-columns: 1fr; }}
      .digest-panel {{ position: static; max-height: none; }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>Yonder</h1>
    <p>AI、金融和科技的每日观察台。温柔一点，锋利一点，把重要信号从信息雾里捞出来。</p>
  </header>
  <main>
    <section class="stats">
      <div class="stat"><strong>{total}</strong><span>总文章</span></div>
      <div class="stat"><strong>{ai_count}</strong><span>AI</span></div>
      <div class="stat"><strong>{finance_count}</strong><span>金融</span></div>
      <div class="stat"><strong>{tech_count}</strong><span>科技</span></div>
      <div class="stat"><strong>{_escape(last_collected)}</strong><span>最近采集</span></div>
    </section>

    <section class="toolbar">
      <nav class="tabs">
        <a class="{_active(valid_channel, '')}" href="/">全部</a>
        <a class="{_active(valid_channel, 'ai')}" href="/?channel=ai">AI</a>
        <a class="{_active(valid_channel, 'finance')}" href="/?channel=finance">金融</a>
        <a class="{_active(valid_channel, 'tech')}" href="/?channel=tech">科技</a>
      </nav>
      <form method="get" action="/">
        <input type="hidden" name="channel" value="{_escape(valid_channel)}">
        <input name="q" value="{query_escaped}" placeholder="搜索标题、来源或摘要">
        <button type="submit">搜索</button>
      </form>
    </section>

    <section class="layout">
      <div>
        <h2 class="section-title">精选内容</h2>
        <div class="items">
          {''.join(cards) if cards else '<div class="empty">暂无内容。先运行采集命令生成数据。</div>'}
        </div>
      </div>
      <aside class="digest-panel">
        <h2>最新日报预览</h2>
        <div class="digest-content">{digest_html}</div>
      </aside>
    </section>
  </main>
</body>
</html>
"""


def render_landing() -> str:
    return """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="theme-color" content="#ffffff">
  <title>今日宜闻 · 乐子入口</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Fredoka:wght@500;600;700&family=Nunito:wght@400;600;700;800&display=swap" rel="stylesheet">
  <style>
    * { box-sizing: border-box; }
    html { background: #fff; }
    html, body { min-height: 100%; }
    body {
      margin: 0;
      overflow: hidden;
      font-family: "Nunito", "PingFang SC", sans-serif;
      color: #f8fdff;
      background: #fff url("/static/assets/scene/pastoral-4k.png") center bottom / cover no-repeat fixed;
    }
    body::before {
      content: "";
      position: fixed;
      inset: 0;
      background:
        radial-gradient(circle at 52% 48%, rgba(255,255,255,.18), transparent 16rem),
        linear-gradient(180deg, rgba(0,0,0,.08), rgba(0, 59, 78, .14));
      pointer-events: none;
    }
    body::after {
      content: "";
      position: fixed;
      inset: 0;
      pointer-events: none;
      background:
        linear-gradient(100deg, transparent 0 18%, rgba(255,255,255,.2) 27%, transparent 36% 100%),
        linear-gradient(100deg, transparent 0 54%, rgba(255,255,255,.12) 59%, transparent 68% 100%);
      mix-blend-mode: screen;
      animation: homeWind 9s ease-in-out infinite;
    }
    .nav {
      position: fixed;
      top: 18px;
      left: 22px;
      right: 22px;
      z-index: 2;
      display: flex;
      align-items: center;
      justify-content: space-between;
      height: 48px;
      padding: 0 4px;
      border: 0;
      background: transparent;
      box-shadow: none;
    }
    .brand {
      position: absolute;
      left: 0;
      font-family: "Fredoka", sans-serif;
      font-size: 25px;
      font-weight: 700;
      text-shadow: 0 2px 18px rgba(0,0,0,.22);
    }
    .nav-right {
      position: absolute;
      left: 50%;
      transform: translateX(-50%);
      display: flex;
      align-items: center;
      gap: 18px;
    }
    .nav-link {
      color: rgba(255,255,255,.94);
      text-decoration: none;
      font-size: 15px;
      font-weight: 900;
      text-shadow: 0 2px 14px rgba(0,0,0,.24);
      transition: transform .18s ease, color .18s ease;
    }
    .nav-link:hover {
      color: #fff;
      transform: translateY(-2px);
    }
    span.nav-link { cursor: default; opacity: .78; }
    span.nav-link:hover { opacity: 1; }
    .bottom-decor {
      position: fixed;
      left: 28px;
      bottom: 24px;
      z-index: 2;
      color: rgba(255,255,255,.9);
      font-weight: 900;
      text-shadow: 0 2px 16px rgba(0,0,0,.26);
      pointer-events: none;
    }
    .bottom-decor .line {
      display: block;
      width: 92px;
      height: 2px;
      margin-bottom: 10px;
      border-radius: 999px;
      background: rgba(255,255,255,.76);
    }
    .bottom-decor p {
      margin: 0;
      max-width: 240px;
      font-size: 14px;
      line-height: 1.7;
    }
    .hero {
      position: relative;
      z-index: 1;
      min-height: 100vh;
      display: grid;
      place-items: center;
      padding: 40px 24px 40px;
      text-align: center;
    }
    .panel {
      width: min(720px, 92vw);
      padding: 0;
      border: 0;
      background: transparent;
      box-shadow: none;
      transform: translateY(-4vh);
    }
    .fun-link {
      display: block;
      margin: 0 0 14px;
      font-family: "Fredoka", sans-serif;
      font-size: clamp(26px, 4vw, 42px);
      line-height: 1;
      letter-spacing: 0;
      color: #fff;
      text-decoration: none;
      text-shadow: 0 6px 28px rgba(0,0,0,.34);
      font-weight: 900;
      cursor: pointer;
      transition: transform .22s ease, text-shadow .22s ease, filter .22s ease;
    }
    .fun-link:hover {
      transform: translateY(-4px) scale(1.025);
      filter: brightness(1.08);
      text-shadow: 0 8px 32px rgba(0,0,0,.36);
    }
    .fun-link:active {
      transform: translateY(-1px) scale(.99);
    }
    .fun-link:focus {
      outline: 3px solid rgba(255,255,255,.62);
      outline-offset: 8px;
      border-radius: 14px;
    }
    .subtitle {
      display: block;
      margin: 0;
      font-family: "Nunito", "PingFang SC", sans-serif;
      font-size: clamp(13px, 1.6vw, 16px);
      font-weight: 500;
      color: rgba(255,255,255,.78);
      text-shadow: 0 2px 12px rgba(0,0,0,.28);
      letter-spacing: .02em;
    }
    .float-actions {
      position: fixed;
      right: 18px;
      bottom: 22px;
      z-index: 3;
      display: grid;
      grid-template-columns: repeat(2, 40px);
      gap: 7px;
      padding: 8px;
      border: 1px solid rgba(255,255,255,.54);
      border-radius: 15px;
      background: rgba(255,255,255,.2);
      backdrop-filter: blur(16px);
      box-shadow: 0 14px 34px rgba(0, 61, 78, .2);
    }
    .float-actions a {
      position: relative;
      width: 40px;
      height: 40px;
      display: grid;
      place-items: center;
      border-radius: 9px;
      color: #0b5a65;
      text-decoration: none;
      font-size: 20px;
      font-weight: 900;
      border: 1px solid rgba(255,255,255,.62);
      background: linear-gradient(145deg, rgba(255,255,255,.68), rgba(229, 255, 244, .34));
      backdrop-filter: blur(14px);
      box-shadow:
        inset 0 1px 0 rgba(255,255,255,.7),
        0 8px 18px rgba(0, 67, 84, .14);
      transition: transform .18s ease, background .18s ease, color .18s ease;
    }
    .float-actions a::after {
      content: attr(aria-label);
      position: absolute;
      right: calc(100% + 10px);
      top: 50%;
      transform: translateY(-50%) translateX(6px);
      opacity: 0;
      white-space: nowrap;
      pointer-events: none;
      padding: 6px 9px;
      border-radius: 9px;
      color: #073f49;
      background: rgba(255,255,255,.82);
      box-shadow: 0 10px 24px rgba(0, 61, 78, .16);
      font-size: 13px;
      font-weight: 900;
      transition: opacity .18s ease, transform .18s ease;
    }
    .float-actions a:hover {
      transform: translateY(-3px);
      color: #073f49;
      background: linear-gradient(145deg, rgba(255,255,255,.82), rgba(210, 255, 240, .5));
    }
    .float-actions a:hover::after,
    .float-actions a:focus::after {
      opacity: 1;
      transform: translateY(-50%) translateX(0);
    }
    .icon-share {
      width: 21px;
      height: 21px;
      fill: none;
      stroke: currentColor;
      stroke-width: 2.4;
      stroke-linecap: round;
      stroke-linejoin: round;
    }
    .home-wind {
      position: fixed;
      inset: 0;
      z-index: 1;
      pointer-events: none;
      overflow: hidden;
    }
    .home-wind i {
      position: absolute;
      left: -20vw;
      width: 150px;
      height: 2px;
      border-radius: 999px;
      background: linear-gradient(90deg, transparent, rgba(255,255,255,.68), transparent);
      animation: homeWindLine 6.2s linear infinite;
    }
    .home-wind i:nth-child(1) { top: 32%; width: 180px; animation-delay: 0s; }
    .home-wind i:nth-child(2) { top: 47%; width: 120px; animation-delay: -2.1s; opacity: .62; }
    .home-wind i:nth-child(3) { top: 64%; width: 210px; animation-delay: -3.7s; opacity: .5; }
    @keyframes homeWind {
      0%, 100% { transform: translateX(-8%); opacity: .28; }
      50% { transform: translateX(10%); opacity: .48; }
    }
    @keyframes homeWindLine {
      from { transform: translateX(0) translateY(0) rotate(-7deg); opacity: 0; }
      15% { opacity: .68; }
      80% { opacity: .42; }
      to { transform: translateX(132vw) translateY(12vh) rotate(-7deg); opacity: 0; }
    }
    @media (max-width: 640px) {
      .nav { left: 12px; right: 12px; height: auto; min-height: 56px; }
      .brand { position: static; font-size: 20px; }
      .nav-right { position: static; transform: none; gap: 10px; }

      .nav-link { font-size: 12px; }
      .bottom-decor { display: none; }
      .fun-link { font-size: clamp(24px, 8vw, 34px); }
      .subtitle { font-size: clamp(12px, 4vw, 15px); }
    }
  </style>
</head>
<body>
  <nav class="nav" aria-label="顶部导航">
    <div class="brand">今日宜闻</div>
    <div class="nav-right">
      <a class="nav-link" href="/">首页</a>
      <a class="nav-link" href="/github">GitHub</a>
      <a class="nav-link" href="/ai">AI</a>
      <a class="nav-link" href="/finance">金融</a>
      <a class="nav-link" href="/music">音乐</a>
      <a class="nav-link" href="/novels">小说</a>
      <a class="nav-link" href="/github#site-footer">小站</a>
    </div>

  </nav>
  <div class="bottom-decor" aria-hidden="true">
    <span class="line"></span>
    <p>今日宜闻<br>适合摸鱼，也适合认真看点新东西。</p>
  </div>
  <main class="hero">
    <section class="panel">
      <a class="fun-link" href="/github">你渴望力量吗？</a>
      <p class="subtitle">获取最新 AI · 科技 · 金融资讯，每日精选，安静阅读。</p>
    </section>
  </main>
  <div class="home-wind" aria-hidden="true"><i></i><i></i><i></i></div>
  <div class="float-actions" aria-label="快捷入口">
    <a href="/github#projects" aria-label="内容" title="内容">◎</a>
    <a href="#" aria-label="分享" title="分享">
      <svg class="icon-share" viewBox="0 0 24 24" aria-hidden="true">
        <circle cx="18" cy="5" r="3"></circle>
        <circle cx="6" cy="12" r="3"></circle>
        <circle cx="18" cy="19" r="3"></circle>
        <path d="M8.6 10.7 15.4 6.3"></path>
        <path d="M8.6 13.3 15.4 17.7"></path>
      </svg>
    </a>
    <a href="/" aria-label="返回顶部" title="返回顶部">↑</a>
    <a href="/github" aria-label="进入内容页" title="进入内容页">↓</a>
  </div>
</body>
</html>
"""


def render_github_demo() -> str:
    github_payload = load_github_projects(ROOT)
    github_projects = github_payload.get("items", [])
    fetched_at = github_payload.get("fetched_at", "时间未知")
    window = github_payload.get("window", "近 3 个月创建 · stars 排序")
    project_cards = []
    project_nav_items = []
    project_payload = []
    covers_dir = ROOT / "static" / "assets" / "github" / "covers"
    section_copy = (
        f"本批展示 GitHub 近三个月新建仓库 Top {len(github_projects)}，按 stars 排序，简介来自仓库原始 description。"
    )
    for index, project in enumerate(github_projects):
        jpg_cover = covers_dir / f"cover-{project['rank']:02d}.jpg"
        if jpg_cover.exists():
            thumb_path = f"/static/assets/github/covers/cover-{project['rank']:02d}.jpg"
        else:
            fallback_rank = ((int(project["rank"]) - 1) % 20) + 1
            thumb_path = f"/static/assets/anime-thumbs/thumb-{fallback_rank:02d}.svg"
        tech_label = " · ".join(project.get("tech", []))
        project_payload.append(
            {
                "rank": project["rank"],
                "name": project["name"],
                "repo": project["repo"],
                "stars": project["stars"],
                "tech": project.get("tech", []),
                "summary": project["summary"],
                "detail": project["detail"],
                "url": project["url"],
                "created_at": project.get("created_at", "时间未知"),
                "thumb": thumb_path,
            }
        )
        project_nav_items.append(
            f"""
            <button type="button" class="project-nav-item" data-project-index="{index}">
              <span class="nav-rank">{project['rank']:02d}</span>
              <span class="nav-name">{_escape(project['name'])}</span>
            </button>
            """
        )
        project_cards.append(
            f"""
            <article id="project-{project['rank']}" class="bili-card">
              <a class="thumb js-project-link" href="#project-{project['rank']}" data-project-index="{index}" aria-label="在站内查看 {_escape(project['name'])}">
                <img src="{thumb_path}" alt="{_escape(project['name'])} 的二次元风格封面" loading="lazy">
                <span class="rank">#{project['rank']:02d}</span>
                <span class="tech-tag">{_escape(tech_label)}</span>
              </a>
              <h2><a class="js-project-link" href="#project-{project['rank']}" data-project-index="{index}"><span class="rank-num">{project['rank']}</span> {_escape(project['name'])}</a></h2>
              <p class="summary">{_escape(_short_cn(project['summary'], 74))}</p>
              <div class="card-meta">
                <span>上架 {_escape(project.get('created_at', '时间未知'))}</span>
                <span>{project['stars']:,} stars</span>
              </div>
            </article>
            """
        )
    project_data_json = json.dumps(project_payload, ensure_ascii=False).replace("</", "<\\/")

    page = """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="theme-color" content="#ffffff">
  <title>今日宜闻 · GitHub 乐子雷达</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Fredoka:wght@500;600;700&family=Nunito:wght@400;600;700;800&display=swap" rel="stylesheet">
  <style>
    :root {
      color-scheme: light;
      --ink: #172b34;
      --muted: #667985;
      --surface: #ffffff;
      --surface-soft: #f6fbfb;
      --line: #ddebed;
      --cyan: #13a8c2;
      --mint: #4fbd82;
      --sun: #f3b85e;
      --shadow: 0 14px 34px rgba(28, 75, 92, .1);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      color: var(--ink);
      font-family: "Nunito", "PingFang SC", sans-serif;
      background: #f5fafb;
    }
    a { color: inherit; }
    .hero-banner {
      position: relative;
      min-height: 188px;
      height: 21vh;
      max-height: 256px;
      overflow: hidden;
      background: url("/static/assets/github/banner.jpg") center 30% / cover no-repeat;
      border-bottom: 1px solid #d5e7e8;
      color: #fff;
    }
    .topbar {
      position: relative;
      z-index: 2;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 22px;
      width: min(1320px, calc(100% - 44px));
      margin: 0 auto;
      padding: 18px 0 0;
      text-shadow: 0 2px 16px rgba(0,0,0,.28);
    }
    .brand {
      font-family: "Fredoka", sans-serif;
      font-size: 25px;
      font-weight: 700;
      text-decoration: none;
      white-space: nowrap;
    }
    .nav-links {
      display: flex;
      gap: 24px;
      align-items: center;
      justify-content: center;
      flex-wrap: wrap;
    }
    .nav-links a, .nav-links span {
      font-size: inherit;
      font-weight: 900;
      text-decoration: none;
      color: inherit;
      transition: transform .2s ease, opacity .2s ease;
    }
    .nav-links a:hover { transform: translateY(-2px); opacity: .82; }
    .nav-links span { opacity: .72; cursor: default; }
    .status {
      font-weight: 900;
      font-size: 14px;
      white-space: nowrap;
    }
    .banner-copy {
      position: relative;
      z-index: 2;
      width: min(1320px, calc(100% - 44px));
      margin: 42px auto 0;
      text-shadow: 0 3px 20px rgba(0,0,0,.28);
    }
    .banner-copy h1 {
      margin: 0;
      font-family: "Fredoka", sans-serif;
      font-size: clamp(28px, 4vw, 48px);
      line-height: 1;
      letter-spacing: 0;
    }
    .banner-copy p {
      margin: 10px 0 0;
      max-width: 900px;
      font-weight: 900;
      line-height: 1.55;
    }
    .feed {
      width: min(1320px, calc(100% - 44px));
      margin: 24px auto 0;
    }
    .feed-head {
      display: grid;
      grid-template-columns: minmax(0, 2fr) minmax(max-content, 1fr);
      gap: 16px;
      align-items: end;
      margin-bottom: 18px;
    }
    .feed-head h2 {
      margin: 0;
      font-family: "Fredoka", sans-serif;
      font-size: clamp(24px, 3vw, 34px);
      color: #132f38;
    }
    .feed-head p {
      margin: 8px 0 0;
      color: var(--muted);
      font-weight: 800;
      line-height: 1.6;
      white-space: nowrap;
    }
    .source-note {
      justify-self: end;
      min-width: max-content;
      color: #316473;
      font-weight: 900;
    }
    .card-grid {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 28px 20px;
    }
    .card-grid[hidden],
    .project-browser[hidden] {
      display: none !important;
    }
    .bili-card {
      position: relative;
      min-width: 0;
    }
    .thumb {
      position: relative;
      display: block;
      aspect-ratio: 16 / 9;
      overflow: hidden;
      border-radius: 10px;
      background: #dff1ef;
      box-shadow: var(--shadow);
      text-decoration: none;
      cursor: pointer;
      transition: transform .22s ease, box-shadow .22s ease, filter .22s ease;
    }
    .thumb::after {
      content: "";
      position: absolute;
      inset: 0;
      background: linear-gradient(180deg, rgba(13, 38, 44, 0) 48%, rgba(13, 38, 44, .5));
      pointer-events: none;
    }
    .thumb img {
      width: 100%;
      height: 100%;
      display: block;
      object-fit: cover;
    }
    .thumb:hover {
      transform: translateY(-3px);
      box-shadow: 0 18px 42px rgba(28, 75, 92, .16);
      filter: saturate(1.06) brightness(1.02);
    }
    .rank,
    .tech-tag {
      position: absolute;
      z-index: 1;
      left: 10px;
      bottom: 10px;
      display: inline-flex;
      align-items: center;
      min-height: 24px;
      padding: 0 8px;
      border-radius: 7px;
      color: #fff;
      background: rgba(16, 39, 48, .52);
      backdrop-filter: blur(10px);
      font-size: 12px;
      font-weight: 900;
    }
    .rank {
      top: 10px;
      bottom: auto;
      background: linear-gradient(90deg, rgba(19, 168, 194, .9), rgba(79, 189, 130, .9));
    }
    .tech-tag {
      right: 10px;
      left: auto;
      max-width: calc(100% - 20px);
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .bili-card h2 {
      margin: 10px 0 0;
      font-family: "Fredoka", sans-serif;
      font-size: 18px;
      line-height: 1.25;
      color: #172b34;
    }
    .bili-card h2 a {
      display: block;
      overflow: hidden;
      text-decoration: none;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .bili-card h2 a:hover { color: var(--cyan); }
    .rank-num {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 24px;
      height: 24px;
      border-radius: 50%;
      background: #316473;
      color: #fff;
      font-size: 13px;
      font-weight: 900;
      vertical-align: middle;
      margin-right: 6px;
    }
    .summary {
      display: -webkit-box;
      min-height: 44px;
      margin: 6px 0 0;
      overflow: hidden;
      -webkit-box-orient: vertical;
      -webkit-line-clamp: 2;
      color: #475b65;
      font-size: 14px;
      font-weight: 800;
      line-height: 1.55;
    }
    .card-meta {
      display: flex;
      justify-content: space-between;
      gap: 10px;
      margin-top: 8px;
      color: #71838c;
      font-size: 13px;
      font-weight: 900;
    }
    .card-meta span {
      min-width: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .project-browser {
      display: grid;
      grid-template-columns: 268px minmax(0, 1fr);
      gap: 18px;
      min-height: 620px;
      height: min(820px, calc(100vh - 292px));
    }
    .browser-sidebar,
    .project-viewer {
      min-width: 0;
      overflow: hidden;
      border: 1px solid #dbe9ea;
      border-radius: 14px;
      background: #fff;
      box-shadow: 0 16px 36px rgba(28, 75, 92, .1);
    }
    .browser-sidebar {
      display: grid;
      grid-template-rows: auto minmax(0, 1fr);
    }
    .browser-actions {
      position: sticky;
      top: 0;
      z-index: 3;
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 9px;
      padding: 12px;
      border-bottom: 1px solid #dbe9ea;
      background:
        linear-gradient(180deg, rgba(255,255,255,.98), rgba(246,251,251,.96)),
        radial-gradient(circle at 20% 0, rgba(79,189,130,.2), transparent 34%);
    }
    .browser-button {
      appearance: none;
      min-height: 38px;
      border: 1px solid #cddfe2;
      border-radius: 10px;
      background: #ffffff;
      color: #244854;
      font: inherit;
      font-size: 13px;
      font-weight: 900;
      cursor: pointer;
      transition: transform .2s ease, border-color .2s ease, box-shadow .2s ease, background .2s ease;
    }
    .browser-button:hover,
    .browser-button:focus-visible {
      transform: translateY(-1px);
      border-color: #8bcfd6;
      background: #f3fbfb;
      box-shadow: 0 8px 18px rgba(28,75,92,.1);
      outline: none;
    }
    .browser-button.return {
      grid-column: 1 / -1;
      color: #fff;
      border-color: #176d81;
      background: linear-gradient(135deg, #176d81, #4fbd82);
    }
    .project-nav-list {
      min-height: 0;
      overflow-y: auto;
      padding: 8px;
      scrollbar-color: #9cced4 #eff7f8;
    }
    .project-nav-item {
      appearance: none;
      width: 100%;
      min-height: 44px;
      display: grid;
      grid-template-columns: 36px minmax(0, 1fr);
      align-items: center;
      gap: 9px;
      margin: 0;
      padding: 7px 8px;
      border: 0;
      border-radius: 10px;
      background: transparent;
      color: #365b66;
      font: inherit;
      text-align: left;
      cursor: pointer;
      transition: background .18s ease, color .18s ease, transform .18s ease;
    }
    .project-nav-item + .project-nav-item {
      margin-top: 3px;
    }
    .project-nav-item:hover,
    .project-nav-item:focus-visible {
      background: #eef8f8;
      color: #12323b;
      outline: none;
      transform: translateX(2px);
    }
    .project-nav-item.is-active {
      color: #102d36;
      background: linear-gradient(90deg, rgba(19,168,194,.16), rgba(79,189,130,.15));
      box-shadow: inset 3px 0 0 #13a8c2;
    }
    .nav-rank {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 30px;
      height: 30px;
      border-radius: 8px;
      background: #e3f2f3;
      color: #176d81;
      font-size: 12px;
      font-weight: 900;
    }
    .project-nav-item.is-active .nav-rank {
      color: #fff;
      background: #176d81;
    }
    .nav-name {
      min-width: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      font-size: 13px;
      font-weight: 900;
    }
    .project-viewer {
      display: grid;
      grid-template-rows: auto minmax(0, 1fr);
    }
    .viewer-toolbar {
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 16px;
      align-items: center;
      padding: 14px 16px;
      border-bottom: 1px solid #dbe9ea;
      background: #fff;
    }
    .viewer-title {
      min-width: 0;
    }
    .viewer-title h3 {
      margin: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      color: #142f38;
      font-family: "Fredoka", sans-serif;
      font-size: 20px;
      letter-spacing: 0;
    }
    .viewer-title p {
      margin: 5px 0 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      color: #647b84;
      font-size: 13px;
      font-weight: 900;
    }
    .external-link {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-height: 36px;
      padding: 0 13px;
      border: 1px solid #cddfe2;
      border-radius: 10px;
      color: #176d81;
      background: #f8fcfc;
      font-size: 13px;
      font-weight: 900;
      text-decoration: none;
      white-space: nowrap;
      transition: transform .2s ease, background .2s ease, border-color .2s ease;
    }
    .external-link:hover,
    .external-link:focus-visible {
      transform: translateY(-1px);
      border-color: #8bcfd6;
      background: #eef8f8;
      outline: none;
    }
    .frame-wrap {
      position: relative;
      min-height: 0;
      overflow: hidden;
      background: #f8fbfb;
    }
    .project-frame[hidden],
    .project-profile[hidden] {
      display: none !important;
    }
    .project-frame {
      width: 100%;
      height: 100%;
      min-height: 520px;
      display: block;
      border: 0;
      background: #fff;
    }
    .frame-fallback {
      position: absolute;
      right: 18px;
      bottom: 18px;
      z-index: 2;
      width: min(420px, calc(100% - 36px));
      padding: 14px 16px;
      border: 1px solid rgba(205,223,226,.9);
      border-radius: 14px;
      color: #244854;
      background: rgba(255,255,255,.94);
      box-shadow: 0 16px 34px rgba(28, 75, 92, .16);
      opacity: 0;
      transform: translateY(8px);
      pointer-events: none;
      transition: opacity .22s ease, transform .22s ease;
    }
    .frame-fallback.is-visible {
      opacity: 1;
      transform: translateY(0);
      pointer-events: auto;
    }
    .frame-fallback strong {
      display: block;
      color: #12323b;
      font-size: 14px;
      font-weight: 900;
    }
    .frame-fallback p {
      margin: 6px 0 10px;
      color: #516b74;
      font-size: 13px;
      font-weight: 800;
      line-height: 1.55;
    }
    .frame-fallback a {
      color: #176d81;
      font-weight: 900;
      text-decoration: none;
    }
    .project-profile {
      height: 100%;
      min-height: 520px;
      overflow-y: auto;
      padding: 24px;
      background:
        linear-gradient(135deg, rgba(255,255,255,.96), rgba(245,251,251,.94)),
        radial-gradient(circle at 100% 0, rgba(19,168,194,.14), transparent 32%),
        radial-gradient(circle at 0 100%, rgba(79,189,130,.12), transparent 28%);
    }
    .profile-hero {
      display: grid;
      grid-template-columns: minmax(280px, 44%) minmax(0, 1fr);
      gap: 24px;
      align-items: stretch;
    }
    .profile-cover {
      position: relative;
      overflow: hidden;
      min-height: 300px;
      border-radius: 16px;
      background: #dff1ef;
      box-shadow: 0 18px 42px rgba(28,75,92,.14);
    }
    .profile-cover img {
      width: 100%;
      height: 100%;
      display: block;
      object-fit: cover;
    }
    .profile-cover::after {
      content: "";
      position: absolute;
      inset: 0;
      background: linear-gradient(180deg, transparent 42%, rgba(15,45,54,.5));
    }
    .profile-rank {
      position: absolute;
      left: 14px;
      top: 14px;
      z-index: 1;
      display: inline-flex;
      align-items: center;
      min-height: 30px;
      padding: 0 10px;
      border-radius: 10px;
      color: #fff;
      background: linear-gradient(90deg, rgba(19,168,194,.92), rgba(79,189,130,.92));
      font-size: 13px;
      font-weight: 900;
    }
    .profile-content {
      display: flex;
      flex-direction: column;
      justify-content: center;
      min-width: 0;
      padding: 8px 2px;
    }
    .profile-kicker {
      margin: 0 0 10px;
      color: #176d81;
      font-size: 13px;
      font-weight: 900;
      letter-spacing: 0;
    }
    .profile-content h4 {
      margin: 0;
      color: #102d36;
      font-family: "Fredoka", sans-serif;
      font-size: clamp(30px, 4vw, 54px);
      line-height: 1.02;
      letter-spacing: 0;
    }
    .profile-repo {
      margin: 10px 0 0;
      color: #5d7580;
      font-size: 15px;
      font-weight: 900;
      word-break: break-word;
    }
    .profile-summary {
      margin: 18px 0 0;
      color: #244854;
      font-size: 18px;
      font-weight: 900;
      line-height: 1.7;
    }
    .profile-stats {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 20px;
    }
    .profile-stat,
    .profile-chip {
      display: inline-flex;
      align-items: center;
      min-height: 32px;
      padding: 0 11px;
      border: 1px solid #d3e5e7;
      border-radius: 999px;
      color: #315c68;
      background: rgba(255,255,255,.72);
      font-size: 13px;
      font-weight: 900;
    }
    .profile-tech {
      display: flex;
      flex-wrap: wrap;
      gap: 9px;
      margin-top: 14px;
    }
    .profile-chip {
      color: #176d81;
      border-color: rgba(19,168,194,.22);
      background: rgba(231,247,248,.82);
    }
    .profile-detail {
      margin-top: 24px;
      padding: 22px;
      border: 1px solid #dbe9ea;
      border-radius: 16px;
      background: rgba(255,255,255,.74);
    }
    .profile-detail h5 {
      margin: 0 0 10px;
      color: #14313b;
      font-size: 17px;
      font-weight: 900;
    }
    .profile-detail p {
      margin: 0;
      color: #496670;
      font-size: 15px;
      font-weight: 800;
      line-height: 1.85;
    }
    .profile-actions {
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      margin-top: 22px;
    }
    .profile-open,
    .profile-note {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-height: 40px;
      padding: 0 15px;
      border-radius: 11px;
      font-size: 13px;
      font-weight: 900;
    }
    .profile-open {
      color: #fff;
      background: linear-gradient(135deg, #176d81, #4fbd82);
      text-decoration: none;
      box-shadow: 0 12px 24px rgba(23,109,129,.18);
    }
    .profile-note {
      color: #55717b;
      border: 1px dashed #c8dde0;
      background: rgba(255,255,255,.72);
    }
    .poem {
      width: min(1320px, calc(100% - 44px));
      margin: 44px auto 30px;
      text-align: center;
      color: #607680;
      font-weight: 900;
    }
    @media (max-width: 1120px) {
      .card-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
      .project-browser { grid-template-columns: 238px minmax(0, 1fr); }
    }
    @media (max-width: 820px) {
      .hero-banner { height: 240px; }
      .topbar {
        width: min(100% - 28px, 1320px);
        align-items: flex-start;
        flex-direction: column;
        gap: 12px;
      }
      .nav-links { gap: 16px; }
      .status { display: none; }
      .banner-copy {
        width: min(100% - 28px, 1320px);
        margin-top: 28px;
      }
      .feed { width: min(100% - 28px, 1320px); }
      .feed-head { grid-template-columns: 1fr; }
      .feed-head p {
        max-width: 100%;
        white-space: normal;
      }
      .source-note { justify-self: start; }
      .card-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 22px 14px; }
      .project-browser {
        grid-template-columns: 1fr;
        height: auto;
        min-height: 0;
        max-height: none;
      }
      .browser-sidebar {
        max-height: 360px;
      }
      .project-frame {
        height: 68vh;
      }
      .project-profile {
        min-height: 0;
      }
      .profile-hero {
        grid-template-columns: 1fr;
      }
      .viewer-toolbar {
        grid-template-columns: 1fr;
      }
    }
    @media (max-width: 540px) {
      .nav-links { width: 100%; justify-content: space-between; }
      .card-grid { grid-template-columns: 1fr; }
      .card-meta { font-size: 12px; }
      .browser-actions { grid-template-columns: 1fr; }
      .browser-button.return { grid-column: auto; }
      .viewer-title h3 { white-space: normal; }
      .viewer-title p { white-space: normal; }
    }
    @media (prefers-reduced-motion: reduce) {
      *, *::before, *::after { transition: none !important; animation: none !important; }
    }
  </style>
</head>
<body>
  <header class="hero-banner">
    <nav class="topbar" aria-label="顶部导航">
      <a class="brand" href="/">今日宜闻</a>
      <div class="nav-links">
        <a href="/">首页</a>
        <a href="#projects">GitHub</a>
        <a href="/ai">AI</a>
        <a href="/finance">金融</a>
        <a href="/music">音乐</a>
        <a href="/novels">小说</a>
        <a href="#site-footer">小站</a>
      </div>
      <div class="status">近 3 个月 · Top __PROJECT_COUNT__</div>
    </nav>
    <section class="banner-copy">
      <h1>GitHub 乐子雷达</h1>
      <p>最近三个月创建、按星数排序的热门项目 Top __PROJECT_COUNT__。适合快速扫一眼今天开源圈又在整什么活。</p>
    </section>
  </header>

  <main id="projects" class="feed">
    <header class="feed-head">
      <div>
        <h2>热门项目</h2>
        <p>__PROJECT_COPY__</p>
      </div>
      <div class="source-note">GitHub · __FETCHED__</div>
    </header>
    <section class="card-grid" data-project-grid aria-label="GitHub 热门项目">
      __PROJECT_CARDS__
    </section>
    <section class="project-browser" data-project-browser hidden aria-label="GitHub 项目站内浏览器">
      <aside class="browser-sidebar" aria-label="项目导航">
        <div class="browser-actions">
          <button type="button" class="browser-button" data-browser-prev>上一个</button>
          <button type="button" class="browser-button" data-browser-next>下一个</button>
          <button type="button" class="browser-button return" data-browser-home>返回主页</button>
        </div>
        <div class="project-nav-list" aria-label="32 个 GitHub 项目">
          __PROJECT_NAV__
        </div>
      </aside>
      <section class="project-viewer" aria-live="polite">
        <header class="viewer-toolbar">
          <div class="viewer-title">
            <h3 data-viewer-title>选择一个项目</h3>
            <p data-viewer-meta>左侧选择项目后会在这里载入对应页面</p>
          </div>
          <a class="external-link" data-viewer-link href="https://github.com" target="_blank" rel="noopener noreferrer">打开原站</a>
        </header>
        <div class="frame-wrap">
          <iframe class="project-frame" data-project-frame title="GitHub 项目页面" referrerpolicy="no-referrer-when-downgrade"></iframe>
          <article class="project-profile" data-project-profile hidden>
            <div class="profile-hero">
              <figure class="profile-cover">
                <img data-profile-thumb src="" alt="">
                <span class="profile-rank" data-profile-rank></span>
              </figure>
              <div class="profile-content">
                <p class="profile-kicker">GitHub 项目档案</p>
                <h4 data-profile-name></h4>
                <p class="profile-repo" data-profile-repo></p>
                <p class="profile-summary" data-profile-summary></p>
                <div class="profile-stats">
                  <span class="profile-stat" data-profile-stars></span>
                  <span class="profile-stat" data-profile-date></span>
                </div>
                <div class="profile-tech" data-profile-tech></div>
                <div class="profile-actions">
                  <a class="profile-open" data-profile-link href="https://github.com" target="_blank" rel="noopener noreferrer">打开 GitHub 原站</a>
                  <span class="profile-note">GitHub 禁止 iframe 嵌入，这里显示站内阅读版</span>
                </div>
              </div>
            </div>
            <section class="profile-detail">
              <h5>为什么值得看</h5>
              <p data-profile-detail></p>
            </section>
          </article>
          <div class="frame-fallback" data-frame-fallback>
            <strong data-fallback-title>外部页面可能禁止嵌入</strong>
            <p data-fallback-copy>如果右侧没有显示内容，可以使用原站链接查看。项目摘要仍保留在卡片列表里。</p>
            <a data-fallback-link href="https://github.com" target="_blank" rel="noopener noreferrer">打开原站 →</a>
          </div>
        </div>
      </section>
    </section>
  </main>

  <footer id="site-footer" class="poem">海阔凭鱼跃，天高任鸟飞。</footer>
  <script>
    (() => {
      const projects = __PROJECT_DATA__;
      const feed = document.querySelector("#projects");
      const grid = document.querySelector("[data-project-grid]");
      const browser = document.querySelector("[data-project-browser]");
      const frame = document.querySelector("[data-project-frame]");
      const title = document.querySelector("[data-viewer-title]");
      const meta = document.querySelector("[data-viewer-meta]");
      const externalLink = document.querySelector("[data-viewer-link]");
      const profile = document.querySelector("[data-project-profile]");
      const profileThumb = document.querySelector("[data-profile-thumb]");
      const profileRank = document.querySelector("[data-profile-rank]");
      const profileName = document.querySelector("[data-profile-name]");
      const profileRepo = document.querySelector("[data-profile-repo]");
      const profileSummary = document.querySelector("[data-profile-summary]");
      const profileStars = document.querySelector("[data-profile-stars]");
      const profileDate = document.querySelector("[data-profile-date]");
      const profileTech = document.querySelector("[data-profile-tech]");
      const profileLink = document.querySelector("[data-profile-link]");
      const profileDetail = document.querySelector("[data-profile-detail]");
      const fallback = document.querySelector("[data-frame-fallback]");
      const fallbackTitle = document.querySelector("[data-fallback-title]");
      const fallbackCopy = document.querySelector("[data-fallback-copy]");
      const fallbackLink = document.querySelector("[data-fallback-link]");
      const navItems = [...document.querySelectorAll(".project-nav-item")];
      let currentIndex = -1;
      let fallbackTimer = 0;
      let currentFrameLikelyBlocked = false;

      const formatStars = (value) => Number(value || 0).toLocaleString("zh-CN");

      const isLikelyBlockedFrame = (url) => {
        try {
          const hostname = new URL(url).hostname;
          return hostname === "github.com" || hostname.endsWith(".github.com");
        } catch {
          return false;
        }
      };

      const renderProfile = (project) => {
        profileThumb.src = project.thumb;
        profileThumb.alt = `${project.name} 的项目封面`;
        profileRank.textContent = `#${String(project.rank).padStart(2, "0")}`;
        profileName.textContent = project.name;
        profileRepo.textContent = project.repo;
        profileSummary.textContent = project.summary;
        profileStars.textContent = `${formatStars(project.stars)} stars`;
        profileDate.textContent = `上架 ${project.created_at}`;
        profileLink.href = project.url;
        profileDetail.textContent = project.detail;
        profileTech.replaceChildren();
        project.tech.forEach((tech) => {
          const chip = document.createElement("span");
          chip.className = "profile-chip";
          chip.textContent = tech;
          profileTech.appendChild(chip);
        });
      };

      const indexFromHash = () => {
        const match = window.location.hash.match(/^#project-(\\d+)$/);
        if (!match) return -1;
        const rank = Number(match[1]);
        return projects.findIndex((project) => Number(project.rank) === rank);
      };

      const syncActiveNav = (index) => {
        navItems.forEach((item) => {
          const active = Number(item.dataset.projectIndex) === index;
          item.classList.toggle("is-active", active);
          item.setAttribute("aria-current", active ? "true" : "false");
          if (active) item.scrollIntoView({ block: "nearest" });
        });
      };

      const showFallbackLater = (project) => {
        window.clearTimeout(fallbackTimer);
        fallback.classList.remove("is-visible");
        currentFrameLikelyBlocked = isLikelyBlockedFrame(project.url);
        fallbackTitle.textContent = `${project.name} 可能无法嵌入`;
        fallbackCopy.textContent = project.detail;
        fallbackLink.href = project.url;
        fallbackTimer = window.setTimeout(() => {
          fallback.classList.add("is-visible");
        }, currentFrameLikelyBlocked ? 700 : 2200);
      };

      const openProject = (index, pushHistory = true) => {
        const project = projects[index];
        if (!project) returnHome(pushHistory);
        currentIndex = index;
        grid.hidden = true;
        browser.hidden = false;
        feed.classList.add("is-viewing");
        title.textContent = `${project.rank}. ${project.name}`;
        meta.textContent = `${project.repo} · ${formatStars(project.stars)} stars · ${project.tech.join(" / ")}`;
        externalLink.href = project.url;
        externalLink.textContent = "打开原站";
        frame.title = `${project.name} 项目页面`;
        currentFrameLikelyBlocked = isLikelyBlockedFrame(project.url);
        if (currentFrameLikelyBlocked) {
          frame.hidden = true;
          frame.removeAttribute("src");
          fallback.classList.remove("is-visible");
          window.clearTimeout(fallbackTimer);
          renderProfile(project);
          profile.hidden = false;
        } else {
          profile.hidden = true;
          frame.hidden = false;
          frame.removeAttribute("src");
          requestAnimationFrame(() => {
            frame.src = project.url;
          });
          showFallbackLater(project);
        }
        syncActiveNav(index);
        if (pushHistory) {
          history.pushState({ projectIndex: index }, "", `#project-${project.rank}`);
        }
        browser.scrollIntoView({ block: "start", behavior: "smooth" });
      };

      function returnHome(pushHistory = true) {
        currentIndex = -1;
        grid.hidden = false;
        browser.hidden = true;
        feed.classList.remove("is-viewing");
        frame.removeAttribute("src");
        frame.hidden = false;
        profile.hidden = true;
        fallback.classList.remove("is-visible");
        window.clearTimeout(fallbackTimer);
        syncActiveNav(-1);
        if (pushHistory) {
          history.pushState({}, "", window.location.pathname);
        }
        feed.scrollIntoView({ block: "start", behavior: "smooth" });
      }

      document.querySelectorAll(".js-project-link").forEach((link) => {
        link.addEventListener("click", (event) => {
          event.preventDefault();
          openProject(Number(link.dataset.projectIndex));
        });
      });

      navItems.forEach((item) => {
        item.addEventListener("click", () => {
          openProject(Number(item.dataset.projectIndex));
        });
      });

      document.querySelector("[data-browser-prev]").addEventListener("click", () => {
        if (currentIndex <= 0) returnHome();
        else openProject(currentIndex - 1);
      });

      document.querySelector("[data-browser-next]").addEventListener("click", () => {
        if (currentIndex < 0 || currentIndex >= projects.length - 1) returnHome();
        else openProject(currentIndex + 1);
      });

      document.querySelector("[data-browser-home]").addEventListener("click", () => {
        returnHome();
      });

      frame.addEventListener("load", () => {
        if (currentFrameLikelyBlocked) return;
        window.clearTimeout(fallbackTimer);
        fallback.classList.remove("is-visible");
      });

      window.addEventListener("popstate", () => {
        const index = indexFromHash();
        if (index >= 0) openProject(index, false);
        else returnHome(false);
      });

      const initialIndex = indexFromHash();
      if (initialIndex >= 0) {
        openProject(initialIndex, false);
      }
    })();
  </script>
</body>
</html>
"""
    return (
        page.replace("__PROJECT_CARDS__", "".join(project_cards))
        .replace("__PROJECT_NAV__", "".join(project_nav_items))
        .replace("__PROJECT_DATA__", project_data_json)
        .replace("__FETCHED__", _escape(fetched_at))
        .replace("__PROJECT_COUNT__", str(len(github_projects)))
        .replace("__PROJECT_COPY__", _escape(section_copy))
    )


def _reader_nav(active_path: str) -> str:
    links = [
        ("/", "首页"),
        ("/github", "GitHub"),
        ("/ai", "AI"),
        ("/finance", "金融"),
        ("/music", "音乐"),
        ("/novels", "小说"),
    ]
    return "".join(
        f'<a class="{"is-current" if href == active_path else ""}" href="{href}">{label}</a>'
        for href, label in links
    ) + '<a href="#site-footer">小站</a>'


def _render_reader_channel(
    *,
    slug: str,
    active_path: str,
    title: str,
    page_title: str,
    subtitle: str,
    section_title: str,
    section_copy: str,
    status: str,
    banner: str,
    poem: str,
    items,
) -> str:
    cards = []
    nav_items = []
    payload = []
    for index, item in enumerate(items):
        rank = item["rank"]
        thumb = item["thumb"]
        payload.append(item)
        nav_items.append(
            f"""
            <button type="button" class="reader-nav-item" data-reader-index="{index}">
              <span>{rank:02d}</span>
              <b>{_escape(item["title"])}</b>
            </button>"""
        )
        cards.append(
            f"""
            <article id="{slug}-{rank}" class="reader-card">
              <a class="reader-thumb js-reader-link" href="#item-{rank}" data-reader-index="{index}" aria-label="站内阅读 {_escape(item["title"])}">
                <img src="{_escape(thumb)}" alt="{_escape(item["title"])} 的频道封面" loading="lazy">
                <span>{_escape(item["category"])}</span>
              </a>
              <h2><a class="js-reader-link" href="#item-{rank}" data-reader-index="{index}"><i>{rank}</i>{_escape(item["title"])}</a></h2>
              <p>{_escape(item["summary"])}</p>
              <div class="reader-card-meta">
                <span>{_escape(item["source"])}</span>
                <span>{_escape(item["date"])}</span>
              </div>
            </article>"""
        )

    item_json = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    page = """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="theme-color" content="#ffffff">
  <title>今日宜闻 · __PAGE_TITLE__</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Fredoka:wght@500;600;700&family=Nunito:wght@400;600;700;800&display=swap" rel="stylesheet">
  <style>
    :root {
      color-scheme: light;
      --ink: #172b34;
      --muted: #667985;
      --cyan: #176d81;
      --mint: #4fbd82;
      --line: #dbe9ea;
      --surface: #ffffff;
      --shadow: 0 14px 34px rgba(28, 75, 92, .1);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      color: var(--ink);
      font-family: "Nunito", "PingFang SC", sans-serif;
      background: #f5fafb;
    }
    a { color: inherit; }
    .hero-banner {
      min-height: 188px;
      height: 21vh;
      max-height: 256px;
      overflow: hidden;
      color: #fff;
      background: url("__BANNER__") center 35% / cover no-repeat;
      border-bottom: 1px solid #d5e7e8;
    }
    .topbar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 22px;
      width: min(1320px, calc(100% - 44px));
      margin: 0 auto;
      padding-top: 18px;
      text-shadow: 0 2px 16px rgba(0,0,0,.28);
    }
    .brand {
      font-family: "Fredoka", sans-serif;
      font-size: 25px;
      font-weight: 700;
      text-decoration: none;
      white-space: nowrap;
    }
    .nav-links {
      display: flex;
      gap: 22px;
      align-items: center;
      justify-content: center;
      flex-wrap: wrap;
    }
    .nav-links a {
      font-weight: 900;
      text-decoration: none;
      transition: transform .2s ease, opacity .2s ease;
    }
    .nav-links a:hover,
    .nav-links .is-current {
      transform: translateY(-2px);
      opacity: .84;
    }
    .status {
      font-size: 14px;
      font-weight: 900;
      white-space: nowrap;
    }
    .banner-copy {
      width: min(1320px, calc(100% - 44px));
      margin: 42px auto 0;
      text-shadow: 0 3px 20px rgba(0,0,0,.28);
    }
    .banner-copy h1 {
      margin: 0;
      font-family: "Fredoka", sans-serif;
      font-size: clamp(28px, 4vw, 48px);
      line-height: 1;
      letter-spacing: 0;
    }
    .banner-copy p {
      margin: 10px 0 0;
      max-width: 920px;
      font-weight: 900;
      line-height: 1.55;
    }
    .reader-feed {
      width: min(1320px, calc(100% - 44px));
      margin: 24px auto 0;
      padding-bottom: 30px;
    }
    .reader-head {
      display: grid;
      grid-template-columns: minmax(0, 2fr) minmax(max-content, 1fr);
      gap: 18px;
      align-items: end;
      margin-bottom: 22px;
    }
    .reader-head h2 {
      margin: 0;
      color: #132f38;
      font-family: "Fredoka", sans-serif;
      font-size: clamp(24px, 3vw, 34px);
    }
    .reader-head p {
      margin: 8px 0 0;
      color: var(--muted);
      font-weight: 800;
      line-height: 1.6;
      white-space: nowrap;
    }
    .reader-source-note {
      color: #316473;
      font-weight: 900;
      white-space: nowrap;
    }
    .reader-grid {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 28px 20px;
    }
    .reader-grid[hidden],
    .reader-browser[hidden] { display: none !important; }
    .reader-card { min-width: 0; }
    .reader-thumb {
      position: relative;
      display: block;
      aspect-ratio: 16 / 9;
      overflow: hidden;
      border-radius: 10px;
      background: #dff1ef;
      box-shadow: var(--shadow);
      cursor: pointer;
      text-decoration: none;
      transition: transform .22s ease, box-shadow .22s ease, filter .22s ease;
    }
    .reader-thumb::after {
      content: "";
      position: absolute;
      inset: 0;
      background: linear-gradient(180deg, rgba(13,38,44,0) 48%, rgba(13,38,44,.5));
      pointer-events: none;
    }
    .reader-thumb img {
      width: 100%;
      height: 100%;
      display: block;
      object-fit: cover;
    }
    .reader-thumb span {
      position: absolute;
      z-index: 1;
      right: 10px;
      top: 10px;
      max-width: calc(100% - 20px);
      min-height: 24px;
      padding: 3px 10px;
      border-radius: 7px;
      color: #fff;
      background: rgba(23,109,129,.82);
      backdrop-filter: blur(8px);
      font-size: 11px;
      font-weight: 900;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .reader-thumb:hover {
      transform: translateY(-3px);
      box-shadow: 0 18px 42px rgba(28,75,92,.16);
      filter: saturate(1.06) brightness(1.02);
    }
    .reader-card h2 {
      margin: 10px 0 0;
      font-size: clamp(14px, 1.3vw, 16px);
      font-weight: 900;
      line-height: 1.45;
    }
    .reader-card h2 a {
      display: block;
      min-width: 0;
      overflow: hidden;
      gap: 7px;
      text-decoration: none;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .reader-card h2 a:hover { color: var(--cyan); }
    .reader-card h2 i {
      flex: 0 0 auto;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 24px;
      height: 24px;
      border-radius: 50%;
      color: #fff;
      background: #316473;
      font-size: 13px;
      font-style: normal;
      font-weight: 900;
      vertical-align: middle;
      margin-right: 7px;
    }
    .reader-card p {
      display: -webkit-box;
      min-height: 44px;
      margin: 6px 0 0;
      overflow: hidden;
      -webkit-box-orient: vertical;
      -webkit-line-clamp: 2;
      color: #475b65;
      font-size: 14px;
      font-weight: 800;
      line-height: 1.55;
    }
    .reader-card-meta {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      margin-top: 7px;
      color: #738f99;
      font-size: 12px;
      font-weight: 900;
    }
    .reader-card-meta span {
      min-width: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .reader-browser {
      display: grid;
      grid-template-columns: 268px minmax(0, 1fr);
      gap: 18px;
      min-height: 620px;
      height: min(820px, calc(100vh - 292px));
    }
    .reader-sidebar,
    .reader-viewer {
      min-width: 0;
      overflow: hidden;
      border: 1px solid var(--line);
      border-radius: 14px;
      background: var(--surface);
      box-shadow: var(--shadow);
    }
    .reader-sidebar {
      display: grid;
      grid-template-rows: auto minmax(0, 1fr);
    }
    .reader-actions {
      position: sticky;
      top: 0;
      z-index: 2;
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 9px;
      padding: 12px;
      border-bottom: 1px solid var(--line);
      background: linear-gradient(180deg, rgba(255,255,255,.98), rgba(246,251,251,.96));
    }
    .reader-button {
      appearance: none;
      min-height: 38px;
      border: 1px solid #cddfe2;
      border-radius: 10px;
      color: #244854;
      background: #fff;
      font: inherit;
      font-size: 13px;
      font-weight: 900;
      cursor: pointer;
      transition: transform .2s ease, border-color .2s ease, box-shadow .2s ease, background .2s ease;
    }
    .reader-button:hover,
    .reader-button:focus-visible {
      transform: translateY(-1px);
      border-color: #8bcfd6;
      background: #f3fbfb;
      box-shadow: 0 8px 18px rgba(28,75,92,.1);
      outline: none;
    }
    .reader-button.return {
      grid-column: 1 / -1;
      color: #fff;
      border-color: #176d81;
      background: linear-gradient(135deg, #176d81, #4fbd82);
    }
    .reader-nav-list {
      min-height: 0;
      overflow-y: auto;
      padding: 8px;
      scrollbar-color: #9cced4 #eff7f8;
    }
    .reader-nav-item {
      appearance: none;
      width: 100%;
      min-height: 44px;
      display: grid;
      grid-template-columns: 36px minmax(0, 1fr);
      align-items: center;
      gap: 9px;
      padding: 7px 8px;
      border: 0;
      border-radius: 10px;
      color: #365b66;
      background: transparent;
      font: inherit;
      text-align: left;
      cursor: pointer;
      transition: background .18s ease, color .18s ease, transform .18s ease;
    }
    .reader-nav-item + .reader-nav-item { margin-top: 3px; }
    .reader-nav-item:hover,
    .reader-nav-item:focus-visible {
      color: #12323b;
      background: #eef8f8;
      outline: none;
      transform: translateX(2px);
    }
    .reader-nav-item.is-active {
      color: #102d36;
      background: linear-gradient(90deg, rgba(19,168,194,.16), rgba(79,189,130,.15));
      box-shadow: inset 3px 0 0 #13a8c2;
    }
    .reader-nav-item span {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 30px;
      height: 30px;
      border-radius: 8px;
      color: #176d81;
      background: #e3f2f3;
      font-size: 12px;
      font-weight: 900;
    }
    .reader-nav-item.is-active span {
      color: #fff;
      background: #176d81;
    }
    .reader-nav-item b {
      min-width: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      font-size: 13px;
      font-weight: 900;
    }
    .reader-viewer {
      display: grid;
      grid-template-rows: auto minmax(0, 1fr);
    }
    .reader-toolbar {
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 16px;
      align-items: center;
      padding: 14px 16px;
      border-bottom: 1px solid var(--line);
      background: #fff;
    }
    .reader-toolbar h3 {
      margin: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      color: #142f38;
      font-family: "Fredoka", sans-serif;
      font-size: 20px;
      letter-spacing: 0;
    }
    .reader-toolbar p {
      margin: 5px 0 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      color: #647b84;
      font-size: 13px;
      font-weight: 900;
    }
    .reader-open {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-height: 36px;
      padding: 0 13px;
      border: 1px solid #cddfe2;
      border-radius: 10px;
      color: #176d81;
      background: #f8fcfc;
      font-size: 13px;
      font-weight: 900;
      text-decoration: none;
      white-space: nowrap;
    }
    .reader-detail {
      min-height: 0;
      overflow-y: auto;
      padding: 24px;
      background:
        linear-gradient(135deg, rgba(255,255,255,.96), rgba(245,251,251,.94)),
        radial-gradient(circle at 100% 0, rgba(19,168,194,.14), transparent 32%),
        radial-gradient(circle at 0 100%, rgba(79,189,130,.12), transparent 28%);
    }
    .detail-hero {
      display: grid;
      grid-template-columns: minmax(280px, 44%) minmax(0, 1fr);
      gap: 24px;
      align-items: stretch;
    }
    .detail-cover {
      position: relative;
      min-height: 300px;
      overflow: hidden;
      margin: 0;
      border-radius: 16px;
      background: #dff1ef;
      box-shadow: 0 18px 42px rgba(28,75,92,.14);
    }
    .detail-cover img {
      width: 100%;
      height: 100%;
      display: block;
      object-fit: cover;
    }
    .detail-cover::after {
      content: "";
      position: absolute;
      inset: 0;
      background: linear-gradient(180deg, transparent 42%, rgba(15,45,54,.5));
    }
    .detail-rank {
      position: absolute;
      z-index: 1;
      left: 14px;
      top: 14px;
      display: inline-flex;
      align-items: center;
      min-height: 30px;
      padding: 0 10px;
      border-radius: 10px;
      color: #fff;
      background: linear-gradient(90deg, rgba(19,168,194,.92), rgba(79,189,130,.92));
      font-size: 13px;
      font-weight: 900;
    }
    .detail-copy {
      display: flex;
      flex-direction: column;
      justify-content: center;
      min-width: 0;
      padding: 8px 2px;
    }
    .detail-kicker {
      margin: 0 0 10px;
      color: #176d81;
      font-size: 13px;
      font-weight: 900;
    }
    .detail-copy h4 {
      margin: 0;
      color: #102d36;
      font-family: "Fredoka", sans-serif;
      font-size: clamp(30px, 4vw, 54px);
      line-height: 1.02;
      letter-spacing: 0;
    }
    .detail-source {
      margin: 10px 0 0;
      color: #5d7580;
      font-size: 15px;
      font-weight: 900;
      word-break: break-word;
    }
    .detail-summary {
      margin: 18px 0 0;
      color: #244854;
      font-size: 18px;
      font-weight: 900;
      line-height: 1.7;
    }
    .detail-meta,
    .detail-chips {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 18px;
    }
    .detail-meta span,
    .detail-chips span {
      display: inline-flex;
      align-items: center;
      min-height: 32px;
      padding: 0 11px;
      border: 1px solid #d3e5e7;
      border-radius: 999px;
      color: #315c68;
      background: rgba(255,255,255,.72);
      font-size: 13px;
      font-weight: 900;
    }
    .detail-chips span {
      color: #176d81;
      border-color: rgba(19,168,194,.22);
      background: rgba(231,247,248,.82);
    }
    .detail-body {
      margin-top: 24px;
      padding: 22px;
      border: 1px solid var(--line);
      border-radius: 16px;
      background: rgba(255,255,255,.74);
    }
    .detail-body h5 {
      margin: 0 0 10px;
      color: #14313b;
      font-size: 17px;
      font-weight: 900;
    }
    .detail-body p {
      margin: 0;
      color: #496670;
      font-size: 15px;
      font-weight: 800;
      line-height: 1.85;
    }
    .poem {
      width: min(1320px, calc(100% - 44px));
      margin: 44px auto 30px;
      text-align: center;
      color: #607680;
      font-weight: 900;
    }
    @media (max-width: 1120px) {
      .reader-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
      .reader-browser { grid-template-columns: 238px minmax(0, 1fr); }
    }
    @media (max-width: 820px) {
      .hero-banner { height: 240px; }
      .topbar {
        width: min(100% - 28px, 1320px);
        align-items: flex-start;
        flex-direction: column;
        gap: 12px;
      }
      .nav-links { gap: 16px; }
      .status { display: none; }
      .banner-copy,
      .reader-feed { width: min(100% - 28px, 1320px); }
      .banner-copy { margin-top: 28px; }
      .reader-head { grid-template-columns: 1fr; }
      .reader-head p {
        max-width: 100%;
        white-space: normal;
      }
      .reader-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 22px 14px; }
      .reader-browser {
        grid-template-columns: 1fr;
        height: auto;
        min-height: 0;
      }
      .reader-sidebar { max-height: 360px; }
      .detail-hero { grid-template-columns: 1fr; }
      .reader-toolbar { grid-template-columns: 1fr; }
    }
    @media (max-width: 540px) {
      .nav-links { width: 100%; justify-content: space-between; }
      .reader-grid { grid-template-columns: 1fr; }
      .reader-actions { grid-template-columns: 1fr; }
      .reader-button.return { grid-column: auto; }
      .reader-toolbar h3,
      .reader-toolbar p { white-space: normal; }
    }
    @media (prefers-reduced-motion: reduce) {
      *, *::before, *::after { transition: none !important; animation: none !important; }
    }
  </style>
</head>
<body>
  <header class="hero-banner">
    <nav class="topbar" aria-label="顶部导航">
      <a class="brand" href="/">今日宜闻</a>
      <div class="nav-links">__NAV__</div>
      <div class="status">__STATUS__</div>
    </nav>
    <section class="banner-copy">
      <h1>__TITLE__</h1>
      <p>__SUBTITLE__</p>
    </section>
  </header>

  <main id="reader-root" class="reader-feed">
    <header class="reader-head">
      <div>
        <h2>__SECTION_TITLE__</h2>
        <p>__SECTION_COPY__</p>
      </div>
      <div class="reader-source-note">__STATUS__</div>
    </header>
    <section class="reader-grid" data-reader-grid aria-label="__TITLE__列表">
      __CARDS__
    </section>
    <section class="reader-browser" data-reader-browser hidden aria-label="__TITLE__站内阅读器">
      <aside class="reader-sidebar" aria-label="内容导航">
        <div class="reader-actions">
          <button type="button" class="reader-button" data-reader-prev>上一个</button>
          <button type="button" class="reader-button" data-reader-next>下一个</button>
          <button type="button" class="reader-button return" data-reader-home>返回主页</button>
        </div>
        <div class="reader-nav-list" aria-label="内容目录">
          __ITEM_NAV__
        </div>
      </aside>
      <section class="reader-viewer" aria-live="polite">
        <header class="reader-toolbar">
          <div>
            <h3 data-detail-title>选择一条内容</h3>
            <p data-detail-meta>左侧选择后会在这里显示站内阅读版</p>
          </div>
          <a class="reader-open" data-detail-link href="#" target="_blank" rel="noopener noreferrer">打开原文</a>
        </header>
        <article class="reader-detail">
          <div class="detail-hero">
            <figure class="detail-cover">
              <img data-detail-thumb src="" alt="">
              <span class="detail-rank" data-detail-rank></span>
            </figure>
            <div class="detail-copy">
              <p class="detail-kicker" data-detail-category></p>
              <h4 data-detail-heading></h4>
              <p class="detail-source" data-detail-source></p>
              <p class="detail-summary" data-detail-summary></p>
              <div class="detail-meta">
                <span data-detail-date></span>
                <span data-detail-metric></span>
              </div>
              <div class="detail-chips" data-detail-tags></div>
            </div>
          </div>
          <section class="detail-body">
            <h5>为什么值得看</h5>
            <p data-detail-body></p>
          </section>
        </article>
      </section>
    </section>
  </main>

  <footer id="site-footer" class="poem">__POEM__</footer>
  <script>
    (() => {
      const items = __ITEM_DATA__;
      const root = document.querySelector("#reader-root");
      const grid = document.querySelector("[data-reader-grid]");
      const browser = document.querySelector("[data-reader-browser]");
      const title = document.querySelector("[data-detail-title]");
      const meta = document.querySelector("[data-detail-meta]");
      const link = document.querySelector("[data-detail-link]");
      const thumb = document.querySelector("[data-detail-thumb]");
      const rank = document.querySelector("[data-detail-rank]");
      const category = document.querySelector("[data-detail-category]");
      const heading = document.querySelector("[data-detail-heading]");
      const source = document.querySelector("[data-detail-source]");
      const summary = document.querySelector("[data-detail-summary]");
      const date = document.querySelector("[data-detail-date]");
      const metric = document.querySelector("[data-detail-metric]");
      const tags = document.querySelector("[data-detail-tags]");
      const body = document.querySelector("[data-detail-body]");
      const navItems = [...document.querySelectorAll(".reader-nav-item")];
      let currentIndex = -1;

      const indexFromHash = () => {
        const match = window.location.hash.match(/^#item-(\\d+)$/);
        if (!match) return -1;
        const rankValue = Number(match[1]);
        return items.findIndex((item) => Number(item.rank) === rankValue);
      };

      const syncActiveNav = (index) => {
        navItems.forEach((item) => {
          const active = Number(item.dataset.readerIndex) === index;
          item.classList.toggle("is-active", active);
          item.setAttribute("aria-current", active ? "true" : "false");
          if (active) item.scrollIntoView({ block: "nearest" });
        });
      };

      const renderItem = (item) => {
        title.textContent = `${item.rank}. ${item.title}`;
        meta.textContent = `${item.source} · ${item.date}`;
        link.href = item.url;
        thumb.src = item.thumb;
        thumb.alt = `${item.title} 的频道封面`;
        rank.textContent = `#${String(item.rank).padStart(2, "0")}`;
        category.textContent = item.category;
        heading.textContent = item.title;
        source.textContent = item.source;
        summary.textContent = item.summary;
        date.textContent = item.date;
        metric.textContent = item.metric || "站内阅读版";
        body.textContent = item.detail;
        tags.replaceChildren();
        (item.tags || []).forEach((name) => {
          const chip = document.createElement("span");
          chip.textContent = name;
          tags.appendChild(chip);
        });
      };

      const openItem = (index, pushHistory = true) => {
        const item = items[index];
        if (!item) returnHome(pushHistory);
        currentIndex = index;
        grid.hidden = true;
        browser.hidden = false;
        renderItem(item);
        syncActiveNav(index);
        if (pushHistory) history.pushState({ itemIndex: index }, "", `#item-${item.rank}`);
        browser.scrollIntoView({ block: "start", behavior: "smooth" });
      };

      function returnHome(pushHistory = true) {
        currentIndex = -1;
        grid.hidden = false;
        browser.hidden = true;
        syncActiveNav(-1);
        if (pushHistory) history.pushState({}, "", window.location.pathname);
        root.scrollIntoView({ block: "start", behavior: "smooth" });
      }

      document.querySelectorAll(".js-reader-link").forEach((entry) => {
        entry.addEventListener("click", (event) => {
          event.preventDefault();
          openItem(Number(entry.dataset.readerIndex));
        });
      });
      navItems.forEach((entry) => entry.addEventListener("click", () => openItem(Number(entry.dataset.readerIndex))));
      document.querySelector("[data-reader-prev]").addEventListener("click", () => currentIndex <= 0 ? returnHome() : openItem(currentIndex - 1));
      document.querySelector("[data-reader-next]").addEventListener("click", () => currentIndex < 0 || currentIndex >= items.length - 1 ? returnHome() : openItem(currentIndex + 1));
      document.querySelector("[data-reader-home]").addEventListener("click", () => returnHome());
      window.addEventListener("popstate", () => {
        const index = indexFromHash();
        if (index >= 0) openItem(index, false);
        else returnHome(false);
      });
      const initialIndex = indexFromHash();
      if (initialIndex >= 0) openItem(initialIndex, false);
    })();
  </script>
</body>
</html>"""
    return (
        page.replace("__PAGE_TITLE__", _escape(page_title))
        .replace("__BANNER__", _escape(banner))
        .replace("__NAV__", _reader_nav(active_path))
        .replace("__STATUS__", _escape(status))
        .replace("__TITLE__", _escape(title))
        .replace("__SUBTITLE__", _escape(subtitle))
        .replace("__SECTION_TITLE__", _escape(section_title))
        .replace("__SECTION_COPY__", _escape(section_copy))
        .replace("__CARDS__", "".join(cards))
        .replace("__ITEM_NAV__", "".join(nav_items))
        .replace("__ITEM_DATA__", item_json)
        .replace("__POEM__", _escape(poem))
    )


def _row_category(row, slug: str) -> str:
    text = f"{row['title']} {row['one_liner'] or ''} {row['source_name']}".lower()
    if slug == "ai":
        if any(key in text for key in ["大模型", "模型", "llm", "gpt", "deepseek", "kimi", "通义", "豆包"]):
            return "大模型"
        if any(key in text for key in ["机器人", "具身", "自动驾驶"]):
            return "机器人"
        if any(key in text for key in ["芯片", "算力", "gpu", "英伟达"]):
            return "算力"
        if any(key in text for key in ["融资", "创业", "公司"]):
            return "产业"
        return "AI"
    if any(key in text for key in ["美股", "纳指", "道指", "标普", "英伟达", "特斯拉"]):
        return "美股"
    if any(key in text for key in ["a股", "涨", "跌", "主力", "成交额", "板块"]):
        return "A股"
    if any(key in text for key in ["基金", "etf"]):
        return "基金"
    if any(key in text for key in ["央行", "利率", "人民币", "宏观"]):
        return "宏观"
    return "市场"


def _row_detail(row) -> str:
    parts = []
    if row["bullet_points"]:
        points = [
            line.strip().lstrip("- ").strip()
            for line in str(row["bullet_points"]).splitlines()
            if line.strip()
        ]
        parts.extend(points)
    if row["importance"]:
        parts.append(f"重要性：{row['importance']}")
    if row["uncertainty"]:
        parts.append(f"备注：{row['uncertainty']}")
    return " ".join(parts) or (row["one_liner"] or row["title"])


def _row_summary(row, slug: str, category: str) -> str:
    summary = row["one_liner"] or row["title"]
    source = row["source_name"] or ""
    prefixes = [
        f"{source} 最新文章：",
        f"{source} 最新滚动：",
        "最新文章：",
        "最新滚动：",
    ]
    for prefix in prefixes:
        if summary.startswith(prefix):
            summary = summary[len(prefix):].strip()
            break
    return _short_cn(summary, 76)


def _reader_section_copy(items, slug: str) -> str:
    if not items:
        return "当前还没有可展示的最新内容，稍后刷新采集后会自动补齐。"
    sources = []
    categories = []
    for item in items:
        if item["source"] not in sources:
            sources.append(item["source"])
        if item["category"] not in categories:
            categories.append(item["category"])
    source_text = "、".join(sources[:3])
    category_text = "、".join(categories[:4])
    if slug == "ai":
        return f"本批 AI 内容来自 {source_text}，覆盖 {category_text}，按热度和时间排序。"
    return f"本批金融内容来自 {source_text}，覆盖 {category_text}，按热度和时间排序。"


def _reader_items_from_db(settings, slug: str, limit: int = 32):
    if not settings:
        return []
    active_source_names = set()
    try:
        active_source_names = {
            source.name
            for source in load_sources(settings.sources_path)
            if source.enabled and source.channel == slug
        }
    except Exception as exc:
        LOGGER.warning("Failed to load active source list: %s", exc)
    try:
        with connect(settings.database_path) as conn:
            init_db(conn)
            rows = dashboard_items(conn, channel=slug, limit=limit * 3)
    except Exception as exc:
        LOGGER.warning("Failed to load %s dashboard rows: %s", slug, exc)
        return []

    items = []
    filtered_rows = [
        row for row in rows if not active_source_names or row["source_name"] in active_source_names
    ][:limit]
    for rank, row in enumerate(filtered_rows, start=1):
        if slug == "finance":
            thumb = _finance_cover(rank)
            metric = f"热度 {int(row['score'] or 0)}"
        else:
            cover_path = ROOT / "static" / "assets" / "ai" / "covers" / f"cover-{rank:02d}.jpg"
            thumb = (
                f"/static/assets/ai/covers/cover-{rank:02d}.jpg"
                if cover_path.exists()
                else f"/static/assets/anime-thumbs/thumb-{((rank - 1) % 20) + 1:02d}.svg"
            )
            metric = f"AI 热度 {int(row['score'] or 0)}"
        category = _row_category(row, slug)
        items.append(
            {
                "rank": rank,
                "title": row["title"],
                "source": row["source_name"],
                "category": category,
                "summary": _row_summary(row, slug, category),
                "detail": _row_detail(row),
                "url": row["url"],
                "date": _format_date(row["published_at"] or row["created_at"]),
                "thumb": thumb,
                "metric": metric,
                "tags": [category, row["source_name"]],
            }
        )
    return items


def render_ai_news(settings=None) -> str:
    db_items = _reader_items_from_db(settings, "ai", limit=32)
    if db_items:
        return _render_reader_channel(
            slug="ai",
            active_path="/ai",
            title="AI 雷达",
            page_title="AI 雷达",
            subtitle="国内 AI 新闻与产业动态每日自动更新，覆盖大模型、应用、算力、创业公司与机器人。",
            section_title="今日 AI",
            section_copy=_reader_section_copy(db_items, "ai"),
            status=f"自动更新 · Top {len(db_items)}",
            banner="/static/assets/ai/banner.jpg",
            poem="大鹏一日同风起，扶摇直上九万里。",
            items=db_items,
        )

    items = []
    covers_dir = ROOT / "static" / "assets" / "ai" / "covers"
    for article in AI_ARTICLES:
        rank = article["rank"]
        cover_path = covers_dir / f"cover-{rank:02d}.jpg"
        thumb = (
            f"/static/assets/ai/covers/cover-{rank:02d}.jpg"
            if cover_path.exists()
            else f"/static/assets/anime-thumbs/thumb-{((rank - 1) % 20) + 1:02d}.svg"
        )
        items.append(
            {
                "rank": rank,
                "title": article["title"],
                "source": article["source"],
                "category": article["category"],
                "summary": article["summary"],
                "detail": article["detail"],
                "url": article["url"],
                "date": article.get("date", AI_NEWS_FETCHED_AT),
                "thumb": thumb,
                "metric": "AI 观察",
                "tags": [article["category"], article["source"]],
            }
        )
    return _render_reader_channel(
        slug="ai",
        active_path="/ai",
        title="AI 雷达",
        page_title="AI 雷达",
        subtitle="全球 AI 领域本周精选 32 条，大模型、开源、应用、研究与政策，一条不漏。",
        section_title="本周 AI",
        section_copy="Top 32 覆盖 Mythos 安全限制、GPT-5.5 开放、算力租赁、NVIDIA 与自研芯片、五角大楼多供应商、医疗诊断、欧盟 AI 法案、Google Agent、国产开源模型、融资竞赛与 Agent 事故。",
        status=f"{AI_NEWS_FETCHED_AT} · Top {len(items)}",
        banner="/static/assets/ai/banner.jpg",
        poem="大鹏一日同风起，扶摇直上九万里。",
        items=items,
    )


def _finance_cover(rank: int) -> str:
    palettes = [
        ("#0f766e", "#22c55e", "#eafff6"),
        ("#1d4ed8", "#38bdf8", "#eef7ff"),
        ("#7c2d12", "#f97316", "#fff7ed"),
        ("#14532d", "#84cc16", "#f7fee7"),
        ("#334155", "#94a3b8", "#f8fafc"),
        ("#6d28d9", "#a78bfa", "#f5f3ff"),
        ("#be123c", "#fb7185", "#fff1f2"),
        ("#0369a1", "#2dd4bf", "#ecfeff"),
        ("#4d7c0f", "#facc15", "#fefce8"),
        ("#312e81", "#60a5fa", "#eff6ff"),
    ]
    dark, accent, paper = palettes[(rank - 1) % len(palettes)]
    points = [
        (0, 180),
        (80, 150 - (rank % 5) * 9),
        (160, 166 - (rank % 4) * 12),
        (240, 112 + (rank % 3) * 11),
        (320, 130 - (rank % 6) * 7),
        (420, 76 + (rank % 5) * 8),
        (560, 96 - (rank % 4) * 10),
        (720, 46 + (rank % 3) * 13),
    ]
    polyline = " ".join(f"{x},{y}" for x, y in points)
    svg = f"""
    <svg xmlns="http://www.w3.org/2000/svg" width="960" height="540" viewBox="0 0 960 540">
      <defs>
        <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stop-color="{paper}"/>
          <stop offset="1" stop-color="#ffffff"/>
        </linearGradient>
        <linearGradient id="line" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0" stop-color="{dark}"/>
          <stop offset="1" stop-color="{accent}"/>
        </linearGradient>
      </defs>
      <rect width="960" height="540" fill="url(#bg)"/>
      <circle cx="780" cy="72" r="172" fill="{accent}" opacity=".14"/>
      <circle cx="120" cy="446" r="210" fill="{dark}" opacity=".09"/>
      <g transform="translate(120 146)">
        <rect x="-20" y="-48" width="760" height="300" rx="28" fill="#fff" opacity=".74"/>
        <path d="M0 220H720" stroke="{dark}" stroke-opacity=".16" stroke-width="3"/>
        <path d="M0 170H720" stroke="{dark}" stroke-opacity=".1" stroke-width="2"/>
        <path d="M0 120H720" stroke="{dark}" stroke-opacity=".1" stroke-width="2"/>
        <path d="M0 70H720" stroke="{dark}" stroke-opacity=".1" stroke-width="2"/>
        <polyline points="{polyline}" fill="none" stroke="url(#line)" stroke-width="14" stroke-linecap="round" stroke-linejoin="round"/>
        <g fill="{accent}">
          <circle cx="{points[-1][0]}" cy="{points[-1][1]}" r="19"/>
          <circle cx="{points[-1][0]}" cy="{points[-1][1]}" r="34" opacity=".16"/>
        </g>
      </g>
      <text x="70" y="96" fill="{dark}" font-size="42" font-family="Arial, sans-serif" font-weight="800">MARKET RADAR</text>
      <text x="72" y="132" fill="{dark}" opacity=".72" font-size="23" font-family="Arial, sans-serif">A股 / 美股 · 近1日市场快讯</text>
    </svg>
    """
    return "data:image/svg+xml," + urllib.parse.quote(svg)


def _finance_market_items():
    raw_items = [
        {
            "title": "美股三大指数小幅收高，纳指继续领涨",
            "source": "搜狐财经 / 美股收盘",
            "category": "美股",
            "summary": "隔夜美股延续反弹，市场继续关注科技龙头和半导体链条，纳指表现强于道指。",
            "detail": "周末前的美股交易仍由大型科技股和 AI 相关板块牵动。页面内采用站内中文摘要，原文按钮保留外部来源链接，避免财经站点 iframe 限制导致空白。",
            "url": "https://m.sohu.com/a/1020083945_122014422",
            "date": "2026-05-09",
            "metric": "美股收盘",
            "tags": ["美股", "纳指", "科技股"],
        },
        {
            "title": "半导体股带动美股风险偏好，AMD 大涨、NVIDIA 收高",
            "source": "Yahoo 财经 / 美股收盘",
            "category": "美股",
            "summary": "半导体股成为美股盘面焦点，AMD 单日大涨，NVIDIA 同步收高，AI 硬件链热度仍在。",
            "detail": "这条适合放在金融页的原因是：AI 产业链不只属于科技频道，也会直接影响美股风险偏好、芯片 ETF、纳指权重股和相关主题基金。",
            "url": "https://tw.stock.yahoo.com/news/%E7%BE%8E%E8%82%A1%E6%94%B6%E7%B4%85-%E8%8B%B1%E7%89%B9%E7%88%BE%E9%A3%86%E9%80%BE10-%E5%90%88%E4%BD%9C%E6%A8%99%E7%9A%84%E8%98%8B%E6%A6%82%E8%82%A1%E4%BD%B3%E5%BF%85%E7%90%AA-%E4%B8%8A%E6%BC%B220-215520342.html",
            "date": "2026-05-09",
            "metric": "AMD / NVDA",
            "tags": ["半导体", "AMD", "NVIDIA"],
        },
        {
            "title": "美股盘前情绪偏强，交易员等待宏观数据落地",
            "source": "TradingKey",
            "category": "美股盘前",
            "summary": "美股期货盘前偏强，投资者继续围绕就业、通胀和地缘风险调整仓位。",
            "detail": "盘前消息适合用来解释夜盘的情绪来源：如果宏观数据强化降息预期，成长股估值会受益；如果油价或地缘风险升温，资金会更谨慎。",
            "url": "https://www.tradingkey.com/zh-hans/analysis/stocks/us-stock/261874125-us-pre-market-nfp-iran-war-oil-price-tradingkey",
            "date": "2026-05-08",
            "metric": "盘前情绪",
            "tags": ["美股期货", "宏观数据", "油价"],
        },
        {
            "title": "A股半导体板块震荡，资金仍围绕 AI 算力反复博弈",
            "source": "新浪财经",
            "category": "A股",
            "summary": "A股半导体方向出现分化，算力、先进制程和设备材料仍是资金关注的高波动主线。",
            "detail": "这类消息需要和美股芯片链一起看：当海外半导体走强，A股相关板块往往会在次日开盘被资金重新定价，但高位题材也容易波动放大。",
            "url": "https://finance.sina.com.cn/headline/2026-05-08/doc-inhxcqkr2383894.shtml?froms=pccs",
            "date": "2026-05-08",
            "metric": "A股题材",
            "tags": ["A股", "半导体", "AI算力"],
        },
        {
            "title": "券商热议商业航天投资机会，周末题材热度升温",
            "source": "东方财富财经首页",
            "category": "A股题材",
            "summary": "周末机构和媒体继续关注商业航天，题材热度可能影响下一个交易日的军工、卫星互联网和高端制造分支。",
            "detail": "周末消息对 A股 的意义不在于即时成交，而在于为周一盘前预期定调。题材若连续发酵，需要观察竞价强度和板块内部扩散。",
            "url": "https://finance.eastmoney.com/",
            "date": "2026-05-10",
            "metric": "周末题材",
            "tags": ["商业航天", "军工", "A股"],
        },
        {
            "title": "融资资金继续活跃，热门科技股获得杠杆资金关注",
            "source": "东方财富数据",
            "category": "A股资金",
            "summary": "融资净买入榜显示，部分半导体和科技成长股仍被杠杆资金重点交易。",
            "detail": "融资资金可以作为短期情绪温度计，但不能单独作为买卖依据。更适合配合成交额、板块强度和公司基本面一起看。",
            "url": "https://stock.eastmoney.com/",
            "date": "2026-05-10",
            "metric": "融资观察",
            "tags": ["融资余额", "科技股", "资金流"],
        },
        {
            "title": "出口链数据保持热度，机电产品增长支撑制造板块叙事",
            "source": "东方财富财经首页",
            "category": "A股宏观",
            "summary": "前 4 个月出口机电产品保持增长，市场可能继续关注高端制造、汽车零部件和出海产业链。",
            "detail": "这类宏观数据通常不是单日交易催化剂，但能为中期板块叙事提供背景。对 A股 来说，出口链和汇率、关税、海外需求要一起观察。",
            "url": "https://finance.eastmoney.com/",
            "date": "2026-05-10",
            "metric": "出口链",
            "tags": ["机电出口", "制造业", "A股"],
        },
        {
            "title": "机器人、光伏与光纤概念轮动，题材交易仍偏活跃",
            "source": "东方财富市场频道",
            "category": "A股题材",
            "summary": "东方财富热门板块显示，机器人、光伏设备、光纤概念等方向仍有资金轮动迹象。",
            "detail": "题材轮动适合用来观察市场风险偏好：当主线不清晰时，资金会在多个概念之间快速切换，追高风险会增加。",
            "url": "https://quote.eastmoney.com/center/gridlist.html",
            "date": "2026-05-10",
            "metric": "板块轮动",
            "tags": ["机器人", "光伏", "光纤"],
        },
        {
            "title": "A股高波动个股继续活跃，次新与主题股弹性较强",
            "source": "东方财富财经首页",
            "category": "A股个股",
            "summary": "个股层面，次新股和主题股仍有较高波动，短线资金偏好弹性品种。",
            "detail": "这类内容只适合作为市场情绪观察，不构成个股推荐。高波动品种需要特别注意流动性、换手率和消息兑现风险。",
            "url": "https://finance.eastmoney.com/",
            "date": "2026-05-10",
            "metric": "短线情绪",
            "tags": ["次新股", "主题股", "波动"],
        },
        {
            "title": "A股与美股联动增强，AI 与半导体仍是跨市场主线",
            "source": "今日宜闻整理",
            "category": "跨市场",
            "summary": "从近 1 日消息看，美股芯片链和 A股算力、半导体题材仍然互相映射。",
            "detail": "本条是站内综合判断：美股看权重科技和半导体，A股看算力、设备、材料和题材扩散。周末没有正常交易时，应以最新交易日数据和周末消息面结合观察。",
            "url": "https://finance.eastmoney.com/",
            "date": "2026-05-10",
            "metric": "站内综合",
            "tags": ["AI", "半导体", "跨市场"],
        },
    ]
    items = []
    for index, item in enumerate(raw_items, start=1):
        items.append(
            {
                "rank": index,
                "title": item["title"],
                "source": item["source"],
                "category": item["category"],
                "summary": item["summary"],
                "detail": item["detail"],
                "url": item["url"],
                "date": item["date"],
                "thumb": _finance_cover(index),
                "metric": item["metric"],
                "tags": item["tags"],
            }
        )
    return items


def render_finance_page(settings) -> str:
    items = _reader_items_from_db(settings, "finance", limit=32) or _finance_market_items()
    return _render_reader_channel(
        slug="finance",
        active_path="/finance",
        title="金融雷达",
        page_title="金融雷达",
        subtitle="近 1 日国内财经与 A股、美股相关快讯，覆盖个股、板块、资金情绪和跨市场线索。仅作信息阅读，不构成投资建议。",
        section_title="A股 · 美股快讯",
        section_copy=_reader_section_copy(items, "finance"),
        status=f"自动更新 · Top {len(items)}",
        banner="/static/assets/finance/banner.svg",
        poem="看盘有风浪，落子须清醒。",
        items=items,
    )


def _load_music_playlist():
    path = ROOT / "static" / "music" / "playlist.json"
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    tracks = []
    for index, track in enumerate(payload.get("tracks", []), start=1):
        tracks.append(
            {
                "rank": index,
                "title": track.get("title", f"Track {index}"),
                "artist": track.get("artist", "Unknown"),
                "src": track.get("src", ""),
                "cover": track.get("cover", payload.get("cover", "")),
                "duration": track.get("duration", "--:--"),
                "album": track.get("album", "公开音频"),
                "likes": track.get("likes", "0"),
                "tags": track.get("tags", []),
                "description": track.get("description", ""),
                "source_name": track.get("source_name", "公开来源"),
                "source_url": track.get("source_url", track.get("src", "")),
                "lyrics": track.get("lyrics", []),
            }
        )
    payload["tracks"] = tracks
    return payload


def render_music_page() -> str:
    playlist = _load_music_playlist()
    tracks = playlist["tracks"]
    rows = []
    for index, track in enumerate(tracks):
        rows.append(
            f"""
            <button type="button" class="song-row js-track-link" data-track-index="{index}" aria-label="播放 {_escape(track['title'])}">
              <span class="song-index">{track['rank']:02d}</span>
              <img src="{_escape(track['cover'])}" alt="{_escape(track['title'])} 封面" loading="lazy">
              <span class="song-main">
                <b>{_escape(track['title'])}</b>
                <em>{_escape(track['artist'])}</em>
              </span>
              <span class="song-album">{_escape(track['album'])}</span>
              <span class="song-like">♡ { _escape(track['likes']) }</span>
              <span class="song-time">{_escape(track['duration'])}</span>
            </button>"""
        )

    playlist_json = json.dumps(playlist, ensure_ascii=False).replace("</", "<\\/")
    page = """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="theme-color" content="#f6fbfb">
  <title>今日宜闻 · 音乐小站</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Fredoka:wght@500;600;700&family=Nunito:wght@400;600;700;800&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="/static/music/player.css">
</head>
<body>
  <header class="music-hero">
    <nav class="topbar" aria-label="顶部导航">
      <a class="brand" href="/">今日宜闻</a>
      <div class="nav-links">__NAV__</div>
    </nav>
    <section class="hero-copy">
      <h1>音乐小站</h1>
      <p>公开音频先顶上，交互做成歌单态和播放器态两套；等你给本地音乐后，直接替换歌单数据就行。</p>
    </section>
  </header>

  <main id="music-root" class="music-root">
    <section class="mini-status" data-mini-status hidden aria-label="当前播放状态">
      <img data-status-cover src="" alt="">
      <div>
        <span>正在播放</span>
        <b data-status-title></b>
        <em data-status-artist></em>
      </div>
      <button type="button" data-open-current>打开播放器</button>
      <button type="button" data-stop-current>停止播放</button>
    </section>
    <section class="playlist-head" data-playlist-head>
      <img src="__PLAYLIST_COVER__" alt="__PLAYLIST_NAME__ 封面">
      <div>
        <h2>__PLAYLIST_NAME__</h2>
        <p>__PLAYLIST_DESCRIPTION__</p>
        <span class="track-count">__TRACK_COUNT__ 首歌 · iTunes 试听源</span>
      </div>
    </section>
    <section class="netease-entry" data-netease-entry aria-label="网易云音乐入口">
      <div class="netease-mark" aria-hidden="true">
        <span></span>
      </div>
      <div class="netease-copy">
        <b>网易云音乐网页版</b>
        <p>扫码登录、完整歌曲播放和会员权限建议在网易云官网完成；这里作为快速入口，不做 iframe 嵌入。</p>
      </div>
      <a href="https://music.163.com/" target="_blank" rel="noopener noreferrer">打开网易云</a>
    </section>
    <section class="playlist-table" data-track-grid aria-label="当前歌单">
      <div class="song-table-head" aria-hidden="true">
        <span>#</span><span>标题</span><span>专辑</span><span>喜欢</span><span>时长</span>
      </div>
      __TRACK_ROWS__
    </section>
    <section class="player-shell" data-player-shell hidden aria-label="音乐播放器">
      <div class="window-controls" aria-label="窗口控制">
        <button type="button" class="window-close" data-close-player title="关闭并停止播放" aria-label="关闭并停止播放"></button>
        <button type="button" class="window-minimize" data-minimize-player title="缩小并继续播放" aria-label="缩小并继续播放"></button>
      </div>
      <section class="turntable-panel" aria-label="唱片封面">
        <div class="tonearm" aria-hidden="true"></div>
        <div class="record-wrap">
          <div class="record" data-record>
            <img class="now-cover" data-now-cover src="" alt="">
          </div>
        </div>
      </section>
      <section class="lyric-panel" aria-label="歌词">
        <p class="now-kicker">播放器模式</p>
        <h2 class="now-title" data-now-title></h2>
        <p class="now-artist" data-now-artist></p>
        <div class="tab-strip" aria-hidden="true"><span class="is-active">歌词</span><span>百科</span><span>相似推荐</span></div>
        <div class="lyric-list" data-lyric-list></div>
        <a class="source-link" data-source-link href="#" target="_blank" rel="noopener noreferrer">查看公开来源</a>
      </section>
      <section class="dock-player" aria-label="播放控制条">
        <div class="mini-now">
          <img data-mini-cover src="" alt="">
          <div><b data-mini-title></b><span data-mini-artist></span></div>
        </div>
        <div class="transport">
          <div class="transport-buttons">
            <button type="button" data-prev-track aria-label="上一首">⏮</button>
            <button type="button" class="play-toggle" data-play-toggle aria-label="播放或暂停">▶</button>
            <button type="button" data-next-track aria-label="下一首">⏭</button>
          </div>
          <div class="progress-line">
            <span data-current-time>00:00</span>
            <input type="range" data-seek min="0" max="1000" value="0" aria-label="播放进度">
            <span data-duration>--:--</span>
          </div>
        </div>
        <div class="dock-actions"><span>极高</span><span>词</span><span>音量</span></div>
        <audio data-audio preload="metadata" crossorigin="anonymous"></audio>
      </section>
    </section>
  </main>
  <footer id="site-footer" class="poem">此曲只应天上有，人间能得几回闻。</footer>

  <script id="playlist-data" type="application/json">__PLAYLIST_DATA__</script>
  <script src="/static/music/player.js"></script>
</body>
</html>"""
    return (
        page.replace("__NAV__", _reader_nav("/music"))
        .replace("__PLAYLIST_COVER__", _escape(playlist.get("cover", "")))
        .replace("__PLAYLIST_NAME__", _escape(playlist.get("name", "音乐小站")))
        .replace("__PLAYLIST_DESCRIPTION__", _escape(playlist.get("description", "")))
        .replace("__TRACK_COUNT__", str(len(tracks)))
        .replace("__TRACK_ROWS__", "".join(rows))
        .replace("__PLAYLIST_DATA__", playlist_json)
    )


def render_novels_page() -> str:
    page = """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="theme-color" content="#fdfbf7">
  <title>今日宜闻 · 小说书架</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@500;600;700&family=Noto+Serif+SC:wght@400;500;700;800&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="/static/novels/novels.css?v=3">
</head>
<body>
  <header class="novel-hero">
    <nav class="topbar" aria-label="顶部导航">
      <a class="brand" href="/">今日宜闻</a>
      <div class="nav-links">__NAV__</div>
    </nav>
    <section class="hero-copy">
      <span>本地 Demo · 可替换小说源</span>
      <h1>小说书架</h1>
      <p>先把书库、搜索、分类、详情和阅读器体验跑通；后续接入具体来源时，只需要替换小说源适配器。</p>
    </section>
  </header>

  <main id="novel-app" class="novel-app">
    <section class="library-view" data-view="library">
      <section class="shelf-panel">
        <div class="source-panel" aria-label="小说书源">
          <div>
            <span>当前书源</span>
            <strong data-source-name>本地 Demo 书库</strong>
            <p data-source-note>可切换到 Project Gutenberg 中文公版书，正文仍使用本站阅读器展示。</p>
          </div>
          <div class="source-actions">
            <button type="button" class="source-btn is-active" data-source="local">本地 Demo</button>
            <button type="button" class="source-btn" data-source="gutenberg">公版书源</button>
          </div>
        </div>
        <label class="search-box">
          <span>搜索书名 / 作者 / 简介</span>
          <input data-search type="search" placeholder="例如：玄幻、江湖、她的名字">
        </label>
        <div class="section-title">
          <div>
            <span data-result-count>0 本书</span>
            <h2>今日书单</h2>
          </div>
          <p>点击一本书进入介绍页，再点击“开始阅读”进入沉浸阅读模式。</p>
        </div>
        <div class="filter-row">
          <div class="filter-group" data-gender-filters aria-label="频道筛选"></div>
          <div class="filter-group" data-category-filters aria-label="分类筛选"></div>
          <label class="sort-box">
            <span>排序</span>
            <select data-sort>
              <option value="updated">按更新时间</option>
              <option value="hot">按热度</option>
              <option value="words">按字数</option>
              <option value="title">按书名</option>
            </select>
          </label>
        </div>
        <div class="book-grid" data-book-grid></div>
      </section>
    </section>

    <section class="detail-view" data-view="detail" hidden></section>
    <section class="reader-view" data-view="reader" hidden></section>
  </main>
  <footer id="site-footer" class="poem">灯下翻书，风也慢下来。</footer>

  <script src="/static/novels/novels.js?v=2"></script>
</body>
</html>"""
    return page.replace("__NAV__", _reader_nav("/novels"))


def render_scene_demo() -> str:
    return """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>今日宜闻 · 动态背景预览</title>
  <style>
    * { box-sizing: border-box; }
    html, body { width: 100%; height: 100%; }
    body {
      margin: 0;
      overflow: hidden;
      background: #74d0e8;
      font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", sans-serif;
    }
    .scene {
      position: fixed;
      inset: 0;
      overflow: hidden;
      background: url("/static/assets/scene/pastoral-4k.png") center bottom / cover no-repeat;
      isolation: isolate;
    }
    .scene::before {
      content: "";
      position: absolute;
      inset: 0;
      pointer-events: none;
      background:
        linear-gradient(100deg, transparent 0 18%, rgba(255,255,255,.16) 27%, transparent 36% 100%),
        radial-gradient(circle at 18% 18%, rgba(255,255,255,.18), transparent 16rem);
      animation: windGlow 9s ease-in-out infinite;
      mix-blend-mode: screen;
    }
    .wind-layer {
      position: absolute;
      inset: 0;
      pointer-events: none;
      opacity: .72;
    }
    .wind {
      position: absolute;
      left: -18vw;
      height: 2px;
      width: 160px;
      border-radius: 999px;
      background: linear-gradient(90deg, transparent, rgba(255,255,255,.72), transparent);
      filter: blur(.2px);
      animation: windMove 5.8s linear infinite;
    }
    .wind:nth-child(1) { top: 28%; animation-delay: 0s; width: 180px; }
    .wind:nth-child(2) { top: 39%; animation-delay: -1.8s; width: 110px; opacity: .62; }
    .wind:nth-child(3) { top: 51%; animation-delay: -3.2s; width: 220px; opacity: .55; }
    .wind:nth-child(4) { top: 68%; animation-delay: -2.3s; width: 150px; opacity: .5; }
    .grass-flecks {
      position: absolute;
      inset: 52% 0 0;
      pointer-events: none;
      opacity: .7;
      background-image:
        radial-gradient(ellipse at 12% 78%, rgba(255,255,255,.45) 0 2px, transparent 3px),
        radial-gradient(ellipse at 28% 54%, rgba(255,255,255,.35) 0 2px, transparent 3px),
        radial-gradient(ellipse at 44% 68%, rgba(255,255,255,.4) 0 2px, transparent 3px),
        radial-gradient(ellipse at 70% 58%, rgba(255,255,255,.34) 0 2px, transparent 3px),
        radial-gradient(ellipse at 88% 72%, rgba(255,255,255,.42) 0 2px, transparent 3px);
      background-size: 360px 120px;
      animation: flecks 7s linear infinite;
    }
    .label {
      position: fixed;
      top: 24px;
      left: 28px;
      color: rgba(255,255,255,.92);
      text-shadow: 0 2px 14px rgba(0,0,0,.28);
      font-weight: 800;
      letter-spacing: .04em;
    }
    .label a { color: inherit; text-decoration: none; }
    @keyframes windMove {
      from { transform: translateX(0) translateY(0) rotate(-7deg); opacity: 0; }
      12% { opacity: .75; }
      82% { opacity: .48; }
      to { transform: translateX(134vw) translateY(12vh) rotate(-7deg); opacity: 0; }
    }
    @keyframes flecks {
      from { background-position: 0 0; }
      to { background-position: 360px 0; }
    }
    @keyframes windGlow {
      0%, 100% { transform: translateX(-8%); opacity: .32; }
      50% { transform: translateX(12%); opacity: .6; }
    }
    @media (prefers-reduced-motion: reduce) {
      *, *::before, *::after { animation: none !important; }
    }
  </style>
</head>
<body>
  <main class="scene" aria-label="动态背景预览">
    <div class="label"><a href="/">今日宜闻</a> · 动态背景预览</div>
    <div class="wind-layer" aria-hidden="true">
      <i class="wind"></i><i class="wind"></i><i class="wind"></i><i class="wind"></i>
    </div>
    <div class="grass-flecks" aria-hidden="true"></div>
  </main>
</body>
</html>
"""


class DashboardHandler(BaseHTTPRequestHandler):
    settings = None
    project_root = None

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path.startswith("/static/"):
            self._serve_static(parsed.path)
            return

        if parsed.path == "/api/novels/gutenberg":
            params = urllib.parse.parse_qs(parsed.query)
            query = params.get("q", [""])[0].strip()
            try:
                self._send_json(gutenberg_books_payload(query))
            except Exception as exc:
                LOGGER.exception("Failed to load Gutenberg books")
                self._send_json({"error": f"书源加载失败：{exc}"}, status=502)
            return

        if parsed.path.startswith("/api/novels/gutenberg/"):
            book_id = parsed.path.removeprefix("/api/novels/gutenberg/").strip("/")
            try:
                self._send_json(gutenberg_book_detail_payload(book_id))
            except ValueError as exc:
                self._send_json({"error": str(exc)}, status=400)
            except Exception as exc:
                LOGGER.exception("Failed to load Gutenberg book detail")
                self._send_json({"error": f"正文加载失败：{exc}"}, status=502)
            return

        if parsed.path in {"/", "/index.html"}:
            body = render_landing().encode("utf-8")
            self._send_html(body)
            return

        if parsed.path in {"/github", "/daily"}:
            body = render_github_demo().encode("utf-8")
            self._send_html(body)
            return

        if parsed.path == "/ai":
            body = render_ai_news(self.settings).encode("utf-8")
            self._send_html(body)
            return

        if parsed.path == "/finance":
            body = render_finance_page(self.settings).encode("utf-8")
            self._send_html(body)
            return

        if parsed.path == "/music":
            body = render_music_page().encode("utf-8")
            self._send_html(body)
            return

        if parsed.path == "/novels":
            body = render_novels_page().encode("utf-8")
            self._send_html(body)
            return

        if parsed.path in {"/scene", "/background"}:
            body = render_scene_demo().encode("utf-8")
            self._send_html(body)
            return

        if parsed.path not in {"/old", "/old-dashboard"}:
            self.send_error(404)
            return

        params = urllib.parse.parse_qs(parsed.query)
        channel = params.get("channel", [""])[0]
        query = params.get("q", [""])[0].strip()
        body = render_dashboard(self.settings, channel=channel, query=query).encode("utf-8")
        self._send_html(body)

    def _send_html(self, body: bytes) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, payload, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve_static(self, path: str) -> None:
        relative = urllib.parse.unquote(path.removeprefix("/static/"))
        static_root = self.project_root / "static"
        file_path = (static_root / relative).resolve()
        if not str(file_path).startswith(str(static_root.resolve())) or not file_path.is_file():
            self.send_error(404)
            return

        content_type, _ = mimetypes.guess_type(str(file_path))
        body = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type or "application/octet-stream")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args) -> None:
        LOGGER.info(format, *args)


def serve_dashboard(project_root: Path, host: str, port: int) -> None:
    settings = load_settings(project_root)
    DashboardHandler.settings = settings
    DashboardHandler.project_root = project_root
    server = ThreadingHTTPServer((host, port), DashboardHandler)
    print(f"Yonder dashboard: http://{host}:{port}")
    print("Press Ctrl+C to stop.")
    server.serve_forever()
