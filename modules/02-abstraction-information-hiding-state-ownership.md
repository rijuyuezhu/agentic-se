---
id: M02
type: module
visibility: student
order: 2
---
# M02 — Abstraction、Information Hiding 与 State Ownership

M01 最后留下了一个没有被 specification 本身回答的问题：我们已经知道哪些状态必须合法、哪些 transition 应被拒绝，也开始寻找 invariant 的 enforcement point；但**谁有资格改变这些事实，谁只能观察或请求变化？**

这一章不从 `encapsulation`、`repository pattern` 或 `dependency inversion` 的定义开始。先看一个更难受的现象：TaskForge 的功能测试全部通过，但一个普通 caller 仍然可以绕开所有 lifecycle rule，把 authoritative state 直接改掉。

为了隔离本章变量，实验仓库里的 TaskForge 仍然是一个刻意简单的 v0：只有 `QUEUED / RUNNING / SUCCEEDED / FAILED / CANCELLED`，没有把 M00/M01 用来推理的 `CANCELLING` 或 `cancellation_requested` 候选设计写进 production baseline。前两章讨论的是可选 contract；这一章先拿更小的现有系统练习 boundary 和 ownership。不要把教学候选和当前 repo state 混成同一张模型。

## 1. 六个测试都绿，为什么 caller 仍然能改掉系统事实？

TaskForge v0 的共享状态非常直接：

```python
# state.py
jobs: dict[str, Job] = {}
next_job_number: int = 1
```

`service.submit()` 负责分配 ID 并插入 `Job`，`service.cancel()` 会改 status；`worker.claim_next()` 和 `worker.finish()` 也直接遍历或修改同一个 dict。`metrics.py` 虽然只读，却同样知道 collection 的具体 representation。

真正危险的地方还不止这些显式 writer。`service.get()` 当前直接返回 dict 里那一个 `Job`：

```python
job_id = service.submit("echo hi")
job = service.get(job_id)
job.status = JobStatus.SUCCEEDED

assert service.get(job_id).status == JobStatus.SUCCEEDED
```

这段修改没有经过 `cancel()`、`claim_next()` 或 `finish()`，也没有检查任何 lifecycle rule，却真的改变了 TaskForge 后续看到的状态。于是“有哪些 writer？”这个问题不能只靠搜索 `.status =` 回答。严格地说，**每一个拿到 authoritative mutable `Job` reference 的 caller 都获得了潜在 write authority**。

现在想象你要增加一种新的 lifecycle 语义，或者只是把内存 dict 换成 SQLite。你会马上碰到几类压力：

- `service.py`、`worker.py`、`metrics.py` 都知道 collection 是 `dict[str, Job]`；
- lifecycle rule 分散在 cancel、claim、finish 等路径；
- ID allocator 与 collection 是两个 module-level mutable globals；
- `get()` / `list_jobs()` 把内部 mutable object 直接交给 caller；
- claim 的 FIFO 行为实际上依赖 dict insertion order；
- 测试 fixture 也能直接 reset 共享状态。

这时再问“应该加哪个 class？”还太早。更有价值的是先问：**哪些知识本来应该只存在一个地方？哪些事实本来应该只有一个 authoritative mutation path？**

这两个问题分别把我们带向 abstraction / information hiding 和 state ownership。

## 2. 先让 representation 变化一次，Abstraction 才不再是空话

假设我们希望把 job storage 从当前 dict 换成 SQLite。最直接的接口如果是：

```python
def all_jobs() -> dict[str, Job]:
    return jobs
```

client 依赖的不只是“可以读取 jobs”。它还知道：

- collection 是 dict；
- value 是当前 authoritative mutable `Job`；
- 遍历顺序来自 dict；
- 修改 value 会修改系统事实。

于是 storage 一变，很多 client 都必须跟着变；更糟的是，即使 storage 不变，client 也可以绕过 lifecycle policy。

一种候选边界可以不再交出 collection，而只暴露语义操作和 read projection：

