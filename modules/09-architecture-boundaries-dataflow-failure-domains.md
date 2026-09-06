# M09 — Architecture：边界、数据流、Authority 与 Failure Domain

> 这一章不从“微服务 / 分层 / 六边形 / CQRS / Event Sourcing”名词开始。
>
> 我们先回答一个更基础的问题：**一个 design decision 什么时候重要到值得被称为 architecture？**

前八章已经分别训练了：

```text
M01 contract / invariant
M02 state ownership
M03 executable evidence
M04 boundary / error / retry
M05 evolutionary change
M06 legacy takeover
M07 concurrency / crash / failure
M08 compatibility / migration
```

M09 要把这些局部 reasoning 重新组合成 system-level model。

---

# 1. Architecture 不是“大盒子图”

很多 architecture discussion 一上来就是：

```text
Frontend
  ↓
API Gateway
  ↓
Service A / B / C
  ↓
Database
```

图本身没有错。

问题是它可能完全没有回答：

- 谁拥有 lifecycle truth？
- 谁能修改状态？
- crash 后什么还存在？
- snapshot 是 source of truth 还是 export？
- worker failure 会影响几个用户？
- old consumer 可以和 new producer 共存多久？
- external effect 如何 deduplicate？
- 哪条 dependency 是长期 contract，哪条只是 local implementation？

如果这些问题没有答案，再漂亮的图也只是 topology illustration。

SEI 对 software architecture 的一个核心 framing 是：

> architecture 是**为了对系统进行推理而需要的 structures**；这些 structures 由 elements、relations 和它们的 properties 构成。

这给我们一个很实用的判断：

> **一张图值不值得画，取决于它是否帮助回答一个重要 engineering question。**

而不是图上 box 越多越 architecture。

---

# 2. 什么决定具有 architectural significance？

Martin Fowler 总结 Ralph Johnson 时有一句很有用的话：

```text
Architecture is about the important stuff.
```

“important”不能靠职位或直觉定义。

本课程用下面七个 consequence 作为 heuristic。

如果一个决定在多个维度上都很高，就更值得上升成 architecture concern。

## 2.1 Blast radius

错了影响多大？

```text
一个 formatter 的局部 bug
```

通常不是 architecture。

```text
所有 worker 都能直接写 shared lifecycle rows
```

很可能是。

因为错误会跨多个执行主体传播。

---

## 2.2 Reversal cost

这个决定以后能多容易撤销？

```text
rename private helper
```

很容易。

```text
把 durable format 从 v1 切成 v2 并写了三个月数据
```

很难。

M08 已经看到：

```text
binary rollback
!=
system rollback
```

一旦 decision 改变 durable state 或 long-lived protocol，它的 architecture significance 通常上升。

---

## 2.3 Coordination cost

改变它要协调多少独立 actor？

```text
same module
same owner
same deployment
```

通常较低。

而：

```text
three teams
four repos
offline clients
rolling deployment
```

明显更高。

---

## 2.4 Failure consequence

它会改变 failure 怎样传播吗？

例如：

```text
cluster B down
→ route all traffic to A
→ A overload
→ A down
```

一个看起来“提高 availability”的 failover policy，可能实际上把 local failure 变成 global failure。

Google SRE 的 cascading-failure 讨论正是在强调这种 mechanism interaction。

---

## 2.5 Authority consequence

它会改变谁有资格决定 truth 吗？

例如：

```text
API service writes Job.status
worker writes Job.status
scheduler writes Job.status
recovery script writes Job.status
```

这不是普通 code organization 问题。

这是 semantic authority 问题。

---

## 2.6 Long-lived contract

这个决定会活多久？

```text
private Python call
```

可能随着一次 refactor 消失。

```text
snapshot schema
remote worker protocol
public error code
config file
```

可能比当前 implementation 活得久得多。

---

## 2.7 Unknown-consumer risk

你能不能枚举所有依赖者？

如果可以：

```text
3 call sites
same repo
```

变更风险容易控制。

如果是：

```text
old binary
offline tool
external script
third-party client
```

architecture significance 上升。

---

# 3. Architecture 是 Consequential Boundaries

把前面浓缩成一句：

> **Architecture 关注那些会跨局部边界放大 consequence 的结构。**

常见 consequential boundary 有：

