---
id: case-M07
type: case_study
visibility: instructor
related: [M07]
---
# M07 Instructor Analysis — Double Claim、Linearization Point 与 Crash Window

> **Spoiler warning**：完成 [`../../labs/07-concurrency-lifecycle-failure.md`](../../labs/07-concurrency-lifecycle-failure.md) 前不要读。
>
> 这不是唯一正确 concurrency design。它记录一条 instructor reference reasoning：先从两个确定性的坏 history 恢复 contract，再判断哪些问题可以靠当前 process 内的 atomic decision 修，哪些问题其实缺少更高层 authority / durability assumption。对应来源与 course-synthesis 边界见 [`../../reading-notes/m07-source-audit.md`](../../reading-notes/m07-source-audit.md)。

M07 有两条故意并列、但不能用同一种修法回答的 running case。第一条里，一个 queued job 产生两个 successful claim receipts；第二条里，external effect 已发生，但 local completion record 尚未写入时发生 interruption，retry 又执行一次 effect。它们共同说明“最后 state 看起来合理”不足以证明 history 正确，但工程结论不同：前者在当前 process 内已有足够 mechanism 收敛 atomic claim decision；后者如果要求 arbitrary external effect exactly-once，则缺的是 TaskForge 当前并不拥有的 effect authority。

## 1. 第一个坏 history：两个 caller 都成功，最终 row 却看起来只有一个 owner

Teaching target `concurrent_claim.py` 的 baseline 近似是：

```python
if job.status == QUEUED:
    after_observe(...)
    job.status = RUNNING
    claim_owners[job.id] = worker_id
    return success
```

Deterministic barrier 强制两个 workers 先都完成 observation：

```text
A observes QUEUED
B observes QUEUED
--- both observations completed ---
A commits
B commits
```

Canonical probe 因而稳定得到 two-success history。最终 `Job.status` 仍然只是 `RUNNING`，`claim_owners[job.id]` 也只留下 A 或 B 中一个值；如果只看最后 state，系统甚至可能显得“只有一个 owner”。但已经发生的 operation results 是：

```text
claim(A) -> success
claim(B) -> success
```

对于 sequential specification，第一条 successful claim 已经应该让 job 离开 `QUEUED`，第二条不能再成功。**Final state 不能 retroactively 收回已经发出的 success receipt。**

这也是为什么一个静态 invariant 如“RUNNING job 有一个 recorded owner”太弱。当前 case 至少还需要 history-level obligation：每个 job 从 `QUEUED` 最多产生一个 successful claim transition；success receipt 与 committed owner 必须对应；commit 以后 competing claim 不能再次为同一个 job成功。

## 2. 从 bad history 推到 atomic semantic decision，再谈 linearization

Reference 的 local fix 使用一把很短的 lock，但 `threading.Lock` 不是课程答案。真正需要原子化的是一组语义事实：candidate 仍然 `QUEUED`、transition 到 `RUNNING`、owner identity 与 success receipt 必须属于同一个 claim decision。

Reference shape 是：

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
    return success receipt
```

Mutex、CAS、database conditional update、single-owner event loop 等都可能实现同一个 abstract contract。判断标准不是 primitive 名称，而是所有 competing writers 是否服从同一个 ownership invariant，以及 success 何时被允许返回。

这时 linearization intuition 才有用。对一个 concurrent history，我们先问：**是否存在至少一个 legal sequential explanation，并保持已经建立的 real-time precedence？** Herlihy–Wing 的定义不要求这个 witness 唯一；同一个合法 history 可以有多个 valid extension / linearization。课程不能把“有多个可能 linearization”误写成错误。

对这个具体 reference implementation，我们还能进一步指出一个 candidate linearization region：在 lock-protected decision 中重新确认 `QUEUED`，并一起提交 status + owner。A 若先在该 region 成功，B 后续就必须 re-check 到 stale/non-queued，从而无法再为同一个 job成功。这里说的是**这个 implementation candidate** 的 atomic region，不是“所有正确实现都必须有同一条代码行”。

## 3. Deterministic instrumentation 本身也参与 concurrency semantics

为什么 `after_observe` 必须留在 lock 外？如果先拿 lock，再在 barrier 等待第二个 thread：

```python
with lock:
    observe()
    barrier.wait()
```

第一个 thread 会占着 lock 等第二个；第二个又永远拿不到 lock，因此根本无法到 barrier。Test harness 自己制造 deadlock。

Reference 因而让 barrier seam 只负责稳定制造 stale observation；真正 authority decision 在 seam 之后重新检查。这个 layout 是当前 teaching fixture 的 deterministic-evidence requirement，不应被升级成 production instrumentation 的通用规则。

修完 one-job safety 后还要检查 progress。若 loser re-check 到 stale 就直接 `return None`，两个 workers 同时先看到 `job-1` 时，A 可以拿走 `job-1`，B 却立即退出，尽管 `job-2` 仍 queued。Reference 选择 `continue` 扫描，使当前 first-eligible / insertion-order selection semantics 下的 loser 仍能找到下一份 work。

这不需要被夸成严格 liveness theorem；它只说明**safety fix 不应无意退化当前可观察的 progress semantics**。Historical reference 在临时副本中用两个 focused histories验证：one job / two workers -> one success；two jobs / two workers -> two distinct successful receipts。

M07 也故意没有直接修改原 `worker.claim_next()`。`concurrent_claim.py` 是 teaching-only target，用来隔离 check-then-act / owner atomicity / history reasoning，避免 M02–M06 的 baseline artifacts因为本章实验被全部改写。这不是 production 建议保留两个 claim authorities；真实 architecture 最终仍需要把 lifecycle transition authority 收敛到一致的 semantic boundary。

## 4. 第二个坏 history：effect 已发生，completion record 没写

另一个 teaching target `effect_delivery` 近似是：

```python
if job_id in completed:
    return False

