# M06 — Legacy Code：先建立 Feedback，再谈改进设计

> 这一章不是教你“如何嫌弃旧代码”。
>
> 真正目标是：**当你必须修改一个自己不完全理解、缺少可靠测试、又与环境强耦合的系统时，怎样把未知逐步变成可观察事实，把不可控依赖变成可控边界，然后再做最小、可验证的变化。**

---

# 0. 从 M05 的舒适条件撤退

M05 里我们做 refactoring 时有一个很舒服的前提：

```text
现有 behavior 已经比较清楚
+
有 baseline tests
+
有 behavior probe
+
我们知道哪些输出必须保持
```

所以可以：

```text
structure change
→ run evidence
→ behavior unchanged
```

真实维护工作常常不是这样。

你接手一个模块：

```python
from datetime import datetime
from pathlib import Path
import os
import socket


def publish_report():
    ...
```

它可能同时：

- 读全局状态；
- 读环境变量；
- 读当前时间；
- 读 hostname；
- 写文件；
- append 旧文件；
- print 到 stdout；
- 吞掉某些 exception；
- 输出一个没人写过 spec 的文本格式。

然后 issue 说：

> “加一个 failed-only 模式。”

这时最危险的第一反应是：

```text
这代码太烂了
→ 先重构
→ 顺便加 feature
```

因为你甚至不知道什么叫“保持行为”。

M06 要训练的是另一种工作顺序。

---

# 1. 什么叫 Legacy Code

“legacy”很容易被当成情绪词：

```text
old
ugly
Java 7
没有 type hints
很多 globals
```

这些都不是本章真正关心的东西。

## 1.1 一个更有工程意义的定义

本课程采用：

> **Legacy condition = 你需要改变代码，但缺少足够快速、可信、与这次变化相关的 feedback。**

因此：

```text
新代码也可以立刻进入 legacy condition
```

例如 Agent 昨天生成了 4000 行代码，只有一个 smoke test：

```text
CI green
```

但你不知道：

- retry semantics；
- ordering contract；
- error behavior；
- persistent format；
- crash recovery；
- caller assumptions。

从 change-risk 角度，它已经很 legacy。

## 1.2 Legacy 的核心不是“坏”，而是“不安全地未知”

最重要的变量不是美观度，而是：

```text
unknown behavior
+
slow / noisy feedback
+
hard-to-control dependencies
```

所以 M06 的目标不是先降低 code smell，而是先降低 **epistemic uncertainty**。

---

# 2. Legacy change 的真正困难：你不知道什么不能变

假设看到：

```python
line = f"{job.id}|{job.status.value}|{job.command}\n"
```

你可能觉得：

```text
pipe 分隔太难看了，改成 JSON 吧
```

但你不知道：

```text
有没有 shell script grep 第 2 列？
有没有 cron job diff 这个文件？
有没有用户依赖 newline？
有没有 downstream parser 把 insertion order 当 contract？
```

这就是 legacy maintenance 的核心：

> **declared contract 与 actual dependency surface 可能严重不一致。**

M08 会专门讨论 compatibility；M06 先教你如何在不知道全部 consumer 的情况下获取局部证据。

---

# 3. 先区分四类东西：Spec、Observed Behavior、Quirk、Bug

接手旧系统时，千万不要把当前行为和正确行为混成一个集合。

可以建立一个表：

| 行为 | 当前观察 | 是否有明确 spec | 判断 |
|---|---|---|---|
| job 顺序 | insertion order | 无 | unknown / possible dependency |
| unknown ID | KeyError | M04 想改 | implementation leakage |
| report 末尾 newline | 有 | 无 | unknown quirk |
| FAILED exit code | 显示数字 | 有测试 | protected behavior |
| 空 command | 被接受 | 新 contract 说不应接受 | known bug / old behavior |

这里最重要的是：

```text
observed
!=
correct
```

但：

```text
observed
也不能随便改
```

因为它可能已成为 compatibility surface。

---

# 4. Characterization Test：先记录事实，不急着判断

Michael Feathers 对 characterization test 的定义非常实用：

> 用测试记录当前软件行为，并在修改代码时保持它。

M03 的 specification-oriented test 是：

```text
根据 contract，结果应该是 X
```

M06 的 characterization test 首先是：

```text
我运行以后，结果实际是 X
```

## 4.1 它像一次受控实验

典型过程：

```text
1. 构造一个输入/环境
2. 运行旧代码
3. 观察输出
4. 把观察到的结果写成 assertion
5. 故意改坏一点代码，确认 test 真能红
6. 恢复代码
```

