import html
import logging
import mimetypes
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .config import channel_labels, load_settings
from .db import connect, dashboard_items, dashboard_stats, init_db, latest_digest
from .github_demo import GITHUB_DEMO_FETCHED_AT, GITHUB_PROJECTS

LOGGER = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[2]


def _escape(value) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def _active(current: str, value: str) -> str:
    return "active" if current == value else ""


def _format_date(value) -> str:
    if not value:
        return "时间未知"
    return str(value).replace("T", " ")[:16]


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
  <title>InsightPulse Dashboard</title>
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
    <h1>InsightPulse</h1>
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
      <span class="nav-link">AI</span>
      <span class="nav-link">金融</span>
      <span class="nav-link">科技</span>
      <span class="nav-link">生活</span>
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
    project_cards = []
    covers_dir = ROOT / "static" / "assets" / "generated-covers"
    for project in GITHUB_PROJECTS:
        tech_summary = " · ".join(project["tech"][:2])
        jpg_cover = covers_dir / f"cover-{project['rank']:02d}.jpg"
        if jpg_cover.exists():
            thumb_path = f"/static/assets/generated-covers/cover-{project['rank']:02d}.jpg"
        else:
            thumb_path = f"/static/assets/anime-thumbs/thumb-{project['rank']:02d}.svg"
        project_cards.append(
            f"""
            <article id="project-{project['rank']}" class="bili-card">
              <a class="thumb" href="{_escape(project['url'])}" target="_blank" rel="noopener noreferrer" aria-label="打开 {_escape(project['name'])}">
                <img src="{thumb_path}" alt="{_escape(project['name'])} 的二次元风格封面" loading="lazy">
                <span class="rank">#{project['rank']:02d}</span>
                <span class="tech-tag">{_escape(tech_summary)}</span>
              </a>
              <h2><a href="{_escape(project['url'])}" target="_blank" rel="noopener noreferrer">{_escape(project['name'])}</a></h2>
              <p class="summary">{_escape(project['summary'])}</p>
              <div class="card-meta">
                <span>上架 {_escape(project.get('created_at', '时间未知'))}</span>
                <span>{project['stars']:,} stars</span>
              </div>
            </article>
            """
        )

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
      background: url("/static/assets/scene/cyber-banner.jpg") center 30% / cover no-repeat;
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
      max-width: 660px;
      font-weight: 900;
      line-height: 1.55;
    }
    .feed {
      width: min(1320px, calc(100% - 44px));
      margin: 24px auto 0;
    }
    .feed-head {
      display: grid;
      grid-template-columns: 1fr auto;
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
      text-decoration: none;
    }
    .bili-card h2 a:hover { color: var(--cyan); }
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
    .poem {
      width: min(1320px, calc(100% - 44px));
      margin: 44px auto 30px;
      text-align: center;
      color: #607680;
      font-weight: 900;
    }
    @media (max-width: 1120px) {
      .card-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
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
      .source-note { justify-self: start; }
      .card-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 22px 14px; }
    }
    @media (max-width: 540px) {
      .nav-links { width: 100%; justify-content: space-between; }
      .card-grid { grid-template-columns: 1fr; }
      .card-meta { font-size: 12px; }
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
        <span>AI</span>
        <span>金融</span>
        <span>科技</span>
        <span>生活</span>
        <a href="#site-footer">小站</a>
      </div>
      <div class="status">近 3 个月 · Top 20</div>
    </nav>
    <section class="banner-copy">
      <h1>GitHub 乐子雷达</h1>
      <p>最近三个月创建、按星数排序的高星项目。适合快速扫一眼今天开源圈又在整什么活。</p>
    </section>
  </header>

  <main id="projects" class="feed">
    <header class="feed-head">
      <div>
        <h2>热门项目</h2>
        <p>涵盖 AI 编码代理、开源工作流、设计系统、知识图谱与命令行工具等前沿领域，近三月高星项目一览。</p>
      </div>
      <div class="source-note">GitHub · __FETCHED__</div>
    </header>
    <section class="card-grid" aria-label="GitHub 热门项目">
      __PROJECT_CARDS__
    </section>
  </main>

  <footer id="site-footer" class="poem">海阔凭鱼跃，天高任鸟飞。</footer>
</body>
</html>
"""
    return (
        page.replace("__PROJECT_CARDS__", "".join(project_cards))
        .replace("__FETCHED__", _escape(GITHUB_DEMO_FETCHED_AT))
    )


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

        if parsed.path in {"/", "/index.html"}:
            body = render_landing().encode("utf-8")
            self._send_html(body)
            return

        if parsed.path in {"/github", "/daily"}:
            body = render_github_demo().encode("utf-8")
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
    print(f"InsightPulse dashboard: http://{host}:{port}")
    print("Press Ctrl+C to stop.")
    server.serve_forever()
