# Engineering Risk、Estimation 与 Economics：怎样比较两个都能做出来的方案

软件设计讨论里经常出现一种伪客观性：方案 A 和方案 B 都能实现，于是大家开始争哪一个“更优雅”。如果争不出结果，就数代码行、比较 benchmark，或者让 senior engineer 凭经验拍板。

但真实工程决策通常不是在真空中比较实现。它们是在有限时间、有限 review capacity、兼容性约束、未知 failure mode 和未来变化下选择一个**值得现在承担的风险与成本结构**。

Software Engineering Management 和 Software Engineering Economics 中最值得本课程保留的，不是项目管理表格，而是这套 decision reasoning。

主线已经要求你比较 design trade-off、migration risk 和 review evidence；本页只在“多个方案都技术可行，但 uncertainty、resource scarcity、future cost 开始主导选择”时提供更一般的经济决策语言，所以不值得为所有学生再增加一章线性必修。

## 1. 从一个 rewrite 决策开始

假设一个旧 scheduler 越来越难改。两个方案都可行：

**方案 A：完整 rewrite。** 新实现更简单，可以一次解决 ownership、persistence 和 API 历史包袱。

**方案 B：分阶段演化。** 先建立 characterization tests，再收拢 state owner，然后做 expand/contract migration，最后删除旧路径。

如果只比较最终架构，A 可能明显更漂亮。但工程问题还包括：

- 我们真的理解全部 legacy behavior 吗？
- 旧 consumer 能否一起切换？
- rewrite 期间业务是否停止变化？
- 两个系统需要并存多久？
- reviewer 一次能可靠验证多大的 semantic delta？
- 如果三周后发现假设错误，已经花掉的工作还能复用多少？
- 哪个方案更容易获得早期 evidence？

这时“哪套代码最终更好”已经不是唯一目标。

## 2. Risk 不是一个红黄绿标签

最常见的 risk 表达是 `probability × impact`。它有用，但对软件 change 不够。

软件风险还有几个经常决定方案质量的维度。

### 可探测性

一个错误多久会被发现？如果只有极端 mixed-version rollout 才出现，它可能在测试阶段长期潜伏。

### 可逆性

发现错了以后能不能回到安全状态？一个 UI 文案改动和一个不可逆 data rewrite 即使失败概率相同，工程风险也完全不同。

### Blast radius

失败只影响一个 opt-in tenant，还是所有 caller？是否可以 canary？

### Unknown unknowns

最危险的方案有时不是已知 failure probability 高，而是你甚至不知道自己遗漏了哪些 consumer、协议或状态。

### Evidence latency

做出决定后多久能得到有信息量的反馈？如果必须完成三个月 rewrite 才能验证核心假设，决策成本远高于一周后就能跑 compatibility probe 的方案。

所以高质量的 risk analysis 不只是给每项打 1–5 分，而是问：**我们怎样让错误更早暴露、更局部、更容易撤销？**

## 3. Reversibility 是一种 option value

M05/M08 已经多次强调可逆 change。Economics 给它一个更一般的解释：保留未来选择本身可能有价值。

例如你不确定新 protocol 是否会被所有 worker 正确实现。直接删除旧协议意味着今天获得一点代码简化，却失去 rollout 期间的退路。保留一个短期 compatibility bridge 会增加当前复杂度，但买来一个 option：观察真实 evidence 后再决定何时退休旧路径。

这种 option 不是免费。Bridge 也有维护、测试、认知成本，所以不能无限保留。

真正的问题是：

> 在不确定性消失之前，这个暂时的复杂度是否值得为可逆性付费？

这比“兼容层永远好”或“技术债一定要马上删”都更接近工程现实。

## 4. Sunk cost 不应该偷偷变成设计理由

项目做到一半时最难说的一句话是：

> 我们已经投入很多，但这个方向仍然不值得继续。

已经不可回收的工作量是 sunk cost。它可以告诉你为什么团队情绪上难以放弃，却不应该自动提高方案未来的价值。

Review 一个长时间 Agent task 时尤其需要警惕这一点。Agent 已经改了 80 个文件、跑了两小时，并不会使错误 architecture 更值得 merge。

未来决策应该主要比较：

- 从现在继续需要什么成本；
- 能产生什么 value/evidence；
- 有什么 remaining risk；
- 有哪些替代方案。

当然，已有工作可能产生 reusable artifact，那部分不是纯 sunk cost。关键是不要因为“都写这么多了”取消独立判断。

## 5. Estimation 的第一目标不是给出一个看起来专业的数字

“这个 change 几天能做完？”很多团队期待一个单点答案：`3 days`。

但未知代码库、migration、跨团队 contract 或新 Agent workflow 中，单点 estimate 很容易隐藏不确定性。

更有信息量的 estimate 会先分解**我们到底不知道什么**。

例如：

```text
已知机械工作：API adapter + tests
未知 1：旧 client 是否依赖 KeyError
未知 2：schema expand 是否兼容 frozen reader
未知 3：remote worker 是否存在长期离线版本
```

这时下一步可能不是“估得更准”，而是先花半天跑 compatibility probe，让 uncertainty collapse。

因此 estimation 可以成为 reconnaissance tool：它迫使你说明复杂度来自哪里。

## 6. 用 range 和 condition，比伪精确更诚实

不是所有项目都需要概率模型。简单 change 也不必写 PERT。

但对高不确定任务，下面这种表达通常比 `5 days` 更有工程价值：

> 如果 frozen v1 reader 可以读取 expand-only schema，实现 + test 约 1–2 天；如果不能，需要额外 compatibility layer 和 rollout phase，工作量会显著增加。先用 1 小时 probe 决定走哪条路径。

