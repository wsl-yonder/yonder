from datetime import datetime, timezone
from typing import Optional

from .models import ProcessedItem
from .text import first_sentence, short_text


CHANNEL_IMPORTANCE = {
    "ai": "关注其对模型能力、开发者生态和产品路线的影响。",
    "finance": "关注其对市场预期、风险偏好和相关资产价格的影响。",
    "tech": "关注其对产品趋势、开发者工具和科技公司竞争格局的影响。",
}


def _parse_iso_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def score_article(credibility_score: float, published_at: Optional[str], title: str) -> float:
    score = 50.0 + (credibility_score * 35.0)

    published = _parse_iso_datetime(published_at)
    if published:
        now = datetime.now(timezone.utc)
        if published.tzinfo is None:
            published = published.replace(tzinfo=timezone.utc)
        age_hours = max((now - published).total_seconds() / 3600.0, 0.0)
        score += max(0.0, 15.0 - min(age_hours / 8.0, 15.0))

    title_lower = title.lower()
    hot_terms = [
        "ai",
        "model",
        "openai",
        "nvidia",
        "fed",
        "rate",
        "earnings",
        "security",
        "release",
        "launch",
    ]
    score += min(sum(2.0 for term in hot_terms if term in title_lower), 10.0)
    return round(min(score, 100.0), 2)


def process_row(row) -> ProcessedItem:
    title = row["title"]
    raw_summary = row["raw_summary"] or ""
    channel = row["channel"]

    one_liner = first_sentence(raw_summary, title, max_chars=130)
    bullet_seed = short_text(raw_summary or title, 260)
    bullet_points = "\n".join(
        [
            f"- {short_text(title, 120)}",
            f"- {bullet_seed}",
        ]
    )
    importance = CHANNEL_IMPORTANCE.get(channel, "关注其对相关行业和用户决策的影响。")
    uncertainty = "当前基于公开信息源摘要生成，需阅读原文确认细节和上下文。"
    score = score_article(float(row["credibility_score"]), row["published_at"], title)

    return ProcessedItem(
        article_id=int(row["id"]),
        channel=channel,
        title=title,
        url=row["url"],
        source_name=row["source_name"],
        published_at=row["published_at"],
        one_liner=one_liner,
        bullet_points=bullet_points,
        importance=importance,
        uncertainty=uncertainty,
        score=score,
    )
