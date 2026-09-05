# M07 — Concurrency、Lifecycle 与 Failure：正确性必须跨越交错与中断

> 单线程代码里，“先检查，再修改”常常看起来完全正确。
>
> 一旦另一个 actor 可以在两步之间行动，或者进程可以在两步之间 crash，原来隐含的“这两步连续发生”就不再成立。
>
> M07 的目标不是学会更多 concurrency primitives，而是学会：**把 lifecycle operation 当成跨时间的 protocol，明确它的 invariant、interleaving、commit point、failure window 与 retry semantics。**

---

# 0. 从两个“最后状态看起来没问题”的 bug 开始

假设 TaskForge 有一个 queued job：

```text
job-1: QUEUED
```

两个 worker 同时执行：

```text
if status == QUEUED:
    status = RUNNING
    owner = me
    return SUCCESS
```

可能发生：

```text
Worker A              Worker B
--------              --------
read QUEUED
                      read QUEUED
write RUNNING
owner=A
return success
                      write RUNNING
                      owner=B
                      return success
```

最终 state：

```text
job-1.status = RUNNING
owner = B
```

如果你只检查最终 state，甚至可能觉得：

> “挺正常，一个 running job，一个 owner。”

但 history 已经包含：

```text
A: claim(job-1) -> success
B: claim(job-1) -> success
```

这不符合我们的抽象 contract：

> **一个 queued job 最多只能被一个 worker 成功 claim。**

这说明：

> **Concurrent correctness 不能只检查最终对象长什么样，还要检查 operation history 是否可以解释成合法行为。**

再看第二个问题。

我们想保证一个 external effect “只执行一次”：

```python
if job_id not in completed:
    send_email()
    completed.add(job_id)
```

如果：

```text
send_email()
  ↓
邮件已经发出
  ↓
CRASH
  ↓
completed.add(...) 尚未发生
```

恢复后 retry：

```text
completed 中没有 job
→ 再发一次邮件
```

有人会说：

> “那先写 completed，再发邮件。”

于是：

```text
completed.add(job_id)
  ↓
CRASH
  ↓
send_email() 尚未发生
```

恢复后：

```text
completed 已存在
→ 不再执行
→ 邮件永远没发
```

这不是换两行顺序可以解决的问题。

真正的问题是：

```text
local completion authority
和
external side-effect authority
```

不是同一个 atomic transaction。

M07 要学会先说清：

```text
at-most-once?
at-least-once?
idempotent effect?
transactional effect?
```

而不是先写 retry loop。

---

# 1. Concurrency 到底是什么

不要把 concurrency 等价成：

```text
threads
```

更有用的定义是：

> **多个 computation / operation 的相对顺序不是由单个顺序控制流完全决定。**

因此这些都属于 concurrency：

```text
threads
async tasks
multiple processes
multiple HTTP clients
worker queue consumers
filesystem users
DB transactions
signals/callbacks
crash + restart + retry
```

最后一项容易被忽略。

但从一个 logical operation 的角度：

```text
attempt 1
CRASH
attempt 2
```

也是两个可能对同一 state/effect 竞争的 execution。

所以“retry safety”本质上和 concurrency 很近。

---

# 2. Race condition 的工程定义

MIT 6.102 给出的 framing 很好：

> correctness 是否依赖事件相对时序？

于是：

```text
race
!=
代码里出现两个线程
```

而是：

```text
存在至少一种允许的 interleaving
使 contract/postcondition/invariant 被破坏
```

例如：

```python
if inventory > 0:
    inventory -= 1
```

单线程：

```text
inventory = 1
check true
subtract
inventory = 0
```

并发：

```text
A read 1
B read 1
A write 0
B write 0
```

最终 `inventory == 0`。

单看最终值甚至没发现负数。

但两个 purchase 都返回 success。

所以 invariant 不能只写：

```text
inventory >= 0
```

还需要 operation-level contract：

```text
每一次 success purchase 都对应一个真实消耗的 unit
```

这和 TaskForge double claim 是同一类问题。

---

# 3. 从 State Machine 升级到 Concurrent Protocol

M01 里我们会画：

```text
QUEUED -> RUNNING -> SUCCEEDED
                 \-> FAILED
QUEUED -> CANCELLED
```

这还只是 sequential lifecycle。

