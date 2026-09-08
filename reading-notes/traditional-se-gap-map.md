---
id: traditional-se-gap-map
type: reference
visibility: student
related: [extensions]
---
# Traditional Software Engineering Gap Map

> 目的：回答一个比“传统 SE 还要不要学”更具体的问题——**SWEBOK 等传统知识地图中的哪些问题已经被 M00–M13 实质吸收，哪些只覆盖了一部分，哪些是真缺口，哪些对本课程目标优先级很低？**
>
> 本表不是 accreditation checklist，也不是要求课程逐项补齐。分类是课程设计判断，依据当前仓库内容和 2026-09-06 实际检查的 SWEBOK v4.0a / 当前课程资料。

## 分类含义

- **已覆盖**：主线已经用自己的问题组织方式充分训练该领域的核心工程判断；不应再增加一篇“传统版”重复讲义。
- **部分覆盖**：主线已经大量使用该领域的概念，但缺少一层能帮助读者识别、命名或迁移的框架；适合短旁支或 cross-link。
- **真缺口**：当前课程目标需要这个能力，但 M00–M13 没有系统训练；需要独立 Extension。
- **低优先级 / 前置知识**：该领域真实存在，但对“控制复杂度、设计变化、驾驭 Agent”的主线不是当前最值得补的内容，或应由其他 CS/工程课程承担。

## 总表

| SWEBOK v4.0a Knowledge Area | 当前判断 | 已有主线 | 还缺什么 / 为什么不另开主模块 |
|---|---|---|---|
| 1. Software Requirements | **真缺口** | M01 强在 specification/contract；M10/M12/M13 会 review issue 和 unresolved decision | 缺 stakeholder、elicitation、需求冲突/协商、validation、traceability/evolution。Contract 不是凭空出现的。 |
| 2. Software Architecture | **已覆盖** | M02、M04、M07、M09 | M09 已直接训练 architecture boundary、data/control flow、authority、failure domain、migration consequence；无需“架构模式百科”。 |
| 3. Software Design | **已覆盖** | M02、M04、M05、M09 | abstraction、information hiding、API/boundary、evolutionary design 已是主线核心。 |
| 4. Software Construction | **低优先级 / 前置知识** | 全课程 labs + TaskForge | 本课程假设会编程；coding/debugging/language mechanics 应由 Software Construction/PL/系统课程承担。Agent 时代也不等于这些技能不重要，只是不需要在本课重新教。 |
| 5. Software Testing | **已覆盖** | M03，且贯穿 M04–M13 | M03 已把 testing 放在 claim/evidence、oracle、mutation、brittleness 和 testability 上训练；不需再写测试分类百科。 |
| 6. Software Engineering Operations | **已覆盖** | M08、M11、M13 | deployment/migration/rollback/production evidence/SLI/SLO/observability 已有完整主线。 |
| 7. Software Maintenance | **已覆盖** | M05、M06、M08、M10 | refactoring、legacy takeover、program comprehension、change impact、compatibility/migration 已充分覆盖。 |
| 8. Software Configuration Management | **部分覆盖** | M08、M10、M12、M13 | 已大量使用 version/compatibility/release/change evidence，但缺 configuration item、baseline、artifact identity、status/accounting、release composition/provenance 的统一解释。 |
| 9. Software Engineering Management | **真缺口（选择性）** | M09/M10 有 scope、risk、review；M12 有 orchestration | 不需要补项目经理课程，但需要 risk、uncertainty、estimation、resource/review bottleneck、decision horizon 的工程解释。与 Economics 合并为一个旁支。 |
| 10. Software Engineering Process | **真缺口（选择性）** | 课程自身有 Understanding/Change/Agent loop | 几乎不解释 iterative feedback、batch size、WIP、flow、team coordination，也没有说明 Scrum/Waterfall/Agile 为什么有些思想有用、有些只是 ceremony。 |
| 11. Software Engineering Models and Methods | **部分覆盖** | system model、state machine、data flow、architecture map 贯穿课程 | 缺“为了回答问题而选择模型”的显式方法，以及 UML/C4/sequence/state/dependency view 各自能表达什么、不能证明什么。 |
| 12. Software Quality | **部分覆盖** | M03 correctness evidence；M05 maintainability；M09 architecture qualities；M11 reliability | 课程谈很多质量问题，但缺 quality attribute vocabulary，以及如何把“高质量”拆成可冲突、可度量、可验收的属性。 |
| 13. Software Security | **部分覆盖** | M04 boundary/error；M09 authority/failure domains；M12 tool permission/authority | 缺 asset/adversary/trust boundary/threat model/least privilege/supply-chain 的完整入口。需要旁支，但不扩成安全课程。 |
| 14. Software Engineering Professional Practice | **真缺口（选择性）** | M10 review communication；M12 human authority | 缺 responsibility、risk communication、privacy/confidentiality、licensing/provenance，以及“自动生成不转移责任”的明确讨论。 |
| 15. Software Engineering Economics | **真缺口（选择性）** | M05/M08/M09 已经讲 reversibility、migration cost、change cost | 缺系统的 alternative/criterion/uncertainty/estimation/TCO/option-value 思维。与 Management/Risk 合并旁支，避免财务课化。 |
| 16. Computing Foundations | **低优先级 / 前置知识** | 课程默认 CS 背景 | 数据结构、算法、OS、DB、network、PL、HCI 等应按需回到专门课程。 |
| 17. Mathematical Foundations | **低优先级 / 前置知识** | M01 invariants、M03 evidence、M07 concurrency 会使用逻辑/状态机思维 | 不在本课补离散数学/概率/形式逻辑；对特定 formal method 需要时再专项学习。 |
| 18. Engineering Foundations | **部分吸收，不单独补** | M00 complexity/change；M03 evidence；M09 trade-off；M13 capstone | modeling、measurement、experiment、root-cause 等思想已散布主线；完整 general engineering foundation 超出课程边界。 |

