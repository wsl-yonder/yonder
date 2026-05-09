# 今日宜闻 — 设计文档

## 概述

一个面向个人和朋友的 AI、科技、金融信息雷达。当前阶段以本地网页 Dashboard 为主，展示精选内容和日报预览。

## 页面结构

### 首页 `/`

- 全屏草坪动漫背景（`pastoral-4k.png`），轻微风感动画
- 居中 CTA："你渴望力量吗？"（Fredoka 字体，白色，阴影），链接到 GitHub 页
- 副标题："获取最新 AI · 科技 · 金融资讯，每日精选，安静阅读。"
- 底部装饰文字和浮动快捷按钮（内容、分享、进入）
- 导航栏：今日宜闻 | 首页 | GitHub | AI | 金融 | 科技 | 生活 | 小站

### GitHub 页 `/github`

- 科幻风顶部横幅（cyberpunk 城市夜景），占页面高度 21vh
- 标题 "GitHub 乐子雷达"，描述文本说明页面定位
- "热门项目" 区块描述具体内容构成（约 3/4 行宽）
- 32 个项目，4 列卡片网格（响应式：>1120px 4 列，>960px 2 列，移动端 1 列）
- 每张卡片：动漫插画封面（16:9）→ 圆圈编号 → 标题 → 简介 → 上架日期 + star 数
- 页脚诗句："海阔凭鱼跃，天高任鸟飞。"
- 数据来源：`src/knowledge_radar/github_demo.py`（手动维护的 32 个高星项目）

### AI 页 `/ai`

- AI 主题顶部横幅（神经网络风格），与 GitHub 页同布局
- 标题 "AI 雷达"，描述文本说明页面定位
- "本周 AI" 区块描述具体焦点话题（约 3/4 行宽）
- 32 篇文章，4 列卡片网格
- 每张卡片：动漫插画封面 → 右上角分类标签 → 圆圈编号 → 标题 → 简介 → 来源 + 日期
- 页脚诗句："大鹏一日同风起，扶摇直上九万里。"
- 数据来源：`src/knowledge_radar/ai_news.py`（手动维护的 32 条周精选）

## 视觉规范

### 字体

- 标题：Fredoka（Google Fonts）
- 正文：Nunito + PingFang SC
- 代码/技术标签：系统等宽字体

### 色彩

- 主色调：青色系 `#176d81` / `#13a8c2`
- 背景：浅灰蓝 `#f5fafb`
- 卡片阴影：`0 14px 34px rgba(28,75,92,.1)`
- 文字：深灰蓝 `#264650`、描述灰 `#597782`
- 圆圈编号：`#316473` 底 + 白色字

### 布局

- 最大内容宽度 1320px，水平居中
- 卡片网格 `grid-template-columns: repeat(4, minmax(0, 1fr))`
- 卡片间距 28px × 20px
- 封面比例 `aspect-ratio: 16/9`，圆角 10px
- 浏览器 chrome 色统一白色

## 封面系统

### 生成管线

```
项目数据 (github_demo.py / ai_news.py)
    ↓
专属关键词 (PROJECT_KEYWORDS / AI_KEYWORDS)
    ↓
Pixabay API 搜图 (anime + illustration + style + keywords)
    ↓
亮度过滤 (>80) + MD5 去重 + 本地缓存
    ↓
Pillow 裁切至 960×540 → JPG 质量 92
    ↓
static/assets/{github,ai}/covers/cover-NN.jpg
```

### 关键参数

- 输出尺寸：960×540（16:9）
- 图片来源：Pixabay，illustration 类型，横向，safesearch
- 搜索风格轮换：bright / dreamy / vivid / colorful
- 每页请求 10 张，随机打乱后逐一筛选
- 本地 pool 缓存以节省 API 调用（已 gitignore）

### 兜底

- GitHub 页：若无 JPG，回退到 `anime-thumbs/thumb-XX.svg`
- AI 页：暂无 SVG 兜底

### 一键重生成

```bash
PYTHONPATH=src python3 scripts/generate_covers.py       # GitHub
PYTHONPATH=src python3 scripts/generate_ai_covers.py     # AI
PYTHONPATH=src python3 scripts/generate_covers.py --rank 1  # 单张
```

## 资产目录

```
static/assets/
├── scene/pastoral-4k.png    首页背景
├── github/
│   ├── banner.jpg           GitHub 页顶部横幅
│   ├── covers/cover-01..32.jpg
│   └── pool/                Pixabay 缓存（gitignore）
├── ai/
│   ├── banner.jpg           AI 页顶部横幅
│   ├── covers/cover-01..32.jpg
│   └── pool/                Pixabay 缓存（gitignore）
├── anime-thumbs/            SVG 兜底封面
└── fonts/                   字体文件
```

## 数据模块

### GitHub 项目 (`github_demo.py`)

```python
{
    "rank": int,        # 1-32
    "name": str,        # 中文名
    "repo": str,        # owner/repo
    "stars": int,       # GitHub stars
    "tech": [str],      # 技术栈标签
    "summary": str,     # 一句话简介
    "detail": str,      # 详细说明（隐藏）
    "url": str,         # 项目链接
    "created_at": str,  # YYYY-MM-DD
}
```

### AI 新闻 (`ai_news.py`)

```python
{
    "rank": int,        # 1-32
    "title": str,       # 标题（≤20 字）
    "source": str,      # 来源
    "category": str,    # 分类标签
    "summary": str,     # 一句话摘要
    "detail": str,      # 详细说明（隐藏）
    "url": str,         # 原文链接
    "date": str,        # YYYY-MM-DD
}
```

## 待建设

- 金融、科技、生活页面（导航已有入口，数据模块和模板待建）
- AI 页 SVG 兜底封面
- 21-32 号项目 SVG 兜底封面
- 内容页文章详情展开
- 数据动态更新（当前为手动维护的静态数据）
