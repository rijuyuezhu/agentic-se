# M13 Instructor Analysis — TaskForge Lease Recovery Capstone

> 这是 instructor reference，不是学生第一次接触 Capstone 时应该先看的答案。
>
> 建议完成 issue review、system model、design memo、implementation 与 independent review 后再读。

---

# 1. Reference 结论先说清楚

原始 `ISSUE.md` **不能按字面直接实现**。

最重要的 blocker 不是 SQLite 语法，也不是 lease timer。

而是这组要求彼此冲突：

```text
arbitrary shell command
+
automatic timeout retry
+
legacy finish has no attempt identity
+
exactly-once external execution
+
old worker mixed rollout
+
old server can be rolled back at any time
```

Instructor reference 的第一判断是：

```text
NEEDS AUTHORITY DECISION
```

而不是：

```text
READY TO IMPLEMENT
```

---

# 2. Baseline Actual Evidence

Starter baseline 实际运行：

```text
...... [100%]
6 passed
```

这六个 tests 覆盖：

- schema v1；
- legacy submit response；
- single-worker FIFO claim；
- legacy finish；
- maintenance stale scan；
- queued cancellation。

它们不是“坏 tests”。

但它们没有提出：

```text
两个 worker 同时 claim 会怎样？
requeue 后 old completion 会怎样？
```

所以 full green 完全允许关键 lifecycle protocol 已经错误。

---

# 3. Deterministic Double-Claim Baseline

`capstone_baseline_probe.py` 使用 barrier 强制：

```text
worker A SELECT job-1
worker B SELECT job-1
```

然后两边才进入 UPDATE。

Actual output：

```text
[KNOWN REMOTE CLAIM RACE]
successful_claims=job-1,job-1
workers_returned_success=2
final_worker_id=worker-b
history_is_illegal=true
```

这个例子再次提醒：

```text
final_worker_id = worker-b
```

只描述 final state。

它没有描述：

```text
A 和 B 都收到 claim success receipt
```

因此 reviewer 不能只检查 row 最后是不是只有一个 owner。

---

# 4. Historical Completion Quirk

Baseline v1 finish payload：

```json
{
  "job_id": "job-1",
  "exit_code": 0
}
```

没有：

```text
worker_id
attempt
lease token
```

Probe 实际执行：

```text
A claim job-1
operator requeue job-1
B claim job-1
A sends old finish(job-1, 0)
```

Actual：

```text
stale_finish_accepted=true
final_status=succeeded
final_worker_id=worker-b
```

这里 row 甚至形成了一个很迷惑的组合：

```text
worker_id = worker-b
status = succeeded
```

但 `succeeded` 是 A 的 stale completion 写进去的。

因此原 issue 提议：

```text
“保持 finish_job() 不变，然后 sweeper 自动 requeue”
```

是 blocker。

---

# 5. 为什么 exactly-once 是错误 guarantee

即使把 stale finish 完全修掉，仍然不能推出 arbitrary command exactly-once。

Reference negative control：

```text
attempt 1 claims charge-card
attempt 1 performs external charge
lease expires
system requeues
attempt 2 claims same logical job
attempt 2 performs external charge
```

此时 TaskForge 可以正确做到：

```text
attempt 1 late finish → reject
```

但 effects 已经是：

```text
[charge-card, charge-card]
```

所以 reference 明确区分：

```text
state transition exactly-one-current-attempt
```

与：

```text
external effect exactly-once
```

后者需要 external effect owner 参与：

```text
idempotency key
fencing token
transactional integration
```

或把 retry 限制在明确 retry-safe 的 workload。

TaskForge 的 arbitrary shell command boundary 本身没有这些 knowledge。

---

# 6. Human Decision 的关键修改

Reference 接受 `decision-pack/01-after-issue-review.md` 作为 product/system authority。

最终 contract：

```text
legacy submit
→ recovery_policy=manual

new v2 submit
→ caller may opt into automatic_at_least_once

new worker protocol
→ attempt identity

current attempt only
→ may heartbeat / finish

old worker protocol
→ supported during migration

old finish
→ may finish legacy attempt only

automatic requeue
→ disabled until migration gate opens
```

并删除原 guarantee：

```text
arbitrary command exactly-once
```

---

