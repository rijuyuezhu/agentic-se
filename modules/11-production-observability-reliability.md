# M11 — Production、Observability 与 Reliability

> 单元测试告诉你：在我们构造过的场景中，代码做了我们要求的事。
>
> Production engineering 还要回答一个更难的问题：
>
> **真实系统正在运行时，我们凭什么知道用户得到的是我们承诺的服务？**

前十章已经建立了一条完整链：

```text
M00  change / complexity
M01  contract / invariant
M02  ownership
M03  executable evidence
M04  boundary / error / retry
M05  refactoring
M06  legacy takeover
M07  concurrency / failure
M08  compatibility / migration
M09  architecture
M10  review / change engineering
```

M11 做的是一件很重要的事：

> 把 engineering evidence 从 **pre-production** 延伸到 **production**。

---

# 1. Tests green，然后呢？

假设 TaskForge：

```text
6 tests passed
CI green
release deployed
```

一小时后：

```text
所有 job 最终都成功
数据库没报错
CPU 只有 40%
queue 最后也是 0
```

你会说系统健康吗？

不一定。

用户可能经历：

```text
submit
 ↓
等 47 秒
 ↓
job 才开始
```

而产品承诺可能是：

```text
99% job 在 2 秒内开始执行
```

最终成功并不能弥补等待时间。

这就是本章的开场原则：

> **Production correctness 不是“进程没挂 + 最终成功”。它必须重新连接到用户可观察的 contract。**

---

# 2. Monitoring、Telemetry、Observability 不要混成一个词

本课程不用这些词制造术语门槛，但会区分它们解决的问题。

## 2.1 Telemetry

系统产生的 observation data：

```text
metrics
logs
structured events
traces
profiles
health probes
synthetic probes
client reports
```

Telemetry 是材料。

不是答案。

---

## 2.2 Monitoring

针对已知问题持续计算某些状态，例如：

```text
error ratio
queue age
p99 latency
worker saturation
error-budget burn
```

Monitoring 更像：

> 我知道自己关心什么，所以持续观察它。

---

## 2.3 Observability

在本课程中，我们不用一个严格学术定义争论这个词。

我们采用一个工程化工作定义：

> **系统是否提供足够、语义清楚、成本可控的 production evidence，使工程师能判断重要用户行为是否满足 contract，并在失败时缩小原因空间。**

这里有几个关键词：

```text
important behavior
semantic clarity
cost
user outcome
diagnosis
```

所以：

```text
接入 OpenTelemetry
!=
获得 observability
```

```text
收集 5000 个 metrics
!=
知道系统是否健康
```

---

# 3. 从 User Expectation 往回设计

Google SRE 对 SLO 的一个核心建议非常值得保留：

> 先从 users care about what 开始，不要先从 what is easy to measure 开始。

对 TaskForge，用户不一定在乎：

```text
Python process RSS
worker thread count
SQLite fsync duration
queue implementation
```

它们可能对 diagnosis 很重要。

但用户更可能在乎：

```text
submit 是否成功
job 多久开始
job 是否完成
结果是否正确
取消是否及时生效
状态是否新鲜
```

于是 production evidence chain 应该从：

```text
User / Product expectation
```

开始，而不是：

```text
What metrics library do we have?
```

---

# 4. SLI：你到底在测什么？

SLI = Service Level Indicator。

可以理解为：

> **对某个重要 service outcome 的量化 observation。**

例如：

```text
成功请求数 / 总请求数
```

```text
2 秒内开始的 jobs / submitted jobs
```

```text
10 分钟内仍然新鲜的数据读取 / 总读取
```

```text
正确结果数 / 被验证结果数
```

---

# 5. SLI Specification 与 SLI Implementation

这是本章最重要的区分之一。

## 5.1 Specification

你真正想知道什么？

例如：

```text
submitted job 是否在 2 秒内开始？
```

这与工具无关。

---

## 5.2 Implementation

你具体怎样测？

例如：

```text
A. API 记录 submit timestamp
   worker 记录 claim timestamp

B. client 提交后 poll status
   记录第一次看到 RUNNING 的时间

C. synthetic probe 定期提交特殊 job
   观察 end-to-end start latency
```

三个 implementation 都试图近似同一个 specification。

但它们 blind spot 不一样。

---

# 6. Measurement placement 会改变你看到的世界

假设：

```text
client
 ↓
load balancer
 ↓
API
 ↓
queue
 ↓
worker
```

如果 latency 从 API 收到请求开始测：

```text
network / load-balancer rejection
```

可能不可见。

如果只测 worker execute duration：

```text
queue wait
```

完全消失。

如果只测 client：

```text
内部具体哪个 component 慢
```

又难诊断。

所以：

> **Where you observe is part of the measurement contract.**

---

# 7. Measurement Blind Spot

本课程使用这个术语表示：

> measurement implementation 系统性漏掉了 specification 中的重要部分。

例如 TaskForge：

```text
metric:
  final queue depth = 0
```

它可能完全正确。

但是它无法回答：

```text
过去 10 分钟用户等了多久？
```

因为：

```text
queue depth at end
```

把历史等待信息擦掉了。

这不是 metric bug。

是 **measurement model 不足**。

---

# 8. TaskForge M11 Baseline

运行：

```bash
cd labs/taskforge
PYTHONPATH=src uv run --with pytest --no-project \
  python tools/m11_production_probe.py
```

得到：

```text
[NAIVE DASHBOARD]
submitted = 12
success_ratio = 1.0
ending_queue_depth = 0
healthy = true
```

