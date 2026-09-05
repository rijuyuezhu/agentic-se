# M11 Instructor Analysis — Production、Observability 与 Reliability

> 这是教师参考，不是学生第一遍实验时应该直接照抄的答案。

---

# 1. Baseline 最重要的事实

M11 starter 没有引入真实 wall-clock benchmark。

它用 deterministic synthetic timeline 表达一个 production workload：

```text
12 jobs almost at once
single worker
1s service time per job
```

所有 job：

```text
最终 SUCCEEDED
```

最终：

```text
queue depth = 0
```

于是 naive dashboard：

```text
success_ratio = 1.0
ending_queue_depth = 0
healthy = true
```

但 authoritative submit→claim wait：

```text
job-1   1.00s  good
job-2   1.95s  good
job-3   2.90s  bad
...
job-12  > 10s  bad
```

最终：

```text
good=2
bad=10
total=12
SLI=0.1667
```

这不是“dashboard 计算错误”。

它准确计算了自己定义的东西。

问题是：

> **它测的不是用户最重要的 contract。**

---

# 2. 这不是 performance benchmark

不要从这个 lab 推出：

```text
TaskForge 能处理 1 job/s
```

synthetic timeline 是教学 fixture。

目的只在于：

```text
all eventual outcomes good
while user latency bad
```

真实 capacity 需要真实 benchmark / production measurement。

---

# 3. Reference SLI Specification

本参考选择：

```text
Total:
  every accepted submission observed in the measurement window

Good:
  first authoritative claim_time - accepted_time <= 2.0s

Bad:
  authoritative first claim exists, but > 2.0s

Unknown:
  accepted submission exists but no first-claim evidence is available
  when the measurement is evaluated
```

Reference summary：

```text
ratio = good / total
```

因此 unknown 不会被自动当 good。

注意：

这不是唯一合理 policy。

一个真实系统可能：

```text
window not closed yet
→ pending, not final unknown
```

或者：

```text
telemetry coverage gap
→ separate coverage SLI
```

关键是不能 silent drop。

---

# 4. 为什么 denominator 必须从 accepted submissions 开始

错误版本：

```text
fast_claimed / all_claimed
```

如果一个 job：

```text
accepted
never claimed
```

它完全不在 denominator。

越严重的 backlog 反而可能让 SLI 更好看。

所以这次 specification 以：

```text
accepted submission
```

作为 cohort authority。

---

# 5. Reference Measurement Placement

本参考选择：

```text
service accepted event
+
worker authoritative claim event
```

原因：

- 能覆盖 queue wait；
- 不依赖 client polling cadence；
- 与 lifecycle authority 接近；
- deterministic lab 中容易验证。

Blind spots：

- client→API network delay 不在里面；
- ingress 前 rejection 不在 accepted-job SLI；
- telemetry event loss 会造成 unknown；
- distributed clocks 将来需要处理 clock semantics。

因此它不是“真实用户端到端 latency”的完美替代。

---

# 6. Reference Implementation

临时副本新增：

```text
src/taskforge/production_observability.py
```

核心类型：

```python
@dataclass(frozen=True)
class StartLatencySummary:
    good: int
    bad: int
    unknown: int
    total: int
    ratio: float
```

关键价值是：

```text
unknown 是 first-class
```

而不是被过滤掉。

---

# 7. Reference Aggregate Metrics

没有真的接 Prometheus。

我们只验证 metric identity model。

Reference labels：

```text
outcome = within_target | late
worker_pool = default
```

不含：

```text
job_id
command
```

因此 baseline：

```text
12 jobs
→ 2 series identities
```

扩大：

```text
120 jobs
→ still 2 series identities
```

这是一条很强的 negative control。

---

# 8. 为什么不测试源码里没有字符串 job_id

这种 test：

```python
assert "job_id" not in source
```

是错的。

因为 diagnostic event 正应该保留 `job_id`。

真正 contract 是：

