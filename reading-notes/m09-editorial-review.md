# M09 Editorial Review — Architecture 主线重写自审

> 这份记录用于让后续 reviewer 看清 scope、语义迁移、source/course 边界和自我修正。它不是 self-approval；最终是否 merge 仍需要独立 review。

## 1. Batch scope

本批只处理 M09：

- `modules/09-architecture-boundaries-dataflow-failure-domains.md`
- `labs/09-architecture-boundaries.md`
- `case-studies/m09/instructor-analysis.md`
- `reading-notes/m09-source-audit.md`
- 本 review record

不带入 M10。原因不是机械“一章一个 PR”，而是 M09 的主问题已经自成一个 reviewable semantic cluster：**从 current system facts 与 remote-worker pressure 推出 consequential boundaries / authority / failure / evolution model**。M10 转向 code review / change engineering 的 evidence process；混在一起会让 architecture design authority 和 review-process authority 互相遮蔽。

Merge base 是 `ac0e408`（M08 rewrite 已 merge）。

## 2. Baseline evidence before editing

真实 starter/probe 在 rewrite 前确认：

```text
core pytest: 6 passed

M09 architecture probe:
DIRECT STATE DEPENDENCIES = concurrent_claim, legacy_audit, metrics, service, worker
LIFECYCLE MUTATORS = concurrent_claim, service, worker
LONG-LIVED SURFACES = public_api, snapshot schema, audit output, external effect protocol
```

并重跑 M05–M08 probes：dashboard fingerprints、legacy audit fingerprints、M07 race/crash teaching phenomena、M08 historical snapshot/old-reader compatibility 全部保持 baseline。

关键 code facts：

- `state.py` 只有 in-memory `jobs` / `next_job_number`；它是 representation location，不自动成为 semantic owner；
- `service.py` direct write submit/cancel/reset；
- `worker.py` direct write claim/finish；
- `concurrent_claim.py` 是 M07 deliberate unsafe historical teaching path，另有 teaching-only `claim_owners`；
- `metrics.py` / `legacy_audit.py` direct read state；
- `snapshot.py` 可以 export current state 和 parse snapshot DTO，但**没有 restore current authority/state 的 path**；
- `effect_delivery.py` 的 completion set 是 process-local，`SimulatedCrash` 是 same-process failpoint。

因此 baseline 不能被概括成“已经有 Job Authority + durable store”。更准确的是：

```text
shared in-process representation
+ multiple semantic writers
+ long-lived external/format surfaces
+ no implemented durable Job authority
```

## 3. Why the remote-worker case is the new spine

Merge-base M09 从 architecture definition、significance heuristic、boundary taxonomy 开始，再到 TaskForge target。对已学过 M01–M08 的读者，内容正确但 cold-reader pressure 较弱：读者先收到很多 architecture vocabulary，之后才知道为什么本系统需要它。

Rewrite 先放入已有 Lab requirement：worker 必须能运行在另一台机器，worker crash 与 API process 隔离，worker 不能持有 durable-store direct-write credential，timeout 不证明 command 未执行。

这个 requirement 连续制造两次失败：

1. current `worker.py -> state.jobs` 无法跨 process/machine；
2. “那就让 worker 直接写 shared DB”又撞上 credential requirement，并保留 split semantic-authority risk。

到这时读者才需要回答：谁拥有 lifecycle truth、什么应该跨 network、什么 representation 不应跨、failure/privilege 应怎样隔离。Semantic/process/deployment/failure boundary 因此由 problem pressure earned，而不是开场定义。

## 4. Old 40-section surface → new reasoning clusters

不是逐标题模板化，但语义 surface 映射如下：

- old §1–§3 architecture/importance/consequential boundaries → new §1–§3；
- old §4–§7 semantic/process/deployment/failure boundary、process premium、monolith/microservice → new §3；
- old §8–§12 authority/storage/snapshot/runtime/read model → new §4–§8；
- old §13–§18 failure domain、containment、retry/failover、protocol compatibility、security/team boundary → new §6、§8–§12；
- old §19–§20 multi-view / diagram lies → new §12；
- old §21–§23 design twice / invariants / fitness function → new §5、§13；
- old §24–§25 probe + historical teaching exception → new §1、§13；
- old §26–§30 ADR / evolution / avoid future-proof / risk register → new §14；
- old §31–§35 review / Agent failure / reconnaissance / design / independent review → new §15–§16；
- old §36–§39 target architecture / minimal refactor / habits / prior-module integration → integrated into new §5、§15–§17；
- old §40 M10 preview was navigation, not a M09 technical contract; it was not preserved as a standalone section.

Two baseline concepts were initially compressed too aggressively during the first rewrite draft and were restored after semantic sweep without restoring atomic sections:

- read-model replication != writer-authority replication；
- architecture risk register as a compact way to expose assumptions/known gaps.

