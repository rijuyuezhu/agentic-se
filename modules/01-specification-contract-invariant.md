# M01 — Specification、Contract 与 Invariant

M00 里，TaskForge 的 `cancel(job_id)` 从几行代码一路长出了 durability、concurrency、state transition 和 compatibility 问题。现在假设实现者已经交来一个 patch，tests 也全绿。reviewer 问了一句看似最简单的话：**这个实现对不对？**

如果我们还说不清 `cancel` 应该做什么，这个问题其实没有答案。本章的目标就是把“应该为真什么”从模糊直觉变成可以讨论、实现、测试和 review 的 engineering artifact。

## 1. 两个实现都能跑，哪个才是正确的？

先看一种实现：

```python
def cancel(job_id):
    job = repo.get(job_id)
    if job.status != "queued":
        return False
    repo.transition(job_id, "cancelled")
    return True
```

它非常容易解释：只有还没开始的任务可以 cancel。已经 running、finished 或 cancelled 都返回 `False`。

另一个实现也很合理：如果 job 已经 cancelled，再次调用仍然返回 success；如果正在 running，不立刻把状态改成 cancelled，而是 durable 地记录 cancellation requested，让 worker 在安全点停止。

哪一个更“正确”？只看 Python 代码无法回答。你必须先知道产品究竟希望 caller 可以依赖什么：

- running job 是“不能取消”，还是“接受取消请求但稍后完成”？
- repeated cancel 应该成功、失败，还是返回一个单独状态？
- missing job 和 terminal job 对 caller 来说是否需要区分？
- success 是“内存里记住了”，还是“crash/restart 后仍不会丢”？

到这里我们才需要给缺少的东西命名：specification。**Implementation 只能相对于某个 specification 判断 correctness。** 当前代码表现出的 behavior 是 evidence，不会自动获得需求定义的 authority。

真实项目还要继续追问 specification 从哪里来：stakeholder 想解决什么问题、哪些约束冲突、issue 是否已经把某个实现方案伪装成需求。这个上游问题很重要，但不在本章展开；旁支 [`Requirements Engineering：contract 从哪里来`](../extensions/requirements-and-stakeholders.md) 专门处理它。这里先假设我们已经有权把产品需求整理成可执行边界语义。

## 2. Signature 只给出了形状，Contract 才分配责任

假设 public API 只有：

```python
cancel(job_id: str) -> bool
```

类型告诉我们 caller 传一个字符串、得到一个布尔值，却没有告诉我们哪些字符串合法、`True` 代表什么、什么情况下会有 side effect，也没有解释 failure。

一个 specification 描述的是从边界外部可以依赖的行为。最常见的基本组成包括：precondition、postcondition、side effects 和 error semantics；有状态或并发系统还必须把 temporal / concurrency semantics 说清楚。

把这些责任分到 boundary 两侧以后，我们通常称它为 **contract**：caller 承担哪些 obligation，implementation 在 caller 满足这些 obligation 时又必须保证什么。

### 2.1 Precondition 决定 caller 必须先保证什么

用一个更小的 transfer case 看会更清楚：

```python
def divide(a: int, b: int) -> float:
    ...
```

一种 contract 可以写：`b != 0` 是 precondition。也就是说 operation 的有效输入域只包含满足这个条件的调用；caller 违反它以后，implementation 不必承诺正常结果。

从这个角度看，带 precondition 的 operation 可以理解成一个 **partial function**：类型签名给出的只是较大的表示域，specification 再说明其中哪些输入真正属于 contract 的定义域。这个词的价值不在数学包装，而在提醒我们：`int × int -> float` 仍然没有回答所有整数对是否都被允许。

另一种 contract 可以允许所有整数输入，并规定 `b == 0` 时产生一个稳定 error。这两种设计都可能实现，差别在于 **谁负责处理这个条件**。

因此 precondition 不是越多越严谨。public HTTP boundary 很难合理要求“caller 一定传合法 JSON”，因为外部输入本来就不可信；而一个只在 parser 内部调用的 helper 可以合理要求“token stream 已通过 lexical validation”。

设计 precondition 时更有用的问题是：哪一侧掌握足够信息、能以较低重复成本验证这个事实？把每个可检测错误都推成 caller obligation，可能只是把复杂度向外泄漏。

