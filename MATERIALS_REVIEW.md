# 候选课程 / 教材审计记录

> 目的：防止“因为有名所以推荐”。
>
> 本文件记录我们实际检查了什么、它真正擅长什么、缺什么，以及最终如何使用。这里的结论是课程设计判断，不是对作者或作品的总排名。

## 审计标准

每个材料至少从以下角度检查：

1. **内容证据**：实际目录、章节正文、讲义、作业、review rubric 是否可见？
2. **核心问题匹配度**：是否真的讨论 complexity/change/contracts/invariants/design/review，而非主要讲流程名词？
3. **训练方式**：是否要求学生做 design/review/修改，还是只读概念？
4. **可迁移性**：知识是否绑定某语言、框架、公司规模？
5. **原则严谨度**：是否说明 trade-off 和适用条件？
6. **时代偏置**：旧例子是否会掩盖仍然有效的核心思想？
7. **与 Agent 时代的连接**：是否能转化成 task specification、context boundary、verification 和 independent review？

状态：

- **主干采用**：会直接影响课程主线。
- **选择性采用**：只取明确强项。
- **对照阅读**：用于训练批判性判断，不作为权威。
- **暂不采用**：当前证据不足或性价比不高。

---

# 1. MIT 6.102 — Software Construction

**状态：主干采用（基础层）**

官方课程：
- Spring 2026: https://web.mit.edu/6.102/www/sp26/
- Spring 2025: https://web.mit.edu/6.102/www/sp25/

## 实际检查了什么

检查了 2025/2026 课程总目录、readings、problem sets，以及 AF/RI 和作业要求。

2026 主线包含：

- Static Checking
- Testing
- Code Review
- Specifications
- Designing Specifications
- Abstract Data Types
- Abstraction Functions & Rep Invariants
- Interfaces & Subtyping
- Functional Programming
- Equality
- Recursive Data Types
- Grammars & Parsing
- Debugging
- Concurrency
- Promises
- Mutual Exclusion
- Message-Passing & Networking
- Little Languages

PS 不只是“写对功能”：课程要求写 documented specifications、abstraction function、representation invariant、rep exposure 防护，以及 principled test suite。

AF/RI 阅读还明确使用一个三阶段 recipe：**Spec → Test → Implement**，并强调写测试会反过来给 spec 施加压力。

## 为什么好

### 1. 它把“spec”放在 implementation 前面

这对 Agent 协作尤其重要。Agent 很容易生成实现；真正稀缺的是“实现应该满足什么”。

### 2. ADT / AF / RI 把 abstraction 讲到了可推理层

很多课程说“封装”，但 6.102 会追问：

- concrete representation 如何映射到 abstract value？
- 哪些 concrete states 是合法的？
- 谁负责保持 representation invariant？

这比背“encapsulation is good”强很多。

### 3. 测试、spec、code review 是连续教学，而不是孤立章节

作业有 alpha / code review / beta 的迭代结构，这说明 review 被当成 construction feedback loop，而不是最后检查 style。

## 局限

### 1. 规模上限偏中等

它非常适合“software construction”，但不是完整的长期 software evolution 课程。

不足包括：

- 大型 architecture；
- legacy takeover；
- schema/API migration；
- dependency/version compatibility；
- production observability；
- incident/failure recovery；
- 大规模 change management。

### 2. TypeScript 只是载体，不应成为课程主体

部分内容（如 equality、parsing、specific TS mechanics）对我们的目标优先级较低。

## 本课程怎么用

重点吸收：

- Testing
- Specifications
- Designing Specifications
- ADT
- AF / RI
- Interfaces / Subtyping
- Concurrency / Mutual Exclusion / Message Passing 中与 invariant 相关的部分

不会照搬整门课。

---

# 2. Stanford CS190 — Software Design Studio

**状态：主干采用（设计训练方法）**

官方课程：
- Winter 2021: https://web.stanford.edu/~ouster/cgi-bin/cs190-winter21/

## 实际检查了什么

检查了：