## 结论：为什么是八个 Extensions，而不是十五个

如果照 SWEBOK 的章节数补课，课程会立刻失去自己的问题主线。上表显示，大量传统 SE 主题不是缺失，而是已经被重新组织进了 M00–M13。

真正需要新增的内容可以收敛成八个旁支：

1. [Requirements Engineering 与 Stakeholders](../extensions/requirements-and-stakeholders.md)：补 Software Requirements 的上游部分。
2. [Configuration、Baseline 与 Release](../extensions/configuration-baselines-and-release.md)：给 M08/M13 已经使用的版本与发布推理补 artifact identity / baseline 框架。
3. [Engineering Risk、Estimation 与 Economics](../extensions/engineering-risk-estimation-economics.md)：把 Management + Economics 中最能帮助技术决策的部分合并。
4. [Process、Feedback 与 Team Coordination](../extensions/process-feedback-and-team-coordination.md)：保留 iterative feedback / small batch / WIP / ownership，拒绝 ceremony memorization。
5. [Software Quality](../extensions/software-quality-models.md)：补 quality-attribute 语言，而不重复 Testing。
6. [Security Engineering](../extensions/security-engineering.md)：把 M09/M12 的 authority 推理连接到 threat/trust/privilege。
7. [Professional Practice](../extensions/professional-practice-ethics-law.md)：补责任、沟通、隐私和许可边界。
8. [Models、Notation 与 UML](../extensions/models-notation-and-uml.md)：把“画什么模型”变成 system-modeling tool choice，而不是 notation exam。

## 几个容易误判的领域

### Testing 不是“传统内容，所以要旁支”

M03 已经比很多传统测试章节更贴近本课程目标。再增加一个“unit/integration/system/acceptance test 分类”页面，只会把读者从 evidence reasoning 拉回术语记忆。因此 Testing 判为已覆盖，而不是因为传统测试不重要。

### Configuration Management 也不是“会 Git 就覆盖了”

课程已有 Git/release/migration 的大量真实操作，但 SCM 真正补充的是另一组问题：你正在 reasoning about 的 artifact 到底是哪一组？哪一个 baseline 获得了什么 authority？source、schema、config、generated artifact、binary 和 deployment 之间怎样保持可追溯的 identity？这正是 Agent 批量生成修改后容易被低估的地方。

### Process 不是 Scrum 教程

课程目前几乎没有 Scrum/Agile/Waterfall，这本身并不是缺点。缺的是更底层的 feedback/flow reasoning：为什么小批次 change 更容易 review 和 rollback？为什么让十个 Agent 同时开始写代码可能增加 WIP 而不是增加 throughput？什么时候 process rule 在保护反馈回路，什么时候只是 ceremony？旁支只保留这一层。

### Professional Practice 不是“软技能附录”

当 Agent 能写 patch、跑测试甚至给出 review 结论后，“谁有 authority、谁承担责任、谁必须披露风险和不确定性”已经是系统工程边界，而不是可有可无的职业礼仪。因此该领域对 Agentic Software Engineering 有直接连接。

## 课程边界没有因此改变

补完 Extensions 后，课程仍然不承诺：

- 教完所有传统 SE 知识；
- 覆盖 certification/accreditation syllabus；
- 训练完整 product management / project management；
- 训练完整 cybersecurity；
- 训练法律实务；
- 代替 CS 基础课程。

它只承诺：对于一个以真实 software change 和 Agent orchestration 为目标的工程师，传统 SE 中那些仍然会改变其判断质量的内容，不会因为“旧课程经常教得不好”而被一起丢掉。
