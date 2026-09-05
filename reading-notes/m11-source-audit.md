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

## 7. Prometheus — Instrumentation Best Practices

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

## 8. OpenTelemetry — Logs Data Model / Semantic Conventions

Primary sources:

- https://opentelemetry.io/docs/specs/otel/logs/data-model/
- https://opentelemetry.io/docs/concepts/semantic-conventions/
- https://opentelemetry.io/docs/specs/semconv/

实际检查：

- OTel log data model 试图给不同来源的日志一个共同、可映射的数据模型；
- `Timestamp`、`TraceId`、`Severity`、`Body`、`Attributes` 等字段有明确角色；
- `EventName` 可标识 event type / event schema；
- semantic conventions 的价值是让 traces、metrics、logs、resources 使用一致命名和语义，便于跨组件消费和关联；
- semantic conventions 自身有稳定性状态，不同部分可能处于 Development / Stable 等阶段。

### 本课程采用

核心不是要求全员采用 OTel，而是：

> **Telemetry schema 也是 interface。**

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

## 9. Prometheus — The Zen of Prometheus

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

# 10. 交叉验证后的 M11 核心模型

这些来源共同支持一个比“装监控工具”更稳定的 model：

```text
User / Product expectation
        ↓
SLI specification
        ↓
measurement implementation
        ↓
telemetry model
        ↓
aggregation / window
        ↓
SLO / budget / threshold
        ↓
notification policy
        ↓
human or automated action
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

所以 observability 是 **semantic design + measurement design + operational action design**。

---

# 11. 本模块刻意不依赖的内容

以下材料可能有价值，但本轮不把它们当 authority：

- vendor-specific observability maturity models；
- “three pillars” 作为完整 observability 定义；
- Honeycomb / Datadog / Grafana 的产品营销材料；
- arbitrary RED / USE checklist 作为普遍模板；
- fixed SLO target，例如“所有 API 都 99.99%”；
- fixed alert threshold；
- fixed sampling percentage；
- “所有服务必须 distributed tracing”。

原因不是这些内容一定错，而是本课要教的是可迁移的 engineering reasoning。

---

# 12. 对 TaskForge M11 的直接影响

M11 starter 应体现：

1. **所有 tests 可以继续绿；**
2. 所有 jobs 最终甚至可以 `SUCCEEDED`；
3. final queue depth 可以回到 0；
4. 但 burst workload 中很多 job 的 `submit → claim` 已经超过用户容忍阈值；
5. naive dashboard 因为只看 final success / ending queue depth，会判断 healthy；
6. user-centered SLI 会判断明显 degraded；
7. naive metrics 若把 `job_id` 作为 label，会制造 workload-proportional cardinality；
8. useful logs/events 可以保留 `job_id` 作为 diagnosis correlation key；
9. page 不应直接由 `queue_depth > N` 这种 cause threshold 定义，除非它确实对应紧急、可行动的 user impact。

这使 M11 能自然复用：

- M01：先定义正确性 / contract；
- M03：evidence 不等于 proof；
- M07：overload / failure propagation；
- M09：failure domain / system view；
- M10：不要相信作者/Agent 自己声称“production-ready”。

---

# 13. Module-level claims 与来源边界

本模块会使用下列课程综合术语，它们不是某一个来源的逐字定义：

```text
observability contract
measurement blind spot
signal placement
telemetry schema as interface
operational action contract
production evidence chain
```

这些是对上述一手材料的课程级 synthesis。

明确区分 source claim 与 course synthesis，避免把课程自己的框架错误归因给 Google / Prometheus / OTel。
