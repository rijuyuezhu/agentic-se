# M05 Instructor Reference — Staged Refactoring of TaskForge Dashboard

> **Spoiler。** 请先完成 `labs/05-refactoring-evolutionary-design.md`。
>
> 这里不是唯一正确设计；它记录一条我实际执行并验证过的 change sequence，以及为什么没有继续“抽象到底”。

---

# 1. Baseline

M05 starter：

```text
labs/taskforge/src/taskforge/dashboard.py
```

`render_dashboard()` 当前正确，但混合：

```text
read jobs
+
status classification
+
count aggregation
+
active/terminal policy
+
text status presentation
+
text line formatting
```

现有 behavior probe：

```bash
PYTHONPATH=src uv run --with pytest --no-project python tools/m05_behavior_probe.py
```

实际结果：

```text
[OK] empty: sha256=eaadf634b7104332
[OK] queued: sha256=ec17ac5523b4b8bd
[OK] mixed: sha256=1181854b1e08cc1c
all existing text dashboard behavior preserved
```

core tests：

```text
6 passed
```

---

# 2. Behavior Inventory

我把 structural phase 的 must-preserve surface 定义为：

```text
render_dashboard(title) 返回值 byte-for-byte 相同
```

具体包括：

- default title；
- custom title；
- summary line 字段及顺序；
- per-status counts；
- active/terminal 的定义；
- `jobs:` 行；
- empty 时 `<none>`；
- job insertion order；
- queued/running/cancelled label；
- succeeded/failed 的 `status(exit_code)` 形式；
- command 原样输出。

明确 non-goals：

```text
不改变 service
不改变 worker
不改变 model
不改变 M04 public_api
不修 ownership
不增加 JSON
```

这点非常重要。

M04 starter 仍然有故意保留的问题。

如果 M05 顺手“把 public_api 也做好”，那么 structural phase 就会和前一章的 behavior exercise 混在一起。

---

# 3. Direct Design

最直接的实现是：

```python
def render_dashboard_json(...):
    jobs = service.list_jobs()
    queued = 0
    running = 0
    ...
```

也就是复制 text renderer 的 semantic interpretation。

## Direct path 的真实优点

不能假装它一无是处：

- 最小 initial diff；
- 不增加 internal model；
- 新功能很快；
- 如果 JSON 是一次性需求，也许 duplication 永远不会再变化。

## 代价

但是当前 duplicated 的并不只是 syntax。

而是知识：

```text
active = queued + running
terminal = succeeded + failed + cancelled
每个 status 如何计数
job ordering 来自现有 list order
```

如果以后加入：

```text
PAUSED
TIMED_OUT
RETRYING
```

两个 renderer 都需要同步理解。

这构成 change amplification risk。

---

# 4. Preparatory Design

reference 采用一个很小的 normalized snapshot：

```text
DashboardSnapshot
├── title
├── counts
└── jobs
```

其中 job 保存 raw semantic facts：

```text
id
command
JobStatus
exit_code
```

而不是保存：

```text
"succeeded(0)"
```

后者是 text presentation。

这样：

```text
_build_snapshot
    ↓
semantic facts
   ↙   ↘
text   JSON
```

---

# 5. 为什么没有做一个 Renderer interface

一个诱人的设计：

```text
DashboardRenderer Protocol
TextRenderer
JsonRenderer
RendererRegistry
```

我没有采用。

原因：

当前 change pressure 只有：

```text
一个现有 text renderer
+
一个新增 JSON renderer
```

共享的是：

```text
fact construction
```

而不是一个复杂的 polymorphic rendering lifecycle。

直接两个 pure-ish renderer：

```python
render_dashboard(...)
render_dashboard_json(...)
```

已经足够。

这是一个重要 lesson：

> preparatory refactoring 不等于“趁机建立未来万能 framework”。

---

# 6. Phase 1 — Structural Only

reference 第一阶段引入：

```python
@dataclass(frozen=True)
class DashboardCounts:
    ...

@dataclass(frozen=True)
class DashboardJob:
    ...

@dataclass(frozen=True)
class DashboardSnapshot:
    ...
```

以及：

```python
def _build_snapshot(title):
    ...
```

`render_dashboard()` 改成：

```text
build snapshot
→ text-specific formatting
```

没有 JSON function。

---

# 7. 为什么 snapshot 是 projection，不是 authority

M02 的 state ownership 不能忘。

`DashboardSnapshot`：

