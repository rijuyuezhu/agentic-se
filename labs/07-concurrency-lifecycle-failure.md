# Lab 07 — Deterministic Race、Commit Point 与 Crash Window

> 本实验有两个目标：
>
> 1. 把一个“偶尔发生的 race”变成**确定性可复现的 operation-history violation**；
> 2. 证明一个外部 effect 与本地 completion record 分属不同 authority 时，**仅靠交换两行代码不能得到 exactly-once**。

---

# 0. Starter

本实验新增：

```text
labs/taskforge/src/taskforge/concurrent_claim.py
labs/taskforge/src/taskforge/effect_delivery.py
labs/taskforge/tools/m07_interleaving_probe.py
```

先运行：

```bash
cd labs/taskforge
PYTHONPATH=src uv run --with pytest --no-project python tools/m07_interleaving_probe.py
```

baseline 应稳定展示：

```text
[RACE REPRODUCED] one queued job produced two successful claims
[FINAL STATE] one RUNNING job and one recorded owner can hide the bad history
[CRASH REPRODUCED] effect happened, completion record was lost, retry produced a duplicate effect
[ORDER REVERSAL] recording completion first avoids duplication but can lose the effect
```

注意：这不是 flaky stress test。

probe 显式控制 interleaving/failure point。

---

# 1. 第一阶段：Read-Only System Model

在改代码前回答。

## 1.1 Writer map

找出所有会修改：

```text
Job.status
concurrent_claim.claim_owners
```

的路径。

至少检查：

```text
service.py
worker.py
concurrent_claim.py
state.py
```

不要假设 M07 starter 是唯一 writer。

## 1.2 写出 invariant

至少包含：

```text
I1. 一个 queued job 最多产生一个 successful claim receipt。
I2. owner record 与 successful claim history 必须一致。
I3. claim 的失败者不能把 winner 的 ownership 覆盖掉。
```

如果你只写：

```text
RUNNING job has one owner
```

太弱。

因为 baseline 最终就可能满足这个 static invariant，同时 history 已经产生两个 success。

---

# 2. 写出具体 Interleaving Table

不要只说“有 race”。

写成：

| Step | worker-A | worker-B | job status | owner |
|---|---|---|---|---|
| 1 | observe QUEUED | | QUEUED | none |
| 2 | | observe QUEUED | QUEUED | none |
| 3 | write RUNNING, owner=A | | RUNNING | A |
| 4 | return success | | RUNNING | A |
| 5 | | write RUNNING, owner=B | RUNNING | B |
| 6 | | return success | RUNNING | B |

然后回答：

```text
哪一步开始 abstract claim 已经生效？
```

如果没有唯一答案，说明 commit point 不明确。

---

# 3. Design It Twice

至少比较两个实现方向。

## Design A — lock-protected check + transition

大致：

```text
observe candidate
  ↓
lock
  ↓
re-check QUEUED
  ↓
status + owner transition
  ↓
unlock
```

讨论：

- lock 保护的是哪个 invariant？
- `after_observe` 为什么必须在 lock 外？
- 如果 re-check 失败，是返回 none 还是继续扫描后续 queued job？
- lock 内是否包含 command execution？

## Design B — single authority operation

概念上把：

```text
find queued + claim
```

变成一个 authority operation：

```text
claim_next(worker_id)
```

调用者不能先拿 candidate 再单独 mutate。

实现可以未来迁移为：

```text
DB conditional update
single-owner queue
message-passing authority
```

讨论：

- 哪个设计更容易从当前 v0 迁移？
- 哪个 design knowledge 应留在 API contract，哪个属于当前 implementation？

---

# 4. 实现 Part A：只修 Double Claim

要求：

```text
一个 queued job
两个 competing workers
→ exactly one success
```

但不要顺手重构整个 TaskForge。

## 4.1 Scope constraint

推荐只改：

```text
concurrent_claim.py
相关 M07 tests
```

除非你的 writer analysis 能证明必须修改其它生产文件。

## 4.2 不允许的伪修复

### sleep

```python
time.sleep(...)
```

不建立 correctness。

### 全局串行整个 worker execution

不要把 command execution 放进 claim lock。

### 删除 after_observe seam

这样只是让 race 更难测，不是修 race。

