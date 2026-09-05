# M10 Source Audit — Code Review 与 Change Engineering

> 本文件记录 M10 实际检查过的材料、课程采纳的 claim、以及明确不升级成课程定律的经验规则。
>
> 本章的目标不是教授某个平台怎么点 Approve，而是回答：**一个 reviewer 到底在为哪种工程判断负责？一份 change 怎样携带足够证据，让另一个人可以独立判断它是否应进入系统？**

---

## 0. 本章的 source-selection 原则

M10 需要的材料必须覆盖至少四种不同问题：

1. reviewer 的 correctness / design responsibility；
2. change size、description 与 review throughput；
3. automated verification 与 human review 的边界；
4. reviewer 如何围绕 hidden knowledge / modularity 做独立设计判断。

因此没有把 GitHub/Gerrit UI 操作手册当成主要教材，也没有把“某公司要求两个 approval”当成 universal rule。

本章实际采用：

- Google Engineering Practices Reviewer Guide；
- *Software Engineering at Google* Chapter 9 `Code Review`；
- Gerrit 官方 `Review Labels` / `Submit Requirements`；
- Stanford CS190 的 code-review teaching material；
- GitHub Pull Request Reviews 仅作为“平台可以 enforce review policy”的机制例子，不作为 reviewer judgment 的理论来源。

---

# 1. Google Engineering Practices — The Standard of Code Review

Source:

https://google.github.io/eng-practices/review/reviewer/standard.html

## 实际检查到的内容

页面把 code review 的 primary purpose 定义为：让 codebase 的 overall code health 随时间改善，而不是追求单个 CL 完美。

它同时强调两个张力：

- developer 必须能继续推进；
- reviewer 不能允许每次“小幅退化”累积成长期 code-health erosion。

最终给出的 senior principle 是：当 change **明确改善整体 code health** 时，即使并不完美，也应该倾向 approve。

它还明确提出：

- technical facts / data 优先于 personal preference；
- design 不是单纯 style preference；
- 如果几个方案工程上等价，应该接受 author preference；
- nit / educational feedback 不应伪装成 blocker。

## M10 采纳

课程采用以下判断：

> **Review 的目标不是让代码符合 reviewer 的个人偏好，而是判断这次 change 是否让系统在 correctness、maintainability、understandability、risk 等方面保持或改善。**

以及：

```text
blocker != "我会用另一种写法"
```

真正 blocker 必须能连接到至少一种工程后果：

- contract 被破坏；
- invariant 无法成立；
- failure / migration risk 不可接受；
- evidence 缺失到无法支撑 claim；
- change scope 本身错误；
- code health 明确退化。

## 不升级成课程规则

Google 的具体组织流程不是 universal law，例如：

- 通常一个 peer LGTM；
- owner/readability approval；
- Google 内部 review latency expectations。

课程关心的是 responsibility separation，不照搬组织配置。

---

# 2. Google Engineering Practices — What to look for in a code review

Source:

https://google.github.io/eng-practices/review/reviewer/looking-for.html

## 实际检查到的内容

页面把 **overall design** 放在最重要的位置，并要求 reviewer 检查：

- change 是否应该进入这个系统；
- pieces 之间 interaction 是否合理；
- functionality 是否符合 developer intent，并且 intent 本身是否对 users 有益；
- edge cases / concurrency；
- unnecessary complexity / over-engineering；
- tests 是否正确、有用，坏代码时是否真的会失败；
- documentation 是否跟随 user-visible workflow/API 变化；
- broad system context，而不只看 diff 附近几行。

特别重要的一句思想是：

> tests do not test themselves。

页面明确要求 human reviewer 判断 tests 本身的 validity。

还明确要求在一般情况下理解所有 human-written lines；如果 reviewer 对某部分缺乏 security/concurrency/privacy 等专业资格，需要确保有合适 reviewer 覆盖该部分。

## M10 采纳

这支撑课程中的：

```text
CI evidence
!=
correctness conclusion
```

reviewer 至少要判断：

```text
claim -> oracle -> test/probe -> observed result
```

这条 evidence chain 是否真的成立。

课程还吸收“看 broader context”这一点，但把它具体化为：

```text
changed line
  ↓
changed semantic operation
  ↓
callers / authority / durable surface / failure path
  ↓
compatibility window
```

