# M09 Instructor Analysis — Architecture：边界、Authority 与 Failure Domain

> Spoiler：这是 instructor reference，不是唯一正确 architecture。
>
> 重点是展示如何从当前系统事实、requirements 和 consequence 推出一个 architecture direction，并验证一个最小 architecture-enabling change。

---

# 1. Baseline 先告诉了我们什么？

运行：

```bash
PYTHONPATH=src uv run --with pytest --no-project python tools/m09_architecture_probe.py
```

实际得到：

```text
[DIRECT STATE DEPENDENCIES] concurrent_claim, legacy_audit, metrics, service, worker
[LIFECYCLE MUTATORS] concurrent_claim, service, worker
[LONG-LIVED SURFACES] public_api, snapshot schema, audit output, external effect protocol
[ARCHITECTURE PRESSURE] semantic authority is not aligned with module/process boundaries
```

第一反应不应该是：

```text
grep 到 5 个 state import
→ 全部替换
```

因为这些文件不是同一种角色。

---

# 2. Source Classification

一个合理 classification：

| Module | Role |
|---|---|
| `service.py` | normal product/domain facade |
| `worker.py` | normal worker lifecycle path |
| `metrics.py` | product read/reporting path |
| `public_api.py` | external-style contract boundary |
| `snapshot.py` | long-lived durable export format |
| `legacy_audit.py` | legacy/reporting integration path |
| `effect_delivery.py` | M07 external-effect teaching model |
| `concurrent_claim.py` | M07 deterministic fault-injection/historical teaching path |

这个 classification 很重要。

`concurrent_claim.py` 的 direct state mutation 是**故意保存的 M07 evidence fixture**。

它不能和 normal production path 混为一谈。

真实仓库也经常有：

- migration scripts；
- emergency repair utilities；
- compatibility shims；
- tests/fuzz harness；
- one-off admin commands。

这些高权限代码必须被 inventory，但 architecture policy 未必和 normal runtime path 完全相同。

---

# 3. Current Responsibility View

## `service.py`

知道：

- ID allocation；
- submit；
- cancel rule；
- read/list。

## `worker.py`

知道：

- queued -> running；
- running -> succeeded/failed；
- exit-code interpretation。

## `concurrent_claim.py`

知道：

- claim transition；
- worker ownership teaching state。

结果：

```text
lifecycle protocol knowledge
```

被拆到多个模块。

这不只是 duplication。

它意味着：

> 没有一个地方能够完整回答“一个 lifecycle transition 是否合法”。

---

# 4. Current Authority View

当前 representation：

```text
state.jobs
state.next_job_number
```

但 storage location 不等于 authority。

真正的 writers：

```text
service
worker
concurrent_claim
```

因此 baseline 更准确的描述是：

```text
one shared representation
multiple semantic writers
```

这正是 remote-worker requirement 到来后必须处理的 architecture pressure。

如果直接把 `worker.py` 搬到另一台机器：

```text
worker -> shared memory
```

已经不可能。

如果改成：

```text
worker -> shared DB direct write
```

则只是把 split authority 从 memory 搬到 database。

---

# 5. Snapshot 的 reference classification

本轮把 `snapshot.py` 定义为：

```text
derived export artifact
```

而不是：

```text
live source of truth
```

为什么？

因为目前代码没有定义：

- startup restore；
- crash-consistent atomic write；
- stale snapshot detection；
- merge/reconciliation；
- multi-writer coordination。

如果现在声称 snapshot 是 recovery truth，会把一大批不存在的 guarantee 偷偷引入 architecture。

因此：

```text
Job Authority -> snapshot export
```

而不是：

```text
snapshot -> Job Authority truth
```

至少在 M09 phase 如此。

---

# 6. Remote Worker Requirements 的真正 architectural pressure

新需求真正迫使我们新增的是：

```text
process / network boundary
```

位置在：

```text
Job Authority <-> worker
```

因为：

- worker 在另一台机器；
- worker crash 要与 API process 隔离；
- worker 不应有 durable-store direct-write credential。

注意哪些东西**没有**形成独立 process requirement：

```text
metrics
audit
snapshot formatter
```

因此把它们全拆成 service 没有 requirement 支付 complexity premium。

---

# 7. Design A — Central Semantic Authority + Remote Worker Protocol

Reference direction：

