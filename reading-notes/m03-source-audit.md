---
id: source-M03
type: source_audit
visibility: student
related: [M03]
---
# M03 Source Audit — Testing as Executable Evidence

> 审计/复核日期：**2026-09-06**。

> 本文件记录 M03 真正采用的原始材料、实际检查内容、可支持的 claim，以及我们明确不从来源中过度外推的部分。
>
> 原则：**“testing best practice” 不是证据。只有看过正文、例子、作业或工具实际语义之后，才决定是否纳入课程。**

---

## 0. 本章为什么需要单独审计

Testing 特别容易退化成口号集合：

- “80% coverage 就够了”；
- “只写 unit tests”；
- “一定要 TDD”；
- “mock 一切 dependency”；
- “永远不要 mock”；
- “遵守 test pyramid”；
- “property-based testing 比 example-based 高级”；
- “mutation score 越高越好”。

这些句子的问题不是一定错误，而是它们把 **risk、contract、fidelity、cost、feedback speed** 等上下文压扁成一个规则。

M03 因此只保留能帮助学生回答以下问题的材料：

1. 一个 test 到底提出了什么可执行 claim？
2. oracle 从哪里来？
3. 什么输入/状态/失败路径尚未被覆盖？
4. 测试为什么会在“正确的变化”后继续通过，而在“错误的变化”后失败？
5. 哪些 test double / integration boundary 会制造 fidelity gap？
6. 怎样判断测试只是执行代码，还是确实验证 observable behavior？
7. 怎样验证“这组测试真的有发现 bug 的能力”？

---

## 1. MIT 6.102 — Reading 2: Testing

**状态：主干采用（系统测试设计的基础层）**

原文：

