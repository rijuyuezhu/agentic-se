# M12 — Agentic Software Engineering：把 Engineering Authority 变成可执行工作系统

> Agentic Software Engineering 不是“让模型写更多代码”。
>
> 它真正的问题是：**当 implementation bandwidth 突然变得非常便宜、Agent 可以读仓库、运行命令、修改文件、并行工作甚至触碰外部系统时，怎样仍然让系统语义、风险接受和长期结构处于可解释的 engineering authority 之下？**

前十一章已经分别训练：

```text
M01  specification / invariant
M02  ownership / information hiding
M03  executable evidence
M04  boundary / error / retry semantics
M05  staged safe change
M06  reconnaissance / characterization / seams
M07  concurrency / crash / failure
M08  compatibility / migration
M09  architecture / consequential boundaries
M10  independent review
M11  production evidence / SLO / reliability
```

M12 不再引入一个新的“软件设计名词”。

它要做的是把前面这些能力变成一个 Agent 可以参与、但不能偷偷替代人类判断的工程流程。

本章的核心公式是：

```text
Agent capability
       ×
engineering context
       ×
feedback quality
       ×
authority discipline
       =
useful software work
```

任何一项接近零，都可能得到大量代码，但得不到可靠系统。

---

# 1. Agent 时代真正变化了什么？

过去一个 change 的成本常常主要来自：

```text
理解
+
写代码
+
写测试
+
跑验证
+
review
```

Agent 最先大幅压低的是：

```text
implementation effort
mechanical search
mechanical transformation
boilerplate tests
repetitive investigation
```

但它没有自动压低：

```text
What behavior should exist?
Which behavior is accidental?
Who owns this state?
What can safely change together?
What evidence is sufficient?
What risk are we willing to accept?
Can this be rolled out / rolled back?
Should this patch merge at all?
```

因此一个反直觉现象会出现：

> **代码生成越快，错误 engineering decision 的放大速度也越快。**

以前一个糟糕 abstraction 可能需要工程师花两天才扩散到十二个文件。

现在 Agent 可以在几分钟内“统一重构”整个仓库。

如果 underlying model 错了，速度只会让 recovery 更贵。

所以本课程一直重复：

> **Agent 可以代替 implementation effort，但不能自动代替 engineering authority。**

注意“自动”两个字。

Engineering authority 当然可以被委托给 automation。

但必须明确：

```text
谁授权？
授权做什么？
在什么 evidence 下？
最大 blast radius 是多少？
何时必须停止并升级？
怎样撤销？
```

如果这些没有答案，所谓 autonomy 往往只是 invisible policy。

---

# 2. 先区分 Capability、Permission、Authority

这是 M12 最重要的三个词之一。

很多 Agent workflow 把它们混成同一件事。

## 2.1 Capability

Agent 技术上能不能做到？

例如：

```text
read files
edit Python
run pytest
call GitHub API
SSH to production
delete object storage
merge PR
```

这是能力问题。

---

## 2.2 Permission

当前执行环境允许不允许？

例如：

```text
sandbox read-only
workspace-write
network disabled
GitHub token only has read
production token absent
```

这是 access-control 问题。

OpenAI 当前 Codex 文档就明确把 sandbox mode 与 approval mode 作为执行环境的一部分，并建议默认保持权限较紧，只在可信 workflow 中按需要放宽。

但 permission 仍然不等于 authority。

---

## 2.3 Authority

即使 Agent 技术上能做、credential 也允许，它**是否应该拥有这个决定的语义权力**？

例如：

```text
CI green
```

Agent 可能有 permission：

```text
merge PR
```

但 repository governance 仍可能规定：

```text
accept residual compatibility risk
=
human maintainer authority
```

所以：

```text
Capability: can do
Permission: may execute
Authority: may decide
```

这三者不能偷换。

这里还故意没有展开两个相邻问题：permission 为什么应该按 asset / trust boundary / least privilege 设计，以及最终 human authority 为什么同时也是责任边界。分别见旁支 [Security Engineering：从 trust boundary 到 Agent authority](../extensions/security-engineering.md) 和 [Professional Practice：责任、沟通、隐私与许可](../extensions/professional-practice-ethics-law.md)。如果问题变成“多个 Agent 怎样并行而不把 review queue 和 shared-state coordination 做爆”，则见 [Process、Feedback 与 Team Coordination](../extensions/process-feedback-and-team-coordination.md)。

---

# 3. Tool Surface 就是 Authority Surface

Software Agent 的输出不只是聊天文本。

它可能：

- 修改 working tree；
- 创建 commit；
- push branch；
- 发 PR；
- 写 issue；
- 调数据库；
- 改配置；
- deploy；
- 触发云资源；
- 发邮件；
- 改 production state。

因此：

> **工具列表不是 UX 配置，而是系统 capability graph。**

一个 Agent harness 如果给模型：

```text
repo write
production SSH
cloud admin
GitHub merge
secret store
```

却只用一句：

```text
“请谨慎操作”
```

来区分权限，是一个非常脆弱的设计。

更好的结构是：

```text
Exploration environment
  read-only repo
  test/log access

Implementation environment
  isolated worktree
  local tests
  no production credentials

Review environment
  base + diff + evidence
  read-only first pass

Release environment
  explicit policy gate
  narrowly scoped credentials
```

把不同 phase 的 capability surface 变成架构。

---

# 4. Prompt 不是完整的 Agent Harness

一个常见误区：

```text
Agent 结果不好
→ prompt 再写长一点
```

但 Agent 的行为由至少这些因素共同决定：

```text
instructions
repository context
tool definitions
permissions
working directory
current files
history / progress artifacts
tests / verifier
runtime feedback
external systems
context-window state
```

