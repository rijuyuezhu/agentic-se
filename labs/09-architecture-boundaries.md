# Lab 09 — Architecture：从“很多模块”到可推理的系统边界

> 本实验不是画一张漂亮的大图。
>
> 你要做的是：从 TaskForge 已有代码恢复真实 architecture，比较两个 target design，写出 architecture invariants，再做一个最小 boundary-enabling refactor。

---

# 0. 规则

本实验有几个强制约束：

1. **先只读恢复 current architecture，不先提 microservices。**
2. 必须区分 semantic / process / deployment / failure boundary。
3. 必须区分 source of truth / durable storage / snapshot / read model。
4. 至少设计两个 target architecture。
5. 所有 infrastructure choice 必须对应明确 requirement。
6. architecture decision 必须包含 migration / rollback consequence。
7. 最终 implementation 只做最小 authority-boundary refactor；不实现 HTTP/Postgres/message queue。
8. 不允许为了减少 grep 数量破坏 M07 的教学 fault-injection module。
9. Agent 只能在 reconnaissance 完成后进入 design/implementation。
10. 最后必须独立 review，而不是复述 Agent summary。

---

# 1. Baseline

进入：

```bash
cd labs/taskforge
```

运行：

```bash
PYTHONPATH=src uv run --with pytest --no-project python -m pytest -q
```

预期：

```text
6 passed
```

再运行 architecture inventory：

```bash
PYTHONPATH=src uv run --with pytest --no-project python tools/m09_architecture_probe.py
```

当前 baseline 应看到：

```text
[DIRECT STATE DEPENDENCIES]
concurrent_claim, legacy_audit, metrics, service, worker

[LIFECYCLE MUTATORS]
concurrent_claim, service, worker
```

这只是事实，不是结论。

---

# 2. 先做 Source Classification

把 `src/taskforge/*.py` 分成：

```text
product normal path
external/public surface
read-only/reporting path
historical teaching/fault-injection path
migration/compatibility artifact
```

至少分类：

- `service.py`
- `worker.py`
- `metrics.py`
- `public_api.py`
- `snapshot.py`
- `legacy_audit.py`
- `concurrent_claim.py`
- `effect_delivery.py`

特别解释：

```text
concurrent_claim.py
```

为什么不能因为它 direct-write state 就立刻“统一修掉”？

提示：它当前承担 M07 的 deterministic race teaching role。

真实项目中的对应物可能是：

- migration tool；
- repair utility；
- test harness；
- deprecated compatibility shim；
- emergency admin command。

---

# 3. Current Architecture — 五张小图

不要画一张万能图。

## 3.1 Responsibility / Knowledge View

填写：

| Module | Unique knowledge | Leaked knowledge |
|---|---|---|
| service | ? | ? |
| worker | ? | ? |
| snapshot | ? | ? |
| effect_delivery | ? | ? |

问：

- lifecycle transition knowledge 出现在哪里？
- storage representation knowledge 出现在哪里？
- snapshot schema knowledge 出现在哪里？

---

## 3.2 Authority / State View

列出：

| State | Semantic authority | Storage | Other writers/readers |
|---|---|---|---|
| job lifecycle | ? | `state.jobs` | ? |
| next id | ? | `state.next_job_number` | ? |
| snapshot | ? | JSON file | ? |
| effect completion | ? | local set | ? |

然后明确回答：

> 当前 Job lifecycle 是否真的有单一 authority？

不要只回答“state.py”。

---

## 3.3 Runtime View

画：

```text
submit
claim
finish
cancel
snapshot
external effect
```

标出谁调用谁、什么 data 移动。

---

## 3.4 Failure View

至少分析：

```text
API process crash
worker crash
snapshot write failure
external sink timeout
storage unavailable
```

当前 system 还没有真正 durable authority，因此你可以明确写：

```text
not yet modeled
```

不要编造 capability。

---

## 3.5 Evolution View

结合 M08：

- snapshot v1 producer/consumer；
- future remote-worker protocol；
- public API；

