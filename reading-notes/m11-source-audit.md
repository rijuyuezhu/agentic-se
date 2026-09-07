# M11 Source Audit — Production、Observability 与 Reliability

> 目标：不是搜集“可观测性最佳实践”口号，而是确认哪些一手材料真正支持本模块要教的工程判断。
>
> 本模块关心的不是 Prometheus / Grafana / OpenTelemetry 的操作教程，而是：
>
> - 什么 production behavior 值得测；
> - SLI specification 与 measurement implementation 如何区分；
> - 为什么 symptom 与 cause 不能混成同一个 alert；
> - error budget 到底在管理什么；
> - telemetry schema 本身为什么也是长期工程接口；
> - cardinality、sampling、alert noise、backpressure 为什么属于 reliability design；
> - Agent 生成 instrumentation 时最容易犯什么错误。

---

## 1. Google SRE — Service Level Objectives

Primary source:

- https://sre.google/sre-book/service-level-objectives/

实际检查的内容：

- SLI 是对 service level 某个方面的 quantitative measure；
- SLO 是 SLI 的 target value / range；
- 常见 SLI 包括 latency、error rate、throughput，但重点不是“有哪些现成指标”，而是哪些行为对用户重要；
- objectives 应先从 users care about what 开始，而不是先从“现在最容易测什么”开始；
- 100% reliability 通常既不现实也不理想；
- error budget 允许在 reliability 与 change velocity 之间做数据化权衡；
- SLO 应明确 measurement conditions，而不是只写一个漂亮百分比。

### 本课程采用

1. **用户结果优先于组件健康。**

   `database_cpu < 70%` 不是天然 SLI；它可能是 useful cause signal，但用户通常在乎的是 request 是否成功、是否及时、结果是否新鲜/正确。

2. **SLI 与 SLO 分开。**

   ```text
   SLI = measurement / indicator
   SLO = target over that indicator
   ```

3. **100% 不是默认目标。**

   reliability 是 product / business / engineering tradeoff，不是越高越好且无代价。

4. **error budget 是 decision input，不是错误额度 KPI。**

   它服务于“现在还能承受多少 change risk / reliability debt”之类决策。

### 本课程不升级为普遍定律

- “所有系统必须有正式 SLO 才能上线”；
- “所有 SLI 都必须是 request success ratio”；
- “所有团队都应该复制 Google 的 target 数值”；
- “error budget 用完就永远必须 freeze feature work”。

这些都依赖组织、服务重要性、成本和治理方式。

---

## 2. Google SRE Workbook — Implementing SLOs

Primary source:

- https://sre.google/workbook/implementing-slos/

这是本模块最关键的来源之一。

实际检查到：

- 推荐把 SLI 常写成 `good events / total events`；
- 明确区分 **SLI specification** 与 **SLI implementation**；
- 同一个 specification 可以由 server logs、probers、client instrumentation 等不同方式实现；
- 每种 implementation 都有 quality / coverage / cost tradeoff；
- availability / latency 只是常见起点，freshness、durability、correctness、quality、coverage 等也可能是重要 SLI；
- 建议从 critical user journeys / user-centric actions 思考；
- 可以先用便宜可行的 measurement，再持续迭代，不要求第一版完美；
- 复杂系统中 SLI implementation 本身也可能漏掉请求或产生 measurement blind spot。

### 本课程采用

核心区分：

```text
SLI specification:
  我们真正想知道什么？

SLI implementation:
  现在具体用什么 telemetry 近似它？
```

例如 TaskForge：

```text
Specification:
  submitted job 是否在 2 秒内开始执行？

Possible implementations:
  A. service-side submit timestamp + worker claim timestamp
  B. client-observed submit-to-running polling latency
  C. synthetic job probe
```

三个 implementation 都可能测“同一个用户关心的现象”，但 blind spot 不同。

### 特别重要的限制

我们不会把“good events / total events”当成唯一 SLI 形式。

它对 request-driven systems 很方便，但：

- queue age；
- backlog oldest age；
- batch completion deadline；
- data freshness；
- durability loss；

可能需要不同的 measurement model。

---

## 3. Google SRE — Monitoring Distributed Systems

