# M11 — Production、Observability 与 Reliability：当“全绿”仍然伤害用户

前十章的 evidence 大多发生在 merge 或 release 之前：specification、tests、compatibility fixtures、failure probes、review。M11 把同一套 engineering discipline 推进到系统运行之后。问题不再只是“这份 patch 在我们构造的 case 里对不对”，而是：**服务已经在跑，我们凭什么知道用户正在得到承诺的服务；如果没有，我们怎样发现、止损、解释并学习？**

这一章不会从 Prometheus、Grafana 或 OpenTelemetry 开始。TaskForge 已经有一个更有用的矛盾：所有 job 最终成功，queue 最后回到 0，naive dashboard 说 `healthy=true`；但同一段 history 里，12 个 accepted jobs 只有 2 个在 2 秒内开始执行。

运行：

```bash
cd labs/taskforge
PYTHONPATH=src uv run --with pytest --no-project \
  python tools/m11_production_probe.py
```

关键输出是：

```text
[NAIVE DASHBOARD]
{
  "ending_queue_depth": 0,
  "healthy": true,
  "submitted": 12,
  "success_ratio": 1.0
}

[USER-CENTERED START-LATENCY SLI]
good=2 bad=10 total=12 sli=0.167 target=0.990
result=VIOLATED despite 100% eventual success and an empty ending queue
```

这个 fixture 是 deterministic synthetic timeline，不是 performance benchmark。它不证明 TaskForge 的真实 throughput 是多少；它只稳定制造一个 production reasoning problem：**final state 很好看，而用户经历的 history 很差。**

## 1. 第一个 production bug 可能不是系统行为，而是“我们在看什么”

Naive dashboard 没有算错。它准确回答了两个问题：accepted work 最终是否成功，以及 observation window 结束时 queue 是否为空。问题在于，这两个问题不足以代表用户 contract。

假设产品真正承诺的是：accepted job 应该很快开始。那一个 job 等十秒后成功，在 eventual-success metric 里仍然是 good；一个曾经排队很久的 burst，在最后一个 job 完成后 `queue_depth=0`。Final state 擦掉了 history。

这让我们第一次需要把三个概念分开。**Telemetry** 是系统产生的 observation data，例如 metrics、structured events、logs、traces、synthetic probes。**Monitoring** 是针对已知问题持续计算和比较这些 observation。至于本课程说的 **observability**，我们只采用一个工程工作定义：系统是否提供足够、语义清楚、成本可控的 production evidence，使工程师能判断重要用户行为是否满足 contract，并在失败时缩小原因空间。

因此“接了 telemetry SDK”不是 observability 结论；“有 500 个 metrics”也不是 reliability 结论。第一步仍然和 M01 一样：先说清楚什么 behavior 重要。

## 2. 从 user journey 推出 SLI，而不是从已有 dashboard 反推需求

TaskForge 这次关注的 critical journey 可以先写成：

```text
submit accepted
    |
    v
authoritative job exists
    |
    v
first authoritative claim
    |
    v
explicit completion / failure
```

我们暂时选择其中一个用户可感知阶段：**accepted submission 到 first authoritative claim 的等待时间**。这不是唯一值得测的行为。真实系统还可能关心 completion latency、correctness、freshness、durability、cancellation 等；M11 只需要一个足以训练 measurement reasoning 的主 SLI。

于是可以给出一个 SLI specification：

> 对进入适用 cohort 的 accepted job，first authoritative claim 是否在 accepted submission 后 2.0 秒内发生？

这里的 2.0 秒和 99% 都是教学 target，不是从 Google 或真实 TaskForge 产品需求里发现的事实。课程用它们制造可重复判断，不把它们升级成 universal production target。

真正重要的是 specification 先于工具存在。若团队先打开 dashboard，看见“已有 queue depth、success ratio、CPU”，再把这些方便测的量拼成 SLO，就会得到一种危险的精确性：**精确地测错东西。**

## 3. SLI specification 与 measurement implementation 是两层 authority

Google SRE Workbook 明确区分 SLI specification 和 SLI implementation。前者回答“我们真正想知道什么”，后者回答“现在具体怎样观测它”。这一层区分在 production engineering 里非常重要，因为同一个 user-facing behavior 可以有多种 measurement placement。

TaskForge 的 start-latency specification 至少可以有三种实现。