- [1. MIT 6.102 — Reading 2: Testing — source 1](https://web.mit.edu/6.102/www/sp26/classes/02-testing/)

另外检查了 2025 Project Testing：

- [1. MIT 6.102 — Reading 2: Testing — source 2](https://web.mit.edu/6.102/www/sp25/project/starb/testing.html)

### 实际检查了什么

阅读了 Testing reading 中以下部分：

- validation；
- why software testing is hard；
- test-first programming；
- systematic testing；
- correctness / thoroughness / size；
- partitioning input space；
- boundary values；
- black-box / glass-box testing；
- code coverage；
- unit testing；
- regression testing；
- property-based testing / fuzzing 的简要介绍；
- summary 中 testing 与 “safe from bugs / easy to understand / ready for change” 的联系。

还检查了项目级 automated testing 页面，确认课程的项目真的通过 push → build server → compile → test 的持续反馈使用自动测试，而不是只在 lecture 中讨论。

### 真正值得吸收的地方

#### 1. 把 test suite 质量拆成多个维度

6.102 不把“测试多”视为好，而要求区分：

- **correctness**：合法实现不应被测试错误拒绝；
- **thoroughness**：能区分更多有 bug 的实现；
- **size**：用更少、更有代表性的 case 获得足够区分能力。

这里最值得移植的不是三个术语本身，而是一个思维转换：

> test suite 的目标不是堆 example，而是尽量高效地区分“允许的实现”和“我们想排除的实现”。

这非常适合 Agent 时代，因为 Agent 很容易生成 100 个形式相似的测试，但数量不意味着增加 semantic discrimination。

#### 2. systematic partitioning 比拍脑袋 example 更可迁移

Reading 要求根据 specification 对 input space 做 partition，并特别检查 boundaries。

课程采用这个方法，但会把 “input” 扩展为：

- 参数；
- object/system state；
- lifecycle state；
- dependency behavior；
- failure mode；
- concurrency interleaving（M07 深入）；
- version / compatibility state（M08 深入）。

也就是说，我们不是只教数值函数的 `x < 0 / x = 0 / x > 0`。

#### 3. testing 被放在 validation 的更大框架里

MIT 明确把 testing 与 formal verification、code review 并列为 validation 方法。

这支持本课程一个关键主张：

> tests 是 correctness argument 的一种 evidence，不是 correctness 本身。

#### 4. 正确测试只依赖 spec，因此 implementation 可以变化

Reading summary 明确把 ready for change 与“tests only depend on behavior in the spec”联系起来。

这与 M02 的 information hiding 直接连起来：

- production code 对 implementation detail 泄漏 → client coupling；
- test 对 implementation detail 泄漏 → test brittleness。

### 局限与我们不会照搬的地方

#### 1. “test-first programming”不升级为宗教

6.102 教 test-first 是合理的 construction discipline，但本课程不要求所有代码都严格 TDD。

原因：

- legacy takeover 时往往先有实现；
- debugging unknown behavior 时可能先 characterization；
- research prototype 早期 contract 可能尚未稳定；
- concurrency / distributed failure 的 useful oracle 有时必须在理解系统后才建立。

我们保留的原则是：

> **在实现一个已定义行为之前，尽量先让 expected behavior 和 validation strategy 清楚。**

这比“必须先写测试文件”更本质。

#### 2. statement/code coverage 只是补充视角

MIT 讨论 coverage 有教学价值，但 M03 会进一步用 Google 的材料校正“coverage = quality”的误读。

#### 3. randomized testing 不是 property-based testing 的全部

MIT 的篇幅较短。M03 的 property-based 部分会用 Hypothesis 官方资料补充 domain/property/shrinking 的实际工作方式。

---

## 2. Software Engineering at Google — Testing Overview

**状态：主干采用（测试与长期变化、规模、coverage、test portfolio）**

原文：

- [2. Software Engineering at Google — Testing Overview](https://abseil.io/resources/swe-book/html/ch11.html)

### 实际检查了什么

重点读了：

- Why Do We Write Tests?；
- Test Size；
- Test Scope；
- test pyramid 的上下文与比例说明；
- Testing for Failure；
- A Note on Code Coverage；
- flaky tests / large test suite cost；
- The Limits of Automated Testing。

### 真正值得吸收的地方

#### 1. 测试的重要目的之一是“允许变化”

正文不是只说 catch bugs，而是把 automated testing 与 refactoring、redesign、快速变化直接联系。

这与全课的 “software engineering = controlled change” 主线高度一致。

#### 2. test size 与 test scope 是两个维度

这是比简单 “unit / integration / e2e” 三分法更精确的模型：

- **size**：运行需要的资源、进程、机器、I/O 等；
- **scope**：这个 test 想验证多大范围的行为。

一个 broad-scope test 可以仍然很 small；一个 narrow-scope test 也可能因为真实 browser/device 而 medium。

M03 会采用这个二维模型。

#### 3. coverage 只说明代码被执行，不说明结果被验证

Google 对 coverage 的批评非常具体：

- line executed ≠ line did something useful；
- metric 变成 target 后会反向塑造行为；
- 单个 percentage 无法回答 “我们是否测试了重要 behaviors”。

因此 M03 会把 coverage 放在：

> **gap detector / question generator**

而不是 quality score。

#### 4. portfolio 应根据 local architecture/risk 决定

正文给出大约 80/15/5 的经验比例，但同时明确说明每个团队的 mix 会不同，并要求根据 architectural / organizational reality 调整。

所以本课程不会考试：

> “unit/integration/e2e 的正确比例是多少？”

正确问题是：

> “哪些风险只有跨 boundary 的高-fidelity test 才看得到？为了这些风险，我们愿意支付多少运行成本？”

#### 5. 自动测试有边界

正文明确保留 human judgment / exploratory testing 的空间。

这对 Agent 时代尤其重要：自动生成更多测试并不会自动覆盖“我们甚至没有意识到需要问的问题”。

### 局限

Google 的经验来自极大规模 monorepo、统一 build/test infrastructure。它的 size policy 和比例不能无条件复制到小型开源项目。

课程吸收 reasoning，不复制组织政策。

---

## 3. Software Engineering at Google — Unit Testing

**状态：主干采用（test maintainability / brittleness / behavior-oriented testing）**

原文：

- [3. Software Engineering at Google — Unit Testing](https://abseil.io/resources/swe-book/html/ch12.html)

### 实际检查了什么

重点读了：

- Importance of Maintainability；
- Preventing Brittle Tests；
- Test via Public APIs；
- Test State, Not Interactions；
- complete / concise tests；
- Test Behaviors, Not Methods；
- test naming / structure；
- DAMP, Not DRY。

### 真正值得吸收的地方

#### 1. 测试本身是长期维护资产

一个 test 若在行为不变的 refactoring 后频繁需要更新，它就把 implementation structure 错误升级成了 contract。

这提供了一个非常强的 review question：

> **这个测试失败时，真实 user/client 是否也应该感知到 breakage？**

如果答案总是“不”，测试很可能绑错了边界。

#### 2. public API 是 semantic boundary，不等于语言 `public`

正文明确指出 unit scope 与 public API 的定义并不等于 language visibility。

M03 会沿用 M02 的 boundary 语言：

- 哪些 API 是这个 unit 对外承诺？
- 哪些只是内部 decomposition？

测试应尽量从真正的 client boundary 观察行为。

#### 3. behavior ≠ method

正文明确指出一个 method 可以实现多个 behavior，一个 behavior 也可能跨多个 method。

所以：

```text
production method → corresponding test method
```

不是合理的默认结构。

课程要求先列 behavior table，再组织 tests。

#### 4. state vs interaction 是 “what vs how” 的典型冲突

正文展示了 interaction test 可能同时：

- 漏掉最终状态错误；
- 又因无害的内部调用变化而失败。

M03 采用 “prefer observable state/outcome” 的方向，但不会把 interaction testing 判死刑。对于真正的 external side effect / protocol obligation，interaction 本身可能就是 observable contract。

#### 5. test code 可以有不同于 production code 的 duplication trade-off

DAMP 的价值不在缩写，而在 reasoning：测试需要让 reader 不跳很多层 helper 就能看到 scenario 中真正重要的信息。

课程不会要求“test 永远不 DRY”；只会问 abstraction 是否隐藏了 test 的意图。

### 局限

章节有很强 Google style，但大多数 reasoning 与规模无关。

“test state, not interactions”不能无条件用于：

- 发邮件/扣款/写审计日志等 side effect；
- protocol sequencing 本身就是 contract；
- 对外 RPC 是否发出就是 desired observable effect。

这些情形应测试真正的 external interaction contract，而不是内部 helper choreography。

---

## 4. Software Engineering at Google — Test Doubles

**状态：选择性主干采用（fidelity 与 doubles 的代价）**

原文：

- [4. Software Engineering at Google — Test Doubles](https://abseil.io/resources/swe-book/html/ch13.html)

### 实际检查了什么

重点读了：

- testability；
- applicability；
- fidelity；
- historical overuse of mocking frameworks；
- real implementations；
- fake / stub / interaction testing。

### 真正值得吸收的地方

#### 1. double 是速度/控制能力与 fidelity 的交换

它不是 “unit testing 标配”。

如果 fake/stub 与真实 dependency 的 behavior contract 不一致，你得到的是：

> 在一个不存在的世界里测试通过。

#### 2. mocking framework 让 overspecification 变得太容易

Google 的经验不是简单“mock bad”，而是：高度隔离的 interaction tests 曾经容易写，却长期 brittle、维护成本高、实际找 bug 价值低。

这非常适合 Agent 时代：Agent 特别容易为“让测试跑得快”而 mock 掉所有真正危险的 boundary。

#### 3. failure injection 是 double 的高价值用途

当真实 failure 很难稳定制造时，一个受控 dependency double 可以让：

- timeout；
- permission error；
- partial response；
- retryable/non-retryable failure

变成确定的测试输入。

M07 会进一步使用这个能力。

### 局限

不把 fake / stub / mock 名词辨析当考试重点。重点是：

- 这个 substitute 与真实 dependency 差在哪里？
- 差异是否会吞掉本次测试关心的风险？
- 是否需要另一层更高 fidelity 的 test 补洞？

---

## 5. Software Engineering at Google — Larger Testing

**状态：主干采用（risk / fidelity / integration gaps）**

原文：

- [5. Software Engineering at Google — Larger Testing](https://abseil.io/resources/swe-book/html/ch14.html)

### 实际检查了什么

重点读了：

- What Are Larger Tests?；
- Fidelity；
- Common Gaps in Unit Tests；
- unfaithful doubles；
- structure of a large test；
- test data；
- verification；
- larger testing 的 cost / nondeterminism。

### 真正值得吸收的地方

#### 1. larger test 的理由不是“更真实所以更高级”

它们用于覆盖 narrow tests 无法充分缓解的风险，尤其：

- component contract mismatch；
- configuration；
- process/network boundary；
- unfaithful doubles；
- emergent behavior。

#### 2. fidelity 是连续变量，不是 unit/e2e 二元选择

课程会要求学生针对 risk 选择 **足够的 fidelity**，而不是自动选择最大范围。

#### 3. larger tests 同样应尽可能小

如果只需要验证 A↔B contract，不需要每次拉起 A→B→C→D→E 全链路。

这与 architecture 里的 boundary thinking 是同一件事。

### 局限

这一章涉及很多 Google-specific infrastructure；M03 只抽出 general reasoning。部署、chaos、production probe 等内容留到 M11。

---

## 6. Hypothesis 官方文档

**状态：选择性采用（property-based testing）**

官方文档：

- [6. Hypothesis 官方文档 — source 1](https://hypothesis.readthedocs.io/en/latest/)
- [6. Hypothesis 官方文档 — source 2](https://hypothesis.readthedocs.io/en/latest/tutorial/introduction.html)

### 实际检查了什么

检查了：

- property-based testing 的基本 API/示例；
- strategy 定义 input domain；
- edge cases；
- failing example shrinking；
- 官方 “When to use Hypothesis and property-based testing” 建议；
- round-trip properties；
- reference implementation equivalence；
- invariant-like properties。

### 为什么采用

Example-based testing 最大的问题之一是：

> 你通常只测试了自己想得到的输入。

Property-based testing 把工作重心改成：

1. 定义 input domain；
2. 定义对整个 domain 应成立的 property；
3. 让工具搜索反例；
4. 找到后 shrink 到更容易理解的失败 example。

这与 M01 的 invariant/spec 思维直接相连。

### 不过度宣传

官方文档自己也明确说 property-based testing 是 unit testing 的强力补充，不总是 replacement。

它不能解决：

- 你写错 property；
- 你漏掉真正重要的 property；
- generator domain 排除了危险状态；
- external-system fidelity gap。

因此本课程把它称为：

> **counterexample search engine**

而不是“自动证明”。

---

## 7. mutmut 官方文档

**状态：工具选读；概念采用，主实验不依赖它**

官方文档：

- [7. mutmut 官方文档](https://mutmut.readthedocs.io/en/latest/)

### 实际检查了什么

检查了：

- mutation testing 基本 workflow；
- mutmut 如何生成 subtle mutations；
- surviving mutant → 写 test → retest 的工作流；
- example mutations（如 `<` → `<=`、integer literal change）；
- fork/平台等工具限制。

### 为什么概念值得学

Coverage 问的是：

> “测试跑到这里了吗？”

Mutation testing 问的是更接近我们真正关心的：

> “如果这里出现一个合理的小 bug，测试会不会叫？”

它把 test suite 的 **fault discrimination ability** 变得可操作。

### 为什么不把 mutmut 变成课程依赖

- tool/version/platform 会产生 incidental complexity；
- 并非所有 surviving mutant 都代表 meaningful missing test；
- equivalent mutant 会污染 score；
- chasing mutation percentage 会复制 coverage metric 的问题。

所以 TaskForge M03 使用 **少量人工设计、语义明确的 mutants** 做主实验；mutmut 仅作为学生想继续探索时的工具。

---

## 8. 本章刻意不采用为“权威规则”的材料/说法

### 8.1 Test Pyramid 比例

会介绍历史直觉，但不把任何固定比例作为 correctness criterion。

Google 自己给比例时也明确标注是 rough guideline 且团队 mix 不同。

本课程统一用：

```text
risk → desired evidence → minimum sufficient fidelity → feedback cost
```

来设计 portfolio。

### 8.2 “100% coverage”

不作为课程目标。

可以有 100% line coverage 但几乎没有有意义的 oracle。

### 8.3 “Mock nothing” / “Mock everything”

都不采用。

讨论 fidelity、control、determinism、cost。

### 8.4 Strict TDD

作为一种 useful discipline 讨论，不作为 universal workflow。

### 8.5 Snapshot/Golden testing

M03 会提到适用场景与 brittleness 风险，但本轮没有选一份足够好的单一材料作为权威来源，因此不建立“必须/禁止 snapshot”规则。

---

## 9. M03 最终综合出的模型

来源不是拼书，而是互相补洞：

```text
MIT 6.102
    ↓
systematic input partition / boundary / test-suite discrimination

Google Testing Overview
    ↓
change enablement / size vs scope / coverage limits / portfolio

Google Unit Testing
    ↓
behavior boundary / maintainability / brittleness / public API

Google Test Doubles + Larger Testing
    ↓
fidelity / isolation trade-off / boundary risk

Hypothesis
    ↓
property → generated cases → counterexample search

Mutation testing
    ↓
small plausible bug → does the suite actually notice?
```

本课程再补一个 Agent-specific layer：

```text
spec / risk model
    ↓
ask Agent for tests
    ↓
check oracle independence
    ↓
check behavior partitions
    ↓
run meaningful mutants
    ↓
force fail-before / pass-after evidence
    ↓
independent human or second-Agent review
```

最重要的结论不是“多写测试”，而是：

> **测试是一组可执行的工程声明。好的测试让错误的未来变化更难悄悄通过，同时尽量不阻碍正确的未来变化。**