- course introduction；
- class schedule；
- code review 1 / 2 rubric；
- Project 1/2 review discussion；
- Project 2 revision requirement；
- APOSD discussion sessions。

课程不是普通 lecture course，而是 studio：

```text
实现
→ code review
→ 课堂讨论
→ 教师 review meeting
→ revision
→ 再实现 / 再 review
```

学生在 review presentation 中必须说明：

- 每个 class 的 key idea；
- 它隐藏了哪些 information/design decisions；
- 考虑过哪些 alternate designs；
- 一个真实 request/lifecycle 怎样走；
- 哪些地方自己也认为设计弱。

reviewer 则被要求检查：

- information hiding；
- class depth；
- code 是否 obvious；
- persistence / RPC / state machine 的边界；
- concurrency/failure 是否容易推理；
- 新需求加入时多少地方要改。

## 为什么好

### 1. 它真正训练 design judgment

它不要求学生“定义 information hiding”，而是让学生在自己刚写完的系统上被追问：

> 这个类到底隐藏了什么？

这是很强的训练。

### 2. revision 是课程的一等公民

Project 2 明确要求学生基于 review **重做 Project 1 的设计**，并写 changes 文件解释最显著的结构改进。

这非常贴近真实 engineering：第一次设计不是最终答案。

### 3. review 看系统上下文，而非只看 diff/style

尤其 persistence、RPC、state machine 的 rubric 很适合移植成 Agent PR review checklist。

## 局限

### 1. 很大程度上代表 Ousterhout 的设计哲学

“deep classes”“general-purpose modules”等观点有很强解释力，但不能伪装成已被形式证明的普适定律。

### 2. 课程使用 C++ / class decomposition 的语言较多

我们的课程会把概念提升到 module/process/service/state owner，不绑定 OO class。

### 3. correctness 在该 studio 中不是第一评分目标

这是为了聚焦 design 的教学取舍；我们的课程不能照搬，因为 Agent 时代尤其需要把 design judgment 和 correctness evidence 合起来。

## 本课程怎么用

重点吸收它的 **教学方法**：

- design it twice；
- review → revision；
- 让学生解释 hidden information；
- 让 reviewer 从 change cost/failure path 看设计；
- 具体代码案例，而不是模式名。

---

# 3. John Ousterhout — A Philosophy of Software Design, 2nd ed.

**状态：主干采用，但明确视为“设计哲学”，不是圣经**

作者官方页面：
- https://web.stanford.edu/~ouster/cgi-bin/aposd.php
- 2nd edition extract: https://web.stanford.edu/~ouster/cgi-bin/aposd2ndEdExtract.pdf

## 实际检查了什么

检查了作者对第二版变更的说明、公开 extract、CS190 对全书核心概念的讨论。

核心概念包括：

- complexity；
- change amplification；
- cognitive load；
- unknown unknowns；
- deep vs shallow modules；
- information hiding / leakage；
- tactical vs strategic programming；
- define errors out of existence；
- different layer, different abstraction；
- pull complexity downward；
- design it twice；
- comments / obvious code；
- decide what matters。

## 为什么好

它最大的价值是提供了一套 **讨论软件设计的 vocabulary**。

尤其“复杂度不是代码行数，而是修改者需要同时理解多少东西、修改会扩散多远、是否存在 unknown unknowns”非常适合作为全课的统一视角。

## 局限和争议

- 很多原则来自长期系统构建经验，不是 empirical law；
- 对 general-purpose module 的偏好需要防止被学生误解为“提前做万能框架”；
- “deep module”不能退化成简单的 interface-size metric；
- 它与 Robert Martin / Clean Code 在 function size、comments 等问题上有明确分歧。

因此每个原则必须搭配反例和边界条件。

---

# 4. Software Engineering at Google

**状态：主干采用（时间、规模、组织与变更层）**

官方免费全文：
- https://abseil.io/resources/swe-book/html/toc.html

## 实际检查了什么

检查了前言/定义，以及以下章节正文或详细目录：

- Code Review
- Documentation
- Testing Overview
- Unit Testing
- Test Doubles
- Build Systems / dependencies
- Dependency Management
- Large-Scale Changes
- Continuous Integration（目录）

