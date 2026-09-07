# M13 Source Audit — Capstone synthesis

M13 不引入新的 software-engineering principle，也不新增一套“Capstone 专用最佳实践”。它的教学目标是检验 M00–M12 已审计内容能否在一个持续演化、约束互相作用的 change 中被组合使用。

因此本文件和前几章不同：**本轮没有因为 Capstone 再找一批新的知名材料来增加引用数量。** 所有 normative claims 都应能追溯到已经实际审计过的 module source audit；M13 只记录这些 claim 在 Capstone 中如何组合，以及哪些地方是课程自己的 synthesis。

---

## 1. 为什么不新增“Capstone 权威教材”

如果最后一章重新引入一套新的 architecture / reliability / Agent workflow 理论，会产生两个问题：

1. 学生可能靠背新 checklist 完成最后作业，而不是调用前十二章已经建立的 mental model；
2. 课程会把“综合能力”误写成“更多材料覆盖率”。

所以 M13 的 source policy 是：

```text
new claim
  → 必须回到已有 audited source

new synthesis
  → 明确标为 course synthesis

new empirical result
  → 必须实际运行 TaskForge capstone evidence
```

---

# 2. M13 使用的 audited claim map

## 2.1 Specification / invariant / behavior ownership

来源：

- `reading-notes/m02-source-audit.md`
- M01/M02 讲义中已完成的 MIT 6.102 / Stanford modular-design audit

Capstone 中使用：

- 先区分 requested behavior、existing behavior、accidental behavior；
- 明确谁拥有 lifecycle truth；
- 不允许 lease / attempt / recovery policy 形成第二份 semantic authority；
- 不能把 SQLite column 本身误当成 domain contract。

课程 synthesis：

> `attempt` 不是“为了存一个数字”；它是 current execution authority 的 fencing identity。

这个表达是 M01/M02/M07 概念在本题中的组合，不归因于某一份 source。

---

## 2.2 Testing / characterization / negative controls

来源：

- `reading-notes/m03-source-audit.md`
- `reading-notes/m06-source-audit.md`

已审计内容包括 MIT Testing、Software Engineering at Google testing chapters、Hypothesis、mutation testing、Feathers seams/characterization。

Capstone 中使用：

- baseline 6 tests 全绿不能证明 remote history 合法；
- deterministic barrier 用来构造 double-claim history；
- stale completion 必须有 fail-before / pass-after evidence；
- “state fencing 仍可能 external duplicate”是 deliberate negative control；
- frozen v1 binary 是 compatibility characterization artifact。

不使用：

- coverage target 作为 Capstone correctness 指标；
- “测试越多越好”；
- flaky timing race test。

---

## 2.3 Error / retry / idempotency semantics

来源：

- `reading-notes/m04-source-audit.md`

已审计内容包括 Google AIP error/retry/request-id guidance、AWS idempotent API、RFC 9110 等。

Capstone 中使用：

- retryability 必须是 semantic contract；
- logical retry identity 与 payload equality 不等价；
- “requeue”不是无语义的 scheduler operation，它改变 execution retry contract；
- arbitrary command 的 external effect 无法由 TaskForge SQLite 单独证明 exactly-once。

课程 synthesis：

> lease recovery 决定的是“TaskForge 何时允许另一个 attempt 成为 current execution authority”；它不自动拥有 command 外部副作用的 dedup authority。

---

## 2.4 Refactoring / change topology

来源：

- `reading-notes/m05-source-audit.md`

已审计内容包括 Fowler Refactoring、Kent Beck `Tidy First?`、Google small changes / large-scale changes。

Capstone 中使用：

- known claim race 应先形成独立 behavior-preserving protocol fix；
- schema expand、protocol migration、recovery activation 不应混成一个不可回滚 patch；
- structural preparation 与 semantic activation 分开；
- “最终设计合理”不能替代安全 migration path。

---

## 2.5 Concurrency / linearization / crash window

来源：

- `reading-notes/m07-source-audit.md`

已审计内容包括 MIT 6.102 concurrency、Herlihy–Wing linearizability、Google SRE/AWS retry/failure material。

Capstone 中使用：

- claim success history 需要 linearizable single winner；
- conditional update / transaction 是实现手段，不是 contract 本身；
- lease expiry、finish、heartbeat、requeue 存在真实 interleavings；
- current attempt 必须有可验证 fencing identity；
- final row 看起来正确不能证明历史正确。

---

## 2.6 Compatibility / migration / rollback

来源：

- `reading-notes/m08-source-audit.md`

已审计内容包括 Google AIP-180、Protocol Buffers evolution、Kubernetes deprecation policy、Fowler Parallel Change、Google dependency/deprecation material。

Capstone 中使用：

- schema compatibility 与 protocol semantic compatibility 分开；
- Expand → protocol migration → activation → later Contract；
- reader/writer version matrix；
- old binary rollback 必须用真实 old binary / frozen consumer 验证；
- binary rollback 与 system rollback 不等价；
- activation 可能形成 point of no safe old-binary return。

Capstone 的实际 reference 已验证：

```text
Expand only:
  frozen v1 binary can still read/write expanded v2 DB

After v2 attempt activation:
  frozen v1 server accepts an unfenced finish
```

因此“任意时刻 rollback old server”不是保守推测，而是被 runnable counterexample 否定。

