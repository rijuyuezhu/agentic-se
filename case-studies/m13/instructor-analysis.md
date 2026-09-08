---
id: case-M13
type: case_study
visibility: instructor
related: [M13]
---
# M13 Instructor Analysis — TaskForge Lease Recovery Capstone

> 这是 instructor reference，不是学生第一次接触 Capstone 时应该先看的答案。建议至少完成 first-pass issue review、human decision delta、system model、design memo、candidate implementation 与 independent review 后再读。

本 reference 的目标不是给出“lease scheduler 标准实现”，而是展示一条能够把 issue contradiction、state authority、migration、runtime evidence、review 与 Agent authority 串起来的可行 change path。对应 provenance 见 [`../../reading-notes/m13-source-audit.md`](../../reading-notes/m13-source-audit.md)。

## 1. 第一结论不是 READY_TO_IMPLEMENT

原始 `ISSUE.md` 同时要求 arbitrary shell command exactly-once、timeout 后 automatic retry、old worker mixed rollout、旧 completion payload 不变，以及任意时刻可切回 old server binary。

Starter 的 v1 finish 只有：

```json
{"job_id": "job-1", "exit_code": 0}
```

它没有 worker identity，也没有 execution identity。更重要的是，即使 TaskForge 能识别 stale completion，它仍不知道一个失联 worker 是否已经在 TaskForge 边界之外完成了副作用。

因此 reference first-pass verdict 是：

```text
NEEDS AUTHORITY DECISION
```

而不是 `READY_TO_IMPLEMENT`。这一步没有选择 at-least-once、attempt column 或 activation gate；它只指出原 guarantee 在当前 knowledge/authority boundary 下无法成立。

## 2. Baseline：六个绿测试允许非法 history

Canonical starter 当前实际得到：

```text
......                                                                   [100%]
6 passed
```

这些 tests 覆盖 schema v1、legacy submit response、single-worker FIFO claim、legacy finish、maintenance stale scan 与 queued cancellation。它们没有提出两个关键问题：concurrent claim 会发生什么；requeue 后旧 completion 会发生什么。

`capstone_baseline_probe.py` 用 deterministic barrier 强制两个 worker 都先观察同一个 queued row。实际输出包括：

```text
successful_claims=job-1,job-1
workers_returned_success=2
final_row_has_single_owner=true
history_is_illegal=true
```

这不是“最终 worker_id 写错”这么简单。A 与 B 都已经拿到了 success receipt；最终 row 只有一个 owner 不能 retroactively 抹掉另一个成功历史。

第二条 baseline history 是：A claim → operator requeue → B claim → A 发送旧 finish。Starter 实际得到：

```text
stale_finish_accepted=true
final_status=succeeded
final_worker_id=worker-b
```

因此原 issue 的“sweeper requeue，但 `finish_job()` 保持不变”不是一个安全兼容方案。旧 payload 没有足够 identity 判断它是否仍属于 current execution。

## 3. Exactly-once contradiction 到底在哪里

即使把 stale finish 完全 fence 掉，下面的 history 仍然成立：

```text
attempt 1 performs external charge
→ lease expires before TaskForge records completion
→ attempt 2 performs external charge
→ attempt 1 late finish is rejected
```

TaskForge state 可以正确只接受 current attempt；外部世界仍然可能已经出现两个 effects。因此必须区分：

- **TaskForge lifecycle state fencing**：哪个 execution 当前可以改变 durable job state；
- **external effect dedup/fencing**：支付、邮件、对象存储等 effect owner 是否会拒绝重复 effect。

第二类 semantics 不会因为 TaskForge 增加 lease、SQLite transaction 或 message broker 自动出现。它可能来自 effect-owner idempotency key、fencing token、transactional integration，或把 automatic retry 限制在明确 retry-safe 的 workload。

Reference 因此拒绝 arbitrary-command exactly-once wording，而不是发明“best effort exactly once”之类模糊 guarantee。

## 4. Human decision 真正授予了什么

Reference 接受 `decision-pack/01-after-issue-review.md` 作为本题 product/system authority。最终 contract 变成：

