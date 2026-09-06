# M07 Source Audit — Concurrency、Lifecycle 与 Failure

> 目标：确认哪些一手材料真正支持本模块关于 race、atomicity、lifecycle、crash/retry 与 failure amplification 的判断。
>
> 本模块不把“会用 lock/async/thread”当学习目标。核心问题是：**当多个动作可以交错、进程可能中断、调用者可能重试时，系统如何继续满足 contract 与 invariant。**

---

# 0. 本模块要回答的问题

M07 关注：

1. race condition 到底是什么，而不是“多线程有 bug”的同义词？
2. 怎样从 lifecycle state machine 推导 concurrent safety requirement？
3. check-then-act 为什么危险？
4. 哪些步骤必须形成一个 atomic decision / linearization point？
5. safety 与 liveness 有什么区别？
6. crash 与普通 exception 为什么不是同一种 failure？
7. timeout 为什么不等于“操作没有发生”？
8. retry 怎样把局部 failure 变成全局 overload？
9. 怎样确定性地测试 interleaving，而不是用 sleep 赌 scheduler？
10. 在 Agent 时代，怎样要求 implementation 同时交付 interleaving/failure evidence？

特别避免这些口号：

- “有 race 就加锁”；
- “用了 async 就没有 shared-memory race”；
- “message passing 自动解决 concurrency”；
- “timeout 表示 server 没执行”；
- “retry 能提升可靠性，所以越多越好”；
- “exactly once 是加个 request_id 就完成”；
- “并发测试多跑几千次就足够”；
- “linearizability 意味着实现必须真的串行执行”。

---

# 1. MIT 6.102 — Concurrency

**状态：主干采用**

原始正文：

- https://web.mit.edu/6.102/www/sp26/classes/14-concurrency/

实际检查：

- shared-memory / message-passing 两种模型；
- process / thread 与 time slicing；
- race condition 的定义；
- race 为什么难以由普通 tests 重现；
- message passing 也可能出现 protocol-level race；
- concurrency design 对 correctness / understandability / changeability 的影响。

正文给出的关键定义可以概括为：

> race condition 存在于 correctness（postcondition / invariant）取决于事件相对时序的地方。

这比“两个线程同时写一个变量”更准确。

因此课程采用：

```text
race
!=
threads exist

race
=
there exists a legal interleaving
that violates the intended contract/invariant
```

正文还明确指出 concurrency bug 通常 reproducibility 很差；scheduler、网络、机器负载都可能改变 interleaving。

本课程由此推出：

> **如果一个 race 可以用显式 barrier/failpoint 控制 interleaving，就不要用 sleep + repeated stress 作为主要 evidence。**

这是课程自己的工程外推，不是假装 MIT 原文提出了 deterministic scheduler。

## 限制

MIT 6.102 是 Software Construction 课程，例子主要用于解释 programming-level concurrency；它不是 distributed-systems failure model 教材。

所以：

- race / shared-memory / message-passing / testing difficulty：主干采用；
- crash recovery / retries / distributed delivery semantics：需要其它来源。

---

# 2. MIT 6.102 — Mutual Exclusion

**状态：主干采用（atomic regions / safety / liveness）**

原始正文：

- https://web.mit.edu/6.102/www/sp26/classes/16-mutual-exclusion/

实际检查：

- asynchronous ADT operations 的 interleaving；
- `await` 作为可能失去 control 的点；
- mutual exclusion 如何保护 representation invariant；
- race conditions 与 deadlock；
- safety / liveness 的区别；
- transaction 作为数据库侧并发控制手段的提示。

最值得课程吸收的是两个模型。

## 2.1 Interleaving point 必须显式画出来

对于 async code：

```text
read state
await something
write state
```

不能把它当作一个连续 operation reasoning。

课程推广成语言无关的问题：

```text
operation invocation
  ↓
read/check
  ↓
INTERLEAVING MAY OCCUR
  ↓
write/act
  ↓
response
```

只要中间允许另一个 operation 改变你依赖的事实，check-then-act 就可能不再安全。

## 2.2 Safety 与 liveness 必须分开

课程采用 MIT 的区分：

```text
Safety:
坏事永远不发生吗？
例如：一个 job 不会同时被两个 worker 成功 claim。

Liveness:
好事最终会发生吗？
例如：queued job 在健康 worker 存在时不会永远卡住。
```

“加锁以后 invariant 不破”只回答 safety 的一部分。

它可能同时制造：

```text
deadlock
starvation
unbounded waiting
```

所以 review concurrency change 时必须有两个问题，而不是一个：

1. invariant 是否仍成立？
2. operation 是否仍能 progress？

## 限制

正文使用 TypeScript `async/await` 说明 cooperative interleaving；TaskForge 使用 Python/threading/failpoint 做实验。课程只迁移 reasoning model，不照搬语言机制。

---

# 3. MIT 6.102 — Message Passing & Networking

**状态：补充采用**

原始正文：

- https://web.mit.edu/6.102/www/sp26/classes/18-message-passing-networking/

实际检查：

