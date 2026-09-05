# M07 Instructor Analysis — Double Claim、Linearization Point 与 Crash Window

> Spoiler。先完成 lab 再看。

---

# 0. Reference 结论

M07 有意要求学生对两个问题给出**不同类型的答案**：

```text
A. double claim
→ 当前 process 内有足够 mechanism 修复
→ 可以实现一个小 atomic claim decision

B. external effect crash window
→ 当前 local bookkeeping 无法为 arbitrary external callback 提供 exactly-once
→ 应先修 contract/authority assumption，而不是假装 reorder 能解决
```

这正是本章最重要的 engineering judgment：

> **不是每一个 correctness hole 都应该通过“再写一点本地代码”解决。**

---

# 1. Baseline Double-Claim History

starter：

```python
if job.status == QUEUED:
    after_observe(...)
    job.status = RUNNING
    claim_owners[job.id] = worker_id
    return success
```

probe 的 barrier 明确制造：

```text
A observe QUEUED
B observe QUEUED
--- both observations completed ---
A commit
B commit
```

实际 baseline：

```text
[RACE REPRODUCED]
one queued job produced two successful claims:
worker-A, worker-B
```

最终：

```text
status = RUNNING
owner = A or B
```

最终 state 并不一定有明显 corruption。

真正 violated contract 是 history：

```text
claim(A) -> success
claim(B) -> success
```

对于 sequential specification：

```text
first successful claim
→ job leaves QUEUED
→ second claim cannot also succeed
```

因此这个 history 不能被解释成合法 sequential history。

---

# 2. 为什么 Static Invariant 不够

一个太弱的 invariant：

```text
RUNNING job has one owner
```

baseline 可能满足。

更完整：

```text
I1. each job produces at most one successful claim transition from QUEUED.
I2. the successful receipt and committed owner identify the same worker.
I3. after the commit point, competing claims cannot succeed for that job.
```

I1 是 history property。

这也是为什么 M03 的 testing mental model 在这里升级：

```text
observable evidence
=
final state
+
operation results/history
```

---

# 3. Reference Safe Claim

reference 在临时副本里采用：

```python
_claim_lock = threading.Lock()
```

但并不是把整个 function 无脑锁住。

概念结构：

```text
scan candidate
observe QUEUED
run deterministic after_observe seam
        ↓
with claim lock:
    re-check QUEUED
    if stale:
        continue scanning
    status = RUNNING
    owner = worker
    return receipt
```

关键不是 `threading.Lock` 这个类型。

关键是：

```text
re-check predicate
+
status transition
+
owner assignment
```

属于一个 atomic claim decision。

---

# 4. Linearization Point

reference 的 abstract commit point 是 lock-protected region 中：

```text
确认 job 仍 QUEUED
并把 status + owner 提交为 claimed
```

在这一 region 前：

```text
observation 只是 candidate information
```

不能据此宣称 ownership。

在这一 region 后：

```text
其它 competing claimant 必须 re-check 到 non-QUEUED
```

因此可以把 operation history 解释成：

```text
A claim linearizes first
B claim observes A 已生效，失败/继续寻找下一 job
```

---

# 5. 为什么 `after_observe` 在 Lock 外

如果：

```python
with lock:
    observe
    barrier.wait()
```

第一个 thread 拿锁后在 barrier 等第二个 thread。

第二个 thread 永远拿不到 lock，也就到不了 barrier。

结果：

```text
deadlock
```

这个细节非常适合教学：

> **测试 instrumentation 同样会参与 concurrency semantics。**

正确用途是：

```text
after_observe seam
```

只用于把 stale observation 确定性地制造出来。

真正 authority decision 在 seam 之后重新检查。

---

# 6. 为什么 Loser 应继续扫描

简单修法：

```python
with lock:
    if stale:
        return None
```

对于 one-job case safety 没问题。

但如果：

```text
job-1 queued
job-2 queued
```

两个 worker 都先看到 job-1：