所以更准确地说：

```text
Agent behavior
=
model
+
context architecture
+
tool architecture
+
feedback architecture
+
authority policy
```

Prompt 只是其中一部分。

Anthropic 的 agent engineering 材料也强调：复杂 framework 并不是自动更好，应该从能完成目标的最简单 workflow 开始，只在必要时增加 autonomy 与 orchestration complexity。

这和软件设计完全一样：

> 不要为了“Agentic”而造 architecture。

---

# 5. Task Contract：不要只写“帮我修一下”

OpenAI 当前 Codex best-practices 给出了一个非常好的最小 prompt envelope：

```text
Goal
Context
Constraints
Done when
```

M12 以此为起点，但对大型软件 change 扩展成：

```text
Goal
Context
Non-goals
Known contracts / invariants
Affected boundaries
Allowed write scope
Forbidden actions
Evidence contract
Stages
Stop conditions
Escalate when
Authority matrix
Done when
```

这不是为了写长文档。

每一项都在消除一种常见失败。

---

# 6. Goal：最终改变什么 observable behavior？

坏任务：

```text
Improve TaskForge overload handling.
```

它允许 Agent 自己发明：

- overload 是什么；
- “improve”是什么意思；
- 是否可以降低 SLO；
- 是否可以拒绝请求；
- 是否允许改变 public API；
- 是否要上 Redis/Kafka；
- 是否允许改历史 tests。

更好的 goal：

```text
Add an opt-in admission-control path so burst overload can be
rejected explicitly before creating work, while preserving the
legacy default path when admission control is disabled.
```

它仍然没有解决全部语义，但已经限定了 change shape。

---

# 7. Non-goals：主动缩小搜索空间

Agent 很擅长发现“顺手可以一起修”的问题。

例如：

```text
while here:
- replace global state
- add SQLite
- redesign errors
- rename ids
- modernize tests
```

每个单独看都可能合理。

合在一次 change 里：

```text
review surface ↑
compatibility uncertainty ↑
rollback ambiguity ↑
```

因此 non-goal 不是消极限制。

它是一种 change-topology design。

例如：

```text
Do not:
- add a database
- redesign historical M04 errors
- change M11 SLO
- fix M07 teaching race
```

它告诉 Agent：

> 发现问题可以报告，但不要自动把所有问题纳入当前 authority scope。

---

# 8. Contract / Invariant：告诉 Agent 什么不能被“优化掉”

一个 Agent 看见：

```python
next_job_number += 1
```

可能觉得 rejection 时也先 allocate ID 更简单。

如果 contract 明确：

```text
Rejected admission:
- creates no Job
- consumes no id
```

那么搜索空间立刻缩小。

同样：

```text
M11 SLO denominator = accepted jobs
```

必须写进任务。

否则 Agent 为了“让 dashboard 变绿”完全可能把 bad work 从 denominator 移除。

这不一定是模型“作弊”。

它可能只是在优化你给它的 objective。

于是一个重要规律出现：

> **Agent 会高效放大 specification quality。**

好 spec 放大成好实现。

坏 spec 也可能被高质量执行。

---

# 9. Allowed Write Scope：限制“能改哪里”

Write scope 是非常低成本、非常高价值的约束。

例如：

```text
allowed:
  public_api.py
  service.py
  tests/

forbidden:
  snapshot fixtures
  production_signals.py
  release workflow
```

它不是说 Agent 不能读其他文件。

相反：

```text
read broadly
write narrowly
```

通常是一个很好的默认。

因为 understanding scope 和 mutation scope 本来就不同。

---

# 10. Forbidden Actions：显式写出 side-effect red lines

只限制文件路径还不够。

Agent 可能有外部工具。

所以还要表达：

```text
Do not:
- merge
- deploy
- rotate credentials
- rewrite production data
- lower SLO
- delete regression evidence
```

特别注意：

```text
lower SLO
```

不是 filesystem permission。

它是 semantic authority boundary。

所以真正高质量的 Agent contract 必须同时包含：

```text
resource boundary
+
semantic boundary
```

---

# 11. Evidence Contract：先规定“怎样知道做对了”

不要只写：

```text
run tests
```

M03、M10 已经说明这远远不够。

更好的 evidence contract 是 claim-oriented：

| Claim | Required evidence |
|---|---|
| rejection 无副作用 | reject 前后 job count / next id evidence |
| legacy path 不变 | old contract regression |
| overload machine-readable | public-boundary semantic assertion |
| 未 game SLO | threshold/denominator unchanged |
| concurrency guarantee | deterministic or otherwise explicit concurrency evidence |

也就是说：

```text
claim
→ oracle
→ evidence source
```

而不是：

```text
run everything
→ green
→ done
```

---

# 12. Stop Conditions：让“停止”成为成功状态

这是很多 Agent workflow 最缺的东西。

坏 harness 只有两种状态：

```text
keep working
or
claim done
```

但真实软件工程还有第三种非常重要的结果：

```text
STOP_AND_ESCALATE
```

例如 Agent 发现：

```text
Task says:
  reject overload explicitly

But public API currently has no authorized overload result shape.
```

如果它自己发明：

```json
{"error": "busy"}
```

它可能已经跨越 compatibility authority。

更高质量的行为是：

```text
I cannot implement without choosing a new public contract.
Here are two options and their consequences.
Please decide.
```

这不是 Agent “能力不足”。

这是 engineering discipline。

---

# 13. Escalation Trigger 应该具体

不要写：

```text
If unsure, ask.
```

这会产生两种极端：

- Agent 什么都问；
- Agent 自信时什么都不问。

更好的 trigger：