## 5. Curriculum completion vs semantic preservation

`COURSE_DESIGN.md` explicitly lists two M09 core concepts that merge-base artifacts did not adequately teach:

```text
control plane / data plane
dependency inversion 的真实用途
```

This is **baseline curriculum debt**, not merely rewrite preservation. The rewrite therefore did provenance work before adding them.

### Dependency inversion

New source audit entry: Brett Schuchert, *DIP in the Wild* on MartinFowler.com.

Source-backed boundary used by M09:

- high-level policy should not depend on low-level detail；
- dependencies should point toward domain-relevant abstraction；
- DIP is not identical to Dependency Injection / IoC；
- abstraction has context/cost and should not be applied ceremonially.

TaskForge mapping is course application:

```text
worker -> jobs table / DB credential / storage representation
```

versus

```text
worker -> claim / finish / heartbeat semantics
       -> authority hides storage detail
```

The source does not prescribe `Job Authority` or this exact architecture.

### Control plane / data plane

Added AWS fault-isolation control/data-plane source alongside existing AWS cell material.

Source-backed: terms originate in networking; control plane creates/modifies rules/resources/orchestration, data plane performs primary service work; the planes may have different availability/complexity profiles.

Course synthesis: TaskForge's lifecycle/control authority vs command/data-execution responsibility is an **analogy/lens**, not a claim that TaskForge has canonical AWS/network planes or must deploy separate control/data services.

## 6. Abstraction-dependency sweep

The current ordering is intentional:

1. remote worker breaks direct shared-memory dependency；
2. shared-DB shortcut exposes credential + authority problem；
3. only then define architectural significance and boundary types；
4. ask what worker should depend on, then name dependency inversion；
5. compare A/B/C before accepting `Job Authority` reference direction；
6. only after responsibilities exist use control/data-plane lens for privilege/failure；
7. inspect state/snapshot/effect authority；
8. run normal/failure-path flow；
9. then generalize to failure domains/cells/cascading failure；
10. independent deployment earns protocol-version compatibility；
11. evidence/views/ADR follow once a design decision exists.

This avoids opening with microservices, DI, CQRS, control plane, cell architecture, or ADR vocabulary.

## 7. Design-decision / authority sweep

### Job Authority

`Job Authority` is consistently a **reference/target candidate**, not current TaskForge fact. The module states that `job_authority.py` does not exist in starter; instructor reference implementation happened only in a temporary copy.

The candidate is earned by stated remote-worker authority/credential requirements and compared against real alternatives. Shared DB direct coordination is not declared universally wrong; its direct-write variant conflicts with this exercise's worker credential requirement, while other shared-DB authority designs may be legitimate under different constraints.

### Durable store

Starter does not have durable Job storage. Target diagrams that mention a store are explicitly future roles/placeholders. Lab now warns that drawing `durable Job Store` does not establish durability.

### Snapshot

Current `snapshot.py` is classified from code: derived durable export / compatibility surface. It parses files into DTOs but has no restore-to-authority path. Recovery-source semantics are future design requiring new durability/restore/reconciliation contracts.

### Control/data plane

Not promoted into required topology. It is only an analysis lens for privilege, availability and failure coupling.

### DIP

Not promoted into “all layers need interfaces” or a DI framework requirement. Lab explicitly asks whether low-level storage knowledge actually disappeared.

### Cell / HA / partitioning

Not current target implementation. They remain future revisit options when measured blast-radius/throughput/recovery requirements justify them.

## 8. State/model projection sweep

M09 has several partial models that could accidentally masquerade as complete architecture.

### Probe writer/import inventory

The AST probe inventories source dependencies/mutations. It does not distinguish normal product, reporting, historical teaching, migration or emergency scope by itself. Therefore `5 direct imports` is evidence, not an architecture score.

### Boundary table

Semantic/process/deployment/failure/security boundaries are reasoning dimensions, not claim that every system has five independent components.

### Five architecture views

Responsibility, authority/state, runtime, failure and evolution views are projections for different questions. They are not five layers of one canonical architecture.

### Read models

Read API/snapshot/replica may be copied without copying lifecycle write authority. `one semantic write authority + many derived read models` is a simplification candidate, not a universal CQRS law.

### Historical exception

`concurrent_claim.py` stays visible in architecture inventory but is explicitly M07 fault-injection scope. A whole-repo “no state import” fitness rule would be a wrong projection of normal product-path authority policy.

## 9. Temporal-consistency sweep

M09 inherits M07/M08 temporal contracts and must not flatten them into topology statements.

