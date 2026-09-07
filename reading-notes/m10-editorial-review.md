# M10 Editorial Review — cold-reader rewrite 与 authority/evidence 边界记录

> 本文件记录 M10 rewrite 的独立校验、压缩决策和已知边界。它不是 self-approval；PR reviewer 仍应从真实 artifacts、starter 和 probes 独立复核。

## 1. Batch scope：M10 单独成批

本轮只重写 M10：

- `modules/10-code-review-change-engineering.md`
- `labs/10-code-review-change-engineering.md`
- `case-studies/m10/instructor-analysis.md`

并新增本 review record。

`reading-notes/m10-source-audit.md` 保持不动，因为当前 source-selection / provenance boundary 本身已经健康，不需要为了 editorial rewrite 制造 source churn。

不与 M11 合批。理由：

- M10 的 authority question 是：**一个 change 怎样被独立接受或拒绝？**
- M11 才系统进入 context engineering、task decomposition、tool authority、parallel agents、merge conflict。

M10 仍可以讨论 Agent-generated PR 的 self-summary / self-test 风险，但 orchestration 只作为显式 bridge，不成为本章主线。

## 2. Baseline artifacts 与真实 review case

Rewrite 前重新检查：

```text
review-cases/m10/reviewer-brief.md
review-cases/m10/agent-pr-description.md
review-cases/m10/agent-pr.patch
tools/m10_review_case.py
src/taskforge/service.py
src/taskforge/worker.py
src/taskforge/public_api.py
```

真实 reviewer brief 的 contract：

```text
architecture-enabling structural refactor only
existing observable behavior unchanged
scheduling semantics unchanged
snapshot compatibility unchanged
M07 concurrent_claim.py is an explicit historical exception
no RPC/database/queue/remote worker yet
```

Candidate patch 的主要 change：

```text
new JobAuthority
service/worker/metrics/audit route through it
list/claim sort state.jobs keys lexically
unknown cancel translates KeyError -> False
3 new tests
```

Author description 同时声称：

```text
preserve all current behavior
```

和：

```text
unknown cancel returns False
```

因此 prose 本身就包含需要 reviewer 拆开的 competing claims。

## 3. Executable baseline 独立复现

Rewrite 前实际运行：

```text
core pytest
=> 6 passed

m10_review_case.py
=> AUTHOR CI: 9 passed
=> author-supplied CI is green
```

Reviewer probes 实际得到四个 symptoms：

```text
ordering-regression
fifo-regression
undeclared-public-behavior-change
snapshot-order-consequence
```

但这四个 ID 不是四个 root-cause blockers。

更合理聚合：

```text
Root cause A:
lexical job-ID sorting replaces submission/FIFO semantics
  -> list order
  -> claim order
  -> snapshot/audit consequences

Root cause B:
unknown-ID behavior change is mixed into a behavior-preserving structural CL
  -> public cancel semantics
```

这也是 rewrite 主线选择该 case 的原因：一个真实 green-CI patch 可以自然承载 review funnel、test/oracle review、context beyond diff、severity、root-cause aggregation、small-change topology 和 re-review。

## 4. `job-9 -> job-10` 是 mechanism-driven partition，不是“彩蛋”

Starter 生成：

```text
job-1
job-2
...
```

Candidate 使用 lexical `sorted(state.jobs)`。

当 ID 都是一位数字时，lexical order 与 submission order 碰巧相同；digit-width boundary 才开始区分：

```text
job-9 -> job-10
```

因此 `>9 jobs` 是从 mechanism 推导出的高信息量 partition，不是 instructor-specific magic number。

这支持 M03→M10 的 evidence continuity：

```text
risk model
-> discriminating input partition
-> oracle
-> observed result
```

而不是“多写几个 tests”。

## 5. Authority seam：M09 locality 不能在 M10 又被偷升成 full isolation

PR #14 review 后 M09 已明确区分：

```text
normal transition policy/direct-state localization
!=
complete mutation-capability isolation
```

M10 candidate 的 `JobAuthority.get()` / `claim_next()` 仍返回 `state.jobs[...]` 中的 live mutable `Job`。

M02 已明确：

> 每一个拿到 authoritative mutable `Job` reference 的 caller 都获得潜在 write authority。

因此 candidate module 名为 `JobAuthority` 不足以证明 complete authority isolation。

但这里还要保持 review scope discipline：

- mutable-`Job` exposure 是 M02 已知 baseline issue；
- candidate 没有新引入该 capability；
- reviewer brief 的 bounded structural scope 是 authority localization；
- 所以不能为了“彻底修好 architecture”强制本 CL 新增 `JobView` / defensive copy。

Rewrite 将其统一写成：

```text
architecture/localization direction = reasonable
complete mutation-capability isolation = not established
mutable Job exposure = residual M02 risk / non-blocking for this CL
```

这同时保持 M10 instructor case 与后续教学 dependency，不重新制造 PR #14 已修掉的 authority overclaim。

## 6. Historical exception 与 evidence lifetime

M07 `concurrent_claim.py` 是 reviewer brief 明确的 historical fault-injection exception。

因此错误 review 是：

