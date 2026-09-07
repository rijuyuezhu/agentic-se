# M11 Instructor Reference — 从 false-green dashboard 到 reliability learning loop

> 教师参考。它描述一条可接受 reference reasoning，不是要求学生照抄唯一 telemetry schema、SLO 参数或 mitigation policy。

## 1. Baseline 不是 performance benchmark，而是一个 measurement contradiction

`production_signals.py` 用 deterministic synthetic timeline 构造 12 个几乎连续提交的 jobs，由单 worker 顺序 claim/finish。所有 jobs 最终 `SUCCEEDED`，ending queue depth 回到 0，所以 naive summary 是：

```text
submitted=12
success_ratio=1.0
ending_queue_depth=0
healthy=true
```

但 submit→first-claim wait 是：

```text
job-1   1.00s   good
job-2   1.95s   good
job-3   2.90s   bad
...
job-12  >10s    bad
```

因此教学 SLI 得到：

```text
good=2
bad=10
total=12
ratio=0.1667
```

第一层结论不是“dashboard bug”，而是 **dashboard 回答的问题不足以代表 user contract**。第二层 qualifier 也必须保留：这些 synthetic timestamps 不证明真实 TaskForge capacity，也不应用来估生产 throughput。

## 2. Reference production contract

本参考选择的 journey 是：

```text
accepted submit -> first authoritative claim -> explicit terminal outcome
```

Primary SLI 只建模第一段等待，不声称覆盖 completion correctness、durability、cancellation、external effects 或真实 end-to-end client latency。

Reference specification：

- Total：measurement scope 内每个 accepted submission；
- Good：first authoritative claim exists 且 wait `<= 2.0s`；
- Bad：claim exists 且 wait `> 2.0s`；
- Unknown：accepted 已知，但 evaluation 时没有 first-claim evidence。

Reference summary 使用 `good / total`，所以 unknown 不会被 silent drop 或自动算 good。真实系统可以把 open-window work 先视为 pending，或者另建 telemetry coverage SLI；课程只要求 missingness 显式。

## 3. 为什么 denominator 从 accepted submissions 开始

错误版本 `fast_claimed / all_claimed` 会把 never-claimed accepted work 从 denominator 删除。越严重的 backlog 越可能让 SLI 看起来更好，属于典型 survivorship bias。

因此 cohort authority 来自 accepted submission，而不是“我们碰巧收到了哪些 claim events”。这和 M01/M03 一致：measurement implementation 不能偷偷改写 specification population。

## 4. Reference measurement placement

本参考选择 service accepted event + worker authoritative claim event，因为它：

- 覆盖 queue wait；
- 不依赖 client polling cadence；
- 靠近 lifecycle authority；
- 在 deterministic lab 中容易验证。

但 blind spots 必须一起写：client→API latency、ingress 前 rejection 不在其中；telemetry loss 会产生 unknown；未来跨主机还需要明确 clock semantics。它不是完美 end-to-end user measurement。

## 5. Reference implementation direction

临时 reference working copy 可以新增一个轻量 `production_observability.py`，而不引入 telemetry vendor。

核心 summary type 可以是：

```python
@dataclass(frozen=True)
class StartLatencySummary:
    good: int
    bad: int
    unknown: int
    total: int
    ratio: float
```

Reference tests 首先保护 behavioral semantics：baseline 是 `2/10/0/12`；accepted-but-no-claim 不消失；summary 不改变 canonical TaskForge lifecycle。

名字和具体 API 不是课程 authority。

## 6. Aggregate metric identity 与 diagnostic event 分工

Reference aggregate dimensions 只使用 bounded vocabulary，例如：

```text
outcome = within_target | late | unknown
worker_pool = default
```

不把 `job_id`、request ID、command 放进 aggregate metric labels。

强 negative control：

```text
12 jobs  -> bounded number of series identities
120 jobs -> same bounded category identities
```

而 diagnosis event 可以保留：

```json
{
  "event": "job_claimed",
  "job_id": "job-12",
  "wait_seconds": 11.45,
  "worker_pool": "default",
  "outcome": "late"
}
```

所以 `job_id` 高 cardinality 不能推出 `job_id` 没 telemetry value。真正 contract 是：individual identity 不应让 aggregate series count 随 workload 线性增长。

### Failure-class transfer reference

高分答案还要把 signal choice 迁移到 latency 之外，而不是把 event/log/trace 当一个 diagnosis bucket：

| Failure | Reference reasoning |
|---|---|
| 慢 | aggregate latency SLI/distribution 判断 scope；component metrics 帮助找 pressure；只有跨组件 path/timing 是问题时才需要 trace |
| 无进展 | lifecycle progress/oldest-age/heartbeat evidence 说明“按哪个 progress contract 没前进”；缺 event 本身仍可能是 telemetry loss |
| 数据不一致 | 先定义应该一致的 authority/read surface 与 freshness bound；mismatch metric 看范围，diagnostic event/log 保留 identity/version/source；跨服务 serving/replication path 才可能需要 trace |

