# Course Site Renderer

这个目录只包含课程网站 renderer。课程正文、title、content ID、relations、visibility 和 Main Path order 仍由仓库根目录的 canonical Markdown 与 `CONTENT_MODEL.md` 负责。

## 本地构建

需要 Node.js 20+ 与 Python 3.12+。

```bash
npm ci --prefix site
npm --prefix site run build:student
```

输出位于 `site/.vitepress/dist/`。开发预览：

```bash
npm --prefix site run dev
```

构建后的 artifact 不依赖 VitePress preview server 的 clean-URL rewrite。默认 `COURSE_SITE_BASE=/` 时可以直接交给普通静态服务器，例如：

```bash
python -m http.server 4180 --directory site/.vitepress/dist
```

普通内容页使用与 artifact 一致的 `.html` URL；目录 index（首页、`/practicum/` 等）仍使用目录 URL。这样 generic static hosting 不需要额外配置 `/foo -> /foo.html` rewrite。

另外提供：

```bash
npm --prefix site run build:instructor
npm --prefix site run build:all
```

student build 只把 `visibility: student` 的 canonical pages 交给 VitePress source discovery；instructor build 包含 student + instructor；all build 包含全部 canonical pages。`.generated/site-model.json` 是 `tools/site_model.py` 产生的临时派生物，不提交，也不是新的内容 authority。

## 配置

- `COURSE_SITE_BASE`：静态站 base path，例如 `/software-engineering/`；默认 `/`。
- `COURSE_SOURCE_REPO`：repo-only artifact 的 source navigation 根 URL；默认当前 GitHub repository。
- `COURSE_SOURCE_REF`：repo-only artifact 链接使用的 branch/tag/ref；默认 `main`。

canonical page 之间继续使用普通相对 Markdown link。若 canonical page 链接 starter、fixture、decision pack 等非 canonical repository artifact，renderer 会把它改成 `COURSE_SOURCE_REPO` 下的 `blob/tree` source link，而不会把 artifact 提升成网站页面。

## 验证边界

`build:student` 同时运行：

1. canonical content validation；
2. derived student site model；
3. VitePress static build / broken-link check；
4. expected route 与 hidden route/search leakage verification；
5. 中文/英文/type-aware MiniSearch probes；
6. Main Path pagination、related materials 与 repo-artifact rendering smoke；
7. 用 Python stdlib 普通 static server 对所有可见 canonical route 做 HTTP 200 probe，并确认 excluded canonical route 为 404；non-root `COURSE_SITE_BASE` 会在临时目录按相同 base path 挂载 artifact 后再测，不依赖 rewrite。

网站导航/sidebar/search metadata 全部消费 derived manifest；不要在前端新增手写 `MODULES`、`LAB_MAP` 或第二份 title/order mapping。
