# M09 — Architecture：哪些边界值得上升到系统级

前八章一直在处理局部 engineering contract：状态归谁写、边界怎样翻译错误、并发 history 怎样才合法、旧数据和新 reader 怎样共存。M09 不突然切换成“背架构模式”。我们给 TaskForge 加一个需求，然后看哪些局部选择被迫变成系统级决定。

需求很简单：**job 要能在另一台机器上执行。** API/control component 和 worker 可以分居两台机器；worker crash 不能带着 API 一起 crash；remote worker 不能拿 durable-store direct-write credential；一次 network timeout 也不能被解释成“command 一定没有执行”。系统仍然很小，没有 multi-region、million-QPS 或把 metrics/audit 独立扩容的要求。

这组条件看起来像 deployment work。真实 starter 很快告诉我们，它首先是 architecture work。

## 1. 把 `worker.py` 搬走以后，第一条调用就失效了

当前 `worker.py` 的 claim 并不是通过某个远程 contract 完成的。它直接遍历进程内的 `state.jobs`：

```python
for job in state.jobs.values():
    if job.status == JobStatus.QUEUED:
        job.status = JobStatus.RUNNING
        return job
```

`finish()` 也直接取出同一个 mutable `Job`，检查它当前是 `RUNNING`，然后写 `exit_code` 和 terminal status。`service.py` 同样直接分配 ID、插入 job、执行 cancel；M07 的 `concurrent_claim.py` 则故意保留另一条 direct mutation path，用于重现 race。

M09 的 baseline probe 把这个事实压成一份 inventory：

```bash
cd labs/taskforge
PYTHONPATH=src uv run --with pytest --no-project python tools/m09_architecture_probe.py
```

当前输出包括：

```text
[DIRECT STATE DEPENDENCIES] concurrent_claim, legacy_audit, metrics, service, worker
[LIFECYCLE MUTATORS] concurrent_claim, service, worker
[ARCHITECTURE PRESSURE] semantic authority is not aligned with module/process boundaries
```

最后一句不是说 probe 已经证明了目标 architecture。它只提醒我们：今天“谁可以决定 lifecycle transition”并没有和一个清楚的 semantic boundary 对齐。

把 `worker.py` 原样复制到另一台机器时，它当然看不到另一个 Python process 的 `state.jobs`。一个很自然的补丁是：把 `state.jobs` 换成共享数据库，让 API 和 worker 都直接更新 rows。这样 remote access 问题似乎解决了。

但新需求又立刻否掉了这条 shortcut：remote worker **不得获得 durable-store direct-write credential**。而且即使我们放宽这个安全要求，API、worker、scheduler 各自解释 lifecycle rule、再共同写一个 `jobs` table，也只是把“shared representation + multiple semantic writers”从内存搬到了数据库。数据库 transaction 可以解决某些原子更新问题，却不会自动决定完整的产品 lifecycle semantics。

于是我们真正需要先回答的不是“RPC 用什么框架”，而是：

- 谁有资格接受或拒绝 `claim / finish / cancel`？
- worker 为了执行工作究竟需要知道什么？
- 哪些东西应该跨 machine boundary，哪些 representation 不应该跨？
- worker、authority、storage、external sink 分别失败时，谁会一起受影响？

这些问题开始具有 **architectural significance**，因为答案会长期约束多个模块、机器、failure path 和 future migration。

## 2. 这才是 architecture：为高后果问题保留可推理的 structure

SEI 对 software architecture 的一个重要 framing 是：architecture 包含**为了对系统进行推理而需要的 structures**，而不是某张固定层级图。Fowler 总结 Ralph Johnson 时用 “the important stuff” 来强调类似方向：重要性不是由 box 大小或“architect”职位赋予的，而要回到 consequence。

在 TaskForge 里，一个 formatter helper 怎么命名通常不需要 architecture discussion。下面这些决定则很可能需要：

- 谁拥有 Job lifecycle truth；
- remote worker 是否知道 storage schema；
- snapshot 是 derived export 还是 recovery source；
- worker 和 authority 是否独立部署、怎样 version；
- 一个 worker / authority / store failure 会扩散到哪里；
- execution host 拥有哪些 privilege。

