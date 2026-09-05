# Lab 11 — Production、Observability 与 Reliability

> 目标：让一个“测试全绿、所有 job 最终成功”的 TaskForge workload 暴露 production blind spot，并设计一套用户中心、成本可控、可 review 的 production evidence。

---

# 0. 规则

本实验不是“给 TaskForge 接 Prometheus”。

你可以完全不安装任何 telemetry SDK。

本实验只关心：

```text
user expectation
→ SLI specification
→ measurement implementation
→ telemetry model
→ SLO / alert / action
```

硬性要求：

1. 不把现有 dashboard 当 specification；
2. 不以“所有 tests green”作为 production health 结论；
3. 不把 `job_id` / `request_id` 作为 aggregate metric label；
4. 不记录 command / token / arbitrary user content；
5. 每个 page-level alert 必须写 operator action contract；
6. 必须说明 measurement blind spots；
7. 必须区分 symptom 与 cause；
8. Agent 写 instrumentation 后必须独立 review。

---

# 1. Baseline

进入：

```bash
cd labs/taskforge
```

先跑原 core tests：

```bash
PYTHONPATH=src uv run --with pytest --no-project python -m pytest -q
```

然后运行 production probe：

```bash
PYTHONPATH=src uv run --with pytest --no-project \
  python tools/m11_production_probe.py
```

你应看到类似：

```text
[NAIVE DASHBOARD]
submitted=12
success_ratio=1.0
ending_queue_depth=0
healthy=true
```

但：

```text
[USER-CENTERED START-LATENCY SLI]
good=2
bad=10
total=12
sli=0.167
target=0.990
```

以及：

```text
12 completed jobs
→ 12 metric series
```

因为 starter 把 `job_id` 当 metric label。

---

# 2. 不要先改代码：先写 Production Contract

回答：

## 2.1 User Journey

TaskForge 的这个实验里，你认为用户真正关心的 critical journey 是什么？

至少写：

```text
submit accepted
→ authoritative job exists
→ worker starts job in reasonable time
→ job eventually completes / fails explicitly
```

---

## 2.2 SLI Specification

本实验给出的目标 specification：

```text
accepted job 的 first authoritative claim
是否在 accepted submission 后 2.0 秒内发生？
```

但你必须补全：

- Total event 是什么？
- Good event 是什么？
- Bad event 是什么？
- Unknown 是什么？
- cancel-before-claim 怎么处理？
- observation window 结束仍未 claim 怎么处理？
- duplicate submit / retry 在什么 identity 下去重？

不要只写：

```text
p99 < 2s
```

---

# 3. 解释 Naive Dashboard 为什么会撒谎

不是说它的数据错。

而是说明它回答的是不同问题。

填写：

| Signal | 它准确回答什么 | 它回答不了什么 |
|---|---|---|
| eventual success ratio | ? | ? |
| ending queue depth | ? | ? |
| terminal count | ? | ? |

必须明确写出：

```text
final state
!=
history experienced by users
```

---

# 4. Measurement Placement

至少设计三种测法：

## A. Service / Worker Event Pair

```text
submit accepted event
claim event
```

优点？

Blind spot？

---

## B. Client-observed Status Transition

client poll `QUEUED → RUNNING`。

优点？

Blind spot？

---

## C. Synthetic End-to-End Job

定期提交特殊 job。

优点？

Blind spot？

---

最后选择一个 primary SLI implementation，并解释为什么。

---

# 5. Denominator Review

考虑以下错误实现：

```text
SLI = fast_claimed_jobs / all_claimed_jobs
```

为什么危险？

提示：

```text
一个永远没被 claim 的 job
是否进入 denominator？
```

请写出一个更符合 specification 的 denominator。

---

# 6. Missing Event Semantics

考虑：

```text
submitted event 有
claimed event 没有
```

可能原因：

```text
job 还在等
worker 挂了
telemetry 丢了
窗口结束
事件迟到
```

你不能简单：

```text
ignore
```

定义一个显式 policy。

例如：

```text
measurement window closed 且 accepted job 没有 claim evidence
→ unknown/bad according to policy
```

并解释 tradeoff。

---

# 7. 设计 Aggregate Metrics

目标：支持：

```text
start-latency SLI
capacity diagnosis
bounded cohort breakdown
```

至少设计：

```text
job_start_total{outcome=...}
job_start_latency_seconds histogram
queue_oldest_age_seconds
queue_depth
```

你可以改名字。

但每个 metric 必须写：

| Field | Answer |
|---|---|
| semantic question | ? |
| unit | ? |
| type/aggregation | ? |
| bounded labels | ? |
| expected cardinality | ? |
| missing semantics | ? |
| likely consumer | ? |

