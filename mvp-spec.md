# Yonder 推送助手 MVP Spec

创建日期：2026-05-09

## 1. 背景

用户希望通过网页 Dashboard 持续获取 AI、金融和科技相关的新知识，并后续分享给自己和朋友。

本阶段实现网页 Dashboard MVP。核心验证点是：系统是否能稳定产出值得阅读的精选内容，并在网页中提供舒服的浏览、筛选和日报预览体验。

## 2. MVP 目标

每天生成 AI、金融、科技精选内容，包含摘要、重要性解释和原文链接，并通过本地网页 Dashboard 展示。

## 3. 非目标

- 暂不做完整账号系统。
- 暂不做复杂账号系统。
- 暂不支持朋友自助订阅。
- 暂不做实时全量新闻监控。
- 暂不抓取需要登录或付费墙后的内容。
- 暂不做 WxPusher 推送。

## 4. 用户场景

### 4.1 网页浏览

用户打开网页 Dashboard，快速浏览 AI、金融、科技领域的重要变化。

### 4.2 日报预览

系统生成日报后，用户可以在网页侧边栏查看最新日报预览。

### 4.3 后续分享

当内容质量稳定后，再考虑公开网页、登录权限、链接分享或其他推送渠道。

## 5. 信息源范围

### AI

- AI 公司官方博客：OpenAI、Anthropic、Google DeepMind、Meta AI 等。
- 论文与模型平台：arXiv、Hugging Face、Papers with Code。
- 开发者社区：GitHub Trending、Hacker News。

### 金融

- 市场数据与新闻 RSS。
- 公司财报、SEC filings、宏观数据源。
- 初期优先聚焦美股、科技股、AI 相关上市公司和宏观利率事件。

### 科技

- 科技媒体 RSS。
- 重要公司工程博客。
- GitHub Release、开发者生态趋势。

## 6. 内容处理流程

1. 采集信息源，获取标题、链接、发布时间、来源、摘要或正文片段。
2. 基于 URL、标题和内容相似度去重。
3. 分类到 AI、金融、科技。
4. 为每条内容生成：
   - 一句话看点
   - 3 条以内要点
   - 为什么重要
   - 风险或不确定性
5. 按新鲜度、可信度、影响力、相关性评分。
6. 每个频道选出 3-5 条候选。
7. 生成日报预览。
8. 在 Dashboard 展示精选内容、搜索、频道筛选和日报预览。

## 7. 推送格式

```md
# 今日知识雷达

## AI
1. 标题
看点：...
为什么重要：...
原文：...

## 金融
1. 标题
看点：...
影响：...
原文：...

## 科技
1. 标题
看点：...
为什么重要：...
原文：...
```

## 8. 系统模块

### Source Manager

维护信息源配置，包括名称、类型、URL、频道、可信度和启用状态。

### Collector

定时抓取 RSS/API 内容，保存原始条目。

### Processor

负责去重、分类、摘要、评分和精选。

### Digest Builder

根据精选条目生成 Markdown 或 HTML 推送内容。

### Dashboard Server

启动本地网页服务，展示统计、频道筛选、搜索、精选卡片和日报预览。

### Digest CLI

生成本地预览文件或在命令行输出日报，供用户确认。

## 9. 数据模型草案

### sources

- id
- name
- url
- type: rss | api | webpage
- channel: ai | finance | tech
- credibility_score
- enabled
- created_at

### articles

- id
- source_id
- title
- url
- published_at
- raw_summary
- content_hash
- channel
- status
- created_at

### processed_items

- id
- article_id
- one_liner
- bullet_points
- importance
- uncertainty
- score
- created_at

### digests

- id
- title
- content_markdown
- status: draft | sent | skipped
- generated_at
- sent_at

## 10. 配置项

- `DATABASE_URL`
- `DIGEST_TIMEZONE`
- `DIGEST_MAX_ITEMS_PER_CHANNEL`
- `MAX_ITEMS_PER_SOURCE`
- `OPENAI_API_KEY` 或其他摘要模型密钥，后续接入

## 11. 验收标准

- 可以从至少 6 个信息源抓取内容。
- 可以生成 AI、金融、科技三个频道的日报草稿。
- 每条精选内容包含看点、重要性说明和原文链接。
- 可以启动本地 Dashboard。
- Dashboard 支持频道筛选、搜索和最新日报预览。
- 失败时有明确错误日志，不静默丢失。

## 12. 后续阶段

### Phase 2: Dashboard 增强

- 文章详情页。
- 手动选择加入日报。
- 收藏、隐藏、已读。
- 推送历史。

### Phase 3: 分享和订阅

- 公开访问或登录。
- 朋友分频道浏览。
- 链接分享。

### Phase 4: 实时重大事件提醒

- 重大模型发布。
- 财报异动。
- 宏观政策事件。
- 科技公司收购、融资、产品发布。
