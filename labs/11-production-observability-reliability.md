# Lab 11 — 从“全绿 dashboard”到可行动的 Reliability Evidence

> 目标：让一个“core tests 全绿、所有 job 最终成功、queue 最后为空”的 TaskForge workload 暴露 production blind spot；再注入一个 deterministic retry-amplification failure，完成从 user contract → measurement → SLO → overload response → incident → postmortem 的闭环。

本实验不是 Prometheus/Grafana/OpenTelemetry 教程。你可以不安装任何 telemetry SDK。评分关注的是 production semantics、measurement quality、operational action 与独立 evidence。

## 1. Baseline：先确认“看起来健康”与“用户体验很差”同时成立

进入：

```bash
cd labs/taskforge
```

运行 core tests：

```bash
PYTHONPATH=src uv run --with pytest --no-project python -m pytest -q
```

再运行 M11 production probe：

```bash
PYTHONPATH=src uv run --with pytest --no-project \
  python tools/m11_production_probe.py
```

记录两组互相冲突、但都真实的 evidence：

```text
naive dashboard:
  submitted = 12
  success_ratio = 1.0
  ending_queue_depth = 0
  healthy = true

user-centered start-latency SLI:
  good = 2
  bad = 10
  total = 12
  ratio ~= 0.167
  target = 0.990
```

还要记录 starter 的 cardinality trap：12 个 completed jobs 因 `job_id` label 形成 12 个 distinct series identities。

这不是 wall-clock benchmark。不要从 synthetic timeline 推断 TaskForge 真实 throughput；它只是 deterministic teaching fixture。

## 2. 先写 Production Contract，不要先“加监控”

先提交 `production-contract.md`，至少回答下面问题。

### User journey

本实验使用的 primary journey 是：

```text
submit accepted
    -> authoritative job exists
    -> first authoritative claim
    -> explicit completion / failure
```

Primary SLI 只覆盖 `accepted -> first claim`，不声称它代表 TaskForge 全部 reliability。

### SLI specification

课程给出的教学 specification 是：

> applicable accepted job 的 first authoritative claim 是否在 accepted submission 后 2.0 秒内发生？

你必须自己补全：

- applicable cohort / Total 是谁；
- Good / Bad 的判定；
- Unknown / pending 的语义；
- cancel-before-claim 怎么处理；
- observation window 关闭时仍缺 claim evidence 怎么处理；
- duplicate submit/retry 若存在，用什么 logical identity 去重；
- 这项 SLI **没有**覆盖哪些 user journey。

禁止只写 `p99 < 2s` 而不说明 denominator 和 placement。

## 3. 解释 naive dashboard 为什么“数据没错，结论却不够”

完成：

| Signal | 它准确回答什么 | 它系统性回答不了什么 |
|---|---|---|
| eventual success ratio | ? | ? |
| ending queue depth | ? | ? |
| terminal count | ? | ? |

你的解释必须包含一条 history-level 判断：final state 可以擦掉过去用户经历的等待；因此 `ending_queue_depth=0` 不能证明 burst 没有造成 latency harm。

不要把这种情况叫“metric calculation bug”。更精确的 diagnosis 是 measurement model / placement 与 user contract 不匹配。

## 4. 选择 measurement implementation，并公开 blind spots

为同一个 start-latency specification 比较至少三种 placement：

| Candidate | 能覆盖什么 | Blind spot / cost |
|---|---|---|
| service accepted event + worker claim event | ? | ? |
| client-observed `QUEUED -> RUNNING` | ? | ? |
| synthetic end-to-end job | ? | ? |

选择一个 primary implementation，并回答：

- timestamp authority 在哪里；
- 跨进程/跨机器时 clock semantics 怎么处理；
- ingress rejection / client-network delay 是否在 scope；
- telemetry loss 如何显现；
- 谁消费这项 measurement。

Reference direction 可以选择 service/worker event pair，但这不是唯一正确答案。

## 5. Denominator 与 missingness：坏 work 不能因为“没事件”而消失

