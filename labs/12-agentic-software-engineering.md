# M12 Lab — Agentic Software Engineering：从 Prompt 到 Delegation Contract

> 本实验不是比谁更会写 prompt，也不是比 Agent 谁写代码更快。
>
> 目标是训练：**怎样把一个跨越 API、state authority、concurrency、SLO 和 review 的真实 change，组织成 Agent 可以安全推进、会在正确地方停止、并能被独立验收的工程工作系统。**

---

## 0. 你要处理的需求

M11 已经证明一个 production blind spot：

```text
12 jobs accepted
12 eventually succeeded
ending queue depth = 0
```

但：

```text
submit → first claim <= 2s
```

只有：

```text
2 / 12
```

满足。

现在产品方向是：

> 在 burst overload 时增加 admission / backpressure，让系统可以显式拒绝超过当前容量策略的 work，而不是无限接受后把等待时间推给用户。

但注意：

```text
“加 admission control”
```

远不是一份完整的软件 change specification。

---

# 1. 实验规则

整个 lab 中：

1. canonical TaskForge 只作为 baseline；
2. 真正实现请在 disposable worktree / branch / copy 中进行；
3. 不允许因为 Agent 建议而修改 M11 SLO target / denominator；
4. 不允许把 failing historical evidence 直接删掉；
5. 不允许 implementation Agent 自己决定 merge / deploy；
6. 第一轮 independent review 不允许 reviewer 直接修改 candidate；
7. 所有“完成”声明必须能指向具体 evidence；
8. **STOP_AND_ESCALATE 是合法且可能是最优的结果。**

---

# 2. Phase 0 — 恢复 baseline

在：

```bash
cd labs/taskforge
```

先运行：

```bash
PYTHONPATH=src uv run --with pytest --no-project python -m pytest -q
PYTHONPATH=src uv run --with pytest --no-project python tools/m11_production_probe.py
PYTHONPATH=src uv run --with pytest --no-project python tools/m12_orchestration_probe.py
```

你应该看到：

```text
core: 6 passed
```

以及 M11：

```text
success_ratio = 1.0
ending_queue_depth = 0
SLI = 2/12 = 0.167
```

M12 orchestration baseline 应出现四种判断：

```text
vague task           → INSUFFICIENT_CONTRACT
unsafe plan          → REJECT_PLAN
bounded plan         → STOP_AND_ESCALATE
authorized plan      → AUTHORIZED_TO_IMPLEMENT
```

如果你没有理解为什么这是四种不同状态，先不要实现 feature。

---

# 3. Phase 1 — 先看 Vague Task

打开：

```text
labs/taskforge/agent-contracts/m12/vague-task.json
```

它只有：

```text
TaskForge burst 时等待太久。
加一个 overload/backpressure 机制，把它修好，测试一下。
```

先不要看 engineered task。

独立写出：

## 3.1 你认为 Agent 必须自己猜的东西

至少回答：

- overload 是 queue depth、queue age、CPU、worker availability 还是别的？
- reject 应该发生在哪个 boundary？
- reject 是否创建 job id？
- reject 的 public semantic 是什么？
- legacy caller 是否必须兼容？
- threshold 是谁决定？
- M11 的 SLO 是否允许改变？
- concurrent submits 如何处理？
- admission policy 是否 durable？
- Agent 是否能改 tests / probes / CI？
- Agent 是否能 merge / deploy？

## 3.2 预测三种“可能全绿但不该接受”的 patch

例如：

```text
A. 把 SLO 从 99% 降成 15%
B. 把 rejected work 从 denominator 静默移除
C. 接受请求但只是不记入 metrics
```

不要只预测语法 bug。

目标是预测：

```text
semantic goal gaming
```

---

# 4. 可选实验 — 真的把 Vague Task 给一个 Coding Agent

如果你有可用 coding Agent，可以在 disposable worktree 中直接给它 vague task。

要求：

```text
不要给额外提示
不要把结果 merge
```

保存：

```text
agent plan
patch
self-summary
test output
```

这一步不是为了嘲笑 Agent。

比较的对象是：

```text
vague delegation system
vs
engineered delegation system
```

如果 Agent 恰好做对了，也不能因此证明 vague task 足够。

问：

> 它是被 contract 约束到正确答案，还是碰巧选择了一个你接受的解释？

