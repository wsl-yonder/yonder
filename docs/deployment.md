# Yonder Deployment

Yonder 的公网部署走 Cloudflare Pages Direct Upload：

1. GitHub Actions 每天北京时间 08:30 刷新数据。
2. 工作流导出 `dist/` 静态站点。
3. Wrangler 把 `dist/` 上传到 Cloudflare Pages 项目 `yonder`。

## Cloudflare 准备

在 Cloudflare Dashboard 创建或准备一个 Pages 项目：

- Project name: `yonder`
- Production branch: `main`
- Build command: 留空
- Build output directory: `dist`

如果使用当前 GitHub Actions 工作流部署，可以不启用 Cloudflare 自带的 GitHub 构建集成，避免重复部署。

## GitHub Secrets

在 GitHub 仓库里打开：

```text
Settings -> Secrets and variables -> Actions -> New repository secret
```

添加两个 secret：

```text
CLOUDFLARE_API_TOKEN
CLOUDFLARE_ACCOUNT_ID
```

`CLOUDFLARE_API_TOKEN` 建议使用 Cloudflare API Token，权限至少包含 Cloudflare Pages 的编辑/部署权限。`CLOUDFLARE_ACCOUNT_ID` 在 Cloudflare Dashboard 右侧账号信息或 Workers & Pages 页面可以找到。

## 手动部署

本地也可以手动导出并部署：

```bash
cd /Users/wsl/code/codex/yonder
PYTHONPATH=src python3 -m yonder.cli daily-update
PYTHONPATH=src python3 -m yonder.cli export-static
npx wrangler pages deploy dist --project-name=yonder
```

## 注意

- 当前线上版本是静态站点，首页、GitHub、AI、金融、音乐、小说 Demo 内容都能直接访问。
- Project Gutenberg 在线书源代理依赖本地 Python API，纯 Cloudflare Pages 静态部署暂时不能实时代理；后续可以用预生成 JSON 或 Pages Functions 补齐。
- 如果想绑定免费二级域名，Cloudflare 会自动提供 `*.pages.dev` 地址；如果之后有自己的域名，可以在 Pages 项目里添加 Custom domain。