- legacy `submit_job(command)` response shape 不变，创建的 job 默认 `recovery_policy=manual`；historical `operator_requeue()` 仍是 migration emergency path，但其 stale-completion / duplicate-execution risk 明确保留；
- 新 submission surface 可显式选择 `automatic_at_least_once`；
- new worker claim 获得 monotonic attempt identity；
- v2 heartbeat / finish 必须携带 `job_id + attempt + worker_id`，只有 current running v2 attempt 可 renew / finish；current-attempt fencing guarantee 只覆盖 v2 attempt protocol；
- v1 completion 在 migration window 继续支持，但只能完成 legacy attempt；它不能区分 manual requeue 前后的两个 legacy executions，因此不属于 v2 fencing guarantee；
- existing v1-v1 claim race 必须在 mixed rollout 前先修；mixed window 中所有 active claim protocol 还必须共享 queued-row single-winner invariant；
- automatic recovery 在 protocol migration 完成并通过 activation gate 前保持关闭；
- Expand-only 阶段追求 old-binary compatibility；v2 semantic state 已经出现后不再承诺 simple old-server rollback；
- 不默认引入 broker / distributed DB 等新 infrastructure。

从这里开始，attempt fencing、manual default 与 staged activation 才是 normative teaching contract。在这之前它们只能是 candidate design，不应被写成“自然答案”。

## 5. Reference representation：默认值承担 migration 语义

Reference 没有增加新 service，仍使用单 SQLite `jobs` table。Expand 增加：

```text
attempt INTEGER NOT NULL DEFAULT 0
lease_expires_at REAL NULL
recovery_policy TEXT NOT NULL DEFAULT 'manual'
```

`attempt=0` 在这条 reference path 中表示 legacy protocol attempt，是 migration sentinel，不是业务上“第零次 retry”。`lease_expires_at=NULL` 允许 legacy/manual row 没有 automatic-recovery lease；`recovery_policy=manual` 则确保旧 submit binary 不知道新 column 时，也不会偷偷把 legacy job 变成自动 retry job。

Starter initializer 还有一个重要 compatibility detail：`PRAGMA user_version` 只在当前值为 0 时初始化成 1。否则 frozen v1 code 在 expanded DB 上重新启动，会把 version 2 错写回 1，使真正要测试的 old-binary compatibility 被无关版本标记 bug 污染。

这些都是 reference choices。Separate attempts table 或其它 default-safe representation 也可以成立，只要相同 contract / migration evidence 能闭合。

## 6. Single winner 必须跨越 mixed protocol boundary

Starter 的 v1 algorithm 是 read candidate，再在另一个 connection 中 update；两个 callers 都可以成功返回同一 row。Historical reference 使用 conditional update，使 update 只有在 candidate 仍为 queued 时成功，并用 rowcount 判断 winner。

真正的 contract 不是“必须 CAS”，而是：同一个 queued row 在 concurrent claim history 中最多产生一个 successful receipt。Historical reference test 只验证了 v1-v1 两个 contenders 中恰有一个成功；这足以证明旧 race fix，却不足以证明 mixed rollout。

`BEGIN IMMEDIATE` transaction 或其它等价 atomic decision 也可能成立。这个 race fix 保持 v1 response shape，因此可以在 schema/protocol migration 前作为独立 change reasoning。等 v2 claim path 加入后，v1 与 v2 entry point 必须共享同一个 ownership invariant：至少 deterministic 验证 v1-v1 与 v1-v2；若 v2 是独立 claim path，再验证 v2-v2。不能因为两个版本各自单测为绿，就推断 coexistence history 合法。

## 7. Attempt identity 是 fencing authority，不是计数装饰

Reference v2 claim 返回：

```text
job_id
command
worker_id
attempt
lease_expires_at
```

每次新的 successful v2 claim 让 attempt monotonic 增长。Reference finish / heartbeat 的 acceptance condition要求 public id、`status=running`、worker_id 与 attempt 全部匹配 current row。

因此 history：

```text
attempt 1 running
→ lease expires / authorized recovery
→ attempt 2 starts
→ attempt 1 finish or heartbeat arrives
```

会被拒绝，而不是覆盖 attempt 2。