```text
A wins job-1
B sees stale and returns None
```

job-2 仍无人 claim。

这不一定构成严格 liveness violation，但它不必要地降低 progress，并改变了 `claim_next` 的直觉语义。

reference 选择：

```python
if stale:
    continue
```

实际 reference test：

```text
2 workers
2 queued jobs
→ 2 distinct successful receipts
```

因此 safety fix 没有不必要地退化基本 progress。

---

# 7. Reference 实际验证

临时副本中：

```text
original core tests: 6
M07 reference tests: 3
-----------------------
total: 9 passed
```

三个新增 tests：

1. one job / two workers → one success；
2. two jobs / two workers → two distinct success；
3. idempotent sink → duplicate callback attempts, one logical external effect。

同时，旧 baseline race probe 在 safe claim 上会退出失败，因为它已经无法得到：

```text
worker-A success
worker-B success
```

这是预期的 red→green 反转。

---

# 8. 为什么没有直接复用原 `worker.claim_next()`

课程没有把 M07 修复直接塞进已有 `worker.py`，原因是 teaching isolation。

M02–M06 已经建立了一系列 baseline probes。

如果直接改变 `worker.claim_next()` concurrency/owner contract：

```text
前面模块的 fixture/history
```

会被不必要地耦合到 M07。

所以 M07 加：

```text
concurrent_claim.py
```

作为一个专门演示：

```text
check-then-act
owner atomicity
history correctness
```

的 target。

这不是建议 production 系统保留两个 claim authorities。

事实上 student 的 writer-map 应该指出：

> 当前 teaching repo 正是故意存在多个 lifecycle writer；真实系统最终应统一 authority/transition boundary。

这个问题会在 architecture 模块再次处理。

---

# 9. Effect Delivery：Baseline Failure Window

starter：

```python
if job_id in completed:
    return False

effect(job_id)

if crash_after_effect:
    raise SimulatedCrash

completed.add(job_id)
```

实际 probe：

```text
external effect count = 1
local completed = missing
CRASH
retry
external effect count = 2
```

所以 `deliver_once` 的名字比真实 guarantee 强。

这是故意的。

---

# 10. 为什么 Record-First 不是修复

把顺序换成：

```python
completed.add(job_id)
effect(job_id)
```

failure window：

```text
record completion
CRASH
external effect never happened
```

recovery：

```text
completed says done
→ suppress retry
```

于是：

```text
duplicate risk ↓
loss risk ↑
```

没有 exactly-once。

这证明问题不是语句顺序，而是：

```text
local completion state
external effect
```

缺乏 shared transaction/authority。

---

# 11. Reference 不伪修 Production Function

instructor reference **没有**把 `effect_delivery.deliver_once()` 魔改成声称 exactly-once。

而是建立更精确 dependency contract：

```text
external effect is idempotent by logical effect ID
```

reference sink：

```python
seen = set()
logical_effects = []
callback_attempts = []

def sink(effect_id):
    callback_attempts.append(effect_id)
    if effect_id in seen:
        return
    seen.add(effect_id)
    logical_effects.append(effect_id)
```

然后：

```text
attempt 1:
sink(job-1)
logical effect happens
CRASH before local completion

attempt 2:
sink(job-1)
same key deduplicated
local completion written
```

结果：

```text
callback_attempts = [job-1, job-1]
logical_effects = [job-1]
```

这才是准确的语义：

> 两次 delivery attempt，一个 logical external effect。

---

# 12. 这里的 Authority Alignment

为什么 idempotent sink 能做本地 set 做不到的事？

因为 external effect owner 自己拥有 dedup knowledge：

```text
EffectAuthority:
(effect_id -> whether logical effect already committed)
```

TaskForge 重试时不需要推断：

```text
“上次到底发生了吗？”
```

它可以重发：

```text
same logical effect ID
```

由真正拥有 external effect 的 authority 判断。

这和 M02 的 state ownership 完全同构。

---

