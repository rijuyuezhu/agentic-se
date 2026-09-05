# Lab 05 — Refactoring 与 Evolutionary Design

> 目标不是“让 `dashboard.py` 更漂亮”。
>
> 目标是训练：**先锁定已有 behavior → 比较两条 change path → 用 pure structural checkpoints 改变结构 → 独立证明旧 behavior 没漂移 → 再添加新 behavior。**

---

# 0. 场景

TaskForge 新增了一个 text dashboard：

```python
from taskforge.dashboard import render_dashboard
```

当前实现：

[`taskforge/src/taskforge/dashboard.py`](taskforge/src/taskforge/dashboard.py)

它的功能目前是正确的。

但是它把这些 responsibility 混在一个函数里：

```text
read current jobs
status classification
count aggregation
terminal/active interpretation
status display text
line formatting
```

现在收到 feature request：

> **新增 JSON dashboard。**

需求看起来很简单。

也正因为简单，它非常容易写成：

```text
copy render_dashboard
→ 把 string formatting 改成 dict/json
```

本实验要判断：这是不是你真正想留下来的系统结构。

---

# 1. 先不要改代码

进入：

```bash
cd labs/taskforge
```

运行 core tests：

```bash
PYTHONPATH=src uv run --with pytest --no-project python -m pytest -q
```

当前基线应为：

```text
6 passed
```

再运行 M05 behavior probe：

```bash
PYTHONPATH=src uv run --with pytest --no-project python tools/m05_behavior_probe.py
```

课程基线实际验证为：

```text
[OK] empty:  sha256=eaadf634b7104332
[OK] queued: sha256=ec17ac5523b4b8bd
[OK] mixed:  sha256=1181854b1e08cc1c
all existing text dashboard behavior preserved
```

不要只记 hash。

打开 probe 看它锁住了哪些 observable behavior。

---

# 2. Behavior Inventory

在改代码前，写一份：

```text
m05-behavior-inventory.md
```

至少回答：

## 2.1 输入

`render_dashboard` 的输入是什么？

不要只写函数参数。

还包括：

```text
TaskForge 当前 job state
job insertion order
```

## 2.2 输出

哪些东西当前被 probe 锁住？

例如：

- title；
- exact line ordering；
- count definitions；
- `<none>`；
- status label；
- exit code presentation；
- command text；
- job ordering。

## 2.3 依赖语义

判断：

```text
active = queued + running
terminal = succeeded + failed + cancelled
```

这些是：

```text
presentation detail
还是 domain interpretation？
```

如果新增 JSON renderer，是否应该重新写一遍？

## 2.4 这次不允许顺手改变什么

至少：

```text
job lifecycle
service API
M04 public_api error semantics
job ordering
existing text output
```

---

# 3. 新 JSON contract

新增：

```python
render_dashboard_json(title: str = "TaskForge Dashboard") -> str
```

它返回 JSON text。

解析后必须满足 schema：

```json
{
  "title": "TaskForge Dashboard",
  "counts": {
    "total": 5,
    "active": 2,
    "terminal": 3,
    "queued": 1,
    "running": 1,
    "succeeded": 1,
    "failed": 1,
    "cancelled": 1
  },
  "jobs": [
    {
      "id": "job-1",
      "command": "true",
      "status": "succeeded",
      "exit_code": 0
    }
  ]
}
```

要求：

- `jobs` 顺序与现有 text dashboard 相同；
- status 使用 raw enum value，例如 `"succeeded"`，不是 `"succeeded(0)"`；
- `exit_code` 对 queued/running/cancelled 为 `null`；
- counts 的语义与 text dashboard 一致；
- JSON whitespace / key ordering 不进入 contract；测试应 `json.loads()` 后比较 structure；
- **现有 text dashboard 必须 byte-for-byte 不变。**

---

# 4. 先做 Direct Design，不实现

写：

```text
m05-direct-design.md
```

假设你完全不 refactor `render_dashboard`，直接加 JSON。

画出实现草图。

例如会不会出现：

```text
render_text
  ├─ status counting rules
  ├─ active/terminal rules
  └─ status interpretation

render_json
  ├─ status counting rules
  ├─ active/terminal rules
  └─ status interpretation
```

回答：

1. 需要 duplicate 哪些 knowledge？
2. 如果以后加 `PAUSED`，改几处？
3. 如果 terminal 定义变化，改几处？
4. 两个 renderer 有没有可能 silently diverge？
5. Direct path 的优点是什么？

最后一题很重要。

不要把 direct patch 描述成“显然坏”。

它可能：

- diff 小；
- feature 很快；
- 不引入新 abstraction；
- 如果第二个 renderer 是一次性需求，长期 duplication 也许完全可接受。

---

# 5. 再做 Preparatory Design

写第二个设计：

```text
m05-preparatory-design.md
```

目标：

```text
让 text / JSON 共用 domain facts
但 presentation 保持独立
```

不要被限定成某个 class hierarchy。

候选可以是：