```text
Knowledge boundary
Authority boundary
Durability boundary
Compatibility boundary
Failure boundary
Security boundary
Team / ownership boundary
```

它们可以重合。

但不应该被默认认为重合。

---

# 4. Semantic Boundary ≠ Process Boundary

这是 M09 最重要的区分之一。

假设我们有：

```text
JobAuthority
```

它负责：

- create job；
- validate transition；
- claim；
- finish；
- cancel；
- expose read model。

它可以首先只是：

```text
same Python process
same repository
one module
```

但已经形成很强的 **semantic boundary**。

另一个系统可能有：

```text
API Service
Worker Service
Scheduler Service
```

三个独立 process。

但它们都直接写：

```text
shared jobs table
```

此时虽然有三个 deployment boundary，semantic authority 仍然是 split 的。

所以：

```text
more processes
!=
stronger architecture
```

---

# 5. 四种 boundary 不要混在一起

## 5.1 Semantic boundary

谁负责什么 concept / invariant？

## 5.2 Process boundary

哪里需要 IPC / network / serialization？

## 5.3 Deployment boundary

什么可以独立 rollout / rollback / scale？

## 5.4 Failure boundary

一个 component 挂掉时，什么还能继续工作？

它们有时应该重合。

例如 remote worker：

```text
worker crashes
```

你可能希望：

```text
API + other workers remain available
```

此时 process boundary 确实帮助形成 failure isolation。

但 metrics function 没有这种需求，就没必要为了“architecture purity”做成网络服务。

---

# 6. Process Boundary 是昂贵的

把一个 function call：

```python
job = authority.claim(worker_id)
```

变成 network call 后，新增的不是一行 RPC client。

新增的是：

```text
serialization
partial failure
timeout
retry
idempotency
authentication
authorization
version skew
observability
capacity
backpressure
rollout compatibility
```

所以 network boundary 应该有明确收益来支付这些成本。

典型收益包括：

- independent failure isolation；
- independent scale；
- remote hardware/location；
- privilege/security isolation；
- independent ownership/deployment；
- heterogeneous runtime。

没有这些需求时，process split 可能只是 complexity tax。

---

# 7. Monolith 与 Microservice 不是成熟度等级

Fowler 的 `Monolith First` 文章最有价值的不是“所有系统必须 monolith first”。

而是提醒：

> service decomposition 需要真正稳定的 boundary，而 service 本身有额外 premium。

本课程把系统选择看成：

```text
Architecture requirement
        ↓
Which boundary needs independent process/deployment/failure isolation?
        ↓
Choose mechanism
```

而不是：

```text
monolith -> beginner
microservices -> advanced
```

TaskForge 当前规模下，如果为了：

```text
metrics
snapshot exporter
audit formatter
```

各自起一个 service，很可能只是把 local dependency 变成 distributed dependency。

---

# 8. Authority View：谁拥有 Truth？

TaskForge 当前 baseline：

```text
state.py
  jobs: dict
```

但这不代表 `state.py` 就是 semantic owner。

目前：

```text
service.py          writes lifecycle
worker.py           writes lifecycle
concurrent_claim.py writes lifecycle
```

因此当前真实模型更接近：

```text
shared representation
+
multiple authorities
```

M09 要求你明确：

```text
Job lifecycle authority = ?
```

一个更强的目标 architecture 可以是：

```text
             +----------------+
API -------->|                |
worker ----->|  Job Authority |----> durable Job Store
admin ------>|                |
             +----------------+
                     |
                     +----> read views / snapshot export
```

关键不是 box。

关键是 invariant：

> **只有 Job Authority 有权接受或拒绝 lifecycle transition。**

worker 可以请求：

```text
claim
finish
heartbeat
```

但不是 authority。

---

# 9. Storage Owner ≠ Semantic Owner

M02 已经强调过：

```text
who stores data
!=
who owns state
```

M09 把它提升到 deployment scale。

例如：

```text
PostgreSQL stores rows
```

不意味着：

```text
PostgreSQL is domain authority
```

如果三个 service 都根据自己的规则更新 row：

```text
status='running'
```

数据库最多执行 structural constraints。

它无法自动知道完整 domain protocol。

反过来，一个 Job Authority 可以使用：

```text
memory
SQLite
Postgres
DynamoDB
```

