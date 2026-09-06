# M13 — Capstone：把 Software Engineering 变成一次完整的 Change

> 本章不再引入新的工程原则。
>
> 它只问一个问题：**当 system model、contract、state ownership、tests、migration、concurrency、architecture、production evidence 和 Agent orchestration 同时出现时，你还能不能保持判断清晰？**

---

# 0. 这一章不是“大作业功能题”

很多课程的 Capstone 会变成：

```text
功能更多
代码更多
框架更多
部署更复杂
```

但这并不自动意味着 software engineering 更难。

一个人完全可以写几千行功能代码，却从未真正回答：

- 现有 contract 是什么？
- 哪些行为其实只是 implementation accident？
- 谁拥有 lifecycle truth？
- crash 后哪个 attempt 仍有 authority？
- old reader / old worker / old binary 在 migration window 中会看到什么？
- rollback 是 binary rollback，还是 system-state rollback？
- tests 到底排除了哪些错误实现？
- Agent 是在执行已经做出的 engineering decision，还是在偷偷替人做 product / compatibility / production decision？

所以本 Capstone 的难度来自：

```text
多个真实约束发生交互
```

而不是：

```text
技术栈更多
```

---

# 1. Capstone System：一个已经“活过几个版本”的 TaskForge

前面的 TaskForge v0 是按教学目的逐章暴露问题的系统。

M13 提供一个独立 starting point：

[`../labs/taskforge/capstone-starter/`](../labs/taskforge/capstone-starter/)

它代表另一个时间点上的 TaskForge：

```text
existing public API clients
        ↓
TaskForge server
        ↓
SQLite durable state
        ↑
remote worker protocol
        ↑
old + current workers
```

同时有：

- durable SQLite schema v1；
- old CLI 依赖的 API response；
- remote worker claim / finish protocol；
- background maintenance scan；
- 一个已知 double-claim race；
- 一个历史 compatibility quirk；
- 全绿但明显不完整的 tests；
- 一个看起来合理、实际互相冲突的 feature request。

这比“从零设计一个可靠 scheduler”更接近真实工程。

因为你面对的是：

> **已经存在的世界。**

---

# 2. 原始需求

Capstone issue 见：

[`../labs/taskforge/capstone-starter/ISSUE.md`](../labs/taskforge/capstone-starter/ISSUE.md)

它大意要求：

```text
remote worker claim 增加 30s lease
lease 超时自动 requeue
worker crash 自动恢复
exactly once
旧 API 不变
旧 worker 继续工作
mixed old/new worker
无停机 migration
任何时刻可 rollback 老 server
finish payload 继续只有 job_id + exit_code
```

然后 issue 还说：

```text
“应该很小，加个 lease_expires_at 和 sweeper 就行。”
```

你的第一项工作不是写代码。

而是判断：

> **这个 issue 是否已经足够一致，能够直接交给 implementation Agent？**

---

# 3. Issue Review 不是需求复述

Issue review 应该至少拆成四类内容。

## 3.1 Explicit requirements

用户明确要求了什么？

例如：

```text
automatic recovery
old API compatibility
mixed-version workers
no maintenance window
```

## 3.2 Existing contracts

当前系统已经承诺了什么？

例如：

```text
submit_job() response shape
job ordering
SQLite schema v1
v1 worker claim response
v1 finish payload
```

## 3.3 Assumptions

Issue 假设了什么，但没有证明？

例如：

```text
lease expiry means old worker definitely stopped
requeue means old attempt cannot still produce effects
old finish payload remains sufficient after multiple attempts
schema expansion automatically means old binary rollback safe
```

## 3.4 Contradictions / authority gaps

哪些要求不能同时成立，或者需要产品/系统 authority 做新决定？

Capstone 最重要的例子是：

```text
arbitrary shell command
+
worker can crash after external effect but before TaskForge learns completion
+
automatic retry
```

此时 TaskForge 无法仅凭自己的 DB 分辨：

```text
attempt A:
  external effect did not happen
```

还是：

```text
attempt A:
  external effect happened
  response/completion record lost
```

因此：

```text
lease + retry
```

本身不能推出：

```text
arbitrary external effect exactly once
```

这不是“实现难一点”。

这是 guarantee 本身需要被重新定义。

---

# 4. Capstone 的第一条评分原则：先拒绝错误问题

软件工程能力不只是：

```text
给定 spec
→ 实现 spec
```

还包括：

```text
发现 spec 自己不一致
→ 明确指出 impossibility / ambiguity
→ 让正确 authority 做 decision
→ 再实现
```