看起来很好。

但是 user-centered SLI：

```text
start within 2s:
2 good
10 bad
12 total

SLI = 0.167
```

如果 SLO 是：

```text
99% within 2s
```

这是严重 violation。

---

# 9. 为什么“eventual success”是一个危险的单一指标

很多系统会自然记录：

```text
requests_total
success_total
failure_total
```

于是：

```text
success_ratio = success_total / requests_total
```

非常有用。

但它只能回答某一类问题。

例如：

```text
job 等 10 分钟后成功
```

仍然是 success。

所以：

```text
availability / success
!=
latency
```

同样：

```text
latency
!=
freshness
```

```text
freshness
!=
correctness
```

不能用一个漂亮指标替代整个 service contract。

---

# 10. SLO：什么时候算“足够好”？

SLO = Service Level Objective。

例如：

```text
99% submitted jobs
must be claimed within 2 seconds
over a rolling 28-day window
```

这里至少包含：

```text
what events
what is good
what is total
threshold
measurement window
scope / exclusions
measurement placement
```

如果只写：

```text
latency SLO = 99%
```

几乎没有意义。

---

# 11. 先定义 Good Event

对 TaskForge start-latency SLI：

```text
good event:
  a submitted job whose first authoritative claim
  occurs <= 2.0s after accepted submission
```

马上会出现边界问题：

```text
cancel before claim 算什么？
rejected submit 算 total 吗？
client retry 产生 duplicate submit 怎么算？
restored jobs after restart 怎么算？
clock skew 怎么处理？
```

这些不是 monitoring trivia。

它们是 contract questions。

M01 又回来了。

---

# 12. Denominator 是工程判断

很多 SLI 最危险的地方不是 numerator。

是 denominator。

例如：

```text
successes / completed_requests
```

如果超时、掉线、未完成请求根本没进入 denominator：

```text
99.99% success
```

可能只是 survivorship bias。

更合理的 denominator 可能是：

```text
accepted requests
```

或者：

```text
all attempts observed at ingress
```

取决于 specification。

---

# 13. Unknown 不应该偷偷变成 Good

一个很常见的 telemetry bug：

```text
missing status
→ ignored
```

如果系统漏 telemetry 恰好发生在 outage 时：

```text
worst requests disappear
```

SLI 反而变好。

所以 production measurement 要显式讨论：

```text
unknown
missing
late
partial
```

怎么计入。

一个 conservative design 可能：

```text
unknown counts as bad
```

但也不是永远正确。

关键是：

> **measurement failure semantics 必须显式。**

---

# 14. 100% 为什么通常不是目标

100% reliability 听起来很好。

但它意味着：

```text
任何 failure 都不可接受
```

可能导致：

```text
极端 redundancy
极慢 change velocity
昂贵 migration
永不升级 dependencies
极端保守 release
```

可靠性是成本函数。

所以更成熟的问题是：

```text
什么 level 足以满足用户？
低于它时怎么反应？
高于它很多时，是否在浪费 engineering effort？
```

---

# 15. Error Budget

如果 SLO：

```text
99.9%
```

那么一个简单 error budget：

```text
0.1% bad events
```

它不是：

> 允许工程师故意制造 0.1% bug。

而是：

> 用一个共同 quantitative model 表达我们愿意承受多少 unreliability。

这样可以讨论：

```text
继续 rollout？
停止 feature launch？
优先做 capacity？
优先做 retry control？
继续 experiment？
```

---

# 16. Burn Rate

error budget 不只看“剩多少”。

还要看：

```text
烧得多快？
```

例如：

```text
budget 可撑 30 天
```

如果现在速度意味着：

```text
2 小时烧完
```

那是 urgent。

如果意味着：

```text
40 天烧完
```

可能不该 page。

所以 burn rate 把：

```text
当前坏事件比例
```

变成：

```text
相对于允许 unreliability 的消费速度
```

---

# 17. 不背 14.4x

Google SRE Workbook 给出了 multi-window multi-burn-rate 的推荐起点。

本课程不要求记数字。

要求理解：

```text
alert policy
=
impact magnitude
× duration
× budget consequence
× response urgency
```

如果 service 不同：

```text
traffic
business importance
on-call staffing
recovery time
```

都不同。

参数当然会变。

---

# 18. Alert 是一个 Action Contract

本课程把 page 理解成：

> **A human must do something now.**

所以一个 page 必须隐含：

```text
现在有用户影响或即将有
有人有权限/能力改变结果
现在处理比明天处理明显更好
```

如果不是：

```text
page
```

可能是错误 notification channel。

---

# 19. Symptom vs Cause

这是 production monitoring 最重要的区分之一。

## Symptom

用户体验到的坏结果：

```text
job start latency > 2s
request failed
result stale
cancel not taking effect
```

## Cause

可能解释 symptom 的内部状态：

```text
queue depth high
worker CPU saturated
database slow
retry rate high
GC pause
```

---

# 20. 为什么 Page 更应该接近 Symptom

假设：

```text
worker CPU = 95%
```

如果：

```text
所有用户 requests 仍满足 SLO
```

可能只是高效使用资源。

反过来：

```text
CPU = 20%
```

但 dependency 卡住，用户大量 timeout。

CPU alert 没有抓到真正问题。

所以：

> **Page user impact; use cause signals to diagnose.**

不是绝对规则，但通常是很强的起点。

---

# 21. Four Golden Signals：heuristic，不是 dashboard template

Google SRE 的四个 golden signals：

```text
latency
traffic
errors
saturation
```

