# M02 — Abstraction、Information Hiding 与 State Ownership

> 本章目标：从“把代码分成几个类/文件”提升到“让变化、知识和状态都有明确归属”。

上一章讨论了 specification、contract 与 invariant。现在我们进入一个更困难的问题：

> **这些 contract 和 invariant 应该由谁负责？**

这是软件设计真正开始的地方。

很多代码库表面上已经“模块化”了：有很多文件、class、interface，字段甚至都是 `private`。但一旦加一个需求，你仍然可能需要同时修改十几个地方；一旦某个状态出错，你也不知道哪个模块说了算。

这说明：

> **语法上的封装不等于工程上的信息隐藏；代码里只有一份变量，也不等于系统里只有一个 authority。**

本章建立三层模型：

1. **Abstraction**：使用者应该依赖什么概念，而不是依赖什么表示；
2. **Information Hiding**：哪些设计知识必须被局部化；
3. **State Ownership**：哪个组件有权决定某个事实是什么、怎样变化。

这三层共同决定一个系统是否真的“ready for change”。

---

## 1. 从一个很普通的坏设计开始

假设我们有一个后台任务系统 TaskForge。

最初代码只有几个模块：

```text
api.py
worker.py
metrics.py
state.py
```

`state.py` 里有：

```python
jobs = {}
next_job_id = 1
```

然后：

- `api.py` 创建 job，直接写 `jobs`；
- `worker.py` claim job，直接改 `jobs[job_id].status`；
- `api.py` cancel job，也直接改 `status`；
- `metrics.py` 遍历 `jobs` 计算 queued count；
- 测试为了清空环境，也直接 `jobs.clear()`。

功能完全可以跑。

甚至代码还很短。

但现在加几个需求：

1. `RUNNING` 的 job 不能直接 cancel，只能先发 cancellation request；
2. job ID 以后需要从 SQLite 恢复，重启不能重复；
3. worker claim 时必须原子地从 `QUEUED -> RUNNING`；
4. API 查询到的 job 不能让调用方直接修改内部状态；
5. 以后可能有 remote worker。

突然你发现每个需求都需要知道：

```text
谁在写 jobs？
谁在生成 ID？
谁在解释 status？
谁保证状态转移合法？
谁把内存状态和持久化状态保持一致？
```

如果答案是“很多地方都知道一点”，那真正的问题不是某个函数写得不好。

真正的问题是：

> **设计知识和修改权限没有清晰的 owner。**

---

# 2. Abstraction 到底是什么

“抽象”这个词非常容易被讲空。

一个实用定义是：

> **Abstraction 是一组允许调用者依赖的概念与行为，同时故意省略实现这些行为所不需要知道的细节。**

比如一个 `JobQueue` 的抽象可能是：

```text
submit(command) -> JobId
claim() -> Job | None
cancel(job_id) -> outcome
get(job_id) -> JobView
```

调用者应该依赖的是：

- job 有 identity；
- job 有 lifecycle；
- claim 会取一个可运行 job；
- cancel 有明确结果。

调用者不应该必须知道：

- job 放在 list、dict 还是 SQLite；
- ID 是整数、UUID 还是数据库 sequence；
- queue 是按数组扫描还是 heap；
- 内存里是否有 cache；
- 一次 transition 实际写几张表。

MIT 6.102 对 ADT 的一个关键表述就是：**抽象类型由它的 operations 及其 specification 定义，而不是由内部 representation 定义。** 课程进一步用 representation independence 检查：替换内部 representation 时，client 是否需要变化。

这个检查极有用：

> **如果我把内部表示完全换掉，哪些外部代码必须跟着改？为什么？**

如果答案是“大量 client 都必须知道”，说明 abstraction 没有真正成立。

---

# 3. Interface 不只是函数签名

很多人把 interface 理解成：

```python
def submit(command: str) -> str:
    ...
```

但真正的 interface 远比签名大。

调用者可能还必须知道：

- `submit()` 是否立即持久化；
- 是否可能返回重复 ID；
- callback 会不会同步调用；
- 返回对象能不能修改；
- 调用 `close()` 以后还能不能 `submit()`；
- error 是否代表“确定失败”还是“结果未知”；
- 两个并发调用之间有什么 ordering；
- 某个方法必须在另一个方法之后调用。