- message passing 通过 explicit immutable messages 减少 shared mutable state；
- client/server 本身天然 concurrent；
- protocol 必须像 ADT interface 一样被设计；
- message passing 不意味着不存在 race。

课程吸收：

> **Concurrency strategy 的关键不是“lock vs actor”标签，而是 authority 与 mutation 被放在哪里。**

例如：

```text
shared-memory design:
worker A ─┐
          ├─ mutate shared job table
worker B ─┘

message-passing design:
worker A ─ request ─┐
                    ├─ one authority owns job mutation
worker B ─ request ─┘
```

后者可以减少 shared mutation surface，但 protocol 仍可能出现：

```text
check message
then act message
```

被其它 message 插入的 race。

所以课程不会教：

> “改 actor/message passing 就自动 thread-safe。”

---

# 4. Herlihy & Wing — Linearizability (1990)

**状态：概念性主干采用；不进入形式证明细节**

原始论文：

- https://cs.brown.edu/~mph/HerlihyW90/p463-herlihy.pdf

实际检查：

- abstract；
- history / operation invocation-response framing；
- linearizable history 的基本定义；
- queue examples；
- locality property。

论文最适合本课程的一个思想是：

> 一个 concurrent operation 可以被理解为在 invocation 与 response 之间的某个瞬间原子生效，同时保持 real-time ordering constraint。

课程把这个点翻译为 engineering review question：

```text
claim(job)

invocation ---------------- response
             ^
             |
       到底在哪里之后，
       其它 actor 必须认为 job 已被这个 worker claim？
```

这个位置就是我们口语中所说的 **linearization point / commit point**。

但需要保留 Herlihy–Wing 定义中的一个重要 qualifier。对可能含 pending invocation 的 history `H`，形式定义要求**存在**一个 extension `H'`，使 `complete(H')` 等价于某个 legal sequential history `S`，并且 `S` 保持 `H` 已建立的 real-time precedence。这个 existential witness 不要求唯一；论文紧接着明确指出，同一个 history 可能有多个满足条件的 extension，也可能有多个合法 linearization。因此 “multiple valid linearizations” 本身不是错误。

所以课程需要分两层提问：先问 concurrent history 是否存在至少一个合法 sequential explanation；只有在分析某个 concrete implementation candidate 时，才继续问哪些实际代码事件/region 可以承担这个实现的 linearization point。后者也不要求代码真的只执行一条 machine instruction；数据库 transaction、lock-protected region、compare-and-swap、single-owner event loop 都可能实现等价语义。

## 为什么放进本课程

因为它能纠正一个常见 bug-fix 风格：

```text
看到两个函数各自“看起来线程安全”
→ 以为整个 protocol 线程安全
```

真正要问的是：

```text
operation-level abstract behavior
是否还能对应到某个合法 sequential history？
```

## 限制

本课不要求：

- 完成 formal linearizability proof；
- 学习 wait-free / lock-free hierarchy；
- 把所有 distributed workflow 都硬套 linearizability；
- 为每个正确 history 找到唯一 linearization。

M07 只用它帮助学生先检查 history 是否能解释为至少一个合法 sequential behavior，再对具体 implementation candidate 定位其 atomic decision / linearization region。

---

# 5. Google SRE — Addressing Cascading Failures

**状态：主干采用（retry amplification / retry budget）**

原始正文：

- https://sre.google/sre-book/addressing-cascading-failures/

实际检查：

- cascading failure 如何形成 positive feedback；
- naive retry 如何放大 backend load；
- exponential backoff + jitter；
- per-request retry limit；
- server-wide retry budget；
- 多层 retry 乘法放大；
- retriable / non-retriable distinction。

正文有一个特别适合课程的例子：多个层级各自进行 retry 时，attempt 数会乘起来；如果每层总共尝试 4 次，三层组合就可能把一个 user action 放大成 64 次底层 attempts。

课程吸收：

```text
retry
不是 error-handling detail

retry
是 load-generating operation
```

所以 retry policy 必须进入 system model：

```text
logical request
→ attempt count
→ timeout
→ backoff/jitter
→ retry budget
→ cancellation/deadline propagation
```

## 和 M04 的区别

M04 关注：

```text
这个 operation 是否具有可安全 retry 的 semantics？
```

M07 进一步关注：

```text
即使语义上可以 retry，
系统在 concurrency / overload 下应该 retry 几次、何时 retry？
```

**Idempotent 不意味着 unlimited retry 是安全的。**

---

# 6. AWS — Exponential Backoff and Jitter / Retry Guidance

**状态：补充采用**

原始材料：

- https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/
- https://docs.aws.amazon.com/wellarchitected/latest/framework/rel_mitigate_interaction_failure_limit_retries.html

实际检查：

- optimistic concurrency control contention example；
- synchronized retries 带来的 contention；
- jitter 把 attempts 在时间上打散；
- retry 应有限制；
- mutation operation 在 retry 前应先明确 idempotency。

课程不会要求学生手写 production-grade retry algorithm。

这里吸收的是：

```text
failure handling 也会改变 schedule
```

例如：

```text
100 clients 同时 timeout
→ 全部 1s 后 retry
→ 第二次 synchronized spike
```