非常实用。

TaskForge 可以映射：

```text
latency:
  submit → claim
  claim → finish

traffic:
  submit rate

errors:
  rejected / failed / bad-SLI jobs

saturation:
  queue age
  queue depth
  worker utilization
```

但不要机械认为：

```text
四张图齐全
= observability 完整
```

如果用户关心 correctness/freshness：

仍然需要对应 SLI。

---

# 22. Queue Depth 为什么容易骗人

queue depth 很有价值。

但它是一个 instantaneous state。

例如：

```text
t=0   burst enters
queue=100

t=60  queue drained
queue=0
```

如果 dashboard 只采到了：

```text
t=60
```

就可能说：

```text
healthy
```

而过去一分钟用户已经经历了巨大 delay。

所以 queue systems 常常需要同时考虑：

```text
queue depth
oldest age
wait latency distribution
arrival rate
service rate
rejection/load shedding
```

---

# 23. Final State 不是 History

M07 已经学过：

```text
最终 state 看起来合法
!=
operation history 合法
```

M11 再次出现：

```text
ending queue depth = 0
!=
用户没有经历 backlog
```

Production systems 很多问题本质上是：

> history information 被最终状态擦掉了。

这也是为什么 event / histogram / trace / duration measurements 有价值。

---

# 24. Metric 是 Aggregation Contract

一个 metric 不只是一个 number。

它定义：

```text
measurement unit
aggregation semantics
label dimensions
scope
monotonicity / temporality
consumer expectations
```

比如：

```text
taskforge_jobs_total{outcome="succeeded"}
```

比：

```text
taskforge_job_1234_succeeded = 1
```

更容易聚合。

---

# 25. Metric Cardinality

假设 metric：

```text
job_finished_total{
  job_id="job-123",
  outcome="succeeded"
}
```

每个 job 一个不同 `job_id`。

那么：

```text
job count ↑
→ time series count ↑
```

这就是高 cardinality dimension。

Prometheus 官方明确提醒：

> 每个不同 labelset 都是一条新的 time series。

所以 telemetry schema 会影响：

```text
RAM
CPU
storage
network
query cost
operational stability
```

---

# 26. 高 Cardinality 信息不是“没用”

`job_id` 非常有用。

但适合什么 signal？

通常：

```text
metrics:
  bounded aggregation dimensions

logs/events/traces:
  correlation / high-cardinality context
```

例如：

```text
metric:
taskforge_job_start_total{pool="remote", outcome="late"}
```

而 event：

```json
{
  "event": "job_claimed",
  "job_id": "job-847231",
  "worker_id": "worker-12",
  "wait_ms": 4812
}
```

两者解决不同问题。

---

# 27. Logs 不是 println

日志真正有工程价值时，需要能回答：

```text
what happened?
when?
where?
which logical operation?
what outcome?
what causal context?
```

这不等于所有日志必须 JSON。

但如果机器需要稳定查询：

```text
free-form prose
```

通常会比明确字段更脆弱。

---

# 28. Structured Event 是一种 Semantic Boundary

例如：

```json
{
  "event": "job_finished",
  "job_id": "job-42",
  "outcome": "failed",
  "exit_code": 7,
  "worker_pool": "remote"
}
```

一旦 dashboards / alerts / offline analysis 开始消费：

```text
field names
value meanings
event identity
```

就形成 compatibility surface。

M08 又回来了。

---

# 29. Telemetry Schema 也要 Migration

今天：

```text
status="failed"
```

明天：

```text
result="error"
```

如果直接 cut over：

```text
dashboards break
alerts disappear
incident queries lie
```

所以 telemetry 也可能需要：

```text
expand
migrate consumers
contract
```

这不是过度工程。

取决于 telemetry consumers 有多少、寿命多长、风险多大。

---

# 30. Trace 解决什么？

Trace 最适合回答：

> 一个 logical operation 穿过多个 component 时，时间和 causal path 去哪里了？

例如：

```text
submit request
  ↓ 12ms
API validation
  ↓ 3ms
queue enqueue
  ↓ 4200ms
worker claim
  ↓ 310ms
external command
```

如果只看：

```text
API latency = 15ms
worker execution = 310ms
```

可能完全不知道：

```text
4200ms queue wait
```

---

# 31. 但 Trace Everything 也不是答案

trace 每个内部函数：

```text
大量 span
高 storage cost
sampling complexity
query noise
```

不一定提高 diagnosis quality。

同样：

```text
100% sampling
```

也不是普遍正确。

Instrumentation 设计始终要回答：

```text
what decision will this evidence support?
```

---

# 32. Correlation ID 的位置

`request_id` / `job_id` 这类 identifier：

```text
metrics label
```

往往危险。

但在：

```text
logs
traces
structured events
```

里非常有价值。

这是一个典型例子：

> **字段是否有用，不等于字段适合所有 signal。**

---

# 33. Production Evidence Chain

本课程在 M11 使用这个综合模型：

```text
User expectation
   ↓
SLI specification
   ↓
measurement implementation
   ↓
telemetry events / metrics / traces
   ↓
aggregation / window
   ↓
SLO / budget
   ↓
alert or decision
   ↓
operator action
```

每一箭头都要能解释。

---

# 34. 常见断链 1：Measure What Is Easy

```text
CPU easy to measure
→ CPU becomes SLI
```

错误在于：

```text
measurement availability
```

偷换成：

```text
product importance
```

---

# 35. 常见断链 2：Metric Has No Decision

收集：

```text
42 dashboards
900 charts
```

但没有人能说：

