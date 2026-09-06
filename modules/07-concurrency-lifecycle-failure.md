# M07 — Concurrency、Lifecycle 与 Failure：把时间纳入 Contract

前六章里，我们已经反复问过：谁拥有 state、operation 承诺什么、哪些 behavior 必须保持、什么 evidence 足以支持一次 change。那些问题还缺一个维度：**时间**。

只要两个 operation 可以 overlap，或者一个 operation 可以在中途 crash、timeout、restart、retry，原来隐藏在顺序代码里的假设就会暴露出来。`read → decide → write` 不再天然连续；“函数已经返回 success”也不再是我们唯一需要描述的时刻。M07 不打算把课程变成 mutex / semaphore / actor primitive 目录，而是先追着这些时间上的裂缝问：哪些历史还能算合法，另一个 actor 能在哪两步之间行动，哪些事实必须一起生效，crash 或 retry 后又留下了什么。

## 1. 最终 state 看起来正常，为什么还是错了

先看 TaskForge 为本章专门准备的 `concurrent_claim.py`。starter 会扫描第一个 queued job，允许测试在 observation 之后插入一个 hook，然后把 status 与 owner 写进去：

```python
for job in state.jobs.values():
    if job.status != JobStatus.QUEUED:
        continue

    if after_observe is not None:
        after_observe(worker_id, job.id)

    job.status = JobStatus.RUNNING
    claim_owners[job.id] = worker_id
    return ClaimReceipt(job_id=job.id, worker_id=worker_id)
```

单独看一个 caller，这段代码很自然：看见 `QUEUED`，于是 claim，最后留下一个 `RUNNING` job 和一个 owner。现在让 worker A 和 worker B 同时执行，并让 `after_observe` 的 barrier 保证两边都先看见同一个 `QUEUED`：

```text
Worker A                         Worker B
--------                         --------
observe job-1 == QUEUED
                                 observe job-1 == QUEUED
-------- both observations complete --------
write RUNNING, owner=A
return success
                                 write RUNNING, owner=B
                                 return success
```

运行仓库里的真实 probe：

```bash
cd labs/taskforge
PYTHONPATH=src uv run --with pytest --no-project python tools/m07_interleaving_probe.py
```

当前 baseline 会稳定报告：

```text
[RACE REPRODUCED] one queued job produced two successful claims: worker-A, worker-B
[FINAL STATE] one RUNNING job and one recorded owner can hide the bad history
```

最后对象甚至没有明显 corruption：`status == RUNNING`，`owner` 也是 A 或 B 中的一个。真正无法接受的是已经发生过的 **operation history**：

```text
claim(A) -> success
claim(B) -> success
```

如果 sequential contract 是“一个 queued job 最多产生一次 successful claim”，那么第一次 success 之后 job 已经不再是 queued，第二次就不可能仍然 success。坏的是 history，而不是某个字段最终长得难看。

这时再引入 **race condition** 才有对象可指。MIT 6.102 给出的 framing 是：correctness 是否依赖事件的相对时序。课程把它翻译成一个工程判断：如果存在一种系统允许的 interleaving，会破坏 intended postcondition / invariant / operation history，那么这里就有 race。两个 thread 的存在本身不是 race；反过来，async task、多个 process、多个 client、queue consumer，甚至两个被 retry 的 attempt，都可能竞争同一个 state 或 effect。

这也是为什么经典的 check-then-act 形状危险：

```text
READ / CHECK
    |
    | another actor may change the fact here
    v
ACT / WRITE
```

问题不在 `if` 这个语法，而在从 check 到 act 之间，谁保证 predicate 仍成立。回答“这两行很近”“通常 scheduler 不会刚好切走”或者“当前解释器碰巧有某种执行特性”，都不是稳定的 correctness argument；实现语言、process boundary 或 scheduling policy 一变，论证就消失了。

同一问题也不会因为换成 message passing 自动消失。一个 authority 可以把 mutation confinement 到自己内部，但如果 client 先发 `get_status`，收到 `QUEUED`，另一个 client 随后先 `claim` 成功，第一个 client 再根据旧 observation 发 `claim`，它仍然基于 stale fact。更好的 protocol 往往需要让“如果仍 queued 就 claim”成为 authority 内部的一个 semantic operation，而不是把 check 与 act 拆成两个独立 message。

## 2. Sequential state machine 不够：edge 也需要 protocol semantics

M01 已经可以把 TaskForge lifecycle 画成：

```text
QUEUED -> RUNNING -> SUCCEEDED
                 \-> FAILED
QUEUED -> CANCELLED
```