分析这个错误 SLI：

```text
fast_claimed_jobs / all_claimed_jobs
```

构造一个 accepted-but-never-claimed job，解释为什么它会被 denominator 丢掉。

然后给出你的 explicit policy。至少区分：

```text
accepted + claim evidence within target
accepted + claim evidence late
accepted + no claim evidence yet
telemetry coverage unknown
```

你可以把窗口未关闭的 work 视为 pending；窗口关闭后也可以把 unresolved/unknown 分开报告。允许多种 policy，但禁止 silent drop，也禁止把 unknown 自动算 good。

## 6. 设计 telemetry：aggregate identity 与 diagnostic correlation 分开

至少设计这些 aggregate questions：

- start-latency good/bad/unknown；
- start-latency distribution；
- queue oldest age / backlog pressure；
- bounded cause/outcome cohort；
- retry attempts / timeout amplification（第二阶段使用）。

每个 metric 写：

| Field | Answer |
|---|---|
| semantic question | ? |
| unit / aggregation | ? |
| bounded labels | ? |
| expected cardinality | ? |
| missing semantics | ? |
| likely consumer/action | ? |

硬性要求：`job_id`、request ID、command、arbitrary user string 不进入 aggregate metric labels。

然后设计一个 diagnosis-oriented event，例如：

```json
{
  "event": "job_claimed",
  "job_id": "job-42",
  "wait_seconds": 4.81,
  "worker_pool": "default",
  "outcome": "late"
}
```

`job_id` 可以保留 correlation value，但不得因此推导“适合 metric label”。Event 不能默认记录 command、token、headers 或 arbitrary user content。

### Cardinality negative control

你的实现若包含 aggregate metric identity model，必须比较至少两个 workload：例如 12 jobs 与 120 jobs。若只是增加相同 bounded categories，series identity count 不应按 job 数近似线性增长。

禁止用：

```python
assert "job_id" not in source
```

因为 diagnosis event 正可以合法包含 `job_id`。

### Failure-class transfer：慢 / 无进展 / 数据不一致

提交一个 `failure-signal-matrix.md`。不要再围绕 starter latency case 复述同一套 signals，而是针对三种不同 failure semantics 设计 production evidence：

| Failure class | 你必须定义的 question |
|---|---|
| 慢 | 哪个 user-visible phase 超过 contract，慢发生在哪个 cohort/path？ |
| 无进展 / 像挂住 | accepted work 是否在声明的 progress model 下停止前进？ |
| 数据不一致 | 哪两个 surface / invariant 本应在什么 freshness/consistency boundary 内一致？ |

对每类都回答：

1. 哪个 aggregate metric/SLI 能发现范围或趋势？
2. 哪个 event/log 能保留单个 observation 的 identity、version、source 与局部事实？
3. **什么时候 trace 才提供不同 evidence？** 只有当你需要恢复 logical request/job 跨 process/service/component 的 path/timing 时才选它；不要因为 rubric 写了 trace 就虚构 span。
4. sampling、event loss、clock/freshness semantics 会让什么 conclusion 失效？
5. 哪个 evidence 只支持 correlation/diagnosis，不能单独证明 root cause 或 correctness？

数据不一致可以使用一个明确的 future TaskForge transfer case：假设存在 derived status/read model，并承诺在某 freshness bound 内与 lifecycle authority 一致。设计 bounded mismatch metric；再设计一条 diagnosis event/log，保留 `job_id`、authority version/status、observed version/status 与 source。若 stale read 可能经过多个 service/process，再说明 trace 怎样帮助恢复 serving/replication path；同时明确 trace **不能**决定哪一份状态有 authority。

这里不要求实现 tracing SDK，也不要求为三个 failure class 都新增 executable instrumentation。评分看的是 `failure question → signal choice → limitation` 是否成立。

## 7. Telemetry compatibility：schema 也是 consumer contract

假设已有 dashboard/alert/query 依赖：

```text
job_claimed.outcome
```

新版本想改成：

```text
job_claimed.status
```

写一个 compatibility decision：