```text
看到它变化后做什么？
```

这叫 telemetry inventory。

不叫 operational design。

---

# 36. 常见断链 3：Alert Has No Action

```text
queue_depth > 100
→ page
```

但 operator 只能：

```text
看一眼
等它自己恢复
```

那 page 很可能没有 actionability。

更合理可能：

```text
queue-depth cause signal
→ dashboard / diagnosis

start-latency SLO burn
→ page
```

---

# 37. 常见断链 4：Averages Hide Tails

假设：

```text
90% = 100ms
10% = 10s
```

平均值可能仍然“看起来还行”。

但大量用户非常痛苦。

所以 latency 往往用：

```text
threshold ratios
percentiles
histograms
```

而不是只用 average。

注意：percentile 也不是万能。

关键仍然是用户 contract。

---

# 38. 常见断链 5：Success + Fast Error

如果失败请求 5ms 返回 500：

```text
all-request average latency
```

甚至会因为 outage 变低。

所以要区分：

```text
successful latency
failed latency
error ratio
```

否则 metric 可能在系统变坏时“改善”。

---

# 39. Common Failure: Missing Events Improve SLI

例如：

```text
telemetry exporter overload
→ slow requests 的 finish event 丢失
```

如果 denominator 只统计完整 event pairs：

```text
slow jobs 消失
SLI 上升
```

这是 observability system 与 product failure 相关导致的 bias。

需要考虑：

```text
coverage
missingness
telemetry reliability
```

---

# 40. Metrics、Logs、Traces 不要按“3 Pillars”机械分工

一个常见说法是 observability 有三根柱子：

```text
metrics
logs
traces
```

它可以帮助初学者分类。

但本课程不把它当完整 theory。

真正的问题仍然是：

```text
我要判断什么？
哪种 evidence 最合适？
```

---

# 41. Signal Selection

可以用一个简单矩阵：

| Question | Often useful signal |
|---|---|
| 整体是否违反 SLO？ | aggregated metrics |
| 哪类 request 受影响？ | labeled metrics / events |
| 某个 job 到底经历了什么？ | structured event / trace |
| 为什么 dependency 慢？ | trace + component metrics |
| 故障前发生了什么？ | logs/events |
| CPU hotspot 在哪？ | profiles |

这不是硬规则。

只是从 question 出发。

---

# 42. Reliability 不只是 Detect Failure

好的 production engineering 还包括：

```text
prevent overload
limit blast radius
shed load
degrade gracefully
retry safely
recover quickly
```

M07、M09 已经建立了其中一部分。

M11 关注的是：

> 这些机制是否有 evidence 告诉我们它们真的在工作？

---

# 43. Saturation 是 Failure Precursor

如果：

```text
arrival rate > service rate
```

queue 会增长。

增长本身可能暂时还没有错误。

但它意味着未来：

```text
wait latency ↑
timeout ↑
retry ↑
load ↑
```

于是可能进入 positive feedback loop。

所以 saturation signal 很重要。

---

# 44. Queue Age 往往比 Queue Depth 更接近用户痛苦

两种 queue：

```text
A: 10000 jobs, processing extremely fast
B: 10 jobs, oldest waiting 5 minutes
```

仅看 depth：

```text
A 更严重
```

用户体验可能正好相反。

所以 architecture-specific saturation metric 要结合 workload semantics。

---

# 45. Backpressure

backpressure 的核心不是某个 library API。

是：

> downstream 处理能力不足时，系统如何把 capacity information 向 upstream 传播。

可能形式：

```text
bounded queue
request rejection
rate limit
client throttling
adaptive concurrency
pause producer
```

没有 backpressure 的系统常见结果：

```text
accept everything
queue forever
```

表面 availability 很高。

实际 user latency 无限恶化。

---

# 46. Load Shedding

有时：

```text
reject 5%
```

比：

```text
100% 请求都慢到超时
```

更可靠。

因为 bounded failure 可以防止整个系统 collapse。

但 load shedding 需要明确：

```text
谁被 shed？
怎么告诉 caller？
retry semantics？
是否算 SLI bad event？
优先级？
```

这又回到 M04 contract。

---

# 47. Graceful Degradation

如果完整结果很贵：

```text
full result
↓ overload
cached/stale/partial result
```

可能比 hard failure 更好。

但要看 product contract。

例如：

```text
搜索结果略旧
```

可能接受。

```text
银行余额略旧
```

可能完全不接受。

Reliability 不是抽象层面的“永远 fallback”。

---

# 48. Reliability Mechanism 也可能制造事故

例如：

```text
retry
failover
fallback
cache
```

都可以帮助恢复。

也都可能：

```text
放大 load
隐藏 stale data
扩大 blast radius
制造 duplicate effect
```

所以每个 mechanism 都需要 production evidence。

---

# 49. Release 也是 Production Experiment

deploy 后：

```text
new binary exists
```

不等于：

```text
new behavior safe at production scale
```

所以 rollout 可以设计成：

```text
1%
5%
20%
100%
```

每一步看：

```text
SLI
error budget
capacity
new error mode
```

这不是 release ceremony。

是降低 blast radius 的 architecture + evidence strategy。

---

# 50. Canary 必须看对 Signal

如果 canary 只看：

```text
process alive
CPU
memory
```

但 release 把：

```text
job start latency
```

从 1s 变成 8s：

canary 仍可能判 green。

所以：

> **Rollout gate 应连接到 change risk 和 user-facing SLI。**

---

# 51. Production Debugging 的目标不是先找 Root Cause