第一种靠 service-side accepted timestamp 与 worker-side claim event 配对。它贴近 lifecycle authority，也能直接覆盖 queue wait；但 client 到 API 的网络延迟、ingress 前 rejection 不在其中，将来跨机器时还要处理 clock semantics。

第二种从 client 观察 `QUEUED → RUNNING`。它更接近 end-to-end user experience，但会混入 polling cadence、client scheduling 和 network delay，也更难区分内部哪里慢。

第三种用 synthetic job probe。它能长期检查 end-to-end journey，却只覆盖 probe cohort，可能与真实 workload、tenant、payload 分布不同。

没有一种 placement 自动“最真实”。选择 measurement implementation 时应写出它覆盖什么、系统性漏掉什么、成本是什么，以及谁消费它。

这就是本章的 **measurement blind spot**：implementation 系统性漏掉了 specification 中的重要部分。Blind spot 不是简单的“数据有误”；它可以发生在所有数字都计算正确时。

## 4. Denominator 决定最糟糕的 work 会不会凭空消失

Start-latency 很适合写成 good events / total events，但 denominator 必须由 user contract 决定，而不能只由已有 telemetry 决定。

一个看似自然的实现是：

```text
fast_claimed_jobs / all_claimed_jobs
```

它有一个严重 blind spot：如果 job 已经 accepted，却一直没被 claim，它根本不会进入 denominator。系统越坏，越可能把坏样本从观测里删除。

因此这次教学 reference 从 **accepted submissions** 建 cohort。Reference policy 是：

- Total：measurement scope 内被 accepted 的 submissions；
- Good：有 first authoritative claim evidence，且 wait `<= 2.0s`；
- Bad：有 claim evidence，但 wait `> 2.0s`；
- Unknown：accepted 已知，但评估时缺 first-claim evidence。

Unknown 不是 automatically good，也不该 silent drop。真实系统可以把 still-open window 中的 event 先标 pending，可以单独维护 telemetry coverage SLI，也可以在窗口关闭后按 policy 将 unknown 计 bad。课程不强制唯一答案；它强制的是 **missingness 必须显式进入 contract**。

## 5. Metrics、events、logs、traces 不是四种“等级”，而是不同成本结构

M11 starter 故意给了第二个错误设计：把 `job_id` 放进 aggregate metric labels。Probe 会输出：

```text
12 completed jobs -> 12 metric series because job_id is a label
```

这不是因为 `job_id` 没有诊断价值。恰恰相反，单个 job 的 correlation 常常非常有用。问题是 metric backend 会为不同 labelset 建不同 series identity；如果 label value 随每个 job、request、user 增长，aggregation model 的成本会随 workload identity 增长。

所以我们把两个问题拆开：

| Question | 更合适的 signal shape |
|---|---|
| “最近 5 分钟 late jobs 占比多少？” | bounded aggregate metric |
| “job-847 为什么等了 11 秒？” | diagnostic event/log/trace with correlation ID |

Reference aggregate labels 可以是 `outcome=within_target|late`、`worker_pool=default`、bounded reason code。`job_id`、request ID、具体 command 等高基数或敏感上下文更适合 diagnosis-oriented signal，而且仍要有 retention/privacy policy。

这也解释了为什么“禁止源码出现 `job_id`”是错误 fitness rule。我们要保护的是 **aggregate series identity 不按 individual job identity 增长**，不是消灭 correlation。

## 6. Telemetry schema 也是长期接口

假设 dashboard、alert 与 incident query 都消费：

```json
{"event":"job_claimed","outcome":"late","worker_pool":"default"}
```

下个版本把 `outcome` 改成 `status`，producer 自己可能完全正常，但 consumer 会 break。这和 M08 没本质区别：telemetry 也会形成 long-lived contract。

因此 schema change 也可能需要 Expand → Migrate consumers → Contract。是否值得做完整迁移取决于 consumer 数量、支持窗口与风险；课程不要求每个 log field 都永久兼容。但 reviewer 不能因为“这只是 observability”就忽略 downstream consumers。

Structured event 也不是越多字段越好。TaskForge command 未来可能含 path、token、user content 或 business data；默认把 payload 全量送进 telemetry backend，会把 diagnosis convenience 变成 security/privacy liability。

## 7. SLO 给“足够好”一个 operational target，但不是 performance snapshot

SLI 只是 measurement；SLO 才给出 target。教学 reference 使用：

> 99% applicable accepted jobs 的 first authoritative claim 在 2.0 秒内发生。

