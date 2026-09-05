# M08 Instructor Analysis — Snapshot v1 → v2 的安全 migration

> **Spoiler warning**：请先完成 `labs/08-compatibility-migration.md`。

---

# 0. Reference conclusion

本实验最重要的答案不是某段 parser code。

而是：

```text
这轮 change 只能完成 Expand phase。
```

正确的第一阶段目标是：

```text
R2 reads v1 + v2
W1 remains default
```

不是：

```text
R2 + W2 immediately everywhere
```

原因非常具体：

```text
frozen R1 cannot read W2
```

只要系统仍可能存在 R1，默认打开 W2 就会把 rollout 从“兼容升级”变成“要求同步切换”。

---

# 1. Starter 的真实 compatibility surface

`src/taskforge/snapshot.py` 的 starter 暴露：

```text
schema_version = 1
root.jobs = array
```

job representation：

```text
id: string
command: string
status: string
exit_code: integer | null
```

另外 observable behavior 还有：

```text
job order = service.list_jobs() order
JSON UTF-8
pretty indent=2
trailing newline
```

但这里必须区分：

## 明确需要保持

```text
field meanings
job ordering
version identity
status / exit_code semantics
v1 readable history
```

## 当前只是 implementation formatting

```text
exact indentation
exact whitespace
```

除非外部 consumer 真的把 byte-level formatting 当 contract，否则不应该因为 golden hash 就自动冻结。

M03 的教训在这里再次出现：

> tests 不应该凭空发明 compatibility contract。

---

# 2. Historical fixture 为什么不能“顺手更新”

文件：

```text
fixtures/m08/snapshot-v1.json
```

它不是普通 test fixture。

它代表：

```text
已经存在于过去世界里的 durable artifact
```

如果实现 v2 时把它也改成：

```text
schema_version = 2
```

测试可能继续绿，但你已经删除：

```text
new reader can read old data
```

这条证据。

所以 reference 明确保持 fixture byte-for-byte 不变。

---

# 3. Frozen reader 的作用

`tools/m08_compat_probe.py` 内的：

```python
_legacy_v1_reader(...)
```

代表：

```text
已经部署、无法随当前 PR 一起修改的 consumer
```

它故意只接受：

```text
schema_version == 1
job["command"]
```

这比：

```text
new_writer → new_reader
```

更能验证 rollout compatibility。

因为 current-current roundtrip 只证明：

```text
当前两边对同一个新 contract 达成一致
```

它无法证明历史世界还活着。

---

# 4. Reference normalized representation

reference 没有让 domain code 到处判断：

```python
if version == 1:
    ...
elif version == 2:
    ...
```

而是把 version-specific parsing 留在 boundary：

```text
_decode_v1_job
_decode_v2_job
       ↓
SnapshotJob
```

normalized internal representation 仍然是：

```python
SnapshotJob(
    id,
    command,
    status,
    exit_code,
)
```

因此：

```text
wire evolution
```

不会强迫所有 downstream consumers 同时理解：

```text
flat command
vs
task object
```

这直接复用了 M04 boundary design。

---

# 5. 为什么 v2 task.kind 必须显式检查

v2：

```json
{
  "task": {
    "kind": "shell",
    "command": "echo hi"
  }
}
```

如果 parser 写：

```python
command = raw["task"]["command"]
```

却忽略：

```text
kind
```

那么未来：

```json
{
  "kind": "http",
  "command": "..."
}
```

旧 reader 可能把 HTTP task 当 shell task。

这不是 forward compatibility。

这是 semantic misinterpretation。

所以 reference 对 unknown `task.kind` fail closed。

这也是为什么：

```text
ignore unknown fields
```

不能机械升级成 universal rule。

---

# 6. Reference writer 为什么 default 仍是 1

reference 提供：

```python
dumps_current_snapshot(format_version=2)
```

但默认：

```python
DEFAULT_WRITE_VERSION = 1
```

这里故意把两个 capability 分开：

```text
Can write v2
```

和：

```text
May write v2 in production now
```

不是同一件事。

新代码提前拥有 W2 能力，有利于：

```text
fixture generation
integration testing
staged rollout
```

但 production default 仍受 rollout contract 控制。

---

# 7. Reference compatibility matrix

Reference 实际验证：

| Writer | Reader | 结果 |
|---|---|---|
| W1 | frozen R1 | PASS |
| W1 | R2 | PASS |
| W2 | R2 | PASS |
| W2 | frozen R1 | FAIL（已知、预期） |
| historical W1 fixture | R2 | PASS |
| future W99 | R2 | explicit reject |

这里最关键的是：

```text
W2 → R1 FAIL
```

不是 reference implementation 的 bug。

它是 rollout constraint。

因此 Phase E 的系统策略是：

```text
默认不要产生 W2
```

---

# 8. 为什么不是让 R1 自动接受 v2

一种可能思路：

```text
让 v2 仍保留 flat command
同时加 task
```

例如：

```json
{
  "command": "echo hi",
  "task": {"kind":"shell","command":"echo hi"}
}
```

这样 old reader 可能还能工作。

但这引入：

```text
两个 command copies
```

接着必须回答：

```text
哪一个 authoritative？
两者不一致怎么办？
writer partial bug 怎么办？
```

对于本实验而言，这相当于 dual representation。

不是一定错误，但 complexity 明显更高。

由于 rollout 可以通过“reader first, writer later”解决，所以 reference 没有选择 dual field。

这是一个具体 trade-off，不是说 dual-write 永远不好。