# 13. 为什么仍然不叫 Universal Exactly-Once

即便 sink 对一个 effect key 提供 idempotency，也必须限制 claim：

```text
exactly-once logical effect
```

只是在那个 sink contract 范围内。

不能推出：

```text
整个 job exactly once
subprocess exactly once
all filesystem changes exactly once
all downstream services exactly once
```

一个 job 可能包含多个 independently observable side effects。

所以 review 里禁止模糊写：

> “系统现在 exactly-once。”

必须写：

> “For this external sink, retries using the same effect ID produce one logical sink effect.”

---

# 14. Timeout 应建模成 Unknown Outcome

本章没有引入真实 network timeout code，但 instructor 应强调：

```text
timeout
```

不是一个 server-side state transition。

它是 caller knowledge：

```text
response not observed before deadline
```

因此 M04 request ID 的意义在 M07 才完全显现：

```text
attempt 1 response lost
retry same logical request ID
```

caller 可以安全询问/重放同一个 logical request，而不是创建新 intent。

但 request dedup 不等于 effect dedup。

---

# 15. Retry Amplification Reference

实验里的三层：

```text
API total attempts = 3
worker total attempts = 3
effect client total attempts = 3
```

最坏：

```text
3 × 3 × 3 = 27
```

底层 attempts。

如果有人把“retry 3 times”解释成**初始 + 3 retries = 4 attempts**，则是：

```text
4^3 = 64
```

所以设计文档必须避免模糊词：

```text
retry count
```

最好写：

```text
max attempts
```

或：

```text
1 initial + N retries
```

这也是 contract precision 的例子。

---

# 16. Cancellation Reference Discussion

未来 running cancellation 不应直接从：

```text
RUNNING -> CANCELLED
```

除非 `CANCELLED` contract 只表示：

```text
cancellation accepted/requested
```

如果 caller 会理解成：

```text
command is no longer executing
```

那么通常需要中间 protocol：

```text
RUNNING
  ↓ cancel accepted
CANCELLING
  ↓ executor confirms termination
CANCELLED
```

但不要机械添加 state。

可以选择其它 abstraction：

```text
cancel_request_state
execution_state
```

分离表达。

真正标准是：

> state name 与现实事实是否一致。

---

# 17. Common Bad Solutions

## Bad A — Wrap all TaskForge in one RLock

问题：

- scope 远超 invariant；
- 后续可能把 process/network I/O 锁住；
- 把 authority design 隐藏在 synchronization primitive 后。

## Bad B — Re-check but no synchronization

```python
if queued:
    after_observe()
    if queued:
        set running
```

两个 thread 仍可同步执行第二次 check。

只是 race window 变了。

## Bad C — Catch duplicate and repair owner afterwards

如果两个 caller 都已经收到 success：

```text
history violation 已发生
```

事后选一个 owner 不能收回另一个 success。

## Bad D — Record completion first

把 duplicate 改成 loss。

## Bad E — Infinite retry because effect is idempotent

idempotency 只解决 duplicate semantics。

不解决：

```text
overload
resource consumption
latency deadline
cascading failure
```

---

# 18. Review Agent Patch 的顺序

不要先看 lock diff。

先看 Agent 是否提交了：

```text
1. writer map
2. concrete bad interleaving
3. invariant
4. linearization point
5. safety evidence
6. liveness evidence
7. crash/failure table
8. retry guarantee wording
```

如果没有这些，哪怕 tests green，也应该自己重建 model。

---

# 19. M07 最终教学结论

这一章真正增加的不是 concurrency syntax，而是四个新的 reasoning object：

```text
operation history
interleaving
commit/linearization point
failure window
```

于是课程目前的 system model 从：

```text
state + contract + ownership
```

升级为：

```text
state
+ contract
+ ownership
+ history
+ time/interleaving
+ failure/retry
```

这为后续：

```text
M08 compatibility/migration
M09 architecture
M11 production reliability
```

提供了真正的 temporal foundation。