课程用 blast radius、reversal cost、coordination cost、failure consequence、authority consequence、long-lived contract 和 unknown-consumer risk 作为**定性 review heuristic**。它不是一个打分公式，也不是说“难改的设计就是好 architecture”。Accidental coupling 本身也会让 change 很难。

更有用的压缩是：**architecture 关注那些会让局部决定跨边界放大 consequence 的 structure。**

这也解释了为什么 M09 不把 architecture 等同于 microservices、top-level folders 或 UML。一个进程内 module 可以形成强 semantic boundary；三个独立 service 也可能通过 shared database、backdoor reads 和 synchronized rollout 保持高度耦合。

## 3. 先把几种 boundary 分开，否则“拆服务”没有可验证含义

回到 remote-worker case。这里至少有五种不同问题：

| Boundary | 问的问题 | TaskForge 当前压力 |
|---|---|---|
| semantic / authority | 谁负责 concept 与 invariant，谁能决定 truth？ | claim/finish/cancel 的 rule 分散在多个 writer |
| process / network | 哪里开始需要 IPC、serialization、timeout？ | remote worker 必然跨 machine/process |
| storage / durability | 哪份 state 只是 representation，什么在 crash 后应继续存在？ | current `state.jobs` 是 memory；target store/durability 尚未实现 |
| deployment / compatibility | 谁可以独立 rollout/rollback/version？ | authority 与 worker 未来可能 version skew |
| failure / security | 一个 component 或 credential 出问题会拖谁下水？ | worker crash/compromise 不应等于 authority/store failure |

这些 boundary **可以**重合，但不能默认重合。

例如我们可以先把 lifecycle operations 聚合进一个明确的 `Job Authority` semantic boundary，而它仍和 API 位于同一个 Python process。这样还没有新增 network failure，却已经减少了 lifecycle knowledge 和 storage representation 的泄漏。等 remote worker 真正出现时，再在 authority 与 execution worker 之间建立 process/network boundary。

反过来，如果现在创建 `API Service / Worker Service / Scheduler Service` 三个 process，却都拿着 shared DB write credential 并直接修改相同 rows，deployment box 变多了，semantic authority 并没有更清楚。

一个 process call 变成 network call 还有真实成本：serialization、partial failure、timeout、retry、authentication、authorization、version skew、observability、capacity、backpressure 与 rollout compatibility。只有 independent failure isolation、remote hardware/location、privilege separation、独立 scale/deploy 等真实需求，才有理由支付这些成本。

这也是 Fowler `Monolith First` 在本章的用途：不是推出“所有系统必须 monolith first”，而是反驳“service 数量 = architecture maturity”。

## 4. Remote worker 应该依赖什么？这时 dependency inversion 才有实际意义

现在假设我们同意：worker 不应直接写 storage。一个机械式“分层”修法可能只是创建 `StoreInterface`，然后把 DB connection 通过 Dependency Injection 塞给 worker。代码出现了 interface，dependency 仍然指向 persistence detail：worker 还是得知道 rows、columns、transaction 或 storage errors。

Brett Schuchert 在 *DIP in the Wild* 对 Dependency Inversion Principle 的解释很适合这里：高层 policy 不应依赖低层 detail，dependency 应朝更接近 domain 的 abstraction 指向；同时，DIP 不是 Dependency Injection / IoC 的同义词，也不是“所有东西都做 interface”。Abstraction 自身有成本，必须由 context 支付。

对 TaskForge，问题可以写得很具体：

```text
bad dependency shape
remote worker
  -> jobs table / DB credential / storage representation

better candidate dependency shape
remote worker
  -> claim / finish / heartbeat semantics
  -> lifecycle authority hides storage detail
```

这里 dependency inversion 的真实用途是：**让 execution-side code 依赖 job lifecycle contract，而不是依赖某个持久化 mechanism。**

这不会自动证明“Central Job Authority”一定是唯一正确 architecture。它只是告诉我们，如果 remote worker 的职责是执行 job，那么 `claim(job semantics)` 比 `UPDATE jobs SET status=...` 更符合它真正需要依赖的 abstraction level。是否采用这个 boundary，还要继续比较 availability、failure、security、implementation cost 和 future partitioning。

