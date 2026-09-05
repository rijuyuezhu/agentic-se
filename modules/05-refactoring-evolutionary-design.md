# M05 — Refactoring 与 Evolutionary Design：改变结构，而不是顺手改变世界

> 这一章不是教你背 `Extract Method`、`Move Field`、`Replace Conditional with Polymorphism`。
>
> 真正目标是：**面对一个已经有人依赖、已经有历史、已经有测试的系统，你能把结构变化设计成一条可验证、可 review、可回退的 change sequence，并知道什么时候应该重构，什么时候不应该。**

---

# 0. 从一句被滥用得很严重的话开始

工程里经常听到：

```text
“这个模块太乱了，我先重构一下。”
```

然后发生：

```text
rename
move files
change API
change error behavior
change data format
顺便修几个 bug
顺便加 feature
顺便换 dependency
```

三天后：

```text
tests 终于绿了
```

作者说：

> “重构完成。”

严格来说，这通常不是 refactoring。

Martin Fowler 给这个词的定义很窄：

> **改变软件内部结构，使它更容易理解和修改，同时保持 observable behavior 不变。**

而且它的核心不是一次大手术，而是：

```text
small behavior-preserving transformation
→ verify
→ small behavior-preserving transformation
→ verify
→ ...
```

这一定义的价值不在术语洁癖。

它给了我们一个极其有用的 **proof discipline**：

```text
如果我这一小步只是在改结构，
那任何行为变化都应该被视为 bug。
```

---

# 1. 为什么 Agent 时代更需要严格区分“结构变化”和“行为变化”

过去大规模重构的主要成本之一是：

```text
人改得慢
```

Agent 把这个成本大幅降低。

于是很容易产生一种错误推理：

```text
Agent 可以一次改 300 个文件
        ↓
那就让它一次改完
```

但真正限制大变更的从来不只有打字速度。

还有：

```text
review bandwidth
correctness evidence
merge conflicts
compatibility uncertainty
rollback granularity
ownership boundaries
unknown downstream users
```

Agent 把 implementation bandwidth 提高以后，这些约束反而更突出。

所以未来一个很重要的软件工程能力不是：

> “能不能生成巨大 patch？”

而是：

> **“能不能把巨大目标分解成一条每一步都有明确语义、每一步都可以独立验证的 change topology？”**

---

# 2. Refactoring 的 proof obligation

说：

```text
“这是纯重构。”
```

实际上是在提出一个 claim：

```text
Before 与 After 的 observable behavior 等价。
```

形式化一点：

```text
Obs_before(x, e) ≈ Obs_after(x, e)
```

其中：

- `x`：输入；
- `e`：相关环境状态；
- `Obs`：contract 允许观察到的行为；
- `≈`：在本次 compatibility boundary 下等价。

关键不是这个公式。

关键是：

> **你必须先回答什么算 observable。**

---

# 3. Observable behavior 比“返回值一样”大得多

最简单的 pure function：

```python
def f(x):
    ...
```

observable behavior 也许主要是：

```text
return value
exception
```

但真实软件可能还有：

```text
写了哪些文件
修改了什么数据库状态
发了多少 RPC
错误类型
错误 code
输出顺序
stdout/stderr
配置优先级
锁获取顺序
retry 次数
callback 时机
是否创建临时文件
是否保留旧 CLI flag
```

甚至 performance 也可能成为 contract。

例如：

```text
原 API: O(log n)
重构后: O(n²)
```

如果生产 workload 依赖原性能，那么“输出值一样”并不意味着工程意义上的 behavior-preserving。

同样：

```text
原来 callback 在 commit 后触发
现在 callback 在 commit 前触发
```

单线程 happy-path tests 可能全部通过，但 observable temporal behavior 已经变化。

因此重构前要做的不是先按 `rename symbol`。

而是先列：

# Behavior Inventory

例如：

