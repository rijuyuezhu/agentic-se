# M09 Instructor Analysis — 从 remote-worker pressure 推到 architecture boundary

> 这是 instructor reference，不是唯一正确 architecture。它展示的是：怎样从真实 starter、明确 requirement、可比较 alternatives 和 executable evidence 推出一个**有条件的** architecture direction；学生可以选择不同 topology，只要 authority、failure、compatibility 与 migration reasoning 能闭合。

## 1. 先恢复 current system，而不是先画 target diagram

M09 probe 的 current baseline 是：

```text
[DIRECT STATE DEPENDENCIES] concurrent_claim, legacy_audit, metrics, service, worker
[LIFECYCLE MUTATORS] concurrent_claim, service, worker
[LONG-LIVED SURFACES] public_api, snapshot schema, audit output, external effect protocol
[ARCHITECTURE PRESSURE] semantic authority is not aligned with module/process boundaries
```

这个 inventory 不能直接变成“把五个 import 都删掉”。源码角色不同：

| Module | Current role | M09 relevance |
|---|---|---|
| `service.py` | normal submit/get/list/cancel path | direct lifecycle writer |
| `worker.py` | normal claim/finish path | direct lifecycle writer；remote requirement 直接影响它 |
| `metrics.py` | product read/reporting path | direct state reader |
| `public_api.py` | external-style API boundary | 经 `service` 访问 |
| `snapshot.py` | JSON format/export + decoder | long-lived compatibility surface |
| `legacy_audit.py` | M06 legacy/reporting integration | direct reader + external filesystem/time/env seams |
| `concurrent_claim.py` | M07 deterministic race fixture | deliberate historical direct writer |
| `effect_delivery.py` | M07 effect/crash teaching model | external-effect boundary，不是 durable delivery system |

当前 `state.py` 只有 `jobs` 和 `next_job_number` 两个 in-memory globals。Storage location 并不构成 semantic authority；真正 lifecycle knowledge 分散在 `service.py`、`worker.py` 与 historical `concurrent_claim.py`。

所以 current model 是：

```text
shared in-process representation
+
multiple semantic writers
+
no implemented durable Job authority
```

这是后面所有 target reasoning 的起点。

## 2. Remote worker requirement 先否掉两个“看起来很直接”的方案

Requirement 要求 worker 能在另一台机器执行、worker crash 不带着 API crash、worker 不拿 durable-store direct-write credential，并且 network timeout 不等价于 non-execution。

第一条事实已经让 current worker implementation不能直接迁移：

```text
remote worker -> another process's state.jobs
```

不存在。

最容易想到的替代是共享数据库：

```text
API --------\
scheduler ----> jobs table
worker ------/
```

这个方案有真实优点：DB transaction 可以帮助实现 atomic claim；少一个 service protocol；同一小团队可以很快实现。

但本题的 direct-write credential requirement 已经使“worker 自己写 durable table”的版本不合格。即使忽略 credential，多个 process 仍可能各自解释 lifecycle rule；split semantic authority 不会因为 representation 从 dict 换成 SQL 自动消失。

因此 reference 把问题重新写成：**worker 需要依赖什么 semantic contract，而不是它应该连哪种 storage？**

这时 dependency inversion 才有实际用途。Reference 希望得到：

```text
worker -> claim / finish / heartbeat semantics
       -> lifecycle authority hides storage detail
```

而不是：

```text
worker -> StoreInterface -> jobs table schema
```

后者即使使用 interface / DI，也可能只是把 low-level detail 换了一个注入入口。

## 3. Reference 选择 Design A，但理由来自 requirement，不来自 pattern prestige

### Design A — central semantic authority + remote worker protocol

Reference direction：

```text
client / API
     |
     v
+----------------+
| Job Authority  | ----> storage mechanism
+-------+--------+
        |
        | claim / finish / heartbeat
        v
+----------------+
| remote worker  |
+-------+--------+
        |
        v
 external effect
```

`Job Authority` 可以先与 API 同 process；这里先建立的是 semantic boundary，不是“Job Service” deployment topology。

Reference 接受它的原因：

- normal lifecycle rules 有单一 semantic owner；
- worker 不需要 storage representation / direct-write credential；
- future storage migration 可以发生在 authority 后面；
- remote execution 的 distributed complexity 集中在真正必须跨 machine 的 edge。

Reference 同时接受代价：

- authority 是 lifecycle write-path availability dependency；
- remote protocol需要 timeout/retry/auth/version semantics；
- 单 authority domain 未来可能碰到 throughput 或 failure-isolation上限。