Primary source:

- https://sre.google/sre-book/monitoring-distributed-systems/

实际检查：

- four golden signals：latency、traffic、errors、saturation；
- successful 与 failed request latency 应区分，否则快速失败可能让总体 latency 看起来更好；
- monitoring 应服务于诊断与用户影响判断；
- cause-oriented internal metrics 与 user-facing symptom 不应混淆。

### 本课程采用

把 four golden signals 当作**排查遗漏的 heuristic**，不是 dashboard 模板。

例如 TaskForge：

```text
traffic      = submitted jobs / second
latency      = submit → claim, claim → finish
errors       = rejected/failed jobs or SLI-bad events
saturation   = queue age / queue depth / worker utilization
```

但如果用户最关心的是 data freshness，四个词本身仍不足够。

### 重要纠偏

```text
symptom metric
!=
cause metric
```

例如：

```text
symptom:
  40% jobs wait > 2s before start

possible causes:
  worker saturation
  dependency slowdown
  retry storm
  scheduler bug
```

Page 应优先由用户影响驱动；cause signal 更适合 diagnosis / routing / enrichment。

---

## 4. Google SRE Workbook — Alerting on SLOs

Primary source:

- https://sre.google/workbook/alerting-on-slos/

实际检查：

- alert 应围绕 significant threats to error budget；
- burn rate 是相对 SLO 允许错误率的预算消耗速度；
- 单窗口 threshold 有 detection / reset / precision / recall tradeoff；
- multi-window, multi-burn-rate 是 Google 推荐的一个实用模式；
- page 与 ticket 的 urgency 应不同；
- 参数只是起点，需要根据 service 和 on-call load 调整。

### 本课程采用

不要求学生背 `14.4x` / `6x`。

真正要学的是：

```text
alert threshold
必须对应：
  user impact
  budget consumption
  response urgency
  actionable operator decision
```

如果 alert 触发后 operator 不知道该做什么，或者无需现在行动，那么它很可能不该 page。

### 本课程明确拒绝

- 每个 metric threshold 都配 pager；
- CPU 80% 必须报警；
- 固定 burn-rate 数值适用于所有服务；
- alert 数量越多 coverage 越好。

---

## 5. Google SRE — Production Services Best Practices

Primary source:

- https://sre.google/sre-book/service-best-practices/

实际检查到 monitoring outputs 的一个强 framing：

- Page：人现在必须做事；
- Ticket：几天内需要行动；
- Logging：当前不要求人立刻行动，保留供分析。

以及 error budget 可作为 release / reliability policy 的治理机制。

### 本课程采用

把 notification channel 看成**action contract**：

```text
page
= there is an urgent human action now
```

不是：

```text
page
= metric exceeded an arbitrary threshold
```

这与 M04 的 API contract、M10 的 review claim 一脉相承：alert 也是一个 boundary contract。

---

## 6. Google SRE — Handling Overload

Primary source:

- https://sre.google/sre-book/handling-overload/

实际检查：

- overload 最终不可避免，系统必须设计 graceful handling；
- degraded responses / load shedding 可能比让整个系统 collapse 更可靠；
- capacity 与 demand mismatch 是 production reliability 的核心问题，而不是单纯 performance tuning。

### 本课程采用

M11 不深入排队论，但明确：

```text
queue depth growth
queue age growth
worker saturation
rejection/load shedding
```

不是“性能指标附录”，而是 failure prevention signal。

特别是：

```text
accepted request
!=
useful service delivered in time
```

TaskForge 的 production lab 会用这个差异作为主场景。

---


## 7. Google SRE — Addressing Cascading Failures / Retry Amplification

Primary sources:

- https://sre.google/sre-book/addressing-cascading-failures/
- https://sre.google/sre-book/service-best-practices/

实际检查：

- retries 会把已经存在的 overload 放大成更多 traffic；
- automatic retries 需要 randomized exponential backoff 等机制来降低同步放大；
- overload 时不能把 retry 当成“免费恢复动作”，因为 retry 自己也消耗 downstream capacity；
- graceful degradation、load shedding 与 upstream traffic reduction 都可能是从 cascading failure 中恢复的手段；
- 具体 retry 次数、timeout、backoff 参数取决于 service contract、capacity、deadline、idempotency 与 failure semantics。