而 semantic boundary 不需要跟着 storage mechanism 改名。

---

# 10. Snapshot 是什么？必须选一个答案

TaskForge M08 有：

```text
snapshot.py
```

现在它把 current state 序列化成 durable JSON。

Architecture review 必须明确：

## Option A — Export artifact

```text
Job Authority
   ↓
snapshot export
```

snapshot 用于：

- debugging；
- offline analysis；
- transfer；
- backup artifact。

它不是 live truth。

## Option B — Recovery source

如果 startup 会：

```text
load snapshot
→ reconstruct authority
```

那 snapshot 就进入 durability contract。

此时：

- atomic write；
- fsync；
- corruption；
- schema migration；
- partial snapshot；
- stale snapshot；

都会成为 architecture concern。

## Option C — Shared database substitute

多个 process 同时读写 JSON snapshot。

这通常会迅速产生 concurrency / crash / locking 问题。

所以：

> 不要让 mechanism 自己偷偷决定 semantic role。

---

# 11. Runtime View：Data Flow 与 Control Flow 分开看

一个 useful view：

```text
client
  |
  | submit
  v
Job Authority ----> durable store
  |
  | claim
  v
worker
  |
  | execute
  v
external world
  |
  | finish
  v
Job Authority
```

这里至少有两种 flow。

## Control flow

谁调用谁？

```text
client -> authority -> worker
```

## Data flow

什么 information 在哪里移动？

```text
command
job_id
lease/claim token
exit_code
effect id
```

有些 design bug 不在 call graph 里明显出现。

例如：

```text
worker never calls DB API directly
```

但它拿到了 database credential 并自己连 shared DB。

control-flow 图可能看起来干净，authority view 却已经破裂。

---

# 12. Read Model 可以分离，但 Writer Authority 不要随便复制

metrics / dashboard / audit 往往不需要 authoritative mutation。

它们可以消费：

```text
read API
snapshot
stream
replica
```

这和：

```text
多个 writer 都可以改 source of truth
```

是完全不同的问题。

课程常用的一个 architecture simplification 是：

```text
one semantic write authority
many derived read models
```

但这也不是 universal CQRS rule。

如果系统很简单：

```text
same module query
```

完全可能足够。

---

# 13. Failure Domain：一个失败会拖谁下水？

AWS cell-based architecture 的价值在于把 **scope of impact** 直接当设计对象。

假设 100 个 tenants 全部共享：

```text
one worker pool
one hot queue
one effect sink
```

一个 poisoned workload 可能：

```text
consume all workers
→ queue latency rises globally
```

另一种设计：

```text
cell A -> tenants 0..9
cell B -> tenants 10..19
...
```

如果 cell 真正独立：

```text
cell A failure
```

不应该把其他 cells 拖下去。

但“画了 cell”不够。

如果 cells 仍共享：

```text
same stateful coordinator
same exhausted connection pool
same global lock
```

failure boundary 可能是假象。

---

# 14. Failure Containment 要检查 Cross-Boundary Dependencies

Architecture review 可以做一个 failure walk：

```text
Component X fails
    ↓
Who waits?
Who retries?
Who fails over?
Who receives extra load?
Who owns recovery?
What state becomes unavailable?
What capacity assumption changes?
```

例如：

```text
worker pool B fails
→ router sends B work to A
→ A capacity < A+B load
→ A overload
→ global outage
```

这不是“load balancer implementation bug”。

它是 architecture-level capacity/failure assumption 错了。

---

# 15. Retry / Failover 会改变 Dependency Graph

M07 已经学过：

```text
retry
```

不是 local error-handling detail。

M09 再进一步：

```text
retry policy
```

实际上增加了 runtime edges。

正常情况：

```text
A -> B
```

failover 后：

```text
A -> B
A -> C
```

这意味着 C 现在也是 A 的 failure-path dependency。

所以 architecture diagram 如果只画 happy-path dependency，可能严重低估真实 coupling。

---

# 16. Compatibility Boundary：独立演化才需要 Protocol Discipline

一旦有两个 independently deployed components：

```text
Authority v2
Worker v1
```

你就获得了 M08 的 version-skew 问题。

因此 process split 的 cost 之一是：

```text
internal function contract
        ↓
versioned distributed protocol
```

这会要求：

