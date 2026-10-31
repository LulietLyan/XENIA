# XENIA · 个人作品集

游戏设计、玩法拆解、商业化观察与社区洞察。基于 [VIIO Astro Theme](https://github.com/sijad/viio-astro) 制作，保留原模板的渐变配色、交互动效与 Three.js 视觉元素。

- 网站：<https://lulietlyan.github.io/XENIA/>
- 哔哩哔哩：<https://space.bilibili.com/26270462>

## 本地运行

使用 Node.js 24（见 `.nvmrc`，最低版本为 22.12.0）。

```bash
npm ci
npm run dev
```

在终端显示的本地地址后访问 `/XENIA/`。

```bash
npm run build
npm run preview
```

构建产物位于 `dist/`，全部页面均为静态文件。

## 内容维护

- `src/pages/index.astro`：首页栏目、介绍和精选内容。
- `src/data/portfolio.json`：从素材整理的文章正文、摘要和图片索引。
- `public/media/`：文章使用的图片素材。
- `src/layouts/Layout.astro`：站点导航、标题和分享信息。

原始 Word 素材保存在本地 `resource/`。提取脚本需要 Python 3.9+ 和 Pillow（`python3 -m pip install Pillow`）。更新素材后，可通过 `python3 scripts/extract-content.py` 重新提取内容；发布前请检查摘要、正文格式及图片。原始文档、临时提取文件和检查截图不提交到公开仓库，网站直接使用整理后的 JSON 和图片，构建无需原始 Word 文档。

## 自动部署

仓库通过 GitHub Actions 发布到 GitHub Pages。每次推送到 `main`，`.github/workflows/deploy.yml` 会安装依赖、构建并部署；也可在 Actions 中手动运行。仓库的 **Settings → Pages → Source** 应设置为 **GitHub Actions**。

部署地址由 `astro.config.mjs` 的 `site` 和 `base` 控制。内部链接与公开资源须使用 `import.meta.env.BASE_URL`，以兼容 `/XENIA/` 子路径。

## 素材与模板说明

作品正文和素材来自 XENIA 提供的文档。文中游戏画面、产品名称和相关标识归各自权利人所有；资料中的游戏时长、排名等数据反映原稿记录时的情况。

原始模板由 [Sijad Hashemian](https://hashemian.me/) 创作，页脚保留作者署名。原模板使用限制保持不变：**This theme and all included components may be used for non-commercial purposes only.** 此仓库未额外授予素材或模板的商业使用许可。

页面字体 Inter 与 Roboto Slab 随站点本地托管，字体授权文件见 `src/assets/fonts/`。B 站展示卡片采用主页公开视频及其封面，并链接回原视频。