```text
internal snapshot model
pure fact builder
count object
normalized records
```

也可以是其他设计。

要求解释：

```text
什么 information 被集中？
什么 information 仍属于 renderer？
新的 abstraction 隐藏了什么？
```

如果你的答案只是：

> “因为 DRY。”

不够。

必须说清楚 duplicated 的是：

```text
syntax
还是 knowledge / policy
```

---

# 6. Design It Twice 比较表

填写：

| 维度 | Direct | Preparatory + Feature |
|---|---|---|
| 首次 diff 大小 | | |
| 新 abstraction 数量 | | |
| duplicated domain knowledge | | |
| text behavior drift 风险 | | |
| JSON 实现复杂度 | | |
| 加 `PAUSED` 的 change amplification | | |
| rollback 粒度 | | |
| review 是否能分开 structural / behavioral claim | | |

然后做决定。

课程推荐你至少尝试 preparatory path，但评分不以“必须抽某个 class”为标准。

评分看 reasoning。

---

# 7. 设计 Change Topology

在写 production code 前，先写 staged plan。

一个合理形状可能是：

```text
C0 baseline
 ↓
C1 strengthen/record behavior evidence
 ↓
C2 isolate shared dashboard facts
 ↓
C3 make text renderer consume new structure
 ↓
C4 add JSON renderer
 ↓
C5 cleanup only if justified
```

你可以合并 C2/C3，如果仍然是一个很小、单一 proof obligation 的 structural step。

但不能直接写：

```text
C1 refactor and add JSON
```

这失去了本实验的核心。

对每个 checkpoint 写：

```text
hat:
intended behavior change:
evidence:
rollback:
```

---

# 8. Phase A — Preparatory Refactoring Only

现在才开始改 production code。

硬约束：

```text
禁止增加 render_dashboard_json
禁止改变 existing text output
禁止改变 service/model/public_api semantics
禁止引入第三方 dependency
```

每完成一个 semantic checkpoint，运行：

```bash
PYTHONPATH=src uv run --with pytest --no-project python tools/m05_behavior_probe.py
PYTHONPATH=src uv run --with pytest --no-project python -m pytest -q
```

如果 probe 出现：

```text
[DRIFT]
```

在 structural phase 默认当 bug 处理。

不要先 update golden。

---

# 9. 不要只依赖最终状态

对每个 structural commit，写一个简短 note：

```text
Why this step exists:

Why behavior should be unchanged:

Evidence:

What new change becomes easier after this step:
```

例如：

```text
Why:
- status/count interpretation would otherwise be duplicated by JSON renderer.

Behavior:
- render_dashboard public text remains byte-for-byte identical.

Evidence:
- m05_behavior_probe unchanged
- core tests pass

Enables:
- second renderer can consume shared facts without copying classification logic.
```

---

# 10. Phase B — 独立 Review Structural Diff

在加 JSON 前停下来。

只 review structural phase。

问：

## 10.1 它真的是 behavior-preserving 吗？

不要只说 tests green。

列出：

```text
behavior inventory item
→ evidence
```

## 10.2 complexity 真下降了吗？

比较：

```text
before
```

和：

```text
after
```

问：

- reader 需要理解更多 type 吗？
- control flow 更清楚了吗？
- domain interpretation 集中了吗？
- renderer interface 变深还是变浅？

## 10.3 有没有 over-abstraction？

如果为了一个简单 dashboard 引入：

```text
AbstractDashboardFactory
RendererRegistry
DashboardProvider
StatusStrategy
```

你必须有非常强的理由。

不要因为“用了 pattern”加分。

---

# 11. Phase C — Add JSON Behavior

只有 structural phase 通过 review 后，才加：

```python
render_dashboard_json(...)
```

先写 tests。

至少覆盖：

## Empty

```text
counts all zero
jobs=[]
```

## Mixed lifecycle

覆盖：

```text
queued
running
succeeded
failed
cancelled
```

## Command preservation

确保 JSON 不丢 command。

## Exit code semantics

```text
succeeded → 0
failed → nonzero
non-finished → null
```

## Ordering

job order 与 text/dashboard 现有 contract 保持一致。

建议测试：

```python
payload = json.loads(render_dashboard_json())
```

然后比较 data structure。

不要把 JSON whitespace 冻成无意义 contract。

---

# 12. Feature Phase 后再次验证旧 behavior

运行：

```bash
PYTHONPATH=src uv run --with pytest --no-project python tools/m05_behavior_probe.py
PYTHONPATH=src uv run --with pytest --no-project python -m pytest -q
```

新增 behavior 的同时，旧 text output 仍必须保持。

这就是 regression evidence。

---

# 13. 一个故意设置的陷阱：`status_text`

现有 text output：

```text
succeeded(0)
failed(7)
```

JSON contract：

```json
{
  "status": "succeeded",
  "exit_code": 0
}
```

不要为了复用，把：

```text
"succeeded(0)"
```

当成 domain status。

它是 presentation。

更好的分层应该能表达：