书的核心定义很符合本课程：software engineering 不只是 programming，而是 **programming integrated over time**，也就是组织用来长期构建和维护代码的工具与过程。

## 为什么好

### 1. 它把“time”真正引入软件工程

很多本科课程把设计理解成“交作业前设计一次”；这本书反复讨论：

- API 在几年后怎样演化；
- downstream 用户怎样被影响；
- dependency 如何升级；
- large-scale change 为什么不能靠一次 atomic commit。

### 2. testing 章节不是 coverage 崇拜

它强调测试支持 **change confidence**；unit testing 章节讨论 brittle tests、public API、state vs interactions、DAMP vs DRY。

### 3. dependency management 章节足够诚实

它明确承认该问题很难、没有万能答案，并讨论 SemVer 的信息损失、diamond dependency、Hyrum's Law 和跨组织协调限制。

这比“版本号按 x.y.z 就解决了”严谨得多。

### 4. large-scale changes 非常适合 Agent 时代

其中直接讨论 machine-authored / tool-generated changes 如何依赖测试、sharding、review 和异常检测。这和未来大量 Agent patch 的治理问题高度相关。

## 局限

- Google 的 monorepo、build/test infra、组织规模非常特殊；
- “Google 这样做”不能直接推出小团队也应这样做；
- 人员/组织章节很多，不全部服务于本课程目标。

## 本课程怎么用

选择性吸收：

- Programming Over Time
- Code Review
- Documentation
- Testing Overview / Unit Testing / Test Doubles
- Dependency Management
- Large-Scale Changes
- CI 中与 change feedback 相关部分

---

# 5. Martin Fowler — Refactoring, 2nd ed.

**状态：选择性采用**

作者官方页：
- https://martinfowler.com/books/refactoring.html

## 实际检查了什么

检查了作者对第二版结构的说明、opening chapter 入口、refactoring catalog 的定位。

全书不是“告诉你代码应该长什么样”这么简单，而是强调：

- 在保持 observable behavior 的情况下改变内部结构；
- 通过小步骤降低一次修改的风险；
- testing 是安全重构的重要反馈机制；
- code smells 是“进一步调查”的信号，而不是形式化错误；
- 大量 refactoring 有明确 mechanics。

## 为什么好

它提供的是 **change mechanics**：把“我觉得应该重构”变成一系列可以验证的小步。

Agent 一次改几千行的时代，小步是否仍然重要？仍然重要，因为它降低的是 **reasoning/review risk**，而不只是人敲键盘的成本。

## 局限

- catalog 很大，不值得逐项背；
- 许多 IDE 已自动化机械 refactoring；
- 如果学生只学“smell → pattern”，会退化成模式匹配而不是设计 reasoning。

## 本课程怎么用

只讲：

- behavior preservation；
- small-step transformation；
- tests 与 refactoring 的关系；
- 少量高频 mechanics。

不背 70 个 refactoring 名称。

---

# 6. Michael Feathers — Working Effectively with Legacy Code

**状态：选择性采用，强烈保留核心概念**

可检查目录/章节：
- https://www.oreilly.com/library/view/working-effectively-with/0131177052/toc.html
- Seam Model: https://www.oreilly.com/library/view/working-effectively-with/0131177052/ch04.html

## 实际检查了什么

检查了目录与 Seam Model 章节内容。全书结构不是“整理旧代码”，而是围绕：

- working with feedback；
- sensing and separation；
- seam model；
- 在无法直接测试的代码里打开测试入口；
- dependency-breaking techniques；
- 在必须修改、但没有安全网时如何降低风险。

## 为什么好

它回答了课堂里经常被忽略的问题：

> 如果代码已经存在、设计已经不好、测试也没有，我今天还必须改它，怎么办？

“先测试再写代码”对 greenfield 有用，但对真实 legacy repo 不够。Seam/characterization 思维特别适合 Agent 接管旧项目：先建立可观察边界，再允许大规模自动修改。

## 局限