effect(job_id)

if crash_after_effect:
    raise SimulatedCrash

completed.add(job_id)
```

Canonical probe 稳定制造：external effect count 已经变成 1，local `completed` 仍缺该 job，然后 `SimulatedCrash` 被抛出；同一进程内 retry 再次执行 effect，于是 external effect count 变成 2。

这里必须非常精确：`completed_jobs` 是**进程内 `set`**，`SimulatedCrash` 是**同进程 exception/failpoint**。这个 probe 直接证明的是 effect-before-record ordering hole，以及在该 fixture 的 same-process retry 下 duplicate effect 会发生。它**没有**证明 starter 已经具备真实 process restart、durable completion record 或 restart recovery。

因此分析 record-first 时，必须先额外声明一个 starter 当前没有的 thought-experiment assumption：completion record 能跨目标 failure/recovery horizon 留存。只有在这个 assumption 下，把顺序改成：

```python
completed.add(job_id)
effect(job_id)
```

才会出现另一种可讨论的 recovery window：record 已 durable，process 在 effect 前消失，recovery 因 record 显示 done 而 suppress retry，于是 logical effect 永远没发生。

也就是：

```text
effect first  -> duplicate risk
record first  -> loss risk   # only under durable-record assumption
```

语句顺序没有凭空创造 exactly-once；当前 in-memory set 甚至还不满足 record-first recovery reasoning所需要的 durability 前提。

## 5. 更强的 external guarantee 必须让真正的 effect authority 参与

Instructor reference 没有魔改 `deliver_once()` 然后声称 TaskForge 已经 exactly-once。它改的是 dependency contract：假设 external sink 自己能按 logical effect ID 做 idempotent dedup。

Reference sink 可以近似表示为：

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

History 可以是：第一次 `sink(job-1)` 已产生 logical effect，随后 TaskForge 在 local completion 前 interruption；第二次 retry 再调用 `sink(job-1)`，sink 因同一 effect ID 去重，最后 TaskForge 才写 local completion。

于是 evidence 可以同时显示：

```text
callback_attempts = [job-1, job-1]
logical_effects   = [job-1]
```

这条 guarantee 很窄：**对于这个 sink contract，同一个 logical effect ID 的重试产生一个 logical sink effect。** 它不能推出 whole job、subprocess、filesystem mutation、或所有 downstream services exactly-once。一个 job 本来就可能包含多个 independently observable effects。

Authority 为什么重要也由此很清楚：真正的 effect owner 拥有 `(effect_id -> whether this logical effect committed)` 这份事实，TaskForge 本地 bookkeeping没有。Retry 不应该让 TaskForge猜“上一次到底发生了吗”，而是把 stable effect identity 送到能够 authoritative 地 dedup/fence 的 boundary。

Historical M07 reference 在临时 copy 中记录了第 3 个 focused test：duplicate callback attempts under one effect ID，sink 只产生 one logical effect。和前两个 claim tests 加起来是 `6 core + 3 focused = 9 passed`。这是 instructor historical evidence，不是 canonical starter oracle，也不把 sink-specific guarantee升级成 arbitrary exactly-once。

## 6. Timeout 与 retry 同时改变 knowledge 和 load

Timeout 本身不是 server-side transition。它只说明 caller 在 deadline 前没有观察到 response；original operation 可能没有开始、正在执行、已经 commit，或者 effect 已发生但 response 丢失。

这让 M04 request identity 在 M07 中继续有价值：caller 可以表达“这次 transmission 是同一个 logical request 的 retry”，而不是创建新 intent。但 request creation dedup 与 downstream effect dedup 仍是不同 authorities；有 request ID 不代表任意 external effect变成 exactly-once。

即使 operation 语义上允许 retry，retry 仍然制造 load。若 API / worker / effect client 三层各自总共最多 3 attempts，一个 logical action 最坏可能放大为：

```text
3 × 3 × 3 = 27 attempts
```

若某文档里的“retry 3 times”实际表示 1 initial + 3 retries，也就是 4 attempts，则三层可能是 `4^3 = 64`。所以设计文档最好直接写 `max attempts`，或者明确 `1 initial + N retries`，不要把 attempt 与 retry count 混成一个模糊词。

Backoff/jitter 能改变 retry schedule、降低同步 spike；retry budget 能限制 amplification。但它们都不创造 capacity，也不解决 non-idempotent duplicate effect。**Idempotent effect 也不意味着 unlimited retry 是安全的**：latency、resource consumption、deadline、overload 与 cascading failure 仍然存在。

## 7. Cancellation 把同一套 temporal reasoning迁移到 lifecycle contract

对于 running cancellation，最危险的压缩是把“cancel request accepted”和“command 已停止”写成同一个瞬间。如果 public `CANCELLED` 被 caller 理解为 execution 已不再发生，那么 request 仅被接受时就写 terminal `CANCELLED` 会比现实事实走得更快。

一种 plausible representation 是：

```text
RUNNING
  ↓ cancel accepted
