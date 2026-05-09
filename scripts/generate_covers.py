"""Cover generation pipeline for Knowledge Radar project cards.

Generates JPG covers by compositing real background images with project text
overlays. When PIXABAY_API_KEY is not configured, the website falls back to
the existing anime-tech SVG covers (which are vector-crisp and CSS-aware).

Usage:
    python scripts/generate_covers.py              # all 20 projects
    python scripts/generate_covers.py --rank 1     # single project
    python scripts/generate_covers.py --dry-run    # print search keywords only
    python scripts/generate_covers.py --pool-only  # build background pool only
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from knowledge_radar.github_demo import GITHUB_PROJECTS  # noqa: E402

OUT_DIR = ROOT / "static" / "assets" / "github" / "covers"
POOL_DIR = ROOT / "static" / "assets" / "github" / "pool"
MANIFEST_PATH = OUT_DIR / "manifest.json"
WIDTH, HEIGHT = 960, 540

# Per-project search keywords — crafted to match each project's actual theme.
# Prefixed with "anime illustration" for style. English keywords work better
# with Pixabay's search but are informed by the project's Chinese name + summary.
PROJECT_KEYWORDS: dict[int, list[str]] = {
    1:  ["terminal", "code", "hacker", "digital", "technology"],
    2:  ["robot", "workshop", "automation", "future", "mechanical"],
    3:  ["laboratory", "science", "experiment", "discovery", "research"],
    4:  ["colorful", "abstract", "art", "creative", "design", "palette"],
    5:  ["orchestra", "symphony", "harmony", "automation", "conductor"],
    6:  ["cave", "primitive", "ancient", "stone", "torch", "prehistoric"],
    7:  ["library", "archive", "ancient", "books", "mystical", "palace"],
    8:  ["calligraphy", "writing", "manuscript", "letter", "poetry", "ink"],
    9:  ["constellation", "stars", "network", "nodes", "universe", "connection"],
    10: ["dashboard", "control room", "mission", "command", "tactical"],
    11: ["toolbox", "workshop", "tools", "engineering", "craftsman"],
    12: ["art studio", "workshop", "creative", "palette", "design"],
    13: ["command line", "terminal", "hacker", "interface", "digital"],
    14: ["headquarters", "base", "station", "home", "sanctuary"],
    15: ["window", "portal", "gateway", "communication", "connection"],
    16: ["workspace", "office", "desk", "studio", "modern"],
    17: ["chip", "processor", "circuit", "hardware", "machine"],
    18: ["symphony", "orchestra", "music", "harmony", "conductor", "theater"],
    19: ["shield", "fortress", "guardian", "protection", "citadel"],
    20: ["radar", "antenna", "detection", "signal", "waves", "satellite"],
    21: ["blueprint", "engineering", "workshop", "craft", "precision", "tools"],
    22: ["tiny robot", "cat companion", "cute", "miniature", "futuristic", "mecha"],
    23: ["treasure chest", "collection", "compendium", "archive", "showcase", "gallery"],
    24: ["tiny house", "minimalist", "compact", "efficient", "speed", "lightning"],
    25: ["power armor", "mecha suit", "upgrade", "enhancement", "hologram", "interface"],
    26: ["portal", "gateway", "hub", "nexus", "bridge", "dimension"],
    27: ["all seeing eye", "vision", "telescope", "observer", "watcher", "omniscient"],
    28: ["goddess", "creation", "sculpture", "essence", "transformation", "mystical"],
    29: ["twin dragons", "bridge", "fusion", "collaboration", "harmony", "duality"],
    30: ["blueprint tower", "architecture", "foundation", "structure", "construction", "pillar"],
    31: ["game studio", "pixel world", "fantasy realm", "adventure", "dungeon", "magic"],
    32: ["digital soul", "time capsule", "memory crystal", "hologram", "ethereal", "starlight"],
}


def load_pixabay_key() -> str:
    env_path = ROOT / ".env"
    if not env_path.exists():
        return ""
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("PIXABAY_API_KEY="):
            return line.split("=", 1)[1].strip()
    return ""


def search_pixabay(keywords: list[str], api_key: str, per_page: int = 5) -> list[dict]:
    query = "+".join(urllib.parse.quote(k) for k in keywords[:4])
    url = (
        f"https://pixabay.com/api/?"
        f"key={api_key}&q={query}&image_type=illustration"
        f"&orientation=horizontal&min_width=800&safesearch=true"
        f"&per_page={per_page}"
    )
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "KnowledgeRadar/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode()).get("hits", [])
    except Exception as e:
        print(f"  Pixabay search error: {e}")
        return []


def download_image(url: str, dest: Path, label: str = "") -> bool:
    if dest.exists():
        return True
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "KnowledgeRadar/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(resp.read())
        print(f"  Downloaded {label}: {dest.name}")
        return True
    except Exception as e:
        print(f"  Download error for {label}: {e}")
        return False


def pick_background(project: dict, api_key: str) -> Path | None:
    """Search Pixabay with project-specific keywords for a matching background."""
    rank = project["rank"]
    cached = POOL_DIR / f"project-{rank:02d}.jpg"
    if cached.exists():
        return cached

    keywords = PROJECT_KEYWORDS.get(rank, ["technology", "abstract", "digital"])
    # Try with "anime illustration" prefix first for style consistency
    results = search_pixabay(
        ["anime", "illustration"] + keywords, api_key, per_page=5
    )
    if not results:
        # Fall back: broader search without anime prefix
        results = search_pixabay(keywords, api_key, per_page=5)

    if results:
        if download_image(results[0]["largeImageURL"], cached, project["name"]):
            return cached

    return None


def _category(project: dict) -> str:
    text = " ".join(
        [project["repo"], project["name"], project["summary"], project["detail"],
         " ".join(project["tech"])]
    ).lower()
    tech = {t.lower() for t in project["tech"]}
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
    if "cli" in tech or "command" in text or "命令行" in text:
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


def composite_cover(bg_path: Path, project: dict, output_path: Path) -> bool:
    """Overlay project text onto a clean background, save as JPG cover."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("  Pillow not installed, cannot composite cover.")
        return False

    img = Image.open(bg_path).convert("RGB")
    img = img.resize((WIDTH, HEIGHT), Image.LANCZOS)
    draw = ImageDraw.Draw(img)

    font_dir = ROOT / "static" / "assets" / "fonts"
    title_font = _load_font(draw, font_dir, 26)
    tech_font = _load_font(draw, font_dir, 15)
    rank_font = _load_font(draw, font_dir, 20)

    name = project["name"]
    repo_name = project["repo"].split("/")[-1]
    tech_str = " / ".join(project["tech"][:2])

    # Text shadow helper — draws a dark outline behind white text for readability
    def shadowed_text(xy, text, fill, font, shadow_color=(13, 38, 44)):
        x, y = xy
        for dx, dy in [(-1, -1), (1, -1), (-1, 1), (1, 1)]:
            draw.text((x + dx, y + dy), text, fill=shadow_color, font=font)
        draw.text((x, y), text, fill=fill, font=font)

    shadowed_text((24, HEIGHT - 52), name, fill=(255, 255, 255, 240), font=title_font)
    shadowed_text(
        (24, HEIGHT - 24), f"{repo_name}  ·  {tech_str}",
        fill=(255, 255, 255, 200), font=tech_font
    )

    # Top-left rank badge
    badge_x, badge_y = 20, 20
    ImageDraw.Draw(img).rounded_rectangle(
        [(badge_x, badge_y), (badge_x + 72, badge_y + 34)],
        radius=12, fill=(22, 85, 94, 200)
    )
    draw.text((badge_x + 36, badge_y + 13), f"#{project['rank']:02d}",
              fill=(255, 255, 255), font=rank_font, anchor="ma")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, "JPEG", quality=92)
    return True