- worker timeout -> caller uncertainty, **not** proof command did not execute；
- effect success + lost finish -> duplicate window remains；authority boundary alone does not produce exactly-once；
- worker process death -> process isolation, **not** automatic safe requeue；lease/recovery remains future work；
- authority process death -> lifecycle write outage; current starter memory means restart reconciliation is not solved；
- process split -> independent version skew, so worker protocol gains an explicit coexistence / rollout / rollback policy obligation；`N/N-1` is one possible policy, not an automatic MUST；
- snapshot export on disk -> durable artifact, **not** durable lifecycle authority/recovery truth；
- moving normal transition code/direct-state access behind one module -> locality, **not** proof that production claim is atomic under concurrency or that all mutation capability is isolated；
- a returned live mutable `Job` can remain an authority-bearing handle even when its caller never imports `state.py`; direct-import fitness evidence cannot close that M02 property.

These qualifiers are repeated in module, Lab and instructor case where normative exercises could otherwise overclaim.

## 10. Source/provenance boundary

Main source responsibilities after this pass:

- SEI: architecture as structures needed for reasoning；
- Fowler/Ralph Johnson: important design elements / evolution framing, not a metric formula；
- Stanford CS190/Ousterhout: information leakage / knowledge locality / modular design；
- AWS cells: scope of impact / real isolation boundary；
- AWS control/data planes: source terminology; TaskForge mapping remains course synthesis；
- Google SRE: cascading failure, retry/failover/capacity coupling；
- Fowler `Monolith First`: service premium / stable boundary experience, not universal monolith-first law；
- Schuchert `DIP in the Wild`: dependency direction and anti-ceremony qualifiers；
- Fowler ADR: concise consequential decision record / alternatives / consequences / history；
- Parnas 1972 remains historical pointer, not falsely upgraded to a primary-audited authority.

Course synthesis / repo-specific reasoning includes the consequence heuristic, `Architecture = Consequential Boundaries`, five-view set, TaskForge authority candidate, target invariants, risk register, fitness-rule scope, control-vs-execution mapping, and Agent workflow.

## 11. Self-corrections during rewrite

1. **Curriculum debt — DIP**：merge-base had no real teaching payload despite `COURSE_DESIGN.md`; added audited source and case-earned treatment rather than a SOLID appendix.
2. **Curriculum debt — control/data plane**：baseline only used the phrase loosely; added AWS provenance and explicit TaskForge-as-analogy qualifier.
3. **Current-vs-target durability**：Lab target diagram says `durable Job Store`; added explicit warning that current starter is memory and diagram does not create a guarantee.
4. **`state.py` authority wording**：source-audit teaching-target inventory changed from `mutable lifecycle truth` to `shared mutable lifecycle representation`, because storage location is not semantic owner.
5. **Read-model compression**：first rewrite draft reduced old read-model/writer-authority distinction to one list; restored a compact explicit explanation.
6. **Risk-register compression**：restored compact risk/mechanism/evidence table so known gaps remain reviewable.
7. **ADR Markdown hygiene**：fenced ADR examples originally used `#` / `##`, creating false H1/H2 counts in simple structure checks; converted example labels to plain text without changing content.
8. **PR #14 authority review**：independently reproduced the mutable-`Job` alias capability leak and rechecked M02/M10; narrowed M09 from “single authority established” to normal transition-policy/direct-state localization, while recording complete mutation-capability isolation as a residual M02 risk rather than adding `JobView`.
9. **PR #14 compatibility review**：independently confirmed module/case already treat `N/N-1` as a policy choice; removed the Lab-only MUST and restored an explicit supported coexistence policy/matrix obligation.

## 12. Cold-reader / rhythm review

Merge-base module was ~1800 lines and 40 page-level H1 sections. Rewrite is ~430 lines with one real H1 and a continuous case spine. Tables/fences remain only where structure genuinely helps: boundary/alternative/risk matrices, code/probe output, flows and Agent/ADR artifacts.

The chapter no longer asks the reader to retain a long architecture vocabulary list before seeing a system problem. Transfer material (cells, compatibility, team boundary, ADR) appears after the TaskForge case has earned the relevant question.

## 13. Final validation evidence

Initial rewrite 与 PR #14 authority/compatibility follow-up 后都实际重新运行；以下结果在 follow-up 后再次确认：

```text
cd labs/taskforge
PYTHONPATH=src uv run --with pytest --no-project python -m pytest -q
=> 6 passed

PYTHONPATH=src uv run --with pytest --no-project python tools/m09_architecture_probe.py
=> direct state deps unchanged: concurrent_claim, legacy_audit, metrics, service, worker
=> lifecycle mutators unchanged: concurrent_claim, service, worker

M05 behavior probe
=> empty / queued / mixed fingerprints unchanged

M06 legacy probe
=> empty / mixed / append fingerprints unchanged

M07 interleaving probe
=> two-success race, final-state masking, crash duplicate, record-first loss all reproduced

M08 compatibility probe
=> v1 historical fixture readable
=> current W1 accepted by frozen R1
=> known W2 -> R1 break reproduced
=> current starter R1 rejects W2
=> future version fail-closed
=> historical fixture sha256 = 0cd8f674d54b3da7919c2a9f7b911fdea5b109399438595c471a6baee90d2ecc
```

