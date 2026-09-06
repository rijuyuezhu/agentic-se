# M08 Instructor Analysis — Snapshot v1 → v2 的 compatibility migration

> **Spoiler warning**：请先完成 `labs/08-compatibility-migration.md`。

M08 的 reference judgment 不是“哪段 parser code 最漂亮”，而是先确定这一轮 change **有权改变什么、还没有权改变什么**。TaskForge 的教学目标是从 v1 flat `command` 走向一个 v2 `task={kind, command}` representation，但这个 v2 shape 只是本实验选定的 migration target candidate；它不是由前置模块自动推出的唯一产品设计。

在这个 candidate 下，当前最重要的事实是：frozen R1 无法读取 W2。因此 reference 不会把“R2 能写 v2”偷换成“production 现在可以默认写 v2”。本轮代码最多完成 **capability expansion**：R2 能读取 v1/v2，默认 writer 仍产生 v1。Reader migration、writer cutover 和后续 cleanup 都需要各自的证据与授权。

## 1. 先冻结旧世界，而不是先写新 parser

Starter 的 `src/taskforge/snapshot.py` 暴露了一个简单 v1 format：root 有 `schema_version = 1` 与 `jobs` array；每个 job 含 `id / command / status / exit_code`。`dumps_current_snapshot()` 还会保持 `service.list_jobs()` 的顺序，用 UTF-8 JSON、`indent=2` 和 trailing newline 写出文本。

这里必须区分 contract 与 observation。Job field meanings、ordering、schema identity、status/exit-code semantics，以及历史 v1 仍能被支持的 reader 读取，是本实验明确要求保持的 surface。Exact indentation/whitespace 目前只是 implementation formatting；除非发现真实 consumer 依赖 byte representation，不能因为某个 golden test 恰好比较文本就把它自动升级成 public contract。

这正是 M03 的 evidence lesson：测试应该验证既有 contract，而不是凭自己存在就创造 contract。

### Historical fixture 是过去 producer 留下的证据

`fixtures/m08/snapshot-v1.json` 不是普通可随 implementation 重写的 fixture。它代表一个已经存在于过去世界里的 durable artifact。Reference 因此保持它 byte-for-byte 不变。

如果实现 v2 时顺手把 fixture 改成 v2，current tests 可能仍然全部通过，但下面这条最重要的 evidence 已经消失：

```text
historical W1 data -> current/new reader
```

保留 fixture 原样并不意味着它的每个空格都被宣布为永久 public API；这里冻结 bytes 的理由是防止测试输入随 producer 一起漂移。

### Frozen R1 是已经部署 consumer 的模型

`tools/m08_compat_probe.py` 中的 `_legacy_v1_reader()` 故意不跟着本轮 PR 改。它只接受 `schema_version == 1`，并直接读取 `job["command"]`。这个小函数的价值不在于复刻旧 binary 的全部实现，而在于把一个关键边界变成 executable evidence：**有 consumer 不受当前 patch 控制。**

Current writer -> current reader 的 round-trip 只能说明“今天两边同意一个 contract”；current writer -> frozen R1 才能回答 rollout 中旧世界是否还能工作。

## 2. Baseline probe 已经给出了 migration 的约束

在 starter 上运行：

```bash
cd labs/taskforge
PYTHONPATH=src uv run --with pytest --no-project python tools/m08_compat_probe.py
```

会得到五类现象：历史 v1 data 当前可读；当前 W1 输出可被 frozen R1 接受；frozen R1 会拒绝教学 v2；starter R1 也还不会读 v2；unknown future version 被明确拒绝。

把它写成 matrix 后，reference 要求非常直接：

| Writer / artifact | Reader | 结果 |
|---|---|---|
| current/default W1 | frozen R1 | PASS |
| W1 / historical fixture | R2 | PASS |
| W2 candidate | R2 | PASS |
| W2 candidate | frozen R1 | FAIL，已知且允许 |
| future W99 | R2 | explicit reject |

最重要的一格反而是红色的 `W2 -> R1`。它不是 reference implementation 的 bug，而是 rollout constraint。只要 R1 仍可能读取 shared snapshot，production 默认 writer 就不能擅自打开 W2。

这也是为什么“backward compatible”作为一句话太弱。这里真正重要的是 producer version、consumer version、direction、surface、semantic expectation 和时间窗口。

## 3. Reference parser 先把 wire evolution 收在 boundary

在 reference candidate 中，v1 与 v2 的区别只属于 snapshot wire boundary：

```text
_decode_v1_job(raw)
_decode_v2_job(raw)
        |
        v
SnapshotJob(id, command, status, exit_code)
```

Domain code 不需要到处出现 `if schema_version == ...`。v1 flat `command` 和 v2 `task.command` 都 normalize 成同一个内部 `SnapshotJob.command`。

这不是“所有 version migration 都应该 normalize 成一个 model”的通用答案，而是当前 change 的一个合理 candidate：两个 wire forms 的 domain meaning 目前相同，M04 已经给了我们一个合适的 representation boundary。