```text
Escalate when:
- a public contract must change;
- a new source of truth would be introduced;
- migration ordering is underspecified;
- production threshold must be invented;
- credentials / write scope must expand;
- evidence required by the task cannot be produced;
- rollback semantics change.
```

这把 uncertainty 和 authority 对齐。

---

# 14. Exploration Agent 与 Implementation Agent 不应该是同一个 phase

“先只读调研”并不是因为 Agent 写代码很危险才这样做。

它有更深的 reasoning 价值。

如果任务一开始就允许 edit，Agent 很容易发生：

```text
first plausible hypothesis
        ↓
start patching
        ↓
new evidence interpreted around existing patch
        ↓
sunk-cost attachment
```

先做 read-only reconnaissance：

```text
entry points
callers
state reads/writes
data flow
contract surface
existing tests
historical probes
failure paths
```

可以先形成 candidate model。

然后人类/主 Agent 再判断：

```text
model is sufficient?
unknowns resolved?
write scope correct?
```

才进入 implementation。

---

# 15. Read Broadly, Write Narrowly

陌生 repo 调研时，应鼓励：

```text
search broadly
read callers
read tests
read docs
read history if needed
```

但 mutation 时：

```text
small write set
```

这是一个非常实用的 agent workflow heuristic：

> **理解需要跨边界；修改不应该无边界。**

---

# 16. Planning Artifact 的价值是减少 Hidden State

长任务经常跨：

- context window；
- Agent session；
- 人类工作日；
- reviewer；
- branch；
- release window。

如果关键 state 只存在聊天里：

```text
what has been tried?
what remains?
what is blocked?
which assumptions changed?
which evidence is already collected?
```

下一轮只能重新猜。

OpenAI ExecPlan 和 Anthropic long-running harness 都强调将 progress 外部化。

本课程把这推广成：

```text
conversation state
!=
engineering state
```

Engineering state 应尽量进入 durable artifacts：

```text
issue
plan
ADR
test
commit
diff
progress record
migration checklist
benchmark result
```

---

# 17. Durable Plan 必须能被“失忆的新 Agent”读懂

一个很好的 plan test：

> 假设执行者完全没有昨天的 chat history，只拿到当前 tree 和 plan，它能否继续？

如果答案是否定：

```text
plan still depends on hidden memory
```

这也是为什么：

```text
“我们刚才讨论过”
```

不是 durable engineering artifact。

---

# 18. Incremental Progress 不是因为 Agent 弱

即使模型以后强很多，incremental change 仍有价值：

- failure localization；
- rollback；
- reviewability；
- bisect；
- handoff；
- evidence attribution；
- compatibility windows。

所以 Anthropic 观察到 Agent “一次做太多”会留下半完成状态，这不仅是某代模型 limitation。

它映射到传统工程原则：

> **小的可验证状态转换，比巨大的不可观察 leap 更容易治理。**

---

# 19. “Clean State at Handoff” 是一个 Contract

Agent session 结束不能只给一句：

```text
“差不多好了，还剩一点。”
```

应该留下：

```text
working tree state
commit / diff
what passed
what failed
known limitations
next step
blocked questions
```

如果 handoff point 不是 clean：

必须明确：

```text
DO NOT TREAT AS MERGEABLE
```

否则下一个 Agent 很容易误判已有进度为稳定 baseline。

---

# 20. Self-review 有价值，但不等于 Independent Review

Implementation Agent 最后应该 self-review。

因为它最知道：

- 改了什么；
- 哪些 workaround；
- 哪些 test 新增；
- 哪些 corner case 怀疑。

但它也共享：

```text
same assumptions
same blind spots
same interpretation of task
same sunk cost
```

所以 acceptance path 需要更独立的 pass。

M10 已经训练：

```text
base
+
task contract
+
diff
+
evidence
```

让 reviewer 自己恢复 change model。

---

# 21. 为什么 Reviewer 第一轮不应该只读 Implementer Summary？

Implementer summary 很有用。

但它是一种 framing。

如果 reviewer 先读：

```text
“This is a safe refactor; behavior unchanged.”
```

就更容易围绕这个 claim 搜证据。

因此高风险 change 可以采用：

```text
First pass:
  task + base + diff + evidence

Second pass:
  compare implementer summary
```

目的不是制造敌对关系。

而是减少 correlated reasoning failure。

---

# 22. Independent 不等于“必须不同模型”

可以有很多独立性层次：

```text
same agent, fresh context
same model, separate session
different role prompt
different model
human maintainer
independent runtime probe
formal/static checker
production canary
```

独立性的本质是：

> **不要让所有 acceptance evidence 共享同一个 failure mode。**

如果 implementation Agent：

- 写 code；
- 写 tests；
- 定 oracle；
- 解释 test；
- review 自己；
- merge；

那么这个 pipeline 虽然有很多 stage，实际上仍只有一个 reasoning authority。

---

# 23. Multi-Agent：先并行问题，不要先并行写入

OpenAI 当前 subagent guidance 给出了一个很实用的方向：read-heavy exploration、testing、triage 比 shared write-heavy tasks 更自然。

例如陌生大型 change：

```text
Agent A
  ownership / data flow

Agent B
  compatibility / migration

Agent C
  tests / failure evidence
```

最后由主 Agent / human synthesize。

这通常比：

```text
three agents edit overlapping source files
```

更稳。

原因和多人开发一样：

```text
shared mutable state
→ coordination cost
```

---

# 24. Merge Conflict 只是最容易看见的冲突

两个 Agent 即使修改不同文件，也可能 semantic conflict：

```text
Agent A:
  JobAuthority owns cancellation

Agent B:
  public_api keeps local cancellation cache
```

Git 可以 clean merge。

