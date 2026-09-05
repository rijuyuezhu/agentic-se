# 软件工程：控制复杂度、设计变化、驾驭 Agent

> 一门面向 CS 本科生 / 研究生的中文自学课程。
>
> 目标不是应付《软件工程》考试，也不是背 UML、Scrum、SOLID 或“最佳实践”；目标是获得一种可以迁移到真实代码库、代码 review 和 coding agent 协作中的工程判断力。

## 课程的核心问题

软件工程最根本的问题不是“如何写出程序”，而是：

> **当软件持续变大、持续变化、由多人或多个 Agent 并行修改时，怎样控制复杂度，使系统仍然可以被理解、验证和安全地修改？**

本课程围绕四个对象展开：

1. **Boundary（边界）**：系统在哪里切开，哪些细节必须被隐藏？
2. **Contract（契约）**：调用者和实现者分别可以假设什么、必须保证什么？
3. **Invariant（不变量）**：哪些性质在所有合法状态和变更中必须成立？
4. **Change（变化）**：一个需求变化怎样被局部化、验证、review、迁移和上线？

Agent 时代把代码生成成本大幅降低，但也放大了一个新问题：**如果人不能建立正确的 system model，就无法判断 Agent 生成的大量代码是否真的应该存在、改对了地方、没有破坏隐含契约。**

因此课程最终希望训练的不是“自己每天能写多少行代码”，而是：

> **建立准确的软件 mental model，并把它转化为人或 Agent 可执行、可验证的变更约束。**

---

## 你学完后应该能做什么

完成课程后，你应该能够：

- 面对一个陌生代码库，识别它的主要模块、状态拥有者、依赖方向和 failure boundary，而不是只会逐文件阅读。
- 为一个函数、模块、服务或变更写出清晰的 specification，包括 precondition、postcondition、side effect、error semantics 和 compatibility boundary。
- 区分“代码能跑”和“系统 contract 被满足”；知道一个测试实际上证明了什么、没有证明什么。
- 识别 change amplification、information leakage、shallow abstraction、duplicated authority、temporal coupling、hidden dependency 等设计问题。
- 在重构时保持行为不变，在加功能时区分新行为与已有行为，在 legacy code 中先建立可观察的 safety net。
- 分析并发、lifecycle、retry、crash、partial failure、persistence 等条件下的不变量。
- 设计可逐步迁移、可回滚、可兼容的 change，而不是把“大重写”当成唯一方案。
- 做有技术含量的 code review：从设计、契约、failure mode、测试语义和长期代码健康出发，而不沉迷 style nit。
- 把一个真实需求写成高质量 Agent task：明确目标、non-goal、受影响边界、必须保持的不变量、验证证据和 review checklist。
- 对 Agent 生成的 patch 做独立审查，而不是把“测试绿了”当作正确性的充分条件。

---

## 自包含原则

这门课会引用 MIT、Stanford、Google 和经典书籍，但 **外部材料不是理解课程的前提**。

每个模块最终都应包含：

- 中文主讲义；
- 关键概念与反例；
- 一组可操作的 design/review questions；
- 一个小练习；
- 一个贯穿实验；
- 可选的原始资料阅读；
- “对 Agent 怎么用”一节。

外部资料的作用是：

1. 提供更丰富的原始案例；
2. 允许读者检查本课程是否歪曲来源；
3. 展示不同工程流派之间真实存在的分歧。

我们不会因为一本书“有名”就把它列为必读。每个材料都要经过内容审计，见 [`MATERIALS_REVIEW.md`](MATERIALS_REVIEW.md)。

---

## 课程主线

建议按 12~14 周学习，也可以自定节奏。

| 模块 | 主题 | 关键问题 |
|---|---|---|
| [00](modules/00-what-is-software-engineering.md) | 软件工程到底在优化什么 | 为什么 complexity 和 change 比 LOC 更值得关注？ |
| [01](modules/01-specification-contract-invariant.md) | Specification、Contract 与 Invariant | 什么是“正确”？谁对什么负责？ |
| [02](modules/02-abstraction-information-hiding-state-ownership.md) | Abstraction、Information Hiding 与 State Ownership | 系统应该在哪里切开？谁拥有状态？ |
| [03](modules/03-testing-as-executable-evidence.md) | Testing 作为可执行证据 | 测试究竟证明什么？怎样避免 brittle tests？ |
| [04](modules/04-api-errors-boundary-design.md) | API、错误与边界设计 | 怎样让边界吸收复杂度，并把 retry / error 变成明确 contract？ |
| [05](modules/05-refactoring-evolutionary-design.md) | Refactoring 与 Evolutionary Design | 如何改变设计但保持行为？什么时候先设计、什么时候后重构？ |
| 06 | 阅读和接管 Legacy Code | 不敢改的代码怎样建立反馈回路？什么是 seam？ |
| 07 | Concurrency、Lifecycle 与 Failure | race、retry、crash、restart 下哪些不变量最容易被破坏？ |
| 08 | Dependency、Compatibility 与 Migration | 为什么一个看似局部的 API 改动会伤到未知用户？ |
| 09 | Architecture：边界、数据流与故障域 | 什么值得上升到系统级设计？哪些决定以后很难改？ |
| 10 | Code Review 与 Change Engineering | 怎样把一次 PR 当作“系统演化的最小单位”审查？ |
| 11 | Production、Observability 与 Reliability | 系统在现实世界坏掉时，设计是否仍然成立？ |
| 12 | Agentic Software Engineering | 如何给 Agent 任务、限制搜索空间、要求证据、独立验收？ |
| 13 | Capstone | 在一个持续演化的真实风格系统里完成多轮变更与 review |