哪些会出现 independent version skew？

---

# 4. 新需求

产品现在提出：

> TaskForge 要支持在另一台机器上执行 job。

具体要求：

1. API/control component 与 worker 可以运行在不同机器；
2. worker crash 不应让 API 进程一起 crash；
3. target architecture 的 normal product transition policy 必须收敛到一个明确 semantic authority；current starter 并不满足这一点；
4. remote worker 不得获得 durable-store direct-write credential；
5. snapshot v1 compatibility surface 暂时保留；
6. 一次 worker network timeout 不能自动等价为“job 没执行”；
7. 系统当前规模很小，没有 multi-region / million-QPS requirement；
8. metrics 和 audit 不需要独立 scale；
9. 本轮只设计 architecture，不实现 network stack。

---

# 5. 设计两个 Architecture

必须至少做 A/B 两案。

## Design A — Central Semantic Authority + Remote Worker Protocol

建议起点：

```text
client
  |
  v
API + Job Authority ---- durable Job Store
        |
        | claim / finish protocol
        v
remote worker
        |
        v
external effect
```

注意：`Job Authority` 与 `durable Job Store` 都是 **target-design roles**，不是 starter 已经实现的 component/guarantee。Authority 可以先与 API 同进程；当前 starter 仍只有 in-memory `state.jobs`，不要因为画了 store box 就声称已有 durability。

再做两个额外检查。

**Dependency inversion check**：remote worker 应依赖哪个层级的 contract？比较 `worker -> jobs table / DB credential / storage schema` 与 `worker -> claim / finish / heartbeat semantics`。如果你的答案只是“加一个 StoreInterface / DI container”，继续说明 low-level storage knowledge 是否真的从 worker 消失。DIP 在本 Lab 中不是 interface 数量指标。

**Control/data-plane lens**：可以把 lifecycle/control authority 与 command execution 看成 control responsibility 和 data/execution-plane-like responsibility，但必须注明这是 TaskForge 的课程映射，不是要求复制网络/AWS topology。说明这个 lens 对 privilege 与 failure analysis增加了什么，以及哪些 dependency 会让两个 plane 仍然一起失败。

你要分析：

- authority；
- process boundary；
- worker failure；
- store failure；
- version skew；
- security boundary；
- future scale pressure。

---

## Design B — Shared DB Coordination

```text
API --------\
scheduler ----> jobs table
worker ------/
```

也认真分析，不许 strawman。

它可能有真实优点：

- 少一个 service protocol；
- database transaction 可作为 claim primitive；
- 小团队实现简单。

但也要分析：

- schema coupling；
- credential exposure；
- semantic rule duplication；
- independent deployment；
- worker compromise blast radius。

---

# 6. Optional Design C — Replicated Per-Worker State

如果你愿意，再设计：

```text
API state
worker A state
worker B state
sync/event reconciliation
```

但必须回答：

```text
为什么需求值得支付 reconciliation complexity？
```

如果答不出来，可以明确 reject。

---

# 7. Decision Matrix

至少包含：

| Dimension | A | B | C(optional) |
|---|---|---|---|
| lifecycle authority clarity | | | |
| worker dependency on domain contract vs storage detail | | | |
| worker compromise blast radius | | | |
| partial failure model | | | |
| versioning cost | | | |
| implementation cost now | | | |
| storage portability | | | |
| rollback complexity | | | |
| future partitioning path | | | |

不能只写：

```text
A cleaner
B simpler
```

每格都要回到 mechanism/consequence。

---

# 8. 写 Architecture Invariants

至少写 6 条。

reference direction：

```text
A1. Normal product transition decisions are routed through Job Authority;
    named historical/fault-injection paths remain explicit exceptions.
A2. Remote workers never mutate durable Job state directly.
A3. Worker timeout does not itself prove execution absence.
A4. Snapshot remains a derived export in this phase.
A5. Read/reporting paths should not acquire lifecycle mutation capability
    through authority-bearing mutable handles.
A6. Independently deployed authority/worker versions require an explicit
    supported coexistence policy/matrix.
```

