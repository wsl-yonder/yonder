# Decision Log

## 2026-05-09

### 先做推送助手，再做 Dashboard

决定：第一阶段优先实现推送助手 MVP。

原因：

- 产品核心价值是稳定产出高质量摘要并送达微信。
- Dashboard 可以后置，等内容质量和推送链路稳定后再做。
- 先做推送助手能更快验证信息源、摘要质量和 WxPusher 分发效果。

### 推送先发给自己

决定：第一版只发送给用户本人，朋友订阅放到后续阶段。

原因：

- 避免内容质量不稳定时打扰朋友。
- 方便调整推送格式、频率和选题偏好。
- WxPusher UID 单发比 Topic 群发更适合测试。

### 第一版使用 Python 标准库

决定：推送助手 MVP 先使用 Python 3.9 标准库实现，暂不引入第三方依赖。

原因：

- 当前目标是尽快跑通采集、入库、日报生成和推送链路。
- SQLite、HTTP 请求、RSS/Atom XML 解析都可以先用标准库完成。
- 后续接入 LLM 摘要、网页 Dashboard 时再引入更重的依赖。

### 转向网页 Dashboard

决定：放弃 WxPusher 作为第一体验，改为优先通过网页 Dashboard 展示内容。

原因：

- WxPusher 长内容在微信里需要跳转平台查看，阅读体验不够直接。
- 当前项目的核心价值更像“知识浏览和筛选”，网页更适合承载卡片、搜索、频道和日报预览。
- 推送可以后续作为可选提醒渠道，而不是主入口。

### 首页与内容页风格方向

决定：网站先采用“今日宜闻”这个名字，首页做成极简入口页，内容页做成类 B 站首页的信息流。

原因：

- 首页需要先传达氛围，不要用复杂卡片遮挡背景。
- 内容页需要承载大量项目，四列信息流比三栏 Dashboard 更适合快速浏览。
- 顶部横幅继续使用绿色二次元风景，与首页背景保持同一世界观。

### GitHub Demo 先用自动生成封面

决定：为 GitHub Top 20 Demo 增加自动生成封面脚本 `scripts/generate_project_thumbs.py`，根据项目元数据生成对应动漫科技风 SVG。

原因：

- 外部免费图库和随机动漫 API 风格不稳定，且容易出现角色图、版权和安全筛选问题。
- SVG 本地生成稳定、加载快、可控，适合当前 demo 阶段。
- 目前封面相似度仍偏高，下一步需要评估 ComfyUI、InvokeAI、Fooocus、Stable Diffusion WebUI Forge 等专门图片生成工具，生成更有差异化的项目封面。

### 封面生成管线：Pixabay + SVG 双后端

决定：建立统一的封面生成管线 `scripts/generate_covers.py`，主后端用 Pixabay API 搜图叠加项目文字，兜底用现有 SVG 生成。

原因：

- 评估了 ComfyUI、Draw Things、qwen-image-mps 等本地做图方案，安装配置重、模型下载慢，不适合当前阶段快速迭代。
- 评估了 waifu.pics、Nekos API、sanana 等免费动漫 API，内容以角色图为主，不适合项目封面场景。
- Pixabay 免费 API 提供 600 万+图片，包含动漫风景、科技抽象等类别，可商用无需署名，适合做背景底图。
- SVG 生成作为无依赖兜底，确保任何时候都能跑通。

架构：

- `generate_covers.py` — GitHub 封面入口，支持 --rank 单张、--dry-run 预览
- `generate_ai_covers.py` — AI 新闻封面入口，同样支持 --rank
- Pixabay 后端：按内容专属关键词搜图 → 亮度过滤（>90）→ MD5 去重 → 风格随机（bright/dreamy/vivid/colorful）→ 本地 pool 缓存
- 封面为纯净背景图，不叠加任何文字；CSS 负责圆圈编号和文字排版
- `.env` 中配置 `PIXABAY_API_KEY=`（可选，不配则走 SVG 兜底）
- 网页优先使用 `github/covers/cover-XX.jpg`，无则回退 `anime-thumbs/thumb-XX.svg`

### 网站整体设计

决定：确立"今日宜闻"三页站点结构和统一设计语言。

页面结构：
- **首页 (/)** — 入口页，二次元草坪全屏背景，"你渴望力量吗？" CTA + 副标题
- **GitHub (/github)** — 32 个近三月高星项目，科幻风 banner，4 列卡片网格
- **AI (/ai)** — 32 条周精选 AI 新闻，AI 主题 banner，同布局

设计原则：
- 导航栏统一：首页 | GitHub | AI | 金融 | 科技 | 生活 | 小站（后四个待建）
- 封面统一动漫插画风，按内容匹配，无重复，底色明亮
- 卡片层级：纯封面 → 圆圈编号 → 标题 → 简介 → 来源/日期
- 信息双层：Banner 描述页面定位（这是什么页），Feed-head 描述内容构成（具体有什么）
- 页脚统一诗句收尾，GitHub 用"海阔凭鱼跃，天高任鸟飞"，AI 用"大鹏一日同风起，扶摇直上九万里"
- 浏览器 chrome 色统一白色，不取页面背景色
- 内容页标题控制在 14 寸屏一行内，描述约 3/4 行宽

资产组织：
```
static/assets/
├── github/          GitHub 页面专用
│   ├── banner.jpg   科幻风顶部横幅
│   ├── covers/      32 张项目封面（960×540 JPG）
│   └── pool/        Pixabay 下载缓存（gitignore）
├── ai/              AI 页面专用
│   ├── banner.jpg   AI 主题顶部横幅
│   ├── covers/      32 张新闻封面（960×540 JPG）
│   └── pool/        Pixabay 下载缓存（gitignore）
├── scene/           首页草坪背景
└── anime-thumbs/    SVG 兜底封面
```

后续页面（金融、科技、生活）复用同一管线：建数据模块 → 配关键词 → 跑生成脚本 → 加路由和模板。