### `task.kind` 不能被“宽容解析”掉

V2 candidate 的关键不是 object nesting，而是增加了 semantic discriminator：

```json
{
  "task": {
    "kind": "shell",
    "command": "echo hi"
  }
}
```

如果 parser 只取 `task.command` 而忽略 `kind`，未来看到 `kind = "http"` 时就可能按 shell semantics 解释非 shell task。那不是 forward compatibility，而是 semantic misinterpretation。

因此 reference 对 unknown `task.kind`、missing task、missing command、wrong type 都明确 fail closed。相同理由支持 starter 对 unknown future schema version 的 explicit rejection：reader 不知道新 representation 是否仍能按照旧 semantics 安全解释。

`ignore unknown fields` 可以是某些 representation 的 compatibility rule，但绝不能被提升成普遍 parser philosophy。

## 4. Reference 把 capability 与 rollout authority 分开

Reference 可以选择完全不提供 W2 writer，只在 tests 里构造 v2 input；也可以在一个**假想 reference implementation**里提供显式 `dumps_current_snapshot(format_version=2)`，用于 fixture generation 或 integration evidence。

关键是默认值仍然保持 W1。换句话说：

```text
Can write W2
!=
May make W2 the production default now
```

新 binary 拥有 capability 是 implementation fact；是否打开 capability 是 rollout authority。把这两件事拆开，是这一章最重要的 design-authority boundary 之一。

## 5. Parallel Change 到 TaskForge 时要多看见一个 durable event

Fowler/Danilo Sato 的 Parallel Change 原文把 interface change 分成三个阶段：Expand supplier interface、Migrate clients、Contract old interface。Reference 保留这个来源的原义，不把阶段名称重新解释。

但 TaskForge 是 durable producer/consumer format。即使所有 clients 已迁到 R2，系统还需要一个独立的时点决定：**从什么时候起，production writer 可以开始产生 v2 durable data？**

所以本 case 使用下面四个 operational events：

### Event E — Expand capability

新 release 的 reader 能读 v1/v2；production default writer 仍是 W1。

这一 event 的目标只是让 supplier side 支持 new representation，而不破坏 old world。它完成后并不能声称 fleet 已经没有 R1。

### Event M — Migrate readers / consumers

逐步升级所有仍受支持、且可能读取 shared snapshot 的 consumer：daemon、CLI、offline repair tool、backup restore image、supported rollback binary 等。

Exit criterion 不应写成“new release deployed”。更有意义的是：

```text
all supported readers that may observe shared snapshot are known to be R2-capable
```

如果某类 consumer 无法 inventory，则 writer cutover 要么继续被阻止，要么产品明确终止对那个 consumer 的支持。Reference 不允许通过“不知道”把它从 matrix 里删除。

### Event W — Writer cutover

只有 reader migration evidence 闭合后，才单独审查 W1 default -> W2 default。

这一步会改变 durable data universe。一旦第一份 v2 snapshot 写出，rollback 到只会 R1 的 binary 可能不再成立。因此 W2 cutover 需要独立 rollout evidence 和 rollback analysis。

这里不把 cutover 称为普遍“不可逆”。如果系统有可靠 down-conversion、rollback target 能读 v2，或新 representation 本身兼容旧 reader，它仍可能可逆。Reference 只声明当前 TaskForge teaching candidate 的事实：**W2 -> R1 已知失败，所以 cutover 会缩小当前 rollback-compatible target set。**

### Event C — Contract / cleanup

Writer 已稳定到 W2 后，也不能自动推出“现在可以删所有 v1 reader”。历史 v1 data 可能仍属于长期 support policy。

产品可以选择：

- 永久支持 v1 import，此时 v1 decoder 是 intentional feature；
- 给 v1 明确 EOL，再配 conversion/release note/deadline/data inventory；
- 停止 W1 的时间和删除 v1 reader 的时间不同。

Contract 的目标是结束 transitional burden，而不是因为 pattern 名字叫 contract 就机械删除所有 old-format support。

## 6. Rollback analysis 随 event 改变

这四个 event 让三个常见 rollback case 的差别很清楚。

### Capability 已扩展 / readers 已迁移，但仍只写 W1

此时 snapshot data 仍是 v1。对 format 来说，rollback 到 R1 通常是安全的。Reader rollout 可能有别的 bug，但它没有留下 R1 无法解释的新 durable state。

这就是为什么 capability expansion 和 reader migration 有很好的 representation-level reversibility。

### W2 已经写出 durable data，再 rollback R1

此时 frozen/old R1 会 decode failure。Binary rollback button 并不等于 system rollback safe。

Reference 因此要求 writer cutover 的 change 独立回答：supported rollback target 是谁？它能不能读 v2？有没有 down-conversion？是否存在 data migration/reconciliation requirement？

### 主 fleet 已 R2，但还有 offline R1 tool

