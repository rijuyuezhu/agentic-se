# Canonical Course Content Model

本文件定义课程 Markdown 的**前端无关内容契约**。它不是网站配置，也不是第二份课程数据库。正文、标题和链接仍然写在普通 Markdown 中；frontmatter 只保存无法从正文安全推出、且后续 renderer/navigation 真正需要的少量语义。

## 1. 哪些 Markdown 属于 canonical content

Canonical content 是未来课程网站可以直接装载的页面。为了让“漏 frontmatter”也能被 CI 发现，目录只承担一个很窄的 **inclusion policy**，不推导 type/order/visibility/relations。

**Pure canonical zones / required entries** 中出现的 Markdown 必须带 frontmatter。当前精确 inclusion policy 是：

- root `README.md` 与 `MATERIALS_REVIEW.md`；
- `modules/*.md`；
- 顶层 `labs/*.md`，但不递归 `labs/taskforge/**`；
- `case-studies/*/*.md`；
- `extensions/*.md`；
- `reading-notes/m??-source-audit.md`；
- `reading-notes/extensions-source-audit.md`、`traditional-se-gap-map.md`、`final-practicum-candidate-audit.md`、`final-practicum-instructor-reference.md`、`final-practicum-pilot.md`。

这些路径只回答“如果这个文件存在，漏 frontmatter 是否应 fail”。例如 traditional-SE gap map 是 student reference，`MATERIALS_REVIEW.md` / candidate audit / pilot record 是 internal；这些 type/visibility 差异仍完全来自各自 metadata，不从文件名推断。

`practicum/` 是刻意的 **mixed zone**：`practicum/README.md` 是必须 canonical 的课程入口；其下 student page、checkpoint、instructor reference 通过 frontmatter opt in。这样同一 subtree 内可以保留 harness note、raw validation artifact 等 repo-only 文件，而不会因为递归扫描被偷偷提升成 website page。

Editorial review record、`AGENT.md`、`COURSE_DESIGN.md`、`EDITORIAL_GUIDE.md`、实验项目内部 README / fixture issue 等仍可保持 repo-only。在 pure canonical zone 中缺 frontmatter 是 validation error；在 mixed/repo-only zone 中，没有 frontmatter 才表示“不进入 canonical website content”。这不是低一级的内容质量，只是 inclusion 语义不同。

不要为了“所有 `.md` 看起来一致”给 repo-only 文件补无意义 metadata。

## 2. 最小 frontmatter schema

Canonical page 使用普通 YAML frontmatter：

```yaml
---
id: M07
type: module
visibility: student
order: 7
---
```

为了让 validator 保持 stdlib-only，当前 authoring contract 刻意只使用 YAML 的简单子集：每行一个 `key: scalar`，列表使用一行 inline list（例如 `[M04, M09]`）。不要写 nested mapping、multiline scalar 或其它当前 schema 根本不需要的 YAML feature；如果未来真的需要复杂 metadata，再同时扩文档和 parser，而不是让不同 renderer 各自解释。

允许字段只有：

- `id`：全课程唯一、稳定的 content identity；
- `type`：`reference | module | lab | case_study | source_audit | extension | practicum`；
- `visibility`：`student | instructor | internal`；
- `order`：可选整数，只用于真正的线性 Main Path；
- `related`：可选 stable content-id 列表，例如 `related: [M07]`。

当前**不把**下面这些字段塞进 frontmatter：

- `title`：唯一标题 authority 是正文第一个也是唯一一个 H1；复制到 metadata 只会制造 drift；
- presentation 参数：sidebar icon、theme、column width 等属于 renderer；
- `status` / tags / prerequisites：当前没有被真实 workflow 消费；
- `slug`：稳定 content ID 与 URL 是两回事；没有 URL migration 需求前不提前绑定；
- 手写 module→lab/case/source map：关系从各页面的 `related` 反向索引生成。

以后确实需要新增字段时，先说明它表达哪一条稳定 content semantic，再扩 schema。