- 2004 年出版，示例和工具明显带有当时 C++/Java/OO 风格；
- 某些 dependency-breaking technique 在现代语言/测试工具下不再是最佳做法；
- 不应照抄技术动作。

## 本课程怎么用

保留概念，不照抄时代性的 mechanics：

- characterization；
- seam；
- sensing / separation；
- legacy change algorithm；
- feedback before cleanup。

---

# 7. Google Site Reliability Engineering

**状态：选择性采用（Production / Failure 层）**

官方免费全文：
- https://sre.google/sre-book/table-of-contents/

## 实际检查了什么

检查了完整目录以及：

- Effective Troubleshooting；
- Emergency Response / Managing Incidents；
- Testing for Reliability；
- Handling Overload；
- Cascading Failure 相关内容；
- production best practices。

## 为什么好

它迫使学生面对“软件不是只在 unit test 世界里运行”的事实：

- overload；
- retry amplification；
- partial failure；
- degraded response；
- monitoring；
- incident response；
- postmortem。

对系统代码而言，failure semantics 本身就是 API/architecture 的一部分。

## 局限

- 很多章节针对大规模在线服务；
- 本课程不是 SRE 课程；
- SLO、capacity、load balancing 等只取足够支撑 SE reasoning 的部分。

---

# 8. Robert C. Martin — Clean Code

**状态：对照阅读，不作为主干权威**

第一版官方目录/样章：
- https://www.informit.com/store/clean-code-a-handbook-of-agile-software-craftsmanship-9780132350884

第二版官方页面：
- https://www.informit.com/store/clean-code-a-handbook-of-agile-software-craftsmanship-9780135398579

## 实际检查了什么

检查了第一版目录/公开章节、第二版详细目录，以及 APOSD 第二版专门加入的对比内容。

第一版公开内容里，作者明确说明该书会把这一“school of thought”的观点以 **absolutes** 的方式呈现。其主张包括：

- functions should be small；
- do one thing；
- comments often compensate for failure；
- classes should be small；
- DRY；
- one assert per test（正文有更细 nuance）。

2025 第二版仍延续“Everything Small, Well Named, Organized, and Ordered”等主线，并增加 AI/LLM 章节。

## 为什么不作为主干

不是因为它“差”或“过时”，而是因为 **我们的课程目标不是让学生接受一套 stylistic school**。

几个风险：

1. 规则容易脱离 context 被 Agent 机械执行；
2. “small function / small class”可能和 information hiding / deep module 产生真实冲突；
3. comments 的价值在 interface contract、design rationale、hidden invariant 中不能被简单归为失败；
4. 课程更想训练 trade-off argument，而不是 rule compliance。

## 为什么仍然值得读一部分

它很适合做 **design debate**：

- 同一段代码分别按 Clean Code 和 APOSD 重构；
- 比较依赖数量、接口复杂度、change amplification、可读性；
- 不问“谁赢”，而问“哪种环境下哪个设计更好”。

---

# 9. 当前暂不放入主干的材料

以下不是否定，只是目前还没有完成足够审计，或者与已有主干重合：

- Designing Data-Intensive Applications
- Accelerate
- Team Topologies
- The Pragmatic Programmer
- Code Complete
- Domain-Driven Design
- Fundamentals of Software Architecture
- Release It!

如果后续 architecture / production 模块发现明显内容缺口，再逐项检查后引入；不先塞书单。

---

# 10. 当前组合为什么不是“拼书”

这几份材料分别填不同层次：

```text
MIT 6.102
    ↓
函数 / ADT / spec / invariant / tests

Stanford CS190 + APOSD
    ↓
module / design / information hiding / review / revision

Refactoring + Legacy Code
    ↓
safe change / existing systems / feedback / seams

Software Engineering at Google
    ↓
time / scale / dependency / compatibility / large changes

Google SRE
    ↓
runtime reality / partial failure / observability / incident
```

课程本身再加一层：

```text
Agentic Software Engineering
    ↓
system model → task contract → agent implementation → evidence → independent review
```

这才形成从“小程序正确性”到“长期复杂系统变化”的完整 story。

---

