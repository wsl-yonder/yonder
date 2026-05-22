import json
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional

from .github_demo import GITHUB_DEMO_FETCHED_AT, GITHUB_PROJECTS


GITHUB_SEARCH_API = "https://api.github.com/search/repositories"
CACHE_RELATIVE_PATH = Path("data/github_trending.json")


def _today_utc() -> datetime:
    return datetime.now(timezone.utc)


def _tech_label(repo: Dict[str, object]) -> List[str]:
    labels = []
    language = repo.get("language")
    if language:
        labels.append(str(language))
    for topic in repo.get("topics") or []:
        if len(labels) >= 4:
            break
        labels.append(str(topic))
    return labels or ["开源项目"]


def _cn_project_name(repo: Dict[str, object]) -> str:
    return str(repo.get("name") or repo.get("full_name") or "GitHub 项目")


def _has_cjk(text: str) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in text)


def _description_to_chinese(description: str, repo: Dict[str, object]) -> str:
    text = " ".join((description or "").split())
    lower = text.lower()
    full_name = str(repo.get("full_name") or "").lower()
    repo_name = str(repo.get("name") or "").lower()
    repo_rules = {
        "nexu-io/open-design": "本地优先的开源设计工具，面向 AI 设计工作流和自带密钥使用场景。",
        "hkuds/cli-anything": "把任意任务包装成命令行能力，让工具和 AI 代理更容易调用。",
        "gitlawb/openclaude": "一个可在多环境运行的 Claude/AI 工具入口，强调灵活接入不同能力。",
        "alexsjones/llmfit": "帮助在本机硬件上筛选可运行的大模型和服务商，一条命令找到合适方案。",
        "anthropics/financial-services": "面向金融服务场景的 Python 工具项目，聚焦行业数据和工作流示例。",
        "nvidia/nemoclaw": "在 NVIDIA OpenShell 中更安全地运行 OpenClaw，并接入托管推理能力。",
        "googleworkspace/cli": "Google Workspace 命令行工具，覆盖 Drive、Gmail、Calendar、Sheets、Docs 等服务。",
    }
    if full_name in repo_rules:
        return repo_rules[full_name]
    if repo_name == "cli-anything":
        return repo_rules["hkuds/cli-anything"]
    if not text:
        topics = "、".join(str(topic) for topic in (repo.get("topics") or [])[:3])
        language = repo.get("language") or "多语言"
        return f"一个 {language} 项目，重点方向是 {topics or '工具与工程能力'}。"
    if _has_cjk(text):
        return text

    rules = [
        ("fastest repo", "围绕 Codex 风格开发体验的 Rust 工具项目，主打高速迭代和命令行工程工作流。"),
        ("claude code setup", "复刻 Claude Code 工作台配置，把多种工程角色和工具组织成可复用流程。"),
        ("ai agents running research", "让 AI 代理自动运行研究实验，围绕单 GPU nanochat 训练做自动化探索。"),
        ("design.md", "收集不同品牌风格的 DESIGN.md 文件，帮助编码代理生成更贴近设计系统的界面。"),
        ("manage agents", "用于管理工作场景中 AI 代理的开源应用，把代理协作放进统一工作台。"),
        ("cuts 65% of tokens", "通过极简表达压缩对话 token，用更短文本保留工程协作信息。"),
        ("memory", "面向 AI 长期记忆的开源系统，关注记忆存储、检索和上下文注入。"),
        ("text measurement", "面向文本测量与排版的工具，适合复杂编辑器、创意排版和可视化界面。"),
        ("knowledge graph", "把代码、文档和多模态资料转成可查询知识图谱，方便理解大型项目。"),
        ("job search", "把求职流程做成可运营系统，覆盖岗位追踪、材料生成和进度管理。"),
        ("agent skills", "整理工程化 AI 代理技能，让编码助手按成熟流程完成实际任务。"),
        ("google workspace cli", "Google Workspace 命令行工具，覆盖 Drive、Gmail、Calendar、Sheets、Docs 等服务。"),
        ("command-line", "把常用服务和工作流封装进命令行，方便开发者和 AI 代理调用。"),
        ("local ai", "帮助用户根据本机硬件选择可运行的本地模型和推理方案。"),
        ("autonomous ai personal assistant", "面向自主个人助手的基础设施，强调快速、小型和跨平台部署。"),
        ("financial", "面向金融场景的开源工具，聚焦数据、分析或行业工作流。"),
        ("coding agents", "面向编码代理的工程工具，帮助团队管理自动化实现过程。"),
    ]
    for key, cn in rules:
        if key in lower:
            return cn

    terms = []
    for word in text.replace("/", " ").replace("-", " ").replace("_", " ").split():
        clean = "".join(char for char in word if char.isalnum() or char in {"+", "#"})
        if len(clean) >= 3 and clean.lower() not in {"the", "and", "for", "with", "that", "this", "from"}:
            terms.append(clean)
        if len(terms) >= 3:
            break
    focus = "、".join(terms) if terms else (repo.get("language") or "工程能力")
    return f"根据仓库简介整理：项目围绕 {focus} 展开，具体功能以 README 为准。"