M07 要继续问：

```text
claim 与 cancel 可以 overlap 吗？
claim 与 claim 可以 overlap 吗？
finish 与 cancel 可以 overlap 吗？
timeout/retry 可以在哪个阶段发生？
worker crash 在 RUNNING 时代表什么？
```

一个 state machine 只有 node/edge 不够。

还要给 edge 加 protocol semantics：

| Operation | Pre-state | Commit point | Post-state | Concurrent conflict |
|---|---|---|---|---|
| claim | QUEUED | owner + RUNNING atomic decision | RUNNING | claim, cancel |
| cancel queued | QUEUED | CANCELLED decision | CANCELLED | claim |
| finish | RUNNING + correct owner | terminal result decision | SUCCEEDED/FAILED | duplicate finish, worker loss |

真正的 lifecycle design 是：

```text
state machine
+
operation atomicity
+
conflict semantics
+
failure semantics
```

---

# 4. Check-Then-Act：最常见的 race shape

很多 race 都长这样：

```text
READ / CHECK
   ↓
assume fact remains true
   ↓
ACT / WRITE
```

例如：

```python
if job.status == QUEUED:
    job.status = RUNNING
```

问题不是 `if`。

问题是：

> **从 check 到 act 之间，谁保证 predicate 仍成立？**

如果答案是：

```text
“通常很快”
```

那不是 correctness argument。

如果答案是：

```text
“CPython 有 GIL”
```

也必须继续问：

- 具体哪些 bytecode/extension calls 会切换？
- 以后实现换了怎么办？
- process/remote worker 后怎么办？
- contract 是依赖语言偶然 scheduling 还是明确同步？

工程上更稳定的 reasoning 是：

```text
check + transition
```

必须被定义成一个 atomic decision。

实现可以是：

```text
mutex
CAS
DB conditional update
transaction
single owner event loop
serialized message handler
```

不要从 primitive 倒推 contract。

---

# 5. Atomicity：不是“一个函数”就天然原子

函数边界：

```python
def claim_next():
    ...
```

只是代码组织。

调用者真正关心的是：

> 从外部看，这个 operation 在什么时候已经算发生？

这需要一个 **commit point / linearization point**。

Herlihy–Wing 的 linearizability 提供了非常有用的抽象：

```text
invocation ---------------- response
                  ^
                  |
      operation 在这一点“看起来瞬间生效”
```

例如 safe claim：

```text
A invokes claim
B invokes claim

atomic transition QUEUED -> RUNNING(owner=A)

A returns success
B returns no-job/conflict
```

我们不要求 CPU 真的只执行一条 instruction。

只要求 abstract history 能对应到某个合法 sequential history。

---

# 6. Linearization Point 为什么对 Code Review 有用

面对一段 concurrency patch：

```python
job = find_queued()
await reserve_worker()
job.status = RUNNING
```

不要只问：

> “是不是用了 Lock？”

更好的问题是：

> **claim 到底在哪一行之后对其它 actor 生效？**

如果答案含糊：

```text
大概 await 后？
可能 status 写入后？
worker reservation 成功后？
```

说明 operation contract 没闭环。

你还要问：

```text
如果 reserve_worker 成功但 status write 失败呢？
如果 status write 成功但 response 丢了呢？
```

这就自然进入 failure semantics。

---

# 7. Safety 与 Liveness 必须分开

MIT 6.102 Mutual Exclusion 明确区分：

## Safety

```text
坏事不会发生
```

TaskForge：

```text
一个 job 不会有两个成功 claim
terminal job 不会重新变 RUNNING
非 owner 不能 finish
```

## Liveness

```text
好事最终会发生
```

TaskForge：

```text
queued job 在 worker 健康且容量存在时最终可被 claim
lock acquisition 不会永久死锁
cancel request 不会永远卡 pending
```

一个方案可能：

```text
safety = excellent
liveness = terrible
```

最极端：

```python
lock.acquire()
never_release()
```

不会再发生 double claim。

因为什么都不发生了。

所以：

> **“加锁修复 race”不是完整 review conclusion。**

必须继续检查：

```text
lock duration
lock ordering
blocking I/O inside lock
exception cleanup
cancellation while waiting
fairness/starvation
```

---

# 8. Shared Memory 与 Message Passing 都需要 Authority Design