这也给 M02 的 information hiding 一个 system-scale版本。隐藏的不只是 private field，而是“谁必须知道 persistence representation、transition rule、retry semantics”。一个 stable boundary 的价值，是让这些 knowledge 不必沿着 machine boundary 扩散。

## 5. 设计至少两次：`Job Authority` 是 reference candidate，不是 starter 已经拥有的事实

到这里我们才有足够 criterion 比较 architecture。下面的 Design A 是本课程 reference direction，但不是由术语自动推出的唯一答案。

### Design A — Central semantic authority + remote worker protocol

```text
client / API
     |
     v
+----------------+
| Job Authority  | ----> storage mechanism (future durable store candidate)
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

第一阶段 `Job Authority` 可以与 API 同 process。它的核心是 semantic invariant，而不是 service topology：normal product lifecycle transitions 经过同一个 authority；remote worker 请求 transition，不直接修改 authority 的 storage representation。

它的真实好处包括 lifecycle knowledge locality、worker privilege 收窄，以及 storage 从 memory 演化到 SQLite/Postgres 等 mechanism 时不必把 schema 泄漏给 worker。代价同样真实：authority 成为 lifecycle write-path availability dependency；worker protocol 增加 timeout/retry/version/auth semantics；未来 throughput 或 blast-radius 目标可能要求 partition。

注意图里的 “storage mechanism” 是**target architecture 的 placeholder**。当前 starter 只有进程内 `state.jobs`，并没有 durable Job Store contract。M09 不能画一个 database box 就假装 durability 已经实现。

### Design B — Shared DB direct coordination

```text
API --------\
scheduler ----> shared jobs table
worker ------/
```

这不是 strawman。数据库 transaction 可以提供 atomic claim primitive；少一层 explicit service protocol；同一个小团队、同 deploy/trust domain 下可能非常实用。

但它把 schema 变成跨组件 integration API，并把 DB credential 暴露给 worker。除非 lifecycle semantics 能被一个清楚的 shared authority（例如被明确设计的 DB-side constraints/procedure）承担，否则 rule 仍可能复制到多个 process。对**本题**而言，`remote worker 不得获得 durable-store direct-write credential` 已足够使“worker 直接写表”版本的 Design B 不满足 requirement。

这比“shared database 是反模式”精确得多。换一个 requirement set，B 可能是正确答案。

### Design C — replicated per-worker state

另一条路线是让 API、worker A、worker B 各自维护 lifecycle state，再做 event sync / reconciliation。它可能支持 offline/multi-master operation，但当前需求没有这些压力，却会引入 conflict resolution、duplicate claim、order/causality 和 recovery complexity。因此 reference 不选它；理由是 complexity 没有被当前 requirement 支付，而不是它“不够 clean”。

设计比较至少要看：authority clarity、worker compromise blast radius、partial-failure model、versioning cost、implementation cost、storage portability、rollback 与 future partitioning。`A cleaner / B simpler` 不是工程判断。

## 6. “Control plane / data plane”可以帮助看 privilege 和 failure，但只能当有条件的 lens

AWS 的 fault-isolation材料沿用网络里的 control plane / data plane 区分：control plane 管理资源、规则和 orchestration；data plane 承担服务的主要功能。TaskForge 不是 router，也不是 AWS service，所以不能因为词很贴切就宣布“worker 就是标准 data plane”。

本课程只做一个显式的 course adaptation：把 lifecycle/control authority 看成 **control responsibility**，把 command execution 与 external-effect interaction 看成 **data/execution-plane-like responsibility**。

这个 lens 在 remote-worker case 里有两个具体价值。

第一是 privilege。Execution worker 需要 shell/host capability，却不因此需要 durable-store direct-write credential；API/control side 需要决定 lifecycle truth，却不应该继承 worker 的任意 host execution privilege。把两类权限放在一个无差别 trust domain 中，会放大 compromise blast radius。

第二是 availability。Authority 暂时不可用时，已经开始的 remote command 可能仍在物理执行；“control side down”与“execution 已停止”不是同一个事实。反过来，一个 worker crash 也不应把 API process 一起 crash。这个区别会直接进入 failure walk。

这个 terminology **不要求**我们把 API 和 authority 拆成独立 process，也不证明两个 plane 能完全独立。若每次 execution 都同步依赖一个单点 control action，或两边共享同一个脆弱 stateful dependency，图上的 separation 仍可能没有形成真正 failure containment。

## 7. Data ownership：storage、semantic authority、snapshot 不要互相冒充

当前 TaskForge 有三类东西容易被混成“state owner”。

`state.py` 保存 `jobs` 与 `next_job_number`，但“数据放在哪里”不等于“谁拥有 lifecycle semantics”。今天真正写 lifecycle 的 normal/historical code 包括 `service.py`、`worker.py` 和 teaching-only `concurrent_claim.py`。所以 baseline 更精确的描述是 **shared representation + multiple semantic writers**，而不是“state.py 是 Job owner”。

`snapshot.py` 又是另一类。当前代码可以把 `service.list_jobs()` 序列化成 JSON，也可以把一个 snapshot 文件 parse 成 `Snapshot` DTO；但它没有 `load snapshot -> reconstruct TaskForge authority` 的 startup/restore path。没有 crash-consistent restore、stale-snapshot reconciliation 或 multi-writer recovery contract。

因此本轮 reference classification 是：**snapshot 是 derived durable export / compatibility surface，不是当前 live coordination source，也不是已经实现的 recovery truth。** 如果未来产品真的把它升级成 recovery source，那么 atomic write、corruption、fsync/durability assumption、stale data、schema migration 和 restore lifecycle 都要重新进入 architecture contract。

同理，external-effect bookkeeping 也有自己的 authority。M07 的 `effect_delivery.completed_jobs` 只是进程内 set，`SimulatedCrash` 是 same-process failpoint；它没有成为 durable exactly-once system。M09 只能问“logical effect identity 和 dedup responsibility 应该落在哪个 effect authority/sink”，不能因为画了 remote worker 就宣称这个问题已经解决。

一个 architecture view 必须标清 `source of truth / storage / replica / snapshot / cache / read model` 的角色；mechanism 名字不能替我们做 semantic classification。

这里还要区分 **read-model replication** 与 **writer-authority replication**。Metrics、dashboard、audit 可以在 contract 允许时消费 read API、snapshot、stream 或 replica；复制一份只读 view 并不自动复制 lifecycle 决策权。相反，让多个 derived/read paths 反向成为 hidden writer，会重新制造 split authority。课程常用的 `one semantic write authority + many derived read models` 是一种 simplification candidate，不是要求所有系统实施 CQRS。

## 8. Runtime flow 要把 control、data 和 failure-path edge 一起看

一个正常路径可以画成：

```text
client --submit--> lifecycle authority
                     |
                     | claim: job_id + execution inputs
                     v
                  worker --effect--> external world
                     |
                     | finish: job_id + outcome
                     v
                lifecycle authority
