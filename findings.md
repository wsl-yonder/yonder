# Findings

## 2026-05-10

- GitHub 官方页面通常禁止第三方 iframe 嵌入，因此项目详情需要站内阅读版兜底。
- 现有 AI 数据在 `src/yonder/ai_news.py`，字段包含 `rank/title/source/category/summary/detail/url/date`，适合直接映射为频道卡片和详情。
- 当前频道页面主要由 `src/yonder/web.py` 内联 HTML/CSS/JS 渲染，后续最好逐步抽出共享渲染器，避免每个频道复制一整套页面代码。
