# Knowledge Radar

面向个人和朋友的 AI、金融、科技知识雷达。

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
cd /Users/wsl/code/codex/knowledge-radar
PYTHONPATH=src python3 -m knowledge_radar.cli init-db
PYTHONPATH=src python3 -m knowledge_radar.cli run-once --print
PYTHONPATH=src python3 -m knowledge_radar.cli web
```

然后打开：

```text
http://127.0.0.1:8765
```

如果以后要重新启用 WxPusher：

```bash
cp .env.example .env
# 填写 WXPUSHER_APP_TOKEN 和 WXPUSHER_UIDS
PYTHONPATH=src python3 -m knowledge_radar.cli send
```

`send` 默认会要求输入 `SEND` 二次确认；自动化运行时可以显式加 `--yes`。

第一版不需要安装第三方依赖，RSS 解析、SQLite 和 HTTP 请求都使用 Python 标准库。

## 第一版原则

- 先少量高质量信息源，不追求覆盖全网。
- 网页内容要可扫读、可信、有判断，不做标题搬运。
- 每条内容必须保留原文链接。
- 推送不是第一优先级，先让 Dashboard 好用。