# 11. 审计粒度：教材级与模块级分开

`MATERIALS_REVIEW.md` 只负责回答“这门课/这本书总体值得怎样使用”。

当某个模块真正采用具体观点时，还要有更细的 source audit，至少记录：

- 实际读了哪个公开正文/讲义/作业/review；
- 这个来源到底支持哪条 claim；
- 哪些术语或外推是本课程自己的综合，不是假装来源原话；
- 有哪些规模、语言、年代或组织背景限制；
- 哪些著名材料尚未完成一手审计，因此暂时不能升级成必读。

M02 的第一份模块级记录见：

`reading-notes/m02-source-audit.md`

其中 Parnas 论文被明确保留为 historical pointer，而没有因为“经典”就伪装成已经完成一手审计。

M03 继续使用同一标准，见：

`reading-notes/m03-source-audit.md`

这份审计实际检查了 MIT 6.102 Testing、Software Engineering at Google 的 Testing Overview / Unit Testing / Test Doubles / Larger Testing、Hypothesis 官方文档和 mutmut 官方文档，并明确把固定 test-pyramid 比例、coverage target、strict TDD、mocking 绝对规则和 mutation score 降级为需要 context 的工具/经验，而不是课程定律。

M04 继续使用同一标准，见：

`reading-notes/m04-source-audit.md`