这里的 “storage mechanism” 是 future placeholder。当前 starter 没有 durable store contract；reference 不会把一张图升级成 durability guarantee。

### Design B — shared DB direct coordination

B 不是错误 architecture 的代名词。若 components 同 owner、同 trust domain、同 rollout，DB transaction + constraints/procedures 有可能承担清楚的 authority，并避免额外 service hop。

但本题 worker 不能拿 direct-write credential，所以 reference reject **这个 requirement set 下的 direct-write B**。另外，如果 API/worker 都根据各自代码解释 lifecycle，schema 会变成隐性 integration API，独立部署只是表面上的。

### Design C — replicated per-worker state

C 只有在 offline/multi-master/partition-tolerant writes 等 requirement 出现时才值得认真支付 reconciliation cost。当前没有这些 requirement，因此 reference reject；不是因为“replication 不 clean”，而是因为 complexity 没有被需求支付。

## 4. Reference invariant 与 current fact 必须分开

Reference target 写下：

```text
A1. Normal product transition decisions are routed through Job Authority;
    named historical/fault-injection paths remain explicit exceptions.
A2. Remote workers request lifecycle operations; they do not receive direct
    authority-storage mutation responsibility.
A3. Worker timeout does not prove execution absence.
A4. Snapshot remains a derived export in this phase.
A5. Read/reporting paths should not acquire lifecycle mutation capability
    through authority-bearing mutable handles.
A6. Independently deployed authority/worker versions need an explicit coexistence policy.
A7. concurrent_claim.py is an explicit historical teaching exception.
```

这些是 **target/reference properties**，不是 starter 已满足的事实，也不是后面的最小 boundary-enabling refactor 能全部证明的 acceptance checklist。该 refactor 可以让 normal transition policy / direct-state access 开始收敛，并移除 worker 对 `state` namespace / storage mechanism 的直接知识；但 A5 是更强的 capability property。

如果 `get()` / `list_jobs()` / `claim_next()` 仍把 authoritative mutable `Job` reference 透传给 caller，caller 即使没有任何 `state.py` import，也仍能直接改 lifecycle。M02 已经把这种 read result 定义为 authority-bearing handle。Instructor reference 本轮**不**为此引入 `JobView`、defensive copy 或新的 capability test；它把这条风险保留为 explicit residual / follow-up，以保持 M09 的 architecture-localization scope，也保持 M10 后续 review case 的既有教学前提。

A7 看起来很课程特有，但训练的是一般能力：architecture policy 总有 scope。Migration tool、repair utility、test harness、compatibility shim、emergency admin command 都可能有特殊权限；不能因为 repo grep 发现它们就机械纳入 normal product-path rule。

## 5. Snapshot 的角色必须按真实 code 说，不按文件名猜

当前 `snapshot.py` 做两件主要事情：

1. `service.list_jobs()` -> JSON；
2. snapshot JSON -> immutable `Snapshot` DTO。

它没有：

```text
startup
-> read snapshot
-> reconstruct state.jobs
-> resume lifecycle authority
```

也没有 crash-consistent restore、stale reconciliation 或 multi-writer recovery model。

所以 reference 在 M09 把 snapshot 定义成 **derived durable export / compatibility artifact**。它不是 current live truth，也不是 recovery authority。

若学生选择把 snapshot 升成 recovery source，也可以，但必须新增并审查 atomic write/durability、corruption、restore ordering、staleness、schema migration 与 reconciliation。不能只改一句文档。

## 6. Control plane / data plane 只作为有条件的 TaskForge lens

AWS 文档中的 control/data plane distinction 来自网络并推广到服务。Reference 不声称 remote worker 在标准 taxonomy 中“就是 data plane”。

课程 adaptation 是：

```text
lifecycle/control authority
  -> decides/records legal job transitions

execution plane
  -> executes command / touches external effect
```

这个 lens 的实际收益是 privilege 与 failure analysis。Execution worker 可能需要 shell/host permission，却不应因此获得 store-write permission；authority/API 则不应该因为负责 control semantics 就拥有同样的 arbitrary execution privilege。

同样，authority 暂时不可用不意味着已经开始的 command 立即停止；worker crash 也不应该带着 API process 一起 crash。Plane terminology 只是帮助表达这两个 responsibility profile，不要求强制两个独立 control services。

## 7. Failure walk：reference candidate 仍然留下很多未解决问题

### Worker dies

独立 process 至少限制了 process-crash scope。但 job 是否可以重新 claim，要依赖未来 lease/heartbeat/recovery rule。当前 M09 没实现这些，reference 明确记录为 unresolved。

