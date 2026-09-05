# M10 — Code Review 与 Change Engineering：把 PR 当作可审查的工程论证

> Code review 不是“找几个 bug”，也不是“帮作者把代码改成 reviewer 喜欢的风格”。
>
> 本章的核心定义是：
>
> **一个 PR / CL 是一份 bounded engineering argument：它声称某个具体 change 应当进入系统，并用代码、测试、迁移策略和其他证据支撑这个 claim。**

前九章已经分别训练了：

```text
M01  什么行为算正确？
M02  谁拥有 knowledge / state？
M03  什么 evidence 真能区分对错？
M04  boundary 对 caller 承诺什么？
M05  怎样改变结构而保持行为？
M06  证据不足时怎样先建立 feedback？
M07  interleaving / crash / retry 下 invariant 是否仍成立？
M08  old/new producer/consumer 怎样共存？
M09  哪些 boundary / authority / failure decision 值得上升成 architecture？
```

M10 把这些能力压缩到一个日常工程单位：

```text
Pull Request / Change List
```

---

# 1. 为什么 Agent 时代更需要 Code Review，而不是更少

生成代码的成本下降后，很容易产生一个错觉：

```text
implementation 便宜
→ review 也应该便宜
```

但两者不是同一个问题。

Agent 可以非常快地产生：

- 400 行 refactor；
- 20 个 tests；
- 一段很可信的 PR summary；
- 一份“all tests pass”的 evidence；
- 一个看起来整洁的新 abstraction。

这些会降低：

```text
implementation effort
```

却不会自动降低：

```text
system-understanding cost
contract-reconstruction cost
compatibility reasoning cost
failure analysis cost
review responsibility
```

甚至可能反过来增加 review pressure：

```text
code generation bandwidth ↑↑
review bandwidth         ≈
```

如果一个团队只是把 Agent 生成的 patch 更快塞进 CI，那么瓶颈会从 coding 转成：

```text
semantic verification
```

因此 Agent 时代的核心问题不是：

> 怎样让 reviewer 更快扫完 diff？

而是：

> **怎样把 change 设计成 reviewer 能在有限 mental model 中独立判断？**

---

# 2. Code Review 到底在 approve 什么？

一个 reviewer 点下 Approve，并不是说：

```text
我没有看到红色语法错误
```

也不是：

```text
CI 是绿的
```

更不是：

```text
作者比我熟，我相信他
```

一个有意义的 approval 更接近：

> **基于我实际 review 的 scope 和 evidence，我认为这个 change 的工程 claim 成立，并且 residual risk 在这个系统的标准下可接受。**

这句话里有五个关键词：

```text
scope
claim
evidence
risk
standard
```

任何一个不清楚，approval 的含义都会变弱。

---

# 3. PR 不是 Diff

Diff 只是 change 的一种表示。

一个完整 change 至少有：

```text
Problem
Intent
Existing system context
Changed behavior
Intentionally unchanged behavior
Implementation
Tests / probes
Migration / rollout
Failure behavior
Rollback story
Known limitations
```

而普通 diff viewer 通常只直接展示：

```text
Implementation delta
```

这就是为什么：

```text
只看 changed lines
```

经常不足以 review。

例如你看到：

```python
for job_id in sorted(state.jobs):
```

单看这一行很容易得到：

```text
“不错，更 deterministic。”
```

但如果系统 contract 是：

```text
jobs 保持 submission order
scheduler FIFO
```

并且 ID 是：

```text
job-1
job-2
...
job-10
```

那么 lexicographic sort 会产生：

```text
job-1
job-10
job-11
job-2
...
```

真正需要 review 的不是那一行 syntax。

而是：

```text
这条 implementation change
→ 改变了哪个 semantic ordering？
→ 哪些 caller / durable artifact / scheduling decision 依赖它？
```

---

# 4. Author Description 是 Claim，不是 Truth

一个好的 PR description 很重要。

Google Engineering Practices 明确要求 CL description 解释：

- change 做什么；
- 为什么这样改；
- future reader 应怎样理解 decision。