Architecture 已经坏了。

因此 parallel write 的真正 prerequisite 不是：

```text
files do not overlap
```

而是：

```text
semantic authority / contracts are decomposable
```

---

# 25. Task Decomposition 本身是 Engineering Work

Anthropic 的 C compiler experiment 里，多 Agent 在大量独立 failing tests 上容易并行；进入一个巨大 Linux-kernel bottleneck 后，很多 Agent 会撞同一个问题并覆盖彼此。

这说明：

```text
number of agents
```

不是主要 throughput 参数。

更重要的是：

```text
independent work units
clear verifier
coordination surface
```

如果任务本身不可分：

增加 Agent 数只会增加拥堵。

---

# 26. Harness 不是越复杂越好

Anthropic 2026 harness-design 文章有一个很有价值的提醒：

> harness 每个 component 都编码了“模型需要这个辅助”的假设。

模型能力变化后，旧 scaffolding 可能：

- 不再必要；
- 增加 latency；
- 增加 cost；
- 误导模型；
- 形成 maintenance burden。

所以 Agent harness 也应遵循 M05：

```text
observe failure
→ add smallest support
→ measure
→ later simplify experimentally
```

而不是不断追加 prompt rules。

---

# 27. “再加一句 instruction”也是 Technical Debt

如果每次 Agent 犯错就追加：

```text
Never do X.
Always remember Y.
Also check Z.
```

几年后会形成：

```text
5000-line contradictory prompt
```

更好的 classification：

```text
Repeated semantic rule
→ code/API boundary

Repeated acceptance rule
→ test / linter / policy checker

Repeated workflow
→ script / skill

Repeated repo knowledge
→ scoped documentation / AGENTS.md

One-off task constraint
→ task contract
```

也就是说：

> **把自然语言规则逐渐编译成更强的工程机制。**

---

# 28. Instruction Scope 也需要 Information Hiding

OpenAI/GitHub 当前工具都开始支持 repository-wide、path-specific、task-specific agent instructions。

这和 M02 一样：

```text
knowledge should live near the boundary it governs
```

例如：

```text
root guidance:
  release / security / repo-wide commands

storage/AGENTS.md:
  schema ownership / migration invariants

ui/AGENTS.md:
  accessibility / frontend tests
```

比所有规则堆在 root 更容易维护。

---

# 29. Agent Evaluation 仍然是 Testing 问题

Agent eval 看起来很新。

本质仍是 M03：

```text
input
→ system behavior
→ oracle / grader
```

只是现在 system behavior 变成：

```text
many turns
many tool calls
state mutation
adaptation
```

所以 evaluator 更难设计。

Anthropic 当前 eval guidance 也明确强调 agent tool-use 和 state mutation 使 failure 能跨多步累积。

因此问：

```text
pass rate?
```

之前先问：

```text
what exactly does the grader distinguish?
```

---

# 30. Benchmark Pass 不等于 Mergeable

SWE-bench 是非常重要的 benchmark。

它把任务从：

```text
complete this function
```

推进到了：

```text
real GitHub issue
+
repository
+
code changes
+
tests
```

但仍然不能直接等于：

```text
maintainer would merge
```

METR 2026 的 maintainer-review 研究对一批 SWE-bench Verified agent patches 做真实 maintainer-style review，发现 automated grader 与 maintainer merge judgment 有明显 gap。

研究自己也非常谨慎：

- Agent 没有获得真实 contributor 那样的 review/iteration loop；
- sample 只覆盖部分 repos；
- maintainer judgment 有 noise；
- 不应解释成模型 fundamental ceiling。

课程使用它只支持一个结论：

> **Automated grader 是 evidence，不是 repository acceptance authority。**

---

# 31. Agent 最容易“优化错误目标”

如果 verifier 是：

```text
SLO dashboard green
```

Agent 可能：

- 修 capacity；
- 加 admission control；
- 或降低 threshold；
- 或改 denominator；
- 或删告警。

从优化问题角度，这些都能改变 objective。

所以：

> **Verifier 必须尽量锁定 semantic intent，而不是某个易被修改的 proxy。**

这和 reward hacking、Goodhart's law 有相似结构，但 M12 不需要把它神秘化。

就是普通 software testing：

```text
oracle weak
→ wrong implementation survives
```

只不过 Agent 更擅长快速探索 oracle 的空隙。

---

# 32. Acceptance Criteria 不应完全由 Candidate Patch 控制

一个非常重要的 trust-boundary 问题：

如果 PR 可以同时修改：

```text
implementation
+
tests
+
review instructions
+
CI workflow
```

那么它可能同时改变：

```text
thing being judged
+
judge
```

当然很多正常 feature 合法地需要改 tests。

问题不是“禁止改 evaluator”。

问题是：

> **Evaluator changes 需要独立审查，因为它们改变 acceptance semantics。**

GitHub 当前 Copilot review 文档甚至明确说明，review 时使用的是 head branch 中的 instructions / skills。

这提醒我们：

```text
review policy itself
```

也是 trust boundary。

---

# 33. Agent Productivity 必须被测，而不是被感觉

METR early-2025 RCT 有一个非常有意思的结果：某组熟悉自己成熟 repo 的 experienced developers 使用当时 AI tools 时实际变慢，但主观仍认为自己变快。

到 2026，他们又明确指出 newer-tool follow-up 遇到严重 selection effects，无法给可靠 current uplift estimate；并行 Agent 还让 time tracking 变难。

课程不拿这些数据证明“AI 没用”。

真正的 lesson：

```text
perceived speed
!=
measured workflow outcome
```

团队应该根据目标测：

```text
lead time
review time
rework
escaped defects
incident rate
change size
merge acceptance
maintenance burden
```

