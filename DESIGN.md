# 今日宜闻 — 设计文档

## 1. 项目概述

面向个人和朋友的 AI、科技、金融信息雷达。从 RSS 定时采集信息源，自动去重分类评分，通过本地网页 Dashboard 展示精选内容和日报预览。

**当前阶段**：网页 Dashboard 优先。已上线首页、GitHub 页、AI 页三个页面，金融/科技/生活待建设。WxPusher 推送暂退居可选渠道。

**运行方式**：

```bash
PYTHONPATH=src python3 -m knowledge_radar.cli init-db
PYTHONPATH=src python3 -m knowledge_radar.cli run-once --print
PYTHONPATH=src python3 -m knowledge_radar.cli web
# 打开 http://127.0.0.1:8765
```

## 2. 关键设计决策

### 2.1 为什么是 Python 标准库

第一版只用 Python 3.9+ 标准库，不引入第三方依赖。SQLite、HTTP 请求、RSS/Atom XML 解析、网页服务器均用内置模块完成。Pillow 仅在封面生成时需要（可选），核心功能零依赖。

### 2.2 为什么做网页 Dashboard 而非推送

WxPusher 长内容在微信里需跳转平台查看，阅读体验不好。网页更适合承载卡片、搜索、频道筛选和日报预览。推送后续作为可选提醒渠道。

### 2.3 为什么是 Pixabay 而非本地 AI 做图

评估了 ComfyUI、Draw Things、qwen-image-mps 等方案，安装配置重、模型下载慢、不适合快速迭代。也看了 waifu.pics、Nekos API 等免费动漫 API，内容以角色图为主，不适合项目封面。Pixabay 免费 API 600 万+图片，动漫风景和科技抽象类目丰富，可商用无需署名，适合做背景底图。

### 2.4 为什么是动漫插画风

首页"今日宜闻"以二次元草坪为背景，内容页沿用同一世界观。封面统一为动漫插画风格，按内容关键词匹配差异化的 Pixabay 图片，保持整体视觉的一致性。

### 2.5 为什么封面不做文字叠加

早期版本用 Pillow 在封面上叠加项目名/排名，结果和 CSS 的叠加层冲突，形成双重黑影。改为纯净背景图后，所有文字由 CSS 负责排版——圆圈编号、标题、简介、日期均在图片下方或覆盖层中。修改文字不需要重新生成图片。

## 3. 页面结构

### 3.1 首页 `/`

- 全屏草坪动漫背景（`pastoral-4k.png`，`center bottom / cover no-repeat fixed`），轻微风感动画
- 居中 CTA："你渴望力量吗？" — Fredoka 900 粗体，白色描边阴影，链接到 `/github`
- 副标题一行："获取最新 AI · 科技 · 金融资讯，每日精选，安静阅读。"
- 底部装饰文字、浮动快捷按钮（内容、分享、进入）
- 顶部导航栏：今日宜闻 | 首页 | GitHub | AI | 金融 | 科技 | 生活 | 小站
- 浏览器 chrome 色强制白色（`html { background: #fff }` 和 `<meta name="theme-color">`），防止 Safari 提取草坪背景色

### 3.2 GitHub 页 `/github`

- 科幻风顶部横幅（cyberpunk 城市夜景），高度 21vh，`center 30% / cover`
- 导航栏 + 右上角 "近 3 个月 · Top 32"
- 标题 "GitHub 乐子雷达"
- Banner 描述："最近三个月创建、按星数排序的高星项目 Top 32。适合快速扫一眼今天开源圈又在整什么活。" — 说明页面是什么
- "热门项目"区块：标题 + 描述 — 说明具体内容构成
  - 当前："AI 编码代理 9 个、CLI 工具 4 个、设计系统与知识图谱各 3 个、个人助手与自动化 5 个，另有硬件、游戏等方向。"