Reference inconsistency transfer 可以假设未来有 derived status/read model。**Current starter does not implement this read model**；它只是为了迁移 signal-selection reasoning 的 future assumption，也不要求学生实现。关键 property 是：如果两个 surface 被 contract 要求在某 observation/freshness boundary 内一致，那么 observability 要能识别 mismatch，并说明哪份状态有 authority 的依据来自 architecture/contract，而不是 trace 本身。

OTel 官方 signal model 可以用来校准这里的 distinction：metric 是 runtime measurement，log 是 event record，trace 表达 request/path through components。课程把它们映射成 evidence shape，但不推导“所有 failure 都必须三种 signal 齐全”。Sampling、propagation gap 与 event loss 都会限制 conclusion。

## 7. Sensitive data 与 telemetry compatibility

Reference event 不记录 command、headers、tokens、arbitrary user content。TaskForge command 未来可能携带 path、credential misuse、business/user data，不能默认进入 telemetry backend。

如果已有 consumer 依赖 `job_claimed.outcome`，改名为 `status` 就是 compatibility change。Reference 可用 M08 风格：producer 暂时同时支持 old/new 或 reader 支持两者 → migrate dashboards/alerts/queries → contract/remove old。是否需要完整 migration 取决于 consumer/risk，不是每个 debug log 都必须永久兼容。

## 8. SLO 与 error-budget reference

教学 SLO 是：

> 99% applicable accepted jobs 的 first authoritative claim 在 2 秒内发生。

这只是 fixture target。Reference explanation 必须补 measurement window、traffic scope、missing policy、owner、review cadence。

若 observed bad ratio 为 `10/12 ≈ 0.8333`，SLO 允许 bad ratio 是 `0.01`，则 instantaneous burn-rate intuition 约 `83.33x`。如果这种状态持续 1 小时，而假设 30-day window，window fraction 是 `1/720`，budget consumption 约 11.6%。

这个 calculation 很严重，但 reference 不硬编码“一定 page”。Page 还取决于 persistence、traffic representativeness、service criticality、operator action 和 window design。课程刻意不复制固定 14.4x/6x threshold。

## 9. Symptom、cause 与 action contract

Reference classification：

- start-latency SLI：direct user symptom；
- queue depth：主要是 internal saturation/cause signal；
- queue oldest age：比 depth 更接近 user pain，但仍通常是 queue-internal；
- CPU / worker utilization：cause/capacity signal；
- retry rate：cause/amplifier，也可能反映 caller distress；
- submit error ratio：可能直接是 user symptom。

Reference page 不写 `queue_depth > 10`。更合理的 action contract是：urgent sustained start-latency error-budget threat → TaskForge on-call；先查 oldest age、arrival/service rate、worker availability、recent rollout、dependency latency、retry attempts；mitigation 可包括 rollback scheduler、restore worker capacity、按 public capacity contract throttle/reject new work、降低 retry amplification；当 short-window symptom recovery 且 long-window burn 受控时 stop。

Capacity headroom 长期下降但当前无 SLO threat 更适合 ticket。

## 10. Retry storm probe：第二个 failure model

新增 teaching-only `m11_retry_storm_probe.py` 不修改 TaskForge 产品代码。它稳定表达一个 overload feedback loop：每轮 8 个新 logical requests，downstream capacity 4；所有 timeout attempts 下一轮立即 retry。

Reference naive attempts：

```text
8, 12, 16, 20, 24, 28
```

Reference bounded retry-budget comparison：

```text
8, 10, 10, 10, 10, 10
```

这里的课程结论只有：**retry consumes capacity and can amplify overload**。不要从 probe 推出具体 timeout/backoff/retry-budget 参数。

需要继续保留 M04/M07 semantics：timeout 不证明原 attempt 未执行；backoff/jitter 不提供 exactly-once；retry budget 不创造 capacity。若 operation 可能有 external effect，还需要 logical request/effect identity 和 dedup contract。

## 11. Overload alternatives 没有 universal winner

Reference comparison：

### Accept all / unbounded queue

优点是 immediate rejection 少、接口简单；代价是 wait latency/resource/stale work 可以无界增长。Baseline 就展示了“availability 看起来好，只是把 failure 变成 latency”。

### Bounded queue + explicit rejection/load shedding

优点是资源有界、保护已有 work、overload explicit；代价是 public rejection/retryability contract 必须设计，caller retry 又可能放大 load，SLI cohort interpretation 也会改变。

### Scale workers

提高 service rate，但有 cost、startup lag、dependency bottleneck、concurrency/failure complexity；扩容速度可能赶不上 retry amplification。

Reference 不宣布某个方案“架构更干净”。Decision 取决于 product semantics、capacity、deadline、cost、blast radius 和 caller behavior。

## 12. Incident reference：先重建 impact/timeline，再找 cause