```python
def get(job_id: JobId) -> JobView:
    ...

def list_jobs() -> tuple[JobView, ...]:
    ...

def claim_next() -> JobView | None:
    ...

def finish(job_id: JobId, exit_code: int) -> None:
    ...
```

caller 现在依赖的是 lookup、listing、claim、finish 这些行为，而不是“内部有一个 dict 可以拿来改”。内部以后仍然可能是 dict，也可能变成 SQLite，甚至再往后变成远端 service；只要这组对外语义不变，client 就不应该因为 concrete representation 改变而被迫同步重写。

到这里再给概念命名比较有意义。MIT 6.102 用 Abstract Data Type 说明：抽象由 operations 及其 specification 定义，abstract value 对 client 是 opaque 的，concrete representation 属于 implementation。它还用 **representation independence** 提供了一个非常实用的压力测试：

> 如果内部 representation 改变，而 contract 没变，哪些 client 仍然必须改？它们为什么知道了这么多？

这不是要求“所有实现都可以随便替换 storage”。有时性能、transaction、ordering 或 durability 本来就是 public contract 的一部分，换 representation 确实会改变可观察语义。要找的是 **accidental dependency**：client 只是因为 implementation 泄漏才被迫知道的东西。

### Interface 比函数签名更大

`claim_next() -> Job | None` 看起来只是一个很短的 signature，但真实 interface 还可能包括：

- 选择哪个 eligible job；
- 返回对象是不是 snapshot；
- claim 成功时 transition 是否已经 authoritative；
- concurrent caller 是否可能 claim 到同一个 job；
- failure 以后 caller 能否判断 transition 是否发生；
- 是否必须先调用另一个 operation；
- 返回对象未来是否仍然有效，还是只是某一时刻的 observation。

Stanford CS190 的 modular-design materials 明确强调，module interface 同时包含 formal 和 informal aspects。`private` 能改变语言层可见性，却不能自动消除这些语义依赖。

例如一个 class 把 `_jobs` 标成 private，却提供：

```python
def raw_status(job_id):
    return self._jobs[job_id].status_code
```

而所有 client 都写：

```python
if scheduler.raw_status(job_id) >= 2:
    ...
```

即使没有 mutable reference 泄漏，`0/1/2/3` 的 encoding knowledge 已经扩散出去。以后内部增加状态或重排编码，外部代码都会被拖进来。

所以 abstraction 的工程问题不是“有没有 class/interface”，而是：**client 被允许依赖哪些概念，又被迫知道了哪些本不该知道的实现决定？**

## 3. Information Hiding 隐藏的是设计知识，不只是数据

回到当前 TaskForge，先看哪些 knowledge 已经局部化、哪些还没有。`Job.terminal` 是一个小但重要的正例：`SUCCEEDED / FAILED / CANCELLED` 这组 terminal knowledge 已经集中在 model 里，`metrics.terminal_count()` 只问 `job.terminal`，没有再复制一份 status 集合。将来 terminal 定义改变时，这至少减少了一类同步修改。

但 transition knowledge 仍分散着：

```text
service.cancel()     知道 queued 才能 cancel
worker.claim_next()  知道 queued 才能 claim
worker.finish()      知道 running 才能 finish，并解释 exit code
```

collection representation 又同时被 service、worker、metrics 知道。`Job.terminal` 这个局部正例并不足以形成完整 lifecycle owner；下一次 transition 语义变化时，修改者仍要跨模块恢复整套规则。

这里真正需要局部化的不是几行 syntax，而是 **design knowledge**：哪些 transition 合法、哪些 state 是 terminal、claim 怎样选择 job、ID 怎样分配、哪些事实必须 durable、restart 后怎样恢复 incomplete work。

这就是 information hiding 比 “fields are private” 更强的地方。Stanford CS190 的材料把 information leakage 描述为 implementation detail 或 design knowledge 跨模块传播；课程把同一 reasoning 从 class-oriented 场景推广到 module、component、service、process 和 persistent state。这个推广是课程综合，不是声称 CS190 已经给出了后面整套 state-ownership taxonomy。

