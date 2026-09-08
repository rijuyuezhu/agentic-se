---
id: lab-M13
type: lab
visibility: student
related: [M13]
---
# Lab 13 — Capstone：把 Lease Recovery 做成一份可接受的 Change

这是整门课的综合考核。你会拿到一个已经存在的 TaskForge、一个包含错误 guarantee 的 feature request、一套全部绿色但不完整的 baseline tests、可确定性复现的 failure probe，以及一份只有在 first-pass issue review 完成后才应该读取的 human decision pack。

目标不是“实现一个 lease scheduler”。最终要交的是一份可以独立审查、可以重放 evidence、可以解释 migration/rollback，并且没有把 product / compatibility / production authority 偷偷交给 Agent 的完整 change record。

## 0. Starting point 与不可跨越的边界

Starter 位于：

```text
labs/taskforge/capstone-starter/
```

第一次进入时只读 `README.md`、`ISSUE.md`、current source、tests、fixture 与 baseline probe。**不要先读**：

```text
decision-pack/01-after-issue-review.md
```

也不要立刻修改 canonical starter。实际实现放在你自己的 branch / disposable working copy 中，并保留一个未修改 baseline 以便重放 fail-before evidence。

整个 Lab 必须保持以下边界：

1. 原 issue 不是 specification authority；contradiction 必须先被识别并升级。
2. Human decision pack 是本题 product/system authority；implementation Agent 不能重新定义它。
3. Legacy public API、worker protocol 与 durable schema 都是 compatibility surfaces，不能只凭“代码能跑”判断兼容。
4. TaskForge 只可声明自己有 evidence 支撑的 guarantee；arbitrary external command exactly-once 不能仅由 TaskForge 自己的 local lifecycle state 推出来。
5. Agent 不拥有 merge、release、activation、residual-risk acceptance 或未授权 architecture expansion authority。
6. `STOP_AND_ESCALATE`、`REQUEST_CHANGES`、`NOT_READY_TO_ROLLOUT` 都可以是正确最终状态。

## 1. Phase 0 — 复现 baseline，而不是先相信绿测试

运行：

```bash
cd labs/taskforge/capstone-starter
PYTHONPATH=src uv run --with pytest --no-project python -m pytest -q
PYTHONPATH=src uv run --with pytest --no-project \
  python tools/capstone_baseline_probe.py
```

Canonical starter 当前应得到 `6 passed`，随后 probe 应稳定展示：

```text
successful_claims=job-1,job-1
workers_returned_success=2
history_is_illegal=true

stale_finish_accepted=true
```

保存 raw output。你的 baseline note 至少回答：schema version / columns 是什么；legacy submit response 是什么；为什么两个 claim success 不能被最终单 owner row 抹掉；operator requeue 后为什么旧 completion 仍能成功；现有六个 tests 分别证明了什么、没有证明什么。

这份 evidence 是后面所有 change claim 的 fail-before 基线。

## 2. Phase 1 — First-pass Issue Review：先证明 issue 是否可实现

只根据 `ISSUE.md`、current code 与 Phase 0 evidence，创建：

```text
submission/01-issue-review.md
```

至少分成四类：

- **Explicit requirements**：逐条保留原 issue 的实际要求，不先改成你希望的版本。
- **Existing contracts / compatibility surfaces**：public submit response、SQLite schema、v1 claim response、v1 finish payload、maintenance behavior 等。
- **Assumptions**：例如 lease expiry 是否意味着旧 process 已停止、requeue 是否意味着旧 execution 不会再产生 effect、additive schema 是否自动意味着任意 old-binary rollback safe。
- **Contradictions / unresolved decisions**：标成 `IMPLEMENTABLE AS WRITTEN` / `AMBIGUOUS` / `CONTRADICTORY` / `NEEDS AUTHORITY DECISION`。

必须单独分析这一条 failure window：

