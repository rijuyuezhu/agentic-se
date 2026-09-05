# 课程设计说明

## 1. 课程定位

这是一门面向已经会编程、学过数据结构与基本系统课程的 CS 学生的 **Software Engineering / Software Design 实战课**。

它不试图覆盖软件工程学科的全部内容，而是优先选择最能提升以下能力的主题：

- 理解复杂代码库；
- 设计可演化的软件边界；
- 为修改建立 correctness argument；
- review 真实 patch；
- 在 Agent 生成代码越来越便宜的环境中，仍然保有人类对系统语义和长期结构的控制。

### 目标学生

理想读者：

- CS 本科高年级或研究生；
- 已经能独立完成数千行以内的程序；
- 知道 Git、基本测试和一种主流语言；
- 希望从“会实现”提升到“会设计、会修改、会 review”。

### 不要求

- 不要求有企业实习经验；
- 不要求学过传统 Software Engineering 课程；
- 不要求熟悉某个 Web 框架；
- 不要求先读任何外部教材。

---

## 2. 一个更精确的课程目标

课程把软件工程能力拆成六个可观察能力，而不是抽象地说“培养工程思维”。

### A. System Modeling

给你一个陌生 repo，你能在有限时间内回答：

- 程序从哪里进入？
- 主要数据和控制流怎么走？
- 哪些模块持有 authoritative state？
- 哪些 API 是内部边界，哪些是外部 contract？
- 哪些 failure 会跨边界传播？
- 哪些地方修改后影响面最大？

**验收方式**：要求学生画 system map，并用具体调用链和代码位置证明。

### B. Contract Reasoning

给你一个函数、模块、RPC 或 daemon lifecycle，你能明确：

- precondition；
- postcondition；
- allowed side effects；
- error behavior；
- concurrency semantics；
- compatibility promises；
- invariants。

**验收方式**：给出 intentionally ambiguous implementation，让学生先写 spec，再设计测试。

### C. Design Judgment

给你两个都“能跑”的设计，你能从以下角度做 argument：

- change amplification；
- cognitive load；
- information leakage；
- dependency direction；
- state ownership；
- failure localization；
- reversibility；
- testability；
- compatibility cost。

**验收方式**：不是问“哪个模式名正确”，而是要求写 trade-off memo。

### D. Safe Change

面对现有系统增加功能或修 bug，你能：

1. 先理解现状；
2. 找到 observable behavior；
3. 建立 regression safety net；
4. 拆出结构性修改和行为修改；
5. 设计逐步迁移；
6. 验证旧行为和新行为。

**验收方式**：对 legacy fixture 完成一个不能一次重写的功能变更。

### E. Review

面对一个 PR，你不会只盯 diff，而会主动检查：

- issue 自身是否合理；
- implementation 是否改在正确 abstraction；
- 是否出现第二份 authority；
- 是否引入 hidden dependency；
- failure path 是否闭合；
- tests 是否真的覆盖 contract；
- migration 是否可安全完成；
- 文档和运行时语义是否一致。

**验收方式**：学生必须提交带 severity、evidence、reproduction 的 review。

### F. Agent Orchestration

面对 coding agent，你能把“帮我实现 X”升级成：

- 当前 system model；
- desired behavior；
- non-goals；
- allowed change surface；
- invariants；
- compatibility requirements；
- validation plan；
- review expectations。

并且你能 **不依赖 Agent 自己的总结**，独立检查结果。

**验收方式**：同一任务做两轮：先用模糊 prompt，再用 engineering spec；比较 patch 质量、review 成本和遗漏。

---

## 3. 课程主张：软件工程的核心是“受控变化”

本课程采用下面的工作定义：

> **Software Engineering 是建立、表达和维护软件中的 boundaries、contracts、invariants 与 mental models，从而让复杂系统可以被人或 Agent 安全地持续修改。**

这一定义故意把“change”放在中心。

我们不认为一个设计因为“看起来优雅”就好。更重要的问题是：

- 加一个新功能时需要知道多少东西？
- 一个局部变化会扩散到多少位置？
- 如果调用方误用，哪里会首先暴露问题？
- 系统 crash/retry/restart 后，不变量是否仍成立？
- 三个月后换一个人或 Agent 修改，能否恢复正确 mental model？

---

## 4. 三个反复训练的循环

### 4.1 Understanding Loop

```text
问题/需求
  ↓
定位入口
  ↓
追踪数据流 / 控制流
  ↓
识别 authority / contract / invariant
  ↓
形成 system model
  ↓
用代码与运行证据验证 model
```

禁止只看 README 后猜架构。

### 4.2 Change Loop