```text
不是 job state owner
```

它只是：

```text
read-time projection
```

而且 reference 使用 frozen dataclass，强化：

```text
presentation snapshot 不应该成为新的 mutation authority
```

仍然是：

```text
service/state
```

拥有当前 job state。

---

# 8. Phase 1 实际验证

在临时副本中应用 structural-only reference 后运行：

```bash
PYTHONPATH=src uv run --with pytest --no-project python tools/m05_behavior_probe.py
```

实际结果：

```text
[OK] empty: sha256=eaadf634b7104332
[OK] queued: sha256=ec17ac5523b4b8bd
[OK] mixed: sha256=1181854b1e08cc1c
all existing text dashboard behavior preserved
```

然后：

```bash
PYTHONPATH=src uv run --with pytest --no-project python -m pytest -q
```

结果：

```text
6 passed
```

因此 Phase 1 的 claim 是：

```text
internal representation changed
existing observable text behavior unchanged under current probe/test evidence
```

注意不是说：

```text
形式证明了所有可能 behavior 等价
```

证据范围要诚实。

---

# 9. 一个 subtle choice：`status_text` 放哪里

reference 没把：

```text
succeeded(0)
```

放进 `DashboardJob`。

而是保留：

```python
def _text_status(job: DashboardJob) -> str:
    ...
```

原因：

```text
succeeded + exit_code=0
```

是 semantic fact。

而：

```text
succeeded(0)
```

是 text representation。

JSON 要输出：

```json
{
  "status": "succeeded",
  "exit_code": 0
}
```

如果 snapshot 保存 presentation string，JSON renderer 就要：

```text
重新拆字符串
```

这会反转 abstraction direction。

---

# 10. Counts 为什么放 snapshot

另一个可以争论的设计：

```text
snapshot 只保存 jobs
每个 renderer 自己算 counts
```

这也能工作。

reference 把 counts 集中，是因为：

```text
active/terminal/status count
```

属于两个 renderer 都必须一致理解的 domain/reporting policy。

尤其：

```text
terminal = succeeded + failed + cancelled
```

不是 text formatting detail。

所以它值得成为 shared fact。

---

# 11. Phase 2 — Behavior Change

只有 Phase 1 验证完成后，reference 才新增：

```python
render_dashboard_json(...)
```

实现：

```text
_build_snapshot
→ JSON-specific mapping
→ json.dumps
```

JSON output 不复用 text-specific `status_text`。

---

# 12. JSON Tests

reference 添加两组高信息量 tests。

## Empty

验证整个 schema 的零状态：

```text
counts=0
jobs=[]
```

## Mixed lifecycle

一次构造：

```text
succeeded
failed
cancelled
running
queued
```

然后同时验证：

- title；
- counts；
- order；
- raw statuses；
- exit codes；
- commands。

这样比写 20 个低信息量 one-assert tests 更适合当前 fixture。

---

# 13. Phase 2 实际验证

加入 JSON renderer + focused tests 后，先再次跑旧 behavior probe：

```text
[OK] empty: sha256=eaadf634b7104332
[OK] queued: sha256=ec17ac5523b4b8bd
[OK] mixed: sha256=1181854b1e08cc1c
all existing text dashboard behavior preserved
```

说明 feature phase 没意外改 text behavior。

再跑 pytest：

```text
8 passed
```

其中：

```text
6 existing core tests
2 new JSON tests
```

---

# 14. 为什么 2 个 JSON tests 就可以覆盖很多 claim

test count 不是目标。

Mixed test 构造了一个信息密度很高的 state：

```text
5 statuses
5 commands
2 exit-code states
job ordering
all count categories
```

它一次覆盖多个相关 contract。

如果将来 JSON 逻辑更复杂，再增加更独立的 partitions。

M03 的原则仍然是：

> tests 的价值在于区分错误实现，不在数量。

---

# 15. Reference Change Topology

实际采用：

```text
S0 starter
 |
 | evidence only
 v
S1 behavior inventory + existing probe
 |
 | structural
 v
S2 normalized dashboard snapshot + text renderer migration
 |
 | verify old output identical
 v
S3 add JSON renderer + JSON tests
```

如果是实际 PR，我倾向于：

```text
PR/commit 1: preparatory refactor
PR/commit 2: JSON feature
```

小 repo 里也可以是一个 PR 的两个清晰 commits。

关键不是 Git 形式本身。

关键是 reviewer 可以分别建立：

