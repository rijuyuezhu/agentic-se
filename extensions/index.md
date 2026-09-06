# Extensions：主线之外，仍然值得学的软件工程

M00–M13 是这门课的主线。它刻意把注意力放在 boundary、contract、invariant 和 change 上，因为这些概念能直接迁移到陌生代码库、code review 和 coding agent 协作中。

这并不意味着传统 Software Engineering 里剩下的内容都没有价值。恰恰相反：有些问题只是没有必要各占一章。例如，M01 会教你怎样写清一个 contract，却没有系统回答“这个 requirement 最初从哪里来”；M08 会讨论 compatibility 和 migration，却不会完整介绍 baseline、release composition 和 configuration control；M12 会讨论 Agent 的 authority，却只零散触及 security 与 professional responsibility。

Extensions 用来补这些缺口。它们是**按需阅读的旁支**，不是 M14、M15，也不会进入主线的线性编号。

## 怎么使用这些页面

你不需要按顺序读完所有旁支。遇到真实问题时再进入相应页面，通常效果更好。

| 当你遇到的问题 | 建议阅读 |
|---|---|
| issue 写得很具体，但你怀疑它把 solution 当成了 requirement | [Requirements Engineering：contract 从哪里来](requirements-and-stakeholders.md) |
| 代码能回滚，但 schema、config、binary、generated artifact 对不上 | [Configuration、Baseline 与 Release](configuration-baselines-and-release.md) |
| 两个设计都能做出来，不知道如何比较风险、成本和可逆性 | [Engineering Risk、Estimation 与 Economics](engineering-risk-estimation-economics.md) |
| 团队或多个 Agent 都很忙，但 change 一直卡在 review/integration | [Process、Feedback 与 Team Coordination](process-feedback-and-team-coordination.md) |
| “质量更高”变成一句无法验证的口号 | [Software Quality：把质量属性变成 contract](software-quality-models.md) |
| sandbox、权限、依赖和输入边界开始影响安全性 | [Security Engineering：从 trust boundary 到 Agent authority](security-engineering.md) |
| 技术上能做，但谁有权决定、谁承担责任并不清楚 | [Professional Practice：责任、沟通、隐私与许可](professional-practice-ethics-law.md) |
| 想画图，却不知道什么图真的帮助 reasoning | [Models、Notation 与 UML：图是证据工具，不是作业格式](models-notation-and-uml.md) |

## 这些旁支和传统课程有什么不同

传统教材常按学科目录组织知识：Requirements、Configuration Management、Process、Quality、Economics……这种分类本身没有错，但分类不等于教学优先级。

这里采用另一条准则：一个主题只有在能帮助你做真实 engineering decision 时才值得进入课程。比如 Scrum 的角色名称不会因为属于“Software Process”就自动值得学；但“为什么过多 WIP 会拉长 feedback loop”“为什么一个 3000 行 PR 很难获得可靠 review”则与安全变化直接相关。类似地，我们不会系统背 UML 图形符号，却会讨论什么时候 state machine、sequence/dynamic view 或 dependency graph 能暴露真正的 contract 和 failure ordering。

因此这些页面会反复区分三件事：

1. **问题是否真实存在。** 传统 SE 研究的很多问题一直存在。
2. **旧的教学包装是否值得保留。** 不一定。
3. **这个问题怎样重新连接到本课程的主线。** 这是 Extensions 的重点。

## 与主线的关系

旁支不是另一套平行课程。它们应能回到 M00–M13 已经建立的语言：

- Requirements 最终要落到 observable contract、decision authority 和 validation evidence；
- Configuration Management 最终要保护 change 的 identity、baseline、traceability 和 reversibility；
- Risk/Economics 最终要帮助比较 alternative，而不是制造伪精确数字；
- Process 最终要缩短有信息量的 feedback，并限制协调成本；
- Quality 最终要把模糊形容词变成可观察属性和 trade-off；
- Security 最终要明确 asset、trust boundary、authority 和 failure consequence；
- Professional Practice 最终要明确责任不能随 implementation 一起外包给 Agent；
- Models 最终要帮助人或 Agent更准确地建立和检查 system model。

如果一篇旁支无法回到这些问题，它大概率不值得留在这门课里。

## 为什么没有更多页面

当前没有为 Architecture、Testing、Maintenance、Operations 另写“传统 SE 版”旁支，因为这些领域已经分别被 M02/M04/M05/M09、M03、M05/M06/M08、M11 实质覆盖。重新按 SWEBOK 目录讲一遍只会制造重复。

Computing Foundations 和 Mathematical Foundations 也不在这里补齐：本课程假设读者已经具备 CS 基础，需要时应回到数据结构、算法、OS、网络、数据库、离散数学等专门课程，而不是把它们压缩成软件工程附录。

完整的 coverage/gap 判断见 [`reading-notes/traditional-se-gap-map.md`](../reading-notes/traditional-se-gap-map.md)。旁支材料的实际来源审计见 [`reading-notes/extensions-source-audit.md`](../reading-notes/extensions-source-audit.md)。
