# M01 — Specification、Contract 与 Invariant

## 学习目标

学完这一章，你应该能够：

- 区分 implementation behavior、documented behavior 和真正需要承诺的 contract；
- 为一个操作写出 precondition、postcondition、side effects 和 error semantics；
- 解释为什么“类型签名”通常不是完整 specification；
- 为有状态系统定义 representation invariant / protocol invariant；
- 从 spec 推导 tests，而不是从当前实现反向复制 tests；
- 在给 Agent 任务时先定义 behavior table 和 invariants，再允许修改代码。

---

# 1. “这个函数对不对？”是个不完整问题

看一个简单函数：

```python
def pop_job(queue):
    return queue.pop(0)
```

你问：

> 这个实现对不对？

没有办法回答。

因为我们不知道它 **应该做什么**。

至少缺这些信息：

- 空 queue 怎么办？
- 是否允许修改传入 queue？
- 返回的是最早插入的 job 吗？
- queue 是否允许包含重复 job？
- 并发调用是否合法？
- exception 是 contract 的一部分吗？

implementation 只能相对于 specification 判断正确性。

因此软件工程里的第一条重要纪律是：

> **不要把“当前代码怎么做”误当成“系统应该怎么做”。**

---

# 2. Specification 是什么

一个 specification 描述的是：

> **从调用者可观察的角度，一个组件承诺什么行为。**

最简单可以写成：

```text
precondition
    +
operation
    ↓
postcondition / error / side effects
```

例如：

```python
def divide(a: int, b: int) -> float:
    ...
```

类型只告诉你：

```text
int × int → float
```

但 spec 还需要说：

```text
requires: b != 0
ensures: result == a / b
side effects: none
```

或者另一种设计：

```text
requires: none
ensures:
  - if b != 0, return a / b
  - if b == 0, raise ZeroDivisionError
```

这两个 design 都可以实现。

区别在于：**责任被分配给谁。**

---

# 3. Contract：不是文档装饰，而是责任分界

contract 可以理解为边界两边的责任分工。

```text
caller obligation
      ↓
   boundary
      ↓
implementation obligation
```

## 3.1 Precondition 是调用者的责任

如果 spec 写：

```text
requires: job_id exists
```

那么调用不存在的 job_id 属于 caller violation。

implementation 不一定必须定义结果。

但注意：在真实工程中，是否应该把某条件做成 precondition 是 **设计选择**。

例如 public HTTP API 通常不能说：

```text
requires: user always gives valid JSON
```

因为外部输入天然不可信。

相反，在一个内部 parser helper 中：

```text
requires: token stream has already passed lexical validation
```

可能很合理。

所以不是“precondition 越少越好”或“越多越好”。

要问：

> **哪一侧最有能力、最低成本地验证和处理这个条件？**

---

## 3.2 Postcondition 是实现者的责任

例如：

```text
reserve(job, worker)

requires:
- job.status == queued
- worker is active

ensures:
- job.status == running
- job.worker_id == worker.id
- started_at is set
```

如果 caller 满足 precondition，implementation 必须满足 postcondition。

这让调用者不需要知道：

- SQL 用什么语句；
- 是否加锁；
- row 在哪个表；
- 内部是否有 cache。

只要 contract 不变，实现可以替换。

这就是 abstraction 能独立演化的基础。

---

# 4. Specification 不只是函数输入输出

真实软件中，至少还要考虑四类东西。

## 4.1 Side Effects

例如：

```python
send_email(user)
```

如果只写：

```text
returns None
```

几乎没有信息。

真正重要的是：

- 是否真的发送邮件？
- 是否只是 enqueue？
- 是否可能重复发送？
- 返回前是否 durable？
- 网络失败怎样报告？

side effect 往往是 contract 最重要的部分。

---

## 4.2 Error Semantics

看一个 API：

```python
cancel(job_id) -> bool
```

`False` 是什么意思？

可能是：

- job 不存在；
- job 已完成；
- cancel request 被拒绝；
- worker 无法停止；
- storage error；
- timeout，但其实 server 已经成功处理。

如果把这些全压成 `False`，调用者无法正确决策。

错误设计要问：

- caller 能否恢复？
- 是否值得 retry？
- retry 是否安全？
- error 是否泄漏底层实现？
- 哪一层应该 translate error？

---

## 4.3 Temporal Semantics