## 3. Stable identity 与 relations

文件路径、标题、content ID 和未来 URL 必须分开理解。

- M00–M13 的 stable ID 就是 `M00` … `M13`；
- Lab 使用 `lab-M02` 这类 ID；
- instructor case 使用 `case-M02`；
- module source audit 使用 `source-M02`；
- Extension 使用 `ext-*`；
- Final Practicum 的主入口使用 `final-practicum`。

`related` 表示**内容关系**，不是“前端应该把链接放哪一栏”。例如：

```yaml
---
id: lab-M07
type: lab
visibility: student
related: [M07]
---
```

网站要展示 M07 的 Lab / Case / Source / Extensions 时，扫描所有 page 的 `related` 即可。不要再写：

```js
const LAB_MAP = { M07: "..." }
```

Extension 可以关联多个 module，例如：

```yaml
related: [M04, M09, M12]
```

普通正文 cross-reference 仍优先使用相对 Markdown link；`related` 只承载页面级关系，不取代句子中的语义链接。

## 4. Main Path

当前 Main Path 是：

```text
M00 → M01 → ... → M13 → Final Transfer Practicum
```

因此：

- module 的 `order` 必须与编号一致，即 M00=0 … M13=13；
- `final-practicum` 使用 `order: 14`；
- Lab、Case、Source Audit、Extension 和 practicum 子页面没有 `order`；
- Extension 永远不会因为文件名排序进入上一篇/下一篇导航。

`order` 是线性阅读语义，不是通用排序字段。

## 5. Visibility 是 build contract

Visibility 不是 CSS class。

### `student`

允许进入 student build 和 student search index。

### `instructor`

只允许 instructor build。当前 `case-studies/*` 都是 spoiler/instructor reference，包括文件名为 `baseline-analysis.md` 的 M02 case；Final Practicum instructor reference 也属于这一类。

### `internal`

作者/课程验证材料，例如 candidate audit、pilot record。它们不是学生教材，也不需要因为 instructor build 存在就自动发布。

每种 build 都只能引用自己实际包含的 page 集合：

> student build = `student`；instructor build = `student + instructor`；all/internal tooling = 全部 visibility。

因此：

- student page 不能 `related` / link 到 instructor/internal page；
- instructor page 不能 `related` / link 到 internal page；
- internal page 可以引用全部内容，因为它只进入 all/internal tooling。

“sidebar 不显示”“CSS 隐藏”“不知道 URL”都不算隔离。#5 的网站 build 必须从 content graph 输入阶段就排除非 student page。

Final Practicum checkpoint 是 `visibility: student`：它不是 instructor secret，而是学生在 Phase 1 冻结后按流程打开的 staged authority。阶段顺序由 practicum contract 保证，不伪装成网站访问控制。

## 6. Heading contract

每个 canonical page 必须：

1. frontmatter 后只有一个语义 H1；
2. H1 是页面标题；
3. 后续使用 H2/H3/... 表达真实层级；
4. fenced code / shell snippet 内的 `# ...` 不计入文档 outline；
5. 不用 H1 充当“大号分隔符”。

Canonical authoring 使用一个刻意小、仍可在 GitHub/普通编辑器高质量阅读的 Markdown subset。Validator **不是 CommonMark parser**，所以对会改变 heading/link semantics、但当前 scanner 不理解的写法采用 fail-closed：

- heading 只使用 top-level ATX `#` / `##` / `###`（允许 CommonMark 的 0–3 个前导空格）；禁止 Setext `Title\n=====`，也不在 blockquote/list container 内嵌 heading；
- cross-reference 使用 inline `[text](target)`；禁止 reference-style `[text][id]` + `[id]: target`；
- inline link/image target 不使用 raw nested parentheses；需要时 percent-encode，避免 parser ambiguity；
- 禁止 angle-bracket autolink `<https://...>`，改用有语义的 inline link text；
- canonical page 禁止 raw HTML；未来真需要组件能力时，应先定义统一 renderer contract，而不是用 HTML 绕开 content validation；
- code example 使用 fenced code；inline code 里的 URL / Markdown-like literal 不进入 link contract。

