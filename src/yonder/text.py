import re
from html import unescape


TAG_RE = re.compile(r"<[^>]+>")
SPACE_RE = re.compile(r"\s+")


def clean_text(value: str) -> str:
    value = unescape(value or "")
    value = TAG_RE.sub(" ", value)
    value = SPACE_RE.sub(" ", value)
    return value.strip()


def short_text(value: str, max_chars: int) -> str:
    value = clean_text(value)
    if len(value) <= max_chars:
        return value
    return value[: max_chars - 1].rstrip() + "..."


def first_sentence(value: str, fallback: str, max_chars: int = 120) -> str:
    text = clean_text(value)
    if not text:
        text = clean_text(fallback)
    parts = re.split(r"(?<=[.!?。！？])\s+", text)
    return short_text(parts[0] if parts else text, max_chars)