---

# 5. Phase 2 — Read-only Reconnaissance

现在假设你是 `exploration_agent`。

**禁止修改 production source。**

至少检查：

```text
src/taskforge/public_api.py
src/taskforge/service.py
src/taskforge/state.py
src/taskforge/metrics.py
src/taskforge/worker.py
src/taskforge/production_signals.py
tools/m11_production_probe.py
tests/test_taskforge.py
```

并做 repository search：

```text
submit(
submit_job(
queued_count
state.jobs
next_job_number
production_signals
```

---

# 6. Reconnaissance Deliverable

写一份最多约两页的 brief：

```text
1. Submission path
2. Current state authority
3. Queue-depth read path
4. M11 SLI population / denominator
5. Public compatibility surface
6. Concurrency-relevant state
7. Existing evidence
8. Historical teaching paths that must not be casually “fixed”
9. Unresolved semantic questions
```

必须区分：

```text
OBSERVED
SPECIFIED
UNKNOWN
```

例如：

```text
OBSERVED:
service.submit increments next_job_number before inserting Job.

SPECIFIED by M12 candidate contract:
rejected admission must not consume an id.

UNKNOWN before human decision:
what public result shape means overload.
```

---

# 7. Phase 3 — 比较 Engineered Task

打开：

```text
agent-contracts/m12/engineered-task.json
```

对照 vague task，找出它新增的 engineering information。

至少分类：

```text
goal
non-goal
contract
scope
evidence
authority
stop condition
escalation
```

然后运行：

```bash
PYTHONPATH=src uv run --with pytest --no-project \
  python tools/m12_orchestration_probe.py
```

不要把这个 probe 理解成“自动证明 task spec 正确”。

它只证明一些**结构性要求**已经表达。

它不会判断：

```text
max_queued_jobs 到底是不是好产品策略
```

因为那不是 schema checker 能决定的。

---

# 8. Phase 4 — Review Unsafe Agent Plan

打开：

```text
agent-contracts/m12/unsafe-agent-plan.json
```

不要先跑 probe。

自己 review。

将 finding 分成：

```text
scope violation
authority violation
oracle/evidence violation
semantic goal change
production side-effect violation
```

至少指出：

- 为什么修改 `production_signals.py` 是危险的；
- 为什么“让 dashboard 变绿”不等于满足用户目标；
- 为什么删 M11 probe 是改变 evaluator；
- 为什么 merge / deploy 即使 test 绿也没有自动获得 authority。

然后再用 probe 对照：

```text
REJECT_PLAN
```

问自己：

> probe 有没有漏掉你发现的重要问题？

如果有，这正说明 policy checker 也是 M03 意义上的有限 oracle。

---

# 9. Phase 5 — Bounded Agent 应该停下来

打开：

```text
agent-contracts/m12/bounded-agent-plan.json
```

这个 plan 没有越 scope。

也没有改 SLO。

但它仍然没有 implement。

因为发现两个 unresolved decisions：

```text
1. overload public result shape
2. capacity threshold ownership
```

你要回答：

## 9.1 为什么这些不应该由 implementation Agent 自己猜？

提示：

```text
M04 public contract
M08 compatibility
M09 authority
M11 product SLO/capacity policy
```

## 9.2 为什么 STOP_AND_ESCALATE 是成功？

如果你的 KPI 只奖励：

```text
percentage of tasks autonomously completed
```

会对 Agent 产生什么激励？

---

# 10. Phase 6 — Human Decision Record

现在打开：

```text
agent-contracts/m12/human-decision.json
```

它明确决定：

```text
legacy submit_job unchanged
new opt-in submit_job_admitted
threshold caller-owned
OVERLOADED is machine-readable
reject creates no Job / consumes no id
M11 SLO unchanged
```

以及一个非常重要的 concurrency scope：

```text
admitted submit calls
must serialize
admission-check + job creation
against each other
```

但：

```text
legacy submit_job
```

明确不在这个 opt-in guarantee 中。

这避免把一次 teaching feature 偷偷扩展成全系统 admission authority redesign。

---

# 11. Authority Transfer Audit

做一张 before/after 表：

