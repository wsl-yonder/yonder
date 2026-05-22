import shutil
from pathlib import Path
from typing import Callable, Dict, Optional

from .config import load_settings
from .web import (
    render_ai_news,
    render_finance_page,
    render_github_demo,
    render_landing,
    render_music_page,
    render_novels_page,
    render_scene_demo,
)


def _write_html(output_root: Path, route: str, html: str) -> Path:
    if route == "/":
        path = output_root / "index.html"
    else:
        path = output_root / route.strip("/") / "index.html"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")
    return path


def _copy_static(project_root: Path, output_root: Path) -> None:
    source = project_root / "static"
    target = output_root / "static"
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(
        source,
        target,
        ignore=shutil.ignore_patterns("pool", ".DS_Store"),
    )


def export_static_site(project_root: Path, output_dir: Optional[Path] = None, clean: bool = True) -> Dict[str, object]:
    settings = load_settings(project_root)
    output_root = output_dir or (project_root / "dist")
    if clean and output_root.exists():
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    pages: list[tuple[str, Callable[[], str]]] = [
        ("/", render_landing),
        ("/github", render_github_demo),
        ("/daily", render_github_demo),
        ("/ai", lambda: render_ai_news(settings)),
        ("/finance", lambda: render_finance_page(settings)),
        ("/music", render_music_page),
        ("/novels", render_novels_page),
        ("/scene", render_scene_demo),
        ("/background", render_scene_demo),
    ]

    written = []
    for route, renderer in pages:
        written.append(_write_html(output_root, route, renderer()))

    _copy_static(project_root, output_root)
    return {
        "output_root": output_root,
        "pages": written,
        "static_root": output_root / "static",
    }