---

## 2.7 Architecture / authority / failure domain

来源：

- `reading-notes/m09-source-audit.md`

已审计内容包括 SEI architecture framing、Fowler architecture/ADR、Stanford modular design、AWS cell-based guidance、Google SRE cascading failures。

Capstone 中使用：

- 不因为 remote worker problem 就自动加入 message broker；
- lifecycle current-attempt authority 仍由 TaskForge server/DB boundary 拥有；
- worker protocol 是 semantic boundary；
- external command effect 是另一个 authority/failure domain；
- rollback / activation gate 是 architecture consequence，而不是 deployment script 细节。

---

## 2.8 Code review / acceptance

来源：

- `reading-notes/m10-source-audit.md`

已审计内容包括 Google code-review guidance、Gerrit labels、Stanford review material、GitHub governance。

Capstone 中使用：

- author/Agent narrative 不是 acceptance evidence；
- reviewer 必须独立重建 system/change model；
- green baseline tests 不够；
- finding 按 root cause 聚合；
- review 必须检查 migration、rollback、residual risk，而不只看 implementation diff。

---

## 2.9 Production evidence / rollout gates

来源：

- `reading-notes/m11-source-audit.md`

已审计内容包括 Google SRE SLI/SLO/alerting/overload、Prometheus、OpenTelemetry。

Capstone 中使用：

- activation gate 必须依赖可观测条件，而不是“应该都升级完了”；
- 至少需要：legacy worker count、running legacy attempt count、stale-rejection evidence、rollback review；
- metrics 与 diagnostic identity 分开；
- rollout 成功不是“部署命令退出 0”，而是 system contract 在 production window 中有 evidence。

---

## 2.10 Agent orchestration

来源：

- `reading-notes/m12-source-audit.md`

已审计内容包括 OpenAI Codex current guidance、Anthropic agent harness/evals/parallel work、SWE-bench、METR、GitHub Copilot review behavior。

Capstone 中使用：

- Agent 获得 implementation authority，不自动获得 product guarantee / migration / merge / production authority；
- read-heavy reconnaissance 可以并行；
- shared-write implementation 必须有 scope/ownership；
- unresolved guarantee 应 STOP_AND_ESCALATE；
- Agent evidence 必须可由 reviewer 独立重放；
- implementation Agent 与 acceptance authority 分离。

---

# 3. Capstone 自己新增了什么？

新增的是 **composition**，不是新原则。

课程把前面分开的判断组合成：

```text
Issue claim
  ↓
System model
  ↓
Authority + invariant map
  ↓
Compatibility matrix
  ↓
Failure/interleaving model
  ↓
Staged change topology
  ↓
Agent delegation
  ↓
Executable evidence
  ↓
Independent review
  ↓
Rollout gate
  ↓
Production evidence
```

这个整体 workflow 是课程 synthesis。

不应把它引用成某个外部作者的标准流程。

---

# 4. Reference implementation 的证据边界

Instructor reference 在临时副本中实际验证：

```text
baseline tests + reference tests = 14 passed
```

其中关键 evidence：

1. v1 claim race 被 conditional claim 收敛到一个成功 worker；
2. schema v2 expand 对 frozen v1 binary 保持读写兼容；
3. v2 claim 生成 monotonic attempt；
4. lease expiry 后 attempt 2 接管；
5. attempt 1 stale finish / stale lease renewal 被拒绝；
6. legacy finish 不能完成 v2 attempt；
7. manual recovery job 不会自动 requeue；
8. activation gate 在 legacy worker / legacy running attempt 未清零时关闭；
9. 两个 execution attempt 仍可以各自产生一次外部 effect，证明 state fencing != external exactly-once；
10. v2 attempt 激活后 frozen old server 仍会接受 unfenced finish，证明 arbitrary old-binary rollback unsafe。

这些结果只证明 reference path 满足经过人类 decision 修正后的 Capstone contract；它们不是“所有 lease scheduler 的通用证明”。Reference solution 当时存在于临时 solution copy，并没有作为 canonical starter / 可直接复用的学生 oracle 一起发布；因此学生仍必须在自己的 candidate 上重新产生 fail-before / pass-after、compatibility、negative-control 与 rollback evidence，不能把这里记录的 `14 passed` 当作自己的 acceptance evidence。

---

# 5. 明确拒绝的 Capstone 伪规则

M13 不会教：

```text
Capstone 必须代码很多
Capstone 必须引入分布式基础设施
SQLite 不能做可靠系统
lease automatically gives exactly-once
CAS 一定优于 transaction
所有 old binary 永远必须可 rollback
所有 migration 都必须 expand-contract
Agent 越多越高级
测试全绿就完成 Capstone
必须实现 instructor reference 的具体结构
```

评分对象仍然是：

```text
mental model
contract judgment
authority placement
change localization
migration safety
evidence quality
review independence
Agent orchestration discipline
```

---

# 6. Module-level audit conclusion

M13 没有新增未经检查的“著名最佳实践”。

它只做三件事：

1. 重用 M02–M12 已实际审计的一手材料；
2. 对新的跨模块组合明确标注 course synthesis；
3. 对 Capstone 特有的 correctness / compatibility / rollback claims 使用实际 TaskForge runtime evidence，而不是凭声望或直觉断言。
