from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from yonder.github_demo import GITHUB_PROJECTS  # noqa: E402


OUT_DIR = ROOT / "static" / "assets" / "anime-thumbs"
WIDTH = 640
HEIGHT = 360


PALETTES = [
    ("#7dd9f7", "#ecfbff", "#68b785", "#2f7e65", "#ffcc72"),
    ("#70c6ff", "#fff3d6", "#73bd76", "#316d92", "#f7a35c"),
    ("#85d6e5", "#f8fff4", "#67bfa6", "#276e71", "#f4d15f"),
    ("#99c6ff", "#f9fbff", "#9ecb76", "#596db0", "#ffffff"),
    ("#2a3f78", "#89a5db", "#3f6e8a", "#172449", "#ffd96e"),
    ("#ffbc86", "#ffe7c9", "#6cbf83", "#566c55", "#d86663"),
    ("#8de3d1", "#fff9dd", "#73b96e", "#2b7b64", "#f0bd63"),
    ("#71d0f0", "#f6ffff", "#7ac579", "#3e9070", "#b7ec77"),
]


def esc(value: object) -> str:
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def digest(project: dict) -> int:
    key = f"{project['repo']}|{project['name']}|{' '.join(project['tech'])}"
    return int(hashlib.sha256(key.encode("utf-8")).hexdigest()[:8], 16)


def category(project: dict) -> str:
    text = " ".join(
        [
            project["repo"],
            project["name"],
            project["summary"],
            project["detail"],
            " ".join(project["tech"]),
        ]
    ).lower()
    tech = {item.lower() for item in project["tech"]}
    if "memory" in text or "记忆" in text:
        return "memory"
    if "graph" in text or "图谱" in text:
        return "graph"
    if "orchestration" in text or "编排" in text or "agent workflow" in text:
        return "agent"
    if "dashboard" in tech or "pdf" in tech or "career" in text or "求职" in text:
        return "dashboard"
    if "research" in text or "研究" in text:
        return "research"
    if "design.md" in tech or "ui systems" in tech or "design systems" in tech:
        return "design"
    if "design" in text or "ui" in text or "设计" in text:
        return "design"
    if "cli" in tech or re.search(r"(^|[^a-z])cli([^a-z]|$)", text) or "command" in text or "命令行" in text:
        return "cli"
    if "radar" in text or "雷达" in text:
        return "radar"
    if "workspace" in text or "google" in text:
        return "workspace"
    if "runtime" in text or "hardware" in text or "模型" in text:
        return "runtime"
    if "text" in text or "layout" in text or "排版" in text:
        return "text"
    if "safety" in text or "nvidia" in text or "安全" in text:
        return "security"
    return "agent"


def cloud(x: int, y: int, scale: float) -> str:
    return f"""
      <g opacity=".9" transform="translate({x} {y}) scale({scale})">
        <ellipse cx="0" cy="18" rx="56" ry="18" fill="rgba(255,255,255,.86)"/>
        <circle cx="-30" cy="12" r="20" fill="rgba(255,255,255,.86)"/>
        <circle cx="4" cy="5" r="27" fill="rgba(255,255,255,.86)"/>
        <circle cx="34" cy="13" r="18" fill="rgba(255,255,255,.86)"/>
      </g>
    """


def tree(x: int, y: int, scale: float, deep: str, light: str) -> str:
    return f"""
      <g transform="translate({x} {y}) scale({scale})">
        <rect x="-4" y="18" width="8" height="34" rx="3" fill="#765840"/>
        <circle cx="0" cy="7" r="24" fill="{deep}"/>
        <circle cx="-18" cy="17" r="18" fill="{light}"/>
        <circle cx="18" cy="18" r="17" fill="{light}"/>
      </g>
    """