这些全是 interface 的一部分。

Stanford CS190 的 modular design notes 特别强调：interface 包含 formal aspects，也包含 informal aspects；后者包括 side effect、调用者必须理解的行为和设计决定。

所以：

> **`private` 只隐藏语法可见性；它不能自动隐藏语义依赖。**

例如：

```python
class Queue:
    def __init__(self):
        self._jobs = []

    def first(self):
        return self._jobs[0]
```

虽然 `_jobs` 是 private，但如果所有调用者都知道：

```text
index 0 一定是 oldest queued job
```

并且业务逻辑依赖这个事实，那么这个 representation decision 已经泄漏了。

---

# 4. Information Hiding：隐藏的是“设计知识”

Parnas 式 modularity 和 Ousterhout 的 information hiding 都指向同一个非常重要的直觉：

> **模块应该围绕容易变化、代价高、调用者不应知道的设计决定建立边界。**

这里的“information”不是“数据不能被别人看到”。

它更接近：

```text
为了正确修改这个系统，你必须知道的设计知识。
```

例如 TaskForge 中这些都是应该考虑隐藏的知识：

- job ID 如何分配；
- 哪些 status transition 合法；
- claim 怎样选择 job；
- terminal state 怎样定义；
- cancel 对 running job 的语义；
- persistence transaction 怎么组织；
- restart 时怎样恢复 incomplete work。

如果这些规则散落在多个模块：

```text
api.py       知道一点
worker.py    知道一点
storage.py   知道一点
metrics.py   又复制一点
```

那么添加新状态 `CANCELLING` 时，你就必须进行全仓同步修改。

这叫 **information leakage**。

---

# 5. 一个非常实用的判断：变化是否被局部化

设计质量很难直接测量，但 change amplification 是一个很好用的 proxy。

假设我们把状态从：

```text
QUEUED -> RUNNING -> SUCCEEDED | FAILED
```

扩展成：

```text
QUEUED
  ↓
RUNNING -> CANCELLING -> CANCELLED
  ↓
SUCCEEDED | FAILED
```

设计 A：

```text
api.py       自己判断 transition
worker.py    自己判断 transition
cli.py       自己判断 terminal
metrics.py   自己复制 status 集合
storage.py   自己知道哪些状态需要 persist
```

设计 B：

```text
JobRegistry / JobLifecycle
    ├── transition rules
    ├── state mutation
    └── query semantics

api / worker / cli / metrics
    只通过明确操作访问
```

两个设计当前都能跑。

但增加 `CANCELLING` 时：

- A 要同步修改多个地方，而且你必须先找到所有 hidden assumptions；
- B 的核心规则更可能集中在一个 owner 附近，其他模块只在确实需要新行为时变化。

这不是“文件越少越好”。

而是：

> **同一种设计知识应该尽可能只有一个 authoritative home。**

---

# 6. Representation Independence：一个很强的设计测试

考虑下面两个 API。

### API A

```python
def all_jobs() -> dict[str, Job]:
    return jobs
```

调用者可以：

```python
jobs = all_jobs()
jobs["j-7"].status = Status.SUCCEEDED
```

这意味着调用者不仅知道 representation 是 dict，还获得了修改 authority。

以后你想换成 SQLite：

```text
内存 dict 不再是完整事实
```

大量调用者就会失效。

### API B

```python
def get(job_id: JobId) -> JobView:
    ...

def list_jobs() -> tuple[JobView, ...]:
    ...

def complete(job_id: JobId, exit_code: int) -> CompleteResult:
    ...
```

client 只依赖操作和结果。

内部可以从：

```text
dict
```

换到：

```text
SQLite
```

甚至：

```text
remote service
```

只要 contract 不变。

这就是 representation independence 的工程价值。

一个非常值得反复问的问题：

> **这个 client 依赖的是业务语义，还是偶然的内部表示？**

---

# 7. Encapsulation ≠ Information Hiding

考虑：

```python
class Scheduler:
    def __init__(self):
        self._jobs = {}

    def jobs(self):
        return self._jobs
```

字段虽然是 private，但返回了原对象。

这叫 representation exposure。