```text
现有行为
  ↓
change specification
  ↓
风险与 invariant
  ↓
最小可验证变更
  ↓
测试 / 静态检查 / 运行证据
  ↓
review
  ↓
必要时重构 / 迁移
```

### 4.3 Agent Loop

```text
人建立 system model
  ↓
人定义 task contract
  ↓
Agent 探索 + 实现
  ↓
Agent 给 evidence
  ↓
人独立审查
  ↓
必要时要求修正
```

关键原则：**Agent 可以代替 implementation effort，但不能自动代替 engineering authority。**

---

## 5. 教学结构

每个模块采用相同结构：

1. **为什么这个问题存在**：从 failure case 开始；
2. **核心模型**：给出少量可复用概念；
3. **反例**：展示“看起来合理但会坏”的方案；
4. **真实代码阅读**：短小、可定位；
5. **Design questions**：把概念转成 review checklist；
6. **TaskForge lab**：在贯穿系统中做修改；
7. **Agent transfer**：怎样把本章知识用于指挥 Agent；
8. **可选原始资料**：经过审计的课程/书/文章。

课程不使用“读完一章然后回答定义题”作为主要学习方式。

---

## 6. 模块详细规划

### M00 — 软件工程到底在优化什么

核心：complexity、change amplification、cognitive load、unknown unknowns、programming vs engineering。

作业：
- 对一个 300 行 toy program 和一个 20k+ LOC repo 分别设计同一功能，记录工作差异；
- 写一页“为什么 LOC 不是工程产出的好代理变量”。

Agent 练习：让 Agent 对陌生 repo 直接实现需求；然后禁止实现，只让它建立 system map，比较两轮质量。

### M01 — Specification、Contract、Invariant

核心：pre/postcondition、partial function、side effect、exception/error semantics、representation invariant、protocol invariant。

作业：
- 从实现反推 spec，再找出哪些行为其实只是 implementation accident；
- 为一个状态机写 invariants；
- 区分“测试实现”与“测试 contract”。

Agent 练习：要求 Agent 在写代码前输出 behavior table 和 invariants。

### M02 — Abstraction、Information Hiding、State Ownership

核心：module depth、information leakage、dependency、authority、encapsulation、representation independence。

作业：
- 重构一个“所有模块都能直接改 global state”的系统；
- 比较两个都能工作的 API，分析哪一个把复杂度向调用者泄漏。

Agent 练习：给 Agent 一个“不要新增第二份 state authority”的约束，让它解释每处状态读写的 owner。

### M03 — Testing：可执行证据，不是宗教

核心：test oracle、partition、boundary、property、regression、test pyramid 的适用边界、brittleness、public behavior vs implementation detail。

作业：
- 给一个 100% branch coverage 的测试集找漏掉的 contract；
- 把 mock-heavy test 改成 behavior-oriented test；
- mutation exercise：故意注入 bug 看测试是否失败。

Agent 练习：要求 Agent 先证明“测试在修复前会失败”，再实现修复。

### M04 — API、错误和边界设计

核心：API as contract、make illegal states unrepresentable、error ownership、exception translation、idempotency、temporal coupling。

作业：
- 重新设计一个需要调用者按固定顺序调用 5 个方法的 shallow API；
- 为 retryable/non-retryable error 设计明确语义。

### M05 — Refactoring 与 Evolutionary Design

核心：behavior-preserving transformation、small steps、test safety net、design it twice、reversibility、YAGNI 的正确边界。

作业：
- 将一次“加功能 + 全仓重构”的 PR 拆成可独立验证的 changes；
- 比较 upfront design 与 evolutionary design 的成本。

### M06 — Legacy Code：先建立反馈，再追求漂亮

核心：characterization test、seam、dependency breaking、sensing/separation、change point。

作业：
- 在没有测试的代码中加入一个功能，禁止大重写；
- 先建立 characterization tests，再打开 seam。

### M07 — Concurrency、Lifecycle、Failure

核心：race、atomicity、linearization intuition、ownership under concurrency、cancellation、shutdown、retry、restart recovery、partial failure。

作业：
- 找一个 check-then-act race；
- 为 job lifecycle 画状态机并证明非法转换不可达；
- 设计 crash-after-side-effect 的恢复语义。

### M08 — Dependency、Compatibility、Migration

核心：dependency graph、semantic compatibility、Hyrum's Law、versioning、schema migration、expand-contract、feature flag、rollback。

作业：
- 修改一个被未知 client 使用的 API；
- 设计 zero/low-downtime schema migration；
- 分析为什么 SemVer 不能替代 downstream evidence。

### M09 — Architecture：哪些边界值得上升到系统级