### Network lost after command starts

```text
worker starts command
-> network breaks
-> authority sees no finish
```

不能推出 command 没执行。Retry execution 可能重复 external effect；这必须继承 M07 的 timeout / attempt / effect distinction。

### Authority dies

如果 authority 与 API 同 process：

```text
authority process down
-> lifecycle writes unavailable
-> remote worker may still physically execute already-claimed work
```

而当前 starter lifecycle state 是 memory。Reference 不承诺 restart reconciliation；要做这件事必须另建 durable authority/recovery contract。

### Effect succeeds, finish is lost

M07 的 `effect_delivery.py` 只用进程内 `completed_jobs` 和 same-process `SimulatedCrash` 展示 ordering window。它不提供 durable exactly-once guarantee。Reference 只能要求 logical effect identity 能到达真正负责 dedup 的 authority/sink；不能把责任留在 volatile worker memory 后声称问题已解决。

## 8. Failure domain 要从 dependency graph 走，不从 box 数量数

Reference 接受“worker crash不带 API crash”这个局部 isolation收益，但不把 process boundary = fault boundary 当定律。如果 authority、worker、metrics 全依赖同一个不可用 store，它们仍可能一起失效；failover 把流量推给容量不足的 pool，也可能扩大 blast radius。

因此任何 retry/failover proposal 都要问：

```text
failure
-> first reaction
-> new destination/dependency
-> capacity assumption
-> state uncertainty
-> recovery owner
-> final scope of impact
```

AWS cell guidance在这里提供 transfer case：真正 cell isolation需要 state/traffic/dependency grain 一致。TaskForge 当前没有 tenant/regional isolation requirement，所以 reference 不实现 cell；只保留 revisit trigger：当一个 authority/worker domain 的 blast radius 超过目标时，再设计 partition key 与对应 state ownership。

## 9. Independently deployed protocol 把 M08 带进 M09

Remote worker 一旦独立部署，原本同仓库的 function call 变成 long-lived protocol：

```text
Authority v2 <-> Worker v1
Authority v1 <-> Worker v2
```

Reference 不要求所有组合永久兼容，但要求 supported coexistence window、rollout/rollback order 和 unknown-version policy明确。`A6` 的意义不是喊 “N/N-1”，而是提醒：process split 同时创造 time-dimension coupling。

Snapshot v1 compatibility 同样必须保持；architecture refactor不能借机重写 M08 durable format contract。

## 10. Reference implementation 只验证 semantic seam，不实现 distributed system

Instructor 在**临时副本**中做过一个 boundary-enabling refactor，没有把它提交到 starter。

新增 `job_authority.py`，包含类似：

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

它仍使用现有 in-memory `state.jobs` representation。这是刻意的：M09 要验证 normal transition policy / direct-state dependency localization，不是 persistence mechanism，也不是 complete mutation-capability isolation。

Reference 将 normal paths `service.py`、`worker.py`、`metrics.py` 和 `legacy_audit.py` 改为通过 authority/service read path；`concurrent_claim.py` 保持 direct state mutation，因为它是 M07 historical fault-injection fixture。

因此 refactor 后 direct-state inventory 不是“整个 repo 只剩一个 import”，而大致是：

```text
concurrent_claim   # explicit historical exception
job_authority      # accepted normal authority implementation
```

这体现 fitness rule 必须同时有 invariant 和 scope。但这个 direct-state inventory 还有一个重要 blind spot：它看不见 capability alias。若 `job_authority.get()` / `claim_next()` 返回的仍是 `state.jobs[...]` 中同一个 mutable `Job`，caller 可以在不 import `state` 的情况下修改 authoritative lifecycle state。

因此下面的 reference evidence 只证明：normal transition implementation / direct-state imports 被 localize，worker-facing operation 不需要理解 storage mechanism。它**不证明** detached/read-only observation boundary，也不证明 complete mutation authority isolation。

这个 refactor**没有**解决：mutable-`Job` authority leakage（M02 residual）、durability、authority HA、production claim atomicity、lease/heartbeat、worker auth、RPC transport、remote version skew、crash recovery、exactly-once effect、multi-tenant isolation 或 cell partitioning。

## 11. Reference evidence：结构变了，prior behavior 仍要重新证明

临时 reference 实际跑过：

```text
-- core + M09 reference tests --
......... [100%]
```

即：

```text
6 original core tests
+ 3 M09 architecture tests
= 9 passed
```

新增 architecture tests 关注：

1. service + worker 通过同一个 authority seam 完成 submit -> claim -> finish；
2. normal product modules 不再 direct import state；
3. worker-facing semantic operation 不要求理解 storage mechanism。