```text
public inputs
public outputs
error semantics
side effects
ordering
persistence
lifecycle transitions
compatibility quirks
relevant performance/latency constraints
```

---

# 4. Contract、accident 和 Hyrum reality

M01 已经讲过：

```text
documented behavior
!=
implementation accident
```

但是在真实系统里还多一层：

```text
implementation accident
        ↓
下游已经依赖
        ↓
事实上的 compatibility surface
```

所以 refactoring 时不能简单说：

> “README 没写，所以可以改。”

更准确的问题是：

```text
谁可能观察它？
谁可能依赖它？
我们是否愿意打破这种依赖？
如果愿意，那还是 refactoring 吗？
```

如果你决定主动改变外部行为，那没有问题。

只是应该把它叫做：

```text
behavior change / migration
```

并单独建立新的 correctness argument。

---

# 5. Two Hats：同一小时里可以切换，但同一步不要混

Refactoring 传统里有一个很有用的比喻：**Two Hats**。

## Refactoring Hat

你的目标：

```text
改变结构
保持 behavior
```

这时：

```text
任何 behavior test failure
≈
本步骤可能做错了
```

## Adding-Function Hat

你的目标：

```text
改变 behavior
```

这时某些测试应该发生变化：

```text
旧 expectation 被新 contract 替代
新 behavior tests 先红后绿
```

真实开发当然可能：

```text
refactor 5 min
feature 10 min
refactor 2 min
feature 3 min
```

问题不是不能切换。

问题是：

> **你是否知道当前这一小步戴的是哪顶帽子？**

---

# 6. 为什么混在一起会让 review 变难

假设一个 diff 同时：

```text
rename 20 symbols
move 5 files
extract 3 helpers
change error type
add retry
change timeout default
```

reviewer 看到一行：

```diff
- old_call(x)
+ new_client.invoke(x, retry=policy)
```

他必须同时问：

```text
这是机械 rename？
这是 dependency move？
这是 behavior change？
retry 是否改变 side effects？
timeout default 是否兼容？
```

也就是说一个 diff hunks 同时承载多个 proof obligations。

如果拆成：

```text
CL1: rename only
CL2: move behind adapter, behavior unchanged
CL3: add explicit retry behavior
CL4: change timeout policy
```

每个 diff 可以拥有更窄的问题：

```text
CL1: symbol mapping 是否完整？
CL2: behavior 是否等价？
CL3: retry contract 是否正确？
CL4: compatibility 是否接受？
```

这就是 **semantic separation**。

---

# 7. Small Step 不是“少于 100 行”

“small changes”很容易被机械理解成：

```text
LOC < 100
```

但真正重要的是 **semantic size**。

比较两个 change。

## Change A

```text
500 files
每个文件：
foo_old → foo_new
```

如果是严格机械 substitution，它虽然行数巨大，但语义维度可能很低。

## Change B

20 行：

```text
增加 retry
改变 timeout
调整 transaction boundary
新增 fallback
```

它的 semantic surface 可能更大。

所以更好的“small”定义是：

> **一个 reviewer 可以建立一个主要 correctness argument 的 self-contained change。**

Google Engineering Practices 也明确不把 fixed LOC 当绝对规则。

---

# 8. Semantic Checkpoint

本课程给 small-step refactoring 再加一个词：

## Semantic Checkpoint

一个 checkpoint 应该满足：

```text
代码处于 coherent state
系统能运行
relevant tests 能跑
本步骤目标可独立解释
失败时可以定位到一个窄变化
必要时可以回退
```

例如：

```text
C0 baseline
 ↓
C1 add characterization evidence
 ↓
C2 extract calculation, output unchanged
 ↓
C3 introduce internal model, output unchanged
 ↓
C4 switch old renderer to model, output unchanged
 ↓
C5 add new renderer (behavior change)
```

注意：

```text
C1–C4
```

可以全部戴 refactoring hat。

真正的新功能直到 C5 才出现。