```text
结构等价 argument
```

和：

```text
新 JSON contract argument
```

---

# 16. 为什么不先修改 tests 再 refactor？

当前已有 behavior probe 已经足够锁定本次关键 text surface。

所以 reference 没必要先新增一堆 redundant pytest tests。

如果现有 probe 不存在，我会先考虑：

```text
characterization/golden evidence
```

再做结构变化。

这是一个很重要的反规则：

> “重构前必须先写测试”不是宗教。

真正的问题是：

```text
你有没有足够 evidence 支持 behavior-preserving claim？
```

---

# 17. 现有 probe 的局限

三个场景并不证明所有可能 command/title 都等价。

例如没有专门覆盖：

```text
command 中包含 `|`
command 中包含换行
unicode title
很大的 job list
```

为什么 reference 仍认为可接受？

因为 structural change 没对 command/title 做 parsing 或 transformation，只是搬运。

我们同时用 code reasoning 缩小风险。

如果 refactor 涉及 escaping/parser，则这些 partitions 必须升级优先级。

这就是：

```text
evidence proportional to risk
```

---

# 18. 如果 direct path 其实更好怎么办？

完全可能。

例如产品明确说：

```text
JSON dashboard 只用于一次 debug，下一版本删除
```

那么：

```text
复制 15 行
```

也许比引入三个 dataclass 更经济。

本 lab 的 starter 故意让 shared domain interpretation 足够明显，所以 preparatory path 更有说服力。

但现实不能把练习答案机械迁移成规则。

---

# 19. 一个不推荐的“更 DRY”版本

例如创建：

```python
class Renderer:
    def render_title(...): ...
    def render_counts(...): ...
    def render_job(...): ...
```

然后：

```text
TextRenderer
JsonRenderer
```

看起来更 pattern-heavy。

但 JSON 和 text 的 composition shape 根本不同：

```text
lines
vs
nested data
```

为了“复用 renderer lifecycle”可能反而制造 shallow abstraction。

本次真正共享的是：

```text
normalized facts
```

不是 rendering algorithm。

---

# 20. 一个不推荐的混合 commit

```text
refactor dashboard
add JSON
rename dashboard title
change job order to sort by id
fix public_api KeyError
```

即使 tests 全绿，reviewer 必须同时判断：

```text
old text compatibility
new JSON schema
new ordering
M04 error behavior
```

这正是本章要避免的 proof-obligation pileup。

---

# 21. Agent-specific lesson

如果给 Agent：

```text
“重构 dashboard 并加 JSON。”
```

一个常见结果是直接生成最终 tree。

最终 tree 甚至可能不错。

但 reviewer 失去了：

```text
哪部分本该 behavior-preserving？
哪部分是新 behavior？
哪一步开始出现 drift？
```

所以更好的 Agent interface 不只是：

```text
final desired files
```

而是：

```text
required change sequence
```

---

# 22. 为什么 exploration patch 可以丢

如果 Agent 第一次实现直接复制一套 JSON classification，你已经学到：

```text
shared knowledge 是什么
```

如果第二次又为了抽象在这个 diff 上继续 patch，可能得到难以 review 的历史。

此时可以：

```text
保留 design notes
丢掉 exploratory code
git reset / fresh worktree
重新按 S0 → S1 → S2 → S3 做
```

这和 Kent Beck `Getting Untangled` 的思路高度一致。

生成代码便宜以后，这种选择更加合理。

---

# 23. 如果这是 production repo，我还会检查什么

TaskForge fixture 很小。

真实 repo 会额外检查：

```text
public symbol/API diff
config keys
serialization schema
metrics names
log events
performance regression
threading/async timing
external call sites
```

Refactoring proof obligation 必须随着 observable surface 扩张。

---

# 24. Instructor verdict

这次 reference 的重点不是：

```text
“dataclass 是最佳实践”
```

而是这条 change topology：

```text
observe
→ isolate facts
→ prove old renderer unchanged
→ add new behavior
→ prove old behavior still unchanged
```

它把三个前置模块真正串起来：

```text
M01 contract/invariant
+
M02 abstraction/ownership
+
M03 executable evidence
+
M05 controlled structural change
```

如果学生最后得到不同内部结构，但：

- 能准确说明 shared knowledge；
- structural phase text probe 无 drift；
- 没有过度 abstraction；
- JSON behavior 单独进入；
- change chain 清晰、可 review；

那就是成功答案。