### 2.2 Postcondition 是 caller 可以拿走的结论

考虑：

```text
reserve(job, worker)
```

如果 caller 满足“job 当前 queued、worker 有效”这些 preconditions，implementation 可以承诺：operation 成功以后 job 为 running、绑定该 worker，并且 `started_at` 已建立。

caller 不需要知道内部是 SQL transaction、lock、CAS 还是别的机制。只要 postcondition 不变，implementation 就有演化空间。

contract 的价值就在这里：它不是文档装饰，而是在两边之间建立一个**可以停止继续展开内部 mental model 的责任分界**。

## 3. Behavior table 会把一句“取消任务”里藏着的决定逼出来

回到 TaskForge。先不要写代码，先给出一个**候选** behavior table：

| 当前状态 | `cancel(job_id)` 的语义 | public result | 状态/side effect |
|---|---|---|---|
| queued | 接受取消并持久化 transition | success | `queued -> cancelled` |
| running | durable 地记录 cancellation requested | success | 暂不伪装成已停止 |
| succeeded / failed | 不改变 terminal result | already_terminal | none |
| cancelled | 重复调用仍得到 success | success | no additional transition |
| missing | 找不到目标 | not_found | none |

这张表不是后续 M04 lab 的唯一标准答案。M04 的实验会故意采用一套更严格的 cancel semantics，让你比较不同 contract 的代价。这里选择这组行为，只是为了展示：一旦把模糊需求写成表格，原本藏在 implementation 里的 design choices 就不得不显式出现。

例如 running 行为什么不能直接写成 `status = cancelled`？因为 subprocess 也许仍在执行。若状态名对外声称“已经 cancelled”，而现实 side effect 仍可能继续，系统就在制造 false claim。

这说明状态、返回值和 error 都是 contract 的一部分，而不是 implementation 选什么 enum 的内部小事。

### 3.1 Side effect 与“什么时候算完成”必须一起写

`send_email(user) -> None` 的返回类型几乎没有告诉 caller 任何重要信息。operation 可能同步发送，也可能只是 enqueue；返回前 message 可能已 durable，也可能仍只在 memory queue；network failure 可能意味着 no effect，也可能意味着 outcome unknown。

同样，`cancel()` 返回 success 可以有很多时间语义：request 已写内存、已 durable、worker 已观察到、subprocess 已退出、外部 side effect 已停止。它们不是实现细节，而是 caller 接下来能做什么的依据。

所以在 concurrent / distributed system 里，**temporal semantics 是 specification 的一部分**。不要用一个模糊的 success 把多个时间点假装成同一件事。

### 3.2 Error semantics 必须支持 caller 做决定

如果 `cancel(job_id) -> bool` 把 missing、already terminal、storage failure、worker failure 和 timeout 全部压成 `False`，caller 下一步就只能猜。

这并不意味着 error class 越多越好。需要判断的是：不同情况是否要求 caller 采取不同动作，是否有不同 side-effect guarantee，是否允许 retry，以及哪些 mechanism failure 应该被 boundary 翻译成更稳定的 public semantics。M04 会专门深入这部分。

在 M01 只需要先建立一个纪律：**error 也是 operation outcome 的 contract，不是 success path 之外的一块附属日志。**

### 3.3 Concurrency 不能交给“线程调度自己决定”

假设 `finish(job)` 与 `cancel(job)` 同时到达。调度器当然会决定某条指令先运行，但 contract 仍然必须决定：哪些 transition 被允许、冲突怎样 resolve、caller 最终能观察什么，以及中间是否可能暴露非法状态。

如果你不先定义这些语义，implementation 中某次偶然的 lock 顺序就会悄悄变成事实行为。下一次重构换了 storage 或执行模型，所谓“正确性”也跟着漂移。

### 3.4 重复调用也属于 contract

候选表里，已经 cancelled 的 job 再次 `cancel` 仍返回 success。这个选择的目的不是“所有 cancel API 都应该如此”，而是让 caller 在 response 丢失后重复发送时，不必把“第一次是否已经生效”变成新的分支。

后面的 M04 会把“同一个 logical request 重复发生时不产生额外 intended effect”精确定义为 idempotency，并讨论它为什么不能只靠 payload equality 推断。这里先记住更基础的事实：**repetition semantics 也必须被 specification 决定**，不能等到 retry 出现后再让 implementation 临时猜。