---

# 9. 为什么 checkpoint 比“最终 tests 绿”更强

假设你一次改 2000 行。

最终：

```text
1 test failed
```

bug search space：

```text
2000 行 + 多个语义变化
```

如果你分成十个 checkpoint，每一步都验证：

```text
C1 green
C2 green
C3 green
C4 green
C5 red
```

搜索空间立刻缩小到：

```text
C4 → C5 的变化
```

这不是慢。

它经常是在减少 debugging entropy。

---

# 10. 但 tests 绿并不自动证明 behavior-preserving

M03 已经说明：

```text
green tests
!=
correctness proof
```

所以 refactoring 的 evidence 不应该只有：

```text
pytest passed
```

还可能包括：

```text
static types
repository search
API surface diff
schema diff
golden output
property tests
performance benchmark
trace comparison
call count
side-effect log
manual protocol reasoning
```

例如 rename：

```text
tests green
```

还不够。

可以补：

```bash
rg 'old_symbol'
```

证明 production call sites 清零。

例如 error translation 重构：

```text
tests green
```

还可以检查：

```text
public error code set 是否改变？
```

---

# 11. Preparatory Refactoring：先让变化容易，再做容易的变化

这是 M05 最重要的 workflow 之一。

假设需求是：

```text
TaskForge dashboard 现在只有 text format，
新增 JSON format。
```

当前代码可能是：

```python
def render_text():
    # 读取 jobs
    # 计算 counts
    # 判断每种 status
    # 组装 display labels
    # 拼字符串
```

直接做最容易写成：

```python
def render_json():
    # 再读 jobs
    # 再计算 counts
    # 再判断 status
    # 再组织一遍语义
```

功能很快出来。

但你已经创建：

```text
duplicated domain interpretation
```

另一个路径是：

```text
先抽出 representation-independent report facts
        ↓
text renderer 使用它
        ↓
确认 text behavior 完全不变
        ↓
JSON renderer 复用同一事实模型
```

这就是 preparatory refactoring。

---

# 12. Preparatory ≠ Speculative Cleanup

这里非常容易走偏。

需求：

```text
新增 JSON dashboard
```

你发现：

```text
整个 repo 命名都不够优雅
```

然后决定：

```text
先全仓 rename
再改 package layout
再统一 exception hierarchy
再引入 dependency injection framework
```

这不是合理的 preparatory refactoring。

判断一个 structural change 是否真的 preparatory，可以问：

1. **它直接降低当前 feature 的复杂度吗？**
2. **没有这个 feature，我现在还会优先做它吗？**
3. **它的 change surface 是否明显小于直接 feature 的长期代价？**
4. **能否在 feature 之前独立证明 behavior unchanged？**
5. **如果 feature 被取消，这个 refactoring 本身仍值得保留吗？**

第 5 点不是要求答案一定 yes。

它只是暴露你到底是在：

```text
当前 feature 的必要准备
```

还是：

```text
借机做一个大 redesign
```

---

# 13. First / After / Later / Never

Kent Beck 在 *Tidy First?* 里很有价值的一点是：

> 整理不是永远先做。

我们把它推广成四种选择。

## 13.1 First

先 structural change，再 behavior change。

适合：

```text
当前结构明显放大目标 feature
直接加会制造 duplication / branch explosion
refactoring 很小且容易验证
```

## 13.2 After

先完成 behavior change，再局部整理。

适合：

```text
需求很小
当前结构虽然不漂亮但足以安全修改
先重构反而增加 delay
feature 实现后才真正看清 duplication/coupling
```

## 13.3 Later

记录设计问题，但这次不做。

适合：

```text
问题真实存在
但当前 change 不依赖解决它
风险/成本不值得进入这次 diff
```

关键：

```text
later
!=
假装永远会回来
```

如果确实重要，要有 issue / owner / trigger。

## 13.4 Never

有些“脏”根本不值得清。