### 本课程采用

M11 把 retry 看成 **load-producing reliability mechanism**。如果新请求持续到达，而每个 timeout 都立即 retry，那么 attempts 可以在 downstream capacity 不变时持续增长；这正是 `m11_retry_storm_probe.py` 要稳定复现的 failure shape。

课程要求学生比较：

- naive immediate retry；
- bounded retry budget；
- backoff / jitter / caller throttling 等候选 mitigation；
- rejection / load shedding 与 retryability contract 的关系。

### 不升级成课程规则

- 不把某个固定 backoff base、retry count 或 jitter algorithm 写成 universal answer；
- 不声称“所有 timeout 都应该 retry”；
- 不声称 backoff 本身能创造 capacity 或解决 non-idempotent duplicate effects；
- 不把教学 probe 的离散 round 当成 TaskForge 真实 throughput benchmark。

---
## 8. Prometheus — Instrumentation Best Practices

Primary sources:

- https://prometheus.io/docs/practices/instrumentation/
- https://prometheus.io/docs/practices/naming/

实际检查：

- labelset 的每个不同组合都会形成独立 time series；
- labels 有 CPU / RAM / storage / network 成本；
- 官方明确警告不要过度使用 labels；
- user IDs、email 等高/无界 cardinality 值不应直接做 metric label；
- instrumentation 页面给出了低 cardinality 的经验性 guideline，但其数值显然是 Prometheus-specific operational guidance，不是抽象软件定律。

### 本课程采用

最重要的原则：

```text
metric dimensions
是一个数据模型设计决定
```

而不是“想 debug 什么就把什么塞 label”。

例如：

```text
BAD for metrics:
job_id="job-8472391"
request_id="..."
command="python huge unique command..."
```

因为这会让 time-series cardinality 随 workload 增长。

更适合：

```text
metric labels:
  outcome
  worker_pool
  operation
  bounded reason code

logs/traces/events:
  job_id
  request_id
  causal detail
```

这不是“metrics 永远不能高 cardinality”的绝对规则，而是提醒不同 telemetry signal 的成本结构不同。

### 不采用的机械规则

Prometheus 文档里的具体 cardinality 数字只作为该生态的 guideline，不会升级成跨平台定律。

---

## 9. OpenTelemetry — Signals / Logs Data Model / Semantic Conventions

Primary sources:

- https://opentelemetry.io/docs/concepts/signals/
- https://opentelemetry.io/docs/specs/otel/logs/data-model/
- https://opentelemetry.io/docs/concepts/semantic-conventions/
- https://opentelemetry.io/docs/specs/semconv/

实际检查：

- OTel 当前 signal overview 将 trace 描述为 request 穿过 application/components 的 path，将 metric 描述为 runtime measurement，将 log 描述为 event record；
- 这些 signal 可以从不同角度观察同一系统活动，但没有说“每个问题都必须同时使用所有 signals”；
- OTel log data model 试图给不同来源的日志一个共同、可映射的数据模型；
- `Timestamp`、`TraceId`、`Severity`、`Body`、`Attributes` 等字段有明确角色；
- `EventName` 可标识 event type / event schema；
- semantic conventions 的价值是让 traces、metrics、logs、resources 使用一致命名和语义，便于跨组件消费和关联；
- semantic conventions 自身有稳定性状态，不同部分可能处于 Development / Stable 等阶段。

### 本课程采用

核心不是要求全员采用 OTel，而是保留两条可迁移 reasoning：

1. **signal shape 要由 failure question 决定。** Metric 适合 runtime measurement/aggregation；log/event 适合保留离散 observation；当要恢复 logical request/job 穿过多个 instrumented component 的 path/timing 时，trace 才提供不同 evidence。课程不会把三者写成 maturity ladder，也不会要求每个 failure 三种 signal 齐全。
2. **Telemetry schema 也是 interface。**

如果一个 `job_finished` event 今天：

```json
{"status": "failed", "worker": "pool-a"}
```

明天未经 migration 变成：