| Decision | Before human record | After record |
|---|---|---|
| 是否可以新增 opt-in public operation | ? | yes |
| overload machine code | ? | `OVERLOADED` |
| threshold owner | ? | caller/config owner |
| legacy submit semantics | preserve | preserve |
| M11 SLO | human-only | still human-only |
| merge | human-only | still human-only |
| deploy | human-only | still human-only |

关键问题：

> 为什么一次 human decision 不等于“之后所有相关问题 Agent 都可以自己决定”？

---

# 12. Phase 7 — Authorized Implementation

现在才允许进入实现。

打开：

```text
agent-contracts/m12/authorized-agent-plan.json
```

在一个 isolated worktree / branch / copy 中实现。

推荐 sequence：

```text
1. add focused tests first
2. show relevant fail-before
3. implement smallest admitted path
4. focused tests
5. core regression
6. applicable historical probes
7. self-review
8. independent review
```

---

# 13. Required Feature Contract

你的实现必须满足：

## 13.1 Legacy path unchanged

```python
submit_job(command)
```

仍保持 canonical baseline semantics。

不要偷偷把所有 callers 切到 admission control。

---

## 13.2 New opt-in path

概念接口：

```python
submit_job_admitted(command, max_queued_jobs=...)
```

精确 Python signature 可以合理选择，但必须符合 decision record。

---

## 13.3 Accepted result

machine-readable：

```json
{
  "accepted": true,
  "job_id": "job-N"
}
```

---

## 13.4 Overload result

```json
{
  "accepted": false,
  "code": "OVERLOADED"
}
```

不要要求 caller parse：

```text
"server busy, try later"
```

---

## 13.5 Rejection has zero job-state side effect

至少证明：

```text
job count unchanged
next accepted id unchanged
```

例子：

```text
accepted  → job-1
rejected  → no id
legacy/new accepted → job-2
```

不能变成：

```text
job-1
reject consumes job-2
next accepted job-3
```

---

## 13.6 Admission concurrency scope

两个 admitted submit 同时争一个 slot：

```text
at most one accepted
```

`check queued count` 和 `create job` 必须作为这个 opt-in operation 的一个 admission decision 来同步。

不要写：

```python
if queued_count() < limit:
    # race window
    submit(command)
```

却完全不分析 interleaving。

---

# 14. Threshold 的边界条件

本 lab 的 decision record 规定 threshold 由 caller/config owner 提供，不要求你发明生产默认值；同时已经把参数 domain 补成：

```text
max_queued_jobs is a non-negative integer
```

负数必须在任何 job / id side effect 之前以 `ValueError` 拒绝。

这里故意展示一个过程：bounded Agent 先把 domain 当 unresolved question 提出来，人类 decision record 再把它变成 test oracle。**不要从 reference implementation 反推 contract；contract 已经写在 authority record 中。**

---

# 15. Focused Evidence Contract

至少提供以下证据。

## 15.1 Legacy submit unchanged

已有：

```python
submit_job("...")
```

仍返回旧 shape。

---

## 15.2 Accepted admitted submit

证明：

```text
accepted=true
job exists
queued lifecycle unchanged
```

---

## 15.3 Rejected admitted submit

证明：

```text
accepted=false
code=OVERLOADED
no Job created
no id consumed
```

---

## 15.4 Concurrent admitted submissions

设计一个 evidence，使：

```text
two contenders
one available admission slot
```

不能同时获得两个 accepted results。

如果你的 test 只是：

```text
run threads 1000 times and hope race appears
```

说明为什么它的 evidence strength 有限。

优先考虑 deterministic interleaving seam 或可独立 reasoning 的 critical section。

---

## 15.5 SLO not gamed

证明：

```text
production_signals.py
M11 SLI target / denominator
```

没有因本 feature 被改写。

最简单的证据之一是：

```text
git diff
```

但 reviewer 还应该独立检查。

---

# 16. Regression Evidence

至少运行：

```bash
PYTHONPATH=src uv run --with pytest --no-project python -m pytest -q
PYTHONPATH=src uv run --with pytest --no-project python tools/m04_boundary_probe.py
PYTHONPATH=src uv run --with pytest --no-project python tools/m05_behavior_probe.py
PYTHONPATH=src uv run --with pytest --no-project python tools/m06_legacy_probe.py
PYTHONPATH=src uv run --with pytest --no-project python tools/m07_interleaving_probe.py
PYTHONPATH=src uv run --with pytest --no-project python tools/m08_compat_probe.py
PYTHONPATH=src uv run --with pytest --no-project python tools/m11_production_probe.py
```