```text
Blocker: JobAuthority 不是唯一 writer，因为 concurrent_claim.py 还 direct-write state.
```

这把 whole-repo inventory 错投影成 normal product-path invariant。

M09 baseline architecture probe 与 M03 source-site mutation harness 也有 version/lifetime scope。合法 authority refactor 可能使这些 topology/source-location assumptions 失效；红灯不自动等于 product regression。

Rewrite 保留区分：

```text
long-lived behavior/compatibility evidence
historical topology characterization
source-site teaching harness
superseded fitness rule
```

同时继续要求 M05/M06/M08 中仍属于当前 preservation claim 的 observable/compatibility evidence。

## 7. Unknown cancel：新行为“可能更好”不影响本轮 blocker 结论

Baseline：

```text
service.cancel(missing) -> KeyError
public_api.cancel_job(missing) exposes that path
```

Candidate：

```text
missing -> False
```

M04 已经说明 baseline error contract 不理想，但 reviewer brief 明确要求 behavior preservation。

所以 blocker 的工程理由不是：

```text
False 比 KeyError 差
```

而是：

```text
behavior change is undeclared and packaged into a structural CL
```

如果产品真要改 unknown-ID semantics，应拆成显式 boundary/API behavior change并重新建立 caller contract与 compatibility evidence。

## 8. Source/provenance sweep

`m10-source-audit.md` 已把主要 source roles 分开：

- Google Engineering Practices：code-health standard、broader-context review、review tests、risk-first navigation、assigned human-written scope coverage / partial-scope disclosure、qualified-reviewer coverage、small/coherent CL、description quality；
- *Software Engineering at Google* Ch.9：code review 的长期价值与不同 change type；
- Gerrit：machine `Verified` 与 human `Code-Review` 作为不同 workflow signal；
- Stanford CS190：knowledge hiding/leakage、interface、modularity review；
- GitHub：review/approval governance mechanism 示例。

Rewrite 没把它们升级成：

```text
CI green -> approve
fixed LOC threshold
all PRs require same checklist
all baseline defects must be fixed now
specific approval count = review quality
JobAuthority name = authority isolation proof
```

以下仍明确是 course synthesis / TaskForge-specific：

```text
PR as bounded engineering argument
risk-first funnel = prioritization, not sampling
claim -> oracle -> evidence -> residual risk -> decision
root-cause aggregation
job-9 -> job-10 partition
historical probe lifetime classification
corrected CL topology
Agent tool-output laundering framing
```

Severity taxonomy 则不是随意 synthesis：`COURSE_DESIGN.md` 的 canonical 教学 contract 是 `Blocker / Medium / Nit`。本章允许 `Important / Should fix` 作为 Medium wording alias，`Optional / FYI` 作为额外 comment intent，但不能替换 canonical 三档。

## 9. Cold-reader rewrite decisions

Merge-base teaching chain 的主要问题不是技术方向错误，而是 rhythm：

```text
module: ~1993 lines / 47 H1
Lab:    ~920 lines / 27 H1
case:   ~1086 lines / 31 H1
```

大量短 answer-card 使读者先记 vocabulary，再很晚才回到同一 TaskForge PR。

Rewrite 改为一条 case-driven spine：

```text
reviewer brief
-> baseline contract
-> author claim / 9 passed
-> semantic center
-> job-9 -> job-10 counterexample
-> downstream consequence
-> unknown-cancel scope violation
-> regression vs residual/historical classification
-> severity/comment
-> corrected change topology
-> re-review
```

核心概念在问题压力出现后才命名。

## 10. Curriculum-core sweep

`COURSE_DESIGN.md` M10 核心：

```text
issue -> design -> patch -> evidence -> review
small changes
severity
review code health
context beyond diff
```

当前 module/Lab/case 都有实质教学承载，不只是关键词出现。

作业要求也保留：

- review 一个 CI green 但有 semantic/architecture consequence 的 PR；
- review issue/change contract 本身；
- 写 **Blocker / Medium / Nit** 的 evidence standard。`Important / Should fix` 只作为 Medium alias；Optional/FYI 是额外 comment intent。

PR #15 follow-up review 又暴露两处压缩 drift，本轮独立核验后一起闭环：

1. **risk-first coverage**：先看 semantic center 是 prioritization，不是 sampling。最终 approval 前一般仍完成 assigned human-written scope；partial review 明确披露，specialist area 由 qualified reviewer 覆盖。Code health（maintainability/readability/understandability/complexity）仍是 mandatory engineering judgment，不能与 nits 合并。
2. **severity authority**：`COURSE_DESIGN.md` 的 canonical taxonomy 是 `Blocker / Medium / Nit`，不能由 editorial record 偷换成另一套 label。

M11 leakage sweep 只保留显式桥接句：Agent reviewer 可以做 comparison，但 task decomposition / parallel reviewer-implementer / merge conflicts 明确留到 M11。

## 11. Final validation evidence

Rewrite 后实际重新运行：