- 谁是 consumer；
- 能否直接 break；
- 若不能，Expand / Migrate / Contract 怎么做；
- unknown/new value 如何 fail；
- telemetry retention 是否让旧 schema 继续出现在 query window 中。

不要因为“只是 logs/metrics”而跳过 M08 reasoning。

## 8. 从 SLI 到 SLO、error budget 与 action

教学 SLO 使用：

> 99% applicable accepted jobs 的 first authoritative claim 在 2.0 秒内发生。

你必须补全 measurement window、traffic scope、missing policy、owner 和 review cadence。明确说明 99%/2s 是课程 fixture，不是 external best-practice target。

完成两个 calculation/reasoning task：

1. 对 10,000 applicable events，1% error budget 等于多少 bad events？
2. 如果短窗口 observed bad ratio 很高，如何把 burn rate / window fraction 与 urgency 联系起来？

不要背固定 14.4x/6x。回答应说明 service criticality、traffic representativeness、persistence、operator action 与 on-call cost 为什么影响 alert policy。

## 9. Page、ticket 与 diagnosis signal 必须对应不同 action contract

先分类：

| Signal | User symptom / cause / both | 解释 |
|---|---|---|
| start-latency SLI | ? | ? |
| queue depth | ? | ? |
| queue oldest age | ? | ? |
| worker CPU/utilization | ? | ? |
| retry attempts | ? | ? |
| dependency timeout | ? | ? |
| submit error ratio | ? | ? |

然后设计一个 page-level policy，至少写：

```text
Trigger
User consequence
Urgency
Owner
First action
Diagnostic context
Mitigation options
Stop condition
```

`queue_depth > 10 -> page` 不合格，除非你能证明它和 imminent user impact 以及 immediate action 的关系。

再设计一个非 urgent ticket，例如慢速 budget burn、cardinality growth 或 capacity headroom decline，并解释为什么不该 page。

## 10. 注入 retry storm：恢复机制为什么也能制造事故

运行：

```bash
PYTHONPATH=src uv run --with pytest --no-project \
  python tools/m11_retry_storm_probe.py
```

这个 teaching model 中，每轮有 8 个新 logical requests，dependency capacity 是 4。Naive policy 会把每个 timed-out attempt 在下一轮立即 retry，因此 attempts 应出现：

```text
8, 12, 16, 20, 24, 28
```

另一个 comparison 只允许 bounded retry budget，attempts 稳定在：

```text
8, 10, 10, 10, 10, 10
```

你必须写出：

- 为什么 retry 是 load；
- 为什么 retry 没有创造 capacity；
- 为什么 timeout 不证明原 attempt 没执行；
- backoff/jitter 能缓解哪类同步/放大问题；
- backoff/jitter **不能**解决哪些问题，例如 non-idempotent duplicate effect；
- retry budget、admission control、load shedding、caller throttling 各自改变什么 contract；
- 为什么 probe 的 rounds/ratio 不能升级成 production 参数。

### 比较 overload responses

至少比较三种：

| Design | User semantics | SLI consequence | Retry consequence | Resource/blast-radius consequence | Operational cost |
|---|---|---|---|---|---|
| accept all / unbounded queue | ? | ? | ? | ? | ? |
| bounded queue + explicit reject/load shedding | ? | ? | ? | ? | ? |
| add/scale workers | ? | ? | ? | ? | ? |

没有 universal winner。

## 11. Backpressure 必须重新连接到 M04 的 public contract

如果未来 TaskForge 在 queue full 时 reject submit，不能只改内部 queue。至少要回答：

```text
error code / outcome?
retryable?
Retry-After / caller pacing?
request identity / idempotency expectation?
rejection 算哪个 SLI cohort?
什么时候 page，什么时候只记录 capacity pressure?
```

若 API 永远 accepts，可能只是把 capacity failure 从 rejection 改成 latency。若明确 reject，也可能让 availability 指标变差但整体 user experience 更可控。

## 12. Rollout：把 production signal 变成 stop/continue evidence