而不是：

```text
“感觉一天写了好多代码”
```

---

# 34. Code Volume 是越来越差的 Productivity Proxy

Agent 时代，LOC 的边际生成成本迅速下降。

所以：

```text
lines generated
commits produced
PR count
```

会越来越难代表价值。

反而应该看：

```text
validated behavior change
maintainability
risk reduced
cycle time
review load
production outcome
```

这与 M00 的课程起点闭环：

> Software Engineering 从来就不主要优化 typing speed。

---

# 35. Human-in-the-loop 不是一个 Boolean

很多讨论只问：

```text
human in loop?
```

实际上应该画 authority ladder。

例如：

```text
L0  Agent proposes text only
L1  Agent reads repo
L2  Agent edits isolated worktree
L3  Agent runs local tests
L4  Agent pushes branch / opens PR
L5  Agent requests review / responds to comments
L6  Agent merges under policy
L7  Agent rolls out canary
L8  Agent changes production broadly
```

不同系统可以在不同层自动化。

真正的问题：

```text
每升一级，新增了什么 blast radius？
什么 evidence 支撑这个 authority transfer？
如何 revoke？
```

---

# 36. Reversibility 决定可以给多少 Autonomy

通常更适合自动化的动作：

```text
read-only exploration
create disposable worktree
run test
write draft
open non-merging PR
```

更需要谨慎的动作：

```text
delete durable data
rotate credentials
schema contract
public release
production traffic shift
```

不是因为 Agent “不可信”。

而因为：

```text
expected cost of error
=
probability × blast radius × recovery cost
```

任何 automation 都应该这样设计。

---

# 37. Production Agent 的 Stop Condition 比 Coding Agent 更重要

coding Agent 错了：

```text
reset worktree
```

production Agent 错了：

可能是：

```text
customer impact
lost state
security incident
```

所以 production action 应至少考虑：

```text
bounded scope
preconditions
idempotency
rollback
rate limit
canary
audit trail
human escalation
```

这直接复用 M04/M07/M08/M11。

Agentic operations 并没有发明新的可靠性定律。

它只是让已有可靠性原则变得更重要。

---

# 38. Agent 应该被允许说“不知道”

一个坏 task environment 会隐式奖励：

```text
always produce a patch
```

于是 uncertainty 会被转换成 guess。

更好的 completion state 包括：

```text
DONE
BLOCKED
NEEDS_DECISION
EVIDENCE_GAP
CONTRACT_AMBIGUITY
```

尤其大型系统：

> **准确报告“不足以安全实施”本身就是高价值输出。**

---

# 39. 不要惩罚正确 Escalation

如果团队评价 Agent 只看：

```text
多少任务自动完成
```

Agent workflow 就会倾向：

```text
guess rather than escalate
```

更好的评价应该奖励：

```text
correct implementation
correct stop
correct escalation
correct rejection of unsafe request
```

这和分类器的 abstention / selective prediction 很类似。

但在工程上不需要数学化也能理解。

---

# 40. Agent Task Contract 是一份 Delegation Contract

它不只告诉 Agent：

```text
what to build
```

还告诉它：

```text
what decisions have already been made
what decisions are still reserved
what evidence is required
what actions are forbidden
when authority returns to human
```

所以本章会把它叫：

> **delegation contract**

而不仅是 prompt。

---

# 41. A Good Agent Workflow Can Produce “No Patch”

TaskForge M12 starter 故意留下两个未决问题：

```text
1. overload 的 public machine-readable result shape 是什么？
2. max queued threshold 谁拥有？
```

一个好的 implementation Agent 应该发现：

```text
这些属于产品/compatibility policy
```

然后：

```text
STOP_AND_ESCALATE
```

而不是偷偷选择：

```text
HTTP 429
max_queue=100
```

并宣布 done。

---

# 42. Human Decision Record 不是“聊天里说了可以”

如果人补充决策：

```text
Use new opt-in API.
Threshold is caller-owned.
Machine result uses OVERLOADED.
```

最好形成 durable decision artifact。

因为：

- implementation Agent 需要；
- reviewer 需要；
- future maintainer 需要；
- Capstone / migration 需要。

M12 TaskForge 提供：

```text
human-decision.json
```

不是为了推 JSON 格式。

而是说明：

> authority transfer 应可审计。

---

# 43. 独立 Reviewer 也需要 Authority Matrix

Reviewer 不是 implementation backup。

第一轮它的能力最好是：

```text
read
search
run probes
write findings
```

而不是：

```text
发现 bug
→ 顺手直接修 candidate
→ 再说“review 完了”
```

因为一旦 reviewer 自己修改：

```text
observation
and
remediation
```

又混在一起。

可以在 review decision 之后进入 fix phase。

但 first-pass review 应保持 epistemic separation。

---

# 44. Evidence Packet 应该能独立复跑

Agent 最后不应该只说：

```text
“All tests pass.”
```

应该提供：

```text
claim
command / probe
result
scope
known gaps
```

例如：

```text
Claim:
Rejected admission consumes no id.

Evidence:
pytest tests/test_admission_control.py::test_rejection_does_not_consume_id
PASS

Scope:
single-process opt-in admitted submissions

Gap:
legacy unadmitted submit bypasses policy by design
```

Reviewer 才能独立验证。

---

# 45. Agent Summary 不是 Evidence

这是整章需要牢牢记住的一句话：

```text
Agent says “I checked X”
```

只能证明：

```text
Agent emitted that sentence
```

真正 evidence 可能是：

```text
command output
changed files
runtime behavior
test failure/pass
trace
artifact hash
external system state
```

因此：

> **summary 是 index，不是 proof。**

---