# 7. Reference Schema Design

Reference 没有创建新 service / broker。

仍然使用一个 SQLite jobs table。

Expand 增加：

```text
attempt INTEGER NOT NULL DEFAULT 0
lease_expires_at REAL NULL
recovery_policy TEXT NOT NULL DEFAULT 'manual'
```

这里三个 default 都有 migration 含义。

## attempt = 0

表示 legacy protocol attempt。

不是“第 0 次重试”的业务概念。

它是 migration sentinel。

## lease_expires_at = NULL

legacy/manual row 不需要自动 recovery lease。

## recovery_policy = manual

这是最关键的 compatibility default。

旧 submit binary 不知道新 column，但它写出的 row 自动得到：

```text
manual
```

因此 expand 没有偷偷把 legacy job 变成自动 retry job。

---

# 8. Starter 初始化器里的一个重要细节

Instructor 在构造 Capstone 时专门把：

```python
PRAGMA user_version = 1
```

从“每次 initialize 都写”改成：

```text
只在 current version == 0 时初始化为 1
```

否则 frozen old binary 在 expanded DB 上启动时会把：

```text
user_version=2
```

错误写回：

```text
1
```

那会让“old binary compatible with expanded schema”测试被一个无关版本标记 bug 污染。

这个 starter choice 本身体现：

> compatibility fixture 必须允许真实 old binary 被重放，而不是为了教学故意制造无关 blocker。

---

# 9. Reference v1 Claim Fix

原算法：

```text
SELECT candidate
UPDATE candidate
return success
```

Reference 使用 conditional update / compare-and-set：

```text
SELECT first queued row
↓
UPDATE ...
WHERE id = candidate
  AND status = 'queued'
↓
rowcount == 1 ? success : retry
```

关键 contract：

```text
one queued job
+ N concurrent claim calls
→ at most one successful receipt for that row
```

它没有改变 v1 response：

```json
{
  "job_id": "job-1",
  "command": "one"
}
```

所以 race fix 可以在 protocol migration 之前独立部署。

Reference 并不声称 CAS 一定优于：

```text
BEGIN IMMEDIATE
single transaction
```

后者也可能是完全合理的实现。

---

# 10. Reference v2 Attempt Protocol

新 claim 返回：

```text
job_id
command
worker_id
attempt
lease_expires_at
```

Claim 时：

```text
previous_attempt = n
new_attempt = n + 1
```

并用 conditional update 确保 candidate 仍是：

```text
queued
AND attempt == n
```

所以 attempt 是 monotonic fencing identity。

---

# 11. Finish / Heartbeat Fencing

Reference `finish_v2` 的 acceptance condition：

```text
public_id matches
status == running
worker_id matches
attempt matches
```

Heartbeat 同样。

这意味着：

```text
attempt 1
↓ lease expires
attempt 2 starts
↓
attempt 1 finish
```

会：

```text
rowcount = 0
→ rejected
```

而不是覆盖 current attempt。

---

# 12. Legacy Finish Handler 不能绕过 Fencing

如果 new server 继续写：

```sql
UPDATE jobs
SET status='succeeded'
WHERE public_id=? AND status='running'
```

那么 old payload：

```text
job_id + exit_code
```

仍然可以完成 attempt 2。

因此 reference dual-protocol server 在 expanded schema 下只允许 old finish：

```text
attempt == 0
```

也就是：

```text
legacy worker may finish legacy attempt
```

但不能：

```text
legacy compatibility path
→ bypass new authority model
```

---

# 13. Recovery Policy 是 Contract，不是 Scheduler Flag

Reference 没有让 sweeper 对所有 expired row 做：

```text
running → queued
```

只允许：

```text
status == running
AND recovery_policy == automatic_at_least_once
AND attempt > 0
AND lease expired
```

所以 legacy submit：

```text
manual
```

即使被 new worker claim、lease 过期，也不会自动 requeue。

这保留了旧 API 用户的执行语义。

---

# 14. Reference Activation Gate

Reference gate 输入：

```text
legacy_worker_count
running_legacy_attempt_count
rollback_reviewed
stale_attempt_evidence_passed
```

只要任一不满足：

```text
recovery activation closed
```

Actual test 中故意构造：