教学 incident 可以这样组织，但不要伪造人物戏剧。

### Impact

Accepted-job start latency 大量超过 2s，baseline cohort 10/12 bad。Naive eventual-success/ending-depth dashboard 没显示这个 history-level harm。

### Timeline

一个合理教学 timeline：

```text
T0    burst / downstream pressure starts
T1    first accepted jobs exceed start-latency target
T2    naive retry policy begins amplifying attempts
T3    SLO symptom + retry/saturation evidence cross action threshold
T4    operator limits new/retry load or restores capacity
T5    start-latency symptom recovers
```

这些是 failure-model timestamps，不是 production incident 事实。

### Plausible hypotheses

- arrival rate burst；
- worker capacity loss；
- dependency timeout；
- recent scheduler rollout；
- retry amplification；
- telemetry/query defect。

每个 hypothesis 都要绑定 discriminating evidence，而不是由 temporal correlation 自动升成 root cause。

## 13. Blameless but technically precise postmortem reference

Reference postmortem 应覆盖：summary/impact、timeline、detection、response、trigger、root/contributing conditions、amplification、what went well/poorly、residual risk、follow-up actions。

一个不合格 root cause 是：

```text
operator forgot to disable retries
```

更完整的 analysis 要继续问：为什么 retry policy 没有 budget/backoff；为什么 overload/retry signal 没进入 action contract；为什么 naive dashboard 只看 final success/depth；为什么 rollout/review 没暴露这一 assumption；为什么一个普通 configuration/implementation mistake 能扩大 blast radius。

Reference action items 应可验证，例如：

| Action | Purpose | Done evidence |
|---|---|---|
| define retry budget/backoff contract for this boundary | Prevent/Mitigate | deterministic + integration failure evidence shows bounded amplification |
| add start-latency SLI + missingness policy | Detect | accepted cohort cannot silently disappear; alert evaluation uses it |
| add retry-attempt/saturation diagnostic context | Detect/Diagnose | incident query can distinguish demand, capacity, retry amplification |
| document overload rejection/retryability semantics | Prevent | M04 boundary tests + caller contract updated |
| add rollout stop condition for latency burn | Mitigate | canary exercise demonstrates stop/rollback decision |

“以后更小心”不是 system change；“alert every timeout”也不是 automatically actionable。

## 14. Reference test evidence

在临时 working copy 中，最小 observability implementation 可以用 5 个 tests 覆盖：

1. baseline burst 得到 `2 good / 10 bad`；
2. 12 vs 120 jobs aggregate series identity 不随 job count 增长；
3. diagnosis event 保留 `job_id` 但无 command/sensitive payload；
4. missing claim 不从 denominator 消失；
5. optional error-budget/window helper obeys documented semantics。

Canonical repo 不需要因此接 telemetry stack。`production_signals.py` 和两个 probes 是 teaching surfaces；reference implementation 仍可留在学生/教师临时 copy。

## 15. 哪些判断不能被漂亮 dashboard 或 Agent summary替代

学生常见错误仍包括：

- `100% eventual success -> healthy`：遗漏 latency contract；
- `queue_depth > threshold -> page`：没有 user impact/action reasoning；
- `job_id useful -> metric label`：混淆 diagnosis 与 aggregation；
- missing claim event 直接 filter：survivorship bias；
- installed OTel -> observability done：工具替代 measurement design；
- `SLO = current p99 + 10%`：current performance 偷换 requirement；
- alert every exception：diagnostic event 偷换 urgent action；
- retry on every timeout：recovery mechanism 偷换成 unbounded load source；
- postmortem root cause = person error：组织/系统 learning 被截断。

Agent instrumentation review 要独立问：SLI 真的测什么、bad work 能否消失、telemetry failure 能否改善 SLI、labels 是否 unbounded、schema 是否兼容、敏感数据是否泄漏、page 是否 actionable、retry 是否放大 load、instrumentation 本身 cost/failure 是否可接受。

## 16. Grading focus

高分答案不一定有第三方 telemetry stack。真正看：

- user contract → SLI 的推导是否成立；
- placement/denominator/missingness 是否有明确 model；
- aggregate/cardinality 与 diagnosis correlation 是否分开；
- SLO/budget 是否驱动 decision 而不是数字 cargo cult；
- overload/retry/backpressure alternative 是否比较 contract 与 consequence；
- incident evidence 是否区分 impact、hypothesis、cause；
- postmortem 是否 blameless 且 technically precise，action item 是否可验证；
- Agent/author summary 是否经过 independent review。

M11 的结论不是“production 需要更多数据”。更接近的是：

> Production evidence 的质量取决于 semantic alignment、coverage、placement、aggregation、cost 与 actionability；incident learning 只有在回到 contract/design/test/operation change 时才闭环。

M12 会进一步讨论当 Agent 可以自己收集这些 evidence、运行工具甚至修改系统时，tool authority 与 acceptance authority 应怎样分离。