Source:

https://google.github.io/eng-practices/review/developer/cl-descriptions.html

但必须避免另一种错误：

```text
作者写了“behavior-preserving refactor”
→ reviewer 从此以“它确实 behavior-preserving”为前提看 diff
```

这叫 anchoring。

更好的模型是：

```text
PR description
=
author's hypothesis / argument
```

reviewer 要独立验证。

例如 description 声称：

```text
No public behavior changes.
```

reviewer 应自动转成问题：

```text
哪些 public behavior surface 存在？
哪个 evidence 证明它们没变？
```

而不是把它当事实复制进自己的 review summary。

---

# 5. Review 的第一步不是读代码

Google 的 `Navigating a CL in review` 给出一个很好的顺序：

1. broad view；
2. main part；
3. remaining files；
4. 某些情况下可以先读 tests。

Source:

https://google.github.io/eng-practices/review/reviewer/navigate.html

本课程把它进一步工程化成 **Review Funnel**。

---

# 6. Review Funnel

## Stage 0 — Should this change exist?

先问：

```text
这个 change 是不是解决真实问题？
是不是现在应该做？
是不是放在正确 system boundary？
```

典型错误：

```text
需求只是“worker 以后可能 remote”
```

Agent 直接产生：

```text
Kafka + Redis + gRPC + Kubernetes
```

即使代码都正确，也可能是错误 change。

reviewer 应该尽早阻断：

```text
wrong problem / wrong scope / speculative architecture
```

而不是先逐行 review 2000 行实现。

---

## Stage 1 — What exactly is the claim?

用你自己的话写：

```text
This change claims to ...
```

例如：

```text
This change claims to centralize lifecycle authority
without changing existing behavior.
```

注意：

```text
centralize authority
```

和：

```text
behavior-preserving
```

是两个不同 proof obligations。

可能出现：

```text
architecture improvement = true
behavior preservation   = false
```

不能因为大方向正确就忽略后者。

---

## Stage 2 — What must remain true?

从前面模块恢复：

```text
contracts
invariants
authority rules
ordering
error semantics
side effects
compatibility
failure behavior
```

形成 **change-specific invariant sheet**。

例如：

```text
- list_jobs preserves submission order
- claim_next is FIFO among queued jobs
- unknown cancel currently raises through public boundary
- snapshot v1 remains readable
- default snapshot writer stays v1
- historical M07 fault-injection module remains intentionally unsafe
```

这里非常重要的是：

> 只列与当前 change 有关的东西。

不是把整个项目所有 known issues 都拖进这次 review。

---

## Stage 3 — Find the semantic center of the diff

不要机械按文件顺序开始。

先找：

```text
哪个 change 决定了大部分新行为？
```

例如 authority refactor：

```text
job_authority.py
```

可能是 semantic center。

其他文件：

```text
service.py
worker.py
metrics.py
legacy_audit.py
```

更多是在 routing。

如果 center 本身设计错误，先反馈 center。

不要先 nitpick：

```text
import order
变量命名
docstring punctuation
```

---

# 7. Review Change，不是 Review 作者

Code review comment 的对象必须是：

```text
code / design / consequence
```

而不是：

```text
作者能力 / 动机 / 性格
```

Google reviewer guide 明确强调 comment 针对 code，而不是 developer，并建议解释 why。

Source:

https://google.github.io/eng-practices/review/reviewer/comments.html

例如：

差：

```text
你怎么会想到用 sorted？
```

好：

```text
Blocker: `sorted(state.jobs)` changes the existing submission-order/FIFO
contract once IDs reach `job-10`; the second claim becomes `job-10` rather
than `job-2`. Please preserve insertion order or explicitly split this into
a behavioral change with the corresponding contract/migration discussion.
```

第二种 comment 包含：

```text
severity
location
violated contract
consequence
required outcome
```

而不是攻击作者。

---

# 8. Review Comment 的最小结构

本课程推荐重要 comment 尽量回答五件事：