```text
core pytest
=> 6 passed

M09 architecture baseline inventory
=> direct deps: concurrent_claim, legacy_audit, metrics, service, worker
=> lifecycle mutators: concurrent_claim, service, worker

M10 author CI
=> 9 passed
=> author-supplied CI is green

M10 reviewer probes
=> ordering-regression
=> fifo-regression
=> undeclared-public-behavior-change
=> snapshot-order-consequence

M05 behavior fingerprints
=> unchanged

M06 legacy-audit fingerprints
=> unchanged

M07 deterministic phenomena
=> two-success race / final-state masking / crash duplicate / record-first loss reproduced

M08 compatibility baseline
=> old fixture readable
=> current W1 accepted by frozen R1
=> known W2 -> R1 break reproduced
=> future version fail-closed
=> historical fixture sha256 = 0cd8f674d54b3da7919c2a9f7b911fdea5b109399438595c471a6baee90d2ecc
```

Hygiene / structure：

```text
git diff --check = PASS
relative Markdown links = PASS
changed Markdown fences = balanced
module = 657 lines / 1 H1 / 0 page-level separator
Lab = 634 lines / 1 H1 / 0 page-level separator
instructor case = 519 lines / 1 H1 / 0 page-level separator
source audit = 546 lines / existing 12 H1 / existing 12 source-section separators
editorial review = 412 lines / 1 H1 / 0 page-level separator
secret scan = no findings
uv.lock = absent
```

Semantic stale-claim sweep 也重新确认：

- 没有把 `JobAuthority` 写成 complete authority isolation proof；
- mutable `Job` residual 没被升级成本 CL blocker；
- `concurrent_claim.py` 仍是 explicit historical exception；
- four reviewer-probe symptoms 被聚合成 two root causes；
- `KeyError -> False` blocker 的理由是 scope/contract violation，不是“False 本身一定更差”；
- author CI green 没被写成 acceptance conclusion；
- risk-first 没被写成“只抽查 semantic center 即可 approve”；
- maintainability/readability/code health 没被降格成天然 nit；
- canonical severity 保持 `Blocker / Medium / Nit`，Optional/FYI 只作 comment intent；
- M11 orchestration 只作为显式 bridge，不是 M10 core。

## 12. Independent reviewer focus

This record is not self-approval. Reviewer should independently check at least：

- rewrite 是否真的先产生 review pressure 再引入 abstraction；
- baseline contracts 是否来自真实 starter/前置 module，而不是 instructor answer；
- `job-9 -> job-10` 是否是最小 discriminating mechanism，而不是 magic fixture；
- ordering symptoms 是否正确 root-cause 聚合；
- unknown cancel finding 是否基于 scope/contract，而非 aesthetic API preference；
- M02/M09 authority boundary 是否精确；
- historical probe lifetime 是否没有被滥用来忽略真实 regression；
- source-backed claim 与 course synthesis 是否仍分开；
- risk-first 是否明确是 prioritization 而非 sampling；approval coverage / partial-scope disclosure / specialist coverage 是否完整；
- code health 是否与真正 nits 分开，material maintainability/readability regression 是否仍可升级 severity；
- `Blocker / Medium / Nit` 是否与 `COURSE_DESIGN.md` canonical contract 对齐；
- Lab reveal-probe ordering 是否仍保护 independent review；
- grading 是否奖励 evidence/root-cause/scope/code-health judgment，而不是 comment 数量；
- M11 的 agent orchestration authority 是否没有提前泄漏。

## 13. Issue #2 closure pass — text-fence cleanup

2026-09-07 的独立 #2 closure review 发现：M10 的 semantic spine、authority boundary 与 runnable review case 都已成立，但正文仍保留一批只承担视觉强调的 `text` fence。这个 finding 只授权 presentation cleanup，不授权再次改写 M10 technical contract。

本轮逐个分类所有 `text` fence。移除或改写为 prose / Markdown list 的是普通自然语言 contrast、简单 taxonomy、review funnel 与 summary formula，例如：

- architecture/locality 与 behavior-preservation 两个 proof obligations；
- `scope / claim / source of truth / evidence / residual risk`；
- `localization != complete isolation`；
- root-cause / consequence 的普通自然语言聚合；
- severity taxonomy、Agent review risks 与 re-review checklist。

继续保留 fence 的是 author-supplied artifact、真实 terminal output、`job-9 -> job-10` boundary fixture、ASCII call/dataflow、finding template、corrected CL topology、reviewer-probe labels 与最终 reusable review sample。判断依据是 `EDITORIAL_GUIDE.md` §3.4，而不是追求 fence 数字下降。

Semantic preservation 复核后，下列 M10 claim 没有变化：author CI 仍真实 `9 passed`；ordering/FIFO/snapshot symptoms 仍归于 lexical job-ID sorting 一个 root cause；unknown cancel 仍因 undeclared behavior change 而 blocking；M09 locality 仍不等于 full mutation-capability isolation；historical-probe lifetime、risk-first-not-sampling、canonical severity 与 independent review authority 均保持原义。

Validation：

- core TaskForge：`6 passed`；
- M10 author CI：`9 passed`；
- reviewer probes：`ordering-regression / fifo-regression / undeclared-public-behavior-change / snapshot-order-consequence` 均保持原 observed result；
- `git diff --check`：PASS；
- changed-module relative Markdown links：PASS。