例如：

```text
马上删除的代码
极少变化的稳定边界
短期 migration shim
生成代码
```

软件工程不是最大化美观。

是优化总 change cost。

---

# 14. Refactoring ROI：不要只谈 aesthetic

一个 structural change 值不值得做，可以粗略看：

```text
Cost(refactor now)
vs
Expected future change cost saved
+
risk reduction
+
review/understanding benefit
```

没有必要伪装成精确货币计算。

但至少要问：

```text
谁会从这个 refactoring 获益？
多久会获益？
下一个 change 是否马上会用到？
有没有更小的结构变化？
```

这比：

> “这个代码不够 clean。”

强得多。

---

# 15. Reversibility：好 change 不只容易做，也容易撤

一个重要但常被忽略的维度：

```text
rollback cost
```

比较：

## A

一个 commit 同时：

```text
rename API
迁移 caller
加 feature
删 old API
```

如果 feature 出问题，rollback 可能会把已经迁移的 caller 一起扯回来。

## B

```text
C1 add new internal seam
C2 migrate callers
C3 add feature using new seam
C4 remove old seam later
```

现在 C3 出问题时：

```text
rollback C3
```

更局部。

这种分步在后面的 compatibility/migration 章节会更深入。

M05 先建立意识：

> **change sequence 本身就是设计对象。**

---

# 16. Change Topology

我们通常把“设计”理解成最终代码结构：

```text
module A → interface B → store C
```

但工程里还有另一个同样重要的对象：

## Change Topology

也就是：

```text
系统从 S0 到 S1 到 S2 到最终 Sn
```

每个中间状态：

- 是否合法？
- 是否可运行？
- 是否兼容？
- 是否可回退？
- 是否可 review？

最终架构再漂亮，如果迁移路径要求：

```text
系统在中间坏 3 天
```

也可能不是可执行设计。

---

# 17. Design It Twice 不等于 Implement It Twice

M02 已经讨论 design judgment。

M05 把它用于 change sequence。

需求出现时，至少比较两条路径：

## Path A：Direct Feature

```text
现有结构上直接 patch
```

问：

- diff 多大？
- duplication 多吗？
- 新 branch 会泄漏到几层？
- 后续第二个 format / backend 会怎样？

## Path B：Preparatory + Feature

```text
small structural change
→ verify
→ feature
```

问：

- preparation 本身多大？
- 是否真的 behavior-preserving？
- 是否增加 premature abstraction？
- 两个 change 加起来是否更容易 review？

不是默认 B 胜。

目标是显式比较。

---

# 18. 一个常见陷阱：把“新 abstraction”当重构成功指标

很多 refactor 最后变成：

```text
原来 1 个函数
↓
interface
factory
adapter
strategy
registry
manager
provider
```

然后作者说：

> “解耦了。”

但 complexity 可能上升。

M02 的标准仍然适用：

```text
information hiding
change amplification
cognitive load
dependency direction
state ownership
```

Refactoring 的目标不是：

```text
abstraction count ↑
```

而是：

```text
future relevant changes cheaper / safer / more local
```

---

# 19. Refactoring 与 bug fix 的边界

假设你移动代码时发现：

```text
某个 corner case 明显错了
```

你顺手修吗？

工程上可能值得修。

但最好不要偷偷藏在“behavior-preserving refactor”里。

更清晰的 chain：

```text
C1 add regression test exposing bug
C2 fix behavior
C3 continue refactoring
```

或者：

```text
C1 refactor unchanged
C2 bug test + fix
```

取决于依赖关系。

关键是 reviewer 能知道：

```text
哪一步理论上 behavior 不应变
哪一步 behavior 应该变
```

---

# 20. Refactoring 与 optimization 的边界

性能优化经常会改变：

```text
time
memory
I/O pattern
cache behavior
parallelism
```

即使 functional output 一样，也可能改变 observable operational behavior。

