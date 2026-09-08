# Course Site Framework Decision — VitePress

评估日期：2026-09-08

## Decision

课程网站首版采用 **VitePress 1.6.4**。

选择标准不是“哪个框架最流行”，而是哪个框架最少侵入已经由 `CONTENT_MODEL.md` 定义的 authority boundary：Markdown/H1/stable content ID/relations/visibility 继续由内容层负责，网站只做 rendering、navigation、search 和 presentation。

## Spike 方法

三个候选都使用同一份小型课程样本实际安装和 build，而不是各自使用官方 demo：

- 一个带中文长段落、H2/H3、英文术语的 M07 module；
- 对应 Lab / Source Audit / Extension；
- 一个 instructor-only case，并放置唯一 sentinel 检查 student output/search leakage；
- frontmatter 只使用 #4 已有字段：`id` / `type` / `visibility` / `order` / `related`，**不额外补 framework-owned title/slug**。

候选版本：

- VitePress 1.6.4；
- Astro 7.3.1 + Starlight 0.42.0；
- Docusaurus 3.10.2。

本地测量只用于比较当前课程的实际摩擦，不作为跨机器 benchmark。

## 结果

| 候选 | Canonical Markdown compatibility | Search | 本地 spike build / footprint | 主要 trade-off |
| --- | --- | --- | --- | --- |
| **VitePress 1.6.4** | 原样通过；H1 可继续是唯一 title authority；`id: M07` 不改变 file-based route | 内建 MiniSearch；默认中文正文 tokenization 不够好，但加入 `Intl.Segmenter('zh-CN')` 后实际 index 查询可命中“困难”“静默吞掉”“生命周期”，英文 `failure propagation` 也正常 | 约 2.8–3.0s；约 101MB `node_modules`；126 packages | 需要一个很小的中文 tokenizer 和课程 theme adapter |
| Astro 7.3.1 + **Starlight 0.42.0** | raw sample 失败：Starlight docs schema 要求 frontmatter `title`；只能通过 generated staging 从 H1 派生 title | 默认 Pagefind；静态、无外部服务，对中文有专门 segmentation | staging 后约 3.5s；约 219MB；268 packages | 搜索很强，但必须维护 derived-copy adapter 才能避免双 title authority |
| **Docusaurus 3.10.2** | canonical `id` 被解释为 Docusaurus doc ID，并改变 route；需要 staging 剥离/翻译该字段 | 官方一等方案偏 Algolia；local static search 依赖额外社区方案 | 约 13.4s；约 290MB；1270 packages | content-ID/route authority 冲突最大，依赖面和 build 成本也最高 |

Docusaurus spike 还验证了其 webpack toolchain 不适合把站点 package 直接设为 pure ESM `"type": "module"`；调整到框架支持的配置后可以 build，因此这不是“Docusaurus 无法构建”的结论，只计为额外 tooling friction。

## Search 实测

VitePress 默认 local search 对英文术语工作正常，但同一中文正文中：

- `生命周期`、`并发`、`取消` 可以命中；
- `困难`、`静默吞掉` 在默认 tokenizer 下不能稳定命中。

使用标准平台能力：

```js
const segmenter = new Intl.Segmenter('zh-CN', { granularity: 'word' })
const tokenize = (text) =>
  Array.from(segmenter.segment(text), ({ segment, isWordLike }) =>
    isWordLike ? segment : ''
  ).filter(Boolean)
```

重新 build VitePress 的真实 MiniSearch index 后：

- `困难` 命中 M07 正文；
- `静默吞掉` 被分为“静默 / 吞掉”并命中失败传播段落；
- `生命周期`、`并发`、`取消` 正常；
- `failure`、`propagation`、`failure propagation` 正常。

因此首版不需要 Algolia、外部搜索服务或第三方 Pagefind plugin。

## 为什么选 VitePress

最重要的原因是 **authority compatibility**，不是单纯依赖更少：

1. 可以直接读取仓库现有 Markdown，不要求正文迁到 vendor content tree；
2. 不要求把 H1 再复制到 frontmatter `title`；
3. 不把课程 stable content `id` 偷换成 URL/route authority；
4. `srcExclude`、`transformPageData`、sidebar 与 search renderer 都可以消费 #4 派生 manifest；
5. local static search 有足够小且可测试的中文修复面；
6. static build、GitHub Pages/generic hosting、mobile docs layout、TOC、syntax highlighting 都无需自研 renderer。

## Consequences

首版采用以下边界：

- `site/` 只放 VitePress config/theme/scripts，不复制课程正文；
- `tools/site_model.py` 从 `content_model.py` 的 validated graph 派生临时 site model；派生 JSON 不提交；
- student/instructor/all build 通过派生 `srcExclude` 在 source discovery 阶段排除不可见 canonical pages；不是 CSS/sidebar hiding；
- Main Path sidebar 与 prev/next、module related materials 都从 manifest/order/relations 产生；前端不维护 `MODULES` / `LAB_MAP`；
- canonical → canonical link 继续作为站内链接；canonical → repo-only artifact 在 renderer 层转为 repository source navigation，不把 artifact 提升成课程页面；
- VitePress local search 使用 `Intl.Segmenter` tokenizer，并在 CI 对真实 build index 做中英文 smoke test；
- 保持 VitePress `cleanUrls: false`：普通页面 URL 与生成的 `.html` artifact 对齐，不把 `/foo -> /foo.html` rewrite 偷偷变成 hosting 前提；CI 还会用 Python stdlib 普通 static server 实际请求所有可见 canonical route；
- 如果未来 VitePress 无法满足明确需求，可以重做 renderer；canonical Markdown 和 content graph 不需要迁移。

## 主要参考

- [VitePress Site Config](https://vitepress.dev/reference/site-config)
- [VitePress Routing / Clean URLs](https://vitepress.dev/guide/routing)
- [VitePress Local Search](https://vitepress.dev/reference/default-theme-search)
- [Starlight Authoring Content](https://starlight.astro.build/guides/authoring-content/)
- [Starlight Search](https://starlight.astro.build/guides/site-search/)
- [Pagefind Multilingual Search](https://pagefind.app/docs/multilingual/)
- [Docusaurus Docs Plugin](https://docusaurus.io/docs/api/plugins/@docusaurus/plugin-content-docs)
- [Docusaurus Search](https://docusaurus.io/docs/search)