def base_scene(project: dict, palette: tuple[str, str, str, str, str], seed: int) -> str:
    sky, sky_low, hill, deep, accent = palette
    sun_x = 78 + seed % 460
    house_x = 86 + seed % 360
    return f"""
      <rect width="{WIDTH}" height="{HEIGHT}" fill="url(#sky)"/>
      <circle cx="{sun_x}" cy="70" r="34" fill="{accent}" opacity=".66" filter="url(#soft)"/>
      {cloud(136 + seed % 110, 58 + seed % 22, .68)}
      {cloud(438 - seed % 130, 86 - seed % 18, .52)}
      <path d="M0 215 C88 158 170 190 250 134 C340 74 438 126 640 84 L640 360 L0 360Z" fill="{deep}" opacity=".72"/>
      <path d="M0 250 C110 190 186 238 298 178 C424 110 500 204 640 150 L640 360 L0 360Z" fill="{hill}"/>
      <path d="M0 304 C110 282 205 318 315 286 C442 250 542 300 640 270 L640 360 L0 360Z" fill="{deep}"/>
      {tree(68, 230, .92, deep, hill)}
      {tree(560, 228, .8, deep, hill)}
      <path d="M{house_x} 250 l54 -34 l54 34 v58 h-108z" fill="rgba(255,255,255,.68)"/>
      <path d="M{house_x} 250 l54 -34 l54 34" fill="none" stroke="{accent}" stroke-width="9" stroke-linecap="round"/>
    """


