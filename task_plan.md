# 今日宜闻频道浏览模式改造计划

## Goal

把 AI、金融、科技、生活频道都做成和 GitHub 页一致的体验：列表态展示卡片，点击后进入当前页面内的详情浏览态，左侧显示固定控制按钮和可滚动目录，右侧显示站内阅读版或可嵌入的外部页面。

## Save Rule

每完成一个频道：
- 代码必须已落盘。
- 运行至少一次语法或页面输出验证。
- 更新 `progress.md` 记录完成内容和验证结果。
- 更新本计划中的频道状态。

## Channel Status

| Channel | Status | Notes |
| --- | --- | --- |
| GitHub | complete | 已改为 GitHub Search API 每日刷新近 3 个月高星项目，静态列表仅作兜底。 |
| AI | complete | 已切换为国内来源优先：量子位 RSS + 36氪 AI 列表，每日采集入库后展示。 |
| 金融 | complete | 已切换为国内财经滚动源，每日采集 A股/基金/资金流等近 1 日消息。 |
| 科技 | removed | 用户要求先删除，导航与路由已移除。 |
| 生活 | removed | 用户要求先删除，导航与路由已移除。 |
| 音乐 | complete | 已新增 `/music`，网易云式紧凑歌单 + 白色播放器态；使用 iTunes 公开试听源 20 首中文热歌，支持关闭停止、缩小继续播放和迷你播放状态。 |
| 小说 | complete | 已新增 `/novels`，支持本地 Demo 与 Project Gutenberg 中文公版书源切换、搜索、筛选、详情、目录和阅读模式。 |

## Decisions

- GitHub 等禁止 iframe 的站点展示站内阅读版。
- 其它来源可以保留 iframe 尝试，但必须有站内详情兜底。
- 单页完成后先保存进度，再继续下一个频道。

## Final Route Check

| Route | Result |
| --- | --- |
| `/ai` | ok, database-backed domestic items |
| `/finance` | ok, database-backed domestic items |
| `/music` | ok, 20 iTunes preview tracks |
| `/novels` | ok, 12 demo novels |
| `/tech` | removed, 404 |
| `/life` | removed, 404 |