---

# 8. Cardinality Exercise

Starter：

```python
(("job_id", event.job_id), ("outcome", ...))
```

12 jobs → 12 series。

估算：

```text
10 jobs/s
1 hour
```

如果每个 job 一个永久 distinct labelset，会创造多少 distinct series identity？

然后解释为什么：

```text
job_id useful
```

并不意味着：

```text
job_id suitable metric label
```

---

# 9. 设计 Diagnostic Event

设计一个 `job_claimed` event，例如：

```json
{
  "event": "job_claimed",
  "job_id": "job-42",
  "wait_seconds": 4.81,
  "worker_pool": "default",
  "outcome": "late"
}
```

要求：

- 保留 correlation value；
- 不放 command；
- 不放 token / secret；
- event identity 稳定；
- bounded categorical fields 有清楚语义。

然后回答：

> 如果未来把 `outcome="late"` 改成 `status="slow"`，谁可能被破坏？

---

# 10. SLO

本实验使用：

```text
99% accepted jobs
first authoritative claim <= 2.0s
```

你要补齐：

- measurement window；
- applicable traffic scope；
- canceled/rejected requests；
- missing observation policy；
- measurement source；
- target owner；
- review cadence。

不要照抄生产公司的 target。

---

# 11. Error Budget

如果 SLO：

```text
99%
```

那么：

```text
allowed bad = 1%
```

对 10000 accepted jobs：

```text
budget = ? bad jobs
```

如果 30 分钟里已经出现 120 bad jobs：

回答：

- 这是否可能已经超出整个 window budget？
- 是否应该 page，仍取决于什么？
- 还需要什么时间窗口 / burn-rate context？

不要只算数字。

---

# 12. Symptom / Cause Table

分类：

| Signal | Symptom / Cause / Both | Why |
|---|---|---|
| start latency SLI | ? | ? |
| queue depth | ? | ? |
| oldest queue age | ? | ? |
| worker CPU | ? | ? |
| submit error ratio | ? | ? |
| retry rate | ? | ? |
| dependency timeout | ? | ? |

重点不是唯一答案，而是 reasoning。

---

# 13. Page Design

设计一个 page-level policy。

必须写：

```text
Trigger
User consequence
Urgency
Who owns it
First action
Diagnostic context
Stop condition
```

不允许：

```text
queue_depth > 10 → page
```

除非你能证明这个 threshold 与 urgent user impact 的关系。

---

# 14. Ticket Design

再设计一个非 urgent ticket，例如：

```text
slow error-budget burn
telemetry cardinality growth
capacity headroom trend
```

解释为什么它不应该 page。

---

# 15. Overload Reasoning

当前 deterministic burst：

```text
arrival burst
>
single worker service capacity
```

至少比较三种 response：

## A. Infinite Queue

```text
accept all
wait forever
```

## B. Bounded Queue + Rejection

```text
capacity reached
→ explicit reject
```

## C. Scale / Add Workers

```text
increase service rate
```

对每种写：

- user semantics；
- SLI consequence；
- retry consequence；
- blast radius；
- operational cost。

不要自动认为 C 最好。

---

# 16. Backpressure Contract

如果未来 TaskForge 做：

```text
queue full
→ reject submit
```

M04 需要回答：

```text
error code?
retryable?
Retry-After?
idempotency key?
```

M11 需要回答：

```text
算 availability bad event 吗？
还是 explicit capacity contract？
什么 metric？
什么时候 page？
```

把两个模块连接起来。

---

# 17. Rollout Gate

假设 Agent 实现了新的 remote worker scheduler。

不要写：

```text
CI green → 100%
```

设计：

```text
1%
→ check SLI / errors / saturation
→ 10%
→ ...
```

说明：

- 哪个 signal 是 stop trigger；
- 哪个只是 diagnostic；
- rollback 是否真能恢复；
- 是否涉及 M08 durable compatibility。

---

# 18. Telemetry Compatibility Review

假设已有 dashboard 依赖：

```text
job_claimed.outcome
```

新版本想改成：

```text
job_claimed.status
```

设计 migration：

```text
Expand
Migrate consumers
Contract
```

或者说明为什么这次可以 break。

---

# 19. Instrumentation Cost Review

列出你设计的 telemetry 的成本：

```text
metric series count
log/event volume
storage
query cost
privacy
retention
operator cognitive load
```

并明确一个你决定**不记录**的字段。

---

# 20. Agent Prompt：坏版本

让 Agent 执行：

> 给 TaskForge 加完整 observability，包括 metrics、logs、alerts，做到 production-ready。

