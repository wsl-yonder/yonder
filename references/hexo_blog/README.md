## chagumu's blog（Hexo + Butterfly）使用文档

![77150126381](img/1771501263812.png "Hexo 博客首页")

![77150129781](img/1771501297812.png "Hexo 博客首页")

![77150134925](img/1771501349258.png "Hexo 博客首页")

原作者：[hexo_youqi: 博客样式开源](https://gitee.com/u7u7-sjh/hexo_youqi) 改样式

这份 `README.md` 是本仓库**唯一的博客说明文档**。内容包含：

- **如何写文章 / 预览 / 部署**
- **如何改站点信息与样式（含科技感主题色）**
- **如何换背景图（如 `love.png`）**
- **如何换社交图标（把“力扣”图标换成 GitHub 图标）**
- **如何改公告栏 / 动态文字 / 头像下描述 / 页脚**
- **一些实用的小功能点子（不含“把公告栏换成图片分享”等小巧思）**

---

### 一、快速开始（安装 / 本地预览 / 部署）

- **安装依赖**（首次或依赖变动时）：

```bash
npm install
```

- **本地开发预览**：

```bash
hexo clean
hexo g
hexo s
```

然后浏览器打开：`http://localhost:4000`

- **部署到 GitHub Pages / 远程**（确保 `_config.yml` 的 `deploy` 已配置好）：

```bash
hexo clean
hexo g
hexo d
```

---

### 二、如何发布新文章

1. **创建文章**

```bash
hexo new "文章标题"
```

文章会生成在 `source/_posts` 下。

2. **编辑 Front-matter**

```yaml
title: 文章标题
date: 2026-02-18 12:00:00
categories:
  - 分类名称
tags:
  - 标签1
  - 标签2
cover: https://你的封面图链接
top_img: https://文章顶部大图链接 # 可选
```

3. **写正文**

- 图片写法：`![](图片链接或站内路径)`
- 代码块：

```markdown
​```js
console.log('hello')
```
```

---

### 三、修改站点标题 / 关键词 / 简介

- **文件**：`_config.yml`
- 常用字段：

​```yaml
title: chagumu's blog
subtitle:
description: '网站简介'
keywords: "关键词1,关键词2,..."
author: chagumu's blog
```

改完后重新生成/部署即可生效。

---

### 四、主题颜色（科技感配色）

- **文件**：`_config.butterfly.yml` → `theme_color`
- 当前仓库已按蓝青色科技风配置（你可以继续改颜色值）：

```yaml
theme_color:
  enable: true
  main: "#00d1ff"
  paginator: "#00d1ff"
  button_hover: "#00ffa3"
  text_selection: "#00d1ff"
  link_color: "#18ffff"
  meta_color: "#8a8f9c"
  hr_color: "#00bcd4"
  code_foreground: "#e0f7ff"
  code_background: "rgba(0, 15, 35, .85)"
  toc_color: "#00e5ff"
  blockquote_padding_color: "#00bcd4"
  blockquote_background_color: "rgba(0, 188, 212, .08)"
  scrollbar_color: "#00e5ff"
  meta_theme_color_light: "#0b1020"
  meta_theme_color_dark: "#02040a"
```

---

### 五、背景图片（用 `assets/love.png`，不要星空）

1. **把图片放到站内**
- 把 `love.png` 放到：`source/assets/love.png`

2. **配置 Butterfly 背景**
- **文件**：`_config.butterfly.yml` → `background`

```yaml
background:
  default: url(/assets/love.png);
  darkmode: url(/assets/love.png);
  mobileday: url(/assets/love.png);
  mobilenight: url(/assets/love.png);
```

3. **重新生成并强刷**

```bash
hexo clean
hexo g
hexo d
```

打开线上页面后，建议 `Ctrl + F5` 强制刷新，避免缓存导致仍显示旧背景。

> 如果你仍然看到星空，通常是：浏览器缓存 / CDN 缓存 / GitHub Pages 还没更新到最新构建产物。优先做 `hexo clean` + 重新部署 + 强刷。

---

### 六、社交链接：把“力扣”的图标/文字换成 GitHub（以及微信链接）

#### 1）社交链接配置位置

- **文件**：`_config.butterfly.yml` → `social:`

示例：

```yaml
social:
  微信: /assets/Wechat.jpg || icon-weixin || faa-tada
  QQ: /assets/QQ.jpg || icon-QQ || faa-tada
  B站: https://space.bilibili.com/3546706109008142?spm_id_from=333.1387.0.0 || icon-bilibili || faa-tada
  QQ邮箱: mailto:3835385985@qq.com || icon-youxiang || faa-tada
  github: https://github.com/shanyangcao || icon-github || faa-tada
```

格式是：`显示名: 链接 || 图标 || 动效`

#### 2）把 GitHub 图标换成“真正的 GitHub 图标”（推荐：Font Awesome）

如果你不想依赖 iconfont 的 `icon-github`，直接改成 Font Awesome：

```yaml
github: https://github.com/shanyangcao || fab fa-github || faa-tada
```

> `fab fa-github` 是 Font Awesome Brands 的 GitHub 图标类名。

#### 3）微信二维码怎么换

- **站内文件方式**（推荐）：
  - 放图片到：`source/assets/wechat.png`
  - 然后改成：

```yaml
微信: /assets/wechat.png || icon-weixin || faa-tada
```

- **外链方式**：把 `/assets/wechat.png` 换成你的图床链接即可。

---

### 七、公告栏怎么修改（侧边公告卡片）

- **文件**：`_config.butterfly.yml` → `aside.card_announcement`

```yaml
aside:
  card_announcement:
    enable: true
    content: <center><b>这里是公告内容，可以写站点说明、更新日志等</b></center>
```

- `content` 支持简单 HTML：
  - 换行：`<br>`
  - 链接：`<a href="https://xxx" target="_blank">文字</a>`
  - 加粗：`<b>文字</b>`

关闭公告栏：把 `enable: true` 改成 `enable: false`。

---

### 八、首页标题下会动的文字（打字机效果）怎么改

- **文件**：`_config.butterfly.yml` → `subtitle`

```yaml
subtitle:
  enable: true
  effect: true
  loop: true
  source: false
  sub:
    - "欢迎来到 chagumu's blog"
    - "记录一点代码，也记录一点生活"
    - "愿你所想皆所愿"
```

想关掉打字机动画：把 `effect: true` 改成 `effect: false`。

---

### 九、头像下面的文字怎么改（侧边栏个人卡片）

- **名字**：来自 `_config.yml` 的 `author`
- **头像下面的小字描述**：优先来自 `_config.butterfly.yml` → `aside.card_author.description`（为空时可能回落到 `_config.yml` 的 `description`）

示例：

```yaml
aside:
  card_author:
    enable: true
    description: "chagumu，在互联网里留一点痕迹"
```

---

### 十、页脚那串“运行时间/感性文字”等怎么改（你截图里那块）

- **文件**：`source/js/fomal.js`
- 关键词：搜索 `createtime()` 或 `workboard`

当前仓库已经把那一大段文字收敛为更简洁的输出；如果你想彻底清空，逻辑上就是让最终写入 `#workboard` 的内容为空字符串即可，然后重新生成部署。

---

### 十一、底部“画条图片 / 徽标区域”怎么改

- **文件**：`themes/butterfly/layout/includes/footer.pug`
- 在 `p#ghbdages` 里可以插入图片，例如底部横幅：

```pug
a.github-badge(target='_blank' href="https://你的链接" style='margin-inline:5px' title="这里是图片说明")
  img(src="/assets/your_banner.png" alt="自定义底部横幅")
```

然后把图片放到：`source/assets/your_banner.png`，重新生成即可。

---

### 十二、常用“改样式/改功能”的入口（快速索引）

- **自定义 CSS 主文件**：`themes/butterfly/source/css/_custom/custom.css`
- **JS 主逻辑 / 动效**：`source/js/fomal.js`
- **主题大多数配置**：`_config.butterfly.yml`
- **站点基本信息**：`_config.yml`

> 修改主题文件（`themes/butterfly/...`）后，主题升级可能覆盖你的改动；重要改动建议记录到你的变更笔记里，或用 Git 方便回滚/迁移。

---

### 十三、可以加哪些“实用小功能”（不含“公告栏换成图片分享”等小巧思）

下面是一些“体积小、收益高、比较有科技感”的功能点子（都能在 Butterfly 上落地）：

- **阅读进度条**：文章页顶部一条细进度条，滚动时发光增长（科技蓝 `#00d1ff`）。
- **代码块复制反馈增强**：复制成功 Toast + 按钮状态短暂变绿。
- **返回顶部增强**：按钮显示滚动百分比，或圆环进度条。
- **目录 TOC 高亮增强**：当前章节自动高亮，点击平滑滚动。
- **字数统计 + 预计阅读时长**：`约 2500 字 | 约 8 分钟`。
- **快捷键**：`S` 搜索、`D` 深色模式、`J/K` 上下篇。
- **随机一言卡片（本地句库）**：不依赖外部接口，每天显示一句技术/生活短句。

实现位置通常在：
- JS：`source/js/fomal.js`（或新建 `source/js/*.js` 再用 `_config.butterfly.yml` 的 `inject` 引入）
- CSS：`themes/butterfly/source/css/_custom/custom.css`