注意：

某些历史 harness 可能和 exact source/layout 绑定。

如果 M10 review-case patch 或 M03 mutation harness 因合法结构变化失效：

不要立即把它判断为 product regression。

要先分类：

```text
product contract probe
or
version-scoped teaching artifact
```

然后记录理由。

---

# 17. Implementation Agent Evidence Packet

Agent 最终必须交：

```text
Base commit
Task contract version
Human decision id
Changed files
Claim → evidence table
Commands actually run
Observed results
Known limitations
Open risks
Historical probes that became inapplicable + why
```

禁止只写：

```text
“All tests passed and the implementation is robust.”
```

---

# 18. Self-review

Implementation Agent 在交给 reviewer 前，应自己检查：

- 是否越 write scope？
- 是否改了 SLO/evaluator？
- 是否新增第二 state authority？
- check + create 是否真在同一个 admission critical section？
- reject 是否消耗 id？
- default path 是否偷改？
- test 是否只是 mirror implementation？
- 是否有 unrelated cleanup？

Self-review 是有价值的。

但不能结束于 self-review。

---

# 19. Phase 8 — Independent Reviewer

启动独立 reviewer。

第一轮只给：

```text
base commit
task contract
human decision record
candidate diff
raw evidence / commands
```

**不要先给 implementation Agent 的结论性 summary。**

让 reviewer 独立回答：

```text
1. What is the actual behavior change?
2. Which old behavior is promised unchanged?
3. Where is admission authority?
4. Is check+create atomic for the promised scope?
5. Can rejection consume state/id?
6. Did candidate alter acceptance evidence?
7. What compatibility surface changed?
8. Which tests actually distinguish plausible wrong implementations?
9. What remains deliberately out of scope?
10. Merge / do not merge / needs decision?
```

---

# 20. Reviewer 必须主动找 Counterexample

至少设计三个：

```text
A. queue already at limit
B. two concurrent admitted submits for one slot
C. rejection followed by next accepted submit
```

再加一个你自己发现的边界。

例如：

```text
worker claims between observation and submission
limit=0
legacy submit bypasses admitted policy
```

但每个 counterexample 都必须对照 **promised scope**。

不要把故意 out-of-scope 的行为错报成 blocker。

---

# 21. Review Findings 格式

重要 finding 至少包括：

```text
Severity
Observation
Violated contract / authority
Concrete consequence
Evidence / reproducer
Required outcome
```

例如：

```text
Blocker — admission check and submit are separate critical sections

Two concurrent submit_job_admitted calls can both observe queued_count=0
under max_queued_jobs=1, then both create a job. This violates the human
record that admitted submissions serialize admission-check + creation.

Required outcome: make the decision atomic for admitted submissions and
add deterministic concurrency evidence.
```

---

# 22. Phase 9 — Human Adjudication

Reviewer 的 finding 也不是自动 truth。

Human / repository authority 需要判断：

- finding 是否真实；
- 是否在 task scope；
- 是 blocker 还是 follow-up；
- 是否需要修改 contract；
- 是否需要再授权 Agent；
- residual risk 是否可接受。

如果 reviewer 发现：

```text
legacy submit can bypass admission
```

但 human decision 已明确说：

```text
legacy submit intentionally bypasses opt-in policy
```

这不是本 PR blocker。

它可以是 future architecture concern。

---

# 23. Phase 10 — 两个 Agent 的正确并行方式

可选扩展。

不要让两个 Agent 同时修改 `service.py`。

先试：

```text
Agent A: contract / API compatibility review
Agent B: concurrency / interleaving review
Agent C: evidence / test-oracle review
```

三个都 read-only。

最后比较：

- findings 是否重叠；
- 是否出现 conflict；
- synthesis 成本；
- 哪些问题只被一个 Agent 发现；
- 总 token/tool 成本是否值得。

然后再尝试两个 write-heavy agents，观察 coordination cost。

不要预设 multi-agent 一定更优。

---

# 24. Phase 11 — Authority Ladder Exercise

为下面动作分类：