但这张图只告诉你哪些 state transition 在顺序世界里合法。M07 还要问：`claim` 与 `claim` 能不能 overlap？`claim` 与 `cancel` 呢？`finish` 与未来的 running cancellation 呢？一个 worker 在 transition 中间消失时，谁接管剩下的 lifecycle？

因此一个 lifecycle operation 至少需要再补几列：

| Operation | Required fact at decision time | 必须一起成立的结果 | 可能冲突的 operation |
|---|---|---|---|
| claim | job 仍是 `QUEUED` | job 进入 `RUNNING`，且 committed owner 与 success receipt 一致 | claim, queued cancel |
| cancel queued | job 仍是 `QUEUED` | job 进入 `CANCELLED` | claim |
| finish（current starter） | job 是 `RUNNING` | terminal result 被提交 | duplicate finish, cancellation |

这里要区分两种不同的 “owner”。M02 讨论的是 **state write authority**；当前 `worker.finish(job_id, exit_code)` 只检查 `RUNNING`，并没有接收 worker identity，也不会查询 `claim_owners`，所以 starter 目前没有“只有 claimant 才能 finish”的 worker-owner contract。未来如果产品选择 owner-restricted completion，那会是一个新增 protocol rule：此时 finish 的 decision predicate 才需要把 committed claimant identity 纳入，并重新分析 owner loss / recovery。

这张表仍然只是一个 projection：它描述的是本章正在分析的 lifecycle facts，不是 TaskForge 的完整 state model。以后如果 cancellation、ownership 或 recovery 又出现新的 contract-relevant dimension，不能因为这张表没有列出就假装它们不存在；要么扩表，要么明确另建一个只投影相应维度的 model。

最关键的问题是：**一次 operation 中，哪些 read / validate / write 必须构成一个不可被竞争者拆开的 decision？** 对 double claim 来说，至少“确认 job 仍 queued”与“提交 claimed facts”不能分别基于两个可被打断的时刻。

实现这个 semantic decision 可以有很多机制：mutex、compare-and-swap、database conditional update / transaction、single-owner event loop、serialized message handler 都可能成立。这里不能从 primitive 倒推 contract。先确定 invariant 与 atomic decision，之后才有资格比较哪种 mechanism 最适合当前 system boundary。

这把 M02 的 state ownership 推进一步。仅仅知道“谁拥有 state”还不够；owner 还需要暴露足够原子的 semantic operations。否则 caller 虽然不能直接 mutate representation，却仍可能通过多个合法 API call 拼出一个不安全的 check-then-act protocol。

TaskForge starter 又故意把 lifecycle status 和 `claim_owners` 放在两个 mutable location。这个教学 fixture 的目的正是让学生看到跨 representation 的 invariant；它不是在建议 production system 长期保留两个独立 claim authorities。无论最后 representation 是一个 object、两个 dict 还是数据库多列，review 的问题都应是：**哪些 facts 必须作为同一个 abstract decision 被观察和提交？**

## 3. Function boundary 不是 atomicity boundary

假设有人把 `claim_next()` 整个包进一个函数，甚至再包一层 class method。代码组织变整齐了，但 caller 真正需要知道的是：从哪个时刻开始，其它 actor 必须把这个 claim 当成已经发生？

Herlihy 与 Wing 的 linearizability 给了一个很有用的 operation-level abstraction：一个 concurrent operation 可以被理解为在 invocation 与 response 之间的某个瞬间原子生效，同时保持必要的 real-time ordering。M07 不要求 formal proof，也不会把 linearizability 当成所有 distributed workflow 的默认 consistency level；我们只借它问一个很具体的问题：

```text
claim(job)

invocation ------------------------------ response
                    ^
                    |
          other actors must treat
          the claim as committed here
```

这个位置就是本章口语中的 **linearization point / commit point**。

这里有一个容易被教学 shorthand 偷换掉的 qualifier：**linearizable history 只需要存在至少一个合法 sequential explanation，并保持 real-time precedence；这个 explanation 不要求唯一。** 同一个正确 concurrent history 完全可能有多个合法 linearizations。对 TaskForge 来说，baseline double claim 错在两个 success 无法对应到任何合法 sequential history；而下面 reference design 之所以要求指出清楚的 code-level point，是为了说明这个**具体 implementation**怎样实现 abstract atomic effect，不是为了证明“正确 history 必须只有一个 linearization”。

对于当前 TaskForge lab，instructor reference 选择了一个小而直接的 candidate：先在 lock 外扫描并保留 `after_observe` teaching seam；真正要 commit 时进入一小段同步区域，重新确认 candidate 仍是 `QUEUED`，然后把 `RUNNING` 与 owner 一起提交。如果 re-check 发现 observation 已 stale，就继续扫描后续 queued job。

概念上是：