这里第 5 步非常重要。

否则你可能写出：

```python
assert output is not None
```

然后以为建立了 safety net。

## 4.2 Characterization test 不等于给 bug 发许可证

假设当前系统：

```text
cancelled job 被错误算成 active
```

characterization test 记录它：

```python
assert active_count == 1
```

之后你确认它是 bug。

正确做法不是永远保持：

```text
active_count == 1
```

而是明确进入 behavioral change：

```text
old characterization
↓
known bug confirmed
↓
new specification
↓
red test for desired behavior
↓
fix
↓
remove/update old characterization
```

Characterization 的作用是让变化**有意识**，不是让现状神圣化。

---

# 5. 不要先追 Coverage；先画 Change Cone

一个 100k LOC repo，你只需要改：

```text
legacy_audit failed-only mode
```

最差的任务定义之一是：

```text
先把 legacy_audit 附近覆盖率补到 90%
```

更好的问题是：

```text
这次变化可能影响哪些 observable effects？
```

可以画一个简化 effect sketch：

```text
scope flag
   │
   ▼
selected jobs
   │
   ├── count
   ├── ordering
   ├── line formatting
   ├── output file
   └── stdout summary
```

然后问：

```text
哪些节点最便宜、最可信地可观察？
```

这叫 **targeted feedback**。

---

# 6. Change Point、Test Point、Observation Point

## 6.1 Change Point

你实际需要改行为的位置。

例如：

```text
job selection policy
```

不要一开始把整个 `legacy_audit.py` 都当 change point。

## 6.2 Test Point

你能注入输入或控制依赖的位置。

例如：

```text
env var
function argument
module binding
filesystem root
```

## 6.3 Observation Point

你能判断行为的地方。

例如：

```text
written file bytes
stdout
return value
state change
```

这三个点不一定在同一个函数。

---

# 7. Sensing Problem 与 Separation Problem

这是 WELC 中非常值得保留的区分。

## 7.1 Sensing Problem

代码能运行，但你看不到你关心的结果。

例如：

```python
def reconcile():
    repo.update(...)
    metrics.increment(...)
    notifier.send(...)
```

你想知道：

```text
哪些 job 被 reconcile？
```

但唯一可见结果只是：

```text
三个外部副作用
```

这是 sensing 问题。

可能解决办法：

```text
observable result
recording fake
probe
capture output
query post-state
```

## 7.2 Separation Problem

代码根本无法在可控环境中运行。

例如：

```python
def report():
    db = ProductionDatabase()
    db.connect()
    ...
```

测试一调用就尝试真实数据库。

这是 separation 问题。

可能解决办法：

```text
parameter seam
factory seam
module substitution
filesystem temp root
process boundary
fake collaborator
```

## 7.3 为什么区分有价值

如果你把 sensing 问题误判成 separation 问题，可能会：

```text
创造 8 个 interfaces
```

但其实只需要：

```text
让函数返回一个 summary
```

反之，如果你只有 separation 问题，却加了大量 logging，也无法让测试隔离真实 DB。

---

# 8. Seam：不是“接口”，而是可以改变行为的机会

一个 seam 可以表示：

> 在不直接改目标位置的情况下，让程序在那里采用另一种行为。

## 8.1 Function parameter seam

```python
def build_report(now_fn=datetime.now):
    now = now_fn()
```

测试：

```python
build_report(now_fn=lambda: fixed_time)
```

## 8.2 Module binding seam

Python 里：

```python
from taskforge import filesystem
```

测试可以替换：

```text
taskforge.legacy_audit.filesystem
```

这也是 seam。

## 8.3 Filesystem seam

如果代码接受 output root：

```python
write_report(root)
```

测试使用 `tmp_path`。

无需定义：

```text
IFileSystemFactoryProvider
```

## 8.4 Process seam

某些 legacy CLI 最便宜的 characterization 方法就是：

```text
spawn subprocess
control env/cwd/input files
capture stdout/stderr/files
```

这可能比把 30 年旧程序拆成 unit-testable objects 更安全。

---

# 9. Enabling Point：seam 真正被选择的地方

如果定义：

```python
def export(clock):
    ...
```

seam 本身在 `clock` dependency。

但 enabling point 是：

```python
export(real_clock)
```

或：

```python
export(fake_clock)
```

这个概念非常适合 code review。

因为 reviewer 可以问：

> alternate behavior 到底在哪里被选择？

如果答案散落在全 repo：

```text
if testing:
if env == test:
if mock_mode:
```

那么 seam 可能反而制造了新的 complexity。