### stress-only evidence

```text
10000 iterations passed
```

不能作为主要证明。

---

# 5. 必须写的 Safety Tests

## 5.1 One job / two workers

用 `threading.Barrier` 保证两个 worker 都观察到同一个 queued job。

修复后：

```text
success receipts = 1
```

并验证：

```text
owner == successful worker
job.status == RUNNING
```

## 5.2 Two jobs / two workers

这是 liveness/progress sanity check。

场景：

```text
job-1 QUEUED
job-2 QUEUED
```

两个 worker 都先撞上 job-1。

winner claim job-1。

loser re-check 后不应该直接放弃所有工作；它应该能继续扫描并 claim job-2。

最终希望：

```text
2 distinct receipts
2 distinct job ids
```

这个 test 防止一种过度保守修复：

```text
contention once
→ loser immediately returns None
```

它未必违反 safety，但可能降低 progress semantics。

---

# 6. 写 Linearization-Point Note

实现完成后，不要只写“用了 mutex”。

提交一个简短说明：

```text
Operation: claim_next(worker)

Precondition:
job is QUEUED at commit decision.

Linearization point:
<具体代码区域>

Atomic facts committed together:
- status becomes RUNNING
- owner becomes worker

Competing claim after this point:
must observe/re-check non-QUEUED and cannot return success for the same job.
```

如果 status/owner 不是一起提交，也要解释为什么 invariant 仍成立。

---

# 7. Part B：Crash Window 不是 Lock 能解决的

阅读：

```text
src/taskforge/effect_delivery.py
```

当前：

```text
if not completed:
    effect()
    maybe crash
    completed.add(job)
```

probe 会产生：

```text
effect
CRASH
retry
effect again
```

现在不要急着改代码。

先写 failure table。

---

# 8. Failure Table A — Effect First

| Point | local completed | external effect count | restart/retry outcome |
|---|---:|---:|---|
| before effect | 0 | 0 | retry executes once |
| after effect, before record | 0 | 1 | retry duplicates |
| after record | 1 | 1 | retry suppressed |

这通常接近：

```text
at-least-once attempt/effect
```

但具体 guarantee 还取决于 retry policy。

---

# 9. Failure Table B — Record First

假设改成：

```text
completed.add(job)
effect()
```

写表：

| Point | local completed | external effect count | restart/retry outcome |
|---|---:|---:|---|
| before record | 0 | 0 | retry |
| after record, before effect | 1 | 0 | retry suppressed → lost effect |
| after effect | 1 | 1 | fine |

回答：

> 这是否“修复 exactly-once”？

正确答案必须是：没有。

它只是把：

```text
duplicate risk
```

换成：

```text
loss risk
```

---

# 10. 选择一个明确 Guarantee

你必须写 design decision。

可以选择：

## Option A — At-least-once + idempotent sink

要求外部 effect 支持：

```text
logical_effect_id = job_id / request_id
```

重复调用相同 key 不产生重复 logical effect。

TaskForge 可以 retry。

## Option B — At-most-once attempt

先记录 attempt，然后执行；crash window 接受 loss。

适用于某些“绝不能重复”的 effect，但要明确丢失风险和 reconciliation。

## Option C — Transactional coordination

如果 effect 和 completion record 可以进入同一事务，再设计更强 guarantee。

当前 starter 没有这个 mechanism。

不允许写：

```text
Option D — exactly-once because Python function has a set
```

---

# 11. 推荐 Reference Direction：Idempotent Sink

这一章不要求你把 production `deliver_once()` 改成复杂框架。

更重要的是建立 dependency contract：

```text
external effect accepts logical idempotency key
```

写一个小型 test sink：

```python
class IdempotentSink:
    seen: set[str]
    logical_effects: list[str]

    def __call__(self, effect_id: str):
        if effect_id in self.seen:
            return
        self.seen.add(effect_id)
        self.logical_effects.append(effect_id)
```

然后复现：

```text
first call:
external logical effect happens
local crash

retry:
sink receives same key
but no duplicate logical effect
```

注意：

```text
callback invocation count may be 2
logical effect count = 1
```

这正是 semantic guarantee 与 mechanism count 的区别。

---

# 12. Timeout Thought Experiment

假设未来 `deliver_once()` 是 RPC。