如果你看到原 issue 后直接让 Agent：

```text
implement lease_expires_at + sweeper
```

即使它写出 500 行漂亮代码、tests 全绿，你仍然可能在错误问题上高效前进。

这也是 M12 的继续：

```text
Agent implementation authority
!=
product guarantee authority
```

---

# 5. System Model：至少恢复五个 view

Capstone 不接受一张“系统架构图”代替 system model。

你至少需要五个 view。

---

## 5.1 Responsibility / knowledge view

回答：

```text
API 知道什么？
service 知道什么？
DB 知道什么？
worker protocol 知道什么？
maintenance 知道什么？
external command/effect owner 知道什么？
```

尤其要找：

```text
谁知道 current attempt？
谁知道 external effect 是否真正发生？
```

这两个答案通常不是同一个组件。

---

## 5.2 Authority / state view

至少画出：

```text
Job lifecycle authority
Current attempt authority
Worker identity
Lease expiry
Recovery policy
External effect authority
```

然后问：

```text
同一语义是否出现多个 writer？
```

---

## 5.3 Runtime protocol view

画：

```text
submit
  ↓
queued
  ↓ claim
running
  ↓ finish
terminal
```

再加：

```text
lease expiry
heartbeat
requeue
new claim
stale finish
```

如果你的图里没有 stale attempt 返回这一条路径，说明你画的是 happy path，而不是 failure model。

---

## 5.4 Durable compatibility view

至少列：

```text
schema writer version
schema reader version
server version
worker protocol version
stored row state
```

不要只问：

```text
新代码能不能读旧 DB？
```

还要问：

```text
旧 binary 能不能读 expanded DB？
旧 binary 会不会错误解释新 attempt state？
新 server 能不能接受 old worker？
old finish 在什么 row 上仍合法？
```

---

## 5.5 Failure / rollback view

列出：

```text
server crash
worker crash
worker partition
stale heartbeat
stale finish
DB migration halfway
server rollback
worker rollback
mixed-version window
```

并写清：

```text
哪个 failure 是 safe failure？
哪个 failure 会让 semantic authority 倒退？
```

---

# 6. 先运行 baseline，而不是先改

在 capstone starter：

```bash
PYTHONPATH=src uv run --with pytest --no-project python -m pytest -q
```

baseline 是：

```text
6 passed
```

然后运行：

```bash
PYTHONPATH=src uv run --with pytest --no-project \
  python tools/capstone_baseline_probe.py
```

它会稳定暴露两件 tests 没覆盖的事。

第一：

```text
worker A → claim success job-1
worker B → claim success job-1
```

最终 row 只会记录一个 worker。

因此：

```text
final state looks singular
```

并不代表：

```text
history had one successful claim
```

第二：

```text
worker A claim
operator requeue
worker B claim
worker A old finish(job_id, exit_code)
```

旧 finish 会成功。

于是：

```text
row says worker B
status says succeeded
```

但这个 succeeded 实际由 A 的 stale completion 写入。

这就是 M01、M03、M07、M10 在同一个例子中的交汇。

---

# 7. 为什么 attempt identity 是 semantic object

很容易把 migration 设计成：

```sql
ALTER TABLE jobs ADD COLUMN lease_expires_at REAL;
```

然后认为已经“支持 lease”。

但真正的问题不是缺一列时间。

而是：

> **同一个 logical job 可以存在多个 execution attempt；哪个 attempt 当前仍有权改变 Job 的 lifecycle？**

因此系统需要表达：

```text
job-7 / attempt 1
job-7 / attempt 2
```

并且：

```text
attempt 1 stale finish
```

不能作用到：

```text
current attempt 2
```

所以 `attempt` 是：

```text
execution authority / fencing identity
```

而不只是计数器。

---

# 8. Lease 的真正 contract

一个比较准确的 lease contract 是：

```text
在 lease 有效期间，当前 attempt 被系统视为 current execution authority。

lease 超时后，系统可以撤销该 attempt 的 current authority，并在满足 recovery policy 时允许一个新 attempt 接管。

旧 attempt 之后到达的 heartbeat / completion 必须被拒绝。
```

注意它没有说：

```text
old process 已经停止执行
```

也没有说：

```text
old attempt 没有产生过 external effect
```

这是整个 Capstone 最重要的 boundary distinction。

---

# 9. State fencing 和 External Effect Exactly-Once

假设：