所以时间本身是 concurrency state 的一部分。

## 限制

AWS guidance 服务于 production cloud workload；TaskForge M07 的 starter 是进程内模型。课程只用它把 retry/failure reasoning 从单个 function 提升到 system-level load semantics。

---

# 7. 为什么本章不主讲“各种锁”

候选材料当然可以继续加入：

- mutex / rwlock / semaphore；
- CAS；
- lock-free algorithms；
- actor model；
- STM；
- database isolation levels。

但把这些并排列出来很容易让课程退化为并发 primitive catalogue。

本课先要求学生掌握一个统一分析框架：

```text
1. shared authority 在哪里？
2. invariant 是什么？
3. 哪些 operations 可以 overlap？
4. 哪些 read/write 构成一个 decision？
5. linearization / commit point 在哪里？
6. crash 可以插在哪些 point？
7. timeout 后 caller 知道什么、不知道什么？
8. retry 是否创建 duplicate effect / load amplification？
9. safety 与 liveness 分别怎么验证？
```

primitive 只是实现这些 semantics 的工具。

---

# 8. 本模块最终采用的 teaching model

综合上述材料，M07 使用：

```text
Contract / Invariant
        ↓
Concurrent Operations
        ↓
Interleaving Table
        ↓
Atomic Decision / Linearization Point
        ↓
Crash Points
        ↓
Retry / Timeout Semantics
        ↓
Safety + Liveness Evidence
```

并要求每个重要 lifecycle operation 给出：

```text
pre-state
allowed concurrent operations
commit point
post-state
failure before commit
failure after commit
caller-visible result
safe retry rule
```

这比“用什么锁”更接近真实 engineering contract。

### TaskForge failpoint / durability 边界

这里还需要记录一个 **course fixture / local code clarification**，不能把它误归给上述外部来源。当前 `effect_delivery.completed_jobs` 是进程内 `set`，`SimulatedCrash` 是同进程异常；`m07_interleaving_probe.py` 用它确定性制造“external effect 已发生、completion write 尚未发生”的 interruption point，然后在同一进程 retry。

因此这个 probe 直接支持的是 effect/record ordering counterexample，不是“当前 starter 已实现真实 process-restart recovery”。如果要讨论 record-first 在 crash/recovery 后抑制 retry，必须额外声明 completion/attempt record 能跨目标 failure horizon 留存；当前 starter 本身没有这个 durability mechanism。即使补上该 assumption，record-first 仍只是在 duplicate risk 与 loss risk 之间移动 window，不能推出 arbitrary external effect exactly-once。

这项 precision 来自仓库真实 fixture/probe 的核对，是课程自己的 model-boundary 澄清，不是 MIT / Herlihy-Wing / SRE / AWS 的原文 claim。

### 其它 course-synthesis 边界

本章对 at-most-once / at-least-once / exactly-once 的具体 effect-boundary comparison、`cancel accepted` 与 `work stopped` 的 temporal split、`CANCELLING` vs orthogonal cancellation-request projection，以及 lease / heartbeat / fencing 的 restart-recovery extension，也都属于课程自己的工程综合。当前选定的 MIT / Herlihy-Wing / SRE / AWS 材料分别支撑 concurrency、linearizability intuition 与 retry/load reasoning，但**不作为这些 distributed lifecycle design choices 的直接来源**。

因此正文只能把这些内容写成 scoped reasoning / design candidates，并保留 mechanism、durability、authority 与 product-contract qualifier；不能借已有 source 的权威把它们升级成“唯一正确 protocol”或无条件 guarantee。

---

# 9. Agent-specific 审计结论

Agent 很容易生成看起来合理的 concurrency patch，例如：

```text
add Lock()
wrap function
add stress test
```

但 review 必须独立问：

```text
lock 保护的是哪条 invariant？
所有访问同一 invariant 的 writer 都经过它吗？
critical section 是否包含 blocking I/O？
是否形成 lock-order cycle？
是否只修 race 而制造 liveness 问题？
timeout 后 operation 可能已经 commit 吗？
retry 是否重复 effect？
```

因此 M07 的 Agent task contract 必须要求：

1. interleaving table；
2. explicit invariant；
3. commit/linearization point；
4. fail-before / fail-after semantics；
5. deterministic race/failure reproduction；
6. safety evidence；
7. liveness discussion；
8. 不允许只提交“stress test 1000 次没复现”。

---

# 10. 本章资料取舍结论

主干：

- MIT 6.102 Concurrency；
- MIT 6.102 Mutual Exclusion；
- Herlihy & Wing linearizability 的 operation-level abstraction；
- Google SRE cascading failures / retry amplification。

补充：

- MIT Message Passing & Networking；
- AWS backoff/jitter 与 retry guidance。

明确不升级成课程定律：

- “所有 shared state 都应该加 mutex”；
- “message passing 比 locks 永远好”；
- “linearizable 永远是正确 consistency level”；
- “idempotent operation 可以无限 retry”；
- “并发测试多跑就能证明 race-free”；
- “用了事务就不需要 lifecycle reasoning”。