```json
{"result": "error", "executor": "pool-a"}
```

那么 dashboards、alerts、incident queries、offline analysis 都可能成为 downstream consumers。

这就是 M08 compatibility 在 observability 世界里的再次出现。

### 不采用

- “用了 OpenTelemetry 就获得 observability”；
- “所有 log 都必须 structured”；
- “trace 每个函数”；
- “semantic convention 永远稳定”。

---

## 10. Prometheus — The Zen of Prometheus

Primary source:

- https://prometheus.io/docs/practices/the_zen/

实际检查：

- 强调 measure what users care about；
- 明确提醒 cardinality matters；
- instrumentation 应尽早考虑。

这份材料语言更像 community guidance，不是 formal specification。

### 本课程的使用方式

只把它作为 Prometheus 社区经验，与 Google SRE 的 user-centered SLI 思路相互校验。

不会把“instrument all the things”解释成“记录所有字段”。

事实上，同一页也强调 cardinality cost，所以更准确的综合理解是：

```text
instrument important behavior broadly
but choose signal shape deliberately
```

---

## 11. Google SRE — Postmortem Culture / Incident Learning

Primary sources:

- https://sre.google/sre-book/postmortem-culture/
- https://sre.google/workbook/postmortem-culture/

实际检查：

- postmortem 是 incident 的书面记录，覆盖 impact、mitigation/response、root/contributing causes 与 follow-up actions；
- blamelessness 的重点是分析允许失败发生和扩大的 system/process conditions，而不是把“某个人犯错”当技术 root cause；
- 高质量 action item 应有可验证的完成状态，并面向 prevention / mitigation，而不是只要求“以后更小心”；
- incident learning 不只修 immediate trigger，也会反哺 detection、mitigation、coordination、communication、training 与 architecture；
- 写完文档不是闭环，action-item closeout 才把 learning 变成 system change。

### 本课程采用

M11 要求一份 **blameless but technically precise** postmortem。最低应恢复：

- user impact 与时间线；
- SLI/SLO 或其他 production evidence 如何显示影响；
- trigger、root/contributing conditions 与 retry/overload amplification；
- 哪些 detection / mitigation / review assumptions 失败；
- 可验证的 follow-up actions 与 owner/evidence。

### 不升级成课程规则

- 不要求每个轻微 bug 都写正式 postmortem；
- 不要求使用 Google 的组织流程或模板；
- blameless 不等于技术描述含糊，也不等于不讨论 decision/process failure；
- postmortem 不能把 correlation 自动写成 root cause，也不能用“operator error”结束分析。

---

## 12. Google SRE — Simplicity / Operational Simplicity

Primary sources:

- https://sre.google/sre-book/simplicity/
- https://sre.google/workbook/simplicity/

实际检查：

- SRE Book 把 simplicity 与 reliability/stability 直接联系，并强调 release/change 的可理解性与可测量性；
- SRE Workbook 更明确地把 simplicity 作为 end-to-end goal，范围不只包括 code，也包括 system architecture、tools 与 software-lifecycle processes；
- complexity 会增加理解、维护、测试、变更和运行成本，而且某个局部 change 引入的 complexity 可能成为由其他团队/后续维护者承担的 externality；
- retry 本身就是 workbook 用来说明 end-to-end complexity 的例子之一：一个局部看似简单的 recovery mechanism 可能让整体 path/load 更难推理。

### 本课程采用

M11 的 bounded claim 是：**operational simplicity 是 reliability reasoning 的一个重要维度。** 新 instrumentation、alert、fallback、retry path、deployment step 或 operator workflow 都会增加需要理解、测试、运行和恢复的 surface；只有当它带来的 evidence/mitigation value 值得这些成本时才应保留。

### 不升级成课程规则

- tool count 与 reliability 没有简单的单调关系；少一个工具可能减少 surface，也可能失去必要 evidence / control；
- process / component count 与 reliability 也没有自动关系；redundancy、isolation、failure domain 与 dependency shape 仍需单独分析；
- 不把 LOC、service count 或 dashboard panel count 当 reliability metric；
- 不把“boring/simple”当拒绝必要 redundancy、isolation、telemetry 或 failure handling 的借口。