```text
1. Severity
2. Observation
3. Engineering reason
4. Consequence / risk
5. Required outcome
```

模板：

```text
Blocker — <short title>

At <location>, the change does X.
The existing contract/invariant requires Y.
This can cause Z.
Evidence: ...
Please ensure ...
```

注意最后一句不是一定要写：

```text
请按我下面 17 行代码实现
```

Google reviewer guide 也强调 reviewer 不必替 developer 完成 detailed solution design。

指出：

```text
what must become true
```

往往比规定：

```text
how exactly to code it
```

更好。

---

# 9. Severity 必须清楚

一个 review 如果只有：

```text
comment A
comment B
comment C
```

作者不知道：

```text
哪些必须修？
哪些只是建议？
哪些是 FYI？
```

本课程使用：

```text
Blocker
Important / Should fix
Nit
Optional / Consider
FYI
```

不要求具体平台支持这些 label。

重点是 reviewer intent 清晰。

Google reviewer guidance 也建议显式区分 required change 与 suggestion/nit。

---

# 10. 什么才是 Blocker？

典型 blocker：

### 10.1 Contract regression

```text
旧 caller 合法输入现在错误
```

### 10.2 Invariant violation

```text
两个 worker 可以同时 claim 一个 job
```

### 10.3 Hidden compatibility break

```text
new writer 先于 old readers 退出
```

### 10.4 Incorrect failure semantics

```text
timeout 后 blind retry duplicate external effect
```

### 10.5 Security / authority violation

```text
remote worker 获得 durable DB write credential
```

### 10.6 Evidence does not support the claim

```text
PR 声称并发安全
但 test 只有单线程 happy path
```

### 10.7 Change scope invalid

```text
behavior-preserving refactor 偷带 public API behavior change
```

---

# 11. 什么通常不该是 Blocker？

例如：

```text
“我更喜欢另一个变量名”
“我会拆成两个 helper”
“这里可以换一种 pattern”
```

如果两个方案工程上等价：

```text
reviewer preference
!=
mandatory requirement
```

Google 的 `The Standard of Code Review` 明确强调 technical facts/data 应优先于 personal preference，并且不应追求“完美代码”阻碍明显改善 code health 的 change。

Source:

https://google.github.io/eng-practices/review/reviewer/standard.html

---

# 12. CI Green 到底证明了什么？

最危险的句子之一：

```text
Tests pass, so LGTM.
```

M03 已经知道：

```text
6 tests green
```

并不妨碍三个 meaningful mutants survive。

M10 再把这一点放进 review context。

CI 只能证明：

```text
selected executable checks
ran in selected environment
and returned selected success result
```

它不能自动证明：

```text
selected checks were sufficient
oracle was correct
contract was complete
missing caller was compatible
failure path was explored
migration order was valid
```

Google 的 reviewer guide 明确要求 human review tests 是否 valid，并问：

```text
坏代码时这些 tests 真的会失败吗？
```

Source:

https://google.github.io/eng-practices/review/reviewer/looking-for.html

---

# 13. Gerrit 给了一个很好的现实模型

Gerrit 官方默认概念中：

```text
Verified
```

与：

```text
Code-Review
```

是不同 review labels。

官方文档里，`Verified` 历史上表达：

```text
compile / basic unit tests succeeded
```

`Code-Review` 则表达人工 reviewer 对代码的判断。

Sources:

https://gerrit-review.googlesource.com/Documentation/config-labels.html

https://gerrit-review.googlesource.com/Documentation/config-submit-requirements.html

这不是说所有团队都要用 Gerrit。

它只是很好地体现：

```text
machine verification signal
!=
human review signal
```

---

# 14. Review Evidence，不只是 Review Production Code

很多 reviewer 会认真看：

```text
src/
```

然后快速扫：

```text
tests/
```

这是危险的。

tests 也是 change 的一部分。

你需要问：

```text
这个 test 对应哪个 claim？
这个 oracle 是从 spec 来还是从 implementation copy 来？
这个 input partition 为什么能代表风险？
这个 test 在 mutant/bug 下真会红吗？
有没有只测 happy path？
有没有把新行为直接写进 expected，而没有 fail-before？
```