```text
observe candidate
run deterministic after_observe seam
        |
        v
enter claim synchronization boundary
        |
re-check job is still QUEUED
        |
commit RUNNING + owner + success receipt
        |
leave boundary
```

这不是本章唯一允许的 design。Lab 还要求比较 single-authority operation；未来如果 state 进入数据库，conditional update 也可能比 process-local lock 更自然。reference path 的价值只是让当前 starter 有一个可以实际验证的最小实现方向。

为什么一定要 **re-check**？因为 lock 保护的是 commit decision，不会让 lock 外已经读到的旧事实自动变新。如果两个 worker 都在锁外看见 `QUEUED`，A 先进入 boundary 并 commit；B 随后进入 boundary 时必须重新确认 predicate，否则只是把 race window 移到了 lock 外。

为什么 `after_observe` 不能简单放进这把 lock 里？真实 probe 的 barrier 要等两个 worker 都完成 observation；若 A 持锁后进入 barrier，B 会在拿锁之前被挡住，永远到不了 barrier。测试 instrumentation 也参与 concurrency semantics。这里保留 seam 的目的不是 production observability，而是**确定性制造 stale observation**，然后验证真正 authority decision 能拒绝它。

## 4. “加锁修了 safety”之后，系统还能不能前进

现在假设 one-job/two-worker case 已经只有一个 success。我们还不能立刻宣布 concurrency design 完成，因为 correctness 至少包含两类不同的问题。

MIT 6.102 Mutual Exclusion 区分 **safety** 与 **liveness**。在当前 TaskForge contract 里，safety 可以包括：同一个 queued job 不会产生两个 successful claim；terminal job 不会被重新 claim；`finish` 只从 `RUNNING` 提交 terminal result。若未来 design 明确加入 claimant-bound completion authority，才可以再增加“非 committed claimant 不能 finish”这一条 safety property。Liveness 则关心健康条件下系统能否继续 progress：queued job 在有可用 worker 时不会因为我们的修复永久卡住，lock ordering 不会造成 deadlock，某个 contender 不会因为同步设计被无界地饿死。

最极端的“安全”实现当然可以是拿到一把永不释放的锁。double claim 从此不会再发生，因为任何 claim 都不会再发生。这说明“有锁，所以 race 修了”最多是一个 implementation observation，不是完整 design argument。

M07 lab 特意加入 two-jobs/two-workers 场景。两个 worker 都先撞上 `job-1`；winner commit `job-1` 后，loser 重新检查发现 stale。一个过度保守的实现可以直接 `return None`。它对 one-job safety 没问题，却不必要地让 `job-2` 留在 queue。Instructor reference 因此选择 `continue`，让 loser 继续扫描；这不是宣称所有 queue 都必须拥有某种强 fairness，而是在当前 `claim_next` 语义下保留一个很基本的 progress expectation。

同步边界的大小也影响 liveness。下面这种修复可能压住许多 race：

```python
with global_lock:
    read_db()
    call_network()
    execute_command()
    write_logs()
```

代价是一个慢 dependency 会长时间阻塞所有 claimant，cancellation/exception cleanup 更难，未来还可能和别的 lock 形成 cycle。更稳定的设计目标是保护**最小 semantic atomic decision**，例如 `QUEUED -> RUNNING(owner=A)`；真正 command execution 通常不应该被同一把全局 claim lock 包住。

Lock scope 还必须和 invariant boundary 对齐，而不是和 container 对齐。假设 status 放在一个 dict，owner 放在另一个 dict；“两个 dict 各自 thread-safe”不能推出 `RUNNING iff committed owner exists` 这样的跨结构 invariant 永远成立。同样，只修 `concurrent_claim.claim_next()` 也不自动意味着整个 lifecycle thread-safe。`worker.claim_next()`、`service.cancel()`、`worker.finish()`、未来的 recovery/admin path 只要能写同一事实，都必须进入 writer map，检查它们是否服从相同 authority/synchronization rule。

如果系统有多把锁，review 也不能只逐函数看 `with lock:`。例如一条 path 先拿 jobs lock 再拿 workers lock，另一条反过来，就可能形成 cycle。建立全局 lock order，或者更好地减少 simultaneous lock ownership，都是 liveness reasoning 的一部分。

## 5. Concurrency evidence 应该主动构造坏 history

普通 stress test 很容易写：

```python
for _ in range(10000):
    start_two_threads()
```

跑过一万次只能说明在这些运行里 scheduler 没让 oracle 看到 bug，不能证明不存在允许的坏 interleaving。它还会把 evidence 变得环境相关：本地偶尔红、CI 偶尔绿，大家最后用 `sleep()` 调概率。