### Change amplification 是 symptom，不是文件计数器

假设未来确实增加一个新状态。某些改动本来就不可避免：如果 public API 要暴露新状态，serializer、UI 或 compatibility layer 可能都要理解它。真正值得追问的是：**哪些变化来自需求本身，哪些只是同一份知识被复制了很多次？**

如果每个 caller 都维护一份 terminal set，那么新增状态时的多点修改就是 duplicated knowledge 带来的 accidental change surface。如果只有 lifecycle owner 需要更新 transition rule，而 UI 只是因为产品确实要展示新语义才变化，这两类扩散不能混为一谈。

### `private` 仍然可能发生 representation exposure

TaskForge 当前的 `get()` 是最直接的例子：字段可以都藏在 `Job` 里面，但 caller 拿到的是同一份 mutable instance，于是 owner 再也无法证明“所有 transition 都经过我”。MIT 6.102 的 abstraction-function / representation-invariant materials 对这个问题给了很强的局部标准：如果 client 可以修改 representation，producer/mutator 就无法独立维护 representation invariant。

更稳妥的 read boundary 可以返回 defensive copy、frozen view 或其他 immutable projection。这里先不要把某一种 mechanism 升级成唯一答案。我们要保护的是一个性质：**read 不应无意授予 authoritative mutation authority。**

### Temporal decomposition 也会泄漏知识

另一种常见结构看起来非常“单一职责”：

```text
LoadJob
ValidateJob
PersistJob
PublishJob
```

运行时确实按这个顺序发生。但如果四个模块都必须理解同一套 schema、transaction boundary、durable fields、ID visibility 和 persist-after/publish-before failure semantics，那么只是按时间把一份 cohesive design knowledge 切成了四段。

CS190 把这种风险称为 temporal decomposition。问题不是“按阶段拆分永远错”，而是 decomposition 的理由不能只剩“程序先做 A 再做 B”。如果正确修改任一阶段都必须同时理解其他阶段的同一设计决定，boundary 可能切错了。

## 4. Deep Module 是一个压力测试，不是 depth score

Ousterhout/CS190 的 deep-module vocabulary 对这里很有用。一个 module 如果能用相对简单的 interface 隐藏大量重要 complexity，client 就能少承担很多 knowledge；相反，一个 shallow wrapper 即使代码很短，也可能新增名字、dependency edge 和调用顺序，却没有真正隐藏什么。

因此把：

```text
service -> service_impl -> repository -> adapter -> gateway
```

排成很长一条链，并不会自动让系统 modular。每层如果只是原样转发参数，修改一个概念反而可能需要同步五份 interface。

但不要把这个 heuristic 反过来变成“大类更好”。一个 1500 行 module 如果把五个无关职责混在一起，依然很难理解；一个很小的 parser 如果隐藏了一套稳定 grammar，也可能非常有价值。更不能用 `implementation LOC / API method count` 算“depth score”。

真正的问题仍然是：**这个 boundary 隐藏了什么有价值、会变化、会产生认知负担的知识？**

这也解释了为什么“更通用”不是 abstraction 的同义词。为了未来 SQLite 就提前造 `GenericRepository[T, K, Query, Transaction, ...]`，再配 `UnitOfWork`、`EventBus`、`CommandBus`，可能只是把尚未出现的未来猜测编码进今天的 mental model。只有当一个 general mechanism 真正消除了多个 client 重复理解的复杂度，它才值得存在。

同理，DRY 也不等于 information hiding。两段代码都写：

```python
status in {SUCCEEDED, FAILED, CANCELLED}
```

如果它们表达的是同一条“哪些状态是 terminal”的业务知识，那么值得局部化。两段碰巧都有 `for item in items: validate(item)`，却属于会独立演化的 domain，就未必应该抽成 generic helper。优先消除的是 **duplicated knowledge**，不是视觉上重复的 syntax。

## 5. 从“知识应该放哪里”走到“谁有权改变事实”