这个 estimate 同时表达：

- conditional branch；
- critical unknown；
- cheap information-gathering action；
- 为什么 range 会扩大。

它让 manager、reviewer 和 Agent 都知道什么事实会改变计划。

## 7. Value of Information：什么时候先研究，不要先实现

有些 unknown 很便宜就能消除，却会决定整个 architecture。

例如：

- 旧 binary 能否读新 schema；
- 某 API 是否真的有外部 consumer；
- performance bottleneck 在 CPU 还是 network；
- vendor library 是否支持需要的 transaction semantics。

如果一个 30 分钟 probe 能避免一周错误实现，那么先调查通常是高价值行动。

反过来，也不能无限 research。一个 unknown 如果很难消除、而两个方案对它都不敏感，就没有必要把“更多信息”当作拖延理由。

一个实用问题是：

> **这个新信息有多大概率改变我们的 decision？如果不会改变，为什么要现在获取？**

## 8. Total Cost 不是 license price

Build vs buy、依赖选择、managed service、自研 framework 经常只比较眼前开发成本。

更完整的视角会看整个 relevant horizon：

- acquisition / implementation；
- integration；
- migration；
- training / cognitive load；
- upgrades；
- operations；
- security response；
- vendor/maintainer risk；
- exit / replacement cost；
- review and verification burden。

一个“免费” dependency 也可能因为 compatibility churn 和 supply-chain risk 变贵；一个昂贵 managed service 也可能因为显著降低 operational surface 而总体更便宜。

这不是要求每个依赖都做财务模型，而是提醒：**技术选择会改变未来成本分布。**

## 9. Opportunity Cost：做这个 change 意味着没有做什么

Agent 让 implementation parallelism 变高以后，团队很容易误以为 opportunity cost 消失了。

但 bottleneck 可能已经移动到：

- human review；
- integration environment；
- product decision；
- security approval；
- migration window；
- production observation；
- domain expert attention。

如果十个 Agent 同时生成十个大型 PR，而只有两个 reviewer 能建立可靠 mental model，系统的 WIP 增加，真正 throughput 可能下降。

因此评估 Agent productivity 时不能只看 generated LOC 或 task completion。应该看**稀缺资源被占用了多少，以及 change 到 trustworthy/mergeable state 花了什么代价。**

这和 [Process、Feedback 与 Team Coordination](process-feedback-and-team-coordination.md) 直接相连。

## 10. Technical Debt：不是“所有不漂亮的代码”

“技术债”这个词很容易成为重构预算申请器。

更有用的表达是指出具体 future cost：

- 每新增一种 state 都要改 8 个模块；
- 每次 release 都要手工同步两份 schema；
- 没有 compatibility fixture，升级一次要占用两天人工验证；
- duplicated authority 使任何 lifecycle change 都需要双路径 review。

这样才能比较：

> 现在付出 refactor/migration cost，能否减少未来可预期的 change/review/incident cost？

如果所谓 debt 没有可解释的 future consequence，它可能只是 aesthetic preference。

## 11. Multiple Criteria：有些方案没有单一“最优”

工程 alternative 往往同时影响：

```text
correctness risk
compatibility
latency
operational complexity
implementation time
reviewability
reversibility
future change cost
security
```

不需要发明一个“总分 = 0.23 × 可维护性 + 0.17 × 性能”的公式。很多权重本来就是价值判断。

但把 criteria 明确写出来仍然非常有用，因为它暴露了争论真正在哪里。

如果 A/B 的技术事实大家都同意，但有人优先 backward compatibility，有人优先尽快删除旧路径，那么这是 priority/authority 问题，不应该继续伪装成代码事实争论。

## 12. Agent 可以帮助估算，但不能制造 certainty

Agent 很适合：

- 分解 work surface；
- 搜索 affected consumer；
- 统计 change amplification；
- 建立 migration steps；
- 找历史类似 change；
- 运行 probe 缩小 uncertainty；
- 比较多个 design 的 explicit consequences。

但它给出的 `2–3 days` 如果没有 grounding，和人的拍脑袋数字没有本质区别。

更好的 Agent 输出应包括：

```text
estimate / risk claim
→ evidence
→ unresolved assumption
→ what observation would change the estimate
```

这让 estimation 成为可 review 的 engineering argument。

## 13. 一个轻量 Decision Record

当两个方案都 plausible 时，可以写一个很短的 decision record：

**Problem**：真正需要解决什么？

**Constraints**：哪些 contract、时间、资源、authority 不能随便改变？

**Alternatives**：至少列出实际可行的候选，而不是一个方案 + 一个故意很差的陪衬。

**Critical unknowns**：哪些事实如果不同会改变选择？

**Criteria**：correctness、compatibility、reversibility、cost、reviewability 等哪个在这里重要？

**Evidence**：benchmark、probe、consumer search、historical incident 等实际支持什么？

**Decision and horizon**：现在选什么？这个选择是永久的，还是只到某个 migration phase？

**Revisit trigger**：出现什么新证据时需要重新决策？

如果这份记录不能说明为什么选 A，只能写“更 clean / more scalable”，说明 decision 还没有被工程化。

## 14. 这篇旁支不教什么

这里没有教完整 project budgeting、EVM、组织 staffing 或企业财务，也不会承诺某种 estimation technique 能消除软件不确定性。

本课程只保留一个核心：**当实现方案不止一个时，不要只比较最终代码形状；比较它们如何消耗稀缺资源、暴露不确定性、产生 evidence、保留未来选择，并把 failure consequence 分布到时间和系统边界上。**

材料来源与取舍见 [`reading-notes/extensions-source-audit.md`](../reading-notes/extensions-source-audit.md)。