```text
aggregate metric label identity
不得随 individual job identity 增长
```

所以用行为层 cardinality test 更合理。

---

# 9. Diagnostic Event

Reference：

```json
{
  "event": "job_claimed",
  "job_id": "job-12",
  "wait_seconds": 11.45,
  "worker_pool": "default",
  "outcome": "late"
}
```

这里 `job_id` 很有用：

```text
incident query
correlate submit/claim/finish
investigate one job
```

因此：

```text
job_id high cardinality
```

不能推出：

```text
job_id has no telemetry value
```

只是说明 signal placement 不同。

---

# 10. Sensitive Data

Reference event 明确没有：

```text
command
headers
user content
tokens
```

因为 TaskForge command 未来可能包含：

```text
paths
credentials passed poorly
user input
business data
```

不能默认进入 telemetry backend。

---

# 11. Missing Claim Test

构造：

```python
[JobLifecycleEvent("submitted", 0.0, "job-x")]
```

Reference：

```text
good=0
bad=0
unknown=1
total=1
ratio=0.0
```

这证明 accepted job 没有因为 missing claim 被 denominator 丢掉。

---

# 12. Error Budget Calculation

Reference helper：

```text
burn_rate = observed_bad_ratio / allowed_bad_ratio
budget_consumed = burn_rate × window_fraction
```

对 baseline：

```text
bad_ratio = 10/12 ≈ 0.8333
SLO = 0.99
allowed_bad = 0.01
burn ≈ 83.33x
```

如果这样的状态持续 1h，而 SLO window 是 30 days：

```text
window_fraction = 1 / 720
budget consumed ≈ 0.1157
```

即约 11.6% 整个 30-day budget。

这个数很严重。

但 reference **没有硬编码说一定 page**。

Page policy 还取决于：

```text
windowing
persistence
traffic representativeness
operator action
service criticality
```

---

# 13. 为什么不直接复制 Google 14.4x

Google Workbook 给的是成熟实践中的推荐起点。

TaskForge 课堂没有真实：

```text
30-day traffic distribution
on-call policy
business cost
```

所以本 lab 训练 formula 和 decision relation，而不是 threshold cargo cult。

---

# 14. Symptom / Cause Reference

## start-latency SLI

```text
symptom
```

因为直接表达 user waiting experience。

## queue depth

```text
mostly cause / saturation signal
```

它可以解释 wait，但最终 depth=0 证明它不是完整 symptom history。

## oldest queue age

比 depth 更接近 user pain，但仍然通常是 queue-internal signal。

## CPU

通常 cause / capacity signal。

## submit error ratio

可能直接是 user symptom。

## retry rate

通常 cause/amplifier signal，也可能反映 user retries。

---

# 15. Alert Reference

Page 不直接写：

```text
queue_depth > 10
```

Reference action contract：

```text
Trigger:
  sustained urgent burn of start-latency SLO

User consequence:
  accepted jobs are not beginning within promised time

Urgency:
  current burn would consume significant budget before normal business response

Owner:
  TaskForge on-call

First actions:
  inspect oldest queue age, arrival/service rate, worker availability,
  recent rollout markers, dependency latency

Mitigation options:
  rollback recent scheduler change
  restore worker capacity
  throttle/reject new work according to public capacity contract

Stop:
  short-window symptom recovers and long-window burn is controlled
```

这比“CPU > 80%”更有 operational meaning。

---

# 16. Ticket Reference

例如：

```text
capacity headroom steadily declining over 2 weeks
but no current SLO threat
```

适合 ticket。

因为：

```text
human action required
but not now
```

---

# 17. Overload Options

## Infinite Queue

优点：

```text
few immediate rejections
simple semantics
```

缺点：

```text
unbounded latency
memory/storage growth
stale work
```

## Bounded Queue + Rejection

优点：

```text
bounded resource use
explicit overload
protect existing work
```

缺点：

```text
public rejection contract needed
caller retry may amplify
availability SLI interpretation changes
```