---

# 9. Rollout state machine

## Phase E0 — Before change

```text
Readers: R1
Writers: W1
Data: v1
```

## Phase E1 — Expand

部署：

```text
Readers: R1 + R2
Writers: W1 only by default
Data: v1
```

此时：

```text
rollback safe
```

因为 durable state 仍然是 v1。

### Exit criterion

不能只是：

```text
new release deployed
```

而应确认：

```text
所有可能读取 shared snapshot 的 supported processes/tools 都具备 R2
```

包括：

```text
daemon
CLI/offline repair tool
backup restore image
supported rollback binary
```

如果某类 consumer 无法 inventory，则 writer cutover policy 必须更保守。

---

# 10. Phase M — Writer cutover

只有 E1 exit criterion 满足后，才能逐步：

```text
W1 default
→
W2 default
```

这一步风险比 reader expand 高。

因为一旦 W2 写入 durable state：

```text
rollback to R1
```

可能失效。

所以 writer cutover 应独立：

```text
change
review
metrics
rollback analysis
```

而不是混在 parser PR 里。

---

# 11. Phase C — Contract

writer 全部稳定到 W2 后，还不能自动推出：

```text
可以删 R1
```

因为历史数据可能仍存在。

需要先决定 product support policy。

## Policy A — 永远可导入 v1

那么：

```text
R1 is permanent compatibility feature
```

不是 technical debt。

## Policy B — v1 有明确 EOL

那么需要：

```text
migration tool / release note / deadline / old-data inventory
```

达到 criterion 后再删。

所以：

```text
stop writing v1
```

和：

```text
stop reading v1
```

是两个不同 lifecycle events。

---

# 12. Rollback analysis

## Case A — R2 everywhere, still W1

回滚到 R1：

```text
safe with respect to snapshot format
```

因为没有产生 v2 durable data。

这说明 expand phase 有很好的 reversibility。

## Case B — W2 已经写数据，再 rollback R1

```text
R1 fails to decode
```

所以：

```text
binary rollback button
```

不等于：

```text
system rollback safe
```

## Case C — offline R1 tool

可以选择：

1. writer cutover 前先升级/退役 tool；
2. 提供 explicit export-v1；
3. 长期保持 W1；
4. 给 tool 加 conversion layer。

reference 不替真实产品决定。

但必须把这个 consumer 算进 matrix。

---

# 13. 为什么 reference 不引入 schema library

当前需求只有：

```text
2 versions
small JSON object
simple validation
```

stdlib `json` + 小 parser 已足够表达：

```text
version dispatch
field validation
normalization
error semantics
```

引入外部 schema/migration dependency 会增加：

```text
package maintenance
transitive graph
upgrade policy
compatibility contract
```

这并不是说 schema library 没价值。

当出现：

```text
many versions
complex validation
code generation
shared cross-language schema
```

再重新评估。

M08 的 dependency lesson 是：

> **dependency 的价值必须覆盖它长期带来的 contract 和 upgrade 成本。**

---

# 14. Actual reference verification

在临时副本中，reference 实现增加：

```text
R2 dual reader
explicit W2 capability
default W1 preserved
v2 task validation
future-version rejection
```

原 core tests：

```text
6
```

M08 reference tests 覆盖：

```text
historical v1
v2 normalization
default W1 -> frozen R1
explicit W2 -> R2
explicit W2 -> frozen R1 fails
5 malformed task cases
future version
```

实际运行：

```text
16 passed
```

并额外 spot-check：

```text
default writer version: 1
explicit v2 writer version: 2
R2<-W1: echo hi
R2<-W2: echo hi
```

这证明本 reference 的确处于：

```text
Expand-capable
but not cut over
```

的阶段。

---

# 15. 常见假修复

## 15.1 `SCHEMA_VERSION = 2` 然后 update tests

这是 final-state implementation，不是 migration。

## 15.2 v1 fixture 改成 v2

删除 historical evidence。

## 15.3 `version = raw.get("schema_version", 1)` 对所有 future version 猜 v1

可能 silent misinterpretation。

## 15.4 v1/v2 同时写两份文件

没有先定义 authority / partial failure。

M02 + M07 会立刻回来。

## 15.5 永远 dual reader，却没有 support policy

可能是必要 compatibility，也可能只是永不结束的 transitional complexity。

需要 explicit decision。

---

# 16. Agent review

如果 Agent 收到：

```text
Upgrade snapshot to v2.
```

最值得审的不是它有没有漂亮地写 `_decode_v2()`。

而是：

```text
它是否把 rollout assumption 偷藏进代码？
```

review checklist：

- v1 fixture 有没有改？
- default writer 有没有偷偷变 2？
- old reader evidence 有没有消失？
- unknown future version 是 reject 还是猜？
- v2 `kind` 有没有被忽略？
- current-current roundtrip 是否冒充 migration evidence？
- writer cutover 是否和 reader expand 混成一个 diff？
- rollback durable data 是否讨论？

---

# 17. 最终 instructor statement

一个合格答案应该能说：

> **M08 第一阶段不是“完成 v2 rollout”，而是扩大 compatibility envelope：R2 同时理解 v1/v2，但 production default 仍产生 v1，因此旧 reader 与 binary rollback 仍安全。只有当所有可能读取 shared snapshot 的 supported consumers 都具备 R2 能力后，才能单独审查 W2 cutover；而停止读取 v1 还需要独立的历史数据 support policy。**

这比：

```text
“support backward compatibility”
```

精确得多。