```text
worker performs external effect
→ TaskForge does not observe completion
→ worker disappears / partition persists
→ timeout recovery executes the job again
```

回答 TaskForge 自己的 SQLite 能否区分“第一次 effect 没发生”和“effect 已发生但 completion 丢了”。如果不能，就不能把原 issue 的 arbitrary-command exactly-once 当成 implementation detail。

### Gate A — Freeze first-pass reasoning

在读取任何答案前，把 `01-issue-review.md` 冻结成稳定 checkpoint（commit、tag、patch artifact 或等价 immutable snapshot）。记录 snapshot id。

这个 gate 是 graded evidence：它保留你在没有 human answer 时真正发现了什么。

## 3. Phase 2 — Human Decision 与 decision delta

现在读取：

```text
decision-pack/01-after-issue-review.md
```

创建：

```text
submission/02-decision-delta.md
```

对 D1–D7 至少标记 `I FOUND IT` / `I PARTIALLY FOUND IT` / `I MISSED IT`，并解释差异。必须覆盖：

- arbitrary-command exactly-once 被撤回，automatic recovery 是 at-least-once；
- current-attempt fencing guarantee 只覆盖 v2 attempt protocol；legacy/manual v1 requeue/reclaim 保留 stale-completion residual risk；
- legacy submit 保持原 response，默认 manual recovery；
- 新 opt-in `automatic_at_least_once` surface；
- monotonic attempt identity 与 fenced heartbeat / finish；
- v1 finish 只能完成 legacy attempt，但不能区分 manual requeue 前后的两个 legacy executions；
- existing v1-v1 claim race 必须在 mixed rollout 前修复；mixed window 中所有 active claim protocols 还必须共享 single-winner invariant；
- Expand → protocol migration → activation gate → later Contract；
- post-v2 state 下不再承诺任意 old-server binary rollback。

不要把“我和答案不同”自动算错。真正需要解释的是：你的 first-pass reasoning 是证据不足、遗漏 authority、还是选择了 human decision 未授权的 guarantee。

## 4. Phase 3 — 恢复 system model 与 contract

接下来创建三份相互引用但职责不同的 artifact：

```text
submission/03-system-model.md
submission/04-contracts.md
submission/05-design-memo.md
```

### System model

至少恢复五个 view：

| View | 必须能回答的问题 |
|---|---|
| Responsibility / knowledge | `api.py`、`service.py`、`db.py`、`remote_worker.py`、`maintenance.py` 与 external effect owner 各知道什么？ |
| Authority / state | 谁拥有 job lifecycle、current attempt、worker identity、recovery policy、lease state、external-effect dedup？ |
| Runtime protocol | submit / claim / heartbeat / finish / expiry / requeue / new claim / stale message 如何交错？ |
| Durable / compatibility | schema v1/v2、server v1/v2、worker v1/v2、legacy/default policy 如何组合？ |
| Failure / rollback | worker crash、partition、late finish/heartbeat、expand-only、semantic activation、server rollback 会怎样？ |

不能用一张 deployment diagram 代替这些问题。尤其要分别回答“谁知道 current attempt？”与“谁知道 external effect 是否已经发生？”

### Contract inventory

建议表格：

| Surface | Existing contract | New contract | Must remain | Explicit non-guarantee |
|---|---|---|---|---|

至少覆盖 legacy submit、v2 opt-in submit、v1 claim、v1 finish、v2 claim、v2 heartbeat、v2 finish、automatic recovery、schema migration、rollback。并把三个跨 surface obligation 单独写清：v2 current-attempt fencing 的 guarantee scope；historical legacy/manual `operator_requeue()` 的 unfenced stale-completion residual risk；mixed v1/v2 claim entry points 共享 queued-row single-winner invariant。

必须明确写出：

```text
TaskForge does NOT guarantee exactly-once external effects
for arbitrary commands.
```