M07 的 starter 采用相反策略：如果我们已经知道 bug 需要“两边都基于同一个 `QUEUED` observation”，就用 `threading.Barrier` 直接制造这个条件。测试不是等 scheduler 碰运气，而是在问一个清楚的 claim：

> 当两个 claim 都曾观察到同一个 queued candidate 时，最终最多一个能够成功 commit 这个 job。

Oracle 也必须看 history，而不只看 final state。下面的断言会漏掉 baseline bug：

```python
assert status == JobStatus.RUNNING
assert owner in {"worker-A", "worker-B"}
```

真正高信息量的 observation 还包括两个 operation 的结果：

```python
results = [claim_A_result, claim_B_result]
assert successes(results) == 1
```

这把 M03 的 executable evidence 扩展到了 operation history。对于更复杂的 lifecycle protocol，可以记录 invocation / return sequence，再问它是否能解释成一个符合 sequential specification 的合法 history。M07 借用 linearizability intuition 就到这里；不要求学生实现通用 history checker。

确定性 instrumentation 也有自己的 proof boundary。一个 barrier test 可以稳定拒绝已知 double-claim interleaving，但“这个 test 绿了”仍不能证明所有 concurrency bug 都消失；writer map、其它 conflict path、deadlock、starvation 与 operation 被中断后的行为仍需独立检查。搜索和 stress 可以帮助发现新候选，不能替代 contract-level reasoning。

## 6. Crash 之后，哪一步已经发生？

Double claim 的问题发生在两个活着的 actor 交错。现在看第二个 TaskForge teaching target：没有第二个 thread，也会出现跨时间 correctness hole。

`effect_delivery.py` 当前是：

```python
def deliver_once(job_id: str, effect: Callable[[str], None], *, crash_after_effect=False) -> bool:
    if job_id in completed_jobs:
        return False

    effect(job_id)

    if crash_after_effect:
        raise SimulatedCrash(...)

    completed_jobs.add(job_id)
    return True
```

函数名 `deliver_once()` 是故意比实现能支持的 guarantee 更强。真实 probe 使用 `SimulatedCrash` 这个**同进程 failpoint**：先让 external effect 发生，再在 `completed_jobs.add(...)` 之前抛出异常。它不是一次真实 process restart；它确定性证明的是“effect 已发生、completion write 尚未发生，随后 retry 会再次调用 effect”这个 ordering hole：

```text
[CRASH REPRODUCED] effect happened, completion record was lost, retry produced a duplicate effect
```

这个 failpoint 与真正 process crash 还要再区分一层。当前 `completed_jobs` 只是进程内 `set`；如果 Python process 真正退出，它自己也不会作为 recovery record 留下来。因此 starter 直接给出的 evidence 是 **effect/write ordering counterexample**，不是“这只 set 已经实现 crash recovery”。真正讨论 SIGKILL、power loss、runtime death 或 machine reboot 时，必须额外问哪些 facts 能跨 failure horizon 留存，以及 recovery authority 会看到什么。

普通 exception 与 crash 的区别也因此很重要。`try/finally` 至少假设当前 process 仍有机会运行 cleanup；真正 process death 可能根本不给你 finally。Process-local mutex 常可由 OS 回收，但 durable DB status、remote reservation、filesystem marker 或已经发生的 external effect 不会因此自动被撤销。

分析 multi-step operation 时，一个很有效的做法是把 interruption 插到每两个 effect 之间。先严格按当前 starter 的同进程 failpoint / retry horizon 看 effect-first ordering：

| Interruption point | local `completed` | external logical effect | same-process retry 后风险 |
|---|---:|---:|---|
| before effect | 0 | 0 | 可以再次尝试 |
| after effect, before record | 0 | 1 | retry 可能重复 effect |
| after record | 1 | 1 | local bookkeeping 会抑制后续 attempt |

为了隔离“仅仅调换顺序能不能解决问题”这个问题，再做一个明确的 thought experiment：**暂时假设 completion record 能跨我们关心的 interruption / recovery horizon 留存**，然后把顺序倒过来，先记录 completion，再做 effect。这个额外 assumption 很重要；当前 starter 的 in-memory `set` 本身并不满足它。在这个 assumption 下，effect-first 的 duplicate window 会被换成另一个 window：

| Crash point | durable completion record | external logical effect | recovery 后果（在上述 assumption 下） |
|---|---:|---:|---|
| before record | 0 | 0 | retry |
| after record, before effect | 1 | 0 | retry 被抑制，effect 丢失 |
| after effect | 1 | 1 | 当前顺序下完成 |

