"""Generate Pixabay-backed covers for AI news articles."""

from __future__ import annotations
import sys, time, random, hashlib, urllib.request, json
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
    2:  ["open book", "sunlit library", "knowledge tree", "wisdom", "golden light"],
    3:  ["dna helix", "molecular", "cells", "biology", "microscope", "laboratory"],
    4:  ["majestic beast", "sunlit savanna", "evolution", "golden plains", "wild spirit", "daybreak"],
    5:  ["parliament", "law", "justice", "balance", "civilization", "governance"],
    6:  ["golden forge", "crystal energy", "sunlit factory", "glowing core", "steampunk"],
    7:  ["orchard", "apple tree", "knowledge fruit", "garden", "eden", "harvest"],
    8:  ["terminal", "code", "hacker", "digital", "matrix sunrise", "glowing screen"],
    9:  ["great wall", "ancient scroll", "dragon", "ink brush", "eastern", "mandate"],
    10: ["deep ocean", "coral reef", "sunlit sea", "tropical", "underwater garden", "bioluminescent"],
    11: ["stained glass", "sunlit cathedral", "rainbow window", "heavenly light", "prism", "colorful"],
    12: ["grand archive", "floating library", "wisdom", "books", "sanctuary", "athenaeum"],
    13: ["alchemist lab", "elixir", "transmutation", "philosopher stone", "potion", "gold"],
    14: ["titan forge", "automaton", "clockwork", "steam", "mechanical giant", "iron"],
    15: ["dojo", "training ground", "sparring", "mastery", "martial arts", "discipline"],
    16: ["concert hall", "symphony", "orchestra", "harmony", "composition", "crescendo"],
    17: ["observatory", "telescope", "stars", "cosmos", "astronomer", "celestial"],
    18: ["ink painting", "landscape", "misty mountains", "watercolor", "scroll", "zen"],
    19: ["round table", "knights", "protocol", "alliance", "banner", "chivalry"],
    20: ["lightning bolt", "blue sky", "storm clearing", "electric rainbow", "sunlight", "spark"],
    21: ["peace treaty", "olive branch", "parchment", "diplomacy", "two towers", "accord"],
    22: ["temple of healing", "sunlit garden", "white marble", "caduceus", "serpent", "daylight"],
    23: ["phoenix", "sunrise", "golden sky", "rebirth", "morning light", "dawn"],
    24: ["stone tablet", "chisel", "carving", "foundation", "granite", "inscription"],
    25: ["third eye", "vision quest", "enlightenment", "pineal", "awakening", "crown chakra"],
    26: ["agora", "forum", "debate", "democracy", "assembly", "civic hall"],
    27: ["gemstone", "crystal garden", "prism light", "rainbow", "treasure", "sunlight"],
    28: ["world tree", "genesis", "creation", "planets", "cosmic egg", "yggdrasil"],
    29: ["windmill", "tulip field", "canal", "european", "pastoral", "wind power"],
    30: ["watchtower", "sentinel", "beacon", "lighthouse", "vigil", "guard post"],
    31: ["silk road", "caravan", "trade", "spice market", "cultural exchange", "oasis"],
    32: ["atlas", "cartography", "compass", "navigation", "earth", "meridian"],
}


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--rank", type=int, help="Generate single article by rank")
    args = parser.parse_args()

    api_key = load_pixabay_key()
    if not api_key:
        print("PIXABAY_API_KEY not set")
        return

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    POOL = ROOT / "static" / "assets" / "ai" / "pool"
    POOL.mkdir(parents=True, exist_ok=True)

    articles = AI_ARTICLES
    if args.rank:
        articles = [a for a in articles if a["rank"] == args.rank]

    succeeded = 0
    for article in articles:
        rank = article["rank"]
        title = article["title"]
        keywords = AI_KEYWORDS.get(rank, ["technology", "future", "abstract"])
        output_path = OUT_DIR / f"cover-{rank:02d}.jpg"

        print(f"\n[{rank:02d}] {title[:40]}...")
        print(f"  keywords: anime illustration {' '.join(keywords[:5])}")

        # Build a project-like dict for the existing pipeline
        project = {"rank": rank, "name": title, "repo": article["source"], "tech": [article["category"]]}

        # Inline search since we don't use the github pool
        style = random.choice(["bright colorful", "dreamy pastel", "fantasy vivid", "sunny vibrant"])
        query = "+".join(k.replace(" ", "+") for k in ["anime", "illustration"] + style.split() + keywords[:3])
        url = (f"https://pixabay.com/api/?key={api_key}&q={query}"
               f"&image_type=illustration&orientation=horizontal"
               f"&min_width=800&safesearch=true&per_page=10")
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

        # Collect existing cover hashes for dedup
        existing_hashes = set()
        for f in OUT_DIR.glob("cover-*.jpg"):
            existing_hashes.add(hashlib.md5(f.read_bytes()).hexdigest())

        # Try results, skip duplicates; use random offset to avoid same popular images
        random.shuffle(hits)
        bg_path = None
        for hit in hits[:8]:
            img_url = hit["largeImageURL"]
            test_path = POOL / f"test-{rank:02d}.jpg"
            try:
                req2 = urllib.request.Request(img_url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req2, timeout=30) as resp2:
                    test_path.write_bytes(resp2.read())
                # Check brightness
                from PIL import Image
                import statistics
                img = Image.open(test_path).convert("L")
                avg = statistics.mean(img.getdata())
                img.close()
                if avg > 90:  # bright enough
                    h = hashlib.md5(test_path.read_bytes()).hexdigest()
                    if h in existing_hashes:
                        print(f"  Skipped duplicate (hash: {h[:8]}), trying next...")
                        test_path.unlink()
                    else:
                        existing_hashes.add(h)
                        bg_path = POOL / f"article-{rank:02d}.jpg"
                        test_path.rename(bg_path)
                        print(f"  Downloaded bg: {bg_path.stat().st_size} bytes (brightness: {avg:.0f})")
                        break
                else:
                    print(f"  Skipped dark image (brightness: {avg:.0f}), trying next...")
                    test_path.unlink()
            except Exception as e:
                print(f"  Download error: {e}")
                if test_path.exists():
                    test_path.unlink()

        if not bg_path:
            print(f"  No bright enough image found")
            continue

        if composite_cover(bg_path, project, output_path):
            print(f"  ✓ {output_path.name}")
            succeeded += 1
            time.sleep(0.5)

    print(f"\nDone: {succeeded}/32 AI covers → {OUT_DIR}")


if __name__ == "__main__":
    main()