## 4. 单个 operation 的 spec 还不够：系统需要 Invariant

behavior table 描述 `cancel` 一次调用的结果，但 TaskForge 还有 submit、reserve、finish、recovery 等很多路径。我们需要一些不依赖“当前正在调用哪个函数”的全局事实。

这就是 invariant：**每一个合法系统状态都必须满足的性质。**

### 4.1 Representation invariant：一个 value 内部哪些组合合法

假设 Job 的内部 representation 是：

```python
@dataclass
class Job:
    status: str
    worker_id: str | None
    started_at: datetime | None
    finished_at: datetime | None
```

可能存在这样的 representation invariants：

- `status == queued` 时没有 active `worker_id`；
- `status == running` 时存在 worker assignment；
- terminal state 已有 `finished_at`；
- `finished_at` 存在时，`started_at` 也必须存在。

这些事实不是 `cancel` 私有的。submit、reserve、finish、恢复代码和 migration 都不能制造违反它们的 Job。

### 4.2 Protocol invariant：合法性可能跨多个对象或进程

“同一个 job 在任意时刻最多有一个 authoritative active attempt”就不是单个 `Job` value 的 local representation invariant。它可能依赖数据库 constraint、lease、transaction、CAS 或 worker protocol。

重要的是先把**必须为真的语义事实**和**当前用于 enforcement 的机制**分开。机制未来可以替换，invariant 仍然是 design/review 的共同对象。

### 4.3 Durable invariant：成功承诺可以跨 crash

如果 API 对 caller 明确确认“cancellation request 已 durable 接受”，那么 daemon crash/restart 后这个 request 不能凭空消失。

这个 invariant 把 API contract 与 persistence 连接起来，也说明很多 architecture decision 最后都可以还原成同一个问题：系统准备在哪里、用什么机制保持某些关键事实？

## 5. 找到 Invariant 以后，还要找到 Enforcement Point

一个常见坏状态是：API layer 以为 worker 会检查，worker 以为 repository 已经验证，repository 又假设 caller 不会传非法 transition。每层都“知道规则”，但没有任何一层真正拥有保证它的责任。

一种可能的设计，是让所有 lifecycle mutation 都经过：

```python
JobRepository.transition(job_id, expected_state, new_state)
```

这个 boundary 可以集中检查 transition 合法性，并在 storage transaction 内维护相关 invariant。其他层不直接随意写 `status`。

这只是一个设计示例，不是“所有业务规则都应该塞进 repository”的 pattern rule。有些 invariant 属于 domain object，有些最适合 database constraint，有些需要多个 component 协作才能保持。

这里要建立的 review question 是：**这个 invariant 的 enforcement point 在哪里？是否存在一条绕过它的写路径？**

M02 会把这个问题继续推进成 state ownership 和 authority：不仅问“谁检查”，还问“谁有资格回答这个事实当前到底是什么”。

## 6. Specification 的强弱决定了未来还有多少实现自由

换一个简单 API：

```python
get_users() -> list[User]
```

一种 spec 只承诺“返回所有用户，顺序未指定”；另一种还承诺“按数据库 primary key 升序”。如果真实 caller 根本不需要排序，第二个 contract 就额外冻结了一个 implementation detail。

未来你想换 storage、做并行 query、加 cache 或 sharding 时，这个顺序都可能成为 compatibility burden。

因此 specification 设计不是“越详细越专业”。更强的 spec 给 caller 更多 guarantee，也给 implementation 更少自由。应该承诺 caller 真正需要依赖的 behavior，而不是无意把当前实现的偶然结果升级成永久 promise。

但这不能被反过来理解成“文档越模糊越自由”。“通常很快返回”“大多数情况下不会失败”并没有给 caller 足够信息去设计 timeout、resource management 或 recovery。**少承诺**和**说不清楚**不是一回事。

### 6.1 Implementation behavior、documented behavior 与 contract 不总是重合

Documentation 是判断 intended behavior 的重要 evidence，但它也可能过时、不完整，甚至与实际 requirement 冲突；当前 implementation 又可能表现出从未被设计过的 accidental behavior。这里说的 contract 指的是系统**有意允许 caller 依赖**的语义，而不是简单等同于“代码现在怎么跑”或“某页文档现在怎么写”。