它们没有测试“returned `Job` 是否 detached/read-only”。所以 9 passed 不能升级成 A5 已满足；这正是为什么本轮把 mutable-handle risk 明确留作 M02 residual，而不是给现有 evidence 一个更强的名字。

但 architecture refactor 不能只证明新 seam 自己能跑。Reference 还重跑了已有 evidence：

- M05 text dashboard：empty / queued / mixed fingerprints unchanged；
- M06 legacy audit：三个 characterized fingerprints unchanged；
- M07 deterministic race fixture：仍能稳定重现 two-success history；
- M08 compatibility：historical v1 fixture、current W1 -> frozen R1、known W2 break 与 future-version fail-closed 都保持。

M07 probe 仍然红旗式重现 race，看起来像“bug 没修”。在本课程 artifact scope 中它恰好证明 historical teaching fixture 没被 architecture cleanup 误伤。若要把这个 package 当真正 production package 发布，teaching fixture 是否应移出 production distribution 是另一项 packaging/authority decision。

M03 `mutation_probe.py` 则是另一个重要例子：它寻找 baseline source text 中的具体 mutation site。合法 architecture refactor 把代码移动后，它可能得到 `mutation site not found`。Reference 不为了保住 historical harness 而扭曲新 architecture；正确做法是标明 harness 适用 baseline，并在当前 phase 使用当前 evidence。

## 12. ADR reference：记录 trade-off，不把 candidate 写成永恒真理

一个够用的 record 可以是：

```markdown
ADR-0001 — Normal lifecycle transition logic routes through Job Authority

Status: Accepted

Context:
TaskForge is adding remote workers. Current normal paths mutate shared
in-memory Job state directly. Remote workers must not receive store-write
credentials.

Decision:
Normal product transition implementations and direct state access are routed
through the accepted authority seam. Workers depend on claim/finish semantics,
not storage representation. The authority may initially share a process with
API. This phase does not claim detached/read-only Job observation or complete
mutation-capability isolation for returned objects.

Alternatives considered:
1. Shared DB direct writes.
2. Per-worker replicated lifecycle state with reconciliation.

Consequences:
+ normal transition policy and storage knowledge are localized
+ worker privilege is reduced
- authority availability becomes consequential
- mutable observation handles remain a known M02 authority risk
- remote protocol needs timeout/retry/version semantics

Revisit triggers:
Reconsider partitioning/HA when measured throughput, recovery objectives, or
failure-isolation requirements exceed one authority domain.
```

ADR 的价值在 why / alternatives / consequences / revisit trigger。`Use PostgreSQL because robust` 不是本章想训练的 architecture reasoning。

## 13. Agent sequence：先恢复事实，再允许设计，再允许最小 change

Reference 给 Agent 的顺序是：

1. **Reconnaissance**：只读分类 product/read/teaching/migration paths；列 writers/readers；追 submit/claim/finish/cancel/snapshot/effect flows；标 current process boundary 与 unknowns。不要先提 target topology。
2. **Human-confirmed model**：确认哪些 requirement 真实、哪些 path 在 architecture scope 内。
3. **Design twice**：至少两个真实方案，逐项比较 authority、data/control flow、failure、compatibility、security、migration/rollback 与 complexity cost。
4. **ADR**：保存 accepted trade-off 和 revisit trigger。
5. **Small enabling change**：只做 semantic authority seam；不顺手加 RPC、DB、queue、DI framework、deployment manifest 或 speculative HA。
6. **Independent review**：重新读 code/probes，而不是接受 implementation Agent 的总结。

这比一句“把 TaskForge 设计成 scalable distributed architecture”更能约束 Agent pattern autocomplete。

## 14. Instructor grading judgment

高分答案不需要复制 reference topology。一个 shared-DB design 仍可能很好，如果它能说明 semantic authority 如何由 transaction/constraint/procedure承担，worker credential requirement怎样满足，schema coupling怎样管理，rollout/rollback怎样验证。

低分答案的共同点不是“选错 pattern”，而是没有 consequence model，例如：

```text
microservices 更 scalable，所以拆服务
```

却答不出谁拥有 truth、worker timeout意味着什么、snapshot 是不是 recovery source、authority挂了谁受影响、protocol怎样 version。

M09 最终训练的是：

```text
architecture decision
=
current evidence
+ consequential boundary
+ explicit authority
+ realistic alternatives
+ failure/evolution reasoning
+ migration path
+ evidence
```

当这些东西清楚时，diagram 才开始有意义。