详细教学设计见 [`COURSE_DESIGN.md`](COURSE_DESIGN.md)。

---

## 贯穿实验：TaskForge

课程会配一个小型但“故意接近真实软件”的服务：**TaskForge**。

它不是算法题，而是一个会不断演化的后台任务系统：

- CLI / API 提交任务；
- daemon 持久化任务状态；
- worker 异步执行；
- 支持取消、重试、重启恢复；
- 后续加入 schema migration、remote worker、compatibility、observability；
- 初始版本会故意包含 global state、模糊 ownership、brittle tests、隐式错误语义等设计缺陷。

每个模块都会让它发生一次“真实的软件变化”。你要做的不只是实现功能，而是：

1. 先画出当前 system model；
2. 写 change specification；
3. 明确必须保持的 invariants；
4. 决定测试和观察证据；
5. 再让自己或 Agent 实现；
6. 最后做独立 review。

这样把课程从“读设计原则”变成“反复练设计判断”。

---

## 课程不是这些东西

我们不会把以下内容当成主线：

- UML 图形记忆；
- 瀑布模型阶段背诵；
- Scrum 角色与会议名词；
- Design Pattern 名称收集；
- SOLID 五个缩写背诵；
- “函数必须少于 N 行”之类脱离语境的规则；
- 以 coverage 百分比代替测试质量；
- 以“CI 通过”代替 correctness argument；
- 以“Agent 写出来了”代替 engineering judgment。

这些内容有些会出现，但只会在它们能帮助回答真实工程问题时出现。

---

## 当前状态

前六个核心模块已经形成连续学习链：

- M00、M01、M02、M03、M04、M05 已有自包含中文讲义；
- `MATERIALS_REVIEW.md` 记录教材级审计；
- `reading-notes/m02-source-audit.md` 到 `reading-notes/m05-source-audit.md` 记录逐模块 source audit；
- [`labs/taskforge/`](labs/taskforge/) 已有可运行的 v0 baseline，实际验证 `6 passed`；
- [`labs/02-state-ownership.md`](labs/02-state-ownership.md) 已把 M02 概念转成 system-model → design-it-twice → implementation → evidence → Agent comparison → independent review 的完整实验；
- [`case-studies/m02/baseline-analysis.md`](case-studies/m02/baseline-analysis.md) 提供 instructor reference（有 spoiler）。
- [`labs/03-testing-evidence.md`](labs/03-testing-evidence.md) 从同一 baseline 出发，加入 contract audit、behavior partition、manual mutation probe、fail-before/pass-after 与 Agent test review；
- `labs/taskforge/tools/mutation_probe.py` 已实际验证 baseline 为 `3 killed / 3 survived`，补 3 个 behavior-oriented tests 后为 `6 killed / 0 survived`；
- [`case-studies/m03/instructor-analysis.md`](case-studies/m03/instructor-analysis.md) 记录 M03 的 instructor reference 与实际 red→green 验证。
- [`labs/04-api-error-boundary.md`](labs/04-api-error-boundary.md) 引入 external-style boundary、error taxonomy、no-effect guarantee、request identity 与 idempotent submit；
- `labs/taskforge/tools/m04_boundary_probe.py` 已实际验证 starter 的语义缺口：blank command 被接受、`KeyError` 穿透、cancel failure 被 `False` collapse、same payload 默认仍代表 distinct requests；
- [`case-studies/m04/instructor-analysis.md`](case-studies/m04/instructor-analysis.md) 记录 reference boundary；临时副本已实际验证原 6 个 core tests + 12 个 M04 contract tests，共 `18 passed`。
- [`labs/05-refactoring-evolutionary-design.md`](labs/05-refactoring-evolutionary-design.md) 用 dashboard 的 JSON feature 训练 behavior inventory、Two Hats、preparatory refactoring、semantic checkpoints 与 change topology；
- `labs/taskforge/tools/m05_behavior_probe.py` 锁定三个现有 text-dashboard 场景，structural phase 必须 byte-for-byte 保持；
- [`case-studies/m05/instructor-analysis.md`](case-studies/m05/instructor-analysis.md) 记录一条实际跑通的 `structural-only → verify → JSON feature` reference sequence。

下一阶段进入 M06 Legacy Code：从“已经有足够 evidence 才能安全 refactor”转向更困难的现实问题——**如果现有代码没有可靠测试、dependency 很难切开、你甚至不知道旧行为是不是 contract，怎样先建立 feedback，再做受控变化。**