核心：architecture as hard-to-change decisions、process/network/storage boundaries、data ownership、fault domain、control plane/data plane、dependency inversion 的真实用途。

作业：
- 为 TaskForge 从单进程扩展到 remote worker；
- 先列出必须保持的 semantic invariants，再决定进程边界。

### M10 — Code Review 与 Change Engineering

核心：issue → design → patch → evidence → review；small changes；severity；review code health；context beyond diff。

作业：
- review 一个“CI 全绿但有 architecture regression”的 PR；
- review issue 本身；
- 写 blocker/medium/nit 的证据标准。

### M11 — Production、Observability、Reliability

核心：logs/metrics/traces as evidence、SLO intuition、overload、backoff、incident、postmortem、operational simplicity。

作业：
- 注入 timeout/retry storm；
- 设计能区分“慢”“挂”“数据不一致”的 observability；
- 写 blameless but technically precise postmortem。

### M12 — Agentic Software Engineering

核心：context engineering for code、task decomposition、agent boundary、tool authority、verification, independent review、parallel agents and merge conflicts。

作业：
- 同一 feature 比较 vague prompt vs engineering spec；
- 让两个 Agent 分别实现和 review，人工裁决；
- 设计 Agent 不允许跨越的 authority boundary。

### M13 — Capstone

学生收到一个已经运行多个版本的 TaskForge：

- 有旧 API 用户；
- 有 SQLite schema；
- 有后台 job；
- 有 remote worker；
- 有一个已知 race；
- 有一个历史 compatibility quirk；
- 有不完整测试；
- 有一份看似合理但实际存在漏洞的 feature request。

需要完成：

1. issue review；
2. system model；
3. design memo；
4. staged implementation plan；
5. Agent-assisted implementation；
6. tests + runtime evidence；
7. independent PR review；
8. migration/rollback plan；
9. retrospective：哪些判断必须由人做，哪些适合交给 Agent。

---

## 7. 贯穿实验系统 TaskForge 的设计原则

TaskForge 必须“足够真实，但不被框架细节淹没”。

初始建议实现语言：Python 3.12+，理由不是“Python 最工程化”，而是：

- 环境和构建 incidental complexity 低；
- 可以快速制造/观察 concurrency、persistence、API、process boundary 问题；
- type hints / Protocol / dataclass 足以表达大部分课程概念；
- 后续可穿插 TypeScript/Rust 对“哪些 invariant 能交给类型系统”的比较。

技术栈尽量克制：

- stdlib + pytest；
- SQLite；
- asyncio 或线程只在需要时引入；
- 不依赖大型 Web framework；
- CLI + 极薄 HTTP/RPC 层可后续加入。

TaskForge 的“缺陷”要经过设计，不是随便写烂代码。每个缺陷必须服务于一个教学点。

---

## 8. 评价方式

不设置传统闭卷考试。

### 20% — Design Notes

短文题，要求用具体代码支持设计判断。

### 25% — Labs

重点不是最终功能，而是变更过程是否有明确 contract 和 evidence。

### 25% — Reviews

至少 4 次完整 code review，其中一次必须发现测试没覆盖的语义问题，一次必须发现 architecture/ownership 问题。

### 30% — Capstone

评分依据：

- mental model 是否准确；
- change 是否局部化；
- invariant 是否明确；
- migration 是否安全；
- evidence 是否可信；
- review 是否独立；
- Agent 使用是否降低 mechanical work 而没有放弃 engineering authority。

---

## 9. 关于“原则”的态度

课程会讲原则，但每个原则都必须带三个东西：

1. **它解决什么 failure mode？**
2. **它在哪些条件下不适用？**
3. **怎样从代码和运行证据判断它是否真的改善了系统？**

例如不会只说“DRY”。会讨论：

- duplicated knowledge 与 duplicated syntax 的区别；
- 过早抽象如何制造 coupling；
- test code 为什么有时宁愿 DAMP 而不是极端 DRY；
- 两段现在相同、未来会独立演化的逻辑为何不一定应该合并。

同样，也不会把“small functions”“SOLID”“microservices”“TDD”当成无条件正确。

---

## 10. 课程材料选择原则

候选材料进入主线前至少检查：

- 是否能看到足够的真实内容，而不是只看推荐语；
- 是否有具体例子和 reasoning；
- 是否把观点说成适用条件明确的 trade-off，还是无条件口号；
- 是否能训练 transferable skill；
- 是否和课程已有内容重复；
- 是否存在明显时代/语言/组织规模偏置；
- 是否有更好的替代材料。

审计记录见 `MATERIALS_REVIEW.md`。