尤其 Agent 很容易产生：

```text
production code
+
matching tests
```

二者可以一起错，而且一起绿。

---

# 15. Author-Written Test 可能只是自证循环

例如实现：

```python
return sorted(state.jobs)
```

Agent 同时写：

```python
assert list_jobs() == sorted(expected)
```

CI 当然绿。

但这只是：

```text
implementation assumption
→ copied into oracle
```

而不是：

```text
contract
→ independent oracle
```

reviewer 要寻找：

```text
independent source of truth
```

例如：

- M03 明确 contract：submission order；
- historical fixture；
- public API documentation；
- migration matrix；
- user requirement；
- domain invariant。

---

# 16. Review Surrounding Code，而不是只看 Diff Context

Google reviewer guide 明确建议在需要时看整个 file 和 broader system context。

这是因为很多关键事实在 diff 外：

```text
caller
state owner
old reader
serialization format
retry loop
cleanup path
background worker
```

例如 patch：

```python
except KeyError:
    return False
```

局部看非常合理。

但 public boundary 可能原来是：

```text
unknown ID -> error
```

那么这个一行变化其实是：

```text
API semantic change
```

所以 review 路径应该是：

```text
changed code
→ caller
→ boundary
→ contract
```

---

# 17. “当前行为很烂”不等于可以偷偷改

M04 的 TaskForge starter 故意让 unknown ID 泄漏 `KeyError`。

这不是理想 API。

但假设一个 PR 声称：

```text
behavior-preserving architecture refactor
```

然后顺手改成：

```text
unknown cancel -> False
```

reviewer 应该指出：

```text
out-of-scope behavior change
```

即使新行为可能更好。

为什么？

因为：

```text
“更好”
```

不自动等于：

```text
“应该隐藏在当前 change 里”
```

如果真的要改，应该成为明确 behavior change：

```text
new contract
+ caller impact
+ tests
+ compatibility story
```

这就是 M05 的 Two Hats 在 review 层面的延伸。

---

# 18. Review 不能无限 Scope Creep

反过来也一样。

reviewer 可能在 surrounding code 发现：

```text
service.get() exposes mutable Job
```

M02 已经知道这是设计问题。

但如果当前 PR 只是：

```text
fix snapshot v2 reader
```

你不能自动要求作者：

```text
顺便重做整个 state ownership
```

reviewer 要区分四类问题：

```text
A. introduced regression
B. prerequisite to make this change correct
C. pre-existing defect worth filing
D. unrelated cleanup / preference
```

只有 A/B 通常是当前 change blocker。

C 可以：

```text
FYI + issue/follow-up
```

D 甚至不一定值得 comment。

---

# 19. Review Change Type，而不是套一张 Checklist

*Software Engineering at Google* Chapter 9 区分：

- greenfield；
- behavioral change；
- bug fix / rollback；
- refactoring / large-scale change。

Source:

https://abseil.io/resources/swe-book/html/ch09.html

不同 change type 有不同 proof obligation。

## Refactor

核心：

```text
behavior preservation
```

看：

```text
behavior inventory
regression evidence
change topology
```

## Bug Fix

核心：

```text
bug existed
fix removes it
```

看：

```text
fail-before
pass-after
neighboring cases
```

## Migration

核心：

```text
old/new coexistence
```

看：

```text
compatibility matrix
rollout order
rollback
contract phase
```

## Concurrency Change

核心：

```text
history / interleaving
```

看：

```text
safety
liveness
linearization point
failpoints
```

## Architecture Change

核心：

```text
authority / knowledge / failure boundary
```

看：

```text
what moved
what became long-lived
what failure crosses boundary
reversal cost
```

---

# 20. 一个通用的 Review Matrix