- 32 个项目，4 列卡片网格
- 响应式断点：>1120px 4 列 → >820px 2 列 → 移动端 1 列
- 每张卡片：动漫插画封面（16:9，圆角 10px）→ 圆圈编号 → 标题 → 简介（2 行截断）→ 上架日期 + star 数
- 页脚：诗句 "海阔凭鱼跃，天高任鸟飞。"
- 数据来源：`src/knowledge_radar/github_demo.py` — 手动维护的 32 个项目

### 3.3 AI 页 `/ai`

- AI 主题顶部横幅（神经网络风格），高度 21vh，`center 35% / cover`
- 导航栏 + 右上角 "2026-05-10 · Top 32"
- 标题 "AI 雷达"
- Banner 描述："全球 AI 领域本周精选 32 条——大模型、开源、应用、研究与政策，一条不漏。"
- "本周 AI" 区块描述："Mythos 安全争议、NVIDIA 芯片松动、π0.7 机器人突破、AI 金融决策全败、Agent 误删生产库及裁员潮。"
- 与 GitHub 页同布局：4 列卡片，响应式相同
- 每张卡片：动漫插画封面 → 右上角分类标签（大模型/开源/AI 应用/研究/政策/硬件）→ 圆圈编号 → 标题 → 简介 → 来源 + 日期
- 页脚：诗句 "大鹏一日同风起，扶摇直上九万里。"
- 数据来源：`src/knowledge_radar/ai_news.py` — 手动维护的 32 条周精选 AI 新闻

## 4. 视觉规范

### 4.1 字体

| 用途 | 字体 | Weight |
|------|------|--------|
| 页面标题（h1） | Fredoka | 900 |
| 区块标题（h2） | Fredoka | 900 |
| 卡片标题 | Nunito | 900 |
| 正文/描述 | Nunito + PingFang SC | 400-800 |
| 圆圈编号 | Nunito | 900 |

### 4.2 色彩

```
主色调（青）  #176d81 / #13a8c2
页面背景      #f5fafb（浅灰蓝）
卡片阴影      rgba(28,75,92,.1)
正文色        #264650（深灰蓝）
描述色        #597782（中灰蓝）
圆圈编号底    #316473
分类标签底    rgba(23,109,129,.82)
首页 CTA      #fff（白色 + 深色阴影）
```

### 4.3 布局参数

```
最大内容宽度  1320px
卡片网格      grid-template-columns: repeat(4, minmax(0, 1fr))
卡片间距      28px（行）× 20px（列）
封面比例      aspect-ratio: 16/9
封面圆角      10px
封面上层渐变  linear-gradient(180deg, transparent 48%, rgba(13,38,44,.5))
顶部横幅高度  21vh（min 188px, max 256px）
```

## 5. 封面系统

### 5.1 生成管线

```
数据模块 (github_demo.py / ai_news.py)
    │
    ├─ 专属关键词 (PROJECT_KEYWORDS / AI_KEYWORDS)
    │   每个项目/文章有 4-6 个手动配好的英文搜索词
    │
    ├─ Pixabay API 搜索
    │   查询格式: anime + illustration + {随机风格} + {关键词}
    │   风格轮换: bright / dreamy / vivid / colorful（避免全命中同一张）
    │   参数: illustration 类型, 横向, min_width=800, safesearch=true, per_page=10
    │
    ├─ 质量过滤
    │   亮度 > 80（PIL 灰度均值，跳过纯黑图）
    │   MD5 去重（跳过已用于其他封面的图）
    │   随机打乱后逐一尝试 8 张候选
    │
    ├─ 本地缓存
    │   下载到 pool/ 目录（已 gitignore），二次生成时直接复用
    │
    └─ 输出
       Pillow resize → 960×540 → JPEG quality 92
       → static/assets/{github,ai}/covers/cover-NN.jpg
```

### 5.2 关键词策略

GitHub 项目关键词侧重技术具象（如 "terminal code hacker digital"），AI 新闻关键词侧重意境隐喻（如 "open book sunlit library knowledge tree"）。两类都保证英文搜索词 + "anime illustration" 前缀，使返回结果保持动漫插画风。

### 5.3 兜底

- GitHub 页 JPG 缺失时回退到 `anime-thumbs/thumb-XX.svg`（旧版 SVG 生成器）
- AI 页暂无 SVG 兜底（待补齐）