这些是 target/reference properties，不是“做完最小 refactor 就全部被证明”的 acceptance checklist。尤其 A5 比 `no direct state import` 更强：如果 `get()` / `list_jobs()` / `claim_next()` 仍返回 authoritative mutable `Job`，caller 即使不 import `state.py`，也可能经 alias 获得 mutation capability。M02 已经把这类 handle 识别为 authority leak。

本轮最小 implementation **不要求**顺手引入 `JobView`、defensive copy 或其他 observation redesign；因此它只能证明 normal transition logic / direct-state access 的 localization，以及 worker 不再需要 storage knowledge。完整 mutation-capability isolation 是明确的 residual M02 risk / follow-up。A6 同理只要求明确 coexistence policy；`N/N-1` 可以是其中一个合理选择，但不是自动成立的 MUST。

你可以不同意其中某条，但必须给替代模型。

---

# 9. 写 Failure Walk

对下面每个 failure：

```text
worker process dies
worker loses network after command starts
Job Authority dies
store unavailable
external effect succeeds but finish message is lost
bad worker version deployed
```

写：

```text
initial failure
→ first reaction
→ retry/failover
→ additional load
→ state uncertainty
→ recovery owner
→ blast radius
```

M07 的结论在这里必须复用。

---

# 10. 明确 Snapshot Role

当前 `snapshot.py` 只是：

```text
current state -> JSON
```

本轮必须选：

```text
A. derived export
B. recovery source
C. live coordination mechanism
```

reference 建议本轮选 A。

理由不是“简单”，而是：

当前还没有：

- atomic durable store contract；
- crash-consistent snapshot write；
- restore lifecycle；
- stale-snapshot reconciliation。

如果你选 B/C，必须设计这些东西。

---

# 11. 写 ADR

创建你自己的：

```text
doc/adr/0001-job-lifecycle-authority.md
```

不要提交到课程 starter；这是实验产物。

模板：

```markdown
# ADR-0001 — <decision>

Status: Proposed / Accepted

## Context

## Decision

## Alternatives considered

## Consequences

## Risks

## Revisit triggers
```

限制：

- 1–2 页；
- 不写 architecture textbook；
- 不写 vendor marketing；
- alternatives 必须真实可行；
- 至少一个负面 consequence；
- 至少一个 revisit trigger。

---

# 12. Implementation Phase：只做一个 Architecture-Enabling Refactor

目标：

> normal product transition implementation 不再由 `service.py` / `worker.py` 直接访问和修改 `state` representation；transition policy / direct-state access 收敛到明确 semantic seam，worker 不再需要 storage knowledge。

这不是“所有 mutation capability 都已隔离”的同义词。如果 authority/service 仍把 authoritative mutable `Job` reference 返回给 caller，caller 仍可能绕过 semantic operation 直接改 state。这个 M02 residual risk 本轮明确不靠新增 `JobView` 等机制解决。

推荐做法：

新增：

```text
src/taskforge/job_authority.py
```

它暂时仍然可以使用现有 in-memory representation。

最少需要 semantic operations：

```text
submit(command)
get(job_id)
list_jobs()
cancel(job_id)
claim_next()
finish(job_id, exit_code)
reset_for_tests()
```

然后：

```text
service.py
worker.py
metrics.py
```

改为通过 authority。

`public_api.py` / `snapshot.py` 本来通过 service，可继续。

`legacy_audit.py`：

你要自己判断：

- 本轮一起迁移成 read path；
- 还是保留为 documented legacy exception。

`concurrent_claim.py`：

**不要机械迁移。**

它是 M07 historical fault-injection artifact。

你可以：

- 保留 direct state dependency，并在 architecture scope 里列为 explicit exception；
- 或复制一个新的 production claim path，而不破坏历史 probe。

---

# 13. Dependency inversion 也不等于“现在就建十个 Interface”