所以本课程默认把 optimization 看作：

```text
behavioral/operational change
```

除非本次 contract 明确认为这些维度不可观察。

至少应该带：

```text
functional equivalence evidence
+
benchmark / resource evidence
```

而不是把它藏在 cleanup diff 里。

---

# 21. Refactoring under Weak Tests

现实中经常是：

```text
代码很难改
+
tests 很弱
```

能不能重构？

可以，但 proof obligation 更难。

先问：

```text
哪些行为最危险？
能否先补 characterization / contract tests？
能否用 golden output？
能否做 differential run？
能否缩小 change？
```

注意：

```text
先补测试
```

也不是绝对规则。

如果是 IDE 可证明安全的局部 rename，可能 static tooling + search 就够。

但如果是：

```text
改变 control flow
移动 transaction boundary
合并 state machines
```

weak tests 下风险会陡增。

M06 会专门处理 legacy code 的 feedback/seam 问题。

---

# 22. Differential Testing：重构特别有用的证据

如果目标明确是：

```text
behavior before == behavior after
```

那么非常自然的验证方式是：

```text
同一组输入
分别跑 old/new
比较 outputs / side effects
```

例如：

```python
assert old_render(snapshot) == new_render(snapshot)
```

或者：

```text
before trace
vs
after trace
```

这类 differential evidence 对 refactoring 比“重新手写 expected values”经常更直接。

但要小心：

```text
old implementation 本身可能有 bug
```

所以 differential testing 证明的是：

```text
保持旧行为
```

不是：

```text
旧行为本来正确
```

这正是 characterization 与 specification 的区别。

---

# 23. Snapshot / Golden Test：有用，但要知道你冻结了什么

对于 text renderer、compiler output、serialization：

```text
golden output
```

是很有效的 refactoring safety net。

因为它能快速发现：

```text
空格
排序
字段
文本
```

是否变化。

但它也会冻结 accidental detail。

所以 review golden update 时必须问：

```text
这个变化是 feature 要求？
还是 refactor 意外改了 output？
```

最危险的是：

```text
implementation 改了
snapshot 也一起 update
CI green
```

这时 test 可能什么都没保护。

---

# 24. “先全部重构好，再加功能”为什么危险

想象：

```text
feature 实际只需要一个 20 行变化
```

你决定先：

```text
重新设计整个 subsystem
```

两周后：

- 原需求可能变了；
- 新 abstraction 可能不适合真实 feature；
- migration risk 增大；
- review context 丢失；
- branch drift。

这就是为什么 evolutionary design 偏好：

```text
当前需求提供真实压力
→ 做最小有证据的结构改善
→ 实现需求
→ 从新信息继续演化
```

不是因为 upfront thinking 无用。

而是因为设计应该利用真实 change pressure 提供的信息。

---

# 25. 什么时候应该停下来做更大的 redesign？

“小步”不是宗教。

某些情况：

```text
当前 abstraction fundamentally wrong
安全属性无法在现结构表达
数据 ownership 已经不可修补
旧设计把未来每次 change 都放大
```

此时更大 redesign 可能合理。

但这时要承认：

```text
这可能已经不是纯 refactoring
```

需要单独的：

```text
design review
migration plan
compatibility plan
rollback plan
```

不要用“refactor”这个词把风险包装成低风险。

---

# 26. Large-Scale Change：为什么“大目标”不要求“大 commit”

一个全仓 rename / API migration 可能逻辑上是一个目标：

```text
旧 API → 新 API
```

但实际执行可以是：

```text
introduce compatibility layer
→ migrate shard 1
→ migrate shard 2
→ migrate shard 3
→ verify no old call sites
→ remove old layer
```

Google 在大规模代码变更里就是显式 sharding：

```text
master transformation
↓
independently testable/reviewable/submittable pieces
```

Agent 很适合生成 transformation。

但工程系统仍应该决定 shard boundary。

---