一个完整 SLO 还至少要说明 measurement window、traffic scope、canceled/rejected work 怎么处理、missing observation policy、measurement source、owner 与 review cadence。

SLO 不应该直接等于“当前 p99 + 10%”，因为 current performance 不是 user requirement；也不应该是 wishful `99.999%`。100% 也通常不是默认目标，因为 reliability 有成本，而且某些不可靠性可能已经低于用户感知阈值。

这时 error budget 才有意义。若 SLO 允许 1% bad event，那么 error budget 是一个 decision input：当前 observation 消耗允许 bad 的速度有多快，我们还能承受多少 change risk，什么时候需要把工程注意力从 feature 转向 reliability。

M11 会使用 burn rate 这个关系，但不要求背 Google 的固定 14.4x 等参数。参数必须来自 service criticality、window、traffic、on-call policy 和 action cost，而不是 cargo cult。

## 8. Alert 是 action contract，不是 metric threshold 的另一种显示方式

如果 dashboard 看见 `queue_depth > 10` 就 page，operator 到底要做什么？Queue depth 可能是 saturation cause signal，也可能只是短 burst；同一个 depth 对不同 service rate 的系统意义不同。

更合理的 page 需要把几件事连起来：

- 当前 user symptom / error-budget threat；
- 为什么它足够 urgent；
- 谁负责；
- 第一组 diagnostic action；
- 可选 mitigation；
- 什么时候算恢复。

例如 TaskForge 可以让 urgent start-latency burn 触发 page，再附 queue oldest age、arrival/service rate、worker availability、recent rollout marker、dependency latency 等 cause context。Page 的价值不在“发现原因”，而在告诉人 **现在必须有行动**。

这不是说 cause signal 永远不能 page。Certificate 即将到期、disk 即将满、quorum 即将丢失等 cause 如果和 imminent impact 有可靠关系，而且必须在 user symptom 前采取行动，就可以是优秀 page。规则仍然是 urgency + action contract，而不是 symptom/cause 二分法本身。

Ticket 则适合“需要处理，但不需要现在叫醒人”的问题，例如 capacity headroom 长期下降、cardinality 增长、slow error-budget burn。Logging/recording 可以只服务后续 diagnosis。不同 channel 本质上是在声明不同 human-action urgency。

## 9. Four Golden Signals 是漏项 heuristic，不是 dashboard 模板

Latency、traffic、errors、saturation 是很有用的 review lens。对 TaskForge，可以暂时映射为 submit rate、submit→claim / claim→finish latency、bad outcomes，以及 queue age/depth/worker saturation。

但这四个词不会替你定义 product contract。例如 freshness 或 correctness 可能比 request latency 更重要；successful 与 failed operation latency 也应区分，否则大量快速失败会把整体 latency 指标“改善”。

同样，average 经常隐藏 tail。Production review 应先问哪个 user cohort 和哪个 distribution region 有风险，再决定 histogram、quantile 或 event cohort，而不是因为工具默认展示 average 就停在那里。

## 10. 第二阶段：当 retry 也开始制造 load

Baseline burst 已经说明 arrival pressure 超过 single-worker service capacity 时，accepted work 会排队。现在再加一个很常见的 reaction：timeout 后自动 retry。

运行教学 probe：

```bash
PYTHONPATH=src uv run --with pytest --no-project \
  python tools/m11_retry_storm_probe.py
```

Naive model 中每轮有 8 个新 logical requests，dependency 每轮只能完成 4 个；所有 timed-out attempts 下一轮立即 retry。Attempts 因此变成：

```text
8, 12, 16, 20, 24, 28
```

Capacity 没变，retry 却持续增加 downstream work。这就是 retry amplification 的核心：**retry 是 load，不是免费恢复动作。**

Probe 还给一个 bounded retry-budget comparison，把每轮 admitted retry 限制为 2，于是 attempts 稳定在 `8, 10, 10, ...`。这个数字不是推荐 policy，只是让 failure shape 可观察。真实系统还要比较 exponential backoff、jitter、retry deadline、caller throttling、load shedding、admission control 和 request identity。

尤其要保持 M04/M07 的 qualifier：timeout 不证明 downstream 没执行；backoff 不解决 non-idempotent duplicate effect；retry budget 也不创造 capacity。Reliability mechanism 可能同时是 recovery mechanism 和 failure amplifier。