如果你要提出更强 guarantee，必须说明 effect owner 如何参与，并取得额外 product/architecture authority；不能只在 TaskForge DB 中增加一个字段。

### Design memo

至少回答 current problem、desired semantics、preserved semantics、non-goals、claim atomicity、mixed-protocol ownership、v2 attempt/fencing design、legacy manual-requeue residual risk、recovery policy、schema evolution、protocol compatibility、activation gate、rollback boundary、external-effect residual risk 与 rejected alternatives。

比较至少两个真正 plausible implementation shape，例如 jobs-table attempt columns vs separate attempts table，或 conditional update vs explicit transaction。Reference shape 不是规范；荒谬 strawman 也不算 design comparison。

## 5. Phase 4 — State machine 与 compatibility matrix

把 **v2 current execution** 明确建模。Human decision 之后，一条最小 conceptual state path 是：

```text
queued
  ↓ claim attempt=1
running(a1)
  ├─ finish(a1) → terminal
  └─ lease expires / authorized recovery
       ↓
     queued
       ↓ claim attempt=2
     running(a2)
```

对 `finish(a1)` 或 `heartbeat(a1)` 在 a2 成为 current 后到达的情况，写出 machine-checkable acceptance predicate。可以采用不同 representation，但不能只说“忽略 stale worker”。

随后创建：

```text
submission/06-compatibility-matrix.md
```

至少分析：old server + schema v1；new server 在 migration 前面对 schema v1；old server + expanded schema；new server + old worker；new server + new worker；mixed workers；historical legacy manual requeue；以及 **v2 attempt state 已经出现后切回 old server**。`mixed workers` 行必须明确 claim ownership 是否跨 v1/v2 entry point single-winner；manual-requeue 行必须明确它是 residual-risk exception 而非 v2 fenced recovery。最后一行不能因为旧代码能读 column 就直接写 `PASS`。

## 6. Phase 5 — Staged plan 与 Agent delegation

创建：

```text
submission/07-staged-plan.md
submission/08-agent-plan.md
```

每个 implementation stage 必须写：Goal、Allowed scope、Changed/preserved contract、Evidence、Rollback/reversal、Stop/escalate conditions。

一种合理但非唯一的 decomposition 是：

```text
S0 characterize
S1 fix v1-v1 claim atomicity
S2 schema expand
S3 dual worker protocol + cross-protocol claim ownership + v2 attempt fencing
S4 opt-in automatic_at_least_once submission
S5 observability + activation gate
S6 automatic recovery activation
later: remove v1 protocol (out of scope)
```

不要为了贴合 reference 强制使用相同 commit 数。真正要求是：race fix、representation expand、protocol coexistence 与 semantic activation 可以分别 reasoning 和验证。

Agent plan 至少定义：

- **Reconnaissance Agent**：read-only，输出 state writers、protocol entry points、DB queries、tests/fixtures、compatibility surfaces。
- **Implementation Agent**：每个 stage 单独授权 Goal、Allowed write paths、Invariants、Forbidden actions、Evidence contract、Stop conditions。
- **Review Agent**：与 implementer 使用 separate context/session；重新读取 issue、human decision、candidate diff、raw verification evidence、migration/rollback artifacts，不把 implementer summary 当事实来源。

Read-heavy reconnaissance / compatibility / test audit 可以并行；shared-write implementation 只有在 ownership 明确时才拆。Agent 数量本身不评分。

## 7. Phase 6 — 一次只实现一个 stage

Implementation 可以使用 Agent，但一个 stage 完成后先保存 raw evidence、自审 diff、记录未解决问题，再决定是否进入下一 stage。

如果执行中发现必须改变 human decision、扩大 architecture、改变 legacy response、放宽 activation gate、删除 v1 support、重新声称 exactly-once 或取得 merge/deploy 权限，先 `STOP_AND_ESCALATE`。不要用“顺手做掉”把 staged plan 变成事后文档。

## 8. Required Evidence — 八个不能被 full-green 替代的 proof obligations

