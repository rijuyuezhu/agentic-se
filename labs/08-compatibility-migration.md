# Lab 08 — Compatibility 与 Migration：不要把 final schema 当 rollout plan

> 本实验不是“把 JSON version 从 1 改成 2”。
>
> 目标是：**在旧 reader、旧 snapshot 和新代码可能同时存在时，设计并实现第一阶段安全 migration。**

---

# 0. 场景

TaskForge 现在有一个 durable snapshot format：

```text
src/taskforge/snapshot.py
```

以及一个历史 fixture：

```text
fixtures/m08/snapshot-v1.json
```

当前 v1 job：

```json
{
  "id": "job-41",
  "command": "echo historical",
  "status": "succeeded",
  "exit_code": 0
}
```

产品希望将来支持更多 task kinds，所以提出 v2：

```json
{
  "id": "job-41",
  "task": {
    "kind": "shell",
    "command": "echo historical"
  },
  "status": "succeeded",
  "exit_code": 0
}
```

最终 v2 root：

```json
{
  "schema_version": 2,
  "jobs": [...]
}
```

但你不能假设所有 TaskForge binaries 同时升级。

---

# 1. Baseline

运行：

```bash
cd labs/taskforge
PYTHONPATH=src uv run --with pytest --no-project python tools/m08_compat_probe.py
```

当前应看到类似：

```text
[OLD DATA READABLE] ...
[OLD READER ACCEPTS CURRENT WRITER] ...
[EXPECTED BREAK] frozen v1 reader rejects v2 ...
[STARTER LIMIT] current TaskForge reader also rejects v2
[FAIL CLOSED] unknown future schema version is rejected
```

再运行：

```bash
PYTHONPATH=src uv run --with pytest --no-project python -m pytest
```

记录 baseline。

---

# 2. 第一阶段：只读 Reconnaissance

在改代码前输出：

```text
m08-compatibility-map.md
```

至少回答以下问题。

## 2.1 Compatibility surfaces

列出 snapshot 对外暴露的：

```text
root keys
schema version
job keys
field types
job ordering
status strings
exit_code semantics
UTF-8 / JSON representation
trailing newline, if relied upon by tools/tests
```

然后分类：

```text
explicit contract
observed implementation
historical evidence
unknown
```

不要把所有 JSON whitespace 都自动升级成 public contract。

## 2.2 Producer / consumer inventory

至少列出：

```text
current writer
current reader
historical v1 fixture
frozen v1 reader in m08_compat_probe.py
potential future v2 reader/writer
```

说明哪些：

```text
你能修改
你不能修改
代表已经部署/已经持久化的历史
```

## 2.3 R/W matrix

先写 starter：

| Writer | Reader | 当前结果 | 第一阶段要求 |
|---|---|---|---|
| W1 | R1 | PASS | PASS |
| W1 | R2 | N/A | PASS |
| W2 | R1 | FAIL | **第一阶段不允许默认发生** |
| W2 | R2 | N/A | PASS |

不要只写“backward compatible”。

---

# 3. Design It Twice

提出至少两个方案。

## 方案 A：直接切 v2

```text
replace v1 parser
replace writer with v2
update fixture/tests
```

分析：

```text
old data
old binary
rollback
historical fixture
```

会发生什么。

## 方案 B：Expand first

例如：

```text
R2: read v1 + v2
W1 remains default
optional explicit W2 only for tests / gated rollout
```

分析：

```text
compatibility burden
rollout safety
rollback
cleanup cost
```

你可以提出方案 C，但不能只用：

```text
“更 clean”
“更 enterprise”
“更 future-proof”
```

作为理由。

---

# 4. 本轮 Change Contract

本实验的代码 change **只实现 capability expansion**：让新版本具备同时读取 v1/v2 的能力，但不宣称 supported consumers 已完成迁移，也不切 production writer。这里的 E/M/W/C 是受 Parallel Change 启发的 durable-data adaptation：TaskForge 第一步扩的是 **reader/consumer capability**，不要求与 Fowler 原义里的 supplier-side Expand 做角色一一映射；后续 reader deployment/migration 和 durable writer cutover 是独立 rollout events。

## 4.1 必须保持