- backwards/forwards compatibility；
- rollout order；
- deprecation；
- capability negotiation；
- rollback model。

所以“拆 service”不仅增加 runtime failure，还增加 **time dimension coupling**。

---

# 17. Security Boundary 也可能决定 Process Boundary

有时即使 performance / scale 不要求拆，也可能因为 privilege 拆。

例如 remote worker 可以执行：

```text
shell command
```

而 API/control plane 不应该拥有相同 host permissions。

此时：

```text
control plane
  ↓ restricted protocol
execution worker
```

可能是一个很有价值的 process/security boundary。

这里的 architecture reasoning 是：

```text
separate privileges
reduce compromise blast radius
```

而不是“微服务更 clean”。

---

# 18. Team Boundary：Conway's Law 不需要神秘化

如果两个模块：

```text
必须每次一起改
必须一起 deploy
共享 undocumented state
```

但由两个完全独立团队负责，coordination cost 会持续出现。

反过来，如果想让两个团队真正独立，需要技术边界支持：

```text
stable contract
independent tests
version policy
clear ownership
```

所以 architecture 与 organization 会互相影响。

但课程不把“team topology”当 deterministic law。

先从 concrete coordination consequence 分析。

---

# 19. 多 View 比一张全能图更诚实

M09 要求至少五张“小图”。

## View 1 — Responsibility / Knowledge

```text
component -> unique knowledge
```

例如：

```text
Job Authority -> lifecycle rules
Snapshot Codec -> durable format
Effect Sink -> external dedup semantics
```

## View 2 — Authority / State

标出：

```text
authoritative
storage
replica
snapshot
cache
read model
```

## View 3 — Runtime Flow

```text
submit
claim
execute
finish
observe
```

## View 4 — Failure Propagation

```text
worker crash
store down
sink timeout
bad deploy
```

分别追踪 scope。

## View 5 — Evolution / Compatibility

```text
producer vN
consumer vN-1
rollout
rollback
```

这些 view 之间如果矛盾，通常就是 architecture bug 的信号。

---

# 20. Architecture Diagram 的常见谎言

## 20.1 “Database” 一个 box

但没人标：

- writer；
- schema owner；
- transaction boundary；
- replica lag；
- migration owner。

## 20.2 “Service A → Service B”

但实际还有：

```text
A reads B's DB
A imports B's schema package
A retries to C when B fails
```

## 20.3 “Worker Pool”

但 workers 的：

```text
identity
lease
ownership
recovery
```

全没画。

## 20.4 “Cache”

但没人说：

```text
cache miss behavior
staleness contract
invalidations
source of truth
```

因此 diagram review 最重要的问题通常是：

> **这个 box/arrow 省略了哪些 consequential semantics？**

---

# 21. Architecture Decision：Design It Twice

和 M02/M05 一样，architecture 不应该只有一个草图。

假设 TaskForge 现在要求 remote workers。

至少比较：

## Design A — Modular Authority + Remote Worker Protocol

```text
API / scheduler / persistence
        ↓
   Job Authority
        ↓ protocol
remote workers
```

Authority 可以先和 API 同 process。

### 优点

- one lifecycle authority；
- remote execution boundary 明确；
- distributed complexity 集中在真正需要 remote 的地方；
- future storage migration 在 authority 后面。

### 缺点

- authority 可能是 availability bottleneck；
- 要设计 worker protocol；
- scale/failure isolation 以后可能需要进一步 partition。

---

## Design B — Every Component Owns and Syncs Its State

```text
API state
scheduler state
worker state
     ↕ sync/event
```

### 优点

- 每个 process 看起来独立；
- local reads fast。

### 缺点

- lifecycle truth reconciliation；
- duplicate claims；
- conflict semantics；
- recovery complexity；
- consistency model 成为系统主问题。

除非业务真的需要 multi-authority / offline operation，否则这个复杂度通常没有被需求支付。

---

## Design C — Shared DB as Integration Contract

```text
API ------\
scheduler ---> shared jobs table
worker ----/
```

### 优点

- implementation 快；
- DB transaction 可解决部分 race；
- 少一个 explicit service protocol。

### 缺点

- schema 变成跨组件 public contract；
- semantic authority 仍可能 split；
- DB credential 扩散；
- independent deployment 受 schema coupling 限制。

