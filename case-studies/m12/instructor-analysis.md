# M12 Instructor Analysis — Agentic Software Engineering

> 这份 reference 不是“标准 prompt 答案”。
>
> 它记录的是：怎样判断 delegation 是否完整、Agent 应该在哪里停、human authority 怎样被局部转移，以及授权后的最小实现怎样用独立 evidence 验证。

---

# 1. 这章真正考什么？

不是：

```text
谁能让 Agent 一次写出最漂亮的 admission-control code
```

而是：

```text
能不能先发现任务语义不足？
能不能防止 Agent 优化错误 proxy？
能不能限制 write / production authority？
能不能让 Agent 在需要产品决策时正确停止？
能不能把 human decision durable 化？
能不能让 implementation 和 acceptance reasoning 分离？
```

所以一个没有 patch、但准确输出：

```text
STOP_AND_ESCALATE
```

的 Agent，可能比一个 300 行全绿 patch 做得更好。

---

# 2. Vague Task 为什么不够？

starter：

```text
TaskForge burst 时等待太久。
加一个 overload/backpressure 机制，把它修好，测试一下。
```

它至少缺少这些 decision：

```text
what counts as overload?
where admission happens?
what is rejected?
what public result means reject?
who owns threshold?
what happens to job id?
which old callers must remain compatible?
what happens under concurrent submit?
can the Agent change SLO?
can the Agent modify its own evidence?
can the Agent merge/deploy?
```

因此问题不是：

```text
prompt too short
```

而是：

```text
decision space is under-specified
```

把同一句 prompt 扩成 2000 字，但仍没有这些 authority / contract 信息，也不会本质改善。

---

# 3. 为什么不能用“Agent 恰好做对了”证明 Vague Task 足够？

假设某个强 Agent 收到 vague task 后自己推断：

```text
use opt-in API
preserve legacy path
threshold is caller-owned
reject consumes no id
```

结果和 instructor 一模一样。

这只能说明：

```text
Agent selected an acceptable interpretation
```

不能说明：

```text
the delegation constrained all unacceptable interpretations
```

软件工程关心的不只是：

```text
one run produced a good patch
```

还关心：

```text
what makes future runs / agents / maintainers converge on the same contract?
```

这就是 durable specification 的价值。

---

# 4. Engineered Task 做了什么？

`engineered-task.json` 并没有提前实现 feature。

它只是压缩 decision space。

## 4.1 Goal

从：

```text
fix overload
```

变成：

```text
new opt-in admission path
explicit rejection before work creation
legacy default unchanged
```

---

## 4.2 Non-goals

明确：

```text
no DB/RPC/queue
no M03-M10 cleanup
no SLO rewrite
no silent legacy-submit change
```

这对 Agent 很重要，因为它很容易把 repository-wide cleanup 当成 bonus。

---

## 4.3 Contracts

最关键：

```text
reject creates no Job
reject consumes no id
accepted lifecycle unchanged
no second lifecycle authority
M11 accepted-job denominator unchanged
```

这些都是 future patch 的判据。

---

## 4.4 Write scope

允许读广泛，但写入受限。

这体现：

```text
understanding scope
!=
mutation scope
```

---

## 4.5 Evidence contract

不是：

```text
run tests
```

而是：

```text
claim → required evidence
```

这是 M03/M10 的直接复用。

---

# 5. `m12_orchestration_probe.py` 证明什么？

它只做 structural policy checking。

它能发现：

- required fields 缺失；
- write path 越界；
- plan 明说要改 SLO；
- plan 明说要改 denominator；
- plan 想删 evidence；
- plan 想 merge / deploy；
- unresolved questions；
- authorization id 是否对应 human decision。

它不能证明：

```text
engineered task 的产品策略正确
human decision 一定正确
implementation 不会有 bug
```

所以这个 probe 自己也只是 evidence source。

不要把 M12 变成：