再看一个更隐蔽的例子：

```python
class Scheduler:
    def raw_status(self, job_id):
        return self._jobs[job_id].status_code
```

假设 `status_code` 是：

```text
0 = queued
1 = running
2 = done
3 = failed
```

client 到处写：

```python
if scheduler.raw_status(job_id) >= 2:
    ...
```

即使没有任何 mutable object 泄漏，representation knowledge 仍然泄漏了。

所以真正的问题不是：

> 字段有没有 private？

而是：

> **修改内部设计时，外部到底需要知道多少？**

---

# 8. Deep Module：有用，但不要把它变成公式

Ousterhout 用 deep module 描述一种理想：

```text
提供很多有价值的功能
-------------------
暴露相对简单的 interface
```

相反 shallow module：

```text
功能很少
-------------------
但 interface / dependency / lifecycle 成本不少
```

这个概念特别适合反驳一种机械规则：

> “类越小越好，函数越小越好。”

每增加一个 module，都可能增加：

- 一个名字；
- 一组 API；
- 一条 dependency edge；
- 一个 lifecycle；
- 一个 failure boundary；
- 一个需要维护的 mental model 节点。

所以拆分不是免费的。

但是也不能反过来变成：

> “大类更好。”

真正要问：

> **这个 module 是否隐藏了足够重要的复杂度？**

如果一个 1500 行 module 隐藏了一个稳定、清晰、单一的复杂机制，可能是 deep。

如果它只是把五种无关职责塞在一起，仍然是坏设计。

因此不要计算：

```text
implementation LOC / API method count
```

然后得出“depth score”。

deep module 是 reasoning tool，不是 metric。

---

# 9. Temporal Decomposition：按执行顺序切代码，常常泄漏知识

一个常见拆法是：

```text
LoadJob
ValidateJob
PersistJob
PublishJob
```

因为运行时就是按这个顺序发生。

这看上去“单一职责”。

但如果四个模块都必须共同知道：

```text
Job schema
transaction boundary
which fields are durable
when an ID becomes externally visible
what failure means after persist but before publish
```

那么你只是按照时间把一个 cohesive design decision 切碎了。

Ousterhout 的课程把这种情况叫 temporal decomposition，并把它视为 information leakage 的常见来源。

一个更好的切法可能是：

```text
JobRepository
    负责 durable representation + transaction rules

JobService
    负责 externally visible lifecycle semantics
```

这里模块边界由“知识归属”决定，而不是由“先做 A 再做 B”的时间顺序决定。

---

# 10. State Ownership：比“single source of truth”更精确

工程讨论里经常说：

> single source of truth

这个词有帮助，但太模糊。

例如：

- SQLite 是 source of truth 吗？
- 内存 state machine 是 source of truth 吗？
- remote controller 是 source of truth 吗？
- worker 本地执行状态是 source of truth 吗？

更精确的问题是：

> **对于一个事实，谁有 authority 接受它的合法变化？**

我们把几个角色区分开。

## 10.1 Authority / Owner

有权决定某个逻辑事实如何变化的组件。

例如：

```text
JobRegistry owns logical job lifecycle.
```

它决定：

```text
QUEUED -> RUNNING 是否合法
RUNNING -> SUCCEEDED 是否合法
FAILED -> RUNNING 是否允许 retry
```

## 10.2 Storage

负责让事实 survive process lifetime 的机制。

例如：

```text
SQLite stores job state durably.
```

storage 不一定等于 semantic owner。

SQL 表里可以允许写入任何字符串，但应用层仍可能规定：

```text
status 必须满足 lifecycle transition rules
```

## 10.3 Replica / Cache

为了性能或 locality 保存的 derived copy。

它不是 authority。

如果 cache 与 owner 冲突：

```text
owner wins
```

或者系统必须有明确 reconciliation protocol。

## 10.4 View / Projection

为了 UI、metrics、search 等用途派生出的 representation。

例如：

```text
queued_job_count
recent_failed_jobs
```

这些应该可以从 authoritative facts 重新构建。

---

# 11. “谁存数据”与“谁拥有状态”不是同一个问题

假设：

```text
Controller
   ↓
SQLite
```

Controller 每次 transition 都写数据库。