incident 开始时经常不知道 root cause。

第一优先级可能是：

```text
impact?
scope?
ongoing?
getting worse?
can we mitigate?
```

而不是立刻：

```text
哪个 commit 哪一行？
```

所以 production telemetry 要同时支持：

```text
impact assessment
mitigation decision
cause narrowing
```

---

# 52. Diagnosis Funnel

一个实用 model：

```text
User symptom
   ↓
Which operation / cohort?
   ↓
Which component / dependency?
   ↓
Which resource / state transition?
   ↓
Which causal event / code path?
```

Metrics 往往擅长上半段聚合。

Trace/events/logs 往往帮助下钻。

---

# 53. Cohort 是很强的 Dimension

如果总体：

```text
99.5% good
```

但：

```text
remote workers = 60% good
local workers = 99.99% good
```

总量会隐藏问题。

合理 bounded dimensions 可能包括：

```text
operation
region
worker_pool
client_version
outcome
bounded error code
```

但每个 dimension 都增加 cardinality 和 query complexity。

---

# 54. 不要把 Arbitrary String 当 Dimension

例如：

```text
error_message
command
user_id
job_id
full URL
```

通常不可控。

更好的 metric dimension：

```text
error_code="dependency_timeout"
```

然后详细 message 放 event/log。

这和 M04 的 machine-readable error contract 是同一思路。

---

# 55. Telemetry 中的 PII / Secrets

Observability 数据常常被复制到：

```text
log backend
metrics backend
trace backend
incident docs
alerts
chat rooms
```

所以：

```text
command text
headers
tokens
user content
```

不能因为“debug 有用”就默认记录。

Telemetry schema 也是 security/privacy boundary。

---

# 56. Sampling

高 volume traces/logs 经常需要 sampling。

sampling 会改变：

```text
coverage
rare-event visibility
cost
```

所以不能说：

```text
sampled telemetry shows no errors
→ no errors happened
```

需要知道 sampling semantics。

---

# 57. Production Probe

Synthetic probe 的价值：

```text
从外部定期执行一个真实用户路径
```

它可以发现：

```text
process healthy
但 end-to-end path broken
```

但 probe 也可能：

```text
只覆盖一个 region
只覆盖一个 account
行为过于简单
自身网络故障
```

仍然是 measurement implementation，而不是 truth oracle。

---

# 58. White-box + Black-box

```text
white-box:
  component internals
  queues
  resources
  retries

black-box:
  user-visible outcome
  synthetic/client perspective
```

两者互补。

只 white-box：

```text
可能看不到真实 user path
```

只 black-box：

```text
知道坏了，但 diagnosis 很慢
```

---

# 59. Instrumentation 的 Change Cost

一旦大量 dashboards 依赖：

```text
metric_name{labels...}
```

修改 telemetry schema 就有 migration cost。

所以 instrumentation 也值得 review：

```text
name
unit
labels
cardinality
semantics
consumer
retention
```

不是：

```text
加个 counter 很简单
```

---

# 60. Observability Debt

典型表现：

```text
没人知道哪些 dashboards 有用
alerts 长期 mute
metric names 语义冲突
labels 无限增长
incident 每次靠 grep random logs
release 没有 user SLI gate
```

这不是“监控团队的问题”。

它直接降低 change safety。

---

# 61. Production Evidence 与 Review

M10 的 PR description 应该开始能够回答：

```text
上线以后怎么知道它工作正常？

expected production signal?
new failure mode?
rollout signal?
rollback trigger?
telemetry compatibility?
```

对高风险 change，这些也是 correctness argument 的一部分。

---

# 62. “没有新 Metrics”也可以是正确设计

不是每个 PR 都要加 telemetry。

如果：

```text
已有 SLI 已覆盖风险
已有 event 足够 diagnosis
新增 metric 无决策价值
```

那不加是合理的。

Instrumentation 不是 ceremony。

---

# 63. “加 Metrics”也不能替代 Contract

一个 Agent 可能面对 ambiguous behavior 时说：

> 先加 observability，以后看 production 再决定。

有时这是合理 experiment。

但如果问题是：

```text
unknown cancel 到底该返回什么？
```

仅仅记录 metric：

```text
cancel_unknown_total
```

并没有定义 API semantics。

Observation 不能替代 product decision。

---

# 64. Observability 与 Uncertainty

合理使用 telemetry 的一个重要场景是：

```text
我们不确定某个 legacy behavior 是否被依赖
```

可以先：

```text
instrument usage
observe window
migration
remove
```

这和 M08 deprecation telemetry 很自然地连接。

---

# 65. Production Evidence 不是无限保留

Telemetry 有成本：

```text
storage
indexing
query
privacy
retention
human attention
```

所以要问：

```text
这个 signal 的 lifetime 是什么？
```

例如 migration metric：

```text
old_v1_reader_seen_total
```

migration 完成后可能应该删除。

---

# 66. Temporary Telemetry

临时 instrumentation 可以非常有价值。

例如：

```text
rollout 期间记录一个新 failure reason
```

目的明确：

```text
验证 hypothesis
```

成功后移除。

这比永久堆 dashboard 更健康。

---

# 67. Operational Action Contract

每个 alert 最好能回答：

```text
What happened?
Who is affected?
How urgent?
What should operator do first?
What evidence narrows diagnosis?
When is it safe to stop acting?
```

不要求 alert 本身写完整 runbook。

但必须有 actionable path。

---

# 68. Page / Ticket / Log

一个非常实用的简化：