Legacy compatibility handler 也必须服从同一个 authority model。Historical reference 只允许旧 `job_id + exit_code` completion 完成 `attempt==0` 的 legacy attempt；如果 old handler 仍然只检查 `status=running`，它就会成为绕过 v2 fencing 的后门。但 `attempt==0` 只是 legacy-vs-v2 migration sentinel，不是 legacy execution identity：`legacy A claim → operator_requeue → legacy B claim → A late finish` 里两次 execution 仍都是 legacy domain，旧 payload 无法判断 A 已 stale。因此 reference 的 handler 隔离了 v2 fencing，却没有把 historical manual requeue 变成 fenced recovery。

## 8. Recovery policy 是 caller-facing contract

Reference automatic sweeper 不会把所有 expired running rows机械改回 queued。只有满足：

```text
status == running
AND recovery_policy == automatic_at_least_once
AND attempt > 0
AND lease expired
```

的 row 才进入 automatic recovery path。

所以 legacy submit 即使后来由 new worker claim，也仍保持 `manual` recovery，除非有另一个明确授权的 contract change。这个 qualifier 很重要：实现 automatic recovery 不能顺便改变旧 API 用户已经依赖的 execution semantics。`manual` 只表示 sweeper 不自动 retry；它不等于“operator 手工 requeue 后具有 fencing”。Migration window 若使用 historical `operator_requeue()`，operator 必须把可能的 stale completion / duplicate execution 当作已知 residual risk，并在 rollout/evidence 中留下可审查记录；对 duplicate execution 不可接受、又没有 effect-owner idempotency/fencing 的 workload，这条 escape hatch 不能被批准为“安全 recovery”。

## 9. Activation gate 是 semantic transition authority

Reference gate 输入至少包括：

```text
legacy_worker_count
running_legacy_attempt_count
rollback_reviewed
stale_attempt_evidence_passed
```

任一 blocker 未闭合时，automatic recovery activation 关闭；只有 legacy workers 和 legacy running attempts 都为 0、rollback 已重新审查、stale-attempt evidence 已通过时，gate 才允许进入下一 decision。

这里的 `may open` 不等于 gate 自己拥有 production authority。Gate 把“能否安全进入新 semantic phase”变成 observable condition，最终 activation 仍由被授权流程决定。

为什么 server 支持 v2 protocol 后不能立刻 recovery on？因为旧 worker 可能还活着，legacy attempt 没有 fencing identity，rollback target 仍可能是 v1 server。Protocol compatibility 与 retry-semantic activation 是两个 change。

## 10. Migration / rollback：representation compatible 不等于 semantic compatible

Historical reference rollout topology 是：characterize → fix v1-v1 claim atomicity → schema Expand → dual worker protocol → new opt-in submit → observability/gate → automatic recovery activation；v1 protocol removal 留给 later change。当前 clarified contract 还要求在 dual-protocol stage 用 runtime history 补上 v1-v2 single-winner（以及独立 v2 path 的 v2-v2）evidence，再进入后续 activation reasoning。

Expand-only 阶段，instructor 没有让 new code 用 `legacy=True` 自我模拟，而是保存一份 frozen starter。记录的 experiment 是：frozen code 创建 v1 DB；solution expand 到 schema v2；然后 frozen v1 code 再次 initialize、submit、claim、finish。结果记录为：

```text
frozen_before_expand=ok
expanded_version=2
frozen_after_expand=ok schema_version=2
```

这支持的是 **reference 的 Expand-only compatibility**，不是“所有 additive migration 都 rollback-safe”。

随后在另一个 DB 中，new system 创建并 claim v2 `attempt=1`，再换回真正的 frozen v1 server 处理旧 completion payload。记录的 counterexample 是：

```text
v2_attempt_active=1
frozen_server_accepts_unfenced_finish=True
```

因此原 issue 的“任意时刻都可以切回旧 server binary”被 runtime history 否定。Schema 仍可读，但旧 server 已经无法安全解释当前 semantic state。

Activation 之后的 recovery strategy 因此可能是 roll forward、disable recovery、或按事先设计的 state backup/recovery plan恢复，而不是默认启动旧 binary。

## 11. Reference evidence：14 passed 只是其中一部分

Instructor 在当时的临时 solution copy 中记录了：