有人会说：

> “那 SQLite 才是 owner，因为数据在那里。”

不一定。

如果只有 Controller 有权决定：

```text
RUNNING -> SUCCEEDED
```

而 SQLite 只是事务性保存结果，那么：

```text
semantic authority = Controller
persistence authority = SQLite transaction
```

当然，也可以设计成数据库 constraint / stored procedure 本身拥有部分 invariant。

关键不是哪一种永远正确。

关键是：

> **authority 必须明确，而且 invariant 的 enforcement point 必须与 authority 对齐。**

---

# 12. State Ownership 需要回答的五个问题

对系统中每一类重要 state，都问：

### 1. Who creates it?

谁创建第一份合法状态？

### 2. Who may mutate it?

哪些组件有权触发 transition？

注意：

```text
request a transition
```

和：

```text
perform the authoritative transition
```

是不同的。

worker 可以请求：

```text
complete job 42
```

但最终是否接受这个 transition，可以由 controller 决定。

### 3. Who validates it?

谁保证 invariant？

如果每个调用者都写：

```python
if status == RUNNING:
    status = SUCCEEDED
```

那 invariant enforcement 已经分散。

### 4. Who persists it?

谁负责 durable commit？

特别要问：

```text
side effect 和 state transition 之间的 crash window 怎么办？
```

### 5. Who reconstructs/reconciles it after failure?

process restart 后：

```text
RUNNING job 到底是什么？
```

owner 必须有恢复语义。

---

# 13. Split Authority：最危险的设计味道之一

假设 API server 有：

```python
active_jobs: dict[str, Job]
```

worker manager 又有：

```python
running_jobs: dict[str, Job]
```

两者都能改 status。

你现在有两份 authority。

典型 failure：

```text
API: job 7 = CANCELLED
Worker manager: job 7 = RUNNING
```

接下来所有代码都开始问：

```text
“哪个才是真的？”
```

于是工程师加：

```text
sync()
refresh()
reconcile()
```

有时这是分布式系统不可避免的 protocol；但很多单进程系统里，它其实只是设计错误制造出的伪分布式问题。

所以看到第二份 mutable copy 时不要只问：

> 怎么同步？

先问：

> **为什么它需要成为第二个 writer？它能不能只是 replica/view？**

---

# 14. Ambient Global State：为什么特别伤 mental model

例如：

```python
settings = load_settings()
registry = {}
current_workspace = None
```

然后任何模块都：

```python
from state import registry
```

这种设计的问题不只是“不好测试”。

它让 dependency 变成 invisible。

函数签名：

```python
def run_job(job_id):
    ...
```

看上去只依赖 `job_id`。

实际上它依赖：

```text
global registry
global settings
current process cwd
environment variables
```

这会制造大量 unknown unknowns。

显式 dependency：

```python
def run_job(job_id, registry, executor):
    ...
```

虽然参数更多，却更容易推理。

目标不是“任何 global 都禁止”。

immutable constant 没问题；process-wide registry 也可能有合理场景。

真正危险的是：

> **可变的、拥有业务语义的 ambient authority。**

---

# 15. State Owner 的 interface 应该表达 semantic operation

坏接口：

```python
def jobs() -> dict[str, Job]:
    ...
```

调用者自己实现：

```python
jobs()[id].status = RUNNING
```

好一些：

```python
def claim_next() -> JobView | None:
    ...
```

为什么？

因为 `claim_next()` 隐藏了：

- 哪些状态可 claim；
- claim selection policy；
- transition rule；
- mutation；
- 将来可能需要的 transaction。

这里有一个核心设计原则：

> **把“需要共享的数据结构”尽量升级成“拥有语义的操作”。**

也就是从：

```text
Give me your state, I will manipulate it.
```

变成：

```text
Please perform this domain operation under your invariant.
```

这对 Agent 特别重要。

Agent 很擅长看到一个 dict 然后直接改。

如果 boundary 没表达语义，它会自然选择最短 implementation path，而不是长期正确的 authority path。

---

# 16. Query 与 Command 可以不对称

一个常见误区是：

> 所有读取和写入都必须走完全相同的 abstraction。

不一定。

例如：

```text
commands:
  submit
  claim
  cancel
  complete
```