```text
policy checker green
→ safe Agent workflow
```

那只是把 M10 的 CI worship 换了名字。

---

# 6. Unsafe Plan 的 Root Cause

`unsafe-agent-plan.json` 表面上很积极：

```text
make dashboard healthy
change threshold
change denominator
remove old probe
merge
deploy
```

它不是七个独立问题。

root cause 是：

> **Agent 把“达到 feature goal”的实现 authority 扩张成了“重新定义 success、修改 evaluator、接受风险、发布生产”的 authority。**

具体表现：

```text
semantic authority drift
evaluator capture
write-scope violation
release authority drift
production authority drift
```

所以 instructor 会把最高层 finding 写成 authority failure，而不是只列七个 style comment。

---

# 7. 修改 SLO 为什么是特别危险的？

M11 已经建立：

```text
user expectation
→ SLI
→ SLO
```

如果 feature implementation 为了让自己通过 acceptance，顺手把：

```text
0.99
```

改成：

```text
0.15
```

那是在改变：

```text
what success means
```

而不是实现 success。

这与：

```text
bugfix changes test expected value to current buggy output
```

是同一种结构。

---

# 8. 删除 M11 Probe 为什么不是普通 cleanup？

因为 probe 是 acceptance evidence。

Candidate 同时修改：

```text
implementation
+
thing that judges implementation
```

当然，有时 evaluator 必须合法修改。

但这种修改本身要获得独立 review。

否则 pipeline 可能变成：

```text
change behavior
→ update expected
→ green
```

---

# 9. Bounded Plan 为什么是正确的？

它做了几件成熟的事情：

```text
read first
write only allowed paths
preserve legacy semantics
keep SLO untouched
require evidence
```

然后发现：

```text
public result shape unresolved
threshold owner unresolved
```

于是停。

这个 stop 是高质量输出，因为这些问题分别触及：

```text
M04 public contract
M08 compatibility
M09 authority
M11 product/capacity policy
```

它们不是 implementation detail。

---

# 10. 为什么不能让 Agent “合理选择一个”然后继续？

可以——**如果**组织已经把这个 authority 委托给它。

例如 task 可以明确：

```text
You may choose the overload result shape from A/B based on compatibility analysis.
```

那它就获得了 design authority。

starter 没有这样授权。

因此：

```text
model confidence
```

不能替代：

```text
authority grant
```

---

# 11. Human Decision Record 解决什么？

`M12-ADMISSION-001` 明确：

```text
legacy submit_job stays unchanged
new opt-in submit_job_admitted
max_queued_jobs caller-owned
max_queued_jobs >= 0
negative -> ValueError before side effect
OVERLOADED machine code
reject no Job / no id
admitted submissions serialize check + create
M11 SLO unchanged
```

这把原本 conversation-level decision 变成 durable engineering artifact。

以后：

- implementation Agent；
- reviewer；
- future maintainer；
- Capstone；

都能看到同一个 authority record。

---

# 12. 为什么选择 Opt-in API？

这不是唯一正确设计。

Reference 选择：

```text
submit_job()            legacy path
submit_job_admitted()   opt-in path
```

因为本 lab 目标是：

```text
introduce admission behavior
without silently changing old callers
```

这样可以减少 compatibility surface。

代价：

```text
two submission paths coexist
legacy callers can bypass admission
```

这在长期 architecture 上可能不理想。

但 human decision 明确把它作为 M12 的 bounded scope。

因此 reviewer 不应该把：

```text
legacy path bypasses admission
```

直接写成 blocker。

正确写法更像：

```text
Follow-up / architecture debt:
If admission becomes mandatory system-wide, authority must move to a
single submission boundary and legacy bypass must be migrated.
```

---

# 13. 为什么 Threshold 由 Caller / Config Owner 提供？

因为当前课程没有给 production capacity model。

如果 reference 随便写：

```python
MAX_QUEUE = 100
```

