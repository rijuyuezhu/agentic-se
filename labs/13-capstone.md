# Lab 13 — Capstone：Lease Recovery、Compatibility 与 Agent-assisted Change Engineering

这个 lab 是整门课的综合考核。

你不会得到一个已经完全一致的 specification。

你会得到：

- 一个已经运行多个版本的 TaskForge starting point；
- 一个真实风格但存在错误 guarantee 的 feature request；
- 一组会全部通过的 baseline tests；
- deterministic failure probes；
- 一个只有在你完成 first-pass issue review 后才应该读取的 human decision pack。

你的目标不是“把 lease feature 写出来”。

你的目标是提交一份**可以被独立审查、可以解释 migration/rollback、可以重放 evidence、并且没有把 engineering authority 偷偷交给 Agent 的完整 change record**。

---

# 0. Starting Point

目录：

```text
labs/taskforge/capstone-starter/
```

先读：

```text
README.md
ISSUE.md
```

此时**不要读**：

```text
decision-pack/01-after-issue-review.md
```

也不要修改 production code。

---

# 1. Baseline Evidence

运行：

```bash
cd labs/taskforge/capstone-starter
PYTHONPATH=src uv run --with pytest --no-project python -m pytest -q
```

预期 baseline：

```text
6 passed
```

然后：

```bash
PYTHONPATH=src uv run --with pytest --no-project \
  python tools/capstone_baseline_probe.py
```

记录输出，不要只截图一句结论。

你的 baseline note 必须至少回答：

1. schema version 是什么？
2. public submit response 是什么？
3. concurrent claim history 发生了什么？
4. final row 为什么可能掩盖 bad history？
5. operator requeue 后 stale finish 为什么仍能成功？
6. 哪些 baseline tests 没有检查这些问题？

---

# 2. First-pass Issue Review

只根据：

```text
ISSUE.md
current code
baseline evidence
```

写一份：

```text
submission/01-issue-review.md
```

至少包含四部分。

## 2.1 Requirements

逐条列出原 issue 的 explicit requirements。

不要自己改写成你希望它表达的需求。

## 2.2 Existing compatibility surfaces

至少检查：

```text
public API
SQLite schema
worker claim response
worker finish payload
background maintenance behavior
```

## 2.3 Assumptions

对 issue 中每个强 guarantee 问：

```text
这条结论依赖什么假设？
代码/协议现在真的支持这个假设吗？
```

## 2.4 Contradictions / unresolved decisions

必须明确标：

```text
IMPLEMENTABLE AS WRITTEN
AMBIGUOUS
CONTRADICTORY
NEEDS AUTHORITY DECISION
```

不要把 unresolved product semantics 变成 implementation Agent 的自由发挥空间。

---

# 3. Gate A — Issue Review Freeze

在继续之前，把你的 `01-issue-review.md` 保存为一个独立 checkpoint。

如果你使用 Git：

```text
commit / tag / patch artifact
```

均可。

目的不是流程仪式。

而是让你之后能比较：

```text
在看 human decision 之前
你独立发现了什么？
```

---

# 4. 读取 Human Decision

现在读：

```text
decision-pack/01-after-issue-review.md
```

写：

```text
submission/02-decision-delta.md
```

分三类：

```text
I FOUND IT
I PARTIALLY FOUND IT
I MISSED IT
```

至少覆盖：

- exactly-once guarantee；
- manual vs automatic recovery；
- attempt identity；
- existing claim race；
- mixed-version activation gate；
- rollback boundary。

这份 delta 是 graded artifact。

因为它能区分：

```text
真正独立 reasoning
```

和：

```text
读完答案后觉得“我本来就知道”
```

---

# 5. System Model

创建：

```text
submission/03-system-model.md
```

至少包含五个 view。

## 5.1 Responsibility / knowledge

至少包括：

```text
api.py
service.py
db.py
remote_worker.py
maintenance.py
external command/effect owner
```

## 5.2 Authority / state

明确：

```text
job lifecycle authority
current attempt authority
worker identity
recovery policy
lease expiry
external effect dedup authority
```

## 5.3 Runtime protocol

至少画出：

```text
submit
claim
heartbeat (future)
finish
expiry
requeue
new claim
stale finish
```

## 5.4 Durable / compatibility

至少列：

```text
schema v1/v2
server v1/v2
worker v1/v2
legacy/default recovery policy
```

## 5.5 Failure / rollback

至少包含：

```text
worker crash
partition
late finish
late heartbeat
server rollback
schema expanded but semantics inactive
semantics activated
```

---

# 6. Contract Inventory