---

# 10. “最小 Seam”原则

面对 legacy module：

```text
time
hostname
env
filesystem
network
random
state
```

Agent 很容易一次性抽象成：

```text
Clock
HostProvider
Environment
Filesystem
NetworkClient
RandomSource
StateRepository
```

然后所有函数 constructor injection。

这不是 M06 的目标。

更合理的是：

> **只打开当前 change 所需的最小控制点。**

例如这次变化只要求：

```text
稳定测试 daily audit output
```

可能只需要控制：

```text
now
output root
hostname
```

global state 暂时可以通过现有 `service.reset_for_tests()` 和 submit API 构造。

不要借一次小变化强迫整个系统接受你理想中的 architecture。

---

# 11. Pinch Point：一个测试覆盖更大的 Effect Region

有时你发现：

```text
20 个旧函数
最终都会经过一个 report serialization function
```

那个位置可能是高价值 test point。

因为少量 tests 可以覆盖多个 change path。

你可以把它理解成：

```text
many upstream paths
        │
        ▼
     pinch point
        │
        ▼
observable effect
```

M06 不要求背 Feathers 的术语，但要学会找这种**高 leverage feedback point**。

---

# 12. Legacy Takeover 的第一阶段：Read-Only Reconnaissance

在任何生产修改前，写一个 takeover note。

至少回答：

```text
Entry points:
谁会调用它？

State:
读什么？写什么？

External effects:
文件、网络、stdout、database、process？

Nondeterminism:
time/random/hostname/env/concurrency？

Error behavior:
抛什么？吞什么？打印什么？

Known tests:
哪些是真正相关的？

Unknowns:
哪些行为看起来奇怪但没证据说明可以改？
```

注意最后一项。

好的工程记录里应该允许出现：

```text
UNKNOWN
```

而不是为了显得理解充分而瞎猜。

---

# 13. 第二阶段：Build a Behavior Inventory

运行旧系统，记录真实行为。

例如：

```text
Scenario A: no jobs
output file still created
stdout says 0 jobs
file ends with newline

Scenario B: mixed jobs
jobs use insertion order
SUCCEEDED renders exit code
QUEUED renders '-'

Scenario C: second invocation same day
appends another block
rather than overwriting
```

每一项标：

```text
OBSERVED
SPECIFIED
UNKNOWN
SUSPECTED BUG
```

不要直接写：

```text
MUST
```

除非你有依据。

---

# 14. 第三阶段：Characterization Tests

Characterization test 要尽可能：

```text
controlled
repeatable
high signal
```

## 14.1 Freeze nondeterminism

如果输出包含：

```text
current date
hostname
```

你不能接受：

```text
每次 test update golden
```

需要：

```text
control clock
control host
```

## 14.2 优先保护 boundary behavior

如果唯一 consumer 是一个 text file，characterization test 直接检查：

```text
file bytes
```

往往比检查十个 private helper 更稳。

## 14.3 Characterization test 也要有选择

不要 snapshot：

```text
整个 50MB database dump
```

只因为“这样全覆盖”。

要围绕 change cone 选高信息量 scenario。

---

# 15. 第四阶段：证明 Safety Net 有牙齿

这是 M03 的思想在 legacy 场景中的复用。

例如你写了：

```python
assert report == EXPECTED
```

临时把：

```python
status.value
```

改成：

```python
"broken"
```

test 应该失败。

再恢复。

如果没有失败，你的 characterization 根本没覆盖当前风险。

---

# 16. 第五阶段：只为当前 Change 打 Seam

现在才允许改 production structure。

一个好 seam patch 应该很无聊：

```text
production behavior unchanged
public API unchanged
no feature yet
```

例如：

```python
# before
now = datetime.now(timezone.utc)
host = socket.gethostname()

# after
def _runtime_context(now_fn=..., host_fn=...):
    ...
```

关键验收：

```text
old characterization still identical
```

而不是：

```text
architecture 更优雅了
```

---

# 17. 第六阶段：再做 Requested Behavior Change

现在 issue 是：

> audit 支持 `failed-only`。

这时先写新 specification：

```text
scope=all
→ existing behavior unchanged

scope=failed
→ only FAILED jobs included
→ header count matches selected jobs
→ ordering among selected jobs follows existing order
→ append/path semantics unchanged
```

然后：

```text
red test
→ minimal implementation
→ focused pass
→ full characterization
```

现在这是 M05 的 Two Hats，只不过 M06 多了一个前置阶段：

```text
first obtain feedback
```

---