一个操作何时“算完成”？

例如：

```text
cancel() 返回成功
```

可能表示：

A. cancellation request 已写入内存；

B. cancellation request 已 durable；

C. worker 已观察到 request；

D. subprocess 已退出；

E. 所有 side effects 已停止。

这些 contract 差异巨大。

在 distributed / concurrent system 中，**时间语义是 specification 的一部分。**

---

## 4.4 Concurrency Semantics

如果两个操作并发：

```text
finish(job)
cancel(job)
```

系统必须决定什么状态合法。

不能只说：

> “看线程调度。”

调度可以决定谁先执行，但 contract 必须决定：

- 两个操作是否都允许？
- 哪一个胜出？
- caller 能观察到什么？
- 是否存在非法中间状态？

---

# 5. 一个完整例子：TaskForge 的 `cancel`

我们先不要写代码。

定义一个行为表。

| 当前状态 | `cancel(job_id)` 行为 | 返回 | 新状态 |
|---|---|---|---|
| queued | durable 地标记取消 | success | cancelled |
| running | durable 地记录 cancellation requested | success | running/cancelling |
| succeeded | 不改变 | already_terminal | succeeded |
| failed | 不改变 | already_terminal | failed |
| cancelled | 幂等成功 | success | cancelled |
| missing | 不改变 | not_found | — |

仅这个表已经迫使我们做很多设计决策。

例如 running 时：

> 为什么不是立刻 `cancelled`？

因为如果 subprocess 还在运行，把状态写成 cancelled 会制造 false claim：系统说任务已停止，但现实世界 side effect 仍可能发生。

这说明：

> **状态名本身就是一个 contract。**

---

# 6. Invariant：跨操作、跨实现仍必须成立的东西

Specification 常描述一个操作。

Invariant 描述的是：

> **所有合法系统状态都必须满足的性质。**

## 6.1 Representation Invariant

假设：

```python
@dataclass
class Job:
    status: str
    worker_id: str | None
    started_at: datetime | None
    finished_at: datetime | None
```

可能定义：

```text
RI-1: status == queued => worker_id is None
RI-2: status == running => worker_id is not None
RI-3: status in terminal => finished_at is not None
RI-4: finished_at is not None => started_at is not None
```

这些规则比任何单个 method 更基础。

`submit`、`reserve`、`finish`、`cancel`、recovery 都必须维护它们。

---

## 6.2 Protocol Invariant

跨多个对象/进程也可以有 invariant。

例如：

```text
同一个 job 在任意时刻最多有一个 authoritative active attempt。
```

这不是单个 `Job` object 的 representation invariant。

它可能依赖：

- database unique constraint；
- lease；
- compare-and-swap；
- transaction；
- worker protocol。

但无论实现怎样，系统都要保持这个性质。

---

## 6.3 Durable Invariant

例如：

```text
如果 API 对 caller 确认 cancellation request 已接受，
那么 process crash/restart 后该 request 不能凭空消失。
```

这把 API contract 和 persistence 联系起来。

你会发现：

> **很多 architecture 决策，本质上是在决定如何维护 invariant。**

---

# 7. Invariant 的 owner 是谁？

识别 invariant 后，下一问非常重要：

> **谁负责保证它？**

坏设计经常是：

```text
API layer 假设 worker 会检查
worker 假设 repository 已验证
repository 假设 caller 不会传非法状态
```

结果就是：没人真正负责。

一种更好的思路：

```text
JobRepository.transition(...)
```

作为唯一 state transition boundary。

它可以保证：

- transition 合法；
- transaction atomic；
- invariant 写入后仍成立。

其他层不直接更新 `status`。

注意：这不意味着“一切都放 repository”。

而是：

> **每个 invariant 应该有清楚的 enforcement point。**

---

# 8. Strong / Weak Specification

spec 不是越详细越好。

考虑：

```python
get_users() -> list[User]
```

## Spec A

```text
返回所有用户，顺序未指定。
```

## Spec B

```text
返回所有用户，按数据库 primary key 升序。
```

如果用户并不需要顺序，Spec B 是不必要的 stronger promise。

一旦 client 依赖这个顺序，你以后：

- 换数据库；
- 并行查询；
- cache；
- shard；

都可能被 contract 限制。

因此 API 设计的重要原则之一是：

> **承诺用户真正需要的 behavior，但不要无意把 implementation accident 变成永久 promise。**

