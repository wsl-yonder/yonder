"""Generate distinct Pixabay covers for dynamic GitHub ranks.

This fills ranks beyond the original 32 hand-picked covers. It reads the
current GitHub cache, searches Pixabay with project-specific keywords, skips
duplicate image bytes already used by existing covers, and writes clean 16:9
JPG backgrounds for the card UI.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE_PATH = ROOT / "data" / "github_trending.json"
OUT_DIR = ROOT / "static" / "assets" / "github" / "covers"
POOL_DIR = ROOT / "static" / "assets" / "github" / "pool"
WIDTH, HEIGHT = 960, 540


RANK_THEMES = {
    33: ["neural", "network", "city", "technology"],
    34: ["terminal", "code", "matrix", "interface"],
    35: ["robot", "assistant", "workspace", "automation"],
    36: ["data", "dashboard", "analytics", "finance"],
    37: ["cloud", "server", "architecture", "digital"],
    38: ["ai", "research", "laboratory", "science"],
    39: ["cyber", "security", "shield", "network"],
    40: ["hologram", "interface", "future", "workspace"],
    41: ["chip", "circuit", "processor", "hardware"],
    42: ["library", "knowledge", "archive", "books"],
    43: ["game", "pixel", "fantasy", "adventure"],
    44: ["map", "radar", "signal", "satellite"],
    45: ["design", "palette", "creative", "studio"],
    46: ["workflow", "automation", "factory", "tools"],
    47: ["open", "source", "community", "collaboration"],
    48: ["mobile", "app", "screen", "interface"],
    49: ["memory", "crystal", "dream", "archive"],
    50: ["agency", "agents", "team", "operations"],
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


def load_projects() -> list[dict]:
    payload = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    return payload.get("items", [])


def existing_hashes() -> set[str]:
    hashes: set[str] = set()
    for path in OUT_DIR.glob("cover-*.jpg"):
        hashes.add(hashlib.md5(path.read_bytes()).hexdigest())
    return hashes


def project_keywords(project: dict) -> list[str]:
    rank = int(project["rank"])
    keywords = list(RANK_THEMES.get(rank, []))
    for tech in project.get("tech") or []:
        clean = str(tech).replace("-", " ").strip()
        if clean and clean.lower() not in {k.lower() for k in keywords}:
            keywords.append(clean)
        if len(keywords) >= 6:
            break
    return keywords or ["technology", "abstract", "digital"]


def search_pixabay(api_key: str, keywords: list[str], page: int) -> list[dict]:
    query = " ".join(["anime", "illustration"] + keywords[:4])
    params = urllib.parse.urlencode(
        {
            "key": api_key,
            "q": query,
            "image_type": "illustration",
            "orientation": "horizontal",
            "min_width": "800",
            "safesearch": "true",
            "per_page": "20",
            "page": str(page),
        }
    )
    request = urllib.request.Request(
        f"https://pixabay.com/api/?{params}",
        headers={"User-Agent": "KnowledgeRadar/1.0"},
    )
    with urllib.request.urlopen(request, timeout=8) as response:
        return json.loads(response.read().decode("utf-8")).get("hits", [])


def download_image(url: str, dest: Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": "KnowledgeRadar/1.0"})
    with urllib.request.urlopen(request, timeout=10) as response:
        dest.write_bytes(response.read())


def brightness_ok(path: Path) -> bool:
    try:
        from PIL import Image
        import statistics

        image = Image.open(path).convert("L")
        value = statistics.mean(image.getdata())
        image.close()
        return value > 72
    except Exception:
        return True


def resize_cover(src: Path, dest: Path) -> None:
    from PIL import Image

    image = Image.open(src).convert("RGB")
    image_ratio = image.width / image.height
    target_ratio = WIDTH / HEIGHT
    if image_ratio > target_ratio:
        new_width = int(image.height * target_ratio)
        left = (image.width - new_width) // 2
        image = image.crop((left, 0, left + new_width, image.height))
    else:
        new_height = int(image.width / target_ratio)
        top = (image.height - new_height) // 2
        image = image.crop((0, top, image.width, top + new_height))
    image = image.resize((WIDTH, HEIGHT), Image.LANCZOS)
    dest.parent.mkdir(parents=True, exist_ok=True)
    image.save(dest, "JPEG", quality=92)


def generate_for_project(project: dict, used_hashes: set[str], force: bool) -> bool:
    rank = int(project["rank"])
    output = OUT_DIR / f"cover-{rank:02d}.jpg"
    if output.exists() and not force:
        print(f"[{rank:02d}] exists: {output.name}")
        return True

    keywords = project_keywords(project)
    print(f"[{rank:02d}] {project['name']} -> {' '.join(keywords)}", flush=True)
    candidates: list[dict] = []
    api_key = load_pixabay_key()
    for page in (1, 2, 3):
        try:
            candidates.extend(search_pixabay(api_key, keywords, page))
        except Exception as exc:
            print(f"  search failed page {page}: {exc}", flush=True)
    random.shuffle(candidates)

    POOL_DIR.mkdir(parents=True, exist_ok=True)
    for hit in candidates:
        image_url = hit.get("largeImageURL") or hit.get("webformatURL")
        if not image_url:
            continue
        temp = POOL_DIR / f"rank-{rank:02d}-{hit.get('id', 'img')}.jpg"
        try:
            download_image(image_url, temp)
        except Exception as exc:
            print(f"  download failed: {exc}", flush=True)
            continue
        if not brightness_ok(temp):
            temp.unlink(missing_ok=True)
            continue
        digest = hashlib.md5(temp.read_bytes()).hexdigest()
        if digest in used_hashes:
            temp.unlink(missing_ok=True)
            continue
        used_hashes.add(digest)
        resize_cover(temp, output)
        print(f"  saved {output.name}", flush=True)
        time.sleep(0.25)
        return True

    print("  no unique image found", flush=True)
    return False


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, default=33)
    parser.add_argument("--end", type=int, default=50)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    if not load_pixabay_key():
        print("PIXABAY_API_KEY missing in .env")
        sys.exit(1)

    projects = [
        project
        for project in load_projects()
        if args.start <= int(project["rank"]) <= args.end
    ]
    used_hashes = existing_hashes()
    ok = 0
    for project in projects:
        if generate_for_project(project, used_hashes, args.force):
            ok += 1
    print(f"Done: {ok}/{len(projects)} covers generated or present.", flush=True)


if __name__ == "__main__":
    main()