创建：

```text
submission/04-contracts.md
```

建议使用：

| Surface | Existing contract | New contract | Must remain | Explicit non-guarantee |
|---|---|---|---|---|

至少覆盖：

- v1 public submit；
- v2 opt-in submit；
- v1 worker claim；
- v1 finish；
- v2 claim；
- v2 heartbeat；
- v2 finish；
- automatic recovery；
- schema migration；
- rollback。

必须有一行明确写：

```text
arbitrary command external effect exactly-once is NOT guaranteed
```

如果你决定提供更强 guarantee，必须说明 external effect owner 如何参与，并获得额外 authority；不能靠 TaskForge DB 自己宣称。

---

# 7. State Machine / Attempt Model

画出至少：

```text
queued
  ↓ claim attempt=1
running(a1)
  ├─ finish(a1) → terminal
  └─ lease expires
        ↓
      queued(attempt history preserved)
        ↓ claim attempt=2
      running(a2)
```

然后明确：

```text
finish(a1) after a2 starts
heartbeat(a1) after a2 starts
```

必须发生什么。

不要只写：

```text
“应该忽略 stale worker”
```

要写 machine-checkable condition。

例如 conceptual form：

```text
accepted transition requires:
job.status == running
AND job.current_attempt == payload.attempt
AND job.current_worker == payload.worker_id
```

实现不要求完全照这个表达。

---

# 8. Design Memo / ADR

创建：

```text
submission/05-design-memo.md
```

至少回答：

1. current problem；
2. desired semantics；
3. non-goals；
4. attempt/fencing design；
5. claim atomicity design；
6. recovery policy design；
7. schema change；
8. protocol compatibility；
9. activation gate；
10. rollback boundary；
11. external effect residual risk；
12. rejected alternatives。

至少比较两种 implementation shape，例如：

```text
A. attempt columns on jobs
B. separate attempts table
```

或者：

```text
A. CAS claim
B. explicit transaction claim
```

不要为了“design it twice”故意写一个荒谬 strawman。

---

# 9. Compatibility Matrix

创建：

```text
submission/06-compatibility-matrix.md
```

最少覆盖：

| Server | Worker | Schema | Recovery active? | Expected |
|---|---|---|---|---|

至少分析：

```text
old server + schema v1
new server + schema v1 before migration
old server + expanded schema v2
new server + old worker
new server + new worker
old server after v2 attempt has been used
```

最后一行很重要。

不要只写：

```text
“旧 binary 能读新列，所以可以 rollback。”
```

你必须分析旧 binary 对**新语义 state**的理解。

---

# 10. Staged Implementation Plan

创建：

```text
submission/07-staged-plan.md
```

每个 stage 至少写：

```text
Goal
Allowed scope
Contract changed?
Evidence
Rollback/reversal
Stop conditions
```

一个合理但非唯一的 decomposition：

```text
Stage 0 characterize
Stage 1 fix v1 claim race
Stage 2 schema expand
Stage 3 dual worker protocol + attempt fencing
Stage 4 opt-in recovery submission
Stage 5 activation observability/gate
Stage 6 automatic requeue
```

你可以不同。

但如果计划只有：

```text
1. implement feature
2. test
3. deploy
```

视为没有 staged reasoning。

---

# 11. Agent Delegation Plan

创建：

```text
submission/08-agent-plan.md
```

至少定义三个角色。

## Reconnaissance Agent

只读。

输出：

```text
state writers
protocol entry points
DB queries
compatibility artifacts
```

## Implementation Agent

每个 stage 单独授权。

必须给：

```text
Goal
Allowed write paths
Invariants
Forbidden actions
Evidence contract
Stop/escalate conditions
```

## Independent Review Agent

不得只消费 implementation Agent 的 final summary。

要求它重新读取：

```text
issue
human decision
current code
diff
tests
migration artifacts
```

最终 acceptance 仍由你裁决。

---

# 12. Implementation Rule：一次只做一个 Stage

你可以使用 Agent 实现。

但每个 stage 完成后先保存 evidence，再进入下一个。

禁止：

```text
Stage 1 发现顺手可以做 Stage 4
→ 一起改了
```

除非重新更新 plan 并解释为什么 change topology 应改变。

---

# 13. Required Evidence A — Existing Claim Race

Baseline 已经能 deterministic reproduce：

```text
one queued job
+ two v1 workers
→ two success receipts
```

修复后必须证明：

```text
one queued job
+ two concurrent v1 claim calls
→ exactly one success receipt
```

注意：

```text
final row only has one worker
```

不是充分 evidence。