# 27. Agent 的一个危险优势：它没有“改累了”的反馈

人改 80 个文件以后通常会开始警觉：

```text
这个 change 是不是太大了？
```

Agent 不会。

它可以继续：

```text
800 files
8000 files
```

所以不能把人的 fatigue threshold 当 change-size guardrail。

需要显式 guardrail：

```text
allowed change surface
semantic checkpoint
max responsibility per patch
required evidence
no behavior change clause
```

---

# 28. 不要只让 Agent 说“我保持了行为”

一个差的验收：

```text
Agent: “Refactoring complete. All tests pass.”
```

更好的要求：

```text
1. 列出你认为必须保持的 observable behaviors。
2. 对每一项说明 evidence。
3. 列出所有 public/interface/schema/config changes。
4. 明确指出是否存在 behavior drift。
5. 提供 old symbol / old path residual search。
6. 展示测试结果，而不是只总结。
```

人再独立验证。

---

# 29. Exploration Patch 可以扔掉

这是 Agent 时代特别值得培养的习惯。

第一次 prompt：

```text
“试着实现这个 feature，先帮助我理解改动面。”
```

Agent 可能产出一个能跑但混乱的 patch。

这个 patch 的价值可以只是：

```text
发现 coupling
发现 hidden contract
发现 missing tests
发现真正 change point
```

不一定要 merge。

如果它把：

```text
refactor + feature + bugfix + cleanup
```

全缠在一起，最好的下一步可能不是继续 patch patch。

而是：

```text
保存理解
reset clean base
按 staged design 重新实现
```

这不是浪费。

探索产生的是 information。

代码只是中间产物。

---

# 30. 一个推荐的 Agent Refactoring Workflow

## Phase A — Read-only reconnaissance

要求 Agent 不改代码，输出：

```text
entry points
call graph
state ownership
public behavior
relevant tests
change pressure
likely refactoring boundary
```

## Phase B — Behavior inventory

明确：

```text
must preserve
may change
unknown / needs decision
```

尤其不要让 unknown 被 Agent 擅自归类为 implementation detail。

## Phase C — Design it twice

至少两个 sequence：

```text
Direct patch
vs
Preparatory refactor + patch
```

比较：

```text
change amplification
evidence cost
rollback
review complexity
new abstractions
```

## Phase D — Structural checkpoints

每一个：

```text
one structural purpose
no intended behavior change
focused evidence
full regression evidence where appropriate
```

## Phase E — Behavior change

单独实现 feature。

## Phase F — Independent review

reviewer 不只看最终 tree。

还看：

```text
change sequence 是否合理
哪些 commit 声称 behavior-preserving
证据是否与 claim 匹配
是否夹带 semantics drift
```

---

# 31. Agent Task Contract：一个模板

不要只说：

```text
把 dashboard 重构一下，然后加 JSON。
```

更好的 contract：

```text
Goal:
- add JSON dashboard output

Current behavior to preserve during preparatory phase:
- existing text output must be byte-for-byte identical
- job ordering unchanged
- no change to TaskForge lifecycle semantics
- no changes to public_api behavior

Phase 1 — reconnaissance:
- identify duplicated domain interpretation required by a second renderer
- propose two designs
- do not edit

Phase 2 — preparatory refactoring:
- structure-only
- keep text behavior identical
- produce before/after behavior-probe evidence
- do not add JSON yet

Phase 3 — feature:
- add JSON renderer with specified schema
- add tests for new behavior

Non-goals:
- no state ownership redesign
- no M04 error semantics changes
- no dependency additions

Review:
- report any behavior drift explicitly
```

这就是把 software engineering knowledge 转成 Agent search space constraints。

---

# 32. Refactoring Review Checklist

看到一个“纯重构”PR，先问：

## Intent

- 为什么现在做？
- 它服务哪个近端 change pressure？
- 是否只是 aesthetic cleanup？

## Behavior