## 11. Overload response 是 product semantics，不只是 capacity tuning

当 demand 持续超过 capacity，有三种都 plausible 的 response。

**Infinite queue** 可以减少 immediate rejection，语义简单；代价是 latency、resource use 与 stale work 可能无界增长。

**Bounded queue + explicit rejection/load shedding** 能保护已有 work 和资源边界；代价是需要 public rejection contract：error code、retryability、`Retry-After`、idempotency/request identity、SLI 计数语义都要明确。

**Scale workers / add capacity** 可以提高 service rate；代价是 cost、startup lag、external bottleneck、并发与 failure complexity。它也不自动解决 retry storm，因为扩容速度可能慢于 amplification。

因此 backpressure 的问题不是“用什么 queue library”，而是 downstream capacity information 怎样传播给 upstream。一个永远 accepts 的 API 可能让 availability metric 看起来优秀，只是把 overload 从 rejection 变成 latency。

Graceful degradation 和 load shedding 也没有 universal winner。搜索少返回一点结果可能比 timeout 好，银行余额 stale 可能完全不可接受。所有 degraded mode 都必须回到 product contract。

## 12. Operational simplicity 本身就是 reliability property

Instrumentation、alert、retry、fallback、canary、runbook 都能降低某类风险，也都能制造新的 operational surface。更多 telemetry 会增加 series、storage、query、privacy 和 cognitive cost；更多 alerts 会制造 fatigue；复杂 fallback 会让真实 execution path 与 diagnosis path变难。

因此 production-facing design 要记录一个很朴素的问题：**新增机制后，operator 是否更容易判断、止损和恢复，还是只是多了一套需要维护的系统？**

这也是“没有新 metrics”可能是正确设计的原因。如果现有 signal 已能验证 new change 的 user outcome，而且新 metric 只重复已有 information，就没有必要为了 instrumentation 数量而增加 cost。反过来，“加了 metrics”也不能替代 contract；你仍然要知道每个 signal 对哪个 decision 有贡献。

## 13. Rollout 是 production experiment，但 simulation 不是 production truth

一个 remote-worker scheduler 即使 CI 全绿，也不应该自动从 0% 到 100%。M08 已经告诉我们 independent versions 需要 coexistence/rollback policy；M11 再加一层：rollout 要看能够验证 change hypothesis 的 production signal。

例如先暴露小 cohort，然后观察 start-latency SLI、errors、saturation 和 compatibility markers；只有 signal 支持当前 hypothesis 才继续扩大。如果 stop trigger 命中，要知道 rollback 是否真的能恢复，而不是把 feature flag 当 rollback proof。

Synthetic burst、failure injection 和 load test 都是 evidence，不是 production truth。它们不会自动包含真实 traffic distribution、dependency correlations、client retry behavior、hardware noise 或 operator action。成熟 argument 是 pre-production evidence + production evidence 相互补充，而不是一个替代另一个。

## 14. Incident response 先恢复 service，再逐步缩小 cause space

Production incident 开始时通常还不知道 root cause。把 diagnosis goal 写成“立刻找到真正根因”会鼓励过早 certainty。更有用的顺序是先确认 user impact 和 scope，再检查 recent changes / saturation / dependency / cohort differences，选择低风险 mitigation，同时记录关键 timeline 与被否定的 hypothesis。

TaskForge 的 start-latency incident 中，一个简化 evidence packet 可以包括：

| Evidence | 它帮助回答什么 |
|---|---|
| start-latency SLI/burn | 用户是否正在受影响 |
| oldest queue age | backlog 是否持续老化 |
| arrival/service rate | demand-capacity mismatch 是否存在 |
| retry attempts | retry 是否在放大 load |
| worker availability | service capacity 是否下降 |
| recent rollout marker | 是否有强 temporal correlation |
| diagnostic job events | 哪个 cohort/job path 异常 |

这些 evidence 不自动证明 cause；它们帮助我们缩小 cause space，并决定 mitigation。

## 15. Postmortem 要 blameless，但不能因此失去技术精度

Google SRE 的 postmortem practice 把 incident learning 变成正式工程输入。Blameless 的含义不是“谁都不能讨论决策失误”，而是不要把技术 root cause 停在“某工程师忘了 X”。更重要的问题是：为什么一个普通 mistake 能产生这么大 blast radius，为什么 review/test/rollout 没挡住，为什么 detection 晚，为什么 mitigation 困难。