```text
semantic facts
→ text-specific status label
```

而不是：

```text
text presentation string
→ JSON 再 parse 回 domain facts
```

这是 M02 information hiding 的回归题。

---

# 14. 另一个陷阱：为了 JSON 改 text

你可能觉得：

```text
TaskForge Dashboard
```

不够好，想改成：

```text
TaskForge job dashboard
```

或者想重新排序 counts。

即使新格式“更合理”，也不要放进 structural phase。

如果真的要改：

```text
单独 behavior change
```

并说明 compatibility。

---

# 15. Differential Evidence

本 lab 的 `m05_behavior_probe.py` 本质上是一个小型 differential/golden oracle。

你可以进一步做：

```bash
git show HEAD~1:labs/taskforge/.../dashboard.py
```

或者建立临时 worktree，给同一组 state 分别跑：

```text
before renderer
vs
after renderer
```

比较 exact output。

这比只说：

> “我看代码应该一样。”

强很多。

---

# 16. Agent Exercise A — Vague Prompt

建议在干净 worktree 做，不污染你的正式实现。

给 Agent：

```text
重构 TaskForge dashboard，让代码更好，然后加 JSON 输出。
```

记录：

- 一次改多少文件；
- 是否先读 contract/tests；
- 是否改变 text output；
- 是否把 refactor 和 feature 混一起；
- 是否引入不必要 abstraction；
- 它声称什么 evidence；
- 你真正需要 review 多少语义维度。

不要因为结果能跑就打高分。

---

# 17. Agent Exercise B — Engineering Contract

重新从 clean base 开始。

给 Agent：

```text
Goal:
Add a JSON dashboard renderer.

Before editing:
1. Read dashboard.py and m05_behavior_probe.py.
2. Write a behavior inventory for the existing text renderer.
3. Propose two designs: direct feature vs preparatory-refactor + feature.
4. Do not edit until the designs are compared.

Phase 1: preparatory refactoring only.
- Existing text output must be byte-for-byte identical.
- Do not add render_dashboard_json yet.
- Do not modify service/model/public_api semantics.
- No new third-party dependency.
- Keep each patch to one structural purpose.
- After each semantic checkpoint, run the M05 behavior probe and core tests.

Phase 2: feature.
- Add render_dashboard_json according to the lab schema.
- JSON formatting itself is not contract; parsed data is.
- Add focused tests.
- Re-run existing text behavior probe.

Report:
- exact structural checkpoints
- evidence for each
- any behavior drift
- final files changed
```

比较 A/B：

```text
最终 LOC
review complexity
behavior drift
abstraction quality
evidence quality
```

重点不是证明“长 prompt 一定更好”。

而是观察：

> **engineering constraints 是否改变 Agent 的 change topology。**

---

# 18. Agent Exercise C — Exploration Patch 后重做

第三种练习非常重要。

先让 Agent 自由实现 feature，目的只是探索 coupling。

然后不 merge。

从 exploration patch 提取：

```text
hidden behaviors
duplicated knowledge
missing tests
best change point
```

接着：

```text
git reset / fresh worktree
```

让 Agent 按 staged plan 重做。

比较：

```text
patching exploration diff
vs
clean reimplementation using learned model
```

这训练的是：

```text
code is disposable
understanding is the asset
```

---

# 19. Review Task

把最终提交当真实 PR review。

要求 reviewer 输出：

```text
Blocker / Medium / Low
```

至少检查：

## Refactoring claim

- structural commits 是否真的无 intended behavior change？
- 是否有 text drift？

## Change separation

- JSON feature 是否和 structural move 分开？
- tests 是否在正确阶段变化？

## Abstraction

- shared structure 隐藏的是 domain knowledge，还是只为了 DRY syntax？
- 是否 over-engineered？

## Evidence

- probe 是否在 structural phase 每一步都通过？
- JSON tests 是否验证 semantic schema？
- 是否出现“改 snapshot 让它绿”的行为？

## Scope

- 是否顺手改 M04 public API？
- 是否改 lifecycle？
- 是否改 ordering？

---

# 20. 评分标准

## 20% — Behavior inventory

是否真正列出 observable surface，而不是只写“tests pass”。

## 20% — Design it twice

是否公平比较 direct 与 preparatory 两条路径。

## 25% — Change topology

是否做到：

```text
structural checkpoints
→ feature checkpoint
```

并且每一步 coherent。

## 20% — Evidence

是否有：

```text
behavior probe
core tests
new JSON tests
```

以及 evidence 与 claim 是否匹配。

## 15% — Review / Agent retrospective

是否能识别：

```text
mixed concerns
over-abstraction
behavior drift
weak evidence
```

---

# 21. Instructor Reference

完成实验前不要看：

[`../case-studies/m05/instructor-analysis.md`](../case-studies/m05/instructor-analysis.md)

reference 不提供“唯一正确 class diagram”。

它会展示一条经过实际运行验证的 staged path，并解释为什么这条 path 足够小、为什么没有继续抽更多 abstraction。