必须经过 owner，因为会改变 invariant。

但是 query：

```text
list_recent_jobs
queued_count
```

可以从 read model、cache、index 读取。

只要它们明确是：

```text
projection / replica
```

而不是第二份 write authority。

所以 ownership 不是要求：

```text
所有数据只能存在一份
```

而是要求：

```text
谁能定义事实，谁只是复制/观察事实，必须清楚。
```

---

# 17. Dependency Direction：让 policy 不依赖 accident

考虑：

```text
JobService -> SQLiteJobRepository
```

如果 `JobService` 到处写 SQLite SQL：

```python
conn.execute("update jobs set ...")
```

那么 lifecycle policy 与 storage representation 耦合。

另一种设计：

```text
JobService -> JobRepository protocol
                    ↑
             SQLiteJobRepository
```

这不意味着“任何地方都要 dependency inversion”。

只有当：

- storage 确实可能变化；
- policy 与 mechanism 值得独立测试；
- concrete dependency 让重要知识泄漏；

这种边界才值得建立。

不要因为教材说“依赖接口”就给每个小函数造一个 interface。

否则你会制造 shallow abstractions。

---

# 18. 好的 abstraction 不是“更通用”，而是“隐藏正确的东西”

假设你需要 job storage。

有人马上设计：

```python
class GenericRepository[T, K, Query, Transaction, ...]:
    ...
```

看上去非常 reusable。

但课程不鼓励这种 reflex。

我们更关心：

```text
TaskForge 当前最需要隐藏的变化是什么？
```

可能只是：

```text
Job lifecycle state + durable representation
```

那么一个针对 Job 语义的 repository 可能更好。

所谓 general-purpose module 只有在它真的消除了多个调用者必须重复理解的复杂机制时才有价值。

否则它只是把未来猜测编码成 abstraction。

---

# 19. Information Hiding 与 DRY 不是同一件事

两段代码看起来重复：

```python
if status in (SUCCEEDED, FAILED, CANCELLED):
    ...
```

真正重复的是：

```text
“哪些状态是 terminal”这个知识。
```

所以应该抽象为：

```python
def is_terminal(status):
    ...
```

或者更深地让 lifecycle owner 提供：

```python
job.is_terminal
```

但另外两段碰巧都是：

```python
for item in items:
    validate(item)
```

它们可能属于不同 domain，未来独立演化。

把它们抽成一个 generic helper 不一定隐藏任何有价值的知识。

因此：

> **优先消除 duplicated knowledge，而不是机械消除 duplicated syntax。**

---

# 20. 一个设计练习：谁应该拥有 Job status？

候选方案：

### A. Job object 自己

```python
job.complete(exit_code)
```

优点：

- transition rules 可以靠近 data；
- 单对象 invariant 清晰。

问题：

- 如果 transition 必须和 persistence transaction 原子提交怎么办？
- 多 job policy 怎么办？

### B. JobRegistry

```python
registry.complete(job_id, exit_code)
```

优点：

- 可以统一控制 collection + lifecycle；
- 更容易接 persistence；
- ID allocation 也可以统一。

问题：

- Registry 可能膨胀成 god object。

### C. Worker

```python
worker.jobs[id].status = SUCCEEDED
```

优点：

- implementation 最短。

问题：

- worker 获得了不必要的 lifecycle authority；
- controller/API 与 worker 很容易 split-brain；
- remote worker 时更难演化。

不存在只看类图就能确定的唯一答案。

你要根据 invariant 和未来变化判断。

但通常可以明确淘汰一些设计：

> **如果一个组件不负责某个 invariant，却能绕过 owner 直接改变该 invariant，它拥有了过多 authority。**

---

# 21. Review 一个 abstraction 时，不要先问“用了什么 pattern”

先问这几个问题。

## 21.1 这个模块隐藏什么？

如果答案只是：

```text
“它把三个 helper function 放在一起。”
```

可能没有真正 abstraction。

更好的回答类似：

```text
它隐藏 job ID allocation、legal lifecycle transitions 和 internal storage representation。
```

## 21.2 哪些知识仍然泄漏给 client？

例如：

```text
client 必须知道 status 数字编码
client 必须先 call load 再 call mutate
client 必须手动 acquire lock
```