这个 tool 仍是 consumer。合理策略可能是 writer cutover 前先升级/退役 tool、提供 explicit export-v1、长期保持 W1，或者给 tool 增加 conversion layer。Reference 不替产品选，但要求它出现在 compatibility inventory 中。

## 7. 为什么 reference 不用 dual field “兼容一切”

一个看似聪明的做法是让 W2 同时保留：

```json
{
  "command": "echo hi",
  "task": {"kind": "shell", "command": "echo hi"}
}
```

这样 old R1 也许还能工作。但它立即引入两个 command copies：哪一个 authoritative？如果两者不一致怎么办？writer bug 只更新一个怎么办？

这不是说 dual representation 永远错误。它在某些系统里可能值得，但对当前小型 migration，reader-first rollout 已经能避开同步切换，dual field 反而新增 authority 与 reconciliation surface。Reference 因此不选择它。

同样，dual-write filesystem 或两份 store 会把 M02/M07 的问题带回来：partial failure、retry、reconciliation、single source of truth。任何 dual-write proposal 都必须先建立 authority model，不能只凭“这样两边都兼容”获得 design authority。

## 8. 兼容矩阵决定测试，而不是反过来

Reference evidence 至少包括：

- historical v1 fixture -> R2，验证 `id / command / status / exit_code / ordering`；
- default W1 -> frozen R1；
- v2 input/explicit W2 -> R2；
- explicit W2 -> frozen R1 明确失败；
- malformed v2 task cases fail closed；
- unknown future version fail closed。

`W2 -> frozen R1` 的失败测试尤其重要：它把 rollout boundary 固化成 executable knowledge，避免以后有人看到 W2 capability 已存在，就误把 default writer 切过去。

在临时副本里的 instructor reference implementation 中，我们曾加入 R2 dual reader、显式 W2 capability、default W1、v2 task validation 与 future-version rejection；原 core tests 与 reference-specific tests 合计得到 `16 passed`，并 spot-check 了 W1/W2 normalization。这个数字只证明该 reference candidate 满足当前实验 contract；它不证明 fleet migration 已经发生，更不证明真实产品应该采用同一 implementation。

## 9. Dependency exercise 的答案也不是“永远不要 library”

当前需求只有两个 JSON versions、一个小 object 和有限 validation。Stdlib `json` 已足够表达 version dispatch、field validation、normalization 与 error semantics，因此 reference 不引入 schema/migration dependency。

理由不是“dependency bad”，而是新增 dependency 会带来长期 package maintenance、transitive graph、upgrade/security cadence 和自身 compatibility contract，而当前 complexity 尚不足以覆盖这些成本。

如果以后出现 many versions、复杂 validation、code generation 或 cross-language shared schema，这个判断应重新评估。Lab 评分看的是 dependency reasoning，不是学生有没有复刻 reference conclusion。

## 10. 常见假修复为什么会让 evidence 看起来更绿

**直接把 `SCHEMA_VERSION = 2`，再 update tests**：得到的是 final-state implementation，不是 mixed-version migration。

**把 historical v1 fixture 改成 v2**：删除了 old-data compatibility evidence。

**所有 unknown future version 都 fallback 到 v1**：可能把未知 semantics 静默按旧模型解释。

**为了兼容做 dual-write，却没有 authority/reconciliation model**：把 M08 问题转换成 M02/M07 问题。

**永远保留 dual reader，但没有长期 support policy**：它可能是必要 compatibility feature，也可能只是从未完成的 transitional debt；两者必须由 policy 区分。

这些错误有一个共同模式：Agent 或人只优化当前代码形状，没有把 old producers、old consumers、durable artifacts 和 rollout time 纳入同一个 model。

## 11. Reference review 关注什么

如果 Agent 只收到：

```text
Upgrade snapshot to v2.
```

最值得审的不是 `_decode_v2()` 有没有写得简洁，而是它是否偷偷替系统决定了 rollout。

Review 时我会重点问：historical fixture 有没有动；default writer 有没有悄悄变成 2；frozen old reader 有没有真实运行；R2 是否区分 unknown semantic discriminator；compatibility matrix 是否明确允许/禁止哪些组合；capability expansion、reader migration 和 writer cutover 有没有混成一个 phase；writer cutover 后 rollback target 是否仍能读 durable state；old reader cleanup 是否由明确 support policy 决定。

一个合格的 reference statement应当是：

> **当前代码 change 只扩大 reader capability：R2 同时理解 v1/v2，production default 仍产生 v1。接下来先把所有 supported readers/tools 迁到 R2，再单独审查 W2 cutover；因为 W2 durable data 对 R1 不兼容，cutover 会改变当前 rollback-compatible target set。停止写 v1 与停止读 v1 是不同 lifecycle event，后者还受历史数据 support policy 约束。**

这比一句“support backward compatibility”精确得多，也比把 Fowler 的 `Migrate` 直接改名成 writer cutover 更忠实于 source 和系统时序。