# 18. Legacy Code 中的 Tests 不一定从 Unit Test 开始

这是非常重要的一点。

如果现有程序天然是：

```text
CLI
→ env
→ filesystem
→ file output
```

最安全的第一条 characterization 可能是：

```text
process-level black-box test
```

而不是先 refactor 出 12 个 injectable classes。

## 18.1 High-level characterization 的优点

- 改 production code 少；
- fidelity 高；
- 能记录真实 formatting / file behavior；
- 对第一次 takeover 很安全。

## 18.2 缺点

- 慢；
- failure localization 差；
- setup 可能重；
- 很难穷举 edge cases。

因此之后再逐步增加 focused seam-based tests。

---

# 19. Hermeticity 与 Fidelity 的 Trade-off

你可以有：

```text
A. 完全 fake 的 unit test
fast / deterministic / low fidelity

B. tmpdir + real serializer
medium cost / medium-high fidelity

C. real service integration
slow / high fidelity / noisy
```

M06 的目标不是选一个“最专业”的层级。

而是构造：

```text
fast feedback loop
+
足够真实的 compatibility probe
```

这是一种 portfolio thinking。

---

# 20. 什么时候不应该打 Seam

## 20.1 Dependency 已经便宜且 deterministic

例如 pure function：

```python
normalize_status(x)
```

不需要为了“可测试性”加 interface。

## 20.2 seam 比 dependency 本身更复杂

如果为了替换一行：

```python
len(items)
```

引入 provider abstraction，就是负收益。

## 20.3 你只是想测试 implementation interaction

如果测试唯一价值是：

```text
assert mock.foo called_once_with(...)
```

先问：

> caller-visible behavior 到底是什么？

---

# 21. Legacy Code 中的 Refactoring 顺序

M05 的 refactoring workflow 在 legacy 条件下必须变成：

```text
unknown system
↓
characterize
↓
minimal seam
↓
characterize more precisely
↓
small structural improvement
↓
new feature/fix
```

而不是：

```text
unknown system
↓
large cleanup
↓
write tests for cleaned-up structure
```

后者很容易把你自己的误解固化成新 architecture。

---

# 22. “我看不懂这段代码”时怎么做

不要只做静态阅读。

建立 hypothesis-driven exploration：

```text
Hypothesis:
report appends rather than overwrites.

Probe:
run twice with same day/output root.

Observation:
second block appended.

Update model:
append semantics are observed behavior.
```

然后继续：

```text
Hypothesis:
job order is sorted by id.

Probe:
construct nontrivial lifecycle/order case.

Observation:
order follows insertion order.

Update model:
my hypothesis was wrong.
```

这比“把所有文件读一遍再总结”更接近科学方法。

---

# 23. Repository History 是 Evidence，不是 Oracle

Git history、issue、old PR、comments 都很重要。

它们可以帮助判断：

```text
这个奇怪行为是 intentional 吗？
为什么这里有 workaround？
以前有人试过改吗？
```

但历史也可能：

- 过时；
- 错误；
- 没覆盖 hidden consumer。

所以：

```text
history evidence
+
runtime characterization
+
current tests
```

要交叉使用。

---

# 24. Legacy Takeover 的 Agent Workflow

## Phase 1 — Reconnaissance only

给 Agent：

```text
Do not edit.
Map entry points, dependencies, side effects, nondeterminism,
and current tests related to <change>.
Mark unknowns explicitly.
```

输出必须包含证据位置。

## Phase 2 — Behavior probes

```text
Design the smallest runtime probes that answer these unknowns.
Do not refactor production code yet.
```

## Phase 3 — Characterization

```text
Turn confirmed observations around the change cone
into deterministic characterization tests.
```

## Phase 4 — Minimal seam

```text
Open only the seam required to control the remaining nondeterminism.
No feature change.
Existing characterization must remain unchanged.
```

## Phase 5 — Behavior change

```text
Implement the requested behavior under an explicit new contract.
Show red-before / green-after evidence.
```

## Phase 6 — Independent review

另一个 Agent 只看：

```text
Did the patch preserve characterized behavior outside the requested delta?
Did it broaden the seam unnecessarily?
Did tests assert behavior or new implementation details?
What unknowns remain?
```

---

# 25. 一个坏 Agent Prompt

```text
Clean up legacy_audit.py, make it testable, and add failed-only mode.
```

为什么危险？

因为把三个不同目标混在一起：

```text
understand current behavior
change structure
change behavior
```

Agent 可以轻松生成一个漂亮但无法审计的大 diff。

---

# 26. 一个更好的 Agent Task Contract