## Scale Workers

优点：

```text
higher service rate
```

缺点：

```text
cost
startup lag
external dependency may become bottleneck
concurrency/failure complexity
```

没有 universal winner。

---

# 18. Backpressure 的关键不是 queue library

正确问题：

```text
capacity information 如何向 producer/caller 传播？
```

如果 API 永远 accepts：

```text
availability metric 可能很好
```

但实际只是把 failure 变成 latency。

这正是 baseline 的教学价值。

---

# 19. Telemetry Compatibility

如果已有 consumer 依赖：

```text
job_claimed.outcome
```

改名必须像 M08 一样推理：

```text
Expand:
  produce old + new / reader supports both

Migrate:
  update dashboards/alerts/queries

Contract:
  remove old
```

具体是否值得这么做取决于 consumer 数量和风险。

---

# 20. Reference Test Results

临时副本：

```text
6 core tests
5 M11 tests
-----------
11 passed
```

5 个 M11 tests 分别验证：

1. deterministic burst 得到 `2 good / 10 bad`；
2. 12 vs 120 jobs aggregate series identity 不增长；
3. diagnostic events 保留 job_id，但不带 command；
4. missing claim 不消失；
5. error-budget consumption calculation 与 window semantics 连接。

---

# 21. 为什么 Reference 没修改 Canonical TaskForge

和前几章一样，本章的真正目标是：

```text
学生设计 measurement contract
```

而不是把仓库快速演化成完整 production framework。

因此 canonical baseline 只增加：

```text
production_signals.py
m11_production_probe.py
```

它们是教学 workload + flawed instrumentation surface。

reference solution 留在 instructor analysis，不提交正式实现。

---

# 22. Student 常见错误

## 错误 1

```text
success ratio 100%
→ no problem
```

遗漏 latency contract。

## 错误 2

```text
queue depth > threshold
→ page
```

没有 action/impact reasoning。

## 错误 3

```text
job_id useful
→ metric label
```

混淆 correlation 与 aggregation。

## 错误 4

```text
missing claimed event
→ filter out
```

产生 survivorship bias。

## 错误 5

```text
OpenTelemetry installed
→ observability done
```

工具替代 measurement design。

## 错误 6

```text
SLO = current p99 + 10%
```

current performance 偷换 user requirement。

## 错误 7

```text
alert every exception
```

把 diagnostic event 误当 urgent action。

---

# 23. Agent Review Checklist

Agent instrumentation patch 必须独立问：

```text
Does the SLI measure user outcome?
Can bad work disappear from denominator?
Can telemetry failure improve the SLI?
Are labels bounded?
Does cardinality scale with requests/users/jobs?
Are secrets or user content recorded?
Did metric/event names change existing consumers?
Are pages actionable?
Did the Agent invent arbitrary SLO thresholds?
Did instrumentation itself add meaningful load?
```

---

# 24. 一个非常重要的 M11 结论

```text
production evidence
!=
more data
```

Production evidence 的质量取决于：

```text
semantic alignment
coverage
placement
aggregation
cost
actionability
```

所以 observability 是 software design 的延伸。

---

# 25. 评分时真正看什么

高分答案不一定有任何第三方 telemetry stack。

最重要的是：

```text
能不能从 user contract 推导 measurement
能不能识别 blind spot
能不能控制 cardinality
能不能解释 missing data
能不能把 alert 连接到 action
能不能独立 review Agent instrumentation
```

如果学生接了漂亮 Grafana dashboard，但这些问题答不出来，不应高分。

---

# 26. M11 到 M12 的桥

M12 会进一步问：

> 当 Agent 可以自己运行 tests、读取 logs、查询 metrics、修改代码、重新部署时，谁决定 observation 的语义？谁决定何时 stop？谁拥有 rollback / production action authority？

M11 的答案已经提供基础：

```text
Agent can collect and analyze evidence
but human/system policy must still define
what counts as acceptable service and authorized action
```