最终 `EVIDENCE.md` 必须把 claim 映射到 command、observed result、negative control / limitation。以下八组 evidence 都是 mandatory；实现 shape 可以不同。

### A. Claim ownership across the migration window：fail-before / pass-after

Baseline 已稳定得到 v1-v1 两个 success receipts。先证明修复后的 v1-v1 deterministic interleaving 对同一 queued row 最多一个 success receipt；只展示 final row 一个 worker 不算 pass-after。

然后把同一个 invariant 扩到 mixed protocol coexistence：至少 deterministic 构造 **v1 claimant vs v2 claimant** 同时竞争同一 queued row，并证明最多一个 success receipt。若 v2 使用与 v1 不同的 claim path，还要说明并验证 v2-v2；若多个 entry point 最终共享同一原子 ownership primitive，也要用 history evidence 证明这个共享确实覆盖所有 active protocol，而不是只从代码形状推断。

### B. Schema Expand + frozen v1 consumer

实际验证：

```text
v1 DB
→ new migration expands schema
→ frozen v1 code still reads/writes legacy contract
```

至少覆盖 old public submit、old claim、old finish，并确认旧 initializer 不会把 schema version 意外降级。不要用 new code 的 `legacy_mode=True` 冒充真正 frozen artifact。

### C. Attempt fencing

构造：

```text
attempt 1 claim
→ lease expires / recovery requeues
→ attempt 2 claim
→ attempt 1 finish
→ attempt 1 heartbeat
```

两条 stale message 都必须被拒绝，current attempt 不得被覆盖。

### D. Legacy finish compatibility

Migration window 中，v1 `job_id + exit_code` completion 仍可完成 legacy attempt；同一个 handler 不得完成已经进入 v2 attempt protocol 的 row。否则 compatibility path 会绕过 **v2** fencing。

同时必须把另一条边界写进 evidence：v1 payload 没有 attempt / worker identity，因此它不能区分 `legacy A claim → operator_requeue → legacy B claim → A late finish`。本题 human decision 明确把这条 historical manual-requeue path 留作 migration residual risk，而不是 current-attempt fencing guarantee。至少重放 baseline stale-finish history，并在 contract / rollout artifact 中标成 residual risk，而不是把它误判成 v2 fencing regression。

### E. Recovery policy

证明 legacy/default `manual` job 即使 lease expired 也不会被 automatic sweeper requeue；只有显式 opt-in automatic job 才能按授权 policy requeue。另写清 historical `operator_requeue()` 是人工 emergency exception：如果 migration window 中使用它，operator 必须接受/记录 unfenced legacy stale-completion 风险；对 duplicate execution 不可接受且没有 effect-owner idempotency/fencing 的 workload，rollout/operator plan 不得把这条 escape hatch 当作安全 recovery。实现也不能把“manual”偷换成“安全 fenced retry”。

### F. External-effect negative control

主动构造两个 **v2 attempts** 各自产生一次 external effect，同时 stale v2 finish 仍被正确 fence。这个 test/probe 的期望结果是“duplicate effect 仍可能发生”。它验证的是 non-guarantee，不是要求你把它修成 exactly-once。

### G. Activation gate

至少让 gate 依赖：

```text
legacy_worker_count == 0
running_legacy_attempt_count == 0
stale-attempt rejection evidence passed
post-activation rollback semantics reviewed
```

测试任一 blocker 存在时 gate closed，全部满足时 gate 才 **may open**。最终 activation 仍属于授权 decision，不是 bool 自动赋予 release authority。

### H. Rollback boundary

做两组真实实验：

1. Expand-only：frozen v1 code → v1 DB → new expand → frozen v1 code again，验证这一阶段的 old-binary compatibility。
2. v2 attempt semantics 已使用后：new system 写入/claim v2 attempt → 切回 frozen old server → old finish payload，观察旧 server 是否会接受 unfenced transition。

