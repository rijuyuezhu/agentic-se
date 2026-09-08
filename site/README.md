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

## 导航与布局

- 顶栏短站名为 `软件工程 · Agent`，可见的 Labs、Case Studies、Final Practicum 合并到 `实践` 菜单；canonical H1、SEO title 与内容模型不变。
- `Sources` 顶栏入口、`Source Audits` sidebar 分组和 `source_audit` related cards 只在 `all` 显示。这只是导航策略，不是内容访问策略：student/instructor 中符合 canonical visibility 的 source-audit 页面仍可访问，原有正文内 source citations 与搜索仍按 canonical visibility 保留，不修改根目录 Markdown 或派生模型的 visibility/relations。
- 本地 `VPSidebarGroup` alias 使用 `CourseSidebar.vue`，分组为默认关闭的原生 `<details>`，当前页面所在组也不自动展开。sidebar 显示篇数与学生版/教师版/完整版标签；当前链接使用 `aria-current="page"`，所在组使用 `has-active-link` 标记。
- 桌面 sidebar 宽度基准为 320px，`CourseLayout.vue` 默认收起整个 sidebar（`course-sidebar-collapsed`）。`course-sidebar-toggle` 按钮初始为 `aria-expanded="false"`，控制 `VPSidebarNav`，标题与无障碍标签为 `展开课程导航`；移动端保留 VitePress 原有 drawer。
- 配套材料使用默认关闭的原生 `<details class="course-context__related">`；页面类型、Main Path 进度文字和进度条留在折叠区外。正文与右侧目录保持独立阅读布局。

## 验证边界

`build:student` 同时运行：

1. canonical content validation；
2. derived student site model；
3. VitePress static build / broken-link check；
4. expected route 与 hidden route/search leakage verification；
5. 中文/英文/type-aware MiniSearch probes；
6. Main Path pagination、限定在 course-context aside 内的 related materials、按 audience 的 Source 导航、默认关闭的分组/配套材料与整体 sidebar toggle markup、repo-artifact rendering smoke；
7. 用 Python stdlib 普通 static server 对所有可见 canonical route 做 HTTP 200 probe，并确认 excluded canonical route 为 404；non-root `COURSE_SITE_BASE` 会在临时目录按相同 base path 挂载 artifact 后再测，不依赖 rewrite。

网站导航/sidebar/search metadata 全部消费 derived manifest；不要在前端新增手写 `MODULES`、`LAB_MAP` 或第二份 title/order mapping。

`verify-render.mjs` 只做静态 HTML 字符串/正则回归检查，不启动浏览器，也不验证视觉效果或客户端交互；视觉验证由使用者完成。