这个设计不是“绝对错误”。

如果 components 同 owner、同 deploy、规模小，它可能是 pragmatic choice。

关键是不要把 shared table 误称为 clean service boundary。

---

# 22. Architecture Invariant

好的 architecture design 应该能写出几条跨模块 invariant。

TaskForge 例子：

```text
A1. Only Job Authority may accept a lifecycle transition.

A2. Worker never mutates durable job state directly.

A3. Snapshot is a derived export, not a live coordination channel.

A4. External effect deduplication belongs to the authority that can identify a logical effect.

A5. A worker failure must not make unrelated queued jobs unclaimable forever.

A6. A new worker protocol version must coexist with the supported previous version during rolling deployment.
```

这些比：

```text
use repository pattern
use service layer
```

更有 architectural value。

---

# 23. Architecture Fitness Function

有些 architecture rule 可以变成 executable evidence。

例如：

```text
production modules other than job_authority.py
must not import taskforge.state
```

或者：

```text
historical snapshot v1 fixture must remain readable
```

或者：

```text
worker package must not depend on DB driver package
```

这种检查常被称作 architecture fitness function / architecture test。

课程不要求引入 framework。

一个 50 行 AST script 就可能足够。

重要的是：

> **只自动化真正稳定且 consequential 的 architecture invariant。**

否则 architecture test 会退化成目录命名 policing。

---

# 24. 当前 M09 Probe 说明了什么？

运行：

```bash
PYTHONPATH=src uv run --with pytest --no-project python tools/m09_architecture_probe.py
```

baseline 会报告：

```text
DIRECT STATE DEPENDENCIES
  concurrent_claim
  legacy_audit
  metrics
  service
  worker

LIFECYCLE MUTATORS
  concurrent_claim
  service
  worker
```

这个结果不等于：

```text
5 direct imports = architecture score 0
```

它只是 evidence。

你还必须分类：

- 哪些属于 current product path？
- 哪些是历史 teaching/fault-injection module？
- 哪些读依赖可以允许？
- 哪些写依赖违反目标 authority？

这一步非常重要。

**Architecture review 不是 grep-driven refactor。**

---

# 25. Historical Teaching Module 也是 Architecture Context

TaskForge 是课程系统，因此源码里有：

```text
concurrent_claim.py
```

它故意保留 M07 race。

一个 naïve Agent 可能看到：

```text
state import
```

就统一迁移它，结果 M07 deterministic probe 失去教学意义。

因此 M09 还要训练：

> **Architecture scope 必须先定义。**

真实系统里类似情况是：

- migration tool；
- admin script；
- compatibility shim；
- test harness；
- deprecated endpoint；
- emergency repair tool。

它们可能不在正常 runtime path，却仍可能拥有高权限。

不能简单忽略，也不能和主 product path 混为一谈。

---

# 26. ADR：记录 Why，不只是 What

2026 年 Fowler 的 ADR 总结很适合 M09。

一个 architecture decision record 应该很短。

TaskForge 示例：

```text
ADR-0001: Job Authority is the sole lifecycle writer
```

至少记录：

## Context

为什么现在需要决定？

```text
remote workers are being introduced;
current service and worker both mutate shared state.
```

## Decision

```text
Workers request claim/finish through Job Authority.
Workers do not receive direct durable-store write access.
```

## Alternatives

```text
shared DB writes
per-worker replicated state
```

为什么没选？

## Consequences

```text
+ invariant enforcement localized
+ storage can change behind authority
- authority availability matters
- remote protocol now needs compatibility policy
```

## Revisit trigger

```text
one authority cannot meet required throughput/failure-isolation target
```

这个最后一项很重要。

Architecture decision 不是永恒真理。

---

# 27. ADR 不要写成墓碑

差的 ADR：

```text
Decision: Use PostgreSQL.
Reason: PostgreSQL is robust and popular.
```

这几乎没有 reasoning value。

更好的：

```text
We need atomic lifecycle transitions across API and remote-worker requests.
We require crash recovery on one VPS and do not need multi-region writes.
Choose PostgreSQL/SQLite/... because ...
Reject X because ...
Revisit when ...
```

重点是 forces 和 trade-offs。