def _cn_summary(repo: Dict[str, object]) -> str:
    return _description_to_chinese(str(repo.get("description") or ""), repo)


def _cn_detail(repo: Dict[str, object]) -> str:
    full_name = repo.get("full_name") or repo.get("name") or "unknown/repo"
    stars = int(repo.get("stargazers_count") or 0)
    forks = int(repo.get("forks_count") or 0)
    created_at = str(repo.get("created_at") or "")[:10] or "未知时间"
    topics = "、".join(str(topic) for topic in (repo.get("topics") or [])[:6]) or "暂无 topic"
    return (
        f"{full_name} 创建于 {created_at}，当前约 {stars:,} stars、{forks:,} forks。"
        f"技术标签：{topics}。简介来自仓库 description 的中文整理；点击原站可查看 README、issue 和 release。"
    )


def _normalize_repo(repo: Dict[str, object], rank: int) -> Dict[str, object]:
    return {
        "rank": rank,
        "name": _cn_project_name(repo),
        "repo": repo.get("full_name") or repo.get("html_url") or repo.get("name"),
        "stars": int(repo.get("stargazers_count") or 0),
        "tech": _tech_label(repo),
        "summary": _cn_summary(repo),
        "detail": _cn_detail(repo),
        "url": repo.get("html_url") or "https://github.com",
        "created_at": str(repo.get("created_at") or "")[:10] or "时间未知",
    }


def github_cache_path(project_root: Path) -> Path:
    return project_root / CACHE_RELATIVE_PATH


def fetch_github_trending(limit: int = 50, since: Optional[datetime] = None) -> List[Dict[str, object]]:
    since = since or (_today_utc() - timedelta(days=90))
    query = f"created:>={since.date().isoformat()}"
    params = urllib.parse.urlencode(
        {
            "q": query,
            "sort": "stars",
            "order": "desc",
            "per_page": min(max(limit, 1), 100),
        }
    )
    request = urllib.request.Request(
        f"{GITHUB_SEARCH_API}?{params}",
        headers={
            "User-Agent": "KnowledgeRadar/0.1",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.load(response)
    return [_normalize_repo(repo, index) for index, repo in enumerate(payload.get("items", []), start=1)]


def update_github_cache(project_root: Path, limit: int = 50) -> Dict[str, object]:
    items = fetch_github_trending(limit=limit)
    payload = {
        "fetched_at": _today_utc().astimezone().strftime("%Y-%m-%d %H:%M"),
        "window": "近 3 个月创建 · stars 排序",
        "items": items,
    }
    path = github_cache_path(project_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def load_github_projects(project_root: Path, max_age_hours: int = 24, min_items: int = 50) -> Dict[str, object]:
    path = github_cache_path(project_root)
    if path.exists():
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            fetched_at = datetime.strptime(payload.get("fetched_at", ""), "%Y-%m-%d %H:%M").astimezone()
            age_hours = (_today_utc().astimezone() - fetched_at).total_seconds() / 3600
            if age_hours <= max_age_hours and len(payload.get("items") or []) >= min_items:
                return payload
        except (ValueError, TypeError, json.JSONDecodeError, OSError):
            pass

    try:
        return update_github_cache(project_root, limit=min_items)
    except Exception:
        return {
            "fetched_at": GITHUB_DEMO_FETCHED_AT,
            "window": "静态兜底",
            "items": GITHUB_PROJECTS[:20],
        }