这不是要自研 Markdown renderer，而是明确 validator 能证明的 authoring grammar。若未来确实需要 reference-style link、raw HTML 或更完整 CommonMark grammar，应当同时升级 parser/validator 与本契约，不能只让某个 renderer 私下接受。

这项检查只验证 document semantics，不替代 `EDITORIAL_GUIDE.md` 的 cold-reader/editorial review。

## 7. Extension page 与 inline callout

两者是不同 content semantic：

- `type: extension` 是完整旁支页面，有自己的 H1、stable ID 和 relations；
- inline Note / Warning / Definition 是当前页面的一部分，不获得 content ID，也不进入 Main Path。

网站框架未来若需要专用 callout syntax，应由 renderer adapter 处理，并保持 GitHub/普通 Markdown reader 可理解。不要为了 callout 把正文迁成 MDX component tree。

## 8. Link 与 source 规范

Repo 内：

- 正文 cross-reference 使用上述 simple inline 相对 Markdown link；
- 页面级关系使用 `related` stable IDs；
- local target 不存在时 validation 失败；
- local target resolve 到 repository root 之外时 validation 失败；
- student/instructor page 链接到其 build 不包含的 canonical page 时 validation 失败。

本地链接的目标不一定都是 canonical page。Lab 可以继续链接 starter source、fixture、decision pack 或其它 repository artifact；这些 target 只要在 repo 中存在即可，但**不会因为被链接就自动进入 content graph**。#5 renderer 应把 canonical-page link 映射到网站页面，把非 canonical repo artifact 保持为 source/repository navigation（或等价的可访问 artifact link），不能递归扫描所有 Markdown 并把它们偷偷升级成课程页面。

外部资料：

- 教材正文优先使用有语义的 link text，而不是裸 URL；
- source audit 应把原始 URL 保留为语义 Markdown link 的 target，并同时保留 source 名称、访问/版本上下文和 claim boundary；
- URL 本身不是 authority，source audit 中已经形成的 provenance/qualifier 规则继续生效。

本 issue 不做一次“大规模 URL 美化 rewrite”；发现新的裸链接时按上述规范收敛即可。

## 9. Validation 与 manifest

`tools/content_model.py` 是独立于任何前端的 validation layer：

```bash
python tools/test_content_model.py
python tools/content_model.py validate
python tools/content_model.py manifest --visibility student
```

Validator 至少检查：

- frontmatter schema / unknown fields；
- duplicate content ID；
- M00–M13 identity 与 order；
- Main Path order uniqueness；
- invalid / duplicate relation；
- canonical page 单 H1 与 heading level continuity；
- unsupported Markdown heading/link/HTML grammar fail-closed；
- broken local Markdown links；
- repository-root escape；
- visibility build boundary 上的 link/relation/path leakage；
- 必须进入 canonical graph 的课程页面有没有漏 frontmatter。

`manifest` 从同一 metadata 自动生成页面列表和 inverse relations，供 #5 renderer 使用。Manifest 是**派生物**，不提交进仓库，也不是新的 authority。

CI 运行 validator regression tests、content validation，并 smoke-test student/instructor/all 三种 derived manifest。网站框架将来可以增加自己的 build/search/render checks，但不能取代 content validation。

## 10. Repository layout 决定

本轮不搬到 `content/` root。

现有：

```text
modules/
labs/
case-studies/
reading-notes/
extensions/
practicum/
```

已经对作者和 Git history 有意义。Frontmatter 足以消除前端对目录猜测的依赖；大规模搬家只会制造 link churn，没有当前收益。

因此 canonical model 的原则是：**metadata 解释页面语义；目录 inclusion policy 只负责发现“本来必须 canonical 却漏了 frontmatter”的文件，不给 renderer 推导 type/order/visibility/relations。** 网站只消费 validated metadata/manifest，而不是重新从路径猜课程结构。