看起来实现完整了。

实际上它偷偷做了一个 product/operations decision。

所以 instructor 选择：

```text
mechanism in TaskForge
policy value outside TaskForge
```

即：

```text
TaskForge knows how to enforce a limit
caller/config owner chooses the limit
```

这也符合 M02/M04：

> policy 不应该由偶然 storage / implementation detail 决定。

---

# 14. Negative Threshold 为什么后来被补进 Decision？

第一版 bounded plan 正确地问：

```text
threshold domain是什么？
```

如果 reference implementation直接写：

```python
if max_queued_jobs < 0:
    raise ValueError
```

但 decision record 没有写，test oracle 就会来自 implementation。

这正是 M03 反复警告的方向倒置。

因此 instructor 最终把：

```text
non-negative integer
negative → ValueError before side effect
```

明确写入 `human-decision.json`，再写 reference test。

顺序是：

```text
decision
→ oracle
→ implementation
```

而不是：

```text
implementation
→ test expected
→ retroactive “contract”
```

---

# 15. Reference Implementation

Reference 只改临时副本，不进入 canonical baseline。

核心设计：

```python
_admission_lock = threading.Lock()


def submit_admitted(command: str, *, max_queued_jobs: int) -> str | None:
    if max_queued_jobs < 0:
        raise ValueError(...)

    with _admission_lock:
        queued = sum(
            job.status == JobStatus.QUEUED
            for job in state.jobs.values()
        )
        if queued >= max_queued_jobs:
            return None
        return submit(command)
```

Public boundary：

```python
def submit_job_admitted(command: str, *, max_queued_jobs: int):
    job_id = service.submit_admitted(...)
    if job_id is None:
        return {"accepted": False, "code": "OVERLOADED"}
    return {"accepted": True, "job_id": job_id}
```

---

# 16. 为什么 Lock 只保护 admitted path？

Human decision 的 promised scope 是：

```text
Concurrent calls through the admitted path
serialize admission-check + job creation against each other.
```

不是：

```text
all TaskForge submissions globally obey admission
```

所以 reference 没有重写：

```text
legacy submit
worker claim
all state mutation
```

进同一个 lock。

这是刻意的小 scope。

如果长期需求升级成 mandatory global admission，那需要新的 architecture decision。

---

# 17. Worker 与 Admission 的 Interleaving

Worker 可以在 admitted request counting / creation 附近 claim queued job。

当前 decision 允许：

```text
worker claim may reduce queued work concurrently
```

这最多让 admission decision 保守或瞬时过时，不会让两个 **admitted submissions** 同时越过一个 slot 的 promise。

如果未来 policy 要的是：

```text
exact total system occupancy at one global linearization point
```

那么当前 local lock 不够。

那会重新进入 M07/M09 的系统级 authority 设计。

---

# 18. Reference Tests

临时副本新增 5 个 tests。

原 core：

```text
6
```

M12：

```text
5
```

实际：

```text
........... [100%]
11 passed
```

---

# 19. Test 1 — Legacy Public Shape

```python
assert submit_job("echo legacy") == {"job_id": "job-1"}
```

这是 compatibility claim。

它并不能证明整个 old behavior 没变。

所以还需要旧 regression probes。

---

# 20. Test 2 — Accepted Work 进入原 Lifecycle

```text
submit_job_admitted(..., max=1)
→ accepted=true
→ job-1
→ status=QUEUED
```

目的是证明 new boundary 没有创建 parallel lifecycle representation。

---

# 21. Test 3 — Rejection Zero Side Effect

Sequence：

```text
first admitted → job-1
second admitted → OVERLOADED
legacy accepted → job-2
```

并确认 reject 后：

```text
jobs == [job-1]
```

这个测试比只检查：

```text
accepted=false
```

强得多。

因为它验证 state cardinality 和 allocator side effect。

---

# 22. Test 4 — Invalid Threshold