---

# 13. 交叉验证后的 M11 核心模型

这些来源共同支持一个比“装监控工具”更稳定的 model：

```text
User / Product expectation
        ↓
SLI specification
        ↓
measurement implementation
        ↓
telemetry model / aggregation / missingness
        ↓
SLO / budget / threshold
        ↓
notification + action contract
        ↓
overload / retry / mitigation behavior
        ↓
incident evidence
        ↓
postmortem learning + verifiable follow-up
```

每一层都可能错。

例如：

```text
正确 telemetry
+ 错 SLI specification
= 精确地测错东西
```

```text
正确 SLI
+ 漏请求的 implementation
= measurement blind spot
```

```text
正确 metric
+ 错 alert threshold
= noisy page / missed incident
```

```text
好 metric
+ job_id label
= cardinality incident
```

所以 M11 的 reliability model 不止是 observability：它把 **semantic design + measurement design + operational action + failure amplification + incident learning** 连成一个 loop。

---

# 14. 本模块刻意不依赖的内容

以下材料可能有价值，但本轮不把它们当 authority：

- vendor-specific observability maturity models；
- “three pillars” 作为完整 observability 定义；
- Honeycomb / Datadog / Grafana 的产品营销材料；
- arbitrary RED / USE checklist 作为普遍模板；
- fixed SLO target，例如“所有 API 都 99.99%”；
- fixed alert threshold；
- fixed sampling percentage；
- distributed tracing 不是默认上线义务；只有 failure question 需要跨组件 path/timing evidence 时，才需要为它支付 instrumentation、propagation、sampling 与 storage 成本。

原因不是这些内容一定错，而是本课要教的是可迁移的 engineering reasoning。

---

# 15. 对 TaskForge M11 的直接影响

M11 starter / teaching probes 应体现：

1. **所有 core tests 可以继续绿；**
2. 所有 jobs 最终甚至可以 `SUCCEEDED`，final queue depth 也可以回到 0；
3. 但 burst workload 中很多 job 的 `submit → claim` 已经超过教学 latency target；
4. naive dashboard 因为只看 final success / ending queue depth，会判断 healthy；
5. user-centered SLI 会判断明显 degraded；
6. naive metrics 若把 `job_id` 作为 label，会制造 workload-proportional cardinality；
7. useful logs/events 可以保留 `job_id` 作为 diagnosis correlation key；trace 只有在跨组件 path/timing 是问题时才提供不同 evidence；
8. Lab 必须把 signal-selection reasoning 迁移到 **慢 / 无进展 / 数据不一致**，并为每类说明 metric、event/log、trace 的适用问题与 sampling/missingness limitation；
9. 数据不一致 transfer 必须先声明 authority/read surface 与 freshness/consistency boundary，不能把任意 temporal staleness 自动判成 inconsistency；
10. page 不应直接由 `queue_depth > N` 这种 cause threshold 定义，除非它确实对应紧急、可行动的 user impact；
11. retry-storm teaching probe 要稳定展示 retries 如何在 capacity 不变时增加 attempts，同时明确它不是 production benchmark；
12. Lab 要把 overload/retry evidence 延伸到 incident timeline 与 blameless/technically precise postmortem，而不是停在 dashboard design；
13. operational simplicity 要作为 reliability tradeoff 检查，但不升级成 fewer tools/components automatically better。

这使 M11 能自然复用：

- M01：先定义正确性 / contract；
- M03：evidence 不等于 proof；
- M07：overload / failure propagation；
- M09：failure domain / system view；
- M10：不要相信作者/Agent 自己声称“production-ready”。

---

# 16. Module-level claims 与来源边界

本模块会使用下列课程综合术语，它们不是某一个来源的逐字定义：

```text
observability contract
measurement blind spot
failure-question -> signal-shape transfer
signal placement
telemetry schema as interface
operational action contract
production evidence chain
retry amplification teaching model
operational simplicity as a review dimension
reliability learning loop
```

这些是对上述一手材料的课程级 synthesis。

明确区分 source claim 与 course synthesis，避免把课程自己的框架错误归因给 Google / Prometheus / OTel。