如果第二组证明旧 server 不理解 fencing，就把 `simple old-binary rollback unsafe` 写进 rollout plan；不要用 schema readability 覆盖这个 counterexample。

## 9. Phase 7 — Production evidence 与 rollout gates

创建：

```text
submission/09-production-evidence.md
submission/10-rollout.md
```

Production evidence plan 至少定义：legacy worker inventory、running legacy attempts、v1/v2 claim success、mixed-protocol claim conflicts/single-winner evidence、v2 stale finish / heartbeat rejection、automatic requeue、manual-policy violation、legacy manual-requeue usage/residual-risk event，以及 recovery gate state。对每个 signal 写清它支持哪个 decision、适合 metric/event/log 哪一种表示、有什么 cardinality 风险。

`job_id / attempt / worker_id` 可以保留在 diagnostic events 做 correlation；不要把 `job_id` 当 aggregate metric label。

Rollout plan 至少写三阶段：Expand、Protocol Migration、Activation。每阶段写 entry condition、exit condition、failure action 与 rollback/reversal semantics。对 mixed claim ownership violation、v2 stale rejection spike、legacy worker 重新出现、manual job 被 automatic sweeper requeue、legacy manual requeue 后出现 ambiguous/stale completion、migration partial failure 等 scenario 给 operator action。

不要把 activation 写成“星期二十点开开关”。它必须引用 Phase 8 的 observable gate 和当前 rollback boundary。

## 10. Phase 8 — Independent Review：reviewer 必须能推翻 author

Implementation 完成并冻结 candidate snapshot 后，启动 separate Review Agent context/session。Review Agent 第一轮不要先读 implementer 的“全部正确”总结；给它 base/current code、issue、human decision、candidate、raw evidence 与 migration artifacts。

Review 至少重建七类问题：

| Area | 必查问题 |
|---|---|
| Issue / contract | 有没有重新声称 exactly-once？v2 fencing scope、legacy manual-requeue residual risk、legacy submit/default recovery 是否被准确表达？ |
| State authority | v2 current attempt 是否唯一？legacy handler 能否绕过 v2 fencing？是否错误声称 v1 manual requeue 也有 fencing identity？ |
| Concurrency | v1-v1、v1-v2（以及独立 v2 path 的 v2-v2）claim 是否共享 single-winner history？expiry vs finish、stale heartbeat 是否有 evidence？ |
| Migration | Expand 是否真的由 frozen old artifact 验证？mixed-version claim/finish path、legacy manual exception 与 gate 是否成立？ |
| Rollback | 哪个 phase 可 old-binary rollback，哪个 state 之后不能？ |
| Evidence | 有没有 fail-before、negative control、version-scoped oracle、残余 uncertainty？ |
| Scope | 是否出现无 authority 的 infrastructure、cleanup、v1 deletion 或 guarantee change？ |

Review Agent 给 `APPROVE` / `REQUEST_CHANGES` / `SPLIT` / `NEEDS_AUTHORITY_DECISION` 之一，并让每个 material finding 指向 reproducer / evidence 与 contract impact。

这一步是 **independent review reasoning**；runtime probes、tests、static checks 属于 verification evidence，不能替代 reviewer 的 change-model reconstruction。

## 11. Phase 9 — Human adjudication 与 acceptance closure

Human/policy authority 逐条 adjudicate Review Agent 的 material findings：事实是否成立、是否命中已承诺 contract、修复是否仍在当前 authority 内、是否需要 split/new decision。把这段 closure 追加到 `submission/11-independent-review.md` 的独立 **Human Adjudication** 小节，并清楚区分 reviewer finding 与最终 authority decision。

只有 review findings、verification evidence、migration/rollback boundary 与 rollout gate 全部有 closure 后，才能给 candidate 最终 `MERGEABLE` / `NOT MERGEABLE`，以及 `READY_TO_ROLLOUT` / `NOT_READY_TO_ROLLOUT` 判断。Implementation Agent 和 Review Agent 都不能单独赋予这些 authority。