```text
attempt 1
  ↓
charge card succeeds
  ↓
network partition
  ↓
lease expires
  ↓
TaskForge requeues
  ↓
attempt 2
  ↓
charge card succeeds again
```

即使：

```text
attempt 1 final finish is correctly rejected
```

外部世界仍可能已经：

```text
charged twice
```

因此必须区分：

```text
TaskForge lifecycle state fencing
```

和：

```text
external effect dedup / fencing
```

如果 effect owner 支持：

```text
idempotency key = logical job id
```

或：

```text
fencing token = attempt
```

那么可以设计更强 guarantee。

但 TaskForge 运行 arbitrary shell command 时，它通常并不拥有这些 external systems 的 dedup semantics。

所以：

```text
exactly once arbitrary command
```

必须被 challenge。

---

# 10. Staged Reveal：先 review，后看 authority decision

M13 故意提供：

[`../labs/taskforge/capstone-starter/decision-pack/01-after-issue-review.md`](../labs/taskforge/capstone-starter/decision-pack/01-after-issue-review.md)

但你不应一开始就读。

流程是：

```text
原 issue
  ↓
独立 issue review
  ↓
提交 unresolved decisions
  ↓
再读 human decision
  ↓
比较：
    你发现了哪些？
    漏了哪些？
    哪些你误以为 Agent 可以自己决定？
```

这是为了避免把“识别 ambiguity”变成照答案填空。

---

# 11. Human Decision 修正后的目标

Authority decision 把原需求改成：

```text
legacy submit
  → manual recovery by default

new v2 submit
  → may opt into automatic_at_least_once

new worker protocol
  → attempt identity
  → fenced heartbeat/finish

v1 worker protocol
  → migration window compatibility

claim race
  → must be fixed before mixed rollout

automatic requeue
  → disabled until migration gate opens
```

并明确：

```text
exactly-once arbitrary command
```

不再是 TaskForge guarantee。

---

# 12. Migration 不是“跑一个 ALTER TABLE”

本题至少需要四个阶段。

---

## Phase A — Expand

目标：

```text
new schema can exist
old binary still works
```

典型 additive columns：

```text
attempt DEFAULT 0
lease_expires_at nullable
recovery_policy DEFAULT manual
```

关键 evidence：

```text
frozen v1 binary
→ expanded DB
→ can read/write legacy rows
```

注意：

```text
new schema exists
```

不等于：

```text
new semantics activated
```

---

## Phase B — Protocol migration

部署 dual-protocol server：

```text
v1 worker
  claim v1
  finish v1

v2 worker
  claim with attempt
  heartbeat attempt
  finish attempt
```

此时 automatic requeue 仍关闭。

理由是：

```text
migration compatibility
```

和：

```text
recovery semantics activation
```

应该分开。

---

## Phase C — Activation gate

不要写：

```text
“等旧 worker 差不多都升级了”
```

而要有可测条件，例如：

```text
legacy worker count = 0
running legacy attempt count = 0
stale-attempt tests/evidence pass
rollback semantics reviewed
```

这些属于 M11 的 production evidence。

---

## Phase D — Later Contract

本 Capstone 不要求删除 v1 protocol。

如果以后要删除：

```text
remove old endpoint
remove attempt=0 compatibility
remove old metrics
```

应该是另一个 change。

---

# 13. Rollback 是一个 state question

最常见的错误说法：

```text
“新 release 有问题就把旧 binary 部署回来。”
```

但 binary 只是一部分。

需要问：

```text
旧 binary 是否理解当前 DB state？
旧 binary 是否理解新 protocol-written rows？
旧 binary 是否会重新接受 stale transition？
```

Capstone reference 的一个 actual experiment 是：

```text
Expand-only DB
→ frozen v1 binary still works
```

所以这一阶段 binary rollback 可以是合理目标。

但：

```text
v2 attempt 已经 active
→ frozen v1 server receives old finish payload
→ accepts it without attempt fencing
```

因此 activation 之后：

```text
old binary rollback
```

可能让 semantic guarantees 倒退。

这叫：

> **rollback boundary / point of no safe old-binary return**

它不是失败。

真正失败的是没有识别这个边界却承诺“随时 rollback”。

---

# 14. Fix Existing Race Before Adding Recovery

原系统已经有：

```text
SELECT queued candidate
...
UPDATE running
```

两个 worker 可以：

```text
A SELECT job-1
B SELECT job-1
A UPDATE
B UPDATE
A returns success
B returns success
```

如果在这个基础上直接增加 lease：

```text
lease protocol
```

只会把旧 race 带进新系统。