```text
.............. [100%]
14 passed
```

其中 6 个是 baseline tests，8 个 focused reference tests 覆盖：expanded schema 下 legacy submit/manual default；**v1-v1** concurrent claim single winner；v2 attempt fencing 与 old-finish rejection；expiry→attempt2 后 stale finish/heartbeat rejection；manual job 不被 automatic sweeper requeue；gate blocker state；clean gate state；external duplicate negative control。

这里必须补一个 provenance limitation：那组 historical focused tests **没有**包含 v1-v2 concurrent claim arbitration。当前 D4 已把 mixed-window single-winner 明确成 normative contract，因此 `14 passed` 不能再解释为“完整证明了当前 clarified Capstone contract”。它仍是真实的 historical reference record，证明上面列出的那些局部 claims；mixed v1-v2（以及独立 v2 path 的 v2-v2）必须由当前 student candidate 另外产生 evidence。

Reference solution 本身也没有作为 canonical starter 发布，因此这个 `14 passed` 不是当前学生可以直接重放并据此宣称自己的 candidate 正确。学生必须在自己的 working copy 中产生独立 fail-before / pass-after、mixed-protocol claim、compatibility、negative-control 与 rollback evidence。

更高信息量的 reference evidence 其实是这些 history：

1. baseline v1-v1 double-claim fail-before；
2. historical post-fix v1-v1 one-success history；
3. frozen old artifact on expanded DB；
4. attempt1 expiry → attempt2 → stale finish rejected；
5. stale heartbeat rejected；
6. legacy finish only on legacy attempt；
7. manual job not auto-requeued；
8. activation gate closes on observable blockers；
9. duplicate external effect remains possible；
10. old server after v2 semantic activation accepts unfenced finish。

它们比单个 coverage 数字更直接对应本 change 的风险，但不是当前 clarified contract 的完整 acceptance set。当前还必须补 mixed v1-v2 claim single-winner evidence；historical baseline `operator_requeue()` stale-finish history则继续作为 legacy/manual residual-risk evidence，而不是“reference 应该把它修掉”的 pass-after target。

## 12. Reviewer 应该抓 contract-impacting counterexample

如果 candidate 只做：

```text
ALTER TABLE ADD lease_expires_at
sweeper: running → queued
finish handler unchanged
```

如果 candidate 把 automatic sweeper 用在这种 unfenced v1 path 上，应该 blocker，因为 stale v1 completion 没有 execution identity，requeue/reclaim 后仍可能完成 current row。反过来，如果 candidate 保留 human decision 授权的 historical manual `operator_requeue()`，这个 history 本身是已声明 residual risk；真正的 blocker 是把它写成“current-attempt fenced”或没有在 contract/rollout/operator evidence 中承认它。

另一个 blocker 是：v1-v1 与 v2-v2 各自都能 single-winner，但 v1 与 v2 同时竞争同一 queued row 时都拿到 success receipt。Mixed rollout 的 ownership invariant 跨 protocol entry point；不能用版本内单测替代 coexistence history。

如果 implementation 已正确 fence **v2 attempt state**，但 README 声称 arbitrary-command exactly-once，也应该 blocker：tests 只证明 TaskForge v2 lifecycle fencing，external-effect duplicate negative control明确证明两个 effects 仍可能发生。

如果 migration memo 写“columns additive，所以 old server 随时 rollback safe”，也应该 blocker：post-v2 counterexample 已证明旧 server 可以接受 unfenced transition。

Reviewer 不应把“我更喜欢 separate attempts table”“为什么不用 Postgres”“应该换文件名”等 preference 当 blocker，除非它能连到具体 contract、invariant、migration、failure 或 maintainability consequence。

## 13. Agent orchestration：快不等于拥有更大 authority

一个高质量 workflow 可以让 read-only Agent 分别恢复 state writers、protocol/compatibility surface、tests/evidence gaps；human 先裁决 guarantee contradiction；Implementation Agent 再按 bounded stage 改动；separate Review Agent 重建 change model；最后由 human/policy authority做 acceptance 与 rollout adjudication。