- observable boundary 是什么？
- 明确保持哪些行为？
- 是否有 hidden compatibility surface？

## Structure

- complexity 真下降了吗？
- change amplification 是否下降？
- 有没有只是增加 abstraction count？

## Evidence

- tests 保护的是 contract 还是 implementation？
- 有没有 before/after differential evidence？
- 有没有 static/search evidence？

## Change topology

- 能不能进一步拆？
- 每个 checkpoint 都能运行吗？
- rollback 是否局部？

## Scope

- 是否夹带 bugfix？
- 是否夹带 feature？
- 是否夹带 formatting/generated churn？

---

# 33. “全部 formatting 一遍”为什么会伤害 refactoring review

假设真实结构改动只有 30 行。

Agent 顺手：

```text
格式化 50 个文件
排序 imports
改 quote style
rename local variables
```

现在 reviewer 的 visual signal 被淹没。

这不是说 formatting 不应该做。

而是：

```text
mechanical churn
```

最好与：

```text
semantic/structural reasoning
```

分离。

如果 formatter change 必须发生，可以先做独立 mechanical commit，再做结构变化。

---

# 34. Rename 是最简单的 refactoring，但也能失败

rename 看起来很机械。

仍可能漏：

```text
reflection strings
config keys
serialization names
CLI flags
docs examples
dynamic imports
external consumers
```

所以 rename 的 correctness argument 常常是：

```text
compiler/type checker
+
tests
+
repository search
+
external compatibility decision
```

Agent 很擅长 grep + rename。

人必须决定哪些字符串是 contract。

---

# 35. Move Code 也不是纯文本操作

把函数从 `a.py` 移到 `b.py` 可能改变：

```text
import cycles
initialization order
module side effects
visibility
package API
test monkeypatch targets
serialization paths
plugin discovery
```

所以“只是 move”要有自己的 behavior inventory。

这也是为什么小步重要。

---

# 36. Refactoring 与 abstraction boundary

M02 的 information hiding 在 M05 里变成一个动态问题：

```text
下一次 change pressure 从哪里穿过系统？
```

如果新增 renderer 迫使：

```text
renderer A 理解 status semantics
renderer B 也理解 status semantics
renderer C 将来也要理解
```

那么 change pressure 暗示：

```text
这些 shared semantic facts
```

可能应该被抽到更深的 boundary。

好的 evolutionary design 往往不是提前猜完未来。

而是：

> **让重复出现的真实 change pressure 告诉你 abstraction 应该在哪里。**

---

# 37. Refactoring 与 ownership

M02 的另一个原则也要保持：

重构不能为了“分层”制造第二份 authority。

例如：

```text
Service owns job state
```

重构 dashboard 时不要顺手创建：

```text
DashboardCache.status_by_job
```

然后变成：

```text
谁是真的？
```

presentation model 可以是 snapshot / projection。

但 authority 要清晰。

---

# 38. Refactoring 与 errors

M04 刚刚讲过 error contract。

因此重构 boundary 时尤其检查：

```text
KeyError → ApiError
```

如果发生了，那是 behavior change。

即使新 error “更好”。

不要把它藏在：

```text
refactor error handling
```

里面。

正确做法可能是：

```text
C1 restructure error translation plumbing, externally same
C2 intentionally change public error contract
```

---

# 39. 一个好的 refactoring commit message 应该说明什么

差：

```text
refactor stuff
cleanup
reorganize code
```

更好：

```text
refactor: isolate dashboard fact construction from text rendering
```

描述里说明：

```text
Why:
- JSON renderer would otherwise duplicate status/count interpretation.

Behavior:
- existing text output remains byte-for-byte unchanged.

Evidence:
- dashboard behavior probe unchanged
- core tests pass

Non-goals:
- no JSON behavior yet
- no public API/error changes
```

这同时服务 reviewer 和未来 archaeology。

---

# 40. Exercise：给 change 分类