共享内存：

```text
A ─┐
   ├─ mutable job table
B ─┘
```

风险直观：多个 actor 可以 mutate 同一 representation。

message passing：

```text
A ─request─┐
           ├─ JobAuthority
B ─request─┘
```

优点是 mutation 被 confinement 到 authority。

但不要误以为 race 消失。

如果 protocol 是：

```text
A -> get_status
authority -> QUEUED

B -> claim
authority -> success

A -> claim
```

那么 A 的“先检查再 claim”仍可能基于 stale fact。

正确设计可能要求：

```text
claim-if-queued
```

成为一个 authority 内部的 atomic operation。

所以 M02 的 State Ownership 到 M07 会变成：

> **谁拥有状态还不够；owner 必须提供足够原子的 semantic operations。**

---

# 9. Lock 是实现手段，不是设计理由

看到：

```python
with lock:
    ...
```

要问：

```text
这个 lock 保护哪个 invariant？
```

如果回答是：

```text
“保护这个 dict”
```

通常还不够。

dict 可能包含：

```text
job lifecycle
owner mapping
retry count
cancel flag
```

真正需要同步的是 semantic invariant，例如：

```text
job.status == RUNNING
iff
exactly one active owner exists
```

如果 status 用 lock A，owner 用 lock B：

```text
两个 dict 都“线程安全”
```

但跨数据结构 invariant 仍可能坏。

因此同步边界应该跟 invariant boundary 对齐，而不是跟 field/container 对齐。

---

# 10. Critical Section 也不能无限扩大

反方向的坏修复：

```python
with global_lock:
    read_db()
    call_network()
    execute_command()
    write_logs()
```

可能避免很多 race。

但也可能：

```text
parallelism -> 0
latency -> lock hold time
one slow dependency -> block all work
deadlock/cancellation cleanup -> harder
```

更好的思路是识别：

```text
最小 atomic decision
```

例如：

```text
QUEUED -> RUNNING(owner=A)
```

只要求 claim decision 原子。

真正 command execution 不应在同一个全局 lock 内。

---

# 11. Crash 不是 Exception

普通 exception：

```python
try:
    do_x()
except ...:
    cleanup()
```

至少假设：

```text
当前 process 仍然活着
cleanup code 有机会运行
```

crash：

```text
process terminated
power lost
machine rebooted
SIGKILL
runtime died
```

可能根本没有 finally。

所以这样的 invariant：

```python
acquire_resource()
try:
    work()
finally:
    release_resource()
```

对 process-local mutex 可能足够，因为 OS 会回收。

但对：

```text
remote lease
DB status
external API reservation
filesystem marker
```

未必足够。

必须问：

> **owner 消失后，谁恢复这个 lifecycle？**

这就是 lifecycle ownership 的 failure dimension。

---

# 12. Failure Window：把 crash 插到每两个 effect 之间

分析一个 multi-step operation：

```text
1. mark RUNNING
2. launch subprocess
3. record pid
4. acknowledge claim
```

不要只分析 happy path。

做 failure table：

| Crash point | Persistent facts | External facts | Recovery question |
|---|---|---|---|
| before 1 | QUEUED | no process | safe to retry claim? |
| after 1 before 2 | RUNNING | no process | orphaned RUNNING? |
| after 2 before 3 | RUNNING | process exists | how locate it? |
| after 3 before 4 | RUNNING+pid | process exists | caller may retry claim? |

这比一句：

> “我们有 error handling。”

强太多。

---

# 13. Timeout 是 Knowledge Failure，不是 Operation Failure

这是 distributed/client-server code 最重要的 mental model 之一。

caller 发请求：

```text
submit(job)
```

然后 timeout。

至少有这些可能：

```text
A. request 根本没到 server
B. server 收到但未 commit
C. server 已 commit，response 丢了
D. server 正在执行
```

因此：

```text
timeout
!=
operation did not happen
```

更准确：

> **timeout 表示 caller 在 deadline 内没有获得足够信息来确认 outcome。**

这是 knowledge state。

于是 retry semantics 必须和 M04 request identity 结合：

```text
same request_id
→ server 能识别 same logical request
```

但即使 request dedup 解决，也不能自动解决 external effect exactly-once。

---

# 14. At-Most-Once / At-Least-Once / Exactly-Once