Information hiding 仍然没有完全回答 TaskForge 的问题。即使 lifecycle rules 都写进一个 helper，`service.py` 和 `worker.py` 如果仍能直接改同一份 `Job`，authority 还是分散的。

工程讨论里常说 “single source of truth”，但它容易把几个不同角色混在一起。更精确地看一个事实，可以区分：

**Authority / owner** 决定这个逻辑事实是否可以合法变化。比如某个 lifecycle owner 有权接受 `QUEUED -> RUNNING`，也有权拒绝 `FAILED -> RUNNING`。

**Storage** 负责让事实跨 process lifetime 保存。SQLite 可以 durable 地存一个 status，却不自动成为所有业务 transition 的 semantic decision maker。应用层、database constraint、stored procedure 都可能承担不同部分的 invariant enforcement；关键是责任要明确。

**Replica / cache** 保存 derived copy 以改善 locality 或性能。它可以过期。如果它和 authority 冲突，系统需要明确哪一侧有最终权威、怎样判断副本是否已经过期，以及发生分歧后怎样重新收敛，而不是让两份 mutable copy 都“差不多算真的”。

**View / projection** 为 UI、metrics、search 等用途派生出部分 representation。它应该明确自己只投影哪些事实，并通常能够从 authoritative facts 重新构建。

这个区分尤其重要，因为 **state/model projection 不是第二份 authority**。例如前面候选边界里的 `JobView` 可以只承载 `id / command / status / exit_code` 这组 v0 observable fields；它并不因此声称自己是未来所有 durable state 的完整 schema。若后续模块加入其他 execution / cancellation / recovery state，旧 projection 要么扩展，要么继续明确只表达其中一部分。不能因为画了一张 view，就让读者猜没画出来的 state 是不存在还是只是 out of scope。

### “谁存数据”与“谁拥有状态”不是同一个问题

假设未来有：

```text
Controller
    ↓
SQLite
```

Controller 计算合法 transition，并在 transaction 中写入 SQLite。可以合理地说：

```text
semantic authority: Controller 的 transition policy
persistence mechanism: SQLite transaction
```

也可以把部分 invariant 下沉成 database constraint，使数据库对那部分合法性拥有直接 enforcement。两种都可能成立。错误的是只因为 bytes 存在 SQLite，就停止追问“谁决定这个 transition 应该被接受”。

因此每遇到一类重要 state，都至少问五个问题：

1. 谁创建第一份合法状态？
2. 谁可以请求 mutation，谁真正接受 authoritative transition？
3. 谁验证 invariant？
4. 谁负责 durable commit？
5. crash/restart 或副本分歧以后，谁重建或 reconcile？

这里尤其要区分 **request a transition** 和 **perform/accept the authoritative transition**。前者可以来自很多 participant，后者必须服从 owner 的 invariant 与当前 authoritative state。

remote worker 将来可以报告“job 42 已执行完”，但 controller/store 是否接受这个结果，还可能取决于当时的 authoritative execution/recovery state。这些具体机制留到 M07–M09；M02 只先把 authority 边界说清楚。

## 6. Split Authority 往往先伪装成“需要同步一下”

假设 API server 有：

```python
active_jobs: dict[str, Job]
```

worker manager 又有：

```python
running_jobs: dict[str, Job]
```

而两边都能改 status。很快就会出现：

```text
API:            job 7 = CANCELLED
Worker manager: job 7 = RUNNING
```

于是下一步通常是加 `sync()`、`refresh()`、`reconcile()`。在真正的 distributed system 里，副本同步和 reconciliation 当然可能不可避免；但在一个单进程 toy system 里，这种“分布式问题”很可能只是第二份 write authority 人工制造出来的。

所以看到第二份 mutable copy 时，第一反应不要是“怎样同步得更快”，而是：**它为什么需要成为 writer？它能否只是 replica 或 projection？**

当前 TaskForge 的问题更隐蔽：表面只有一个 `state.jobs` dict，但 `service`、`worker` 和任意拿到 `Job` reference 的 caller 都能改变它。物理上只有一份 object，不等于语义上只有一个 owner。