```text
Goal:
Add failed-only audit scope.

Before implementation:
1. do not edit;
2. characterize current default output for empty, mixed, repeated-write cases;
3. record path, ordering, append, newline, stdout behavior;
4. mark observed-but-unspecified quirks.

Structural phase:
open only the smallest seam required to control time/hostname/output root;
do not alter default output bytes.

Behavior phase:
scope=failed selects only FAILED jobs;
scope=all remains byte-compatible with the characterized baseline.

Non-goals:
no audit format redesign;
no global state architecture rewrite;
no new persistence layer;
no broad dependency-injection framework.

Evidence:
- characterization pass before feature;
- seam-only phase preserves fingerprints;
- failed-only test fails before feature and passes after;
- full existing suite passes.
```

这就是 Agent 时代 software engineering 的价值：

> **不是告诉 Agent 每一行怎么写，而是控制它在哪些 epistemic assumptions 下允许开始写。**

---

# 27. 如何 Review Legacy Change

不要先看 style。

先问：

## 27.1 Change understanding

- change point 是否明确？
- effect cone 是否合理？
- unknown 是否被诚实记录？

## 27.2 Feedback

- 新增 characterization 是否真的对应风险？
- 是否验证过 test 能 red？
- 是否过度 snapshot 无关行为？

## 27.3 Seam

- seam 是解决 sensing 还是 separation？
- enabling point 在哪里？
- scope 是否比当前 change 更大？
- 有没有引入新的 production concepts 只为测试服务？

## 27.4 Behavior

- requested delta 是否与 structural change 分开？
- default behavior 是否保持？
- known quirks 是否被无意“修复”？

## 27.5 Remaining risk

- 哪些 behavior 仍然 unknown？
- 哪些高-fidelity scenario 没跑？
- 是否需要 post-merge observation？

---

# 28. Legacy Code 与 Architecture 的关系

不要以为：

```text
legacy code
→ architecture rewrite
```

M06 更关心的是**建立局部可控性**。

有时三行 seam 加两个 characterization tests，就足以让一个危险 change 变成安全 change。

这比花两周设计：

```text
new domain layer
new repository layer
new adapter layer
new event bus
```

更有工程价值。

---

# 29. Legacy Code 的渐进式“去 Legacy 化”

一个系统不是某天从：

```text
legacy
```

瞬间变成：

```text
modern
```

更现实的是：

```text
change A
→ 打开 seam A
→ characterization A

change B
→ characterization B
→ 清理一个 dependency

change C
→ 明确一个 API contract

...
```

逐渐形成：

```text
更清晰的 boundaries
更快的 feedback
更明确的 contracts
更少的 unknowns
```

软件工程的很多改善都发生在**修改功能时顺手建立未来的可修改性**。

---

# 30. 这一章真正想让你形成的直觉

面对陌生旧系统，不要问：

> “怎么重构得更漂亮？”

先问：

> “我需要改变什么？”
>
> “我现在凭什么知道没改坏？”
>
> “哪一个最小 seam 可以让我得到这个 feedback？”

这三问，是 M06 的核心。

---

# 31. 与前五章连接

```text
M00
复杂度最危险的形式之一是 unknown unknowns

M01
没有 spec 时，要明确区分 observed behavior 与 intended contract

M02
seam 本质上是在重新安排 boundary / knowledge / authority

M03
characterization test 仍然只是 evidence，必须验证 oracle 有牙齿

M04
error/output/file semantics 都可能成为 boundary contract

M05
refactoring 需要 behavior-preserving；M06 先解决“behavior 到底是什么”

M06
在不确定系统里先建立 feedback
```

下一章 M07 会进一步破坏我们的假设：

```text
即使你已经有测试和 seam，
并发、lifecycle、retry、crash 仍会让单线程 mental model 失效。
```

---

# 32. 本章最小记忆集

如果只记住八句话：

1. **Legacy 的核心风险不是旧，而是 change without trustworthy feedback。**
2. **Observed behavior 不等于 correct behavior，但不能无意识改变。**
3. **Characterization test 首先记录事实，不是宣判事实合理。**
4. **先围绕当前 change 建 targeted feedback，不要先追全局 coverage。**
5. **Sensing 与 separation 是两个不同问题。**
6. **Seam 是可替换行为的机会，不是 interface 的同义词。**
7. **只打开当前 change 所需的最小 seam。**
8. **Agent 接管 legacy repo 时：read → hypothesize → probe → characterize → seam → change，而不是 read → rewrite。**

这八条足够支撑你开始真正维护陌生系统。