所以即使给 record-first 补上 durability assumption，它仍不是 exactly-once 修复，只是把 duplicate risk 换成 loss risk。若 record 根本不 durable，真实 restart 还会有另一组行为。并且这些表主要分析 effect/record ordering；如果允许多个 caller 同时进入 `deliver_once()`，还需要另外处理 concurrent check-then-act。不要让一个 failure model 的表格假装覆盖另一个维度。

根因是 local completion record 和 external effect 不属于同一个 atomicity authority。只要这两个事实不能在同一 atomic boundary 内提交，单纯重排本地语句就无法凭空得到“一个 logical operation 恰好产生一个 external effect”的强保证。

## 7. 先选择 guarantee，再谈 retry mechanism

看到上面的两个表以后，“失败后重试，确保只执行一次”已经不是一个足够精确的需求。至少要先问：这里的“执行一次”指的是 attempt、process launch、job terminal state，还是某个具体 external effect？不同事实可能由不同 authority 拥有。

一个系统可以选择不同 guarantee，关键是把 trade-off 写清楚。

**At-most-once attempt** 偏向“不重复 attempt”。一种 candidate 是在放行 attempt 前，先原子地建立一个能跨目标 failure horizon 留存的 admission / attempt record；如果之后 crash，可以接受这个 attempt 对应的 effect 最终没发生。这里的 guarantee 只约束“被 authority 放行的 attempt 次数”，不自动约束 attempt 内部可能触发的所有 downstream effects。它是否真的成立还取决于 concurrent callers 能否重复建立 record、record durability 与 recovery policy，不能只靠“代码顺序看起来 record-first”宣布。

**At-least-once attempt** 偏向“不要因为一次未确认 failure 就永远放弃 work”。在系统另有 durable work identity / recovery trigger、能够在失败后再次尝试未确认 work 的前提下，recovery 会保证至少发起一次 attempt，并可能发起多次。它**不自动等于 at-least-once external effect**：effect 是否至少发生一次，还取决于 attempt 在哪里失败、effect owner 的 contract 与 recovery 何时停止。当前 effect-first teaching shape 只说明：一旦 callback 已成功产生 effect、completion record 又没写，后续 retry 可能 duplicate。starter 的 in-memory set + 同进程 failpoint 是这个 ordering hole 的最小 demonstration，并不单独提供 restart recovery。

如果 external effect owner 支持 **idempotency key**，这条路会更强。Instructor reference 用一个小型 sink 演示：TaskForge 对同一个 `effect_id` 可以调用两次，但 sink 自己拥有 `effect_id -> logical effect already committed?` 的 knowledge；第二次 attempt 被 effect authority 去重，于是：

```text
callback attempts = 2
logical sink effects = 1
```

这里的 guarantee 必须收窄到这个 boundary：**对这个 sink，相同 logical effect ID 的 retry 产生一个 logical sink effect。** 它不能推出整个 job、subprocess、filesystem mutation 或所有 downstream service 都 exactly once。一个 job 可能包含多个 independently observable effects，每个 effect 的 authority 和 dedup capability 都不同。

还有更强的 transactional coordination candidate：如果 completion record 与 effect 本来就能进入同一 transaction，或者系统有专门的 coordination protocol，就可以设计不同 guarantee。M07 不展开具体 pattern；重点是知道当前 starter 没有这种 mechanism，因此 Agent 或 reviewer 不能靠一个 local `set()` 伪造更强 contract。

同样的 failure-window 方法也能迁移到真正的 lifecycle。假设 worker claim 后要：

```text
1. mark RUNNING
2. launch subprocess
3. record pid
4. acknowledge claim
```

每一步之间 crash 都留下不同事实：

| Crash point | State-side facts just before failure | External facts | Recovery question |
|---|---|---|---|
| before 1 | job 仍 queued | no process | claim 是否可重新尝试？ |
| after 1 before 2 | `RUNNING` | no process | 这个 state 是否 durable；若是，谁处理 orphaned running state？ |
| after 2 before 3 | `RUNNING` | process exists | state / process identity 哪些能被 recovery 重新发现？ |
| after 3 before 4 | `RUNNING + pid` | process exists | 这些 facts 是否跨 failure 留存；caller 若没看到 ack，下一步做什么？ |

这张表刻意不假设 state-side facts 一定 durable；“哪些 facts 能跨 failure 留存”本身就是 recovery contract 的一部分。表格没有自动给答案，但会迫使设计暴露 **recovery authority**：原 owner 消失后，谁有资格判断这次 work 仍活着、已经完成、应该终止，还是可以重新执行？

## 8. Timeout 是 knowledge state；retry 还会制造新的 load

假设 `submit(job)` 穿过 network boundary，caller 等到 deadline 却没收到 response。至少有这些可能：request 根本没到 server；server 收到但尚未 commit；server 已 commit 但 response 丢了；server 已经进入后续 execution。