```

这张图只说明调用顺序还不够。还要问跨 boundary 的 data 是什么：command、job ID、claim/lease identity、exit code、effect identity；哪些字段是 protocol contract，哪些只是内部 representation。

更重要的是 failure path 会新增正常图没有的 edges。比如 worker 对 authority timeout 后 retry，或 scheduler 把失败 worker 的任务 fail over 到另一 pool。M07 已经证明 retry 可以放大请求；Google SRE 的 cascading-failure案例进一步说明 failover/负载重分配可能把局部 overload 推给健康 cluster，最终扩大 outage。

所以 architecture review 对每个 failure 都应做一次 walk：

```text
initial failure
-> first reaction
-> retry / failover
-> new dependency or added load
-> state uncertainty
-> recovery owner
-> blast radius
```

“系统有 retry/failover”不是可靠性结论；它只是另一组需要 capacity、authority 和 isolation reasoning 的 mechanisms。

## 9. 四个 failure walk 会暴露这个 candidate architecture 还没有解决什么

### Worker process dies

如果 worker 已经是独立 process，至少 API process 不必一起 crash。但某个 job 是否可以重新 claim，要依赖未来的 lease/heartbeat/recovery rule。M09 当前 starter 没有这套 production protocol，不能写成“worker dead -> job automatically requeued”。

这里 process boundary 确实形成了一部分 failure isolation，却没有自动解决 lifecycle recovery。

### Network lost after command starts

worker 可能已经执行 command，authority 却收不到 finish。M04/M07 的 temporal lesson 在这里继续成立：timeout 描述 caller knowledge，不证明 downstream non-execution。直接 retry execution 可能重放 external effect。

因此 worker protocol 的 timeout/result semantics 是 architecture concern，不只是 RPC client error string。

### Authority process dies

如果 reference candidate 中 authority 与 API 同 process，那么 lifecycle writes 暂时不可用；远端 worker 可能仍在运行已经 claim 的 command。更关键的是，**当前 starter authority state仍只是 memory**。没有 durable authority state，我们不能严谨承诺 restart reconciliation。

这正是 architecture honesty：把 “not solved in M09” 写出来，比加一个 `Database` box 更有价值。

### External effect succeeds, finish is lost

worker 对外 effect 可能已经成功，随后 finish message 丢失。重试 job 或 effect 都可能重复。M07 的 attempt/effect distinction 必须保留；architecture 只能要求 effect identity 到达真正能 enforce dedup semantics 的 authority/sink，不能把 volatile worker bookkeeping叫 exactly-once guarantee。

这些 failure walk 也解释了为什么一个 target invariant 不能只写“worker 和 API 分进程”。真正有意义的 invariant 应绑定 semantic consequence。

## 10. Failure domain 不是进程数量；要问 scope of impact

AWS cell-based architecture 的可迁移价值不是“TaskForge 现在就要上 cells”，而是把 **scope of impact** 当设计对象。

假设未来很多 tenants 共享一个 worker pool、hot queue 或 effect sink，一个 poisoned workload 可能吃掉所有 capacity，让 unrelated jobs 一起变慢。把 workload 分成 cells/shards 只有在 state、traffic 和 dependency 真正按相同 grain 被隔离时才形成 containment；如果所谓 cells 仍共享同一个 hot mutable coordinator、global lock 或 exhausted pool，cell boxes 只是 topology decoration。

TaskForge 当前没有 large tenant population、regional isolation 或 noisy-neighbor requirement，因此 M09 不实现 cell architecture。它只留下 revisit question：**当一个 authority/worker failure domain 超过产品可接受 blast radius 时，按什么 key partition，哪些 state/dependency 也必须一起 partition？**

同样，process boundary 也不自动等于 fault boundary。两个 process 共享单点 storage 时可能一起不可用；一个 process 内的两个 semantic modules 也可能通过 careful error isolation保持不同 failure consequences。Failure domain 要从实际 dependency/failure propagation判断。

## 11. 独立部署以后，architecture 同时获得了时间维度

一旦 authority 与 worker 可以 independently deploy，就会出现：

```text
Authority v2 <-> Worker v1
Authority v1 <-> Worker v2
```

M08 的 producer/consumer compatibility 问题因此进入 worker protocol。现在要明确 protocol surface、N/N-1 是否支持、rollout order、capability negotiation/deprecation、unknown version如何处理，以及 rollback target 能否与已经部署的另一端共存。

这也是 process split 的隐藏成本之一：一个原本同版本仓库里的 Python call，可能变成长寿命 distributed contract。

不要因此要求“所有组合永远兼容”。和 M08 一样，先写 supported coexistence matrix，再让 deployment policy避免不支持组合。Architecture 与 compatibility 不是两个独立章节；一个 boundary 一旦允许 independent evolution，就创造了新的 compatibility obligation。

## 12. 不要画一张全能图：针对问题选择 view

同一个 TaskForge architecture，至少有几种不同的 useful view：

| View | 要回答的核心问题 |
|---|---|
| responsibility / knowledge | lifecycle rule、snapshot schema、effect semantics 分别谁知道？ |
| authority / state | 哪份 truth authoritative，谁能写，snapshot/read model 是什么角色？ |
| runtime flow | submit/claim/execute/finish 时 calls 和 data 如何移动？ |
| failure propagation | worker/store/authority/sink/bad deploy 失败时边如何变化？ |
| evolution / compatibility | independently deployed producer/consumer 怎样共存与 rollback？ |

一张只画 `Service A -> Service B -> Database` 的图很容易撒谎，因为它省略了：A 是否直接读 B 的 table、谁拿 write credential、timeout 后是否 failover 到 C、cache miss/staleness contract 是什么、worker pool 是否共享同一个 recovery authority。

SEI 的“structures for reasoning”在这里回到实践：**view 的价值取决于它帮助回答哪个 consequential question。** 没有唯一一张 architecture diagram 可以同时忠实表达所有 concern。

团队/ownership boundary 也属于这类 view。Conway's Law 不需要神秘化成 deterministic theorem；更直接的问题是：两个组件如果必须每次一起改、一起 deploy、共享 undocumented state，却由完全独立团队负责，coordination cost 会持续出现。想要独立 ownership，就需要 stable contract、独立 evidence 和清楚 version policy 支撑。

## 13. 把 architecture invariant 变成 evidence，但不要做目录 policing

M09 probe 的 direct-import inventory 是 evidence，不是 architecture score。它同时看到 `service.py`、`worker.py`、`metrics.py`、`legacy_audit.py` 和 `concurrent_claim.py`，而这些文件并不是同一种角色。

`concurrent_claim.py` 故意保存 M07 的 unsafe check-then-act 和独立 `claim_owners` registry，供 deterministic race probe 使用。一个 naïve “only one file may import state” refactor 会把历史 teaching evidence 一起抹掉。真实系统里也有 migration tool、repair utility、compatibility shim、test harness 或 emergency admin path；它们必须被 inventory，但未必受 normal product-path rule以相同方式约束。

因此一个和本轮 implementation scope 对齐的 fitness rule 可以是：

```text
normal product modules
(service / worker / metrics / selected reporting path)
must not import/use taskforge.state directly for normal lifecycle access
```

这条 rule 证明的是 **direct-state dependency / transition implementation 被 localize**，不是“完整 mutation authority 已经隔离”。M02 已经指出：如果 `get()`、`list_jobs()` 或 `claim_next()` 返回的是 authoritative mutable `Job`，caller 即使从未 import `state.py`，仍可能通过 alias 直接改 lifecycle。这样的 read result 是 authority-bearing handle；grep/AST import check 看不见这条 capability edge。

所以 M09 的最小 boundary-enabling refactor 只完成 target architecture 的一部分：normal transition policy 与 storage knowledge 有了明确 seam。若要进一步声称 read/reporting path **不能**成为 hidden writer，就需要 capability-oriented evidence 来区分 detached/read-only observation 与 live mutable authority。M09 刻意不顺手引入 `JobView` 或 defensive copy；这条 M02 residual risk 留给后续 change/review 继续识别。

而不是：

```text
no file in repo may import taskforge.state
```

Architecture fitness function 只有同时表达 **invariant + scope** 才有价值。否则 50 行 AST script 也会退化成 grep-driven folder policy。

同样，M03 的 historical mutation harness 可能绑定某段旧 source text。未来合法 architecture refactor 移动 mutation site 后，harness 不再适用并不自动等于 product regression。Evidence 工具本身也有适用 baseline 和 architecture scope。

## 14. ADR 保存的是为什么选这条 boundary，以及什么时候重开这个决定

当两个方案都能完成 feature 时，architecture decision真正需要保存的是 forces 与 consequence。Fowler 对 ADR 的总结强调 context/rationale、decision、serious alternatives、consequences、status，并建议 decision 被替代时保留历史而不是重写过去。

TaskForge 可以为 accepted design 写一个很短的 ADR。若最终选择 reference candidate，它可能是：

```markdown
ADR-0001 — Normal lifecycle transition logic routes through Job Authority