| Dimension | Reviewer question |
|---|---|
| Problem | 这个 change 解决了正确问题吗？ |
| Scope | patch 是否只包含这个 engineering claim 所需内容？ |
| Contract | 哪些 observable behavior 改了 / 保持？ |
| Invariant | 什么必须在所有路径继续成立？ |
| Ownership | 谁现在拥有 knowledge/state/decision？ |
| Failure | timeout/crash/retry/partial failure 怎么样？ |
| Compatibility | old/new caller/data/protocol 能否共存？ |
| Evidence | tests/probes 真能证伪错误实现吗？ |
| Operability | 上线后怎样知道它坏了？ |
| Rollback | change 能否被安全撤销？ |
| Complexity | 是否引入超过需求的 mechanism？ |
| Reviewability | reviewer 是否能在 bounded model 中理解它？ |

不是每个 PR 都要同样深入检查 12 项。

这是：

```text
risk-triggered review map
```

不是表格宗教。

---

# 21. Small Change 的真正含义

Google 的 Small CL guidance 强调小 change 更容易：

- review；
- test；
- rollback；
- merge；
- 理解。

Source:

https://google.github.io/eng-practices/review/developer/small-cls.html

但：

```text
small != N LOC
```

本课程定义：

> **A small change is one coherent engineering claim with bounded consequences and independently reviewable evidence.**

例如：

```text
rename 12,000 generated references
```

可能 LOC 巨大，但 semantic change 很机械。

而：

```text
改 7 行 retry logic
```

可能影响：

```text
load amplification
external duplication
SLO
failure propagation
```

semantic scope 很大。

---

# 22. Diff Size 与 Semantic Size 不同

可以写：

```text
textual size     = 8 lines
semantic surface = huge
```

也可能：

```text
textual size     = 5000 lines
semantic surface = one mechanical rename
```

reviewer 应估算的是：

```text
semantic surface
```

而不仅是：

```text
+423 -177
```

---

# 23. Review Order：Risk First

一种有效顺序：

```text
1. Description / problem
2. Semantic center
3. Contract-affecting code
4. Failure/migration/authority path
5. Tests and evidence
6. Callers / surrounding code
7. Mechanical/supporting changes
8. Naming / polish / nits
```

为什么不是从 line 1 开始？

因为 reviewer time 是有限资源。

如果 20 分钟后才发现：

```text
migration rollout order 根本不成立
```

前面的 naming comments 都是低价值工作。

---

# 24. Review Findings 要按 Root Cause 聚合

假设 `sorted(job_ids)` 导致：

```text
list order wrong
claim FIFO wrong
snapshot order wrong
audit output wrong
```

可以写四个 comments。

但更好的 review 可能是一个 root-cause blocker：

```text
Blocker — sorting by opaque/string job ID replaces the existing
submission-order semantics. This affects both scheduler FIFO and all consumers
of list_jobs, including snapshot/audit output. IDs are not an ordering key.
```

然后给一两个 reproduction。

这比：

```text
line 17 wrong
line 33 wrong
snapshot changed
audit changed
```

更有 engineering value。

---

# 25. Review 不需要证明“没有任何 bug”

这是不可能目标。

reviewer 要做的是：

```text
建立足够强的 acceptance argument
```

并判断 residual risk。

可以写：

```text
I reviewed lifecycle semantics, ordering, and compatibility.
I did not review the security properties of the future remote-worker transport.
```

scope 明确比模糊的：

```text
LGTM
```

更有价值。

Google reviewer guide 也建议 reviewer 在只覆盖部分 files/aspects 时明确说明 review scope。

---

# 26. Qualified Reviewers 与 Risk Ownership

不是所有 reviewer 都必须懂所有东西。

当 change 触及：

```text
security
privacy
concurrency
accessibility
schema migration
crypto
```

reviewer 应知道：

```text
自己的 review competence 边界
```

然后确保有合适的人覆盖。

这不是推卸责任。

恰恰是：

```text
明确 responsibility allocation
```

和 M01/M02 的思想一致。

---

# 27. Review Speed 为什么也是 Engineering Concern

慢 review 会造成：

```text
large stacked changes
context loss
author work built on unapproved assumptions
pressure to waive quality
```