```text
client / API
     |
     v
+----------------+
| Job Authority  | ----> durable Job Store
+-------+--------+
        |
        | claim / finish / heartbeat protocol
        v
+----------------+
| remote worker  |
+-------+--------+
        |
        v
 external effect
```

这里：

```text
Job Authority
```

不必立刻独立 process。

第一阶段完全可以：

```text
API + Authority = same process
worker = remote process
```

---

# 8. Design A 的 Consequences

## Positive

### Single lifecycle authority

transition knowledge 集中。

### Storage hiding

worker 不知道：

```text
memory / SQLite / Postgres
```

### Security

worker 无需 DB write credential。

### Future evolution

storage migration 不要求 worker protocol 跟着 representation 改。

## Negative

### Availability

如果只有一个 authority instance：

```text
authority down
→ lifecycle write path unavailable
```

这是当前明确接受的 failure domain，不应该藏起来。

### Protocol cost

remote worker 后新增：

- timeout；
- retry；
- authentication；
- version skew；
- lease/ownership semantics；
- observability。

### Scale

未来 authority throughput 可能成为瓶颈。

但当前没有 requirement 证明现在需要 partition。

---

# 9. Design B — Shared DB Direct Coordination

这个方案不能被 strawman。

```text
API --------\
scheduler ----> shared jobs table
worker ------/
```

## Real Advantages

- DB transaction 可以做 atomic claim；
- 少一层 explicit service protocol；
- 小团队/同 deployment 下开发快；
- DB 已经提供 durability/locking primitive。

## Real Costs

### Schema becomes integration API

worker 与 API 都依赖 jobs table representation。

### Credential blast radius

worker compromise 可以直接写 durable truth。

### Domain rule duplication

除非把所有 transition rule 塞进 DB procedure/constraints，否则多个 process 仍各自解释 lifecycle。

### Independent evolution illusion

表面三个 services 可独立 deploy，实际上 schema change 需要 coordinated rollout。

## Instructor judgment

在某些规模小、同 owner、同 trust domain 系统中 B 完全可能是合理 pragmatic architecture。

但本题 requirement 明确要求：

```text
remote worker must not get durable-store direct-write credential
```

所以 B 与 requirement 冲突。

这比“microservices best practice”强得多：

> reject 的理由来自 concrete security/authority requirement。

---

# 10. 为什么不选 Replicated Per-Worker State？

```text
worker A truth
worker B truth
API truth
→ reconcile
```

当前没有：

- offline-first requirement；
- multi-master requirement；
- partition-tolerant independent writes requirement。

却会新增：

- conflict resolution；
- duplicate claim；
- merge semantics；
- causal/order reasoning。

所以 instructor reference reject。

不是因为它“不是 clean architecture”。

而是：

> complexity 没有被 requirement 支付。

---

# 11. Reference Architecture Invariants

本轮建议：

```text
A1. Only Job Authority accepts lifecycle transitions.

A2. Remote workers request claim/finish; they never mutate durable Job state directly.

A3. Worker timeout does not prove that execution did not happen.

A4. Snapshot remains a derived export in this phase.

A5. Reporting/read paths do not become lifecycle writers.

A6. Independently deployed worker/authority versions require a compatibility window.

A7. M07 concurrent_claim.py is an explicit historical fault-injection exception,
    not part of the target production authority path.
```

A7 看起来“课程特有”。

但它训练的是很真实的能力：

> architecture policy 需要知道哪些 code paths 在 scope 内。

---

# 12. Failure Walk — Worker Dies

```text
worker process dies
→ authority loses heartbeat / lease eventually
→ job execution status becomes uncertain until lease/recovery rule resolves
→ unrelated workers/API remain alive
```

需要未来 M10+/capstone 定义：

- lease duration；
- reclaim policy；
- side-effect safety。

当前 architecture 不应该假装这些已经实现。

---

# 13. Failure Walk — Network Lost After Command Starts

```text
worker starts command
→ network breaks
→ authority receives no finish
```

不能推导：

```text
command did not execute
```

所以：

```text
retry execution
```

必须与 M07 external-effect/idempotency reasoning 相连。

这是为什么 worker protocol 的错误语义是 architecture concern，而不只是 RPC client detail。

---

# 14. Failure Walk — Authority Dies

如果 authority 与 API 同 process：

```text
authority process dies
→ API lifecycle writes unavailable
→ remote worker may still physically execute already-claimed work
```