### Ambient global state 让 dependency 变成不可见

假设函数只有：

```python
def run_job(job_id):
    ...
```

看起来只依赖 `job_id`。但实现里却从 module global 读取 registry、settings、current workspace、cwd 和环境变量，那么 signature 隐藏了真实 dependency。

把依赖显式写出来：

```python
def run_job(job_id, registry, executor):
    ...
```

参数变多了，却可能更容易 reasoning 和 test。目标不是“禁止所有 global”：immutable constant 没有这类问题，process-wide registry 也可能有合理场景。危险的是**可变的、携带业务语义、又可被环境中任意位置使用的 ambient authority**。

### 发现 failure 的地方不一定拥有处理 authority

CS190 的 Raft review material 里有一个很有启发性的具体问题：某个 message 层能发现 socket EOF/error，却不拥有 socket lifecycle，因此 cleanup 还必须把信息继续传给真正 owner。这里最值得迁移的不是 C++ 细节，而是区分 **observes a failure** 与 **owns the affected resource/lifecycle**。

如果 boundary 让“发现问题”和“有权完成恢复”长期错位，系统就会产生额外 information flow、ordering requirement 和 callback plumbing。不要因为一个 component 最先看见 error，就自动把 resource authority 也交给它。

## 7. Owner 的 API 应表达 semantic operation，而不是交出数据结构

TaskForge 当前 worker 想 claim 一个 job，最短写法是：

```python
for job in state.jobs.values():
    if job.status == JobStatus.QUEUED:
        job.status = JobStatus.RUNNING
        return job
```

这几行同时让 worker 知道 collection representation、eligible state、selection policy 和 transition mutation。

如果 owner 提供：

```python
def claim_next() -> JobView | None:
    ...
```

调用方只请求一个 domain operation。owner 内部可以统一处理：哪些 job eligible、选择策略是什么、transition 是否合法、mutation 怎么做，以及以后是否需要 transaction。

可以把这个差别概括成两种请求：一种是“把你的 state 给我，我自己改”，另一种是“请在你的 invariant 下执行这个 semantic operation”。后者把 mutation authority 留在 owner 一侧。

Agent 时代这个差别更重要。coding agent 很擅长发现一个可写 dict 后走最短路径；如果 repo 同时存在 `registry.transition(...)` 和 `state.jobs[id].status = ...` 两条路，后者很容易被复制。**好的 boundary 不只是教育修改者“应该怎么做”，还尽量让正确 path 成为唯一、显式、容易找到的 path。**

### Query 和 Command 可以不对称

收敛 write authority 不代表所有读取必须经过同一条昂贵路径。commands 如 `submit / claim / cancel / finish` 若改变 invariant，通常应经过 owner；但 `queued_count`、recent failures 或 search result 可以从 read model、cache、index 读取，只要它们明确是 derived view，而不是第二份 write authority。

这也是为什么“只有一份数据”不是 ownership 的目标。可以有很多副本和 projection，真正需要清楚的是：**谁能定义事实，谁只是在复制、缓存或观察事实。**

如果某个 projection 有自己独立的 freshness contract，例如 metrics 允许延迟 30 秒，那是它自己的 observable contract；不能一边允许 staleness，一边又把这个 projection 当成 authoritative decision input 而不说明 reconciliation 规则。

## 8. Design it twice：Job 自己拥有 transition，还是 Registry 拥有？

有了上面的标准，仍然不应该跳到“所以一定要建 `JobRegistry`”。M02 lab 刻意要求至少比较两个真实设计，因为 ownership placement 本身就是 engineering decision。

一种方案是让 `Job` 管理单对象 transition：

```python
job.claim()
job.cancel()
job.finish(exit_code)
```

优点是 local lifecycle rule 靠近 data，单对象 invariant 清楚。问题是 ID allocation、collection、`claim_next` selection policy 仍然需要别的 owner；如果 future persistence 要求 transition 与 storage transaction 原子提交，纯 object-local mutation 可能还要重新设计。最关键的是：即使 `Job` 有好方法，也不能再把 authoritative mutable instance 发给所有 caller。