# 46. Evidence 也有 Authority

一个 Agent 可以运行：

```text
pytest
```

但它是否可以：

```text
edit pytest config to skip failures
```

是另一个问题。

所以 verifier / test / baseline 也需要 ownership。

对于高风险 workflow：

```text
candidate cannot freely rewrite all acceptance machinery
```

或者 evaluator changes 本身需要额外 review。

---

# 47. Agent-generated Tests 的危险不是“AI 写测试”

真正危险的是：

```text
same interpretation
→ implementation
→ oracle
```

形成 tautology。

因此可以让 Agent 写 tests。

但要求：

- test claim 来自 contract；
- fail-before 尽可能成立；
- reviewer 检查 oracle；
- negative controls / mutation / alternative implementation 检查 strength。

M03 已经训练过。

M12 只是在 workflow 层重新使用。

---

# 48. Model Choice 不是课程核心

今天：

```text
Model A > Model B
```

几个月后可能反过来。

所以课程不教：

```text
“复杂重构一定用 X”
```

更稳定的是：

```text
task shape
→ required context
→ required tools
→ evidence quality
→ latency/cost budget
→ model/harness experiment
```

然后用实际结果选择。

---

# 49. Harness 必须允许 Model Upgrade

如果 workflow 依赖：

```text
model-specific superstition
```

升级模型时很难判断哪些 rule 还必要。

更好的 harness component 应尽量对应真实 engineering requirement：

```text
repo invariant
security boundary
approval rule
test command
migration protocol
```

而不是：

```text
“模型总是喜欢做 X，所以永远写十句话阻止它”
```

模型-specific workaround 可以有，但必须被标记为 workaround。

---

# 50. Agent Workflow 也需要 Observability

M11 的思路同样适用于 Agent：

如果只记录：

```text
task completed = true
```

看不出：

- token / tool cost；
- number of retries；
- failed approaches；
- review rework；
- escalation；
- test instability；
- scope drift。

但也不要把每个 token 都做成 dashboard。

应该从 operational question 反推：

```text
Why are agent changes taking longer?
Why are review rejects rising?
Where do agents most often escalate?
Which task contracts generate rework?
```

再设计 telemetry。

---

# 51. 一个可维护的 Agent Engineering Stack

可以把 Agent integration 分成五层：

```text
1. Repository knowledge
   docs / AGENTS / commands / architecture

2. Task delegation
   goal / constraints / authority / evidence

3. Execution harness
   sandbox / tools / worktree / progress

4. Verification
   tests / probes / eval / review

5. Governance
   merge / release / production authority
```

如果第 5 层的 policy 全写进第 2 层 prompt：

系统会越来越脆弱。

如果第 1 层全存在某个人聊天记忆：

handoff 会越来越差。

分层就是为了让不同 lifetime 的 knowledge 分离。

---

# 52. TaskForge M12：同一个需求，两种工作方式

需求：

> burst 时 TaskForge 的 start-latency 很差。加入 overload/backpressure handling。

仓库提供：

```text
agent-contracts/m12/vague-task.json
agent-contracts/m12/engineered-task.json
agent-contracts/m12/unsafe-agent-plan.json
agent-contracts/m12/bounded-agent-plan.json
agent-contracts/m12/human-decision.json
agent-contracts/m12/authorized-agent-plan.json
```

以及：

```text
tools/m12_orchestration_probe.py
```

---

# 53. Vague Task 的问题不是“不够客气”

vague task 只有：

```text
“加 overload/backpressure，修好，测试一下。”
```

它缺失：

```text
scope
contracts
non-goals
evidence
authority
stop conditions
```

因此 Agent 做出很多不同 patch 都可能自认为正确。

M12 probe 将它判定：

```text
INSUFFICIENT_CONTRACT
```

---

# 54. Unsafe Plan 不是一个“笨 Agent”

starter 中 unsafe plan 很主动：

```text
- 修改 M11 target
- 改 denominator
- 删除旧 probe
- 改 release workflow
- merge
- deploy
```

如果 objective 只是：

```text
make health green
```

这些动作甚至很“有效”。

问题是它跨越了 task authority。

因此 probe 输出：

```text
REJECT_PLAN
```

这说明：

> Agent safety 不只是在执行危险 shell command 时拦截；语义上的目标偷换也需要 engineering control。

---

# 55. Bounded Plan 的正确结果是 Stop

另一个 plan 做了良好 reconnaissance 后发现：

```text
public overload result 未定义
threshold owner 未定义
```

它没有写代码。

结果：

```text
STOP_AND_ESCALATE
```

在本课程里，这是**成功**。

因为 Agent 正确识别了 authority boundary。

---

# 56. Human Decision 后 Authority 才扩大

`human-decision.json` 决定：

```text
legacy submit_job unchanged
new opt-in submit_job_admitted
caller owns max_queued_jobs
OVERLOADED is machine-readable
reject has zero job/id side effect
M11 SLO unchanged
```

然后才有：

```text
authorized-agent-plan.json
```

结果：

```text
AUTHORIZED_TO_IMPLEMENT
```

注意：

```text
merge / deploy
```

仍然没有被授权。

Authority transfer 是局部的，不是：

```text
“既然允许写代码，那剩下都可以自己处理。”
```

---

# 57. Human Authority 不应该成为单点机械瓶颈

课程强调 human authority，并不是要求：

```text
每一个 rename 都人工审批
```

更成熟的系统会把稳定判断下沉成：

```text
static rule
test
policy-as-code
branch protection
migration checker
rate limit
canary controller
```

于是 human 只处理：

```text
new ambiguity
new risk
new semantics
new tradeoff
```

也就是说最终目标不是“human does everything”。

而是：