Google reviewer guide 明确把 team velocity 而不是 reviewer 个体 velocity 作为 review speed 的优化目标。

Source:

https://google.github.io/eng-practices/review/reviewer/speed.html

本课程不采用具体的“一工作日”SLA。

但采用一个 principle：

> **Major structural feedback should be surfaced early.**

因为越晚指出：

```text
整个 authority model 不对
```

后续 sunk cost 越高。

---

# 28. Review Record 是未来系统的一部分

一个好的 review comment 可能在半年后解释：

```text
为什么不能把 timeout 当 failure
为什么 writer cutover 晚于 reader rollout
为什么这个 weird compatibility branch 还不能删
```

因此 review 不是瞬时 chat。

它也是：

```text
change history
```

如果 review 中达成了新的长期 design decision：

```text
最好更新 code / docs / ADR / PR description
```

不要让唯一 explanation 永远埋在 review thread。

---

# 29. Agent 生成的 PR 有哪些特殊 Failure Mode？

## 29.1 Confident summary

Agent 写：

```text
This is a behavior-preserving refactor.
```

语气不能作为 evidence。

---

## 29.2 Tests mirror implementation

Agent 同时写实现和 oracle。

---

## 29.3 Broad cleanup

Agent 很喜欢顺手：

```text
rename
format
extract helper
change errors
sort output
```

导致 semantic diff 被噪声埋没。

---

## 29.4 Silent assumption completion

任务没说 ordering。

Agent 会自动挑一个：

```text
sorted = deterministic = better
```

但这里实际上需要 contract reasoning。

---

## 29.5 Tool-output laundering

Agent summary：

```text
All tests pass.
```

但可能：

- 没跑 full suite；
- 跑错 worktree；
- skipped important test；
- command 根本没覆盖 target；
- tests 本身没牙齿。

reviewer 应尽可能看到：

```text
exact command
exact environment
exact result
```

而不是只信 summary。

---

# 30. Agent Review Workflow

本课程推荐：

```text
Phase 1 — Author/Agent implementation
Phase 2 — Freeze author narrative
Phase 3 — Independent reviewer reconnaissance
Phase 4 — Reviewer writes own change model
Phase 5 — Compare against author claims
Phase 6 — Targeted verification
Phase 7 — Findings by severity/root cause
Phase 8 — Author/Agent fixes
Phase 9 — Re-review latest patch, not old mental snapshot
```

非常关键：

> **不要让实现 Agent 同时成为唯一 reviewer。**

可以用同一个模型，但应是：

```text
new context
fresh prompt
independent evidence reconstruction
```

而不是：

```text
“检查一下你刚才写的有没有问题”
```

后者容易 self-confirm。

---

# 31. 一个差的 Agent Review Prompt

```text
Review this PR and tell me if it looks good.
```

很容易得到：

```text
整体实现清晰
测试充分
建议加一点注释
LGTM
```

因为任务没有要求 reviewer 独立重建任何东西。

---

# 32. 一个更好的 Agent Review Contract

```text
You are the independent reviewer, not the implementation author.

Before reading the author's conclusions as facts:
1. reconstruct the change goal from issue + diff;
2. identify changed contracts, invariants, authority boundaries, failure paths,
   compatibility surfaces, and durable artifacts;
3. classify this as refactor / behavior change / migration / concurrency /
   architecture change or a mixture;
4. inspect tests as code and explain what each important test actually proves;
5. run targeted counterexamples where existing evidence is weak;
6. distinguish regressions introduced by this PR from pre-existing problems;
7. report findings in severity order with file/location, violated contract,
   consequence, and evidence;
8. do not approve merely because CI is green or the author summary is plausible.
```

这个 prompt 的核心不是“更长”。

而是强迫 Agent 建立：

```text
independent review authority
```

---

# 33. Reviewer 自己也会犯什么错？

## 33.1 Anchoring

先读作者 summary，然后只寻找支持它的证据。

## 33.2 Nit saturation

大量小评论让 reviewer 感觉“review 很认真”，却没有检查主要 risk。