---

# 9. 但“少承诺”也不能成为偷懒借口

有人会把上面的原则误解为：

> 文档越模糊，未来越自由。

错误。

模糊 spec 会把复杂度转移给调用者。

例如：

```text
“这个函数通常会尽快返回。”
```

这不是有用 contract。

调用者无法决定 timeout、retry、resource management。

好的 abstraction 需要：

- **对用户重要的语义明确**；
- **对实现不重要的细节保留自由**。

这是 specification design，而不是少写文档。

---

# 10. Tests 应该从 Specification 推导

一个常见失败模式：

1. 先写实现；
2. 看实现怎么做；
3. 写测试验证实现确实这样做；
4. coverage 100%；
5. 误以为行为正确。

例如实现：

```python
def normalize(name):
    return name.strip().lower()
```

然后测试：

```python
assert normalize(" Alice ") == "alice"
```

但需求也许只说：

```text
去除首尾空格；大小写必须保留。
```

测试和实现高度一致，但它们一起错了。

所以测试的 oracle 应来自：

- spec；
- external protocol；
- product requirement；
- invariant；
- known compatibility behavior；

而不是当前代码本身。

---

# 11. 从 Spec 系统地产生测试

假设：

```text
cancel(job_id)
```

我们可以从 contract 列 partitions：

### State partition

```text
queued
running
succeeded
failed
cancelled
missing
```

### Repetition partition

```text
first cancel
second cancel
many retries
```

### Concurrency partition

```text
cancel before reserve
cancel races reserve
cancel races finish
```

### Durability partition

```text
crash before durable write
crash after durable write but before response
restart after successful response
```

### Failure partition

```text
DB unavailable
worker unreachable
subprocess refuses termination
```

这比“再补几个测试”有原则得多。

---

# 12. Specification 与 Compatibility

一旦外部用户依赖某个行为，改变它就可能变成 breaking change。

但现实里还有一个麻烦：

> 用户可能依赖你从没想承诺、但长期稳定存在的 observable behavior。

例如：

- iteration order；
- error message text；
- timing；
- undocumented field；
- retry pattern。

后面 Dependency/Compatibility 模块会深入讨论。

这里先记住：

> **公开 implementation behavior 的时间越久，它越可能事实性变成 contract。**

所以边界设计越早清楚，长期维护成本越低。

---

# 13. “Make Illegal States Unrepresentable” 应该怎么理解

这是一个很强但容易被口号化的思想。

例如：

```python
@dataclass
class Job:
    status: str
    worker_id: str | None
```

允许：

```text
status = queued
worker_id = "w7"
```

但这个状态按 invariant 是非法的。

可以改成：

```python
QueuedJob(...)
RunningJob(worker_id=...)
FinishedJob(...)
```

让类型结构减少非法组合。

但不要走极端。

如果状态非常动态，过度 encoding 到类型系统可能：

- 类型数量爆炸；
- serialization 复杂；
- migration 困难；
- runtime state machine 仍不可避免。

正确问题不是：

> “能不能全部用类型表达？”

而是：

> **哪些重要 invariant 值得尽早、自动、低成本地 enforcement？**

工具可以是：

- type system；
- constructor；
- database constraint；
- transaction；
- assertion；
- property test；
- state machine；
- review rule。

---

# 14. 一个设计技巧：先写 State Machine

对有 lifecycle 的东西，先别写 if/else。

先写状态转换图：

```text
            reserve
 queued  ------------> running
   |                     |   \
   | cancel              |    \ fail
   v                     |     v
cancelled                |   failed
                         |
                         | finish
                         v
                      succeeded
```

然后明确：

```text
terminal = {cancelled, failed, succeeded}
terminal 不允许离开 terminal
```

再问每条边：

- 谁能触发？
- atomic 吗？
- 需要 durable 吗？
- concurrent transition 怎么 resolve？
- crash 在边中间怎么办？

这比在代码里发现十几个 status `if` 后再猜 lifecycle 清楚得多。

---

# 15. Specification Review Checklist

当你 review 一个 API 或 Agent task，问：

## Inputs
- 哪些输入合法？
- validation 在哪一层？
- caller 违反 precondition 会怎样？

## Outputs
- 返回值准确表达哪些状态？
- 有没有把多种错误压成一个 ambiguous boolean/null？