因此 timeout 本身不能推出 operation failed。更准确的说法是：**caller 在 deadline 内没有获得足够信息确认 outcome。** 这是 caller knowledge state，不是一个 server-side lifecycle transition。

这时 M04 的 request identity 才真正派上用场。若 retry 表示同一个 logical request，稳定 identity 可以让 server 识别“这是同一个 intent 的另一次 attempt”，而不是误创建第二份 work。但要保持边界：request dedup 只回答那个 request boundary 的 intended effect；它不自动把 downstream subprocess/email/payment 也变成 deduplicated effect。

即使 retry 在语义上安全，也不意味着可以无限重试。Google SRE 的 cascading-failure material 强调，retry attempt 仍然是一个真实 request。假设三层各自允许 **最多 4 次 total attempts**，一个 logical request 最坏可能放大成：

```text
4 x 4 x 4 = 64 downstream attempts
```

因此设计文档最好写 `max attempts` 或明确“1 initial + N retries”，不要用含糊的“retry 3 次”让不同人算出不同 contract。

Review retry policy 时至少要知道：哪一层拥有 retry；什么 error 可 retry；最大 attempts / total deadline 是什么；有没有 backoff、jitter 或 system-wide retry budget。SRE 与 AWS 的 guidance 说明了两个相关 failure mode：exponential backoff 可以降低频率，但如果大量 client 在同一时刻失败、又按相同 schedule 重试，仍会形成 synchronized spike；jitter 的作用之一就是把 attempts 在时间轴上打散。

所以 retry timing 也是 concurrency behavior，而不只是 performance tuning。一个 operation 可以是 idempotent 的，同时因为无限 retry 把一个局部故障推成 overload positive feedback。**duplicate semantics 与 load/liveness semantics 是两个不同 proof obligation。**

## 9. Cancellation 与 restart：state name 不能比现实走得更快

现在把前面的 temporal model 迁移回 TaskForge lifecycle。当前系统对 running job 的 `cancel()` 直接返回 `False`；Lab 只要求你设计未来“running job 可以 cancel”的 protocol，不要求这一章真的把它实现进 core。

一个危险的 spec 是把 `cancel(job)` 压成一个 boolean，却不说明这个 boolean 对应哪个时刻。对于 running work，现实里可能依次发生：request accepted、signal sent、worker acknowledged、process exited、cleanup completed、terminal state recorded。它们不是同一个瞬间。

因此 `cancel accepted` 与 `work stopped` 必须保持 temporal distinction。至于怎样表示它，设计并不唯一。一种 candidate 是增加 `CANCELLING`：

```text
RUNNING
   |
   | cancel request accepted
   v
CANCELLING
   |
   | executor confirms termination
   v
CANCELLED
```

另一种 candidate 是保留 execution status 仍为 `RUNNING`，另有 `cancellation_requested=true` 之类的 request-state projection，直到 executor 真正停止后才把 execution lifecycle 写成 `CANCELLED`。M01 已经用过这种“orthogonal flag / projection”思路。哪个表示更好取决于 caller 需要区分什么、哪些 transition 必须原子、未来查询与恢复如何工作；M07 不应因为 running example 顺手选择一个 state，就替 design authority 做完这道题。

无论选哪种 representation，有一条 temporal consistency 不能丢：如果 `CANCELLED` 在 public contract 里意味着 command 已不再执行，就不能在“只接受了 cancellation request”时提前写 `CANCELLED`。Acceptance success 也不能因为后续 termination failure 被 retroactively 改写成“当初没有接受”；更准确的 model 应分别表达 request 是否被接受、work 是否停止、recovery 是否完成。

`finish` 与 cancellation acknowledgment 还可能 overlap。它们谁赢不能靠最后一次 write；要回到 concurrent protocol，定义 commit point 和 conflict semantics。比如 process 在 cancel request 之后但 signal 生效前自然完成，到底应该记录 `SUCCEEDED` 还是 `CANCELLED`？没有 product contract，代码本身给不出唯一答案。

Worker crash 又增加另一个 lifecycle pressure：

```text
status = RUNNING
owner = worker-A
worker-A disappears
```

如果只有 owner 会 cleanup，这个 job 可能永久 orphan。一种常见候选是 lease / heartbeat，让 ownership 带 expiry；expiry 后 recovery 可以 reclaim。但 lease 本身又引入 clock assumption 与 stale-owner risk：旧 worker 也许并没有真的死，只是 heartbeat 延迟；新 worker reclaim 后，旧 worker 恢复并继续写结果，就需要 generation/token/version/fencing 一类更强 semantics 阻止 stale owner commit。