def motif(project: dict, kind: str, palette: tuple[str, str, str, str, str], seed: int) -> str:
    _, _, hill, deep, accent = palette
    if kind == "cli":
        lines = "".join(
            f'<rect x="188" y="{120 + i * 22}" width="{120 + (seed + i * 37) % 220}" height="7" rx="4" fill="{accent}" opacity="{.72 - i * .06}"/>'
            for i in range(5)
        )
        return f"""
          <rect x="158" y="92" width="326" height="172" rx="18" fill="rgba(14,38,48,.68)" stroke="rgba(255,255,255,.56)"/>
          <circle cx="184" cy="116" r="7" fill="#ff7d7d"/><circle cx="206" cy="116" r="7" fill="#ffd87a"/><circle cx="228" cy="116" r="7" fill="#84e59f"/>
          <path d="M198 172 l32 24 l-32 24" fill="none" stroke="#fff" stroke-width="10" stroke-linecap="round" stroke-linejoin="round"/>
          {lines}
        """
    if kind == "agent":
        nodes = [(250, 132), (330, 104), (414, 142), (376, 218), (270, 228), (210, 188)]
        edges = "".join(
            f'<line x1="{nodes[i][0]}" y1="{nodes[i][1]}" x2="{nodes[(i+1)%len(nodes)][0]}" y2="{nodes[(i+1)%len(nodes)][1]}" stroke="rgba(255,255,255,.72)" stroke-width="4"/>'
            for i in range(len(nodes))
        )
        dots = "".join(
            f'<circle cx="{x}" cy="{y}" r="{16 + (i % 2) * 5}" fill="{accent if i % 2 else deep}" stroke="#fff" stroke-width="4"/>'
            for i, (x, y) in enumerate(nodes)
        )
        return f"{edges}{dots}<circle cx='320' cy='176' r='44' fill='rgba(255,255,255,.5)'/><path d='M302 176 h36 M320 158 v36' stroke='{deep}' stroke-width='9' stroke-linecap='round'/>"
    if kind == "memory":
        towers = "".join(
            f'<rect x="{218+i*52}" y="{118-(i%2)*18}" width="34" height="{120+(i%3)*20}" rx="8" fill="rgba(255,255,255,.58)" stroke="{deep}" stroke-width="3"/>'
            for i in range(5)
        )
        stars = "".join(
            f'<circle cx="{178+(i*43)%300}" cy="{74+(i*31)%90}" r="{2+i%3}" fill="#fff" opacity=".86"/>'
            for i in range(14)
        )
        return f"{stars}{towers}<path d='M196 252 C250 210 390 210 446 252' fill='none' stroke='{accent}' stroke-width='8' stroke-linecap='round'/>"
    if kind == "graph":
        nodes = [(178, 114), (258, 90), (352, 116), (444, 96), (218, 206), (332, 220), (458, 196)]
        edges = "".join(
            f'<line x1="{a[0]}" y1="{a[1]}" x2="{b[0]}" y2="{b[1]}" stroke="rgba(255,255,255,.7)" stroke-width="3"/>'
            for a, b in zip(nodes, nodes[1:] + nodes[:1])
        )
        dots = "".join(
            f'<circle cx="{x}" cy="{y}" r="18" fill="{accent if i%2 else deep}" stroke="#fff" stroke-width="4"/>'
            for i, (x, y) in enumerate(nodes)
        )
        return f"{edges}{dots}<path d='M188 260 C260 238 360 244 452 258' stroke='{accent}' stroke-width='7' fill='none' stroke-linecap='round'/>"
    if kind == "design":
        return f"""
          <rect x="168" y="90" width="130" height="92" rx="16" fill="rgba(255,255,255,.76)"/>
          <rect x="320" y="86" width="150" height="128" rx="18" fill="rgba(255,255,255,.58)"/>
          <rect x="188" y="112" width="72" height="12" rx="6" fill="{deep}"/>
          <rect x="188" y="136" width="86" height="12" rx="6" fill="{accent}"/>
          <circle cx="366" cy="130" r="26" fill="{accent}" opacity=".82"/>
          <path d="M340 180 h96" stroke="{deep}" stroke-width="10" stroke-linecap="round"/>
          <path d="M192 228 C252 198 384 202 452 234" stroke="#fff" stroke-width="8" fill="none" stroke-linecap="round"/>
        """
    if kind == "research":
        return f"""
          <ellipse cx="320" cy="184" rx="132" ry="62" fill="rgba(255,255,255,.42)" stroke="#fff" stroke-width="5"/>
          <path d="M248 184 C272 120 366 120 392 184 C366 244 272 244 248 184Z" fill="rgba(255,255,255,.55)" stroke="{deep}" stroke-width="5"/>
          <circle cx="320" cy="184" r="34" fill="{accent}" opacity=".86"/>
          <path d="M204 104 C280 76 390 84 456 118" stroke="#fff" stroke-width="6" fill="none" stroke-linecap="round"/>
          <path d="M214 262 C300 236 374 240 450 266" stroke="{accent}" stroke-width="7" fill="none" stroke-linecap="round"/>
        """
    if kind == "radar":
        rings = "".join(
            f'<circle cx="320" cy="188" r="{36+i*28}" fill="none" stroke="rgba(255,255,255,{.78-i*.11})" stroke-width="5"/>'
            for i in range(4)
        )
        return f"{rings}<path d='M320 188 L446 128' stroke='{accent}' stroke-width='9' stroke-linecap='round'/><circle cx='320' cy='188' r='18' fill='{deep}' stroke='#fff' stroke-width='5'/><path d='M180 286 h280' stroke='{accent}' stroke-width='7' stroke-linecap='round'/>"
    if kind == "workspace":
        cards = "".join(
            f'<rect x="{174+i*74}" y="{112+(i%2)*24}" width="58" height="76" rx="12" fill="rgba(255,255,255,.72)" stroke="{deep}" stroke-width="3"/><path d="M{188+i*74} {142+(i%2)*24} h30" stroke="{accent}" stroke-width="6" stroke-linecap="round"/>'
            for i in range(4)
        )
        return f"{cards}<path d='M192 250 C280 226 382 228 468 252' stroke='#fff' stroke-width='8' fill='none' stroke-linecap='round'/>"
    if kind == "runtime":
        chips = "".join(
            f'<rect x="{188+i*76}" y="{126+(i%2)*54}" width="58" height="42" rx="9" fill="rgba(255,255,255,.74)" stroke="{deep}" stroke-width="4"/>'
            for i in range(4)
        )
        pins = "".join(
            f'<line x1="{196+i*76}" y1="116" x2="{196+i*76}" y2="96" stroke="{accent}" stroke-width="4"/>'
            for i in range(4)
        )
        return f"<rect x='166' y='98' width='308' height='168' rx='22' fill='rgba(17,53,62,.34)'/>{chips}{pins}<path d='M236 238 h168' stroke='{accent}' stroke-width='9' stroke-linecap='round'/>"
    if kind == "dashboard":
        bars = "".join(
            f'<rect x="{188+i*44}" y="{220-(seed+i*31)%92}" width="26" height="{48+(seed+i*31)%92}" rx="7" fill="{accent if i%2 else deep}" opacity=".88"/>'
            for i in range(7)
        )
        return f"<rect x='154' y='90' width='334' height='190' rx='22' fill='rgba(255,255,255,.52)' stroke='#fff' stroke-width='4'/>{bars}<path d='M184 134 C246 176 324 126 454 150' stroke='{deep}' stroke-width='8' fill='none' stroke-linecap='round'/>"
    if kind == "text":
        lines = "".join(
            f'<rect x="178" y="{104+i*28}" width="{250 + (i%3)*50}" height="12" rx="6" fill="{deep if i%2 else accent}" opacity=".82"/>'
            for i in range(6)
        )
        return f"<rect x='152' y='80' width='340' height='220' rx='24' fill='rgba(255,255,255,.62)'/>{lines}<path d='M218 254 C280 232 376 236 430 258' stroke='#fff' stroke-width='8' fill='none' stroke-linecap='round'/>"
    if kind == "security":
        return f"""
          <path d="M320 88 L438 132 V206 C438 250 392 282 320 300 C248 282 202 250 202 206 V132Z" fill="rgba(255,255,255,.56)" stroke="{deep}" stroke-width="6"/>
          <path d="M320 126 v108" stroke="{accent}" stroke-width="10" stroke-linecap="round"/>
          <path d="M274 176 h92" stroke="{accent}" stroke-width="10" stroke-linecap="round"/>
          <circle cx="320" cy="176" r="72" fill="none" stroke="#fff" stroke-width="7" opacity=".72"/>
        """
    return ""