## 33.3 Design substitution

把个人偏好当 correctness。

## 33.4 Scope explosion

看到任何旧债都要求当前 PR 修。

## 33.5 CI outsourcing

把测试判断完全交给 automation。

## 33.6 Historical-probe absolutism

旧 test/probe 失败就认定新 change 错。

M09 已看到：

```text
architecture topology 改变后
baseline inventory probe 应该升级
```

历史工具也有 scope/version。

## 33.7 Stale approval

patch set 改了大量核心代码后，reviewer 仍按旧 mental model approve。

---

# 34. 新 Patch Set 必须重新判断什么？

不是每次都从零 review。

但要问：

```text
作者修 finding 时改了哪些 assumptions？
```

如果原 blocker 是：

```text
ordering semantics
```

修复方式却重写：

```text
ID allocation
```

那 review scope 已变化。

不要只看：

```text
comment resolved
```

要看：

```text
new diff consequence
```

---

# 35. Review 与 Ownership

M02 说：

```text
Authority = who can decide legal state transition
```

M10 可以类比：

```text
Review authority = who is accountable for accepting this class of change
```

但不要混淆：

```text
code owner
reviewer
security approver
product owner
```

他们可能回答不同问题。

例如：

```text
CI       -> selected executable checks
reviewer -> correctness / design
owner    -> codebase stewardship
security -> threat boundary
```

这也是为什么治理系统常有多个独立 gates。

---

# 36. TaskForge M10 Review Case

本章给你一份 Agent candidate PR：

```text
review-cases/m10/agent-pr-description.md
review-cases/m10/agent-pr.patch
```

它声称：

```text
centralize Job lifecycle authority
preserve all existing behavior
low risk internal refactor
9 tests passed
```

你的第一任务不是运行 hidden probe。

而是：

```text
先写自己的 review model
```

问：

```text
这到底是哪种 change？
哪些行为必须保持？
哪些旧问题是 out-of-scope？
哪些新 line 有 semantic consequence？
作者新增 test 真的覆盖这些 risk 吗？
```

---

# 37. 为什么这个 Case 不是“找彩蛋”

真正目标不是猜 instructor 藏了几个 bug。

而是训练：

```text
从 contract 推导 adversarial example
```

而不是：

```text
从异常代码风格猜 bug
```

例如看到：

```python
sorted(state.jobs)
```

你不应该因为“sorted 可疑”就报错。

应该推导：

```text
ID ordering = lexical
contract ordering = submission
```

然后构造最小反例：

```text
job-1 ... job-10
```

这是 engineering review。

---

# 38. 什么时候 reviewer 应自己跑代码？

不是所有 PR 都要 reviewer 本地 checkout。

但下面情况很值得：

```text
user-visible behavior hard to infer from diff
concurrency
migration
serialization
performance claim
failure recovery
suspiciously weak tests
```

Google reviewer guide 也明确允许 reviewer 自己 validate behavior，并指出 concurrency 很难只靠运行发现，需要 reasoning。

因此本课程使用：

```text
reasoning + targeted execution
```

而不是二选一。

---

# 39. Targeted Probe 比“再跑一次全套 CI”更有信息量

如果 CI 已经：

```text
9 passed
```

reviewer 再运行同一命令，得到：

```text
9 passed
```

信息增量很低。

如果你的 hypothesis 是：

```text
lexical ID sort breaks FIFO after 9
```

更好的 probe：

```text
submit 12 jobs
claim twice
```

如果 hypothesis 是：

```text
public error behavior changed
```

更好的 probe：

```text
cancel unknown ID
```

review evidence 应针对 uncertainty。

---

# 40. “我没看出问题”不是 Acceptance Argument

高质量 approval 可以很短。

但你的内部 reasoning 至少应能回答：

```text
What did I review?
What did I not review?
What were the high-risk claims?
What evidence supports them?
What residual risk remains?
```

最终 comment 可能只是：

```text
LGTM. Reviewed lifecycle ordering, public cancel behavior, and authority routing;
existing M07 fault-injection module is intentionally outside the architecture
cleanup scope.
```