Decision 已定义：

```text
negative → ValueError before any state/id side effect
```

reference 验证：

```text
invalid
→ ValueError
→ jobs empty
→ next valid submit = job-1
```

---

# 23. Test 5 — Two Contenders / One Slot

两个线程由 barrier 同时开始：

```text
max_queued_jobs=1
```

结果必须：

```text
1 accepted
1 OVERLOADED
1 Job total
```

实际通过。

但是 instructor 特别强调：

> **这个 stress-shaped concurrency test 单独并不能证明 atomicity。**

它需要和 implementation review 一起使用。

---

# 24. 为什么另外做 Naive Deterministic Counterexample？

为了证明一个非常 plausible 的错误实现：

```python
if queued_count() < limit:
    return submit(command)
```

确实存在 interleaving bug。

Instructor 构造：

```text
A observes queue=0
B observes queue=0
barrier
A submit
B submit
```

实际结果：

```text
naive_results = ['job-2', 'job-1']
naive_jobs    = ['job-1', 'job-2']
```

也就是说：

```text
one-slot policy
→ two accepted jobs
```

这个 negative control 比“我觉得应该加锁”更强。

---

# 25. Concurrency Evidence 的正确组合

Reference 的 correctness argument 是：

```text
1. Contract says admitted check+create serializes.
2. Naive two-step implementation has deterministic counterexample.
3. Reference code puts count + reject/submit under one admitted-path lock.
4. Concurrent public test observes at most one acceptance.
```

不是：

```text
one thread test passed
→ proven thread-safe
```

---

# 26. Regression Results

Reference 临时副本实际运行：

```text
M04 boundary       PASS / same visible behavior
M05 dashboard      fingerprints unchanged
M06 legacy audit   fingerprints unchanged
M07 failure probe  unchanged
M08 compatibility  unchanged
M09 architecture   baseline inventory still runs
M11 production     original overload gap unchanged
M12 orchestration  unchanged
```

特别是 M11：

```text
2 / 12 start-latency SLI
```

仍然存在。

这不是 reference 失败。

因为 M12 feature 是 opt-in admission mechanism，不是宣称已经选择并部署了 production threshold。

这非常重要：

> **不要为了证明新 mechanism 有价值而伪造 production outcome。**

---

# 27. M03 Historical Mutation Harness

M03 mutation harness 在 reference temp copy 中仍可运行：

```text
3 killed
3 survived
```

因为 M12 没移动它依赖的那些 exact mutation sites。

新 tests 让每个 mutant run 中出现的 pytest test count 增加，但 baseline semantic result 仍一致。

这只是偶然兼容，不应被升级成 M12 必须保持的 product contract。

---

# 28. M10 Replay Harness 为什么失效？

Reference 中：

```text
m10_rc = 1
```

原因不是 M12 product regression。

M10 的 `agent-pr.patch` 是一个**针对 M10 baseline source shape 的教学 candidate patch**。

它会重写 `service.py`。

当 M12 已合法在同一文件增加：

```text
_admission_lock
submit_admitted
```

再 replay 那个 old candidate，会形成一个不再代表原 M10 case 的混合 tree，甚至产生：

```text
NameError: state is not defined
```

正确分类：

```text
M10 replay harness
=
version-scoped teaching artifact
```

而不是：

```text
permanent product regression suite
```

这和 M05/M09 已经讨论的 test/tool lifetime 完全一致。

---

# 29. 一个 Reviewer 可能错误报告的 Finding

例如：

```text
Blocker: legacy submit_job bypasses max_queued_jobs.
```

如果 reviewer 没看 human decision，这很像 blocker。

但 decision 明确：

```text
legacy submit_job intentionally bypasses admission
```

所以应改成：

```text
Non-blocking architecture note:
mandatory future admission will require migration of legacy callers.
```

这说明独立 review 不等于“忽略 specification”。