caller timeout 时：

```text
request not received?
received but not committed?
committed but response lost?
```

写出：

```text
what caller knows
what caller does not know
```

然后回答：

> 为什么 timeout 后直接换一个新的 request ID retry 可能破坏 dedup？

---

# 13. Retry Amplification Exercise

假设：

```text
API layer: max 3 attempts
worker layer: max 3 attempts
effect client: max 3 attempts
```

一个 logical request 最坏会产生多少 effect-client attempts？

不要只给数字。

画出 multiplication tree，并说明：

```text
为什么每一层“都只是 retry 两次”组合起来可能很危险？
```

然后提出更好的 ownership：

```text
哪个层应该拥有 retry policy？
其它层应该怎样 propagate error/deadline？
```

---

# 14. Cancellation Protocol Exercise

当前 TaskForge：

```text
RUNNING cancel -> False
```

假设未来需求：

```text
running job 可以 cancel
```

不要直接实现。

先设计 lifecycle：

```text
RUNNING
  ↓ cancel requested
?
  ↓ process stopped
CANCELLED
```

回答：

- 是否需要 `CANCELLING`？
- cancel request accepted 后，API 可以承诺什么？
- process 还活着时能不能叫 `CANCELLED`？
- finish 与 cancel acknowledgement race 时谁赢？
- cancel 是否 idempotent？

---

# 15. Agent A/B Exercise

## Prompt A

```text
修复 concurrent_claim.py 的 race，确保线程安全，加测试。
```

让 Agent 实现。

review：

- 它是否直接加 global lock？
- 是否识别了 operation-level invariant？
- 是否有 deterministic interleaving test？
- 是否讨论 liveness？

## Prompt B

给 Agent：

```text
Invariant:
- each queued job yields at most one successful claim.
- committed owner and successful receipt must agree.

Before editing:
- enumerate lifecycle writers;
- provide the double-claim interleaving;
- identify proposed linearization point.

Implementation:
- preserve after_observe as deterministic interleaving seam;
- synchronize only claim decision, not command execution;
- loser must continue scanning later queued jobs.

Evidence:
- one-job/two-worker barrier test;
- two-job/two-worker progress test;
- existing regression suite.
```

比较两个结果。

重点不是 Prompt B 字更多。

而是它提供了：

```text
system model
contract
non-goals
expected proof shape
```

---

# 16. Independent Review Checklist

完成后独立 review。

## Safety

```text
[ ] 一个 job 最多一个 successful claim
[ ] owner 与 receipt 一致
[ ] static final state + history 都检查
```

## Synchronization

```text
[ ] lock/authority scope 对齐 invariant
[ ] blocking command execution 不在 critical section
[ ] 所有相关 writers 已检查
```

## Liveness

```text
[ ] loser 仍可尝试后续 queued job
[ ] 没有新 deadlock path
[ ] exception/failure 不会永久持锁
```

## Failure

```text
[ ] effect-before-record crash window 有明确 counterexample
[ ] record-before-effect loss window 有明确 counterexample
[ ] 没有虚假宣称 exactly-once
```

## Evidence

```text
[ ] deterministic barrier
[ ] explicit failpoint
[ ] 没有 sleep-based correctness test
[ ] full suite still passes
```

---

# 17. 实验交付物

提交：

1. `writer-map.md`
2. `double-claim-interleaving.md`
3. `claim-contract.md`
4. safe claim implementation
5. deterministic safety tests
6. `failure-window.md`
7. chosen delivery guarantee + rationale
8. idempotent-sink experiment or equivalent evidence
9. Agent A/B comparison
10. final independent review

---

# 18. 评分重点

不是：

```text
用了 threading.Lock +20 分
```

而是：

### System model

你是否找对 authority/writers/interleaving？

### Contract

你能否明确 operation history 哪些是非法的？

### Atomicity

你能否指出 commit/linearization point？

### Failure semantics

你是否区分 duplicate 与 loss window？

### Evidence

你能否确定性构造 race/crash，而不是靠概率？

### Judgment

你有没有拒绝不可能由当前 mechanism 支撑的 exactly-once 承诺？

> **这一章最重要的能力，是在“代码看起来能跑”之前先看见时间轴上的 correctness hole。**