### 5.4 重新生成

```bash
PYTHONPATH=src python3 scripts/generate_covers.py          # GitHub 32 张
PYTHONPATH=src python3 scripts/generate_ai_covers.py        # AI 32 张
PYTHONPATH=src python3 scripts/generate_covers.py --rank 5  # 单张
```

### 5.5 环境依赖

`.env` 中配置 `PIXABAY_API_KEY=`（在 pixabay.com 免费注册获取）。未配置时 `generate_covers.py` 直接退出，网页使用 SVG 兜底。

## 6. 项目结构

```
knowledge-radar/
│
├── DESIGN.md                    本文件
├── README.md                    项目概述和快速开始
├── tasks.md                     任务清单
├── decision-log.md              历史决策记录
├── pyproject.toml               包配置（入口点 knowledge-radar）
├── .env / .env.example          运行配置
├── .gitignore
│
├── config/
│   └── sources.json             RSS 信息源（11 个，AI/金融/科技三个频道）
│
├── src/knowledge_radar/         主包
│   ├── cli.py                   命令行入口（init-db / collect / process / digest / web 等 8 个子命令）
│   ├── config.py                配置加载（.env + sources.json）
│   ├── models.py                数据模型（Source, FeedItem, ProcessedItem）
│   ├── db.py                    SQLite 数据库（建表 + CRUD）
│   ├── collector.py             RSS 采集和解析
│   ├── processor.py             文章评分和处理
│   ├── text.py                  文本工具（HTML 剥离、截断、首句提取）
│   ├── digest.py                Markdown 日报生成
│   ├── web.py                   网页服务器 + 全部页面模板（~1700 行）
│   ├── wxpusher.py              WxPusher 推送（已退居次要）
│   ├── github_demo.py           GitHub 32 项目静态数据
│   └── ai_news.py               AI 32 新闻静态数据
│
├── scripts/
│   ├── generate_covers.py       GitHub 封面生成（Pixabay → JPG）
│   ├── generate_ai_covers.py    AI 封面生成
│   └── generate_project_thumbs.py  SVG 封面生成（兜底）
│
├── static/assets/
│   ├── scene/pastoral-4k.png    首页草坪背景
│   ├── github/                  GitHub 页面资产
│   │   ├── banner.jpg
│   │   ├── covers/cover-01..32.jpg
│   │   └── pool/                Pixabay 缓存（gitignore）
│   ├── ai/                      AI 页面资产
│   │   ├── banner.jpg
│   │   ├── covers/cover-01..32.jpg
│   │   └── pool/                Pixabay 缓存（gitignore）
│   ├── anime-thumbs/            SVG 兜底封面
│   └── fonts/                   字体文件
│
├── data/                        SQLite 数据库文件（gitignore）
└── out/                         Markdown 日报输出
```

## 7. 数据流

```
config/sources.json
       │
       ▼
  collector.py ── RSS 抓取 → FeedItem 列表
       │
       ▼
  db.py ── content_hash 去重 → articles 表
       │
       ▼
  processor.py ── 规则评分 → processed_items 表（one_liner, bullet_points, score）
       │
       ▼
  digest.py ── 按频道 top 5 → Markdown 日报 → out/*.md
       │
       ▼
  wxpusher.py (可选) ── 推送到微信
```

GitHub 和 AI 页面不读数据库，使用静态数据模块（`github_demo.py`、`ai_news.py`），封面预先生成。

## 8. 待建设

- **金融、科技、生活页面**：导航入口已就位，需建数据模块、关键词、封面、页面模板
- **AI 页 SVG 兜底**：目前无 JPG 时封面为空
- **21-32 号项目 SVG 兜底**：SVG 生成器目前只覆盖到 20
- **数据动态更新**：GitHub 和 AI 数据当前手动维护，后续可接 API 自动刷新
- **文章详情展开**：卡片 detail 字段已存在但 display:none 隐藏
- **LLM 摘要接入**：当前评分和摘要为规则驱动，可接入模型提升质量