M07 只要求你看见这条 reasoning chain，不展开完整 distributed lease/fencing design。重要的是：restart recovery 不是 `finally` 的延长版，而是一个需要单独 authority、state 与 conflict rule 的 protocol。

## 10. 给 Agent 的任务不能只写“修 race，加测试”

Agent 很容易生成几类看起来合理的伪修复：给整个模块套 global `Lock`；写一个 1000 次 stress test；catch exception 后无条件 retry；看到 request ID 就声称 exactly once；用 `sleep(0.1)` 改变 timing。它们都可能让某个 symptom 消失，却没有完成前面的 correctness argument。

一个更可审查的 TaskForge task contract 可以是：

```text
Current invariant:
- a queued job may produce at most one successful claim.
- the committed owner and successful claim receipt must agree.

Required analysis before edit:
1. enumerate all lifecycle writers relevant to claim state;
2. provide the concrete double-claim interleaving;
3. identify the proposed linearization point;
4. state safety and basic progress expectations separately.

Implementation constraints:
- preserve the deterministic after_observe seam;
- do not hold the claim synchronization boundary during command execution;
- preserve the current first-eligible/insertion-order selection semantics at the commit decision;
- if a candidate becomes stale, do not unnecessarily prevent claiming later queued jobs;
- do not change M02-M06 public behavior unless the task explicitly requires it.

Evidence:
- deterministic one-job/two-worker reproduction that fails on baseline;
- exactly one successful claim for the competing job after the fix;
- two-job/two-worker progress sanity check;
- full regression suite;
- explanation of synchronization/authority scope and remaining risks.
```

注意这里没有要求“必须用 `threading.Lock`”。Task contract 约束的是 invariant、proof shape、non-goal 与 evidence，implementation candidate 仍可比较。

Crash-safety task 更不能写成“确保 job 只执行一次，失败就 retry”。Agent 在动代码前应该先列出：要保护的是哪个具体 effect；local record 与 effect 是否共享 transaction authority；attempt/retry side 选择什么 semantics（例如 at-most-once attempt 或在明确 recovery assumptions 下的 at-least-once attempt）；这个具体 external effect 又承诺什么 guarantee；downstream 是否支持 stable idempotency key；timeout 后 caller 可能不知道什么；retry budget 归谁。**Attempt policy 与 effect guarantee 都属于 design authority，不应由 Agent 在 patch 中默默替系统设计者决定，更不能用前者替代后者。**

## 11. Review concurrent lifecycle change 时，沿着时间轴检查

完成 patch 后，可以按下面几组问题独立 review。它们不是“用了哪个 primitive”的清单，而是前面 reasoning 的压缩形式。

### Shared authority 与 state projection

- 哪些 actor / path 可以写同一个 lifecycle fact？writer map 是否完整？
- representation 中有没有第二份可独立漂移的 authority？
- 某个 table / flag / lease model 是完整 state，还是明确 scope 的 projection？
- 所有相关 writer 是否服从同一个 atomicity / ownership rule？

### Interleaving 与 atomicity

- operation 在哪里可能 yield、block、await 或被另一个 actor 插入？
- check 与 act 之间依赖的 predicate 谁保证？
- abstract operation 的 commit / linearization point 在哪里？
- final state 与 operation history 是否都能解释成合法 behavior？

### Safety 与 liveness

- 什么坏事不能发生？tests 是否直接观察它？
- 一个过度保守的 safety fix 会不会让工作永久等、制造 deadlock/starvation，或把慢 I/O 锁进 global critical section？
- lock order / cancellation / exception cleanup 是否闭合？

### Failure、timeout 与 retry

- crash 可以插在哪两个 effects 之间？每个 window 留下哪些 durable/local/external facts？
- owner 消失后谁负责 recovery？
- timeout 后 caller **知道什么、不知道什么**？operation 是否可能已 commit？
- retry 是 same logical request 还是 new intent？会不会 duplicate effect？
- retry 是否放大 load；deadline、backoff、jitter、attempt budget 归谁？

### Evidence

- 已知 race 是否有 deterministic reproduction，而不是主要依赖 sleep/stress？
- failure 是否有 explicit failpoint / failure table？
- oracle 是否检查 history / side-effect count，而不只看最终字段？
- evidence 覆盖了哪些 interleavings / failure windows，哪些仍是 remaining risk？

## 12. TaskForge M07 Lab：两个 correctness hole，要给两种答案

[Lab 07](../labs/07-concurrency-lifecycle-failure.md) 把这一章压成两个 teaching targets。

**Target A — double claim** 在当前 process 内已经有足够 mechanism 构造并修复：先写 writer map 和 bad interleaving，再比较实现方向，选择一个清楚的 commit point，用 deterministic barrier 证明同一个 queued job 只产生一个 successful claim，并检查 loser 仍能继续尝试后续 work。