先预测它可能做什么。

至少列 5 个风险：

```text
high-cardinality labels
arbitrary thresholds
alert every exception
sensitive logging
huge instrumentation diff
vendor coupling
wrong SLI
```

---

# 21. Agent Prompt：工程版本

写一个约束更明确的 prompt，至少包含：

```text
Goal
User-facing SLI specification
Measurement placement
Allowed / forbidden labels
Sensitive-data constraints
Existing telemetry contracts
Expected cardinality
Failure/missing-event semantics
No paging until action contract exists
Deterministic evidence
Independent review requirement
```

---

# 22. 实现任务

在你自己的 working copy 中实现一个最小 M11 reference direction。

推荐但不强制：

新增：

```text
production_observability.py
```

提供：

```python
summarize_start_latency(...)
metric_points(...)
diagnostic_events(...)
```

要求：

1. `job_id` 不进入 aggregate metric labels；
2. job ID 仍可进入 diagnostic event；
3. user SLI 在 baseline burst 中必须得到 `2/12`；
4. SLI summary 显式报告 `good/bad/unknown/total`；
5. bounded labels；
6. canonical TaskForge semantics 不改变。

---

# 23. Failure-before / Pass-after

先写 tests，至少：

```text
baseline naive dashboard says healthy
user SLI says violated
metric series count is bounded by category, not jobs
job_id remains available in diagnostic events
```

如果你重构生产模块，再保证旧 probes 仍通过。

---

# 24. Series Cardinality Negative Control

一个很强的 test：

```text
run 12 jobs
run 120 jobs
```

如果只增加同样 outcome/pool categories：

```text
aggregate metric series identity count
```

不应按 10x 增长。

这比：

```text
assert no job_id string in source
```

更接近真实 contract。

---

# 25. Missing Event Test

人为构造：

```text
submitted
no claimed event
window closes
```

验证你的 summary：

```text
不会把它悄悄丢出 denominator
```

具体 bad/unknown policy 由你定义。

---

# 26. Event Schema Test

不要 snapshot 整个 JSON 然后每次更新 golden。

测试稳定 contract：

```text
event name
required correlation id
wait duration
bounded outcome vocabulary
no command/secret
```

---

# 27. Alert 不需要真的接 Pager

实现一个 pure policy evaluator 即可，例如：

```python
def classify_reliability_action(...):
    ...
```

返回：

```text
page
ticket
none
```

重点是输入必须来自明确 SLO / budget model，而不是随手 threshold。

---

# 28. Independent Review

换 reviewer / Agent 后，先不给你的设计解释。

让它独立回答：

```text
What does this SLI actually measure?
What accepted work can disappear?
Can telemetry failure improve SLI?
Which labels are unbounded?
What pages require immediate action?
What schema is now compatibility surface?
What user pain remains invisible?
```

然后再比较你的 rationale。

---

# 29. Deliverables

提交：

1. `production-contract.md`
2. SLI specification + measurement implementation
3. measurement blind-spot analysis
4. metric/event schema
5. SLO/error-budget reasoning
6. page + ticket action contract
7. overload/backpressure comparison
8. implementation patch
9. tests / deterministic evidence
10. Agent prompt
11. independent review findings
12. residual risk

---

# 30. 评分

## 30% — User-centered Reliability Model

是否从用户行为而不是现有 dashboard 出发？

## 20% — Measurement Quality

是否明确 denominator、placement、missingness 与 blind spot？

## 15% — Telemetry Design

是否 bounded cardinality、语义清楚、无敏感字段、区分 aggregate 与 diagnostic signals？

## 15% — Operational Action

alert 是否有 urgency / ownership / action contract？

## 10% — Reliability / Overload Reasoning

是否考虑 queue age、backpressure、rejection、retry、capacity？

## 10% — Agent Orchestration / Review

是否约束 Agent，并独立验收？

---

# 31. 不加分项

以下不会因为“更高级”自动加分：

- Prometheus；
- Grafana；
- OpenTelemetry Collector；
- Jaeger；
- Tempo；
- vendor APM；
- 100 个 metrics；
- 100% trace sampling；
- 99.999% SLO；
- 大型 dashboard。

如果它们不帮助当前 reasoning，反而可能扣分。

---

# 32. 结束问题

完成实验后，请回答：

> 当你看到一个 production dashboard 全绿时，你还会问哪五个问题？

一个好的答案应该开始接近：

```text
这些绿灯对应的 user contract 是什么？
measurement 在哪里？
它漏掉什么？
denominator 是谁？
alerts 真正驱动什么行动？
```

这就是 M11 的目标。