另一种方案是让 `JobRegistry` 或同等 component 管理 collection + transitions：

```text
submit
get/list read-only views
claim_next
cancel
finish
```

这会让 collection representation、ID allocation 和 lifecycle enforcement 更容易收敛，也让 dict -> SQLite 的 change surface 更局部。但它同样有风险：Registry 可能逐步变成 god object；process execution、network transport、observability、所有 persistence policy 都不应该因为“ownership”三个字就被塞进去。

对当前极小的 TaskForge，第二种通常是很直接的教学实现；这不是因为 “Registry pattern 更高级”。未来 M05/M08/M09 加入 persistence、compatibility 和 process boundary 后，今天合理的 responsibility placement 还可能重新分解。

第三种“worker 直接拥有 status”写起来最短，却需要非常强的理由。worker 的核心责任如果只是执行 work，它却能绕过 controller policy 改 lifecycle，remote worker 出现后就很容易形成 split authority。可以据此形成一个比 pattern name 更稳定的排除标准：

> 如果一个 component 不负责某个 invariant，却能绕过 owner 直接改变它，那么它拥有了过多 authority。

### Dependency direction 只有在隐藏真实变化时才值得增加

以后如果 `JobService` 直接散落 SQL：

```python
conn.execute("update jobs set ...")
```

lifecycle policy 与 storage mechanism 就会耦合。此时引入一个窄的 `JobRepository` boundary，可能让 policy 不依赖 SQLite 的 concrete accident。

但不要把这一点机械升级成“所有依赖都必须倒置成 interface”。只有当 storage 确实是重要 variation、policy 与 mechanism 值得独立 reasoning/test，或者 concrete dependency 正在传播不应传播的 knowledge，额外 boundary 才有收益。否则 interface 本身只是一个新的 shallow abstraction。

## 9. 把 M02 变成一次真正的 read-only design review

这一章最值得带进陌生 repo 的不是一个类图，而是一张 **authority map**。面对 `session`、`job`、`config`、`cache`、`workspace`、`connection` 或 scheduler state，不要只搜变量名。对每个重要 fact 记录：

```text
Fact
├── semantic owner / authority
├── current writers
├── readers
├── invariant
├── persistence mechanism
├── replicas / projections
└── recovery / reconciliation rule
```

如果某项不存在，就写 `none` 或 `unknown`，不要把未来设计猜成当前事实。

然后再做 representation-change thought experiment：`dict -> SQLite`、local executor -> remote executor、in-memory config -> durable config。哪个 client 被迫变化？这些变化来自真实 contract，还是来自 representation leakage？

再做 future-change pressure test：新增 lifecycle state、增加 persistence、增加 remote worker。哪些规则会被复制修改？是否出现新的 writer？当前 abstraction 是在局部化 change，还是只是增加一层名字？

### 给 Agent 的任务先分成 reconnaissance 与 implementation

“重构 TaskForge 的状态管理，让代码更干净、更可维护”几乎没有 engineering constraint。更稳妥的第一阶段应当是只读：

```text
Read-only reconnaissance

- locate all authoritative job-state and ID-allocation writers;
- identify every path that exposes a mutable Job or collection;
- reconstruct the current lifecycle and its enforcement points;
- separate current observable contract from representation accidents;
- compare at least two ownership designs;
- explain the expected dict -> SQLite change surface for each design;
- do not modify production code yet.
```

人 review 这个 model 后，第二阶段再形成 implementation contract。对 M02 lab，必须保持的行为和 non-goals 已经写在 [`../labs/02-state-ownership.md`](../labs/02-state-ownership.md)：本次练习要收敛 mutable authority，但**禁止**顺便引入 SQLite、async/thread lock、HTTP、remote worker、retry、新 status 或 dependency-injection framework。

