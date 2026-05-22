from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List

from .config import channel_labels


CHANNEL_ORDER = ["ai", "finance", "tech"]


def build_digest(title: str, items_by_channel: Dict[str, Iterable]) -> str:
    labels = channel_labels()
    lines: List[str] = [
        f"# {title}",
        "",
        "这是一份自动生成的知识雷达草稿。发送前建议快速检查标题、来源和重要性判断。",
        "",
    ]

    for channel in CHANNEL_ORDER:
        label = labels.get(channel, channel)
        items = list(items_by_channel.get(channel, []))
        lines.append(f"## {label}")
        lines.append("")

        if not items:
            lines.append("暂无精选内容。")
            lines.append("")
            continue

        for index, item in enumerate(items, start=1):
            lines.extend(
                [
                    f"{index}. {item['title']}",
                    f"来源：{item['source_name']}",
                    f"看点：{item['one_liner']}",
                    f"为什么重要：{item['importance']}",
                    f"不确定性：{item['uncertainty']}",
                    f"原文：{item['url']}",
                    "",
                ]
            )

    lines.extend(
        [
            "---",
            "提示：金融相关内容仅用于信息参考，不构成投资建议。",
        ]
    )
    return "\n".join(lines).strip() + "\n"


def digest_title(now: datetime) -> str:
    return f"今日知识雷达 {now.strftime('%Y-%m-%d')}"


def write_preview(output_dir: Path, title: str, content: str) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    safe_title = title.replace(" ", "_").replace("/", "-")
    path = output_dir / f"{safe_title}.md"
    path.write_text(content, encoding="utf-8")
    return path