因此 staged plan 中一个合理的早期 change 是：

```text
fix v1 claim atomicity
preserve v1 response contract
```

实现可以是：

```text
transaction
conditional update / CAS
other equivalent atomic decision
```

课程不要求特定 primitive。

要求的是：

```text
one queued job
+
two concurrent claim calls
→ at most one success receipt
```

---

# 15. Change Topology：不要提交一个“万能 PR”

一个不良 capstone patch 会同时做：

```text
schema migration
claim race fix
new protocol
lease implementation
sweeper activation
old API cleanup
metrics redesign
refactor DB layer
remove legacy worker support
```

即使最终 tests 全绿，也很难回答：

```text
哪一步改变了哪条 contract？
哪里可以 rollback？
哪个 failure 属于哪个 phase？
```

一个更好的 change topology 可能是：

```text
C1 characterization + deterministic race evidence
C2 v1 claim atomicity fix
C3 additive schema expand
C4 dual worker protocol + attempt fencing
C5 new opt-in submission contract
C6 migration observability / activation gate
C7 automatic recovery enablement
C8 later legacy contract removal (out of current scope)
```

不要求 commit 数完全相同。

但每一步应有：

```text
bounded claim
bounded evidence
clear rollback/reversal semantics
```

---

# 16. Design Memo 必须回答什么

Capstone design memo 不是 architecture prose。

必须至少回答：

## 16.1 Current model

```text
what is true now?
```

## 16.2 Desired contract

```text
what becomes newly true?
```

## 16.3 Preserved contract

```text
what must remain true?
```

## 16.4 Explicit non-guarantees

例如：

```text
TaskForge does not guarantee arbitrary external command exactly-once
```

## 16.5 Authority

```text
who owns current attempt?
who owns external effect dedup?
who can activate recovery?
```

## 16.6 State machine

至少：

```text
queued
running(attempt=n)
expired/requeued
running(attempt=n+1)
terminal
```

## 16.7 Compatibility matrix

至少包含：

```text
old/new server
old/new worker
schema v1/v2
manual/automatic job
```

## 16.8 Rollout gates

不是时间：

```text
Tuesday 10am enable recovery
```

而是 conditions：

```text
legacy_worker_count == 0
```

## 16.9 Residual risk

哪些风险没有被解决？

---

# 17. Agent 在 Capstone 中的正确位置

你应该使用 Agent。

但不是：

```text
“这是 issue，全部做完。”
```

更合理的角色分工：

---

## Agent A — Reconnaissance

只读：

```text
map DB access
map protocol entry points
map lifecycle writes
map tests
map compatibility artifacts
```

输出 evidence，不改代码。

---

## Agent B — Compatibility / migration audit

只读：

```text
old reader/writer assumptions
schema expansion risks
worker protocol version surfaces
rollback hazards
```

---

## Agent C — Test/evidence audit

只读：

```text
what existing tests actually claim
what race is untested
what frozen artifacts exist
what negative controls are missing
```

这些任务天然更适合并行。

---

## Implementation Agent

等 human design memo / decisions 完成后再获得：

```text
allowed files
stage goal
invariants
forbidden actions
evidence contract
stop conditions
```

---

## Independent Reviewer

至少独立重建：

```text
current model
change claim
migration state
failure history
rollback boundary
```

不要只读 implementation Agent 的总结。

---

# 18. Agent 必须被允许“正确停止”

在 Capstone 中，以下都可能是正确结果：

```text
STOP_AND_ESCALATE
```

例如发现：

```text
new API response shape 未授权
migration gate ownership 未授权
external effect exactly-once 无法满足
old worker inventory 不可观测
```

如果你的 delegation contract 没有 stop/escalation 条件，Agent 很容易为了“完成任务”自行发明答案。

---

# 19. Evidence Matrix

最终不能只写：

```text
all tests passed
```

至少做一张 evidence matrix：

| Claim | Evidence | Negative control / counterexample | Remaining uncertainty |
|---|---|---|---|
| v1 API unchanged | old-client characterization | changed response would fail | unknown external clients? |
| one job one successful claim | deterministic barrier race test | baseline reproduces 2 success | SQLite deployment assumptions |
| v1 binary works after expand | frozen binary against expanded DB | destructive migration would fail | platform SQLite differences |
| stale v2 finish rejected | attempt1→expiry→attempt2→finish1 | baseline old finish succeeds | malicious DB writer |
| manual jobs not auto-requeued | expired manual job test | automatic job requeues | product policy correctness |
| recovery activation gated | gate state tests + production counters | legacy workers present closes gate | inventory freshness |
| exactly-once not claimed | duplicate-effect negative control | two effects despite state fence | effect-specific idempotency |