假设一个新 scheduler 要逐步 rollout。设计一个 rollout table：

| Cohort | Continue condition | Stop condition | Diagnostic signals | Rollback assumption |
|---|---|---|---|---|
| 1% | ? | ? | ? | ? |
| 10% | ? | ? | ? | ? |
| larger | ? | ? | ? | ? |

至少覆盖：

- start-latency SLI；
- errors；
- saturation / queue age；
- retry amplification；
- telemetry/compatibility markers；
- rollback 是否真的能恢复，而不是只说“有 flag”。

Simulation / deterministic probe 是 pre-production evidence，不是 production truth。

## 13. Incident exercise：先恢复 impact/timeline，再讨论 root cause

把 baseline overload + retry amplification 当成一个教学 incident。不要编虚构人物故事；只恢复 system state 与 evidence。

提交 `incident-evidence.md`，至少包含：

### Impact

- 哪个 user journey degraded；
- applicable cohort；
- SLI / budget impact；
- blast radius。

### Timeline

至少记录：

```text
load increase / dependency degradation
first user-visible SLI violation
retry amplification becomes visible
alert/detection point
mitigation start
recovery
```

### Hypotheses

至少列三个 plausible causes，并说明哪个 evidence 支持/反驳。例如 worker capacity loss、arrival burst、dependency timeout、recent rollout、retry amplification。

### Mitigation

比较 rollback、restore capacity、throttle/reject new work、disable/reduce retry 等动作。说明它们为什么能减轻 user impact，以及可能引入的新风险。

不要要求 incident 开始时已经知道 root cause。

## 14. 写一份 blameless but technically precise postmortem

提交 `postmortem.md`。最低结构：

```text
Summary / user impact
Incident timeline
Detection
Response / mitigation
Trigger
Root + contributing conditions
Retry/overload amplification
What went well
What went poorly
Where we got lucky / residual risk
Follow-up actions
```

禁止把 root cause 写成：

```text
operator forgot X
```

然后结束。你要继续问为什么一个普通 mistake 或 failure 能产生该 blast radius，为什么 review/test/rollout/detection 没挡住，以及系统如何变得更难复发、更早发现、更容易止损。

每个 follow-up action 要有：

- owner / evidence owner；
- verifiable done condition；
- Prevent / Detect / Mitigate / Learn 中至少一个目的；
- 它对应哪条 failure chain；
- 如何验证 action 真的生效。

“以后更小心”与“给每个 timeout 加 alert”都不是自动合格的 action item。

## 15. 实现一个最小 observability seam，而不是接一套 stack

在自己的 working copy 实现一个 minimal reference direction。推荐新增 `production_observability.py`，但名字不是 contract。

实现至少支持：

```python
summarize_start_latency(...)
metric_points_or_series_identities(...)
diagnostic_events(...)
```

硬性 behavioral requirements：

1. baseline burst summary 是 `2 good / 10 bad / 12 total`；
2. accepted-but-missing-claim 不会 silent drop；
3. `job_id` 不进入 aggregate metric labels；
4. `job_id` 可留在 diagnostic event；
5. diagnostic event 不记录 command/secret/user content；
6. labels/vocab bounded；
7. canonical TaskForge lifecycle semantics 不改变；
8. 不引入真实 telemetry vendor dependency，除非你能证明它是实验必要条件。

建议 tests：

- baseline naive dashboard healthy vs user SLI violated；
- 12 vs 120 jobs cardinality negative control；
- missing event policy；
- diagnostic event stable fields / sensitive-data negative check；
- optional error-budget helper；
- existing core + M05–M11 probes unchanged。

不要 snapshot 整份 JSON 后每次更新 golden；测试稳定 contract，而不是 formatting accident。

## 16. Agent task 与 independent review

先比较两个 prompt。

Bad：

> 给 TaskForge 加完整 observability，做到 production-ready。

先预测至少五个风险，例如 high-cardinality labels、arbitrary thresholds、alert-every-error、sensitive logging、vendor coupling、instrument-every-branch、wrong SLI。