Status: Accepted

Context:
Remote workers are required. Current normal paths mutate shared in-memory Job
representation directly. Remote workers must not get store write credentials.

Decision:
Normal product transition implementations and direct state access are routed
through the accepted authority seam. Workers depend on claim/finish semantics,
not storage representation. The authority may initially share a process with
the API. This phase does not claim detached/read-only Job observation or
complete mutation-capability isolation for returned objects.

Alternatives considered:
- direct shared-DB writes
- replicated per-worker lifecycle state

Consequences:
+ normal transition policy and storage knowledge are localized
+ worker privilege is narrower
- authority availability matters
- mutable observation handles remain a known M02 authority risk
- remote protocol creates timeout/version obligations

Revisit triggers:
Reconsider partitioning/HA when measured throughput, recovery objectives, or
failure-isolation requirements exceed one authority domain.
```

它不是“Job Authority 永远正确”的墓碑。Revisit trigger 把当前 assumption 变成可被未来 evidence 推翻的决定。

同样，不要每个 library choice 都写 ADR。只有 blast radius、reversal/coordination cost、authority、failure 或 long-lived contract 足够 consequential 的决定，才值得长期保存 reasoning。

ADR 之外，一张短 **architecture risk register** 也能防止图把不确定性藏掉。例如当前 candidate 可以显式记录：

| Risk | Mechanism | 当前 evidence / mitigation |
|---|---|---|
| authority outage | normal transition implementation converges on one authority seam | accepted current failure domain；revisit HA on measured objective |
| mutable alias bypass | authority/service may return live authoritative `Job` handles | residual M02 risk；not closed by direct-import fitness rule |
| worker duplicate/retry | timeout leaves execution outcome uncertain | inherit M07 attempt/effect analysis；future lease/idempotency work |
| protocol skew | worker/authority independently deploy | define supported coexistence matrix before network rollout |
| snapshot confusion | durable export 被误当 recovery truth | document current export role；no restore claim |
| sink duplicate | effect succeeds before finish is recorded | carry logical effect identity to actual dedup authority/sink |

Risk register 不是 process bureaucracy，也不是说这些 mitigation 已实现。它只是把 assumption、known gap 与 future evidence owner从 diagram 背后移到 reviewer 能看见的位置。

当多个 architecture 都合理，比较可能继续落到 uncertainty、reversibility、migration cost 与 option value；旁支 [Engineering Risk、Estimation 与 Economics](../extensions/engineering-risk-estimation-economics.md) 专门讨论这一层。需要选择 dependency/state/sequence/data-flow/C4-style 等不同模型时，见 [Models、Notation 与 UML](../extensions/models-notation-and-uml.md)。

## 15. M09 Lab 只做 boundary-enabling refactor，不假装已经建成 distributed system

完整实验见 [Lab 09](../labs/09-architecture-boundaries.md)。实验先做 source classification 与多-view recovery，再设计至少两个 architecture、写 failure walk / ADR，最后才允许一个很小的 implementation phase。

reference implementation direction 是新增一个进程内 `job_authority.py` semantic seam，让 normal `service.py` / `worker.py` 的 transition logic 与 direct `state` access 收敛到一个位置，worker 不再需要 storage representation knowledge。它仍可以使用当前 in-memory `state.jobs`；这一步**不提供 durability、HA、RPC、lease、worker authentication、production concurrency atomicity 或 exactly-once effect guarantee**。

它也**不自动提供 complete mutation-capability isolation**。如果 seam 继续返回 current authoritative mutable `Job`，caller 仍可通过 alias 修改 lifecycle；direct-import fitness check 不会发现这条路径。这是 M02 已知 authority risk，也是本轮有意保留的 non-goal，而不是用 `JobView` 等新 abstraction 顺手“修完”的问题。

特别注意：这个 `job_authority.py` **目前不存在于 starter**。它只是 Lab/Instructor reference 的 candidate change。M09 正文不能把 target diagram 写成 current architecture。

一个谨慎的 Agent implementation contract 应类似：

```text
First recover current architecture from real code and probes; do not propose topology yet.