这比：

```text
Looks good!
```

信息强得多。

---

# 41. Review Decision 是三值以上，不是二值

现实里不是只有：

```text
approve / reject forever
```

至少有：

```text
Approve
Approve with non-blocking comments
Request changes
Need specialist review
Need design discussion before code review
Split change first
```

尤其 architecture-heavy change：

如果核心争议是：

```text
系统到底应不应该有这个 boundary？
```

可能需要先回 design discussion，而不是把架构辩论塞在 300 行 diff comments 里。

---

# 42. Review Completion 的一个实用 Definition

可以认为 review 达到可接受状态，当：

```text
1. Change claim 清楚；
2. Scope 清楚；
3. Blocker contracts/invariants 已有可信 evidence；
4. Major failure/migration paths 已被考虑；
5. Author tests 的 oracle 已被审查；
6. New comments 不再暴露新的 system-model misunderstanding；
7. Residual issues 要么 non-blocking，要么有明确 follow-up owner；
8. Latest patch set 已重新确认。
```

不是：

```text
comment count = 0
```

---

# 43. M00–M09 如何在一次 Review 中重新出现

一次 authority refactor review 可以同时调用：

```text
M00: change amplification 是否下降？
M01: behavior-preserving 的 contract 到底是什么？
M02: authority 是否真的集中？
M03: 9 tests 的 discriminating power 如何？
M04: error semantic 是否偷变？
M05: structural / behavioral change 是否混在一起？
M06: legacy audit 是否仍被 characterize？
M07: claim semantics / concurrency path 是否受影响？
M08: snapshot durable output 是否改变？
M09: architecture boundary 是否与 intended authority 对齐？
```

这就是为什么 M10 不是“另一个专题”。

它是前九章的 integration point。

---

# 44. 本章的核心 Review Loop

```text
Change request
     ↓
Author argument
     ↓
Independent reviewer system model
     ↓
Change classification
     ↓
Contract / authority / failure / compatibility map
     ↓
Semantic diff review
     ↓
Evidence review
     ↓
Targeted counterexamples
     ↓
Findings by root cause + severity
     ↓
Updated patch
     ↓
Re-review changed assumptions
     ↓
Accept / reject / split / escalate
```

---

# 45. 最后一个重要原则：Review 是 Change Engineering，不是静态审美

优秀 reviewer 不是：

```text
最会挑命名的人
```

而是能判断：

```text
这次 change 为什么应该存在；
它真正改变了什么；
它不能改变什么；
哪些 failure/compatibility consequence 被遗漏；
作者的 evidence 是否真的支持 claim；
怎样用最小 comment 把系统拉回正确演化路径。
```

所以本章最终定义：

> **Code Review 是对一次系统演化提案进行独立工程验证，并决定它是否足够安全、清晰、可维护地进入 shared history。**

Agent 可以写 patch。

Agent 也可以辅助 review。

但：

> **approval 本质上仍是 engineering authority。**

谁拥有这个 authority，谁就必须对 acceptance argument 负责。

---

# 46. 进入 Lab 前的自检

在打开 M10 candidate patch 前，先确认你能回答：

1. PR description 为什么是 claim 而不是事实？
2. 为什么 CI green 不能推出 approve？
3. blocker 和 personal preference 的边界是什么？
4. 为什么要先看 semantic center，再看 nit？
5. 怎样区分 introduced regression 与 pre-existing defect？
6. 为什么 change type 决定 proof obligation？
7. 为什么一个 8 行 change 可能比 5000 行 mechanical change 更难 review？
8. 怎样写一个包含 consequence 和 evidence 的 blocker comment？
9. 为什么 reviewer 不应该让实现 Agent 成为唯一审查 authority？
10. 为什么 historical probe 失败有时说明 probe scope 过时，而不是新代码错？

如果这些问题已经能用自己的话回答，就进入：

[`../labs/10-code-review-change-engineering.md`](../labs/10-code-review-change-engineering.md)
