# Yonder

中文名：今日宜闻。面向个人和朋友的 AI、金融、科技知识雷达。

当前方向优先做网页 Dashboard：定时采集信息源，自动去重、分类、摘要和评分，再用本地网页展示精选内容和日报预览。WxPusher 推送暂时放弃，后续如果需要再作为可选分享渠道。

## 当前目标

- 跑通从信息源到网页 Dashboard 的完整闭环。
- 先保证阅读体验和内容质量，再考虑推送。
- 初期支持本地浏览、频道筛选、搜索和日报预览。

## 文档

- [MVP Spec](./mvp-spec.md)
- [Tasks](./tasks.md)
- [Decision Log](./decision-log.md)

## 本地运行

```bash
cd /Users/wsl/code/codex/yonder
PYTHONPATH=src python3 -m yonder.cli init-db
PYTHONPATH=src python3 -m yonder.cli daily-update
PYTHONPATH=src python3 -m yonder.cli web
```

然后打开：

```text
http://127.0.0.1:8765
```

如果以后要重新启用 WxPusher：

```bash
cp .env.example .env
# 填写 WXPUSHER_APP_TOKEN 和 WXPUSHER_UIDS
PYTHONPATH=src python3 -m yonder.cli send
```

`send` 默认会要求输入 `SEND` 二次确认；自动化运行时可以显式加 `--yes`。

第一版不需要安装第三方依赖，RSS 解析、SQLite 和 HTTP 请求都使用 Python 标准库。

## 每日自动更新

当前数据更新入口是：

```bash
cd /Users/wsl/code/codex/yonder
PYTHONPATH=src python3 -m yonder.cli auto-update --time 08:30
```

它会每天按本机时间刷新国内 AI/金融来源、重新处理 SQLite 数据，并更新近 3 个月 GitHub 高星项目缓存。想手动立即刷新一次，用：

```bash
PYTHONPATH=src python3 -m yonder.cli daily-update
```

## 导出静态网站

第一阶段上线准备使用静态导出：

```bash
cd /Users/wsl/code/codex/yonder
PYTHONPATH=src python3 -m yonder.cli daily-update
PYTHONPATH=src python3 -m yonder.cli export-static
```

导出结果在：

```text
dist/
```

`dist/` 可以直接交给 Cloudflare Pages、Vercel 或 GitHub Pages 托管。它包含首页、GitHub、AI、金融、音乐、小说和背景页，以及完整 `/static` 资源。注意：小说页的 Project Gutenberg 在线书源目前仍依赖本地 `/api/novels/gutenberg` 动态接口，纯静态部署时先使用本地 Demo 书库；后续阶段再改成预生成 JSON 或边缘函数。

## GitHub Actions 定时更新

第二阶段使用 GitHub Actions 自动生成静态站点产物，第三阶段继续把产物部署到 Cloudflare Pages：

```text
.github/workflows/daily-static-export.yml
```

工作流每天北京时间 08:30 运行一次，也可以在 GitHub 页面手动点 `Run workflow`。它会执行：

```bash
PYTHONPATH=src python -m yonder.cli daily-update
PYTHONPATH=src python -m yonder.cli export-static
```

生成的 `dist/` 会上传为 `yonder-dist` artifact，保留 7 天。随后工作流会用 Wrangler 部署到 Cloudflare Pages 项目 `yonder`。

## Cloudflare Pages 部署

部署配置文件：

```text
wrangler.toml
```

部署说明：

```text
docs/deployment.md
```

在 GitHub 仓库的 Actions Secrets 里添加：

```text
CLOUDFLARE_API_TOKEN
CLOUDFLARE_ACCOUNT_ID
```

之后可以手动运行 workflow，或等待每天北京时间 08:30 自动刷新并部署。Cloudflare 会提供 `https://yonder.pages.dev` 或同名可用变体地址。

## 第一版原则

- 先少量高质量信息源，不追求覆盖全网。
- 网页内容要可扫读、可信、有判断，不做标题搬运。
- 每条内容必须保留原文链接。
- 推送不是第一优先级，先让 Dashboard 好用。