重点不是表格格式。

而是：

> **每条重要 claim 都应该知道自己凭什么相信，以及什么没有被证明。**

---

# 20. Test Suite 的边界

Capstone 应该包含：

### Contract tests

```text
legacy public API
v1 worker response
v2 attempt response
recovery policy
```

### Concurrency tests

```text
double claim
finish vs expiry
stale finish
stale heartbeat
```

### Migration tests

```text
v1 DB → v2 expand
old binary → expanded DB
new binary → old data
```

### Negative controls

```text
old baseline race really fails
external duplicate remains possible
old binary after activation really is unsafe
```

### Production-style gates

```text
legacy worker count
legacy running attempts
activation state
```

不要为了 coverage 数字增加无意义 tests。

---

# 21. Frozen Binary 是很强的 Compatibility Evidence

只在同一份 source 中写：

```text
if version == 1: ...
if version == 2: ...
```

并不能证明真正 old binary 可运行。

更强的测试是：

```text
copy old code
→ create/operate old DB
→ new code expand schema
→ run actual old code against expanded DB
```

这样你检查的不是：

```text
“我觉得 old code 会兼容”
```

而是：

```text
“old code actually ran”
```

M08 的 migration reasoning 到这里变成真正可执行 evidence。

---

# 22. Production Evidence 不是上线后“看一下日志”

Activation 必须预先定义：

```text
what signals
what thresholds/conditions
who owns decision
what action follows
```

Capstone 至少需要：

```text
legacy_worker_count
running_legacy_attempt_count
v2_claim_count
stale_finish_rejected_count
lease_expiry_requeue_count
manual_job_requeue_count (should remain 0)
```

如果 external effect 有 idempotency support，还应观察：

```text
dedup conflict / duplicate suppression
```

不要把：

```text
CPU
memory
```

当成本 change 的主要 correctness signal，除非它们真的映射到用户/系统 guarantee。

---

# 23. Review：作者不能决定自己的 guarantee 已被证明

Independent review 至少检查：

## Contract

```text
有没有偷偷恢复 exactly-once wording？
legacy API 是否改变？
manual recovery 默认是否保持？
```

## Authority

```text
current attempt 是否只有一个 semantic owner？
旧 finish 是否能越过 fencing？
```

## Concurrency

```text
claim linearization point 在哪？
expiry 与 finish 同时发生怎么办？
```

## Migration

```text
expand 是否真的 additive？
old binary 是否 actual tested？
activation gate 是否可观测？
```

## Rollback

```text
哪个 phase 可以 old-binary rollback？
哪个 phase 以后只能 roll-forward？
```

## Evidence

```text
哪些 test 是 implementation-shaped oracle？
有没有 fail-before？
有没有 negative control？
```

## Scope

```text
有没有顺手重写数据库层？
有没有引入不必要 infrastructure？
有没有删 legacy protocol 超出当前 contract phase？
```

---

# 24. “正确实现”不等于 Instructor Reference

Instructor reference 会展示一条可行 path。

它可能选择：

```text
conditional update / CAS
attempt counter
nullable lease expiry
manual default recovery policy
new v2 worker functions
activation gate
```

但你完全可以选择：

```text
BEGIN IMMEDIATE transaction
separate attempts table
lease record table
other equivalent schema
```

只要你能证明：

```text
contract
compatibility
concurrency
migration
rollback
production evidence
```

成立。

课程不按“和参考答案类结构”评分。

---

# 25. Capstone 的真正输出是 Change Record

最终 submission 不应只是一份 repository diff。

更完整的工程产物是：

```text
1. Issue Review
2. System Model
3. Design Memo / ADR
4. Compatibility Matrix
5. Staged Implementation Plan
6. Agent Delegation Records
7. Code Changes
8. Executable Evidence
9. Independent Review
10. Rollout / Rollback Plan
11. Production Evidence Plan
12. Retrospective
```

这整个 bundle 才回答：

> **为什么这个 change 应该被接受？**

---

# 26. Retrospective：判断到底发生在哪里

最后必须重新看整个过程。

列三栏。

## Human-only / human-authority decisions

例如：

```text
reject arbitrary exactly-once promise
choose recovery semantic
approve compatibility break / rollout point
accept residual risk
merge / activation decision
```

## Good Agent delegation

例如：