> **把已经理解的判断自动化，把真正新的判断保留给 engineering authority。**

---

# 58. Authority Compression

随着系统成熟，可以逐步把 repeated decision：

```text
Human decision
```

压缩成：

```text
repository rule
```

再压缩成：

```text
executable verifier
```

例如：

```text
“不要直接写 state.jobs”
```

一开始是 review comment。

后来可能变成：

```text
architecture fitness test
```

之后 Agent 可以自动遵守。

这就是：

> **Authority is not removed; it is encoded.**

---

# 59. 什么时候 Agent 可以更自主？

一个实用判断矩阵：

| Dimension | 更适合高 autonomy | 更需要 gate |
|---|---|---|
| Reversibility | disposable / revertable | irreversible |
| Blast radius | local | production-wide |
| Contract clarity | explicit | ambiguous |
| Evidence | strong automatic | weak / subjective |
| Environment | sandbox | privileged |
| Novelty | repeated workflow | first-of-kind |
| Failure detectability | immediate | delayed / hidden |
| Compatibility | internal | unknown consumers |

不是用“Agent 智商”一个维度决定 autonomy。

---

# 60. 一个完整的 Agentic Change Loop

本课程推荐的大型 change default：

```text
Human goal
  ↓
Read-only Agent reconnaissance
  ↓
System / change model
  ↓
Human confirms contract + authority
  ↓
Implementation Agent in bounded workspace
  ↓
Claim-oriented evidence
  ↓
Agent self-review
  ↓
Independent reviewer
  ↓
Human adjudication / policy gate
  ↓
Merge
  ↓
Controlled rollout
  ↓
Production evidence
```

不是所有任务都需要全部步骤。

但删除步骤必须有理由，而不是因为“Agent 很强”。

---

# 61. 小任务可以压缩 Loop

例如：

```text
fix typo in internal doc
```

可能直接：

```text
Agent edit
→ diff review
→ merge
```

高风险 schema migration：

可能需要：

```text
recon
→ plan
→ compatibility matrix
→ staged implementation
→ dual-version tests
→ independent review
→ canary
→ migration evidence
→ contract cleanup later
```

流程 complexity 应匹配 change consequence。

---

# 62. Orchestration Quality 的一个粗略模型

可以把 Agent workflow 的价值粗略理解成：

```text
useful throughput
≈
implementation speed
×
probability of correct task model
×
probability verifier catches defects
×
review independence
−
coordination cost
−
rework
−
incident cost
```

因此：

```text
more parallel agents
```

只增加第一项，不保证总值增加。

---

# 63. 最常见的 Agentic SWE Failure Modes

## 63.1 Prompt as architecture

所有规则都塞进 prompt，没有 executable boundaries。

## 63.2 Premature write

还没恢复 system model 就开始修改。

## 63.3 Scope drift

顺手修遍整个 repo。

## 63.4 Authority drift

从“实现”逐渐滑到“改变产品语义”。

## 63.5 Oracle capture

Agent 同时重写 implementation 与 acceptance criteria。

## 63.6 Self-certification

“我已经检查过，没有问题。”

## 63.7 Green-CI completion

CI 绿就宣布 done。

## 63.8 Hidden progress state

关键决策只留在 chat。

## 63.9 Parallel-write chaos

多个 Agent 共享 semantic authority。

## 63.10 Infinite autonomy

没有 stop / budget / escalation condition。

## 63.11 Production privilege leakage

coding environment 顺手带 production credentials。

## 63.12 Benchmark worship

把 benchmark score 当真实工程 acceptance rate。

---

# 64. 怎样 Review 一个 Agent Workflow？

不要只 review 最终 patch。

还要看：

```text
Task contract
  是否完整？

Authority matrix
  是否过宽？

Exploration
  是否先恢复关键 model？

Plan
  是否偷做产品决策？

Evidence
  是否独立于 implementation assumption？

Reviewer
  是否足够独立？

Handoff
  是否 durable？

Production action
  是否被明确授权？
```

Agentic SWE 的 review object 比传统 diff 更大。

---

# 65. Agent-generated Code 应该更严格还是更宽松？

不需要“双重标准”。

同一 repository acceptance standard 即可。

但 Agent 会改变 prior probability：

```text
大量机械一致变更更容易
大量 plausible code 更便宜
```

所以 reviewer 可能需要更多关注：

```text
semantic duplication
unrequested scope
weak oracle
invented policy
subtle compatibility change
```

不是因为 AI code 天生差。

而是生成分布变了。

---

# 66. “Agent 写的”不应成为 Finding

坏 review：

```text
This looks AI-generated.
```

这不是 engineering finding。

好 review：

```text
Blocker: the new cache is a second authority for cancellation state.
```

来源不重要。

违反 invariant 才重要。

---

# 67. 也不要因为是 Agent 写的就全部重写

Agent patch 如果：

- contract 正确；
- design 合理；
- evidence 足够；
- maintainable；

就接受。

Engineering judgment 不是反 AI bias。

目标始终是 system quality。

---

# 68. Agent Can Be Better Than Human at Mechanical Review

Agent 非常适合：

```text
search all callers
compare API usages
enumerate error paths
check migration sites
run broad tests
spot repeated patterns
```

人类应该主动利用这种 bandwidth。

例如 review 一个 rename：

```text
Agent search every old identifier
```

比人眼 scroll 更可靠。

但最终判断：

```text
这个 old identifier 是否 intentionally part of compatibility layer？
```

仍然需要 contract reasoning。

---

# 69. Agent Review 的最佳角色之一：Counterexample Generator

不要只问：

```text
“Review this patch.”
```

可以问：

```text
Find a concrete input/interleaving/version combination that violates the stated contract.
```

