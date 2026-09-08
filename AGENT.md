# Agent instructions

本仓库不是“批量生成课程文案”的项目，而是一套需要技术 provenance、教学顺序和阅读体验同时成立的软件工程教材。任何修改都要优先维护可审查的 reasoning，而不是追求一次性覆盖更多文件。

## 开始编辑前

涉及课程正文时，至少先读：

1. [`COURSE_DESIGN.md`](COURSE_DESIGN.md)：课程训练目标与知识主线；
2. [`EDITORIAL_GUIDE.md`](EDITORIAL_GUIDE.md)：教材正文的编辑规范；
3. 对应模块的 `reading-notes/*-source-audit.md`：technical claim、limitations 与 source/course-synthesis 边界；
4. 对应 `modules/`、`labs/`、`case-studies/` 当前内容以及 merge-base 版本。

不要因为 rewrite 更顺口就顺便加入新的 technical claim。需要新增知识时，应单独做 source/provenance 工作，而不是藏在 editorial edit 里。

## Issue #2 的教材重写规则

正文优先采用“主 running example + 侧案例迁移”的组织方式：具体问题先产生压力，原直觉失效后形成 distinction，再命名 abstraction；第二个场景用于检验迁移，而不是堆更多例子。

不要把“去 bullet / 去 fence / 减 heading”当作目标。列表、behavior table、diagram、lab contract 和可复用 artifact 在确实需要结构化时应继续结构化。格式统计只能做 diagnostics，不能作为 acceptance metric。

每个大章 rewrite 都要执行 [`EDITORIAL_GUIDE.md`](EDITORIAL_GUIDE.md) 的 original-vs-rewrite review protocol：semantic preservation、cold-reader flow、abstraction dependency sweep、design-decision dependency sweep、compression/rhythm。

### Abstraction dependency sweep 是强制 review technique

M04 pilot 在 PR #7 中暴露出一个可推广的问题：reviewer 最初只指出 §2 提前使用 `request_id`，但全前置 narrative 复核后，又发现 §3–§5 的 `request identity` / `idempotency` / `idempotent` 同样提前泄漏。如果只修 reviewer 点名的 occurrence，章节仍然违反 example-first 的 dependency order。

因此，当发现某个 abstraction 在故事真正需要它之前已经出现时：

- 不要只 patch 被评论的那一处；
- 先确定它应该第一次被命名的位置；
- 搜索此前 narrative 中的 canonical term、中英文/缩写/同义表达，以及会预设该 abstraction 已存在的字段、类型、error reason、例子和描述；
- 区分不要求预备知识的 foreshadowing 与真正的 dependency leak；
- 对 leak，优先改用读者已经拥有上下文的例子，或只描述底层现象而暂不命名 abstraction；
- 修完后重新顺读“问题压力 → first naming”，再做一次前置范围搜索验证。

搜索为 0 只能证明一个具体 dependency constraint 没有已知泄漏，不能证明教材质量。

完整案例与修订 reasoning 见 [`reading-notes/m04-editorial-pilot-review.md`](reading-notes/m04-editorial-pilot-review.md) 的“PR review 后的 dependency / flow refinement”。

### Design conclusion 也必须服从 dependency order

PR #8 的 M00–M01 review 暴露了第二类 leak：正文即使没有提前命名 abstraction，也可能在读者尚未拥有 decision criterion 时，把一个 plausible design 写成自然答案。M00 原先用“于是我们加一个 `CANCELLING`”继续故事，但 M01 才负责建立“没有 specification 就不能判断哪个 cancel design 正确”的 authority；这会让前一章偷偷替后一章做决定。

因此后续 rewrite 还要检查：

- 后文是否负责建立“怎样选择”的 criterion，而前文已经把某个 state/schema/API/error/ownership/recovery design 当成既定事实；
- 为了维持 running example，可以明确采用 hypothetical candidate，但必须标记它只是 working assumption；
- 后续 complexity / migration / testing 分析继续复用该 candidate 时，要保持 conditional scope；
- criterion 建立以后，必须允许比较或替换此前 candidate，而不是为了维持故事连续性强行证明它“本来就对”。

这条规则不是“前一章不能出现具体设计”。禁止的是**未声明的 design authority 偷跑**。案例与 reasoning 记录见 [`reading-notes/m00-m01-editorial-review.md`](reading-notes/m00-m01-editorial-review.md)。

## 如何处理 reviewer 意见

Reviewer 不是规范来源。不要因为 reviewer 写了具体修法就直接执行。

把 **diagnosis** 和 **remediation** 分开判断：