Hygiene / structure：

- `git diff --check` PASS；
- changed Markdown fences balanced；
- changed relative Markdown links resolve；
- module 442 行、1 个 H1、0 个 page-level `---`；
- instructor case 410 行、1 个 H1、0 个 page-level `---`；
- `COURSE_DESIGN.md` M09 core sweep covers architectural significance/reversal consequence、process/network boundary、storage/durability boundary、data ownership、failure domain、control plane/data plane、dependency inversion；
- current-vs-target overclaim sweep found no stale claim that starter already has Job Authority/durable store/recovery source, that direct-import localization proves complete mutation-capability isolation, that timeout proves non-execution, or that N/N-1 is a universal MUST；
- Markdown secret scan 无 finding；
- 无新增 `uv.lock` / temp artifact。

Because no TaskForge teaching code/fixture changed, unchanged M05–M09 executable evidence is also the intended scope check: this batch rewrites and tightens teaching authority rather than silently implementing the target architecture.

## 14. Independent reviewer focus

This record is not self-approval. Reviewer should independently test at least:

- whether remote-worker/shared-DB pressure genuinely earns boundary vocabulary before abstraction appears；
- whether `Job Authority` ever slips from candidate/reference direction into current fact or universal design law；
- whether current in-memory state and snapshot export are ever over-described as durable/recovery authority；
- whether dependency inversion is taught as dependency shape rather than interface/DI ceremony；
- whether control/data-plane language is sufficiently scoped as TaskForge course adaptation；
- whether Design B/C remain real alternatives rather than strawmen；
- whether worker timeout/effect/lost-finish/authority-crash semantics remain consistent with M07；
- whether process split correctly inherits M08 version-skew/rollback obligations；
- whether failure-domain/cell discussion is useful transfer rather than speculative architecture；
- whether fitness rules distinguish normal product path from historical teaching/repair/migration exceptions **and** stay scoped to direct-state localization rather than claiming capability isolation；
- whether returned mutable `Job` handles are explicitly treated as residual M02 authority risk rather than hidden by import-topology evidence；
- whether worker protocol requires an explicit supported coexistence policy/matrix without hard-coding N/N-1 as universal support contract；
- whether read-model replication / writer authority and risk-register semantics survived compression；
- whether any old M09 qualifier, non-goal or source limitation disappeared in the 1800 -> ~430 line rewrite.

## 15. PR #14 review 后的独立复核

Reviewer 的两条 finding 没有直接照单全收；本轮重新对了真实 starter、M02 authority contract、M10 downstream teaching seam，以及 M08/M09 compatibility chain。

### Authority localization vs mutation-capability isolation

真实 starter 独立复现：

```text
claimed is service.get(jid) => True
claimed.status = SUCCEEDED
service.get(jid).status => succeeded
```

因此 `Job` 确实是 authority-bearing mutable handle。M02 明确教过：read/observation 不应无意授予 authoritative mutation authority；而 M10 instructor case 又明确把 `service.get()` 继续返回 mutable `Job` 视为既有 M02 issue，并把后续 candidate 的 scope 定义为 authority localization。两者共同说明：M09 不应为了把一句 invariant“做真”而新增 `JobView`，也不应把 `no direct state import` 证据夸成 complete authority isolation。

最终 artifact chain 统一成：

- target architecture 可以要求 normal product transition policy 收敛到明确 semantic authority；
- M09 minimal refactor 证明 normal transition logic/direct-state access localization 与 worker storage-knowledge removal；
- historical `concurrent_claim.py` 仍是 named exception；
- mutable observation/claim handle 可能继续泄漏 mutation capability，明确作为 residual M02 risk / non-goal；
- 如果未来要声称 A5 已实现，需要 capability-focused evidence（detached/read-only view、defensive copy 或其他机制只是候选，不是本轮强制设计）。

### Compatibility policy

Module 已写“`N/N-1` 是否支持”需要决定并先定义 supported coexistence matrix；instructor case 也明确说 A6 的意义不是喊 `N/N-1`。只有 Lab 把它升级成 MUST，因此这次只修 Lab artifact drift：独立部署带来的 obligation 是**明确支持矩阵/窗口、rollout/rollback 与 unknown-version policy**，而不是默认 N/N-1 一定互通。

本轮没有新增/修改 TaskForge production teaching code，没有引入 `JobView` 或 capability-isolation test，也没有修改 M02/M10。这样既修正 M09 自己的 authority claim，又保留 M10 对同一 residual issue 的后续 review 教学。