这些词不要背定义，要看 failure window。

## At-most-once

宁愿漏，也不要重复：

```text
record done
then effect
```

crash window 可能：

```text
recorded done
but effect missing
```

## At-least-once

宁愿重复，也不要漏：

```text
effect
then record done
```

crash window 可能：

```text
effect happened
record missing
→ retry duplicates
```

## Exactly-once

要想真的保证：

```text
one logical operation
→ one externally visible effect
```

通常需要更强机制，例如：

```text
same transactional authority
idempotent external operation keyed by logical request
transactional message/outbox style coordination
```

课程此处不展开具体 pattern。

最重要的是认识：

> **如果 completion record 与 external effect 不在同一个 atomicity boundary，单纯调换两行顺序不能凭空得到 exactly-once。**

---

# 15. “Idempotent” 也不是魔法

如果 external service 支持：

```text
send_email(request_id=req-123)
```

并保证相同 request ID 只产生一个 logical effect，

那么 TaskForge 可以安全地：

```text
effect(req-123)
CRASH
retry effect(req-123)
```

因为 dedup authority 在 effect owner 那边。

这是一种 authority alignment。

但注意：

```text
HTTP POST retry request dedup
```

和：

```text
subprocess command 本身的 external side effect
```

不是同一个层面。

TaskForge submit idempotent：

```text
只创建一个 job
```

不代表 command：

```bash
charge-credit-card
```

就只执行一次。

---

# 16. Retry 是新的 Load，不只是新的机会

Google SRE 的 cascading failure 章节非常重要的一点：

```text
retry attempt
```

仍然是一个真实 request。

如果：

```text
frontend 4 attempts
backend 4 attempts
database wrapper 4 attempts
```

一个 logical request 最坏可能变成：

```text
4 × 4 × 4 = 64
```

次底层 attempt。

所以 review retry policy 要问：

```text
谁 retry？
retry 几次？
哪些 error retriable？
有没有 total deadline？
有没有 backoff？
有没有 jitter？
有没有 retry budget？
```

而不是：

```python
for _ in range(3):
    try_again()
```

---

# 17. Backoff 和 Jitter 也是 Concurrency Control

假设 1000 个 client 同时收到 failure。

固定 1 秒 retry：

```text
t=0: failure spike

t=1: 1000 retries together

t=2: another synchronized spike
```

backoff：

```text
1s, 2s, 4s, ...
```

可以降低频率。

但如果所有 client schedule 一样，仍然同步。

jitter 的目的：

```text
把 attempt 在时间轴上打散
```

所以：

> **Retry timing 本身就是 concurrency behavior。**

这不是性能-only concern。

它可能决定系统是否进入 positive feedback outage。

---

# 18. Cancellation 不是一个 Boolean

很多系统写：

```python
cancel(job) -> bool
```

但对于 running work，至少可能有：

```text
cancel requested
signal sent
worker acknowledged
process exited
cleanup done
terminal CANCELLED recorded
```

这些不是一个瞬间。

所以 lifecycle 可能需要：

```text
RUNNING
  ↓ request
CANCELLING
  ↓ worker/process confirms stop
CANCELLED
```

是否需要额外 state 取决于 contract。

关键是：

> **不要让 state name 宣称比现实更多的事实。**

如果 process 还在跑，却已经写：

```text
CANCELLED
```

调用者可能合理地认为：

```text
external work 已停止
```

这就是 temporal contract bug。

---

# 19. Lease / Heartbeat：什么时候需要

worker crash 后：

```text
job = RUNNING
owner = worker-A
```

如果 owner 永远不会主动 cleanup：

```text
RUNNING 永久 orphan
```

一种常见设计是 lease：

```text
owner=A
lease_until=t
```

当 lease expired：

```text
job 可被 recovery/reclaim
```

但 lease 引入新的问题：

```text
clock assumptions
heartbeat delay
old worker may still be running
new worker may reclaim
```

如果旧 worker 恢复后继续写结果：

```text
stale owner writes
```

就需要更强 token/version/fencing semantics。

M07 只把这个问题提出来；真正分布式 lease/fencing 可以在后续 architecture/production 模块展开。

---

# 20. Deterministic Interleaving Test

普通 race test：

```python
for _ in range(10000):
    start_two_threads()
```

缺点：

