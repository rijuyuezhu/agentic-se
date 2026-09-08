---
id: practicum-click-deliverables
type: practicum
visibility: student
related: [practicum-click]
---
# Deliverables and Rubric

这份格式规定**交什么**，不规定你应该在代码里发现什么。可以用 Markdown、diagram、tables、patch 或 command transcript，只要另一个 engineer 能独立检查你的 reasoning。

## A. Reconnaissance Record

建立一个有 evidence 的 current-system model。至少让 reviewer 能理解：

- relevant entry points / control flow；
- 哪些 runtime/process state 会被读写；
- public 或长期 compatibility surfaces；
- failure / cleanup boundaries；
- 你仍不知道什么；
- 你认为 change 最可能放大的位置，以及代码/history/runtime evidence。

不要交“逐文件摘要”。

## B. Issue Review

把 issue 中的内容分清：

- explicit requirement；
- current observed behavior；
- existing contract；
- assumption；
- unresolved decision / contradiction；
- implementation suggestion。

给出当前 decision：`READY_TO_IMPLEMENT`、`NEEDS_DECISION`、`STOP_AND_ESCALATE` 或你定义的等价状态，并说明为什么。

## C. Design Memo

在看 checkpoint **之前**比较至少两个 plausible response/design family。它们不必都能满足 literal request；如果某一路线必须改变 requirement，要明确写出来。

至少比较：

- observable behavior / compatibility；
- failure/concurrency semantics；
- change surface；
- validation strategy；
- reversibility / migration；
- implementation 与 review cost。

看 checkpoint 后另写 addendum，保留 first-pass judgment。

## D. Delegation / Agent Contract

保存你实际给 implementation/reconnaissance Agent 的 bounded task。至少说明：

- goal / non-goals；
- allowed write surface 或 scope rule；
- behavior/invariants that must remain；
- evidence contract；
- stop/escalation conditions；
- human-only decisions；
- destructive/external action policy。

不要把 target implementation 写成 acceptance criterion，除非 maintainer decision 已经真的授权它。

## E. Candidate Change

只有 issue 已 ready 才实现。保存：

- production/docs/tests diff；
-必要的 migration/release notes；
- implementation Agent 的可见 plan/summary。

Patch 大小不是评分项。没有 patch 也不自动失败；但必须由 issue authority 和 evidence 证明“为什么此时不应实现”。

## F. Evidence Packet

按 claim 组织，不要只贴 raw CI：

| Claim | Oracle / source of truth | Command / probe | Observed result | Does not prove / residual risk |
|---|---|---|---|---|

至少包含：

- frozen baseline；
- focused change evidence；
- full minimal suite；
- `git diff --check`；
- 对 candidate 实际改动的其它独立 artifact contract 做验证，例如修改 Sphinx 文档时运行 docs build；若无法运行，明确记录 evidence gap；
- 你认为最有区分力的 negative/counterexample evidence；
- 未覆盖或无法证明的边界。

## G. Independent Review

保存 reviewer 的**第一轮**输入和输出。第一轮输入不得先附 implementation Agent 的结论性 summary。

Reviewer 应能独立判断：

- change claim 是否自洽；
- patch 是否越过 maintainer decision；
- compatibility / release semantics；
- evidence 是否真的能排除 plausible wrong implementation；
- docs/tests/runtime 是否一致。

## H. Human Adjudication

逐条处理 review finding：

| Finding | Real? | In scope? | Severity | Decision | Evidence / reasoning |
|---|---:|---:|---|---|---|

允许拒绝 reviewer finding，但必须有工程理由。若修复，保存 rework 前后的 reproduction/evidence。

## I. Rollout / Migration / Reversal Judgment

把这个 change 当成 library release，而不是只看 local checkout：

- 谁可能消费被改变的 public / compatibility surface？
- 哪些 evidence 足以进入 release？
- compatibility window / documentation / upgrade guidance 应承担什么职责？
- package rollback 能恢复哪些 runtime semantics？
- 哪些 downstream migration、配置/测试调整、代码修改不会因为你回滚 package 就自动消失？
- 哪些后续 breaking action 仍需要新的 authority？

## J. Retrospective

重点回答 transfer，而不是“Agent 好不好用”：

- 哪些课程方法在陌生 repo 中自然产生了价值？
- 哪些 checklist/术语没有帮助，甚至拖慢理解？
- Agent 做对了哪些 mechanical work？
- Agent 最容易合理地猜错什么？
- 你用什么独立 evidence 推翻或限制了它？
- 哪些 rule 应固化到 repo docs/tests/policy，而不是下次继续靠 prompt 记住？

## Agent artifact inventory

附一个简短 inventory，指出：

- reconnaissance prompts/outputs；
- implementation prompt/plan/summary；
- commands/evidence；
- independent review input/output；
- human corrections/escalations。

只保存正常对话与工程 artifact，不要求模型 private reasoning。

---

## Grading Rubric

总分 100。评分重点是 reasoning quality，不奖励代码量或 Agent 数量。

| Weight | Dimension | 高质量表现 |
|---:|---|---|
| 18 | System model / reconnaissance | 找到真正 relevant control/runtime surfaces，evidence 可定位，unknowns 不伪装成事实 |
| 17 | Issue/spec judgment | 能质疑 literal request 与 suggested implementation；正确区分 requirement、current behavior、decision authority |
| 12 | Design alternatives | 至少两条真实 plausible 路线；trade-off 不靠 pattern 名称，能说明哪个 premise 改变才让某路线成立 |
| 10 | Agent delegation / scope | task boundary、stop/escalation、human-only decision 与 evidence contract 清楚；Agent 没被授予隐含 product authority |
| 12 | Candidate change / scope control | 若实现，patch 与 maintainer decision 一致、兼容边界清楚、无无关 churn；若不实现，有充分 authority/evidence |
| 13 | Evidence strength | claim-oriented；有 high-information negative evidence；知道 green suite 不能证明什么 |
| 8 | Independent review + adjudication | reviewer 真正独立；finding 有 severity/evidence；human 不机械接受也不防御性拒绝 |
| 6 | Migration / reversal judgment | 从 consumer/release 角度讨论 compatibility、migration 与 rollback asymmetry |
| 4 | Retrospective / transfer | 能指出哪些方法真的迁移、哪些只是课堂习惯，并提出可固化的 repo mechanism |

### 不自动加分

- 使用更多或更强的 Agent；
- patch 更大；
- 一次实现成功；
- test count / coverage 更高；
- reviewer comment 更多；
- “完全无人介入”。

### 关键扣分 / blocker

即使最终 tests green，以下行为也可使 practicum 不通过：

- 在没有 product/maintainer authority 时偷偷改变 requirement；
- 把 suggested implementation 当 requirement；
- 用 implementation-derived test 给新 behavior 自己授权；
- first-pass artifact 在读取 checkpoint 后被回写得像“早就知道”；
- independent reviewer 只复述 implementation Agent summary；
- 隐瞒 material residual risk 或把 unsupported guarantee 写进 docs；
- 为了通过测试大范围删除/弱化旧 evidence。