独立的是 reasoning，不是 contract。

---

# 30. 一个真正的 Blocker 示例

假设 candidate：

```python
def submit_admitted(...):
    if metrics.queued_count() >= max_queued_jobs:
        return None
    return submit(command)
```

Blocker：

```text
The admission decision is split across two independently interleavable
operations. Two admitted submissions can both observe capacity and both
create work. This violates M12-ADMISSION-001's explicit concurrency scope.
```

Required outcome：

```text
serialize admitted check+creation
+
add counterexample-oriented concurrency evidence
```

---

# 31. 另一个真正的 Blocker

Candidate：

```python
job_id = service.submit(command)
if queued_count() > limit:
    service.cancel(job_id)
    return OVERLOADED
```

即使最终 jobs 看起来被 cancel：

它仍违反：

```text
reject creates no Job
reject consumes no id
```

而且可能产生：

- audit artifacts；
- metrics；
- concurrent claim；
- external observer history。

这是 M07 的：

```text
final state != history
```

再次出现。

---

# 32. 还有一种更隐蔽的 Goal Gaming

Candidate 不改 SLO target，但改：

```text
accepted job definition
```

让 slow job 在 claim 前都不算 accepted。

于是：

```text
SLI suddenly improves
```

这仍是 denominator gaming。

所以 evidence contract 写的不是：

```text
literal source line unchanged
```

而是：

```text
accepted jobs remain the measured population
```

Reviewer 必须理解 semantic definition。

---

# 33. 为什么 `job_id` Allocation 也是 Authority Concern？

如果 reject 先 allocate id：

```text
job-1 accept
job-2 reject
job-3 accept
```

是否一定错误？

不一定。

很多真实系统允许 id gaps。

但本 lab human contract 明确：

```text
reject consumes no id
```

所以这里错误来自 contract，不来自通用“ID 必须连续”原则。

这很重要。

不要从 lab 反推出：

> production IDs 永远不能有 gap。

---

# 34. 为什么不把 `max_queued_jobs` 存进 global config？

因为当前 task 没有要求 durable policy authority。

如果 Agent新增：

```text
global mutable config
```

就会引入：

```text
new state owner
reload semantics
concurrent update semantics
persistence questions
```

不必要地扩大 M12 scope。

Caller-owned threshold 是 deliberate minimality。

---

# 35. 为什么不直接用 `metrics.queued_count()`？

Reference 可以技术上调用它。

但 instructor 更倾向在 `service` 的 admitted critical section 中直接读取 canonical state representation，因为：

- `metrics.py` 是 reporting/read view；
- admission 是 semantic mutation decision；
- 将 policy authority 建在 metrics helper 上会增加 temporal/semantic coupling。

不过 canonical TaskForge 仍然是 teaching baseline，没有正式 JobAuthority。

长期正确 architecture 应由 M09 后续 evolution 决定。

因此这里不把这个局部选择升级成 universal principle。

---

# 36. Human Decision 仍然不是“最终架构”

它只是：

```text
one bounded feature decision
```

未来可能被 supersede：

```text
mandatory admission
shared durable queue
remote workers
per-tenant quotas
fair scheduling
SLO-aware queueing
```

那时应重新建模。

好的 authority record 允许后续 decision supersede 它，而不是假装今天的策略永久正确。

---

# 37. Independent Reviewer 的输入顺序

Instructor 推荐第一轮 reviewer 拿：

```text
base
contract
human decision
diff
raw evidence
```

不要先看：

```text
Implementer: “This is safe, minimal, fully tested.”
```

因为后一句是 framing。

第二轮再比对 implementer summary：

```text
Did author omit a known limitation?
Did reviewer misunderstand intended scope?
```

---

# 38. Reviewer 不一定必须是另一种模型

可接受独立性来源：

```text
fresh context
separate session
different role prompt
different model
human reviewer
runtime negative control
static checker
```