而不是把 review 限制为 diff viewer 里显示的几行 context。

## 不升级成课程规则

页面偏向 unit/integration/end-to-end testing taxonomy；M10 不重复 M03 的完整 testing curriculum，也不把“每个 endpoint 必须有 unit test”脱离 context 普遍化。

---

# 3. Google Engineering Practices — Navigating a CL in review

Source:

https://google.github.io/eng-practices/review/reviewer/navigate.html

## 实际检查到的内容

推荐 review 顺序大致是：

1. broad view：change 本身是否合理，description 是否足够；
2. main part：先看最核心的设计/文件；
3. 再按逻辑顺序检查其余 change；
4. 有时先读 tests 能帮助理解 intended behavior。

如果主要设计已有严重问题，应尽快给出 broad feedback，而不是先花大量时间逐行 nitpick 后才指出整个方案方向不成立。

如果 change 大到 reviewer 找不到主要部分，页面直接建议要求拆分。

## M10 采纳

课程将其重构成 **review funnel**：

```text
Should this change exist?
        ↓
What does it claim?
        ↓
What contract / authority / failure surface does it touch?
        ↓
What is the semantic core of the diff?
        ↓
Does evidence discriminate correct from incorrect implementations?
        ↓
Only then line-level maintainability / nits
```

这样避免：

```text
review 40 分钟命名
最后才发现 migration strategy 根本不成立
```

---

# 4. Google Engineering Practices — Small CLs

Source:

https://google.github.io/eng-practices/review/developer/small-cls.html

## 实际检查到的内容

页面把 small CL 的主要优势放在：

- review 更快、更彻底；
- bugs 更少；
- rollback 更容易；
- merge conflict 更少；
- change 更容易理解。

它不是用固定 LOC 数字定义 small；核心更接近一个 self-contained change。

页面也允许一个 CL 中包含 necessary test code、supporting refactor 等，只要它们构成同一个 self-contained logical change。

## M10 采纳

课程把 M05 的 `change topology` 推进成 reviewability：

> **好的 change boundary 应使 reviewer 能在一个有限 mental model 中判断它的 contract、evidence 与 rollback consequence。**

因此：

```text
small != few lines
```

更接近：

```text
one coherent engineering claim
+ bounded consequences
+ independently reviewable evidence
```

## 不升级成课程规则

不设置：

```text
< 100 LOC = good PR
```

generated migrations、大规模机械 transformation、schema rollouts 等需要不同 review strategy。

---

# 5. Google Engineering Practices — Writing good CL descriptions

Source:

https://google.github.io/eng-practices/review/developer/cl-descriptions.html

## 实际检查到的内容

页面要求 description 解释：

- change 是什么；
- 为什么这样改；
- future reader 如何理解 decision；
- description 应描述当前 patch，而不是只保留历史过程碎片。

它强调 code review record 有长期价值。

## M10 采纳

课程将 PR description 当作：

```text
author's engineering argument
```

而不是 truth source。

最低应回答：

```text
Problem
Intended behavioral change
Intentionally unchanged behavior
Design / authority decision
Risk / migration assumptions
Evidence actually run
Known limits / follow-ups
```

但 reviewer 必须**独立验证**这些 claim，避免 description anchoring。

---

# 6. Software Engineering at Google — Chapter 9: Code Review

Source:

https://abseil.io/resources/swe-book/html/ch09.html

## 实际检查到的内容

Chapter 9 将 code review 定义为由 author 之外的人在代码进入 codebase 前进行 review，并总结其长期价值：

- correctness check；
- comprehensibility；
- consistency；
- team ownership；
- knowledge sharing；
- historical record。

它还区分不同 change types：

- greenfield；
- behavioral change / optimization；
- bug fix / rollback；
- refactoring / large-scale change。

这点非常适合本课程，因为不同 change type 需要不同 proof obligation。

例如：

```text
refactor -> behavior preservation evidence
bug fix -> fail-before / pass-after
migration -> compatibility window evidence
concurrency -> history / interleaving reasoning
```

## M10 采纳

本章明确拒绝“一张 universal review checklist”。

review depth 应由 change type 和 risk model 驱动。

## 限制

Google 的 monorepo、owner/readability system 与内部 Critique tooling 有特定组织背景；课程只采纳可迁移的 reasoning model。