本章确实要求你理解 dependency inversion 的实际用途：high-level lifecycle/execution code 应依赖 domain-relevant contract，而不是 storage representation。但这**不等于**现在必须实现 Store Interface + RPC Interface + Repository + DI framework。

因为你还没有需要那么多 layers 的 evidence。

本实验只要求：

```text
normal transition policy / direct-state access
becomes localized behind an explicit semantic seam
```

不要把这个 structural move 升级成 complete authority isolation。`get()` / `list_jobs()` / `claim_next()` 是否泄漏 authoritative mutable handle 是另一条 capability property；M02 已经定义它，本轮只把它记录为 residual risk，而不扩大 implementation scope。

未来：

```text
in-memory storage
→ SQLite
→ remote DB
```

可以在 authority 后演化。

不要今天为了明天的可能性建十个 abstractions。

---

# 14. Architecture Fitness Check

refactor 后写一个小检查。它的 scope 是 **direct-state dependency localization**，不是 complete mutation-capability isolation。

例如：

```text
normal product modules:
  service.py
  worker.py
  metrics.py

must not import taskforge.state
```

这个 check 能证明 normal modules 不再直接依赖 `state` namespace；它**不能**证明 caller 没有通过 live mutable `Job` alias 获得 write capability。若本轮真的要声称 A5 已被 implementation 满足，就需要额外的 M03-style capability evidence，能够区分 detached/read-only observation 与 authority-bearing handle。本 Lab 刻意不把这项 redesign 加进最小 refactor。

不要检查：

```text
all files in repo must not import state
```

因为这会错误杀掉历史 teaching artifact。

你的 fitness function 必须表达**architecture scope**。

---

# 15. Behavior Evidence

至少跑：

```bash
PYTHONPATH=src uv run --with pytest --no-project python -m pytest -q
```

还要跑：

```bash
PYTHONPATH=src uv run --with pytest --no-project python tools/m05_behavior_probe.py
PYTHONPATH=src uv run --with pytest --no-project python tools/m06_legacy_probe.py
PYTHONPATH=src uv run --with pytest --no-project python tools/m07_interleaving_probe.py
PYTHONPATH=src uv run --with pytest --no-project python tools/m08_compat_probe.py
```

但要注意：

`mutation_probe.py` 是 M03 对具体 baseline source text 的 historical teaching harness，可能因为 architecture refactor 的合法 source transformation 找不到 mutation site。

不要为了保持它而扭曲新 architecture。

正确处理：

```text
classify historical harness
record why no longer applicable
```

这本身就是 architecture/evolution reasoning。

---

# 16. Evidence Table

交付：

| Claim | Evidence |
|---|---|
| core behavior preserved | pytest |
| text dashboard unchanged | M05 fingerprints |
| legacy audit observable behavior preserved | M06 probe |
| M07 fault-injection artifact intentionally preserved | M07 probe |
| v1 snapshot compatibility preserved | M08 probe |
| normal product path no direct state import | architecture fitness check |
| complete mutation-capability isolation | **not established by this minimal M09 refactor**；record as residual M02 risk |

---

# 17. Agent Reconnaissance Prompt

先给 Agent：

```text
Read-only architecture reconnaissance.
Do not propose a target architecture and do not edit files.

For TaskForge:
1. classify runtime/product/test/teaching/migration modules;
2. list every direct state reader and writer;
3. identify lifecycle authority actually implemented today;
4. trace submit/claim/finish/cancel/snapshot/effect flows;
5. identify long-lived contracts;
6. identify current process/deployment boundaries (do not invent any);
7. identify failure-path dependencies;
8. list architectural unknowns that materially affect remote-worker design.

Support claims with file/line evidence.
```

审阅 Agent 是否：

- 把 `state.py` 错当 owner；
- 把所有 source files 当同种 runtime role；
- 根据 module names 猜 dependency；
- 偷偷开始画 target architecture。

---

# 18. Agent Design Prompt

第二轮：