```text
Page:
  act now

Ticket:
  act later

Log/Event:
  no current human action required
```

不要创造：

```text
email alert nobody owns
```

这种第四类 limbo。

---

# 69. Alert Fatigue 是 Reliability Bug

如果：

```text
每天 100 个 false pages
```

人的响应系统会退化。

最终真正事故：

```text
被忽略
```

所以 alert precision 不只是 on-call 体验。

它是可靠性系统的一部分。

---

# 70. Runbook 不是所有问题的补丁

一个坏 alert：

```text
CPU > 80%
```

不能靠写 3 页 runbook magically 变 actionable。

先问：

```text
为什么这个 condition 需要人现在处理？
```

如果答案不成立，应该改 alert。

---

# 71. Capacity Planning 不是预测未来的水晶球

我们只需要足够回答：

```text
当前 growth + capacity
什么时候碰到 saturation？
```

并给出 lead time。

如果扩容需要：

```text
3 weeks
```

那么等 SLO violation 再处理已经太晚。

---

# 72. Leading vs Lagging Signals

```text
lagging:
  user SLO already bad

leading:
  queue age rising
  saturation approaching limit
  error budget burn accelerating
```

两者都重要。

但 leading signal 如果没有可靠 relation：

```text
会变成 noisy guess
```

需要用 production history 校准。

---

# 73. Reliability Policy 需要 Ownership

谁定义 SLO？

谁改 target？

谁拥有 alert？

谁决定 freeze rollout？

谁处理长期 reliability debt？

如果答案是：

```text
大家
```

通常等于：

```text
没人
```

M02 的 ownership 再次出现。

---

# 74. SLO 不是 SRE-only Artifact

SLO target 包含：

```text
user expectation
product tradeoff
engineering cost
business consequence
```

所以它不是 infra engineer 单方面挑出来的数字。

技术团队可以提供 feasibility / cost evidence。

但 target 本身通常包含 product decision。

---

# 75. SLO 不应该等于当前 Performance

如果当前系统：

```text
99.9999%
```

直接写：

```text
SLO=99.9999%
```

可能把偶然超额表现变成永久 contract。

更合理是先问：

```text
用户需要多少？
更高可靠性值得多少成本？
```

---

# 76. SLO 也不应该是 Wishful Target

反过来：

```text
我们想显得可靠
→ 99.99999%
```

如果系统 architecture 根本无法支持：

SLO 只是墙上的愿望。

因此需要：

```text
measurement
capacity
failure model
architecture
```

共同支撑。

---

# 77. Multiple SLOs 也可能冲突

例如：

```text
latency SLO
correctness SLO
freshness SLO
```

为了 latency：

```text
serve stale cache
```

可能损害 freshness。

所以 reliability 不是把每个 SLO 单独 maximization。

而是 product-level tradeoff。

---

# 78. Degraded Success

一个 response 可能：

```text
HTTP 200
```

但用户实际上没得到完整服务。

例如：

```text
fallback result
partial data
stale result
```

因此 SLI 可能需要区分：

```text
full success
degraded success
failure
```

而不是只按 status code。

---

# 79. Correctness SLI 很难

latency 容易测。

correctness 常常困难：

```text
你怎么知道结果本身对？
```

可能需要：

```text
known-answer probes
reference implementation sampling
cross-check
invariant validation
```

这与 M03 property/reference testing 非常相似。

---

# 80. Telemetry 自己也会失败

监控系统可能：

```text
lag
sample
drop
partition
misaggregate
```

所以：

```text
no alert
```

不等于：

```text
no incident
```

高重要系统需要考虑：

```text
monitoring the monitoring
```

但不要递归到无限层。

---

# 81. Telemetry Loss 与 Product Failure 可能相关

最危险的是：

```text
系统 overload
↓
telemetry exporter 也 overload
↓
bad requests 最容易丢 observation
```

这会产生 correlated blind spot。

所以 measurement architecture 也值得 failure analysis。

---

# 82. Cardinality Incident 本身也是 Production Failure

一个新 release 增加：

```text
user_id label
```

可能导致：

```text
metrics backend memory explosion
query timeout
alert evaluation lag
```

于是：

> instrumentation change 可以成为 outage root cause。

所以 M10 review 应该把 telemetry schema 当 production code review。

---

# 83. Instrumentation Review Questions

每个新 metric 问：

```text
What question does it answer?
What action uses it?
Unit?
Counter/gauge/histogram semantics?
Labels bounded?
Expected cardinality?
What does missing mean?
Who consumes it?
How long does it need to exist?
```

每个 event 问：

```text
Event identity stable?
Correlation fields?
Sensitive data?
Volume?
Schema evolution?
```

---

# 84. Alert Review Questions

```text
Symptom or cause?
User impact?
Urgency?
Actionable?
False-positive cost?
False-negative cost?
Window?
Reset behavior?
Owner?
Runbook / first action?
```

---

# 85. Dashboard Review Questions

Dashboard 不是墙纸。

至少问：

```text
Who uses it?
During normal operation or incidents?
Which decisions?
Which user journey?
Which time scale?
What comparison baseline?
```

如果没有用户：

```text
delete it
```

可能比维护它更好。

---

# 86. Production Incident Evidence

incident 中最好记录：

```text
impact start/end
SLI/budget impact
scope
mitigations
key timeline
hypotheses rejected
root/contributing causes
```

不是为了写漂亮 postmortem。

而是为了让后续：

```text
architecture
testing
alerts
runbooks
```

获得真实反馈。

---

# 87. Postmortem 不属于“谁犯错了”