---

# 7. Gerrit — Verified 与 Code-Review 是不同 signal

Sources:

https://gerrit-review.googlesource.com/Documentation/config-labels.html

https://gerrit-review.googlesource.com/Documentation/config-submit-requirements.html

## 实际检查到的内容

Gerrit 官方文档解释：

- `Code-Review` label 原本表达 reviewer 读过代码并认为 reasonably correct；
- `Verified` label 原本表达 compile / basic unit tests 等自动 verification 成功；
- submit requirements 可以同时要求不同 labels；
- requirement 还可以要求 approval 来自 non-uploader / human reviewer。

这不是哲学论文，但它从 workflow design 上提供一个很好的事实：

```text
machine verification
and
human code review
```

被建模为不同 signal。

## M10 采纳

课程用它反驳：

```text
CI green -> review complete
```

更准确的是：

```text
CI answers selected executable questions
review judges whether those were the right questions,
and whether the change's broader claims are supported
```

## 不升级成课程规则

课程不会规定 Gerrit `+2`、几个 reviewer、是否允许 self-approval；这些是 governance policy，不是 software-engineering invariant。

---

# 8. Stanford CS190 — Code Review teaching material

Source:

https://web.stanford.edu/~ouster/cs190-winter24/lectures/codeReview3/

## 实际检查到的内容

CS190 的 review exercise 要求 presenter/reviewer讨论：

- 一个 class 隐藏哪些 knowledge / design decisions；
- knowledge 是否 leak 到其他 class；
- external interface；
- alternatives 与选择理由；
- design weaknesses；
- modularity。

这与课程 M02/M09 非常一致：code review 不只是找 bug，而是重新检查 knowledge boundary。

## M10 采纳

在 architecture / design-heavy CL 中，reviewer 应主动问：

```text
what knowledge moved?
what knowledge duplicated?
who now owns this decision?
which callers must know more after this patch?
```

而不只问：

```text
does this function return the right value?
```

---

# 9. GitHub Pull Request Reviews

Source:

https://docs.github.com/en/pull-requests/reference/pull-request-reviews

## 实际检查到的内容

GitHub 支持：

- request reviewers / teams；
- CODEOWNERS 自动请求相关 owner；
- protected branches 要求 approvals。

## M10 用途

只作为 governance mechanism 例子：平台能确保“某个 review gate 存在”。

它不能确保：

```text
reviewer actually reconstructed the change model
```

因此不把“required approval count”当 review quality proxy。

---

# 10. 本章明确拒绝的规则

以下都不会成为课程定律：

### 10.1 “CI 绿就可以 approve”

错误。

CI 只回答它执行的那些问题。

### 10.2 “reviewer 应重新实现一遍作者的方案”

错误。

reviewer 要独立判断 problem / contract / risk / evidence，不必成为第二个 implementer。

### 10.3 “comment 越多说明 review 越认真”

错误。

一个 migration blocker 比 30 个 naming nit 更有价值。

### 10.4 “所有 PR 必须小于 N 行”

错误。

需要 coherent / independently reviewable，而不是固定 LOC。

### 10.5 “review 只看 diff，不看 surrounding code”

错误。

contract、callers、authority、failure surface 通常在 diff 之外。

### 10.6 “旧问题只要 reviewer 看到了，都必须在本 PR 修”

错误。

reviewer 要区分：

```text
introduced regression
pre-existing defect
necessary prerequisite
out-of-scope cleanup
```

否则 review 会无限 scope creep。

### 10.7 “author / Agent 的 summary 是事实”

错误。

summary 是待验证 claim。

---

# 11. M10 最终采用的课程综合

本章把 change review 建模成：

```text
Author claim
   ↓
Independent reviewer model
   ↓
Contract / invariant / authority / failure / compatibility impact
   ↓
Diff mechanics
   ↓
Evidence quality
   ↓
Residual risk
   ↓
Decision + precisely scoped comments
```

核心句：

> **A PR is not just a patch. It is a bounded engineering argument about why this particular system change should be accepted.**

Agent 时代再加一条：

> **生成 patch 的成本下降，不会自动降低 reviewer 重建 system model 的成本；因此 change boundary 与 evidence quality 反而更重要。**