这些都是 leakage candidate。

## 21.3 representation 能换吗？

把：

```text
dict -> SQLite
```

或者：

```text
local executor -> remote executor
```

思想实验一遍。

如果大量 client 必须改，找出具体泄漏。

## 21.4 谁拥有 mutable state？

把所有 writer 列出来。

如果列表长成：

```text
api.py
worker.py
scheduler.py
cleanup.py
tests fixture
```

需要高度警惕。

## 21.5 invariant enforcement 在哪里？

如果回答：

> “每个调用方都自己检查。”

通常意味着 authority 没有收敛。

---

# 22. Agent 时代为什么这个问题更严重

人类工程师看到：

```python
state.jobs[job_id].status = Status.RUNNING
```

可能会停下来问：

> “这样写是不是绕过了 lifecycle owner？”

coding agent 的默认倾向往往是：

> 找到最短的能让测试通过的修改路径。

如果当前 repo 已经有两种访问方式：

```text
registry.transition(...)
```

和：

```text
state.jobs[id].status = ...
```

Agent 很可能复制更直接的第二种。

于是局部 technical debt 会被生成速度放大。

因此，在 Agent 时代，好的 boundary 有一个额外价值：

> **它不仅降低人类误用概率，也缩小 Agent 的可行错误空间。**

如果正确路径是唯一、显式、容易发现的，Agent 更容易做对。

---

# 23. 如何给 Agent 一个 State Ownership 任务

差的 prompt：

```text
重构一下 job state 管理，让代码更优雅。
```

它没有告诉 Agent：

- 什么不能改变；
- 什么问题要解决；
- authority 应该在哪里；
- 哪些行为是 contract；
- 什么叫完成。

更好的 engineering spec：

```text
目标：收敛 TaskForge 的 job lifecycle authority。

现状：
- api.py、worker.py 都会直接修改 module-level jobs dict；
- get/list 返回内部可变 Job 对象；
- job ID allocator 也是 module global。

必须保持：
- submit 返回格式仍为 job-N；
- claim 仍按 insertion order 选择第一个 QUEUED job；
- 现有 cancel/finish observable behavior 不变，除非下面明确要求。

设计约束：
- mutable job collection 与 ID allocator 只能有一个 authoritative owner；
- lifecycle transition 只能通过 owner 的 semantic operations 完成；
- read API 不得把 authoritative mutable Job object 暴露给 caller；
- worker 只能 request claim/complete，不直接拿内部 collection；
- 不引入 persistence、async、HTTP；这些是 non-goals。

验证：
- 现有 tests 必须通过；
- 新增 tests 证明 caller 修改 query result 不会修改内部 state；
- 用 repo search 证明生产代码没有绕过 owner 的直接 writes；
- 解释未来 dict -> SQLite 时哪些 client 不需要变化。
```

这才是在“指挥 Agent 做工程”。

---

# 24. 但不要把 architecture 在 prompt 里写死

上一节看起来已经指定了 owner。

真实任务中还要注意另一种失败：

> 人提前猜了一个错误 architecture，然后要求 Agent 精确执行。

更成熟的方式是分两阶段。

### Phase 1 — Read-only design reconnaissance

要求 Agent：

```text
列出所有 state writers
列出所有 read paths
找出 lifecycle invariants
找出当前 tests actually protect 的 behavior
提出至少两个 ownership design
比较 trade-off
```

### Phase 2 — implementation contract

人确认 design 后再实施。

也就是说：

> **Agent 不是只能做机械实现；它可以参与 design search，但 engineering authority 不能因为它能提出方案就被默认交出去。**

---

# 25. TaskForge M02 Lab

本章实验位于：

```text
labs/taskforge/
```

当前 v0 故意保留一个“功能正确但 ownership 很差”的实现。

先不要直接重构。

第一步只读回答：

1. 所有 job state 的 writer 在哪里？
2. 所有 ID allocator 的 writer 在哪里？
3. 哪些函数返回了 authoritative mutable object？
4. 哪些 lifecycle knowledge 被复制？
5. 当前 tests 保护的是 contract，还是 implementation accident？
6. 如果下一章把内存 dict 换成 SQLite，哪些调用者会被迫改？