然后写一个 engineering prompt，至少包含：

```text
Goal / user-facing SLI specification
Measurement placement
Allowed + forbidden labels
Sensitive-data constraints
Existing telemetry consumers
Missing-event semantics
Expected cardinality
Retry/overload failure model
No paging without action contract
Deterministic evidence
Independent review requirement
Non-goals
```

换 reviewer/Agent 独立检查你的 patch，不先给 rationale。它至少回答：

- SLI 实际测的是什么；
- 哪些 accepted work 能从 denominator 消失；
- telemetry failure 能否让 SLI 看起来更好；
- 哪些 labels unbounded；
- 哪些 page 真有 immediate action；
- retry policy 是否在放大 load；
- 哪些 event/metric schema 已成为 compatibility surface；
- 哪些 sensitive data 进入 telemetry；
- instrumentation 自己的 cost/failure 是否被考虑。

M12 才系统讨论 Agent orchestration；这里 Agent 只是 implementation/review participant，不拥有 production policy authority。

## 17. Deliverables

提交：

1. `production-contract.md`；
2. SLI specification + measurement implementation / blind spots；
3. aggregate metric + diagnostic event model；
4. `failure-signal-matrix.md`：慢 / 无进展 / 数据不一致的 signal choice 与 limitations；
5. telemetry compatibility decision；
6. SLO / error-budget reasoning；
7. page + ticket action contracts；
8. retry-storm evidence + overload/backpressure comparison；
9. rollout gate；
10. `incident-evidence.md`；
11. blameless technically precise `postmortem.md`；
12. minimal implementation patch + tests；
13. Agent prompt + independent review；
14. residual risk。

## 18. Validation commands

至少重新运行：

```bash
PYTHONPATH=src uv run --with pytest --no-project python -m pytest -q
PYTHONPATH=src uv run --with pytest --no-project python tools/m11_production_probe.py
PYTHONPATH=src uv run --with pytest --no-project python tools/m11_retry_storm_probe.py
```

如果 implementation 触碰前面模块的 observable/compatibility/failure seams，还要跑相应 M05–M10 probes。不要用“新的 M11 tests green”替代旧 evidence preservation。

## 19. Rubric

| Dimension | Weight | Strong evidence |
|---|---:|---|
| User-centered reliability model | 20 | 从 user journey 推 SLI；scope/unknown/missingness 清楚 |
| Measurement quality | 15 | placement、denominator、blind spots、coverage 可解释 |
| Telemetry design | 15 | bounded cardinality；能针对慢/无进展/数据不一致选择 metric/event-log/trace evidence；signal limitation、隐私与 schema compatibility 明确 |
| SLO + operational action | 15 | target/window/budget reasoning 与 page/ticket action contract 相连 |
| Overload + retry reasoning | 15 | 能复现 amplification；比较 backpressure/load shedding/retry alternatives；不 cargo-cult 参数 |
| Incident + postmortem | 10 | impact/timeline/evidence 精确；blameless；systemic conditions 与 verifiable actions 闭环 |
| Implementation + preservation | 5 | behavior-level tests；旧 contract/probes 未被 instrumentation 破坏 |
| Agent + independent review | 5 | prompt 有 contract；review 不依赖 author/Agent summary |

不会因为使用 Prometheus、Grafana、OTel、Jaeger、Tempo、vendor APM、100 个 metrics、100% tracing 或 `99.999%` target 自动加分。工具只有在当前 reliability argument 需要它时才有价值。

## 20. 完成后最后回答

当 dashboard 全绿时，你至少还应该问：

1. 这些绿灯对应的 user contract 是什么？
2. measurement 在哪里，漏掉谁？
3. denominator / unknown / sampling 会不会让失败消失？
4. 如果症状从“慢”换成“无进展”或“数据不一致”，当前 metrics/events/logs/traces 还能区分它们吗？
5. overload/retry mechanism 会不会反过来制造新 load？
6. alert 是否真的驱动 urgent action；incident 后 learning 是否真的回到 system change？