```text
失败不可重复
环境相关
跑过不代表安全
CI 可能 flaky
```

更高信息量的方法：

```text
A read QUEUED
---- barrier ----
B read QUEUED
---- barrier ----
A/B continue commit
```

这样我们不是“等待 scheduler 恰好撞出 bug”。

而是直接构造：

```text
the interleaving that violates the invariant
```

测试的 claim 也更明确：

```text
当两个 claim 都基于同一个 QUEUED observation 时，
最多一个可以成功 commit。
```

---

# 21. Failure Injection 也应该是 Deterministic

不要：

```text
kill -9 random process
希望某次刚好在正确 window
```

教学/单元级 evidence 更适合：

```text
before_commit failpoint
after_commit failpoint
after_external_effect failpoint
before_ack failpoint
```

然后逐一回答：

```text
persistent state 是什么？
external effect 是什么？
caller 能观察到什么？
recovery/retry 应做什么？
```

production chaos testing 当然有价值。

但它不能替代 protocol-level failure reasoning。

---

# 22. Final-State Assertions 不够

假设 double claim 后最终：

```text
owner=B
status=RUNNING
```

测试如果只断言：

```python
assert owner in {"A", "B"}
assert status == RUNNING
```

会绿。

真正应该观察 history：

```python
results = [claim_A_result, claim_B_result]
assert successes(results) == 1
```

这就是 M03 的 oracle 在 concurrency 下升级：

```text
oracle 不只观察 state
也观察 operation history / side-effect count
```

---

# 23. History-Oriented Testing

对于 lifecycle operation，测试对象可以是：

```text
invoke(A, claim)
invoke(B, claim)
return(A, success)
return(B, success)
```

然后问：

> 能不能把这个 history 排成一个符合 sequential specification 的顺序？

对于：

```text
claim A -> success
claim B -> success
```

不能。

因为 sequential spec 是：

```text
第一次 claim 后 job 已 RUNNING
第二次不可能再 success
```

这是 linearizability 思维最实用的工程形式。

---

# 24. Concurrency Invariant 要覆盖所有 Writers

假设你修：

```python
claim_next()
```

加了 lock。

但：

```python
admin_requeue()
recover_orphan()
cancel()
```

仍直接改同一个 lifecycle state。

那么：

```text
claim path thread-safe
```

不等于：

```text
lifecycle thread-safe
```

M02 的 writer map 在这里重新变得关键：

```text
invariant
→ enumerate every writer
→ every writer obeys same synchronization/authority rule
```

所以 concurrency review 前必须重新做 writer search。

---

# 25. Deadlock Review：不要只看单个函数

经典情况：

```text
path A:
lock jobs
then lock workers

path B:
lock workers
then lock jobs
```

各自看：

```text
“都用了 lock”
```

组合：

```text
A holds jobs, waits workers
B holds workers, waits jobs
```

所以 lock review 需要 global order：

```text
jobs_lock < workers_lock < io_lock
```

或者更好的 design：减少 simultaneous lock ownership。

这再次说明：

> concurrency correctness 是 protocol property，不是单个 function property。

---

# 26. Agent 最容易生成的并发伪修复

## 26.1 “加一个 global Lock”

可能修 safety，但：

```text
隐藏 architecture issue
串行化所有 work
把 blocking I/O 放进 critical section
```

## 26.2 stress test 1000 次

```text
1000 passed
```

不能推出 race-free。

## 26.3 捕获 exception 然后 retry

没有回答：

```text
操作是否已 commit？
external effect 是否已发生？
```

## 26.4 “request_id 所以 exactly once”

只可能覆盖某一个 boundary 的 dedup。

不能自动覆盖：

```text
subprocess
email
payment
filesystem
remote tool call
```

## 26.5 sleep 修时序

```python
sleep(0.1)
```

可能改变概率，不是建立 happens-before contract。

---

# 27. Agent Task Contract：必须要求并发模型

坏 prompt：

```text
修一下 worker race，加测试。
```

更好的任务：