```text
legacy workers remain
legacy running attempts remain
rollback review missing
stale evidence missing
```

返回全部四个 blocker。

另一个 clean state：

```text
0 legacy workers
0 legacy running attempts
rollback reviewed
stale evidence passed
```

才允许 gate open。

---

# 15. 为什么 Gate 不是“多余流程”

因为 mixed protocol compatibility 和 automatic retry semantic activation 是两个不同变化。

如果 server 一支持 v2 protocol 就自动开启 requeue：

- legacy worker 可能仍在运行；
- legacy attempt 没 token；
- stale old finish 仍可能出现；
- rollback target 可能仍是 v1 server。

所以 gate 是：

```text
system-state transition authority
```

而不只是 deployment convenience。

---

# 16. Actual Reference Test Result

Instructor 在临时 solution copy 中运行：

```text
.............. [100%]
14 passed
```

构成：

```text
6 baseline tests
8 reference tests
```

8 个新增测试覆盖：

1. expand 后 legacy submit 仍保持 response，并默认 manual；
2. v1 concurrent claim race 收敛为一个 success；
3. v2 claim attempt fencing + old finish rejection；
4. expiry → attempt2 → stale finish / heartbeat rejection；
5. manual job 不自动 requeue；
6. activation gate blocker；
7. clean activation gate；
8. external duplicate negative control。

---

# 17. Frozen v1 Binary：Expand-only Actual Evidence

Instructor 没有用 new code 的 `legacy=True` mode 冒充 old binary。

而是实际复制了一份 starter：

```text
frozen/
solution/
```

先用 frozen code：

```text
create v1 DB
submit job-1
```

再用 solution：

```text
expand schema → user_version=2
```

然后重新运行 frozen v1 code：

```text
initialize expanded DB
submit job-2
claim job-1
finish job-1
```

Actual：

```text
frozen_before_expand=ok
expanded_version=2
frozen_after_expand=ok schema_version=2
```

这证明至少对于 reference 的 explicit-column queries / default-safe added columns：

```text
Expand-only old-binary compatibility
```

真实成立。

---

# 18. Rollback Boundary Actual Counterexample

然后 instructor 构造另一个 DB：

```text
solution expands schema
new API submits automatic job
v2 worker claims attempt=1
```

此时换回真正 frozen v1 server code。

发送：

```json
{
  "job_id": "job-1",
  "exit_code": 0
}
```

Actual：

```text
v2_attempt_active=1
frozen_server_accepts_unfenced_finish=True
```

所以原 issue：

```text
“allow us to roll the server binary backward at any point”
```

被实际 runtime counterexample 否定。

这比写：

```text
“rollback 可能有风险”
```

强得多。

---

# 19. Reference Rollout Topology

Instructor 会建议：

## C0 — Characterize

- freeze API/protocol fixtures；
- deterministic race probe；
- stale completion probe。

## C1 — Fix v1 claim atomicity

- response unchanged；
- no schema dependency；
- independent deploy possible。

## C2 — Expand schema

- additive columns；
- recovery inactive；
- frozen v1 binary evidence。

## C3 — Dual worker protocol

- v1 handler；
- v2 attempt claim/heartbeat/finish；
- legacy finish attempt=0 only；
- recovery still inactive。

## C4 — New opt-in submit

- legacy submit manual unchanged；
- new surface explicit automatic_at_least_once。

## C5 — Observability / Gate

- legacy worker inventory；
- running legacy attempts；
- stale rejection counters；
- rollback decision state。

## C6 — Activate automatic recovery

- gate required；
- only opt-in automatic jobs requeue。

## Later C7 — Contract old protocol

Out of current Capstone scope。

---

# 20. Why Not One Transaction Around Everything?

一个学生可能提出：

```text
把 claim / execute / finish 全放 SQLite transaction
```

这无法覆盖 arbitrary external command execution。

SQLite transaction 不能把：

```text
charge card
send email
write remote object
```

自动包含进自己的 atomic commit。

所以这不是 exactly-once 解法。

它可能反而产生：

- 超长 transaction；
- DB lock；
- crash ambiguity；
- external side effect already committed but DB rollback。

Reference review 会要求明确 external transaction boundary。

---

# 21. Why Not Just Add a Message Broker?

Broker 可能改善：