def _load_font(draw, font_dir: Path, size: int):
    from PIL import ImageFont
    candidates = [
        font_dir / "NotoSansSC-Bold.ttf",
        font_dir / "NotoSansSC-Regular.ttf",
        font_dir / "NotoSans-Bold.ttf",
        font_dir / "NotoSans-Regular.ttf",
    ]
    for p in candidates:
        if p.exists():
            return ImageFont.truetype(str(p), size)
    try:
        return ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", size)
    except Exception:
        return ImageFont.load_default()


def main():
    parser = argparse.ArgumentParser(description="Generate project cover images")
    parser.add_argument("--rank", type=int, help="Generate single project by rank")
    parser.add_argument("--dry-run", action="store_true", help="Print planned search keywords only")
    args = parser.parse_args()

    api_key = load_pixabay_key()

    if not api_key:
        print("PIXABAY_API_KEY not set in .env — no backgrounds to composite.")
        print("The website will use existing SVG covers (vector-crisp, already styled).")
        print("To enable JPG covers with real backgrounds: register at pixabay.com/api/docs/")
        print("and add PIXABAY_API_KEY= to your .env file.\n")
        return

    projects = GITHUB_PROJECTS
    if args.rank:
        projects = [p for p in projects if p["rank"] == args.rank]
        if not projects:
            print(f"No project with rank {args.rank}")
            sys.exit(1)

    succeeded = 0
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    POOL_DIR.mkdir(parents=True, exist_ok=True)

    for project in projects:
        rank = project["rank"]
        name = project["name"]
        output_path = OUT_DIR / f"cover-{rank:02d}.jpg"
        keywords = PROJECT_KEYWORDS.get(rank, ["technology", "abstract", "digital"])

        print(f"\n[{rank:02d}] {name}")
        print(f"  keywords: anime illustration {' '.join(keywords)}")

        if args.dry_run:
            continue

        bg_path = pick_background(project, api_key)
        if bg_path and bg_path.exists():
            if composite_cover(bg_path, project, output_path):
                print(f"  ✓ {output_path.name}")
                succeeded += 1
                time.sleep(0.5)
                continue

        print(f"  ✗ No background found — SVG will be used on web")

    print(f"\nDone: {succeeded}/{len(projects)} JPG covers generated → {OUT_DIR}")


if __name__ == "__main__":
    main()