- diagnosis 是否由当前文本真实支持？
- reviewer 是否只发现了问题类别中的一部分 occurrence？
- 建议修法是否会删掉另一条合理 reasoning、qualifier 或 teaching artifact？
- 是否存在更小但覆盖完整问题类别的修法？

M04 pilot 的经验是：reviewer 对 narrative rewind 的 diagnosis 成立，但“把 §7 大部分压掉”的具体修法不应全盘采用；internal/external vocabulary 应回到 error-translation episode，而 convenience API 是 request-identity 的直接 consequence，应移动而不是删除。

不要把 review record 写成“comment → checkbox”。对重要 rewrite，应记录接受了哪个 diagnosis、没有采用哪部分 remediation、额外发现了什么，以及为什么。

## Source / semantic preservation

重写后必须回到 merge-base 和 source audit 做 claim-level spot check，特别检查：

- condition / limitation；
- non-goal；
- exception；
- compatibility qualifier；
- security/disclosure qualifier；
- source-backed claim 与 course synthesis 的边界；
- lab normative contract 与后续模块依赖；
- 新引入的 contract-relevant state dimension 是否贯穿相关 behavior table / representation / state machine / test partition；如果某个 artifact 只投影一部分 state，必须明确 scope，不能靠读者猜遗漏维度；
- contract 若区分 acceptance / completion / recovery 等 temporal phase，error、state transition、durability 与 test/evidence 必须使用同一时间模型；不要把 downstream completion failure 重新解释成此前 acceptance success 的失败，除非 contract 明确如此。

“概念字符串还存在”不等于教学内容被保留。M04 的 `mask/recover` 就曾 technically present、但对 cold reader 过薄；最终用一个简短 replica fallback 场景恢复了 reasoning，而没有恢复碎片化小标题。

## 验证与提交

提交 editorial rewrite 前至少：

- `git diff --check`；
- 检查 changed Markdown 的 relative links；
- 运行受影响 lab/project 的相关测试；
- 做 secret scan；
- 确认测试工具产生的临时文件（例如 `uv.lock`）没有误入 PR；
- 保持工作区干净并检查最终 diff。

尽量让 commit 按 reasoning phase 可审查，例如 guide、pilot、review refinement 分开提交。

## Canonical content model

进入课程网站内容图的 Markdown 必须遵守 [`CONTENT_MODEL.md`](CONTENT_MODEL.md)。不要把 frontmatter 当网站样式配置：它只表达稳定的 content identity、page type、visibility、Main Path order 和页面级 relations。

特别注意：

- 页面标题的 authority 仍是正文唯一 H1，不要在 frontmatter 再复制一份 `title`；
- relation 使用 stable content ID，由 validator / renderer 建反向索引，不要维护第二份 module→lab/case/source map；
- `visibility: instructor` / `internal` 是 build exclusion contract。Student page 不得 link / relate 到 instructor/internal；instructor page 也不得依赖 internal；不要靠“提醒读者别点”替代隔离；
- canonical Markdown 使用 `CONTENT_MODEL.md` 定义的 fail-closed subset：ATX heading + simple inline links；不要用 Setext heading、reference-style links、angle autolink 或 raw HTML 绕开 validator；
- pure canonical zone 中缺 frontmatter 是错误；`practicum/` 是 mixed zone，只有 root entry 强制 canonical，nested page 用 frontmatter opt in。目录只做 inclusion check，不推导页面 semantics；
- repo-only editorial/source-work records 不需要为了形式统一强行加入 canonical graph；
- 不要因为某个网站框架偏好 MDX、slug 或 presentation field 就扩 schema。先证明新的 content semantic 真有消费者。

涉及 canonical content 的改动，提交前至少运行：

```bash
python tools/test_content_model.py
python tools/content_model.py validate
python tools/content_model.py manifest --visibility student >/dev/null
python tools/content_model.py manifest --visibility instructor >/dev/null
python tools/content_model.py manifest --visibility all >/dev/null
```

网站实现必须消费这个派生 content graph，而不是重新从目录名或前端配置猜课程结构。

## Canonical pilot

PR #7（`教材编辑：建立 Editorial Guide 并重写 M04 pilot`）是 issue #2 的首个已通过独立 semantic/cold-reader review 的困难章节 pilot。后续 M00–M13 rewrite 应复用它的方法，而不是机械复制它的章节结构或 heading 数量。

Issue #2 在 M00–M13、case studies 等剩余 acceptance criteria 完成前保持 open；单个 pilot 或单批章节不应 `Closes #2`。