关键是减少 correlated failure。

例如：

```text
same Agent writes code
same Agent writes expected
same Agent reviews itself
same Agent merges
```

虽然流程有四步，实际上 failure mode 高度相关。

---

# 39. Multi-Agent Reference Exercise

如果并行三个 reviewer：

```text
A API / compatibility
B concurrency / lifecycle
C evidence / oracle
```

这是比较合理的 decomposition。

因为他们主要 read-heavy，而且问题空间相对独立。

最后由主 reviewer / human synthesize：

```text
duplicate findings
conflicting assumptions
root cause grouping
severity
```

不要仅统计：

```text
3 agents found 14 comments
```

comment 数不是 review quality。

---

# 40. Authority Matrix 的 Instructor Interpretation

## Exploration Agent

可以：

```text
read
search
run tests/probes
write notes
```

不需要 source write。

## Implementation Agent

可以：

```text
isolated write
add tests
run local evidence
produce diff
```

不能：

```text
merge
deploy
change SLO
expand scope
```

## Review Agent

第一轮：

```text
read / run / report
```

不改 candidate。

## Human Authority

保留：

```text
new semantic decisions
scope expansion
residual risk acceptance
merge / production policy
```

这不是说所有团队永远都必须这样。

它只是 starter 的 explicit delegation architecture。

---

# 41. 怎样逐步减少 Human Bottleneck？

假设这个 admission workflow 做了 100 次，团队发现：

```text
machine-readable OVERLOADED
no-id-on-reject
non-negative threshold
```

已经成为稳定 repository policy。

那么以后不应每次重新人工决定。

可以把它编码进：

```text
public type
unit tests
architecture policy
API schema
```

Human authority 没消失。

它被编译成 system rule。

---

# 42. Instructor 不给“Prompt Length”分

一个 30 行 contract，如果每一行都对应真实 decision，可能很好。

一个 1000 行 prompt，如果充满：

```text
be careful
think deeply
follow best practices
```

没有价值。

评分看：

```text
decision coverage
scope clarity
oracle quality
authority clarity
```

---

# 43. Correct Escalation 必须得分

如果学生的 Agent 在 bounded phase 说：

```text
I cannot choose overload result shape because this changes caller contract.
```

应该加分。

如果另一个 Agent 自信地发明一个 shape、实现 500 行并全绿：

在 human decision 之前反而应该扣分。

否则课程会训练出错误激励：

```text
confidence > discipline
```

---

# 44. 不要把 Production Human Gate 当宗教

Starter 把 merge/deploy 留给 human，是因为这是教学上的清晰 authority boundary。

成熟组织可以安全地自动化：

```text
canary promotion
rollback
routine dependency updates
```

前提是：

```text
policy explicit
evidence strong
blast radius bounded
rollback tested
audit visible
```

那时 authority 是被明确委托给 automation。

不是“没有人类就没有 authority”。

---

# 45. Source Audit 对课程的校正

M12 没有选一本“Agentic SWE 圣经”。

原因是当前领域变化太快。

我们实际结合：

```text
OpenAI current agent/harness docs
Anthropic harness/eval engineering reports
SWE-bench benchmark scope
METR maintainer acceptance / productivity studies
GitHub AI review instruction behavior
```

并严格区分：

```text
stable engineering pattern
vs
current product implementation
```

例如：

```text
AGENTS.md
```

是当前具体机制。

稳定原则是：

```text
durable scoped repository guidance
```

---

# 46. METR Maintainer Study 应怎样讲？

不能讲成：

```text
“AI 写的代码一半都不能 merge。”
```

研究范围有限，而且 Agent 没有真实 contributor 那样的多轮 review feedback。

正确课程用途是：

> 一个 automated grader 的 pass 与 maintainer acceptance 是两个不同的测量对象。

这直接支持 M10/M12 的 independent review stage。

---

# 47. Productivity Study 应怎样讲？