```text
AUTO
AGENT WITH POLICY
HUMAN APPROVAL
HUMAN ONLY / NOT DELEGATED
```

动作：

1. read source；
2. run pytest；
3. create worktree；
4. edit allowed files；
5. add regression test；
6. push feature branch；
7. edit SLO；
8. modify migration compatibility window；
9. merge PR；
10. deploy 5% canary；
11. promote 100%；
12. rotate credentials；
13. delete durable state。

每个答案必须说明：

```text
reversibility
blast radius
evidence strength
policy maturity
```

不能只写“AI 不安全”。

---

# 25. Phase 12 — 把 Prompt Rule 编译成工程机制

下面这些 rule 应长期放在哪里？

```text
“不要直接写 state.jobs”
“storage schema field number 不得复用”
“所有 release 要跑 release matrix”
“M11 SLO denominator 是 accepted jobs”
“本次 task 不改 dashboard”
```

从这些选择：

```text
task prompt / task contract
repo docs / scoped AGENTS
unit/integration test
architecture fitness test
CI/policy-as-code
ADR
runtime guard
```

目标：

> 不要把所有工程知识都永远留在自然语言 prompt。

---

# 26. Phase 13 — Harness Simplification Exercise

假设半年后新模型已经稳定做到：

```text
always runs core tests
always reports changed files
```

你的 harness 里仍有 30 行 instruction 强调这两件事。

设计一个实验：

```text
remove one harness mechanism
→ compare failure/rework evidence
```

回答：

- 什么证据允许删？
- 失败后怎么 rollback harness change？
- 怎样避免“某次成功”被误判成稳定能力？

这就是把 M05 用在 Agent harness 本身。

---

# 27. Phase 14 — Productivity Measurement

不要回答：

```text
“用了 Agent 感觉快很多。”
```

为这个 lab 设计至少 5 个 measurement：

例如：

```text
time to first correct system model
time to mergeable patch
review findings / blocker count
rework rounds
scope violations
correct escalations
commands/tests automatically completed
human decision time
```

说明每个 metric 可能被怎样 game。

---

# 28. Deliverables

提交：

## A. Reconnaissance Brief

包含 system model / unknowns。

## B. Vague vs Engineered Task Analysis

不要评价“哪个 prompt 更详细”。

评价：

```text
which decision space became bounded?
```

## C. Authority Matrix

至少四类 role。

## D. Stop/Escalation Analysis

解释为什么 bounded plan 不应实现。

## E. Candidate Implementation

仅在 human decision 后。

## F. Evidence Packet

claim-oriented。

## G. Independent Review

包含 severity + reproducer。

## H. Human Adjudication

决定哪些 finding 阻塞、哪些 follow-up。

## I. Retrospective

回答：

```text
哪些工作 Agent 做得比你机械手工更好？
哪些判断如果交给 Agent 自己决定会变成 authority drift？
哪些规则应该下一次被编译成 executable mechanism？
```

---

# 29. 评分

| 维度 | 分值 |
|---|---:|
| System model / reconnaissance | 15 |
| Delegation contract quality | 20 |
| Authority / escalation judgment | 20 |
| Implementation discipline | 10 |
| Evidence quality | 15 |
| Independent review | 15 |
| Retrospective / harness evolution | 5 |

---

# 30. 不按这些东西给高分

不会因为下面任何单项自动高分：

```text
prompt 很长
用了 5 个 Agent
用了最贵模型
Agent 一次写对
全部 tests 绿
生成很多代码
完全没有人工介入
```

真正高分来自：

> **你能让 Agent 在清晰 authority 内快速工作，在语义不足时正确停止，用高质量 evidence 支撑 claim，并让另一个独立 reasoning path 有能力推翻它。**

---

# 31. Lab 结束时必须能回答

如果一个 Agent 说：

```text
“I completed the task, all tests pass, and the system is ready to deploy.”
```

你应该立刻追问：

```text
Completed against which contract?
Which decisions were delegated?
Which tests distinguish what wrong implementation?
Did the candidate change its own evaluator?
Who independently reviewed it?
What remained out of scope?
Who has deployment authority?
What production evidence would confirm the rollout?
```

如果这些问题已经由你的 workflow 自动产生答案，才说明你真正开始掌握 Agentic Software Engineering。