这里有一个容易跨章混淆的细节：M02 lab 为了让“ownership refactor”成为单变量实验，明确把 `job-N` 格式、单调 ID 和 insertion-order claim 列为本次 **Must preserve**。这不等于课程宣称这些 behavior 永远应该成为 TaskForge 的 public contract；M03 lab 后半段会为自己的 testing exercise 显式采用另一份 contract scope，并据此重新审查哪些 tests 属于 overspecification。不同 exercise/change 可以有不同的局部 preservation contract，关键是把 authority 和 scope 写清楚，而不是悄悄切换。

实现完成以后，evidence 也不能只有“tests green”。至少要能证明：caller 修改 query result 不会改变 authoritative state；非法 transition 确实由 owner 拒绝；production code 没有明显绕过 owner 的直接 writes；并解释 repository search 为什么只能提供 syntactic evidence，不能单独证明完整 correctness。

课程维护侧另有一份 instructor-only reference，用 runtime exploit、static search 和 baseline tests 三种证据检查这条 pressure。Student-facing material 不直接导航到它，避免 first-pass system model 被 reference reasoning 污染。

## 10. Review 一个 abstraction，最后问的是 knowledge 和 authority

到这里可以把很多常见“设计原则”收回同一套判断，而不需要先猜 pattern：

### Abstraction / representation

- client 真正需要依赖哪些行为？
- 哪些 concrete representation 已经泄漏？
- 如果 representation 改变，哪些 client 会被迫改，为什么？
- read result 是 snapshot/projection，还是 authority-bearing handle？

### Information hiding / module depth

- 这个 module 隐藏了哪一份重要 design knowledge？
- 哪些知识仍被多个 caller 重复解释？
- decomposition 是按 cohesive knowledge 切，还是只按运行时间顺序切？
- 新增一层 abstraction 后，caller 真正少知道了什么？

### State ownership

- 谁创建、接受 mutation、validate、persist、recover/reconcile 这个 fact？
- request transition 与 authoritative transition 是否被区分？
- 是否存在第二份 writer 或可写 alias？
- storage、cache、replica、projection 是否被误当成 semantic owner？
- 某个 artifact 如果只投影一部分 state，scope 是否明确？

### Change / Agent

- 增加一个新状态或换 representation 时，change surface 为什么是现在这样？
- 正确 mutation path 是否显式、容易找到，还是旁边还有更短的 bypass？
- Agent 是否先恢复 authority map，再开始修改？
- tests/search/diff 能证明什么，又不能证明什么？

如果这些问题能被准确回答，你得到的就不只是“代码被封装了”，而是一份可以支撑后续修改的 system model。

下一章会立刻使用这份模型。M02 告诉我们：`get()` 不应该把 authoritative mutable object 随手交给 caller，lifecycle mutation 应该有明确 owner。M03 不会把这些结论当作“写过文档所以已证明”；它会问另一件事：**怎样设计 tests，使错误的 ownership change 会被发现，同时又不把 `dict`、`job-N` 之类当前 implementation accident 永久冻结成 contract？**

### 可选原始材料与来源边界

本章的 technical provenance 以 [`../reading-notes/m02-source-audit.md`](../reading-notes/m02-source-audit.md) 为准。主要采用：

- MIT 6.102 — Abstract Data Types：operations/specifications、opaque abstract values、representation independence；
- MIT 6.102 — Abstraction Functions & Rep Invariants：AF/RI、representation exposure 与 invariant maintenance；
- Stanford CS190 — Modular Design / code review materials：formal + informal interface、information hiding/leakage、temporal decomposition、design-it-twice 与具体 review pressure。

本章把这些 reasoning 扩展成 `semantic authority / storage / replica-cache / view-projection / writer map / recovery rule` 的长期系统分析框架；**这部分是课程综合模型**，不是 MIT 或 Stanford 原文术语。

Ousterhout/CS190 的 deep-module、change/cognitive-cost 等 vocabulary 在这里都只作为 design heuristic，不是“class 越大越好”或可计算的 metric。Stanford notes 会把 Parnas 的经典模块化论文作为历史来源，但当前 source audit **没有完成该论文的一手逐段审计**，因此本章不把它单独当作已经核验的 technical evidence。