## Side effects
- side effect 是同步还是异步？
- 返回前达到什么 durability / visibility guarantee？

## Errors
- 哪些 retryable？
- retry 是否幂等？
- 是否泄漏内部实现 error？

## Concurrency
- 并发调用是否合法？
- race 的 winner 如何定义？
- 有没有 check-then-act gap？

## Invariants
- 哪些性质永远必须成立？
- enforcement point 是谁？

## Compatibility
- 哪些 behavior 是用户真正依赖的？
- 有没有无意新增 stronger promise？

---

# 16. Agent 时代：先让 Agent 写 Contract，不要先写 Code

一个非常实用的 workflow：

## Phase 1 — Read-only reconnaissance

要求 Agent：

```text
不要修改代码。
找到该行为当前所有入口、state owner、storage、tests、error path。
用代码位置证明。
```

## Phase 2 — Behavioral model

要求输出：

```text
1. current behavior table
2. desired behavior table
3. invariants
4. compatibility constraints
5. unresolved ambiguities
```

人先 review 这一层。

## Phase 3 — Change design

```text
哪些模块必须改？
哪些不应该改？
有没有需要 migration？
怎样 staged rollout？
```

## Phase 4 — Implementation

才允许 Agent 修改代码。

## Phase 5 — Evidence

要求 Agent 提供：

- 哪个测试修复前失败；
- 哪个测试保护旧 behavior；
- 哪个 runtime reproduction 验证 failure path；
- 有没有静态/类型/DB constraint 直接 enforcement invariant。

## Phase 6 — Independent Review

不要只问同一个 Agent：

> “你确定没问题吗？”

重新从 contract 出发 review patch。

这就是 specification 对 Agent workflow 的直接价值。

---

# 17. 练习

## Exercise 1 — 从实现中剥离 accidental behavior

给定：

```python
def list_jobs(db):
    rows = db.execute("SELECT * FROM jobs ORDER BY id")
    return [decode(x) for x in rows]
```

回答：

1. 哪些 behavior 是代码表现出来的？
2. 哪些必须成为 spec？
3. `ORDER BY id` 是否应该成为 contract？为什么？
4. 如果删掉 order 后某 client 失败，说明什么？

---

## Exercise 2 — 写一个真正完整的 `cancel` contract

至少包含：

- state table；
- idempotency；
- durability；
- concurrency；
- error semantics；
- retry behavior；
- non-goals。

禁止出现：

```text
“取消任务，成功返回 True。”
```

这种不够的信息。

---

## Exercise 3 — 找 Invariant 的 Enforcement Point

在一个你熟悉的 repo 里找一个 lifecycle/state：

```text
session
job
request
transaction
connection
cache entry
```

列出：

- invariant；
- 所有可能修改它的位置；
- 当前真正的 enforcement point；
- 是否存在多个 authority；
- 如果 Agent 新增一个写路径，会发生什么。

---

## Exercise 4 — Tests Against Spec

选择一个函数：

1. 暂时不看实现，读 API/requirements；
2. 写 behavior partitions；
3. 写测试；
4. 再看实现；
5. 记录有哪些当前 behavior 你没有测试，因为它不是 contract；
6. 记录有哪些 spec behavior 当前实现根本没做到。

---

# 18. 本章结论

软件系统能够被多人/多 Agent 并行修改，一个根本原因是：

> **边界两边不需要知道彼此全部实现，只需要共享足够准确的 contract。**

而 invariant 让我们能跨多个操作、多个模块、甚至 crash/restart 推理“系统仍然合法吗”。

因此在任何实现之前，先问：

```text
What must be true?
Who guarantees it?
What may the other side rely on?
What evidence will show that we preserved it?
```

下一章会继续问一个自然问题：

> 如果 contract 是边界两边的协议，那么 **边界本身应该怎么划？**

也就是 Abstraction、Information Hiding 与 State Ownership。

---

## 可选原始资料

本章自包含；下面材料用于进一步交叉学习：

- MIT 6.102 Specifications: https://web.mit.edu/6.102/www/sp26/classes/04-specifications/
- MIT 6.102 Designing Specifications: https://web.mit.edu/6.102/www/sp26/classes/05-designing-specs/
- MIT 6.102 AF/RI: https://web.mit.edu/6.102/www/sp26/classes/07-abstraction-functions-rep-invariants/