Then compare at least two remote-worker designs against the confirmed requirements.
If the authority-boundary candidate is accepted, implement only the in-process semantic seam:
localize normal transition policy/direct-state access and remove worker storage knowledge.
Do not claim this proves detached/read-only Job observation or complete mutation-capability isolation.
Do not add JobView/copying, network, DB, queue, DI framework, deployment manifests, or speculative HA.
Preserve prior observable behavior and explicit historical teaching exceptions.
Run core tests plus M05-M09 probes; classify historical harnesses before treating them as gates.
```

这也是 Agent 时代 dependency inversion / architecture reasoning 的实际价值：不是让 Agent autocomplete `API Gateway + Kafka + Redis + Kubernetes`，而是先把 truth、dependency、failure 和 authority 模型恢复出来，再让 mechanism 服从这些约束。

## 16. Review architecture 时，先审 consequence，不审名词密度

Independent reviewer 不应只看 Agent summary，也不应因为 diagram“很像成熟系统”就接受。至少独立检查：

- 当前事实与 target assumption 有没有混写？starter 是否真的有 durable store / restore / lease？
- normal transition policy / direct-state access 是否真的 localize？是否又把这个证据夸成 complete authority isolation？
- `get/list/claim` 是否泄漏 authoritative mutable handle；若是，是否明确标成 residual M02 risk，而不是被 direct-import check 掩盖？
- remote worker 依赖 domain-level contract 还是 storage detail？所谓 DIP 是否只是 interface/DI ceremony？
- semantic、process、deployment、failure boundary 是否被误当成同一个东西？
- control/data-plane wording 是否只是有条件的 TaskForge analogy，没有被写成标准 topology 定律？
- worker timeout / authority crash / effect-finish loss 的 temporal semantics 是否与 M07 一致？
- failover/retry 是否新增了 capacity dependency 或扩大 blast radius？
- snapshot 的 export/recovery role 是否明确，是否凭空增加 durability？
- protocol独立演化后的 compatibility/rollback 有没有继承 M08 的约束；是否把 N/N-1 这类 policy example 偷升成 universal MUST？
- fitness rule 是否包含 scope，并且诚实说明它只证明 direct-state dependency localization，而不是 capability isolation？
- alternatives 是否是真实可行方案，而不是为 reference design 服务的 strawman？
- complexity 是否由当前 requirement 支付，revisit trigger 是否可被未来 evidence 推翻？

Architecture 最终不是几个 box，而是一组可以被 failure、change 和 evidence反复检查的 consequential boundaries。

## 17. 来源边界：哪些是 source-backed，哪些是课程综合

SEI 支撑 architecture 作为用于 reasoning 的 important structures；Fowler/Ralph Johnson 支撑“重要 design elements / evolution”这一 architectural-significance framing。Stanford CS190 支撑 information leakage、knowledge locality 与 simple interface 的 modularity reasoning。

AWS cell material支撑 scope-of-impact / real isolation boundary；AWS control-plane/data-plane material支撑该术语的原始 distinction，但 **TaskForge 的 lifecycle control authority vs data/execution plane 映射是课程综合**。Google SRE 支撑 retry/failover/capacity coupling导致 cascading failure 的 reasoning。

Fowler `Monolith First` 只作为 service premium / stable-boundary经验材料，不升级成“必须 monolith first”的定律。Schuchert 的 *DIP in the Wild* 支撑 high-level policy 不应依赖 low-level detail、dependency 应朝 domain-relevant abstraction，以及 DIP 不等同于 DI/IoC；**把它具体映射到 TaskForge `worker -> claim/finish -> authority` 是课程应用，不是 source 原始案例。**

Fowler ADR material支撑短 decision record 的 context、alternatives、consequences、status 等作用；M09 的 consequence heuristic、五种 view、TaskForge target invariants、Job Authority reference direction、fitness-rule scope 与 Agent workflow 都是课程综合或 repo-specific reasoning。

本章不能从这些来源推出：microservices 更高级、所有 process boundary 都是 fault boundary、所有 shared DB 都错、所有系统都需要 control/data plane services、DIP 要求每层 interface、一个 central authority 永远正确，或 M09 starter 已经具备 durable/HA/recovery guarantee。