当两个 architecture 都能满足功能要求时，比较往往会继续落到 uncertainty、reversibility、migration/review cost 和 future option；旁支 [Engineering Risk、Estimation 与 Economics](../extensions/engineering-risk-estimation-economics.md) 专门讨论这一层。另一方面，architecture 图也不是越完整越好：如何按问题选择 dependency、state、sequence、data-flow 或 C4-style view，见 [Models、Notation 与 UML](../extensions/models-notation-and-uml.md)。

---

# 28. Architecture 与 Evolution

Architecture 不是 project kickoff 产生一次后冻结。

Fowler 明确强调 architecture 应支持自己的 evolution。

课程把 architectural evolution 看成：

```text
current system model
        ↓
new pressure
        ↓
identify architectural consequence
        ↓
design alternatives
        ↓
choose migration path
        ↓
preserve compatibility / rollback
        ↓
measure whether assumption still holds
```

M05 的 change topology 和 M08 的 migration window 都在这里重新出现。

---

# 29. 不要“未来-proof”所有东西

Architecture 不是：

```text
为所有未来可能性先抽象
```

而是：

```text
对 high-consequence uncertainty 留下合理 reversibility
```

例如：

你不需要现在实现：

```text
multi-region active-active Job Authority
```

但可以保证：

```text
worker does not know storage representation
```

这样未来 authority storage 从 memory 变 SQLite/Postgres 时，worker protocol 不必一起重写。

这就是有价值的 option value。

---

# 30. Architecture Risk Register

每个 architecture proposal 至少写：

| Risk | Mechanism | Evidence / mitigation |
|---|---|---|
| authority outage | all writes depend on one authority | restart/recovery + later HA |
| worker duplicate | retry after timeout | lease/idempotent claim |
| protocol skew | rolling deploy | N/N-1 compatibility |
| snapshot confusion | operators restore stale export | explicitly mark export semantics |
| sink duplicate | crash after effect | effect idempotency key |

不是为了 process bureaucracy。

而是防止 diagram 把不确定性藏掉。

---

# 31. Architecture Review 的核心问题

## Boundary

- 这个 boundary 隐藏了什么 knowledge？
- client 为什么不需要知道 implementation？
- 是否有 backdoor dependency？

## Authority

- 谁拥有 truth？
- 是否有绕过 authority 的 writer？
- invariant enforcement 是否和 authority 对齐？

## Data

- durable state 在哪里？
- cache/snapshot/replica 是否被误当 source of truth？

## Runtime

- normal path 的 calls / data flow 是什么？
- timeout/retry/failover 时多出哪些 edges？

## Failure

- component down 时谁一起 down？
- failure 是否扩散到别的 domain？

## Evolution

- independently deployed components 如何 version？
- rollout / rollback 顺序是什么？

## Operations

- 如何观察这个 architecture invariant 在 production 是否成立？

---

# 32. Agent 做 Architecture 时的典型失败模式

Agent 在 architecture task 上最危险的不一定是不会画图。

而是太容易补齐“看起来专业”的模式。

## 失败 1：Pattern autocomplete

Prompt：

```text
给我设计一个可扩展的 TaskForge architecture
```

可能得到：

```text
API Gateway
Auth Service
Scheduler Service
Job Service
Worker Service
Event Bus
Redis
Kafka
PostgreSQL
Kubernetes
```

每个词都合理。

但组合起来不一定有任何需求证据。

---

## 失败 2：Topology before semantics

先决定：

```text
5 microservices
```

再去分 responsibility。

正确顺序应该更接近：

```text
authority / contract / failure / security requirements
        ↓
semantic boundaries
        ↓
deployment topology
```

---

## 失败 3：Happy-path diagram

Agent 很容易画：

```text
A -> B -> C
```

但不画：

```text
B timeout
A retries
A fails over to D
C still executes original request
```

真正的 architecture bug 常在后者。

---

## 失败 4：Shared DB hidden coupling

图上是：

```text
Service A   Service B
```

代码里却：

```text
A and B both mutate same tables
```

Agent 如果只读 README/diagram 会被误导。

所以 architecture reconnaissance 必须 repo-search actual dependencies。

---

## 失败 5：Future-proof explosion

Agent 很擅长列未来场景：

```text
multi-region
ten million QPS
plugin marketplace
arbitrary workflow DAG
multi-cloud
```