或：

```text
Assume this design is wrong. What hidden consumer, crash point, or ownership conflict would expose it?
```

这利用 Agent 的搜索能力补充 M03/M07/M08 reasoning。

---

# 70. Agent Review 的另一个好角色：Repository Historian

可以让 Agent：

```text
git blame
old PR
old tests
release notes
```

恢复：

```text
why this weird code exists
```

但历史 evidence 仍需要判断。

旧 workaround 可能已经 obsolete。

所以：

```text
history explains
not automatically commands
```

---

# 71. Skills / Reusable Workflows

当某个 Agent task 一再重复：

```text
release checklist
migration review
incident triage
PR review
benchmark validation
```

可以把它固化成 reusable skill / script / workflow。

OpenAI/GitHub 当前产品都已经提供类似能力。

课程关注的不是具体格式，而是这个 engineering progression：

```text
ad hoc prompt
→ stable repeated practice
→ reusable workflow
→ executable automation
```

---

# 72. Agent Context 是一种有限资源

把所有 log/test output 塞进主线程会让真正重要的 contract 被淹没。

所以需要 context budgeting：

```text
main thread:
  requirements
  decisions
  current plan
  high-value evidence

subagent/log files:
  raw search output
  full test logs
  exploratory traces
```

OpenAI current subagent docs 和 Anthropic long-running harness 都明确讨论了 noisy context / context pollution 问题。

这不是 token optimization 小技巧。

它是 information architecture。

---

# 73. Summarization 也会丢信息

context compaction / progress summary 很有用。

但：

```text
summary
!=
original evidence
```

所以重要 artifact 应可重新打开：

```text
exact diff
exact test output
exact plan
exact issue text
```

summary 只做 navigation layer。

这与：

```text
Agent summary != proof
```

完全一致。

---

# 74. Long-Running Agent 的真正 Memory 是 Environment

最可靠的 memory 往往不是模型隐状态。

而是：

```text
git
files
issues
plans
tests
database
logs
```

因此：

> **把关键进度写进外部世界，是 Agent 软件工程最重要的 memory design 之一。**

---

# 75. 不要让 Progress File 成为第二 Authority

但这里又回到 M02。

如果：

```text
progress.md says migration complete
```

而实际数据库还有 old rows：

谁是真相？

Progress artifact 只能记录：

```text
engineering belief / plan state
```

真正 system state 仍由对应 authority / telemetry 决定。

所以 durable memory 也需要 state ownership。

---

# 76. Agentic SWE 不是把 SDLC 每一步都做成 Agent

不要机械设计：

```text
requirements agent
architect agent
coder agent
tester agent
reviewer agent
release agent
```

这很容易重新发明一个昂贵的角色剧场。

先问：

```text
哪里需要 independent reasoning？
哪里能 parallelize？
哪里需要不同 permission？
哪里有不同 authority？
```

角色应该来自 boundary，而不是来自组织图。

---

# 77. Workflow vs Agent

Anthropic 的定义很实用：

```text
workflow:
predefined orchestration path

agent:
model dynamically directs process/tool use
```

M12 的推荐是混合：

```text
Deterministic:
  regression command
  forbidden-path checker
  schema checker

Agentic:
  reconnaissance
  alternative design generation
  failure-mode discovery

Human/policy:
  ambiguous semantics
  residual risk
  authority escalation
```

用最合适的执行者，而不是“所有东西 Agent 化”。

---

# 78. Production Autonomy 应该从 Narrow Policy 开始

例如比起：

```text
Agent may deploy anything when it thinks ready
```

更合理的 delegation：

```text
If:
- exact release branch
- CI suite A/B/C green
- canary SLO within threshold
- no migration pending
- diff does not touch security/config paths

then:
- promote canary from 5% to 20%

otherwise:
- stop and page owner
```

这时 autonomy 实际上是：

```text
policy execution
```

而不是无边界判断。

---

# 79. 最终目标：Human Focus on Novel Judgment

好的 Agentic SWE 系统应该逐渐让人少做：

```text
search
boilerplate
mechanical edits
routine validation
status aggregation
```

更多做：

```text
new product semantics
risk tradeoff
architecture boundary
compatibility choice
incident judgment
acceptance standard
```

这才是真正的 leverage。

---

# 80. M12 的最终检查表

开始 Agent task 前：

- 我知道真正 goal 吗？
- non-goal 写了吗？
- 关键 contract/invariant 写了吗？
- write scope 和 tool permission 合理吗？
- 什么决策仍保留给 human？
- evidence contract 是什么？
- 什么情况必须 stop/escalate？

实施中：

- Agent 是否先恢复 system model？
- scope 是否 drift？
- 是否开始改变 evaluator？
- 是否发明未授权 policy？
- progress 是否 durable？

结束时：

- evidence 能独立复跑吗？
- reviewer 是否独立？
- historical probe 失效是否被正确解释？
- residual risk 谁接受？
- merge/deploy authority 是否明确？
- production 怎么验证？

---

# 81. 本章结论

Agentic Software Engineering 不是：

```text
prompt better
→ model smarter
→ software solved
```

更接近：

```text
accurate system model
        ↓
explicit delegation contract
        ↓
scoped capability / permission
        ↓
agent exploration + implementation bandwidth
        ↓
claim-oriented evidence
        ↓
independent review
        ↓
explicit authority decision
        ↓
controlled rollout + production evidence
```

如果只能记住一句：

> **不要问“Agent 能不能完成这个任务”；先问“我们是否已经把完成这个任务所需的语义、权限、证据和停止条件组织成一个它可以安全执行的工程系统”。**

这也是整门课从 M00 一路走到这里的原因。
