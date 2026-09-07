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
| [06](modules/06-working-with-legacy-code.md) | 阅读和接管 Legacy Code | 在 spec/test 不足时，怎样先 characterize、打开最小 seam，再安全变化？ |
| [07](modules/07-concurrency-lifecycle-failure.md) | Concurrency、Lifecycle 与 Failure | race、retry、crash、restart 下哪些不变量最容易被破坏？ |
| [08](modules/08-dependency-compatibility-migration.md) | Dependency、Compatibility 与 Migration | 怎样让旧 caller / 旧数据 / 旧协议穿过新旧版本共存期而不被破坏？ |
| [09](modules/09-architecture-boundaries-dataflow-failure-domains.md) | Architecture：边界、数据流与故障域 | 什么值得上升到系统级设计？哪些决定会跨模块放大 authority / failure / evolution consequence？ |
| [10](modules/10-code-review-change-engineering.md) | Code Review 与 Change Engineering | 怎样把一次 PR 当作 bounded engineering argument 独立验证，而不是把 CI green 当 approval？ |
| [11](modules/11-production-observability-reliability.md) | Production、Observability 与 Reliability | 系统上线后，怎样从 user contract 设计 SLI/SLO、telemetry、alert 与 overload evidence，而不是只堆 metrics？ |
| [12](modules/12-agentic-software-engineering.md) | Agentic Software Engineering | 怎样把 system model、authority、evidence、stop/escalation 与 independent review 组织成 Agent 可安全执行的工作系统？ |
| [13](modules/13-capstone-change-engineering.md) | Capstone：完整 Change Engineering | 在一个持续演化的真实风格系统里，同时完成 issue review、system model、migration、Agent-assisted implementation、evidence、independent review 与 rollout 判断。 |

详细教学设计见 [`COURSE_DESIGN.md`](COURSE_DESIGN.md)。

### Extensions：按需深入，不增加新的主线模块

传统 Software Engineering 里有些问题没有必要重新占一个 M14/M15，却仍然会改变真实工程判断。例如 requirement 并不是从天上掉下来的；代码版本也不等于完整 release identity；Agent 写代码变快以后，review capacity、security boundary 和 professional responsibility 也不会消失。

这些内容收在 [`extensions/`](extensions/index.md) 中，按需要阅读，不进入 M00–M13 的线性学习顺序。当前旁支包括 Requirements/Stakeholders、Configuration/Baseline/Release、Risk/Estimation/Economics、Process/Feedback/Team Coordination、Software Quality、Security Engineering、Professional Practice，以及 Models/Notation/UML。

为什么只补这些、而没有再写一套传统 Architecture/Testing/Maintenance/Operations，见 [`traditional-se-gap-map.md`](reading-notes/traditional-se-gap-map.md)；新增 normative frames 的来源、实际教学材料核查，以及哪些表述属于 course synthesis，见 [`extensions-source-audit.md`](reading-notes/extensions-source-audit.md)。

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

这些内容有些会出现，但只会在它们能帮助回答真实工程问题时出现；其中仍然值得系统了解、但不应占用主线的部分收在 [`Extensions`](extensions/index.md) 中。

---

## 当前状态

M00–M13 的完整主线现已形成：

- M00–M13 全部已有自包含中文讲义；
- `MATERIALS_REVIEW.md` 记录教材级审计；`reading-notes/m02-source-audit.md` 到 `reading-notes/m13-source-audit.md` 记录逐模块 source audit；M13 明确不新增“Capstone 权威教材”，只组合前面已经实际审计的一手材料；
- [`reading-notes/traditional-se-gap-map.md`](reading-notes/traditional-se-gap-map.md) 对 SWEBOK v4.0a 的 18 个 Knowledge Areas 逐项判断“已覆盖 / 部分覆盖 / 真缺口 / 低优先级”，并据此只新增 8 个可选 [`extensions/`](extensions/index.md)；[`reading-notes/extensions-source-audit.md`](reading-notes/extensions-source-audit.md) 记录这些旁支实际检查过的当前标准、课程和一手实践资料及其取舍；
- [`labs/13-capstone.md`](labs/13-capstone.md) 提供最终综合实验；[`labs/taskforge/capstone-starter/`](labs/taskforge/capstone-starter/) 是独立的 SQLite + remote-worker starting point，包含 old API、schema v1、background maintenance、known claim race、legacy finish quirk 与 flawed feature request；
- `capstone_baseline_probe.py` 可确定性复现 double claim 与 stale v1 finish；baseline tests 仍是 `6 passed`，用于证明 green tests 不等于完整 correctness argument；
- human decision pack 将错误的 arbitrary-command exactly-once 要求收敛为 **v2 attempt fencing** + opt-in `automatic_at_least_once`；legacy/manual `operator_requeue()` 的 unfenced stale-completion risk 明确保留为 migration residual risk，同时 mixed v1/v2 claim 必须共享 queued-row single-winner invariant，并定义 rollout gate 与 rollback boundary；
- [`case-studies/m13/instructor-analysis.md`](case-studies/m13/instructor-analysis.md) 记录 historical reference validation：临时 solution 共 `14 passed`，其中包含 v1-v1 claim fix、frozen-v1 Expand compatibility 与 post-v2 old-server rollback counterexample，但没有覆盖当前 clarified contract 要求的 v1-v2 concurrent claim arbitration；因此这组结果不是学生 candidate 或当前完整 contract 的 acceptance oracle。

课程主线至此完成。后续扩展应优先增加新的真实 case study、review exercise 或替代 capstone，而不是继续堆原则名词。