如果 root cause 被写成：

```text
engineer forgot X
```

工程问题通常还没解释完。

更有价值的问题：

```text
为什么一个普通 mistake 能产生这么大 blast radius？
为什么 review/test/rollout 没挡住？
为什么 detection 这么晚？
为什么 mitigation 困难？
```

这把 production feedback 重新送回 M03–M10。

---

# 88. Reliability Loop

完整 loop：

```text
contract
 ↓
design
 ↓
tests/review
 ↓
rollout
 ↓
production evidence
 ↓
incident / SLO history
 ↓
new understanding
 ↓
contract/design/test changes
```

Software Engineering 不是 deployment 前结束。

---

# 89. Agent 时代的新风险：Instrument Everything

Agent 非常容易生成：

```text
100 counters
50 log lines
20 spans
```

代码生成成本极低。

但 telemetry cost 没降低：

```text
backend cost
schema entropy
operator cognition
alert fatigue
privacy risk
```

所以 Agent instrumentation 需要比以前更强的 evidence discipline。

---

# 90. Agent 常见失败模式 1：Metric for Every Branch

Agent：

```python
if error:
    metric_error_x.inc()
```

每个 branch 一个 metric。

结果：

```text
metric zoo
```

更好的问题：

```text
是否应该一个 bounded reason label？
哪个 aggregation 对 diagnosis 有意义？
```

---

# 91. Agent 常见失败模式 2：Unique ID Labels

Agent 为了“可追踪”：

```text
job_id
request_id
user_id
```

全部塞 metric label。

短期 demo 很好。

production cardinality disaster。

---

# 92. Agent 常见失败模式 3：Alert Every Error

每个 exception：

```text
page
```

结果：

```text
expected validation failure
client misuse
transient retry
real outage
```

全部同等级。

失去 signal。

---

# 93. Agent 常见失败模式 4：Logging Sensitive Context

为了 debug：

```text
full request
headers
token
command
user content
```

全部 log。

这是严重边界错误。

---

# 94. Agent 常见失败模式 5：Telemetry Changes Hidden in Refactor

Agent 做 refactor 顺手：

```text
rename metric
change event field
change error reason
```

作者说：

```text
no behavior changes
```

但 observability consumers 已经被破坏。

M10 的 review model 应把 telemetry 也列入 change surface。

---

# 95. Agent 常见失败模式 6：Dashboard-driven SLO

Agent 看现有指标：

```text
现有 p99=350ms
```

自动建议：

```text
SLO p99 < 400ms
```

这只是 current performance + margin。

不是 user requirement。

---

# 96. Agent 常见失败模式 7：False Confidence from Simulation

Agent 构造 synthetic load：

```text
全部通过
```

然后宣称：

```text
production ready
```

但 simulation 可能没有：

```text
real traffic distribution
real dependency behavior
real retries
real failure correlations
```

Simulation 是 evidence。

不是 production truth。

---

# 97. 给 Agent 的 Observability Task Contract

不要只说：

> 给这个服务加完整监控。

更好的任务：

```text
Goal:
  measure whether accepted jobs begin within 2s.

SLI specification:
  authoritative submit→first-claim latency.

Constraints:
  - metric labels must be bounded;
  - no command/user content in telemetry;
  - job_id may appear in diagnostic events, not aggregate metric labels;
  - preserve existing event/metric consumers unless migration is explicit;
  - do not add paging rules until user-impact semantics are defined.

Evidence:
  - deterministic burst fixture;
  - normal + overload windows;
  - expected series cardinality;
  - missing-event behavior;
  - compatibility review.
```

这才是 agentic SE。

---

# 98. TaskForge M11 Lab 的目标

你将面对：

```text
all tests green
all 12 jobs succeed
ending queue = 0
```

但：

```text
only 2/12 start within 2s
```

你的任务不是：

```text
加更多 print
```

而是：

1. 写 user-centered SLI specification；
2. 判断现有 dashboard 的 blind spot；
3. 设计 bounded telemetry；
4. 保留高-cardinality correlation 在合适 signal；
5. 定义 SLO 与 measurement semantics；
6. 区分 page symptom 与 diagnostic cause；
7. 给出 overload mitigation reasoning；
8. 让 Agent 实现后独立 review。

---

# 99. 一个推荐的 SLI 形式

例如：

```text
Total:
  every accepted submission in the observation window

Good:
  first authoritative claim_at - accepted_at <= 2.0s

Bad:
  accepted but claimed later than 2.0s

Unknown:
  accepted but measurement window ends before authoritative result;
  do not silently drop; report separately and define policy
```

注意：

```text
unknown
```

是否算 bad 需要 contract 决定。

---

# 100. 一个更好的 Metric Model

而不是：

```text
job_start_seconds{job_id=...}
```

可以考虑：

```text
taskforge_job_start_total{outcome="within_target"}
taskforge_job_start_total{outcome="late"}
```

或 latency histogram：

```text
taskforge_job_start_latency_seconds_bucket{worker_pool=...}
```

labels 只保留 bounded dimensions。

---

# 101. 一个更好的 Diagnostic Event

```json
{
  "event": "job_claimed",
  "job_id": "job-12",
  "wait_seconds": 11.45,
  "worker_pool": "default",
  "outcome": "late"
}
```

这可以用于：

```text
查具体 job
关联 submit/finish
incident debugging
```

而不要求 metric backend 为每个 job 建独立 series。

---

# 102. Alert Design Example

坏设计：

```text
queue_depth > 10
→ page
```

为什么坏？

因为：