```text
Current invariant:
- a queued job may produce at most one successful claim.
- only the committed owner may finish it.

Required analysis before edit:
1. enumerate lifecycle writers;
2. provide the concrete double-claim interleaving;
3. identify the desired linearization point;
4. state safety and liveness properties separately.

Implementation constraints:
- do not hold the global claim synchronization boundary during command execution;
- preserve FIFO selection among jobs that are queued at the commit point;
- do not change M02–M06 public behavior unless explicitly required.

Evidence:
- deterministic barrier test that fails on baseline;
- test showing exactly one success under competing claim;
- test that loser can continue to claim another queued job;
- full regression suite;
- explanation of lock/authority scope.
```

这里 task prompt 本身就是 concurrency specification。

---

# 28. Crash-Safety Task Contract

坏 prompt：

```text
确保 job 只执行一次，失败后重试。
```

这是自相矛盾风险很高的要求。

应该先问：

```text
什么叫“执行”？
本地 process launch？
command external effect？
terminal state？
```

然后选择 guarantee：

```text
A. at-most-once attempt
B. at-least-once attempt
C. external effect supports idempotency key
D. transactional coordination exists
```

Agent 不应该替产品/系统设计者默默选一个。

---

# 29. M07 Review Checklist

## Shared authority

- 哪些 actor 可以写同一事实？
- 有没有 ambient writer 绕过 synchronization？

## Interleaving

- operation 在哪里可能 yield/block/await？
- check 与 act 之间可以发生什么？
- 能构造最坏 interleaving 吗？

## Atomicity

- abstract operation 的 commit point 在哪里？
- final state 与 operation history 都合法吗？

## Safety

- 什么坏事绝对不能发生？
- tests 是否直接检查它？

## Liveness

- 谁可能永远等？
- lock order / starvation / blocking I/O 怎么样？

## Failure

- crash 可以插在哪些 side effect 之间？
- crash 前后哪些事实 durable？
- recovery authority 是谁？

## Timeout / Retry

- timeout 后 caller 知道什么？
- operation 是否可能已经 commit？
- retry 是否语义安全？
- retry 是否会放大 load？

## Evidence

- race 是否 deterministic reproduction？
- failure 是否 explicit failpoint？
- 有没有只靠 stress/sleep？

---

# 30. 本章实验：两个不同的 atomicity failure

TaskForge M07 会增加两个 teaching targets。

## Target A — double claim

我们会故意让：

```text
Worker A observes QUEUED
Worker B observes QUEUED
A commit success
B commit success
```

最终 owner 可能只有一个。

但 history 里有两个 success。

任务：

```text
find invariant
construct deterministic interleaving
choose commit point
fix with smallest semantic synchronization boundary
verify safety + basic progress
```

## Target B — external effect crash window

starter：

```text
if not completed:
    effect()
    maybe_crash()
    completed.add(job)
```

任务不是机械改顺序。

而是：

1. 实际复现 duplicate effect；
2. 写出两种 ordering 各自的 failure table；
3. 解释为什么 local bookkeeping + independent external effect 无法仅靠 reorder 得到 exactly-once；
4. 选择一个明确 guarantee；
5. 如采用 idempotent external sink，验证 retry 仍只有一个 logical effect。

---

# 31. 与前六章的连接

M01：

```text
Invariant 是什么？
```

M02：

```text
谁拥有 state？
```

M03：

```text
什么 evidence 真的能拒绝错误实现？
```

M04：

```text
retry/error 是什么 public contract？
```

M05：

```text
如何分阶段安全改变实现？
```

M06：

```text
没有 feedback 时先怎样打开 seam？
```

M07：

```text
当 operation 可以 overlap / crash / retry 时，
上述 contract 与 invariant 是否仍成立？
```

---

# 32. 最终 mental model

面对任何 concurrent lifecycle operation，画出：

```text
          invocation
              |
              v
        read / validate
              |
       interleaving?
              |
              v
       atomic decision   <--- linearization / commit point
              |
       external effects
              |
          crash?
              |
              v
          response
              |
          timeout?
              |
              v
           retry?
```

然后分别回答：

```text
Safety:
什么永远不能发生？

Liveness:
什么最终必须能发生？

Crash semantics:
commit 前后分别留下什么？

Retry semantics:
caller 不知道结果时如何继续？
```

如果这四组问题没有答案，

```text
“加了 lock”
```

或者：

```text
“CI concurrency test 绿了”
```

都不足以说明设计正确。

> **M07 的核心不是控制线程；而是把“时间、交错、中断和重试”纳入软件 contract。**