这不是要求固定五个 Agent。一个 Agent 可以承担多个上下文足够清楚的 bounded phase；关键是 implementation narrative 不应同时成为 product specification、verification oracle、review conclusion 与 production authority。

一个优秀的 implementation Agent 在看到原 issue 时完全可能先返回：它可以实现 lease mechanism，但当前 protocol 无法证明 arbitrary-command exactly-once，old finish 也不能区分 stale execution，需要 product/system decision 后才能继续 automatic requeue。这种 `STOP_AND_ESCALATE` 是高质量工程输出。

相反，如果 Agent 一次性加 lease、自动 requeue 所有 job、改 README 声称 exactly-once、修改旧 API、删除 old worker support、重构 DB、再以“all tests pass”宣布 deploy-ready，那么即使代码量很大，主要发生的是 authority drift。

## 14. Production evidence 也必须对准 contract

当前 production plan 至少应观察 worker protocol inventory、running attempt protocol、v1/v2 claim success、mixed-protocol ownership conflict/single-winner evidence、v2 stale finish/heartbeat rejection、lease requeue 按 recovery policy 的分布、legacy manual-requeue usage/residual-risk event，以及 gate state。

Diagnostic event 可以带 `job_id / attempt / worker_id` 做 trace/correlation；aggregate metric 不应把 `job_id` 当 label。CPU/memory 当然可能有运营价值，但除非它们映射到本 change 的 contract risk，否则不能代替 migration/gate/stale-rejection evidence。

真正 rollout 前，reviewer 和 operator 应能回答：旧 worker 是否真的清零？legacy running attempt 是否清零？mixed v1/v2 claim 是否仍 single-winner？manual job 有没有被 automatic sweeper touched？migration window 是否使用过具有 unfenced residual risk 的 manual requeue？v2 stale attempts 是否被拒绝？当前 state 还允许哪个 rollback path？如果这些答案没有 evidence，deployment command 退出 0 也不构成 rollout success。

## 15. Reference 没有解决什么

Historical reference 仍然没有覆盖：mixed v1-v2 concurrent claim arbitration、real distributed clock uncertainty、worker authentication、lease clock-skew policy、DB corruption recovery、多 server heavy contention、真实 production worker inventory implementation、external-effect idempotency、operator UI、schema downgrade tooling、v1 protocol removal。它也没有消除 legacy manual `operator_requeue()` 的 stale-completion risk；当前 contract 是明确保留并管理这条 migration residual risk。

这些不是“以后再说所以可以假装不存在”。它们应该进入 residual risk / explicit scope。Capstone 的目标不是把教学 TaskForge 伪装成生产级 scheduler，而是让学生知道本次 change 的 evidence 到哪里为止。

## 16. Instructor 的 acceptance 标准

一份接近合格线以上的 final statement 应先承认原 issue不可直接 merge：lease retry 不能为 arbitrary external commands 提供 exactly-once，v1 completion 也不能区分 stale executions。

在 human contract revision 之后，candidate 才可以逐条声称：v1-v1 claim race 已收敛且 response 保持；mixed v1/v2 claim 也满足 queued-row single-winner（独立 v2 path 时再覆盖 v2-v2）；schema Expand 有 frozen-v1 evidence；**v2** attempts fence stale heartbeat/finish；legacy jobs 保持 manual，historical manual requeue 的 unfenced stale-completion risk 被明确保留和管理；automatic at-least-once recovery 是显式 opt-in并受 migration gate约束；post-v2 state 下 old-server rollback 不再承诺；external-effect exactly-once 明确留在 TaskForge guarantee之外。

如果自己的 executable evidence、independent review、migration/rollback plan 与 production gate都支撑这些 claim，才可以给出 merge/rollout recommendation。若其中任何一项没有 closure，`NOT READY` 是比“为了完成 Capstone 而 APPROVE”更好的答案。

课程最后希望学生带走的不是 lease scheduler template，而是一种 change discipline：先恢复 what is true，再判断 issue 是否自洽；让正确 authority决定 what should be true；把 change 拆成可验证阶段；让 evidence 能否证 claim；让独立 review 可以推翻 author；最后才让 system state跨过 rollout boundary。Agent 可以加速其中大量工作，但不能替代这些 authority 与 evidence关系。