**Target B — external effect crash window** 则故意不提供能够让任意 external callback exactly once 的本地 mechanism。你需要实际复现 duplicate，写 effect-first / record-first failure table，说明为什么 reorder 只是在 duplicate 与 loss 间移动风险，然后选择一个明确 guarantee。Instructor reference 用 idempotent sink 做实验，但 lab 允许其它被当前 authority/mechanism 真正支持的答案。

这两个目标放在一起，是为了训练一个重要判断：有些 correctness hole 可以通过一个更好的 local atomic decision 修复；另一些 hole 暴露的是 authority / contract assumption 不够，继续“多写一点本地代码”反而会制造虚假 guarantee。

## 13. 来源边界与本章不能推出的结论

本章的 race、shared-memory / message-passing concurrency 与普通测试难以稳定复现 race 的 framing 来自 MIT 6.102 Concurrency；atomic region、`await` 可能发生 interleaving、safety / liveness 与 deadlock reasoning 来自 MIT 6.102 Mutual Exclusion。MIT 材料主要是 programming-level concurrency，本章把这些 reasoning 迁移到 Python/threading 与 TaskForge lifecycle，并不把它当 distributed failure model 教材。

Herlihy & Wing 的 linearizability 只在这里提供 operation history 与 invocation-response 之间“看起来原子生效”的概念模型。课程不要求 formal linearizability proof、wait-free/lock-free hierarchy，也不推出“所有 workflow 都应该 linearizable”。

Google SRE 的 cascading-failure material 支撑 retry amplification、有限 attempts / retry budget、backoff 与 jitter 的 reliability reasoning；AWS retry/backoff guidance 作为补充，帮助说明 synchronized retry 会改变系统 schedule。`Barrier` / failpoint 作为 deterministic teaching evidence、TaskForge 的 effect/record failure analysis、at-most/at-least/exactly-once 的具体 boundary reasoning、cancellation/restart representation candidates、lease/fencing extension、Agent task contract 和 guarantee-selection workflow 都属于课程自己的工程综合，而不是这些来源逐字给出的流程。

因此本章不能推出：

- shared state 一律应该加 mutex；
- message passing 永远优于 locks；
- 一个 function 或 transaction 的存在就自动完成 lifecycle reasoning；
- request identity 自动带来 arbitrary external effect exactly-once；
- idempotent operation 可以无限 retry；
- stress test 跑得足够多就能证明 race-free；
- `CANCELLING`、lease、fencing 或某一种 lock layout 是 TaskForge 唯一正确 architecture。

更完整的 claim/source mapping 与 limitations 见 [M07 source audit](../reading-notes/m07-source-audit.md)。

## 14. 把前六章的 model 加上时间

M01 问 invariant 与 legal transition；M02 问 authority；M03 问 executable evidence；M04 把 timeout / retry / request identity放进 public boundary；M05 要求 change sequence 的每个 checkpoint 有窄 proof obligation；M06 在证据不足时先建立 trustworthy feedback。M07 并没有替换这些模型，而是把它们放进同一条时间轴：

```text
             invocation
                 |
          read / validate
                 |
        interleaving possible?
                 |
                 v
        atomic decision / commit
                 |
          external effects
                 |
             crash?
                 |
             response
                 |
            timeout?
                 |
              retry?
```

以后看到任何 concurrent lifecycle operation，先别问“应该用什么锁”。先问：什么 history 合法；哪些 facts 必须一起 commit；谁可能在中间行动；crash 前后留下什么；caller 在 timeout 后知道什么；recovery authority 在哪里；retry 对 effect 与 load 各造成什么。

当这些问题有了答案，primitive selection 才是 implementation design。反过来，如果只知道“加了 lock”“CI concurrency test 绿了”，我们仍然没有一个足够完整的 correctness argument。

## 可选原始资料

- MIT 6.102 — Concurrency: <https://web.mit.edu/6.102/www/sp26/classes/14-concurrency/>
- MIT 6.102 — Mutual Exclusion: <https://web.mit.edu/6.102/www/sp26/classes/16-mutual-exclusion/>
- MIT 6.102 — Message Passing & Networking: <https://web.mit.edu/6.102/www/sp26/classes/18-message-passing-networking/>
- Herlihy & Wing, *Linearizability: A Correctness Condition for Concurrent Objects*: <https://cs.brown.edu/~mph/HerlihyW90/p463-herlihy.pdf>
- Google SRE — Addressing Cascading Failures: <https://sre.google/sre-book/addressing-cascading-failures/>
- AWS — Exponential Backoff and Jitter: <https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/>