```text
repo reconnaissance
call graph / state writer search
migration matrix generation
focused implementation
race-test scaffolding
mechanical schema edits
regression execution
```

## Agent work that required correction

例如：

```text
assumed lease means process stopped
changed API shape without authority
used test sleep instead of deterministic interleaving
claimed rollback safety from schema shape only
```

目标不是证明：

```text
“人比 Agent 聪明”
```

而是识别：

```text
哪些 knowledge / authority / verification 应该放在哪一层
```

---

# 27. Capstone 评分标准

M13 占课程总评 30%。

本章内部建议评分：

## 20% — Mental Model

- data/control flow 是否准确；
- authority 是否准确；
- failure history 是否覆盖 stale attempt；
- external effect boundary 是否识别。

## 15% — Contract / Issue Review

- 是否识别 guarantee contradiction；
- 是否区分 required / assumption / unresolved decision；
- 是否明确 non-guarantee。

## 15% — Change Localization

- 是否分 staged change；
- 是否避免 unrelated cleanup；
- race fix / migration / activation 是否能独立 reasoning。

## 15% — Migration / Rollback

- 是否有 version matrix；
- 是否验证 frozen old behavior；
- 是否识别 rollback boundary；
- activation gate 是否可观测。

## 15% — Evidence

- deterministic concurrency evidence；
- fail-before / pass-after；
- compatibility evidence；
- negative controls；
- residual uncertainty。

## 10% — Independent Review

- reviewer 是否独立重建 change；
- findings 是否按 root cause；
- 是否检查 migration / production，不只看代码。

## 10% — Agent Orchestration

- delegation contract 是否明确；
- Agent 是否减少 mechanical work；
- 是否允许正确 escalation；
- human authority 是否被保留。

---

# 28. 常见失败方式

## 28.1 “直接照 issue 实现”

问题：

```text
错误 guarantee 未被 challenge
```

## 28.2 “上 Kafka 就解决”

问题：

```text
新增 infrastructure 没有解决 external effect exactly-once
```

## 28.3 “lease token = exactly-once token”

问题：

```text
混淆 internal state fencing 与 external effect authority
```

## 28.4 “测试都绿”

问题：

```text
baseline 本来就 6/6 green
```

## 28.5 “旧 worker 能解析 response，所以兼容”

问题：

```text
protocol syntax compatible
!=
protocol semantics compatible
```

## 28.6 “ALTER TABLE 是 additive，所以 rollback safe”

问题：

```text
schema compatibility
!=
semantic state compatibility
```

## 28.7 “让一个 Agent 全程做完”

问题：

```text
implementation narrative 成为 acceptance narrative
```

## 28.8 “为了安全永远不自动 recovery”

这也可能失败。

因为 human decision 已经允许：

```text
automatic_at_least_once opt-in
```

你仍需要实现目标，而不是用“保守”逃避需求。

---

# 29. 从 M00 到 M13

现在可以重新看整门课。

```text
M00
为什么 change 会放大 complexity？

M01
什么叫正确？谁负责什么？

M02
知识和 state authority 应该放在哪？

M03
凭什么相信 change？

M04
boundary 如何表达 error / retry / intent？

M05
如何改变结构但控制行为变化？

M06
证据不足时怎样先获得 feedback？

M07
并发 / crash / retry 如何击穿直觉？

M08
新旧世界如何安全共存？

M09
哪些 boundary 的后果值得上升到 architecture？

M10
一个 change 为什么应该被 merge？

M11
上线后凭什么知道 contract 正在满足？

M12
怎样让 Agent 执行工程工作而不接管 engineering authority？

M13
这些判断能否同时应用在一次真实风格 change 中？
```

---

# 30. 最终定义

课程最初给出的工作定义是：

> **Software Engineering 是建立、表达和维护软件中的 boundaries、contracts、invariants 与 mental models，从而让复杂系统可以被人或 Agent 安全地持续修改。**

Capstone 的意义就是测试这句话是不是已经从 slogan 变成了你的工作方式。

当你看到一个 issue 时，你不再只问：

```text
我要改哪几行？
```

而会自然问：

```text
系统现在到底是什么？

这个需求真正改变哪个 contract？

谁拥有相关 state / decision？

哪个 failure history 会让直觉失效？

新旧版本如何共存？

我需要什么 evidence？

Agent 可以做哪些 mechanical / exploratory work？

它应该在哪里停止并升级给人？

reviewer 如何独立否证我的 claim？

上线以后怎样知道它真的成立？
```

如果这些问题已经成为习惯，M13 就完成了它真正的目标。