```text
queue durability
consumer coordination
redelivery
```

但仍然不会凭空解决：

```text
consumer external effect succeeded
but ack lost
```

因此“换 Kafka/RabbitMQ”不是 original exactly-once contradiction 的直接解答。

而且它会大幅扩大：

```text
architecture
operations
migration
failure domain
```

所以 reference 在当前 requirement 下不批准这个 scope expansion。

---

# 22. Why Not Disable Retry Forever?

另一个极端是：

```text
既然 exactly-once 做不到
→ 永远不 automatic retry
```

这也没有满足经过 human decision 后的需求。

Authority 已经允许：

```text
automatic_at_least_once opt-in
```

所以工程师必须在诚实 guarantee 下仍然实现 recovery，而不是用保守当借口取消需求。

---

# 23. Compatibility Matrix — Reference Judgment

一个简化 reference matrix：

| Server | Worker | Schema | Recovery | Judgment |
|---|---|---|---|---|
| v1 | v1 | v1 | off | baseline |
| v1 | v1 | v2-expanded | off | expected compatible during Expand |
| v2 | v1 | v2 | off | compatible migration path |
| v2 | v2 | v2 | off | attempt protocol usable |
| v2 | mixed | v2 | off | migration window |
| v2 | v2 only | v2 | on | allowed after gate |
| v1 rollback | v2 attempt active | v2 | any | unsafe semantic downgrade |

关键不是表格本身。

而是最后一行不能因为 schema readable 就写成 PASS。

---

# 24. Production Signals — Reference

至少建议：

```text
workers{protocol=v1|v2}
running_attempts{protocol=v1|v2}
claim_success_total{protocol=v1|v2}
stale_finish_rejected_total
stale_heartbeat_rejected_total
lease_requeue_total{recovery_policy=...}
recovery_gate_open
```

Diagnostic event 可以带：

```text
job_id
attempt
worker_id
```

但不要把：

```text
job_id
```

做 aggregate metric label。

---

# 25. Reviewer 应该抓什么

如果看到 PR：

```text
ALTER TABLE ADD lease_expires_at
sweeper updates running→queued
finish unchanged
```

应该直接 blocker：

> stale v1 completion has no attempt identity and can complete the current row after requeue/reclaim; this violates the new current-attempt authority model.

如果看到：

```text
attempt fencing implemented
README says exactly-once guaranteed
```

也应该 blocker：

> tests only prove TaskForge state fencing. They do not prove external effect exactly-once; the duplicate-effect negative control demonstrates two external effects remain possible.

如果看到：

```text
migration is additive, therefore rollback safe
```

也应 blocker：

> frozen old server accepts unfenced completion after v2 attempt activation; schema readability is insufficient to establish semantic rollback safety.

---

# 26. Reviewer 不应该抓什么

不要把以下当 blocker：

```text
“为什么不用 separate attempts table？”
“我个人更喜欢 BEGIN IMMEDIATE。”
“lease module 应该叫 scheduler.py。”
“应该上 Postgres。”
```

除非能连到具体：

```text
contract
invariant
migration
failure
maintainability consequence
```

否则只是 alternative preference。

---

# 27. Agent Orchestration — Instructor Expectation

优秀 submission 通常不会让一个 Agent 从 issue 一口气跑到 deploy plan。

更好的过程：

```text
Agent A: read-only current-state map
Agent B: compatibility matrix / old binary surfaces
Agent C: tests + race evidence audit
Human: issue/guarantee decision
Agent D: bounded stage implementation
Agent E: independent review
Human: acceptance / rollout authority
```

重点不是 Agent 数量。

如果一个 Agent 能在上下文足够完整时完成多个阶段，也可以。

评分看：

```text
role separation / authority / evidence
```

不是：

```text
multi-agent count
```

---

# 28. 一个优秀 STOP_AND_ESCALATE 示例

如果 implementation Agent 在读原 issue 时输出：

```text
I can implement lease expiry, but I cannot establish the requested
exactly-once guarantee for arbitrary commands from the current protocol.
The existing finish message has no attempt identity, and TaskForge does
not own external-effect deduplication. I need a product/system decision
on retry semantics before implementing automatic requeue.
```

这不是失败。

这是非常高质量的结果。

---

# 29. 一个差的“高自主性”结果