- `snapshot-v1.json` 文件内容不允许修改；
- v1-format decode semantics 保持；
- current default writer 必须仍产生 `schema_version: 1`；
- default writer 输出必须继续被 frozen v1 reader 接受；
- job ordering 保持；
- `status` / `exit_code` semantics 保持；
- unknown future major schema version 必须 explicit reject，不允许猜。

## 4.2 必须新增

new reader 必须同时接受：

```text
v1 flat command
v2 task={kind:"shell", command:...}
```

两者都 normalize 成同一个内部：

```text
SnapshotJob.command
```

建议你把：

```text
wire representation
```

与：

```text
normalized domain representation
```

分开。

## 4.3 v2 writer

你有两个合法选择：

### Choice 1

本轮完全不提供 production v2 writer，只构造 v2 fixture/test input。

### Choice 2

提供显式：

```python
dumps_current_snapshot(format_version=2)
```

但：

```text
默认仍必须是 v1
```

而且 API/documentation 必须明确 v2 writer 还未进入默认 rollout。

## 4.4 Non-goals

本轮不要：

- switch default writer to v2；
- 删除 v1 parser；
- 修改 historical v1 fixture；
- 加 SQLite；
- 加 HTTP；
- 实现 fleet rollout framework；
- 引入 schema-migration dependency，除非你能证明 stdlib 无法满足本轮需求；
- 自动 rewrite 所有 v1 snapshot；
- 做 dual-write filesystem。

---

# 5. Required Evidence

至少写以下 tests。

## 5.1 Historical old data → new reader

```text
snapshot-v1.json
→ R2
→ PASS
```

验证 normalized：

```text
id
command
status
exit_code
ordering
```

## 5.2 v2 → new reader

构造至少：

```text
succeeded
failed
queued
```

不要只测一个 happy path。

## 5.3 Default new writer → frozen old reader

这是本实验最重要的 migration test 之一：

```text
current default W
→ frozen R1
→ PASS
```

它证明当前 capability-expansion change 还没有越过 writer cutover boundary；它**不能**证明 reader migration 已经完成。

## 5.4 Explicit v2 writer → new reader

如果你实现 W2：

```text
W2 → R2 → PASS
```

并明确：

```text
W2 → R1 → FAIL
```

是已知 incompatibility，所以当前不能默认启用。

## 5.5 Unknown future version

```text
version 99
→ explicit SnapshotFormatError
```

不能：

```text
fallback to v1
```

## 5.6 Malformed v2 task

至少覆盖：

```text
missing task
unknown task.kind
missing command
wrong type
```

问：

```text
哪些应该 reject？
```

不要 silent coerce。

---

# 6. Rollout Plan

代码完成后写：

```text
m08-rollout-plan.md
```

不能只写“先升级 reader 再 writer”。本实验把 Fowler 的 `Expand → Migrate clients → Contract` 与 durable format 额外存在的 writer cutover 分开记录，至少包括下面四个 event。

## Phase E — Expand capability

```text
R2 code can read v1/v2
W1 remains default
```

这一阶段的 exit criterion 只证明新 reader capability 本身经过测试、可以部署；**不要**把“所有 reader 都已升级”塞进 Expand 的定义。

## Phase M — Migrate readers / consumers

逐步把所有仍受支持、且可能读取 shared snapshot 的 consumers 迁到 R2。Exit criterion 可以是：

```text
all supported processes/tools that may read the shared snapshot are known to run R2+
```

inventory 必须包括 daemon 之外的 offline repair tool、backup restore image、supported old-release rollback target 等。如果某类 consumer 无法确认，说明 writer cutover 仍有未消除的 compatibility risk。

## Phase W — Writer cutover

只有 Phase M 的前置条件满足后，才定义：

```text
何时可以把 production default W1 -> W2
```

同时写清 rollout evidence 和 rollback-compatible targets。可以把 **feature flag / rollout gate** 作为候选 activation control，用来把“代码已经具备 W2 capability”和“production 已获准启用 W2”分开；本 Lab 不要求实现 flag。无论是否使用 flag，都必须明确：flag 不证明 reader migration 完成、不创造 compatibility，也不自动提供 rollback safety。