```text
Using the confirmed system model, design two architectures for remote workers.

Requirements:
- normal product transition policy converges on one semantic lifecycle authority;
- named historical/fault-injection exceptions remain explicit;
- worker runs on another machine;
- worker crash isolated from API process;
- worker has no direct durable-store write credential;
- no multi-region or extreme-scale requirement;
- snapshot v1 remains supported;
- network timeout does not prove non-execution.

For each design provide:
- semantic boundaries;
- process/deployment boundaries;
- authority/state model;
- normal and failure data/control flow;
- failure domains;
- compatibility consequences;
- migration and rollback path;
- operational evidence;
- concrete complexity cost.

Do not add infrastructure without tying it to a stated requirement.
```

---

# 19. Agent Implementation Contract

只在 design review 后：

```text
Implement the accepted authority-boundary refactor only.
Do not add network, database, message queue, framework, DI container, or deployment manifests.

Localize normal transition policy/direct-state access behind the accepted semantic seam.
Make normal worker code depend on lifecycle semantics rather than storage representation;
do not satisfy this by merely wrapping the same storage detail in a new interface.
Do not claim that this proves detached/read-only Job observation or full mutation-capability isolation,
and do not add JobView/copying solely to close that residual M02 issue in this phase.
Preserve existing observable behavior.
Keep the M07 fault-injection module as an explicit historical exception.
Add a small direct-state architecture fitness test for normal product modules.
Run core tests and M05-M09 probes.
```

---

# 20. Independent Review

reviewer 不看 Agent summary，自己检查：

## Architecture

- normal transition policy / direct-state access 是否真的 localize 到 accepted seam？
- storage knowledge 是否仍从 normal worker path 泄漏？
- `get/list/claim` 是否仍返回 authority-bearing mutable handle？如果是，是否诚实记录为 residual M02 risk，而不是误称 complete authority isolation？
- worker 是否只是换了一个名字继续写 representation？
- snapshot role 是否明确？
- historical exception 是否 document？

## Change

- 有没有顺手引入 repository/DI framework？
- 有没有改变 public behavior？
- 有没有破坏 prior compatibility fixture？
- 有没有把 M07 teaching artifact 当 production bug 修掉？

## Future

- 换 SQLite/Postgres 时 worker 是否需要知道？
- 真正加 RPC 时 semantic API 是否已经足够清楚？
- authority outage 现在还是 single failure domain，是否被明确接受？

---

# 21. Grading

总分 100。

## 25 — Current architecture recovery

- source classification；
- five views；
- actual authority / dependency evidence。

## 20 — Alternative design quality

- 至少两个真实 alternatives；
- 不 strawman；
- consequence-based comparison。

## 20 — Failure / evolution reasoning

- failure walk；
- rollout / rollback；
- protocol versioning；
- blast radius。

## 15 — Architecture invariants / ADR

- stable consequential rules；
- ADR 有 context / alternatives / consequences / revisit trigger。

## 10 — Minimal implementation

- authority boundary 清楚；
- 不 overbuild。

## 10 — Evidence / Agent orchestration

- prior behavior evidence；
- architecture fitness check；
- independent review。

---

# 22. 本章不按这些东西加分

不会因为你：

- 画了更多 boxes；
- 使用 Kubernetes；
- 写了 20 页 architecture doc；
- 套了 Clean Architecture 名词；
- 引入 Kafka；
- 把所有文件都变成 interface；
- 写了 30 个 ADR；

就得高分。

真正评分的是：

> **你的 system model 是否能解释 authority、change、failure、compatibility 和 future evolution。**

---

# 23. 最后问题

完成后，不看你的图，尝试只用 90 秒回答：

```text
TaskForge 里 Job truth 是谁拥有的？
worker 能做什么、不能做什么？
snapshot 是什么、不是什麼？
worker 挂了谁受影响？
authority 挂了谁受影响？
以后把 worker 移到远端，新增的最主要 distributed contracts 是什么？
为什么现在没有把 metrics/audit 各拆成 service？
什么条件出现时你会重新考虑当前 architecture？
```

如果这些答不清楚，architecture 还没有真的形成 shared mental model。