重启后如何 reconcile？

需要 durable authority state 才能严谨回答。

当前 TaskForge 仍是 memory baseline，所以 instructor reference 明确写：

```text
not solved in M09
```

而不是画一个 `Database` box 假装 durability 已存在。

---

# 15. Failure Walk — External Effect Succeeds, Finish Lost

M07 已经证明：

```text
effect
→ crash/lost finish
→ retry
→ duplicate possible
```

所以 architecture 必须保持：

```text
logical effect identity
```

能够到达真正 effect owner / sink。

不能把 dedup 责任仅留在 worker volatile memory。

---

# 16. ADR Reference

一个够用的 ADR 大概如下：

```markdown
# ADR-0001 — Job Authority is the sole lifecycle writer

Status: Accepted

## Context
TaskForge is adding remote workers. Today service and worker modules mutate
shared in-memory Job state directly. Remote workers must not receive durable
store write credentials.

## Decision
All normal lifecycle transitions go through Job Authority. Remote workers use
claim/finish protocol operations and never write the authority's storage
representation directly. Job Authority may initially share a process with the
API.

## Alternatives considered
1. Shared DB writes from API and workers.
2. Per-worker replicated lifecycle state with reconciliation.

## Consequences
+ lifecycle invariants have one semantic owner
+ storage mechanism is hidden from workers
+ worker privilege is reduced
- Job Authority becomes an availability dependency
- worker protocol needs timeout/retry/version semantics

## Revisit triggers
Reconsider partitioning/HA when measured throughput, recovery objectives, or
failure-isolation requirements exceed one authority domain.
```

注意它没有说：

```text
Use Kafka because scalable.
```

---

# 17. Reference Implementation：只做 Boundary-Enabling Refactor

我实际在**临时副本**中做了下面变化，没有提交到 starter：

新增：

```text
job_authority.py
```

包含：

```text
submit
get
list
cancel
claim_next
finish
queued_count
terminal_count
reset_for_tests
```

它仍然用：

```text
state.jobs
```

作为 representation。

这是刻意的。

M09 不是 persistence mechanism 章节。

---

# 18. 哪些模块迁移了？

reference 将：

```text
service.py
worker.py
metrics.py
legacy_audit.py
```

改成通过 semantic authority / service read path。

而：

```text
concurrent_claim.py
```

保持原状。

原因：

它是 M07 historical fault-injection artifact。

因此 refactor 后 direct `taskforge.state` import inventory 实际变成：

```text
concurrent_claim
job_authority
```

这比“全 repo 只允许一个 state import”更准确。

---

# 19. Actual Validation

临时 reference 实际运行：

```text
-- core + M09 reference tests --
......... [100%]
```

也就是：

```text
6 original core tests
+ 3 M09 architecture tests
= 9 passed
```

M09 tests 验证：

1. service + worker 通过同一个 authority 完成 submit → claim → finish；
2. normal product modules 不再直接 import state；
3. authority operation 不要求 worker 暴露/知道 storage representation。

---

# 20. Prior Behavior Evidence

## M05 text dashboard

实际：

```text
empty  fingerprint unchanged
queued fingerprint unchanged
mixed  fingerprint unchanged
```

## M06 legacy audit

实际三个 fingerprint 全部 unchanged。

这很重要，因为 `legacy_audit.py` 从：

```text
direct state read
```

改为：

```text
service.list_jobs()
```

但 observable output 没变。

## M07 historical fault injection

实际仍然稳定复现：

```text
one queued job -> two successful claim receipts
```

这看起来像“仍有 bug”。

但在课程 architecture scope 中，这是**明确保留的 historical teaching artifact**。

如果 production package 真要发布，当然要进一步决定是否把 teaching fixtures 移出 product package。

那属于 course packaging / cleanup decision，不应和本次 architecture reasoning 混淆。

## M08 compatibility

实际：

```text
v1 fixture fingerprint unchanged
current W1 -> frozen R1 unchanged
v2 break demonstration unchanged
future version fail-closed unchanged
```

说明 authority refactor 没偷改 durable export contract。

---

# 21. 为什么没有跑 M03 mutation_probe 作为 reference gate？

M03 mutation harness 是故意绑定 baseline source text 的 teaching tool。

例如它寻找 exact source：

```python
state.jobs[job_id] = Job(...)
```