这个 event 会改变 durable data universe；它是 TaskForge 对 Parallel Change 的 operational adaptation，不要把它重命名成 Fowler 的 client-migration phase。

## Phase C — Contract / cleanup

明确：

```text
何时可以停止 W1
何时可以删除 v1 read support
```

这两个时点可以不同。如果产品承诺长期导入 v1 snapshot，也可以选择：

```text
v1 read support retained intentionally
```

但必须写成 support policy，不是“先留着”。

---

# 7. Rollback Analysis

回答三个具体场景。

## Case A

```text
supported reader migration 已完成
production writer 仍是 W1 only
incident
rollback binaries
```

为什么在 **snapshot-format 这一层** rollback space 仍然较大？不要把这个结论扩大成“整个 release rollback 一定容易”。

## Case B

```text
W2 已经写出 v2
rollback 到只支持 R1 的 binary
```

会怎样？

## Case C

```text
W2 写了一部分 snapshot
系统中还有 offline R1 tool
```

你需要：

```text
阻止 W2？
升级 tool？
保留 conversion？
提供 explicit export-v1？
```

选择一个并解释 trade-off。

---

# 8. Dependency Review Exercise

有人建议：

```text
“既然 schema migration 很复杂，引入一个成熟 schema library。”
```

不要直接接受或拒绝。

写一个简短 decision note：

```text
m08-dependency-note.md
```

至少比较：

```text
当前需求复杂度
stdlib 是否足够
新增 direct dependency
transitive dependency graph
维护/升级责任
security/update cadence
长期 lock-in
```

本实验预期：

> 这个两版本 JSON parser 不需要额外 dependency。

但评分看 reasoning，不看你是否机械得出这个结论。

---

# 9. Agent Version

## Round A — 模糊 prompt

给 Agent：

```text
把 TaskForge snapshot format 升级到 v2，把 command 改成 task object，并更新测试。
```

记录它是否：

- 直接改 `SCHEMA_VERSION = 2`；
- 删除 v1 reader；
- 更新 historical fixture；
- 只做 current-current roundtrip；
- 忽略 rollback；
- 自动 tolerant parse unknown future version。

## Round B — Engineering prompt

使用你在 Part 4 写的 change contract。

明确：

```text
Capability expansion only
historical fixture immutable
default writer remains W1
R2 must read v1/v2
frozen R1 must accept default output
future version rejects
no reader-migration claim, writer cutover, or contract cleanup in this code change
```

比较：

```text
contract drift
patch size
review findings
兼容矩阵覆盖
migration risk
```

---

# 10. Independent Review

reviewer 不应只看 tests 绿不绿。

必须问：

- historical fixture 被偷偷更新了吗？
- new reader 真能读真实 v1 吗？
- default writer 是否仍是 v1？
- frozen old reader 是否被实际执行？
- v2 task validation 是否 fail closed？
- compatibility matrix 是否明确方向？
- writer cutover criterion 是否具体？
- rollback 是否考虑 durable state？
- old reader removal 是否有 policy？
- compatibility branch 是否有结束条件？
- 是否引入不必要 dependency？

---

# 11. 评分

| 部分 | 权重 |
|---|---:|
| compatibility surface / matrix | 20% |
| capability-expansion design | 20% |
| implementation correctness | 20% |
| executable compatibility evidence | 20% |
| reader migration / writer cutover / rollback / contract criteria | 15% |
| dependency judgment | 5% |

---

# 12. 完成标准

完成后，你应该能精确说：

```text
“当前代码 change 只完成 capability expansion：new reader 同时接受 v1/v2，default writer 继续写 v1，因此它没有要求 frozen v1 readers 立刻消失。接下来必须单独迁移所有可能读取 shared snapshot 的 supported consumers；只有这一步有证据闭合后，才能审查 W2 writer cutover。W2 一旦产生 durable v2 data，rollback-compatible targets 需要重新计算。v1 read support 的删除时间则由长期 import policy 决定，不自动等于 writer cutover 时间。”
```

而不是：

```text
“我们做了 backward compatibility。”
```

---

# 13. Instructor reference

完成实验前不要看：

[`../case-studies/m08/instructor-analysis.md`](../case-studies/m08/instructor-analysis.md)
