"""Generate Pixabay-backed covers for AI news articles."""

from __future__ import annotations
import sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from knowledge_radar.ai_news import AI_ARTICLES
from generate_covers import composite_cover, load_pixabay_key

OUT_DIR = ROOT / "static" / "assets" / "ai" / "covers"
WIDTH, HEIGHT = 960, 540

AI_KEYWORDS: dict[int, list[str]] = {
    1:  ["neural network", "brain", "digital mind", "transcendence", "singularity"],
    2:  ["open book", "knowledge", "wisdom", "library of alexandria", "illumination"],
    3:  ["dna helix", "molecular", "cells", "biology", "microscope", "laboratory"],
    4:  ["majestic beast", "evolution", "pack", "savanna", "wild", "nature spirit"],
    5:  ["parliament", "law", "justice", "balance", "civilization", "governance"],
    6:  ["forge", "anvil", "power core", "energy", "industrial", "furnace"],
    7:  ["orchard", "apple tree", "knowledge fruit", "garden", "eden", "harvest"],
    8:  ["terminal", "code", "hacker", "digital", "matrix", "keyboard warrior"],
    9:  ["great wall", "ancient scroll", "dragon", "ink brush", "eastern", "mandate"],
    10: ["deep ocean", "abyss", "leviathan", "trench", "underwater", "bioluminescent"],
    11: ["stained glass", "cathedral", "pixels", "digital church", "revelation", "holographic"],
    12: ["grand archive", "floating library", "wisdom", "books", "sanctuary", "athenaeum"],
    13: ["alchemist lab", "elixir", "transmutation", "philosopher stone", "potion", "gold"],
    14: ["titan forge", "automaton", "clockwork", "steam", "mechanical giant", "iron"],
    15: ["dojo", "training ground", "sparring", "mastery", "martial arts", "discipline"],
    16: ["concert hall", "symphony", "orchestra", "harmony", "composition", "crescendo"],
    17: ["observatory", "telescope", "stars", "cosmos", "astronomer", "celestial"],
    18: ["ink painting", "landscape", "misty mountains", "watercolor", "scroll", "zen"],
    19: ["round table", "knights", "protocol", "alliance", "banner", "chivalry"],
    20: ["lightning bolt", "speed", "energy", "electricity", "thunder", "spark"],
    21: ["peace treaty", "olive branch", "parchment", "diplomacy", "two towers", "accord"],
    22: ["temple of healing", "caduceus", "serpent", "medicine", "sanctuary", "herbs"],
    23: ["phoenix", "rebirth", "fire bird", "renaissance", "eastern phoenix", "vermilion"],
    24: ["stone tablet", "chisel", "carving", "foundation", "granite", "inscription"],
    25: ["third eye", "vision quest", "enlightenment", "pineal", "awakening", "crown chakra"],
    26: ["agora", "forum", "debate", "democracy", "assembly", "civic hall"],
    27: ["gemstone", "crystal cave", "mineral", "underground", "treasure", "diamond"],
    28: ["world tree", "genesis", "creation", "planets", "cosmic egg", "yggdrasil"],
    29: ["windmill", "tulip field", "canal", "european", "pastoral", "wind power"],
    30: ["watchtower", "sentinel", "beacon", "lighthouse", "vigil", "guard post"],
    31: ["silk road", "caravan", "trade", "spice market", "cultural exchange", "oasis"],
    32: ["atlas", "cartography", "compass", "navigation", "earth", "meridian"],
}


def main():
    api_key = load_pixabay_key()
    if not api_key:
        print("PIXABAY_API_KEY not set")
        return

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    POOL = ROOT / "static" / "assets" / "ai" / "pool"
    POOL.mkdir(parents=True, exist_ok=True)

    succeeded = 0
    for article in AI_ARTICLES:
        rank = article["rank"]
        title = article["title"]
        keywords = AI_KEYWORDS.get(rank, ["technology", "future", "abstract"])
        output_path = OUT_DIR / f"cover-{rank:02d}.jpg"

        print(f"\n[{rank:02d}] {title[:40]}...")
        print(f"  keywords: anime illustration {' '.join(keywords[:5])}")

        # Build a project-like dict for the existing pipeline
        project = {"rank": rank, "name": title, "repo": article["source"], "tech": [article["category"]]}

        # Inline search since we don't use the github pool
        import urllib.request, json
        query = "+".join(k.replace(" ", "+") for k in ["anime", "illustration"] + keywords[:4])
        url = (f"https://pixabay.com/api/?key={api_key}&q={query}"
               f"&image_type=illustration&orientation=horizontal"
               f"&min_width=800&safesearch=true&per_page=3")
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "KnowledgeRadar/1.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                hits = json.loads(resp.read().decode()).get("hits", [])
        except Exception as e:
            print(f"  Search error: {e}")
            continue

        if not hits:
            print(f"  No results")
            continue

        # Download to pool
        img_url = hits[0]["largeImageURL"]
        bg_path = POOL / f"article-{rank:02d}.jpg"
        if not bg_path.exists():
            try:
                req2 = urllib.request.Request(img_url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req2, timeout=30) as resp2:
                    bg_path.write_bytes(resp2.read())
                print(f"  Downloaded bg: {bg_path.stat().st_size} bytes")
            except Exception as e:
                print(f"  Download error: {e}")
                continue

        if composite_cover(bg_path, project, output_path):
            print(f"  ✓ {output_path.name}")
            succeeded += 1
            time.sleep(0.5)

    print(f"\nDone: {succeeded}/32 AI covers → {OUT_DIR}")


if __name__ == "__main__":
    main()