```text
不知道用户是否受影响
不知道是否持续
不知道是否需要人现在处理
```

更合理：

```text
start-latency SLO burn exceeds urgent threshold
→ page
```

并把：

```text
queue depth
oldest age
worker utilization
arrival/service rate
```

附在 diagnosis context。

---

# 103. 什么时候 Cause Alert 也合理？

如果 cause signal 与 imminent failure 有非常可靠关系，而且必须在人看到 user impact 前行动：

```text
disk 99.9% full
certificate expires in 2h
replication quorum at immediate risk
```

cause-based alert 可以非常合理。

所以不是：

```text
never alert on causes
```

而是：

> **cause alert 也必须有明确 urgency + action contract。**

---

# 104. Reliability 不是 Dashboard Quality

一个 dashboard 可以非常漂亮：

```text
20 panels
heatmaps
traces
animated topology
```

仍然无法回答：

```text
用户现在好吗？
```

反过来，一个非常简单的：

```text
SLO burn
queue oldest age
release marker
```

可能已经足以做关键决策。

---

# 105. Evidence Coverage Matrix

对于重要 behavior，列：

| Question | Pre-prod evidence | Prod evidence |
|---|---|---|
| FIFO semantics | unit/property tests | start-order event sampling |
| retry duplicate effect | deterministic failpoint | dedup/conflict counters + incidents |
| snapshot compatibility | fixtures | version-use telemetry |
| remote worker latency | integration test | end-to-end SLI |
| capacity | benchmark | saturation + queue age |

Production evidence 不替代 tests。

Tests 也不替代 production evidence。

---

# 106. Reliability 是一个多层 Contract

```text
Product:
  user outcome target

System:
  architecture/failure behavior

Operational:
  detection/action policy

Organizational:
  who owns decisions
```

只优化一层会产生错位。

---

# 107. 本章的最小 Reliability Argument

对于一次 production-facing change，至少可以问：

```text
1. What user behavior matters?
2. How is it measured?
3. What can the measurement miss?
4. What target defines acceptable service?
5. What production failure modes threaten it?
6. What signals distinguish symptom from likely causes?
7. What condition requires urgent human action?
8. What is the rollout/rollback evidence?
9. What telemetry cost/compatibility/security risks exist?
```

不需要每个 PR 写 9 页文档。

但高风险 change 必须有人能回答。

---

# 108. Production-ready 是一个危险词

```text
production-ready
```

如果没有展开，信息量很低。

最好拆成：

```text
correctness evidence
load/capacity evidence
failure evidence
compatibility evidence
observability evidence
rollout strategy
operational ownership
```

Agent 特别容易使用“production-ready”作为 summary adjective。

Reviewer 不应接受形容词代替 evidence。

---

# 109. 本章与前面模块的关系

```text
M01:
  SLI 首先是 contract definition

M02:
  telemetry / alert / SLO 也需要 ownership

M03:
  production metrics 是另一种 evidence，不是 proof

M04:
  retry/rejection/load shedding 都需要 public semantics

M05:
  instrumentation change 也要 preserve observable contracts

M06:
  legacy takeover 可先 characterize production behavior

M07:
  concurrency/crash/retry 在 production 里形成真实 failure history

M08:
  telemetry schema 也有 compatibility/migration

M09:
  observability placement 受 architecture/failure domain 决定

M10:
  production evidence 是 change review 的一部分
```

---

# 110. 一个更完整的 Engineering Loop

到 M11，我们终于可以写出：

```text
Understand
  ↓
Specify
  ↓
Design
  ↓
Implement
  ↓
Test
  ↓
Review
  ↓
Roll out
  ↓
Observe
  ↓
Learn
  ↓
Change again
```

这才是持续存在的软件系统。

---

# 111. 最终判断题

## A

```text
100% requests success
p99 latency 30s
```

健康吗？

答案：

> 取决于用户 latency contract；success ratio 单独不足以判断。

## B

```text
CPU 95%
SLO 全部满足
```

要 page 吗？

答案：

> 不一定；需要证明 urgency 与 operator action。

## C

```text
job_id 非常适合定位问题
```

所以应该放 metric label？

答案：

> 不一定；诊断价值与 aggregation/cardinality suitability 是两个问题。

## D

```text
dashboard 最终 queue=0
```

说明 burst 没有伤害用户？

答案：

> 不成立；final state 可能擦掉历史 wait latency。

## E

```text
没有 page
```

说明 production 没事故？

答案：

> 不成立；可能是 alert blind spot 或 telemetry failure。

---

# 112. 本章结束后你应该能做什么

你应该能：

- 从 user journey 而不是现有 metrics 出发定义 SLI；
- 区分 SLI specification 与 measurement implementation；
- 识别 denominator / placement / missing-event blind spot；
- 判断 metrics / events / traces 分别适合什么问题；
- 识别 high-cardinality telemetry design；
- 把 telemetry schema 当 compatibility surface；
- 区分 symptom、cause、leading、lagging signals；
- 设计有 action contract 的 alerts；
- 用 error budget / burn rate 而不是单点 threshold 推理 urgency；
- 把 overload/backpressure/load shedding 放进 reliability model；
- 把 rollout 和 production evidence 纳入 correctness argument；
- 对 Agent 生成的 instrumentation 做独立 semantic/cost/security review。

下一章 M12 会把这些能力直接用于 Agentic Software Engineering：

> 当 implementation bandwidth 极高时，怎样让 Agent 探索、设计、实现、测试、review、运行与修复，同时保持 human engineering authority。