CANCELLING
  ↓ executor confirms termination
CANCELLED
```

但 `CANCELLING` 不是唯一正确 design。也可以把 execution state 与 orthogonal `cancellation_requested` fact 分开。选择 criterion 应来自 caller 需要区分哪些事实、哪些 transition 由谁确认，而不是“并发系统都应该多一个 state”。

同样，当前 canonical `worker.finish(job_id, exit_code)` 只要求 job 处于 `RUNNING`；它没有 claimant identity / attempt fencing contract。未来如果 recovery protocol 需要 stale owner 不能 finish current execution，owner-bound finish 可以成为新的 product/protocol candidate，但 M07 instructor case不能把这个 future design倒写成 starter 已有事实。

如果 finish 与 cancellation acknowledgment overlap，谁获胜也应由 product conflict semantics 决定，而不是“最后一次 write wins”。后续 lease/heartbeat/fencing 只有在系统真的选择 time-bounded ownership / reclaim semantics 时才相关，本章不提前建立完整 distributed recovery protocol。

## 8. 几种看起来像修复、实际只是在移动问题的路径

**Wrap everything in one `RLock`**：scope 远超当前 invariant，未来可能把 blocking I/O 也放进 critical section，并把 authority design藏在 synchronization primitive 后面。

**Re-check but no synchronization**：A、B 仍可以一起执行第二次 check，再一起写；只是 race window 移了位置。

**Two callers 都 success 后再“修复 owner”**：history violation 已经发生，事后只保留一个 owner 不能收回另一条 success receipt。

**Record completion first**：只有在额外 durable-record assumption 下才能让 retry 看到 record；即使如此，它把 duplicate window 换成 loss window，不是 exactly-once。

**Infinite retry because sink is idempotent**：idempotency 只约束 duplicate effect semantics，不解决 overload、deadline、resource use 或 liveness。

这些 rejected paths 的共同问题不是“代码风格不好”，而是它们没有真正满足被讨论的 contract，或者用一个 mechanism回答了错误层级的问题。

## 9. Review Agent 应先重建 model，再看 lock diff

面对一个 concurrency patch，reviewer 不应从 `threading.Lock()` 那行开始。至少需要恢复：writer/authority map、一个 concrete bad interleaving、目标 invariant、history-level legality、candidate linearization/commit region、safety evidence、progress/liveness evidence、failure window，以及 retry/effect guarantee 的精确 scope。

尤其要检查：

- 所有会改变同一 invariant 的 writer 是否经过一致 decision boundary；
- state machine / owner registry / cancellation projection 是否只是部分 state model，scope 有没有写清；
- critical section 是否引入 blocking I/O、lock-order cycle 或 starvation risk；
- deterministic probe 控制的 failure/interleaving是否和真实 claim 一致；
- timeout 后 caller 到底知道什么；
- attempt/retry policy 与 external-effect guarantee 是否被错误合并；
- tests 是否检查 receipts/history，而不是只看最后 state；
- stress “跑 1000 次没出错”有没有被冒充 race-free proof。

Agent task contract 可以要求这些 artifacts，却不应该预先规定一定用 mutex/CAS/actor。Independent review 的任务是挑战 engineering proposition，而不是检查 Agent 有没有照模板写出某个 primitive。

## 10. Instructor judgment

M07 的两个 running case 最终应该得到**不同类型的答案**。

Double claim 的问题是 current process 内已经存在足够 authority 和 synchronization mechanism，只是 observation 与 commit 没形成一个 coherent atomic decision；reference 可以用 short lock + re-check 修，但其它等价 mechanism也成立。

External-effect crash window 则不同：当前 TaskForge local bookkeeping既不拥有 arbitrary external effect truth，也没有 durable restart protocol。若 product 要 stronger guarantee，必须明确 attempt/retry semantics、failure horizon，以及真正 effect owner 能提供什么 idempotency/fencing/transactional integration；不能靠 rearrange two lines 得到 exactly-once。

M07 因而真正增加的是一组 temporal reasoning objects：operation history、interleaving、atomic/linearization decision、failure window、caller knowledge、retry amplification。它们把前面的 `state + contract + ownership` 扩展成“状态在时间里怎样被多个 actor 观察和改变”。后续 compatibility、architecture 与 production reliability 都会继续依赖这套模型，但不会因此把 M07 的 reference mechanisms自然化成唯一 architecture。