---

# 14. Required Evidence B — Schema Expand

你必须实际验证：

```text
v1 DB
→ v2 expand
→ old/frozen v1 binary still reads/writes legacy contract
```

建议真正复制一份 starter 作为 frozen binary code，而不是在 new code 中写一个 `legacy_mode=True` 模拟。

至少验证：

```text
old public submit works
old worker claim works
old finish works
schema version does not get accidentally downgraded
```

---

# 15. Required Evidence C — Attempt Fencing

构造：

```text
attempt 1 claim
lease expires
requeue
attempt 2 claim
attempt 1 finish arrives
```

必须：

```text
stale finish rejected
current attempt remains authoritative
```

再测：

```text
attempt 1 heartbeat arrives
```

也必须拒绝。

---

# 16. Required Evidence D — Legacy Finish Compatibility

在 migration window：

```text
v1 worker
```

仍要能完成：

```text
legacy attempt
```

但 old payload 不能完成：

```text
v2 attempt
```

否则 fencing boundary 可以被 compatibility handler 绕过。

---

# 17. Required Evidence E — Recovery Policy

Human decision 规定：

```text
legacy submit → manual
```

所以必须证明：

```text
manual job lease expires
→ automatic sweeper does not requeue it
```

新 opt-in automatic job 才允许：

```text
lease expires
→ requeue
```

这检查你有没有为了实现 feature 偷改 legacy semantics。

---

# 18. Required Evidence F — Exactly-once Negative Control

必须主动构造：

```text
attempt 1 executes external effect
lease expires
attempt 2 executes same external effect
```

然后展示：

```text
TaskForge can reject stale finish
BUT
external effect can already have happened twice
```

这是一个**必须通过的 negative-control test/probe**。

它的目的不是暴露你实现错误。

而是证明：

```text
你没有对 system guarantee 说谎
```

---

# 19. Required Evidence G — Activation Gate

设计可观察 gate。

至少包括：

```text
legacy_worker_count == 0
running_legacy_attempt_count == 0
stale-attempt evidence passed
post-activation rollback semantics reviewed
```

你可以增加条件。

必须测试：

```text
任何 blocker 存在 → gate closed
全部满足 → gate may open
```

不要直接把：

```text
enable_recovery = true
```

写进配置然后靠 runbook 人肉记忆。

---

# 20. Required Evidence H — Rollback Boundary

实际做两组实验。

## 20.1 Expand-only

```text
old binary
→ v1 DB
→ new migration expands DB
→ old binary runs again
```

期望：

```text
compatible
```

## 20.2 After v2 attempt semantics

```text
new server creates/claims v2 attempt
→ switch to frozen old server
→ send old finish payload
```

分析旧 server 是否理解 fencing。

如果不理解：

```text
simple old-binary rollback unsafe
```

把 evidence 放进 rollout plan。

---

# 21. Production Evidence Plan

创建：

```text
submission/09-production-evidence.md
```

至少定义：

```text
legacy_worker_count
running_legacy_attempt_count
v1_claim_success_count
v2_claim_success_count
stale_finish_rejected_count
stale_heartbeat_rejected_count
automatic_requeue_count
manual_requeue_by_sweeper_count
```

对每个 signal 写：

```text
why it exists
what decision it supports
metric/event/log?
cardinality considerations
```

不要用 `job_id` 作为 aggregate metric label。

它可以留在 diagnostic event。

---

# 22. Rollout / Rollback Plan

创建：

```text
submission/10-rollout.md
```

至少写：

## Phase A Expand

```text
change
entry condition
exit condition
rollback
```

## Phase B Protocol Migration

同上。

## Phase C Activation

同上。

## Failure actions

例如：

```text
stale rejection spikes
legacy worker unexpectedly appears
automatic requeue affects manual jobs
DB migration partial failure
```

对每个写 operator action。

---

# 23. Independent PR Review

在 implementation 完成后，先冻结 author summary。

然后做独立 review。

创建：

```text
submission/11-independent-review.md
```

至少检查：

### Issue/contract

- 是否重新声称 exactly-once？
- 是否改变 legacy submit？

### State ownership

- current attempt 是否唯一？
- compatibility handler 是否绕过 fencing？

### Concurrency

- claim race；
- expiry vs finish；
- stale heartbeat；

### Migration

- old binary actual evidence；
- schema defaults；
- activation gate；

### Rollback

- expand-only；
- post-activation；

### Evidence

- fail-before；
- negative controls；
- version-scoped tests；

### Scope

- unrelated refactor；
- new infrastructure；
- premature v1 deletion。