但 architecture 应优先解决当前已知 high-consequence pressure。

---

# 33. 给 Agent 的 Architecture Reconnaissance Contract

第一阶段只读：

```text
Do not propose a target architecture yet.

1. Identify all lifecycle writers/readers.
2. Identify durable/long-lived formats and external interfaces.
3. Trace submit -> claim -> finish control/data flow.
4. Identify normal-path and failure-path dependencies.
5. Classify source-of-truth / replica / snapshot / cache.
6. Identify process/deployment boundaries that actually exist today.
7. Separate product runtime code from test/migration/teaching/repair code.
8. List unknowns that materially affect architecture.
```

先拿到 system model。

再进入 design。

---

# 34. 给 Agent 的 Architecture Design Contract

第二阶段：

```text
Design at least two architectures.

For each:
- authority model
- data/control flow
- deployment boundaries
- failure domains
- compatibility consequences
- security/privilege boundaries
- migration path
- rollback path
- operational evidence

Do not add infrastructure unless tied to a stated requirement.
```

---

# 35. Independent Review 仍不可省

Architecture diff 可能不是 code diff。

但 reviewer 仍要独立检查：

- assumptions 是否真实？
- alternatives 是否 strawman？
- blast radius 是否遗漏？
- failure path 是否画了？
- authority 是否清楚？
- migration 是否现实？
- rollback 是否真的可执行？
- complexity 是否由真实 requirement 支付？

Agent 的架构输出尤其容易“听起来都对”。

因此必须把判断落到 consequence/evidence。

---

# 36. TaskForge M09 Target Architecture

本章不要求你实现完整 distributed system。

本章要求形成一个可以指导 M10–M13 的 architecture baseline。

一个合理 reference direction 是：

```text
                        +-------------------+
client / public API --->|                   |
admin ----------------->|   Job Authority   |<---- snapshot exporter/read models
                        |                   |
                        +---------+---------+
                                  |
                         durable Job Store
                                  |
                claim/finish protocol
                                  |
                         +--------v--------+
                         | remote workers  |
                         +--------+--------+
                                  |
                           external effects
                                  |
                         idempotent sink / owner
```

但注意：

```text
Job Authority
```

可以先与 API 在同一个 process。

本章不提前决定它必须是独立 service。

---

# 37. 本章实验为什么只做 Boundary-Enabling Refactor

如果 M09 直接实现：

```text
HTTP server
Postgres
message queue
remote agent
```

学生会忙于 mechanism。

architecture reasoning 反而被淹没。

所以实验只实现一个很小的 architectural move：

> **让 normal product lifecycle path 通过一个明确 Job Authority，而不是让 worker 直接碰 representation。**

然后验证：

- old behavior 保持；
- snapshot contract 保持；
- legacy audit observation 保持；
- M07 fault-injection module 被明确标为 historical/test-only exception，而不是无意识 backdoor；
- authority boundary 可以以后换 storage，而 client 不知道。

这一步不是最终 architecture。

它是一个 **architecture-enabling seam**。

---

# 38. 你应该保留的最终习惯

以后看到 architecture proposal，不先问：

```text
用了什么 pattern？
用了什么云服务？
几个 microservices？
```

先问：

```text
What truth exists?
Who owns it?
What crosses this boundary?
What happens when it fails?
What survives a crash?
Who must evolve together?
How do we roll it back?
Which assumption would make us redesign this?
```

如果这些问题有清晰答案，architecture 才真正开始存在。

---

# 39. M09 与前面课程的连接

```text
M01 invariant
  ↓
M02 authority / information hiding
  ↓
M03 evidence
  ↓
M04 boundary semantics
  ↓
M05 evolutionary path
  ↓
M06 unknown-system takeover
  ↓
M07 failure / concurrency
  ↓
M08 compatibility / migration
  ↓
M09 system-level consequential boundaries
```

M09 不是突然进入另一个主题。

它只是把前面所有 reasoning 提升到 system scale。

---

# 40. 下一章预告

M10 会进入：

```text
Code Review 与 Change Engineering
```

因为 architecture 最终仍通过 change 落地。

M10 会问：

> **一个 PR 到底应该提供哪些证据，reviewer 怎样验证 change scope、contract、migration、failure mode 和 architecture invariant，而不是只读 diff 看 style？**