def make_svg(project: dict) -> str:
    seed = digest(project)
    palette = PALETTES[seed % len(PALETTES)]
    sky, sky_low, hill, deep, accent = palette
    kind = category(project)
    title = esc(project["name"])
    repo = esc(project["repo"].split("/")[-1])
    tech = esc(" / ".join(project["tech"][:2]))
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-label="{title} 动漫科技风封面">
  <defs>
    <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
      <stop stop-color="{sky}"/>
      <stop offset="1" stop-color="{sky_low}"/>
    </linearGradient>
    <filter id="soft"><feGaussianBlur stdDeviation="2"/></filter>
  </defs>
  {base_scene(project, palette, seed)}
  {motif(project, kind, palette, seed)}
  <g opacity=".66">
    <path d="M34 54 C92 36 148 38 210 54" stroke="rgba(255,255,255,.72)" stroke-width="4" fill="none" stroke-linecap="round"/>
    <path d="M460 48 C512 34 560 36 606 52" stroke="rgba(255,255,255,.66)" stroke-width="4" fill="none" stroke-linecap="round"/>
  </g>
  <rect x="22" y="22" width="72" height="34" rx="13" fill="rgba(22,85,94,.55)"/>
  <text x="58" y="45" text-anchor="middle" font-size="18" font-weight="800" fill="#fff" font-family="Arial, sans-serif">#{project['rank']:02d}</text>
  <rect x="28" y="282" width="584" height="52" rx="18" fill="rgba(17,45,55,.55)"/>
  <text x="52" y="306" font-size="22" font-weight="800" fill="#fff" font-family="Arial, sans-serif">{title}</text>
  <text x="52" y="326" font-size="14" font-weight="700" fill="rgba(255,255,255,.82)" font-family="Arial, sans-serif">{repo} · {tech}</text>
</svg>
"""


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = []
    for project in GITHUB_PROJECTS:
        filename = f"thumb-{project['rank']:02d}.svg"
        kind = category(project)
        (OUT_DIR / filename).write_text(make_svg(project), encoding="utf-8")
        manifest.append(
            {
                "file": filename,
                "project": project["repo"],
                "name": project["name"],
                "category": kind,
                "source": "generated from GitHub project metadata",
            }
        )
    (OUT_DIR / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Generated {len(manifest)} project thumbnails in {OUT_DIR}")


if __name__ == "__main__":
    main()