一份 M11 postmortem 至少应恢复：

1. user impact 与 incident window；
2. timeline：什么时候开始 degraded、什么时候检测、采取了什么 mitigation、何时恢复；
3. production evidence：哪些 SLI/signal 支撑 impact 结论；
4. trigger 与 root/contributing conditions；
5. amplification：retry、overload、shared dependency 等怎样改变事故；
6. detection/response gap：为什么现有 dashboard/alert 没更早给出可行动 evidence；
7. follow-up actions：每项有 owner、可验证完成状态，以及 prevention/mitigation evidence。

“以后更小心”不是好的 action item。“给每个 timeout 加一个 alert”也未必是。Action 应改变 system/process，使同类 failure 更难发生、更快发现、blast radius 更小或更容易恢复。

## 16. Production evidence 是另一类 evidence，不是 proof

M03 已经教过：tests 只能覆盖具体 partition；M10 又要求 reviewer 独立判断 evidence 是否真的支持 claim。Production metrics 也一样。一个 SLI 可以有 blind spot；telemetry 可以丢；采样会改变 coverage；dashboard query 可能错；一个 incident correlation 也不自动等于 causation。

因此可以把 production-facing argument写成一条 chain：

```text
user expectation
    -> SLI specification
    -> measurement implementation
    -> telemetry schema / placement
    -> aggregation + missingness
    -> SLO / budget
    -> alert / action policy
    -> incident evidence
    -> learning / change
```

每一层都有自己的 authority，也可能出错。Telemetry 正确但 SLI specification 错，会精确测错东西；SLI 正确但漏掉 accepted work，会产生 survivorship bias；metric 正确但 alert threshold 没 action contract，会制造 noise；postmortem 很完整但 action item永远不关闭，也没有形成 reliability improvement。

## 17. Agent 生成 observability 时，生成成本下降了，operational cost 没下降

Agent 很容易一次生成 counters、logs、spans、alerts、dashboards。代码量本身不再是主要限制；真正昂贵的是 signal semantics、cardinality、retention、privacy、consumer compatibility 和 operator attention。

所以 M11 只把 Agent 当 implementation/research accelerator，不把 production policy authority交出去。一个可 review 的任务至少要说明：user-facing SLI specification、measurement placement、allowed/forbidden labels、sensitive-data constraints、existing telemetry consumers、missing-event semantics、expected cardinality、page action contract 和 deterministic evidence。

Agent 可以运行 probes、生成 instrumentation、整理 evidence；它不能因为自己看到 dashboard green 就自行宣布 `production-ready`。`production-ready` 如果不拆成 correctness、load/capacity、failure、compatibility、observability、rollout 与 ownership evidence，只是低信息量形容词。

M12 才会系统讨论 context engineering、task decomposition、tool authority、parallel agents 与 independent review。M11 只建立它所依赖的 operational premise：**谁能收集 evidence，和谁有权定义 acceptable service / production action，是两件事。**

## 18. 把本章压缩成一次 reliability review

面对 production-facing change，可以顺序问：

- 用户真正关心哪段 journey？
- SLI specification 是什么，measurement implementation 在哪里？
- denominator、missing event、sampling 会漏掉谁？
- aggregate metrics 的 labels 是否 bounded，diagnostic correlation 是否放在合适 signal？
- telemetry schema 是否已有 downstream consumers？
- SLO/error budget如何定义 acceptable service，而不是复制当前 performance 或外部数字？
- 哪些 signal 是 symptom，哪些帮助 diagnosis；哪个 condition 真正需要 urgent human action？
- overload 时系统怎样 backpressure、reject、shed、degrade、retry；这些机制是否反过来放大 load 或 duplicate effect？
- rollout 的 stop/rollback evidence 是什么？
- incident 后能否写出 precise timeline、systemic contributing conditions 和可验证 follow-up actions？
- telemetry、alert 与 mitigation 的 operational complexity 是否值得？

如果这些问题有答案，dashboard 可以很简单；如果这些问题没有答案，再漂亮的 dashboard 也只是在展示未经定义的数字。

本章真正把软件工程 loop 延伸成：specify → design → implement → test → review → roll out → observe → respond → learn → change again。Production 不是开发结束后的运维附录，而是长期系统获得新 evidence 的地方。

进一步的来源、限制与 course-synthesis 边界见 [`../reading-notes/m11-source-audit.md`](../reading-notes/m11-source-audit.md)。