如果 negative control 证明 external duplicate effect 仍可能发生，而 author summary 声称“exactly-once recovery complete”，应以 evidence 推翻 author；不要为了保留一个漂亮结论改 test 或弱化 non-guarantee。

## 12. Phase 10 — Retrospective：判断究竟发生在哪里

创建：

```text
submission/12-retrospective.md
```

至少回答：三个最重要的 human/product authority decisions 是什么；哪些 repo/evidence 工作最适合 Agent；Agent 实际最容易在哪里越界；哪些 guardrail 可以从 prompt 迁移到 test/tool/policy/gate；如果重做会不会改变 change topology，以及为什么。

不要把 retrospective 写成“人负责思考、Agent 负责写代码”。真正要回看的是 knowledge、state authority、verification oracle、review independence 与 production decision 分别被放在哪里。

## 13. Submission layout

最终至少提交：

```text
submission/
  01-issue-review.md
  02-decision-delta.md
  03-system-model.md
  04-contracts.md
  05-design-memo.md
  06-compatibility-matrix.md
  07-staged-plan.md
  08-agent-plan.md
  09-production-evidence.md
  10-rollout.md
  11-independent-review.md
  12-retrospective.md

EVIDENCE.md
```

`EVIDENCE.md` 至少记录 baseline pytest、baseline probe、v1-v1 race fail-before/pass-after、mixed v1-v2 single-winner evidence（独立 v2 path 再含 v2-v2）、schema expand + frozen old artifact、v2 stale finish/heartbeat fencing、legacy finish boundary、legacy manual-requeue stale-completion residual history、manual-vs-automatic recovery、external duplicate negative control、activation gate、rollback boundary 与最终 focused/full test commands。不要只写“见 CI”。

课程维护侧保留 instructor-only analysis。Student-facing build 不生成或导航到它；完成自己的 submission 后，如由课程组织者提供，它只是一条 reference reasoning path，不是标准实现。

## 14. Grading

M13 占课程总评 30%；以下是 Capstone 内部的 100 分 rubric：

| Dimension | Points | High-quality evidence |
|---|---:|---|
| Mental model | 20 | ownership / attempt / external-effect boundary、failure history 准确 |
| Issue / contract reasoning | 15 | 独立识别 contradiction、non-guarantee 与 authority escalation |
| Change localization | 15 | staged claims/evidence/reversal，避免万能 cleanup PR |
| Migration / rollback | 15 | version matrix、frozen old artifact、rollback boundary、observable gate |
| Evidence | 15 | deterministic histories、fail-before/pass-after、negative controls、limitations |
| Independent review | 10 | separate reasoning path 能否证 author，findings 有 reproducer/root cause |
| Agent orchestration | 10 | bounded delegation、正确 escalation、human acceptance authority 保留 |

Automatic deductions 保留 merge-base 的权重：

| Deduction | Trigger |
|---:|---|
| -20 | 没有 first-pass issue review 就直接读 decision pack |
| -20 | 仍声称 arbitrary command exactly-once，且没有 effect-owner idempotency/fencing mechanism 与对应 evidence |
| -15 | 没有 migration / rollback runtime evidence |
| -15 | 只检查 final DB state，不验证 concurrent history |
| -10 | Agent 被授权改 guarantee、merge、deploy 或 activation，但没有明确 human/policy authority |
| -10 | 为了“更现代”引入大型 infrastructure，却没有证明 current requirements 需要这次 architecture expansion |

## 15. Final question

最后用一页回答：

> **为什么这次 change 现在应该被 merge / rollout，或者为什么它还不应该？**

答案必须自然压缩 contract、system/authority model、migration state、failure history、raw evidence、independent review、residual risk 与 operational gate。`tests pass` 只是其中一个 signal，不是整个结论。