假设当前 SQL 恰好长期以某个稳定顺序返回 rows，文档没写，但多个 client 已经依赖它。工程上你不能仅凭“我们从没承诺”就假设改掉一定没有成本。

公开 implementation behavior 存在得越久、被越多 consumer 观察到，它越可能成为事实上的 compatibility constraint。M08 会更系统地讨论这种现象。

这里先形成两个习惯：写 spec 时不要随手承诺 accidental behavior；改 public behavior 时也不要只根据文档猜 downstream 没人依赖。

## 7. Tests 的 oracle 应来自 Specification，而不是当前代码

一个很常见的循环是：先写实现，看实现怎么做，再写 test 验证它确实这样做，最后因为 coverage 很高而产生“行为正确”的错觉。

例如需求只要求 trim 首尾空格，但实现写成：

```python
def normalize(name):
    return name.strip().lower()
```

然后 test 又写：

```python
assert normalize(" Alice ") == "alice"
```

test 与 implementation 完全一致，却可能一起违反需求。测试没有自动提供独立 oracle；它只是把同一份误解执行了一遍。

更可靠的测试依据可以来自 product requirement、external protocol、明确 contract、invariant 或必须保持的 compatibility behavior。M03 会深入讨论 oracle、partition、property、mock brittleness 和 mutation；M01 先训练从 spec 推导 test cases。

以 `cancel` 为例，候选 contract 自然产生多维 partitions：

- state：queued、running、各 terminal state、missing；
- repetition：first call、response 丢失后的 repeat、多次重复；
- concurrency：cancel 与 reserve / finish 的不同相对顺序；
- durability：crash 发生在 durable write 前后，以及 success response 之后 restart；
- failure：storage unavailable、worker unreachable、termination 无法完成。

这不是要求每个函数都机械做五维笛卡尔积，而是说明测试空间应该由**语义分区**产生。值得测的是会改变 contract outcome 的 distinction。

## 8. “Make Illegal States Unrepresentable” 是工具，不是宗教

有了 invariant 以后，一个自然问题是：能不能让 representation 本身减少非法组合？

当前结构：

```python
@dataclass
class Job:
    status: str
    worker_id: str | None
```

允许轻易构造 `status="queued", worker_id="w7"` 这类违反 invariant 的 value。某些语言和场景下，可以改成更精确的 variants：

```python
QueuedJob(...)
RunningJob(worker_id=...)
FinishedJob(...)
```

这样一部分 local invariant 能更早、自动地被 enforcement。

但不能由此推出“所有 invariant 都应该编码进 type system”。远端 mutable state 会过期，跨 process 的 uniqueness 需要共享 state，复杂 lifecycle 也可能因为类型数量爆炸而更难 serialization / migration。

Type、constructor、database constraint、transaction、assertion、property test、state machine 和 review rule 都可能是 enforcement mechanism。选择依据应是：这个事实由谁拥有，需要观察哪些 state，以及在哪里最便宜、最可靠地阻止非法状态进入系统。

## 9. 对有 Lifecycle 的对象，先把 State Machine 写出来

如果一个领域已经不断出现 `if status == ...`，在继续加 branch 前先画状态转换通常更容易暴露遗漏：

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

然后明确 terminal set，并逐条问 transition：谁能触发？是否需要 atomic？返回前需要 durable 到什么程度？并发 transition 怎样 resolve？crash 在中间发生时 caller 能知道什么？

state machine 不是为了画图，而是把散落在很多 `if` 中的 protocol contract 拉到同一个可 review artifact 上。

## 10. 给 Agent 的任务也应该先有 Behavioral Model

Specification 对 Agent workflow 的价值很直接：让实现者先证明自己理解“应该改成什么”，而不是在探索 repo 的同时顺便决定产品语义。

一个可复用流程可以保持结构化，因为它本来就是执行协议：

### Phase 1 — Read-only reconnaissance

要求 Agent 不修改代码，先定位所有行为入口、state owner、storage、tests 和 failure path，并用代码位置证明。

### Phase 2 — Behavioral model

要求输出 current behavior table、desired behavior table、invariants、compatibility constraints 和 unresolved ambiguities。人在这里先 review 语义。

### Phase 3 — Change design