最后给：

```text
APPROVE
REQUEST CHANGES
SPLIT
NEEDS AUTHORITY DECISION
```

之一。

---

# 24. Review 必须能够推翻 Author

如果 implementation Agent 说：

```text
“所有测试都通过，完全实现 exactly-once recovery。”
```

但你的 negative control 证明 external effect duplicate 仍可能发生，那么 reviewer 必须把 author summary 判为错误。

Capstone 不接受：

```text
“Agent 自己解释它为什么对，我觉得合理。”
```

---

# 25. Retrospective

创建：

```text
submission/12-retrospective.md
```

至少回答：

## 25.1 哪三个最重要的 human authority decisions？

不能回答：

```text
“选变量名”
```

## 25.2 哪些工作最适合 Agent？

列具体任务。

## 25.3 Agent 在哪里最容易越界？

列实际观察。

## 25.4 哪些 guardrail 可以从 prompt 编译成 code/tool/policy？

例如：

```text
activation gate
compatibility test
schema migration checker
write scope
```

## 25.5 如果重做一次，你会改变 change topology 吗？为什么？

---

# 26. Submission Layout

最终建议：

```text
submission/
  01-issue-review.md
  02-decision-delta.md
  03-system-model.md
  04-contracts.md
  05-design-memo.md
  06-compatibility-matrix.md
  07-staged-plan.md
  08-agent-plan.md
  09-production-evidence.md
  10-rollout.md
  11-independent-review.md
  12-retrospective.md
```

代码和 tests 保留在你的 working copy / branch。

另附：

```text
EVIDENCE.md
```

记录所有实际执行命令与重要结果。

---

# 27. Evidence.md 最低要求

至少包括：

```text
baseline pytest result
baseline capstone probe
race fail-before
race pass-after
schema expand test
frozen old binary test
v2 stale finish test
v2 stale heartbeat test
manual recovery test
external duplicate negative control
activation gate tests
full test result
```

不要只写：

```text
“见 CI”
```

需要可重放 command。

---

# 28. Capstone Grading

总分 100。

## 20 — Mental Model

优秀：

- ownership / attempt / external effect boundary 准确；
- failure history 完整；
- 没把 DB representation 当 domain model。

## 15 — Issue / Contract Reasoning

优秀：

- 独立发现原 issue contradiction；
- 明确 non-guarantees；
- 正确升级 authority decision。

## 15 — Change Localization

优秀：

- staged changes 可独立理解、验证、回退；
- 没有“大 cleanup PR”。

## 15 — Migration / Rollback

优秀：

- frozen old binary actual evidence；
- version matrix；
- rollback boundary；
- observable activation gate。

## 15 — Evidence

优秀：

- deterministic races；
- negative controls；
- compatibility evidence；
- residual risk honest。

## 10 — Independent Review

优秀：

- reviewer 不依赖 author summary；
- findings 按 root cause；
- 能否证错误 guarantee。

## 10 — Agent Orchestration

优秀：

- Agent 做了大量 mechanical/recon work；
- task contracts 有 scope/evidence/escalation；
- human authority 清晰。

---

# 29. Automatic Deductions

以下会显著扣分。

## -20：没有 first-pass issue review 就直接读 decision pack

因为丢失了最关键的 independent reasoning evidence。

## -20：仍声称 arbitrary command exactly-once

除非你真的增加了 external-effect authority mechanism，并证明它覆盖目标 commands。

## -15：没有 migration / rollback runtime evidence

只有文档推断不够。

## -15：只看 final DB state，不测 concurrent history

## -10：Agent 被授权 merge/deploy/改 guarantee，但没有明确 human authority

## -10：为了“更现代”引入大型基础设施，却没有证明必要性

---

# 30. Instructor Reference 的用途

完成 submission 之后，才阅读：

[`../case-studies/m13/instructor-analysis.md`](../case-studies/m13/instructor-analysis.md)

Reference 不是标准实现。

你应该比较：

```text
我的 mental model 和 reference 哪不同？
我的 guarantee 是否更强/更弱？
我的 evidence 是否同样能证明 claim？
我的 migration 是否有不同但合理的 topology？
```

不要做结构 diff 后把自己代码改成 reference。

---

# 31. Final Question

完成所有 artifact 后，只用一页回答：

> **为什么这次 change 现在应该被 merge / rollout，或者为什么它还不应该？**

不能只写：

```text
tests pass
```

你的答案应该自然压缩：

```text
contract
architecture
authority
migration
failure model
evidence
residual risk
operational gate
```

这就是整个课程最后真正要考的能力。