例如 Agent：

```text
- adds lease column
- auto-requeues everything
- updates README to say exactly-once
- changes old API to add attempt token
- removes old worker support
- upgrades SQLite abstraction
- adds retry daemon
- all tests pass
```

代码可能很多。

但几乎每一步都越过了未授权 boundary。

这正是 M12/M13 要防的：

```text
high implementation throughput
+
low engineering control
```

---

# 30. Capstone 的 High-Information Evidence

Instructor 最看重以下几条：

1. **Baseline double-claim fail-before**
2. **Post-fix one-success history**
3. **Frozen old binary on expanded DB**
4. **Attempt1 expiry → attempt2 → stale finish rejected**
5. **Stale heartbeat rejected**
6. **Legacy finish works only on legacy attempt**
7. **Manual jobs not auto-requeued**
8. **Activation gate closes on observable blockers**
9. **External duplicate negative control**
10. **Old binary after activation accepts unfenced finish**

这十条比：

```text
95% coverage
```

更能描述这次 change 的风险。

---

# 31. What the Reference Did Not Solve

Reference 仍然没有：

```text
real distributed clock uncertainty model
worker authentication
lease clock skew policy
DB corruption recovery
multiple server processes contending under heavy load
production worker inventory implementation
external effect idempotency
operator UI
schema downgrade tooling
v1 protocol removal
```

这些不是遗漏到可以假装不存在。

应该写入 residual risk / scope。

Capstone 的目标不是把 TaskForge 做成生产级 scheduler。

而是证明：

```text
你知道这次 change 到底证明了什么
也知道它没有证明什么
```

---

# 32. Grading Notes

## Mental model 低分表现

- 把 worker 当 lifecycle authority；
- 没有 attempt 概念；
- 把 final row 当 history；
- 把 external effect 放进 SQLite guarantee。

## Contract reasoning 低分

- 原 issue 原样接受；
- 用“best effort exactly once”模糊表达；
- 不写 non-guarantee。

## Migration 低分

- 只有 schema migration；
- 没 mixed version；
- 没 actual old binary；
- “随时 rollback”无 evidence。

## Evidence 低分

- race test 依赖 sleep；
- 只有 happy path；
- 没 negative control；
- tests 只 mirror implementation。

## Review 低分

- summary = “code clean, tests pass”；
- 没 challenge guarantee；
- 没 migration / rollback review。

## Agent orchestration 低分

- Agent 自己改 spec；
- Agent 自己决定 merge/deploy；
- 只给 vague prompt；
- 不允许 escalation。

---

# 33. Reference 最终 Acceptance Statement

一个接近 instructor 标准的一页结论应该像：

```text
The original issue is not mergeable as written because lease retry cannot
provide exactly-once execution for arbitrary external commands and the v1
completion protocol cannot distinguish stale attempts.

After the human contract revision, the proposed staged change is acceptable:
- v1 claim is made single-winner without changing its response;
- schema expansion is additive and was exercised with a frozen v1 binary;
- v2 attempts fence stale heartbeat/finish;
- legacy jobs remain manual recovery;
- automatic at-least-once recovery is opt-in and gated until legacy workers
  and legacy running attempts are absent;
- post-activation rollback to the v1 server is explicitly not promised;
- external effect exactly-once remains outside TaskForge's guarantee.

Reference tests: 14 passed.
Critical negative controls also pass: duplicate external effect remains
possible, and a frozen v1 server is demonstrably unsafe after v2 attempt
activation. Therefore rollout should proceed only through the staged gate,
not as the original one-step server-first deployment.
```

注意这里：

```text
negative control passes
```

并不意味着系统坏。

它意味着 acceptance statement 没有说谎。

---

# 34. 课程最后真正希望学生带走什么

不是：

```text
lease scheduler 设计模板
```

而是一个习惯：

```text
先建立真实 model
再判断 spec
再分配 authority
再设计 change path
再要求 evidence
再独立 review
最后才接受系统变化
```

Agent 可以让其中很多机械步骤快非常多。

但如果人放弃：

```text
what is true?
what should be true?
who may decide?
what would falsify our claim?
```

那么更高的代码生成速度只会提高错误系统演化的速度。

这就是 M13 对整门课的最终检验。