当 M09 合法地把这段移动到 `job_authority.py` 后：

```text
mutation site not found
```

并不代表 product regression。

这说明一个很重要的 evolution lesson：

> **测试/工具本身也有适用版本和 architecture scope。**

正确做法不是为了保住 historical mutation harness 而拒绝结构演化。

而是：

- 保留 M03 checkpoint/history；
- 明确 harness 针对哪个 baseline；
- 当前 phase 使用当前 evidence。

---

# 22. Reference Architecture Fitness Function

一个合适的小检查是：

```text
normal product modules:
  service
  worker
  metrics
  legacy_audit

must not import taskforge.state directly
```

为什么不是：

```text
only job_authority may import state in entire repo
```

因为后者会误杀 explicit historical exception。

Architecture fitness rule 必须同时表达：

```text
invariant
+
scope
```

否则只是 grep policy。

---

# 23. 这个 Refactor 解决了什么？

解决：

```text
normal lifecycle semantic authority locality
```

它使未来：

```text
memory -> SQLite/Postgres
```

有机会在 authority 后面发生，而不要求 worker 理解 storage。

它也使 remote worker protocol 有一个 semantic target：

```text
claim
finish
```

而不是“远程改 row”。

---

# 24. 它没有解决什么？

非常多。

没有解决：

- durability；
- authority HA；
- claim concurrency atomicity in production path；
- lease/heartbeat；
- worker authentication；
- RPC protocol；
- remote version skew；
- crash recovery；
- exactly-once effects；
- multi-tenant isolation；
- cell partitioning。

这不是 incomplete architecture thinking。

相反，它是：

> **不要把未来 architecture mechanism 假装成已经实现的 guarantee。**

---

# 25. 为什么不在 M09 直接上 Cell Architecture？

AWS cell guidance 很有价值，因为它把 scope of impact 当 first-class concern。

但 TaskForge 当前 requirement 没有：

```text
large tenant population
known noisy-neighbor problem
regional isolation objective
```

所以现在实现 cell 会是 speculative complexity。

应该做的是保留一个 revisit trigger：

```text
when one authority/worker failure domain exceeds required blast-radius target
```

到那时再选择 partition key / cell grain。

---

# 26. Agent Review：Vague Prompt 会发生什么？

如果给 Agent：

```text
把 TaskForge 设计成 scalable distributed architecture
```

典型输出：

```text
API Gateway
Job Service
Scheduler Service
Worker Service
Redis
Kafka
Postgres
Kubernetes
```

问题不是这些技术坏。

问题是：

- 哪个 requirement 需要 Kafka？
- Job Service 和 Scheduler 谁是 lifecycle authority？
- shared DB 谁能写？
- worker timeout 怎么处理？
- snapshot 是什么？
- rollback 怎么做？

如果这些没回答，名词越多，unknown unknowns 越多。

---

# 27. 更好的 Agent Sequence

## Phase 1 — Recover

```text
facts, writers, readers, contracts, runtime/failure paths
```

## Phase 2 — Human-confirmed model

确认：

```text
what is product path?
what is historical/test path?
what requirements are real?
```

## Phase 3 — Design twice

至少两案，逐 consequence 比较。

## Phase 4 — ADR

把 accepted trade-off 写短。

## Phase 5 — Small enabling change

只做：

```text
authority boundary
```

而不是同时：

```text
RPC + DB + queue + deployment
```

## Phase 6 — Independent review

重新看代码和 probes。

---

# 28. Instructor Grading Notes

高分答案不需要和 reference topology 完全一样。

例如 shared-DB architecture 也可能得高分，如果学生：

- 明确 semantic authority 放在 DB transaction/stored procedure/constraint；
- 解决 worker credential requirement（例如 restricted API/role）；
- 诚实记录 schema coupling；
- 给出 rollout/rollback；
- 不声称 services independent when they are not。

真正低分的是：

```text
“微服务更 scalable，所以拆服务”
```

但没有 consequence model。

---

# 29. 最终 Instructor Judgment

M09 的关键不是选中某个 diagram。

而是学生开始习惯：

```text
Architecture decision
=
important system consequence
+
explicit boundary
+
assumptions
+
trade-offs
+
migration/recovery reasoning
+
evidence
```

当他们以后指挥 Agent 做大系统改造时，这比背任何 architecture style 名字都更有价值。