这份审计实际检查了 Stanford CS190 Error Handling / APOSD discussion、Google AIP-193 / 194 / 155、AWS Builders' Library 的 idempotent API case study、RFC 9110 §9.2.2、Alexis King 的原始 `Parse, don't validate` 文章，以及 gRPC 官方 error/status 文档。它明确拒绝把“更多 exception class”“payload hash 去重”“retry everything”“HTTP method 决定业务幂等性”或“所有 invariant 都必须编码进 type system”升级成课程规则。

M05 继续使用同一标准，见：

`reading-notes/m05-source-audit.md`

这份审计实际检查了 Fowler 对 refactoring 的定义/边界/Two Hats/preparatory refactoring、Kent Beck `Tidy First?` 可公开访问的 structure-vs-behavior / batch-size / timing / untangling 章节、Google Small CLs 与 Large-Scale Changes，以及 Stanford CS190 的 iterative review/revision 和 `Design it twice`。课程据此把“大重写”“cleanup”“large-scale migration”和严格意义的 behavior-preserving refactoring 分开。

M06 继续使用同一标准，见：

`reading-notes/m06-source-audit.md`

这份审计实际检查了 Michael Feathers `Working Effectively with Legacy Code` 的官方目录、Changing Software、Sensing and Separation、The Seam Model、公开 glossary 中的 characterization-test 定义，以及 Martin Fowler 2024 的 `Legacy Seam`、Software Engineering at Google 的 Testing Overview / Test Doubles / Larger Testing / Hermetic Testing。课程吸收 change point、targeted feedback、sensing/separation、seam/enabling point、characterization 等模型，但拒绝把“legacy=旧代码”“先补全局 coverage”“所有 dependency 都必须 DI”“全 mock unit test 最高级”升级为课程规则。

M07 继续使用同一标准，见：

`reading-notes/m07-source-audit.md`

这份审计实际检查了 MIT 6.102 当前 Concurrency / Mutual Exclusion / Message-Passing & Networking 正文、Herlihy & Wing `Linearizability: A Correctness Condition for Concurrent Objects` 原论文，以及 Google SRE `Addressing Cascading Failures`、AWS backoff/jitter 与 retry guidance。课程吸收 race-as-interleaving、safety/liveness、operation-level linearization point、retry amplification 与 deterministic failure reasoning，但拒绝把“有 race 就加全局锁”“message passing 自动无 race”“idempotent 可以无限 retry”“stress test 跑够次数就证明线程安全”升级成课程规则。

M08 继续使用同一标准，见：

`reading-notes/m08-source-audit.md`

这份审计实际检查了 Google AIP-180 的 source/wire/semantic compatibility、Semantic Versioning 2.0.0 规范、Software Engineering at Google 的 Dependency Management 与 Deprecation、Martin Fowler / Danilo Sato 的 Parallel Change、Protocol Buffers 官方 schema-evolution guidance，以及 Kubernetes Deprecation Policy。课程据此把 compatibility 建模成 producer/consumer/version/direction/time-window 的矩阵，并把 expand→migrate→contract 与 reader-first/writer-later rollout 作为核心迁移模型；同时明确拒绝“major bump 就自动安全”“所有 migration 都 dual-write”“reader 应无限宽容”“历史 fixture 可以随新实现一起更新”等机械规则。

M09 继续使用同一标准，见：

`reading-notes/m09-source-audit.md`

这份审计实际检查了 SEI 对 software architecture 的结构化定义与历史说明、Martin Fowler 的 Software Architecture Guide / Monolith First / 2026 Architecture Decision Record、Stanford CS190 Modular Design、AWS Well-Architected 的 cell-based scope-of-impact guidance，以及 Google SRE Cascading Failures。课程据此把 architecture 建模成用于 system-level reasoning 的 consequential boundaries，并区分 semantic / process / deployment / failure boundary；同时明确拒绝“architecture=最高层目录”“microservices=成熟度”“画了 cell/service box 就形成 failure isolation”“ADR 越多越成熟”等机械规则。Parnas 1972 本轮仅保留 historical pointer，因为未获得愿意升级成新 primary-source authority 的完整原始出版正文。

M10 继续使用同一标准，见：

`reading-notes/m10-source-audit.md`

这份审计实际检查了 Google Engineering Practices 的 Code Review Standard / What to Look For / Navigating a CL / Small CLs / CL Descriptions / Review Comments / Review Speed、`Software Engineering at Google` Chapter 9 Code Review、Gerrit 官方 Review Labels / Submit Requirements、Stanford CS190 Code Review teaching material，以及 GitHub PR review governance mechanism。课程据此把 PR/CL 建模成 bounded engineering argument，把 author description 视为待验证 claim，并区分 machine verification 与 human review signal；同时明确拒绝“CI 绿就 approve”“评论越多 review 越认真”“所有 PR 必须小于固定 LOC”“所有旧债都必须在当前 PR 修”“实现 Agent 可以成为唯一 reviewer”等机械规则。

M11 继续使用同一标准，见：

`reading-notes/m11-source-audit.md`

这份审计实际检查了 Google SRE 的 Service Level Objectives / Monitoring Distributed Systems / Production Services Best Practices / Handling Overload，SRE Workbook 的 Implementing SLOs / Alerting on SLOs，Prometheus 官方 Instrumentation / Naming / Zen guidance，以及 OpenTelemetry Logs Data Model / Semantic Conventions。课程据此把 production evidence 建模成 `user expectation → SLI specification → measurement implementation → telemetry → aggregation/window → SLO/error budget → alert/action`，并区分 symptom/cause、aggregate/diagnostic signals 与 telemetry schema compatibility；同时明确拒绝“接上 OTel 就有 observability”“四个 golden signals 就是固定 dashboard”“所有 metric threshold 都 page”“job/request ID 适合 metric label”“固定 SLO/burn-rate 数值适用于所有系统”等机械规则。

M12 继续使用同一标准，见：

`reading-notes/m12-source-audit.md`

这份审计实际检查了 OpenAI Codex 当前 Best Practices / `AGENTS.md` / ExecPlans / Subagents / agent-loop 材料，Anthropic 的 effective agents、long-running harness、harness simplification、agent eval 与 parallel compiler experiment，SWE-bench 原论文，METR 2025–2026 maintainer-acceptance / developer-productivity 研究，以及 GitHub Copilot code-review instruction behavior。课程据此把 Agentic SWE 建模成 `durable context + scoped capability/permission + explicit engineering authority + evidence contract + stop/escalation + independent acceptance`，并明确拒绝“prompt 越长越好”“一定先 plan”“多 Agent 一定更好”“benchmark/test pass 等于 mergeable”“所有 production action 永远必须人工点击”“某个固定 AI productivity uplift 数字可以当课程定律”等机械规则。