然后完成 `labs/02-state-ownership.md` 中的设计与实现任务。

---

# 26. 本章应该形成的 mental checklist

面对陌生 repo，遇到一个 mutable concept：

```text
session
job
config
cache
workspace
connection
request
model registry
scheduler state
```

不要只搜变量名。

你要建立一张 authority map：

```text
Fact
 ├── owner / authority
 ├── writers
 ├── readers
 ├── invariant
 ├── persistence
 ├── replicas/views
 └── recovery rule
```

然后问：

```text
writer 是否都经过 owner？
owner 是否真的能 enforce invariant？
client 是否依赖 representation？
derived copy 是否偷偷变成第二 authority？
failure/restart 后谁重新建立事实？
```

如果能稳定回答这些问题，你已经不再只是“读代码”。

你在建立一个可用于安全修改的 system model。

---

# 27. Design Questions

完成本章后，你应该能对任何 module 提出以下问题：

- 它隐藏了什么 design knowledge？
- interface 暴露了哪些 formal 与 informal dependency？
- 哪些细节只是 representation？
- representation 能否独立变化？
- 是否存在 representation exposure？
- 是否因为 temporal decomposition 把共同知识拆散？
- 这个 module 是否足够 deep，还是只是增加了一层名字？
- mutable state 的 authority 在哪里？
- storage、owner、cache、view 是否被混为一谈？
- 有多少 writer？
- invariant enforcement point 在哪里？
- 出错/重启以后谁负责恢复？
- Agent 是否可以绕过 intended boundary 找到更短的直接修改路径？

---

# 28. 外部材料：本章实际采用什么

本章是 self-contained 的；外部材料用于交叉验证和扩展。

## MIT 6.102 — Abstract Data Types

https://web.mit.edu/6.102/www/sp25/classes/06-abstract-data-types/

采用：

- ADT 由 operations + specs 定义；
- representation independence；
- client 不应依赖 concrete representation；
- good ADT 应 simple/coherent/adequate。

不直接照搬：

- 课程主要在单进程、对象/ADT 层讨论；
- 本章把同一思想扩展到 service、process、persistent state ownership。

## MIT 6.102 — Abstraction Functions & Rep Invariants

https://web.mit.edu/6.102/www/sp26/classes/07-abstraction-functions-rep-invariants/

采用：

- representation exposure 会破坏 invariant 与 representation independence；
- invariant 必须由 creator/mutator 等操作系统性建立和保持。

## Stanford CS190 — Modular Design

https://web.stanford.edu/~ouster/cgi-bin/cs190-spring16/lecture.php?topic=modularDesign

以及：

https://web.stanford.edu/~ouster/cgi-bin/cs190-winter18/lecture.php?topic=modularDesign

采用：

- interface 不只包含函数签名，还包括调用者必须知道的行为知识；
- information hiding / information leakage；
- private variable 不自动等于 information hiding；
- temporal decomposition 是常见 leakage；
- module/class 的价值应看它隐藏了什么。

保留意见：

- “thick/deep class”是经验性设计 heuristic，不是数学定律；
- 本课程不把 class 当成唯一 module unit，也不鼓励为了追求 depth 制造 god object。

## Stanford CS190 — Raft Project Review

https://web.stanford.edu/~ouster/cgi-bin/cs190-winter19/lecture.php?topic=raftReview1-2019

这份 review notes 的价值在于它展示了概念如何落到真实学生设计：通信层、persistent state、message representation 等位置的信息泄漏会被直接讨论，而不是只背定义。

---

# 29. 小结

本章最重要的几句话：

> **Abstraction 决定 client 可以依赖什么。**

> **Information hiding 决定哪些设计知识应该只在局部存在。**

> **State ownership 决定谁有权改变事实并维护 invariant。**

一个系统真正容易演化，不是因为：

```text
文件很多
class 很小
interface 很多
字段都是 private
```

而是因为：

```text
变化有局部边界
知识有明确归属
状态有明确 authority
invariant 有明确 enforcement point
client 依赖语义而不是 representation
```

这也是 Agent 时代最值得保护的东西：

> **让正确的修改路径成为最自然、最显式、最容易验证的路径。**