下面哪些是 pure refactoring？

### A

```text
rename private helper
all call sites updated
no public string/config impact
```

通常：是。

### B

```text
extract helper
同时修复 null corner case
```

不是纯 refactoring；混了 bug fix。

### C

```text
把 dict 换成 list
对外顺序从不稳定变稳定
```

要看 ordering 是否 observable；很可能 behavior change。

### D

```text
把同步 RPC 改 async
结果值相同
```

通常不能简单算 pure refactor，因为 timing/lifecycle/cancellation semantics 变化巨大。

### E

```text
换更快算法
返回值相同
```

如果 performance 不在 contract，理论上可能被看作 behavior-preserving；但工程上建议把 optimization 单独 review，因为 operational behavior 是目标本身。

---

# 41. Exercise：拆 change chain

需求：

```text
给 TaskForge 增加 JSON dashboard。
```

你发现 text renderer 内部同时做：

```text
state classification
counts
presentation labels
formatting
```

请设计两条路径：

## Direct

```text
?
```

## Preparatory

```text
?
```

对每一步写：

```text
hat:
observable behavior:
evidence:
rollback:
```

不要先写代码。

---

# 42. TaskForge M05 Lab

实际实验见：

[`../labs/05-refactoring-evolutionary-design.md`](../labs/05-refactoring-evolutionary-design.md)

你会得到一个：

```text
功能正确
但 domain interpretation 与 text formatting 缠在一起
```

的 dashboard renderer。

新需求：

```text
增加 JSON renderer
```

实验故意让“直接复制逻辑”非常容易。

你的任务不是单纯写 JSON。

而是比较：

```text
Direct feature patch
vs
Preparatory refactor → feature patch
```

并保持已有 text behavior 在 refactoring phase **byte-for-byte unchanged**。

---

# 43. 本章最重要的十句话

1. **Refactoring 是 behavior-preserving structural change，不是所有 cleanup 的总称。**
2. **说“behavior-preserving”之前，先定义谁能观察什么。**
3. **结构变化和行为变化可以频繁交替，但不要让一个 change step 同时承担两个 proof obligation。**
4. **small 的核心是 semantic/review size，不是机械 LOC 阈值。**
5. **每个 semantic checkpoint 应处于可运行、可验证、可回退的 coherent state。**
6. **preparatory refactoring 服务近端 change pressure，不是借 feature 做全仓春季大扫除。**
7. **First / After / Later / Never 都可能是正确答案。**
8. **最终架构不是唯一设计对象；从旧状态走到新状态的 change topology 也是设计。**
9. **Agent 的巨大 implementation bandwidth 不会消除 review、compatibility 和 rollback 成本。**
10. **如果探索 patch 已经不可 review，保留理解、丢掉代码、从 clean base 重做，完全可能是更好的工程选择。**

---

# 44. 可选原始资料

本章自包含。希望核对原始观点时：

- Martin Fowler, Refactoring: https://martinfowler.com/books/refactoring.html
- Fowler, Definition of Refactoring: https://martinfowler.com/bliki/DefinitionOfRefactoring.html
- Fowler, Workflows of Refactoring: https://martinfowler.com/articles/workflowsOfRefactoring/fallback.html
- Fowler, Preparatory Refactoring: https://martinfowler.com/articles/preparatory-refactoring-example.html
- Kent Beck, Tidy First?: https://www.oreilly.com/library/view/tidy-first/9781098151232/
- Google Engineering Practices, Small CLs: https://google.github.io/eng-practices/review/developer/small-cls.html
- Software Engineering at Google, Large-Scale Changes: https://abseil.io/resources/swe-book/html/ch22.html
- Stanford CS190/APOSD: https://web.stanford.edu/~ouster/cs190-winter24/lectures/aposd/

具体审计与取舍见：

[`../reading-notes/m05-source-audit.md`](../reading-notes/m05-source-audit.md)