明确哪些 module 必须改、哪些不应该改，是否涉及 migration，以及怎样验证 change 不会绕开 enforcement point。

### Phase 4 — Implementation

到这里才允许修改代码。

### Phase 5 — Evidence

要求说明哪个测试在修复前会失败、哪个证据保护旧 contract、哪个 runtime reproduction 覆盖 failure path，以及是否存在 type / DB constraint 等直接 enforcement。

### Phase 6 — Independent review

不要让“实现 Agent 自己说已经完成”成为唯一 correctness argument。reviewer 应重新从 contract 和 invariant 出发检查 patch 与 evidence。

这个流程不是说所有小改动都必须写六份文档。它表达的是 authority 顺序：**先决定 behavior，再让 implementation 对 behavior 负责。**

## 11. Review 一个 Specification 时应该追问什么

完整 contract 不意味着每次都写一篇长文，但下面这些维度不能因为 signature 很短就被自动忽略。

### Input 与 responsibility

- 哪些输入属于合法 domain？
- 哪些条件是 caller precondition，哪些必须由 boundary validation？

### Success、side effect 与 time

- success 让 caller 可以依赖什么事实？
- side effect 是同步、异步还是 merely accepted？
- durability / visibility 在返回时达到哪一步？

### Error 与 repetition

- 不同 failure 是否需要 caller 采取不同动作？
- repeated call 的语义是什么？response 丢失后 caller 能否安全重发？

### Concurrency 与 invariant

- race 的合法结果有哪些？
- 哪些状态永远不能出现？
- invariant 的 enforcement point 在哪里？

### Compatibility

- 哪些 behavior 真正应该成为 public promise？
- 有没有把当前 implementation accident 无意升级成 stronger contract？

## 12. 四个练习：从“代码表现”剥离“系统承诺”

### 12.1 从实现中剥离 accidental behavior

给定：

```python
def list_jobs(db):
    rows = db.execute("SELECT * FROM jobs ORDER BY id")
    return [decode(x) for x in rows]
```

分别写出：当前 implementation 表现出的 behavior、caller 真正需要的 behavior、你愿意承诺的 contract。讨论 `ORDER BY id` 是否应该进入 public promise，以及如果删掉 order 后某个 client 失败，这件事能说明什么、又不能自动说明什么。

### 12.2 写一个完整的 `cancel` contract

不要照抄本章候选表。自己选择 running、already-cancelled 和 missing 的语义，并写清楚 side effect、durability、concurrency、repetition/error behavior 和 non-goals。最后说明你的设计比另一种候选 contract 强在哪里，又限制了哪些 implementation freedom。

### 12.3 找 invariant 的 enforcement point

在一个熟悉 repo 中选 `session`、`job`、`transaction`、`connection` 或 cache entry。列出一个重要 invariant、所有可能修改它的位置、当前真正 enforcement 的机制，以及是否存在绕过路径或第二份 authority。

### 12.4 Tests against spec

选择一个函数或 API。先不看 implementation，只根据 requirement / protocol 写 behavior partitions 和 tests；再读实现。记录哪些当前 behavior 你故意没有测试，因为它不是 contract，以及哪些 spec behavior 当前代码根本没有做到。

## 13. 下一章：有了 Contract，Boundary 应该画在哪里？

这一章给了我们第一个可以直接拿去 review 的问题：**What must be true? Who must guarantee it? What may the other side rely on?**

Specification 让 implementation 有了 correctness target；invariant 让多个 operation 和状态变化可以共享同一个合法性标准；enforcement point 又自然把问题推向下一章：如果某个事实必须由一个地方负责，模块边界、information hiding 和 state ownership 应该怎样设计？

### 可选原始材料

本章没有单独新增 technical provenance；重写保持原知识线，材料审查见 [`../MATERIALS_REVIEW.md`](../MATERIALS_REVIEW.md) 中 MIT 6.102 的部分。进一步可读：

- MIT 6.102 Specifications: https://web.mit.edu/6.102/www/sp26/classes/04-specifications/
- MIT 6.102 Designing Specifications: https://web.mit.edu/6.102/www/sp26/classes/05-designing-specs/
- MIT 6.102 AF/RI: https://web.mit.edu/6.102/www/sp26/classes/07-abstraction-functions-rep-invariants/