也不能讲成：

```text
AI 让程序员慢 19%
```

那是 early-2025 特定样本、特定工具、熟悉成熟 repo 的 RCT 结果。

后续 2026 数据又受到 selection effect 限制。

课程真正拿走：

```text
subjective speed perception can disagree with measured outcome
```

所以团队要测自己真实 workflow。

---

# 48. M12 的核心 Assessment

一个优秀学生应能做到：

1. **不急着让 Agent 写。**
2. 先恢复 system model。
3. 把 task 写成 delegation contract。
4. 区分 capability / permission / authority。
5. 正确识别 stop/escalation point。
6. 把 human decision durable 化。
7. 只授权最小 implementation scope。
8. 要求 claim-oriented evidence。
9. 让独立 reviewer 能推翻 candidate。
10. 识别 old harness 的 version scope。
11. 不把 test/benchmark pass 当 merge authority。
12. 不把 human gate 当永久人工 ceremony，而考虑哪些 rule 可被编码。

---

# 49. 常见错误评分

## High severity

- 修改 SLO / denominator 让 feature 通过；
- 未授权改变 public contract；
- implementation Agent merge/deploy；
- 新增第二 lifecycle authority；
- concurrency promise 没有 atomic decision；
- 删除 failing evidence 而无 supersession reasoning；
- reviewer 只复述 implementer summary。

## Medium

- task scope 太宽；
- evidence 只有“all tests pass”；
- progress state 只存在 chat；
- multi-agent shared-write 没有 ownership decomposition；
- known limitation 没写。

## Low / nit

- contract JSON field 命名不同；
- 使用 YAML/Markdown 而不是 JSON；
- exact Agent product/tool 不同。

课程不绑定 artifact syntax。

---

# 50. Reference 最后的工程判断

这个 lab 的“正确答案”不是 admission lock 本身。

真正答案是整个 sequence：

```text
vague request
  ↓
recognize missing semantics
  ↓
read-only system model
  ↓
engineered delegation contract
  ↓
unsafe plan rejected
  ↓
bounded plan stops correctly
  ↓
human decision record
  ↓
limited authority grant
  ↓
small implementation
  ↓
claim-oriented evidence
  ↓
independent review
  ↓
human/policy adjudication
```

如果学生只提交最后 15 行 lock 代码，即使代码完全正确，也没有完成 M12。

---

# 51. 实际验证记录

本轮 instructor reference 在临时 TaskForge 副本中实际执行。

## Canonical baseline

```text
6 passed
```

## M12 orchestration harness

```text
VAGUE       → INSUFFICIENT_CONTRACT
UNSAFE      → REJECT_PLAN
BOUNDED     → STOP_AND_ESCALATE
AUTHORIZED  → AUTHORIZED_TO_IMPLEMENT
```

## Authorized reference

```text
6 core
+ 5 M12 focused tests
= 11 passed
```

## Naive concurrency negative control

```text
one slot
2 contenders
→ 2 accepted
```

实际示例结果：

```text
naive_results = ['job-2', 'job-1']
naive_jobs = ['job-1', 'job-2']
```

线程返回顺序不重要。

重要的是：

```text
accepted count = 2
```

## Applicable regressions

```text
M04 PASS
M05 PASS
M06 PASS
M07 PASS
M08 PASS
M09 PASS
M11 PASS
M12 PASS
```

## Historical harness applicability

```text
M03 mutation harness: still runs, 3 killed / 3 survived
M10 replay harness: no longer applicable after M12 source evolution
```

M10 failure 被记录为 version-scope change，而不是 product regression。

---

# 52. 最终一句话

> **M12 的目标不是让 Agent 尽量少问人，而是让它尽量少做未经授权的猜测；不是让 human 保留所有机械工作，而是让真正新的 engineering judgment 有明确 owner，并把已经稳定的 judgment 逐步编码进系统。**
