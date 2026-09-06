# Extensions Source Audit — 传统 Software Engineering 旁支

> 本文件记录 `extensions/` 真正检查过的来源、访问时状态、课程吸收的 claim 和明确不照搬的部分。
>
> 审计日期：**2026-09-06**。
>
> 目标不是证明“传统 SE 仍然正确”，而是回答：**哪些长期存在的 Software Engineering 问题仍会直接影响真实代码库和 Agent-assisted development 的工程判断？**

## 0. 审计原则

本轮遵循仓库已有 `MATERIALS_REVIEW.md` 的标准，并额外加三条约束。

第一，**knowledge map 不是教学优先级**。SWEBOK 可以证明一个领域在软件工程共同知识里有稳定位置，但不能据此推出它应该占本课程一章。

第二，**当前 curriculum 只能证明仍有人认真教这个问题，不能证明具体教学法最佳**。因此 CMU 当前 MSE 被用作“AI 进入课程以后，Requirements/Management/Quality/Communication 是否仍被保留”的外部 sanity check，而不是作为课程权威。

第三，**会变化的网页必须记录日期和版本状态**。尤其 NIST SSDF、SWEBOK 和当前 university curriculum，未来同一 URL 可能变化。

---

## 1. IEEE Computer Society — SWEBOK Guide v4.0a

官方主页：

https://www.computer.org/education/bodies-of-knowledge/software-engineering

官方 Topics / Table of Contents：

https://www.computer.org/education/bodies-of-knowledge/software-engineering/topics

访问：2026-09-06。

### 当前版本状态

官方主页写明：SWEBOK v4.0 在 2024 年发布；**2025-09-25** 做了 minor revisions，并以 **v4.0a** 区分更新后的版本。

官方页面把 v4 划分为 18 个 Knowledge Areas，并明确说明相较 v3：

- Agile / DevOps 被整合进多个 KA；
- 新增 Software Architecture；
- 新增 Software Engineering Operations；
- 新增 Software Security。

这对本 issue 很重要，因为它说明我们不能把“传统 SE”偷换成 1990s 的固定课程印象。当前 consensus map 本身已经吸收了一部分现代实践。

### 实际检查的 Knowledge Areas

我们实际检查了当前 Topics 页中与本 issue 相关的目录，而不是只看 18 个标题。

#### Software Requirements

当前目录包括：

- requirements sources / elicitation techniques；
- analysis；
- addressing conflict in requirements；
- formal analysis；
- software requirement activities。

**课程吸收：** M01 的 specification/contract 是 Requirements 的中下游，不足以覆盖 requirement source、stakeholder conflict 和 elicitation。由此确认 [Requirements Engineering](../extensions/requirements-and-stakeholders.md) 是真缺口。

**不照搬：** 不按完整 SRS/template 或 requirement taxonomy 组织旁支；不因为 SWEBOK 列出某个 technique 就要求学生掌握所有 technique。

#### Software Configuration Management

当前 v4 Topics 明确覆盖：

- change request / implementing changes；
- status accounting；
- configuration audits；
- software baselines；
- software release management / building。

**课程吸收：** 把 `baseline / configuration identity / change authority / status / release composition` 作为 M08/M10/M12/M13 已有推理的统一框架。

**不照搬：** 不引入固定 Change Control Board、表单流或传统 library/check-out process 作为现代项目默认做法。

#### Software Engineering Management

当前目录包括：

- determination / negotiation of requirements；
- feasibility；
- effort/schedule/cost estimation；
- resource allocation；
- risk management；
- measurement / monitoring / reporting。

**课程吸收：** 只取与技术 decision 强相关的 uncertainty、risk、estimation、resource bottleneck 和 evidence-driven replanning。

**不照搬：** 不把课程扩成 project management、staffing、budgeting 或 scheduling 课程。

#### Software Engineering Process

当前目录包括：

- life-cycle rationale / paradigms；
- process adaptation；
- process monitoring；
- assessment / improvement；
- Agile process improvement。

**课程吸收：** 把 process 重新解释为 feedback architecture、WIP/flow 和 coordination design。

**不照搬：** 不要求背 waterfall 阶段、Scrum roles、CMMI/process maturity 级别。

#### Software Engineering Models and Methods

当前目录包括：

- modeling principles；
- syntax/semantics/pragmatics；
- structural / behavioral models；
- completeness / consistency / correctness / traceability / interaction analysis；
- heuristic/formal/prototyping/agile methods。

**课程吸收：** 明确“模型必须由 engineering question 驱动”，以及 structural/behavioral/model-analysis 三层用途。

**不照搬：** 不系统教授所有 modeling language，也不把 UML 当成课程共同 notation。

#### Software Quality

当前目录包含：

- value/cost of quality；
- models/standards；
- dependability；
- quality management/measurement；
- product/process assurance；
- V&V/testing/review/audit。

**课程吸收：** 本课程已有 M03/M09/M11，不需要再建 QA 主线；只补 quality attribute / product claim / process evidence 的区分。

#### Software Security

v4 新增独立 Software Security KA，官方介绍强调 security 贯穿 lifecycle，而非最后测试。

**课程吸收：** 把 M04/M09/M12 的 boundary/authority reasoning 加上 adversarial lens，并引入 asset、trust boundary、least privilege、threat model、supply-chain provenance。

**不照搬：** 不扩成完整 secure SDLC、漏洞分类或 penetration-testing 课程。

#### Software Engineering Professional Practice

当前官方资源将 professional practice 描述为 competent / ethical / responsible practice，并覆盖 group dynamics、communication 等非纯技术责任。

**课程吸收：** responsibility、risk communication、privacy/confidentiality 和 Agent authority。

**不照搬：** 不做职业资格/认证/伦理选择题。

#### Software Engineering Economics

当前目录包括：

- alternatives / business model；
- engineering decision-making；
- multiple-attribute decision-making；
- estimation；
- systems thinking；
- prioritization。

**课程吸收：** 让 technical design comparison 显式考虑 uncertainty、reversibility、future cost、opportunity cost、value of information。

**不照搬：** 不教授完整财务、cash-flow、MARR、EVM 等内容。

### 对 SWEBOK 的总体判断

**状态：选择性采用，作为 gap map，不作为课程权威。**

SWEBOK 最有价值的是提醒我们：传统 SE 研究的对象比 coding/design/testing 更宽。它不应该直接决定本课程课时，更不能把 consensus topic list 变成 universal best practices。

这就是为什么 `reading-notes/traditional-se-gap-map.md` 对 Architecture/Testing/Maintenance/Operations 判为“已覆盖”，而不是继续为每个 KA 增加旁支。

---

## 2. Carnegie Mellon MSE — 当前 AI-oriented curriculum sanity check

Requirements：

https://mse.s3d.cmu.edu/applicants/mse-as/requirements.html

Plan of Study：

https://mse.s3d.cmu.edu/applicants/mse-as/plan.html

访问：2026-09-06。

### 实际检查

当前 on-campus MSE 从 Fall 2027 起的 requirements 把以下内容同时列为 core：

- Software Engineering with AI；
- Specifications；
- Requirements；
- Management；
- Quality；
- Architecture/Design；
- Communications。

Plan of Study 还明确写出 learning outcome：学生应能 gathering / analyzing / prioritizing requirements from a real-world industrial customer，并有效结合 human and AI resources；同时要能 manage project、communicate with technical/nontechnical audiences，并适应 AI 带来的行业变化。

### 课程吸收

这份资料只用来反驳一个过度推论：

> “既然 AI 会写代码，传统 Requirements/Management/Quality/Communication 已经不属于现代 Software Engineering。”

当前一所明确把 AI 纳入 MSE core 的项目仍保留这些领域，说明“AI vs traditional SE”不是必须二选一。

### 不照搬

- 不采用 CMU 的具体学分结构；
- 不把 Product Management/Agile Methods 直接加入本课程；
- 不因为 CMU 这么教就证明这些课程内容天然适合自学；
- 不把 employment outcome 当课程质量证据。

**状态：curriculum sanity check，不作为理论来源。**

---

## 3. IEEE Computer Society — Configuration Management resource

URL：

https://www.computer.org/resources/software-configuration-management

访问：2026-09-06。

### 实际检查

当前资源明确把 SCM 描述为控制 software artifacts 在 lifecycle/release 中的变化，并强调：

- configuration item identity；
- change tracking；
- baseline；
- release recreation；
- traceability；
- release management。

页面对 baseline 的解释尤其适合本课程：baseline 是一组被认可的 configuration items 的稳定参考点，用来给后续 change 提供共同起点。

### 课程吸收

[Configuration、Baseline 与 Release](../extensions/configuration-baselines-and-release.md) 使用：

- Git != 完整 SCM；
- baseline 给 correctness/review claim 一个共同 before state；
- release 是 artifact combination；
- rollback 要说明哪些 configuration item 可逆；
- status/accounting 的工程目标是“现在到底在哪个 state”。

### 不照搬

页面带有较传统的 SCM organization/tool language。课程不升级为“必须建立独立 SCM team / library / formal approval board”。

---

## 4. IEEE Computer Society — Software Engineering Management / Economics resources

Management：

https://www.computer.org/resources/software-engineering-management

Economics：

https://www.computer.org/product/education/software-engineering-economics-course/

访问：2026-09-06。

### 实际检查

Management resource 当前明确把：

- scope / requirements；
- feasibility；
- estimation；
- resource allocation；
- risk；
- measurement / monitoring / control

放在 software engineering management 中。

Economics course description 则把 software engineering economics 定位为“在 business context 中做 software engineering decision”，包括 risk/uncertainty、prioritization、estimates 和 economic analysis。

### 课程吸收

[Engineering Risk、Estimation 与 Economics](../extensions/engineering-risk-estimation-economics.md) 保留：

- alternative 必须按明确 criteria 比较；
- uncertainty 本身会改变 design value；
- estimation 先暴露 critical unknown，而不是制造单点 certainty；
- reversibility 可以理解为保留 future option；
- Agent 让 implementation cost 下降时，review/product/security attention 仍可能是稀缺资源。

### 课程 synthesis，不归因给来源的部分

以下表述是本课程把 M05/M08/M10/M12 与 economics 连接后的 synthesis，不应伪装成 IEEE 原句：

- “review capacity 可能成为 Agent 时代 bottleneck”；
- “value of information 可以用 probe 是否会改变 decision 来判断”；
- “technical debt 应解释成 future change/review/incident cost，而不是 aesthetic label”。

### 不照搬

没有进入 finance、cash-flow、MARR、EVM、完整 portfolio/project economics。

---

## 5. Agile Manifesto + Principles

Manifesto：

https://agilemanifesto.org/

Principles：

https://agilemanifesto.org/principles

访问：2026-09-06。

### 实际检查

原始 Manifesto 强调：

- individuals/interactions；
- working software；
- customer collaboration；
- responding to change；

同时明确说明右侧项目仍有价值，只是更重视左侧。

Principles 进一步强调 early/continuous delivery、welcome change、frequent delivery、business/developer collaboration、sustainable pace、technical excellence、simplicity 和 regular reflection。

### 课程吸收

[Process、Feedback 与 Team Coordination](../extensions/process-feedback-and-team-coordination.md) 只吸收其 feedback-oriented 核心：

- 短迭代的意义是更早得到 evidence；
- changing requirements 需要可演化 workflow；
- technical excellence 与适应变化不是对立面。

### 不照搬

- 不把 Agile Manifesto 当科学定律；
- 不把“face-to-face”升级成现代 remote team 的唯一最佳沟通方式；
- 不从 Manifesto 推导特定 Scrum/Kanban implementation；
- 不把“working software”误读为 documentation/evidence 不重要。

**状态：历史上重要、仍有解释力的 primary source，选择性采用。**

---

## 6. Google Engineering Practices — Small CLs

URL：

https://google.github.io/eng-practices/review/developer/small-cls.html

访问：2026-09-06。

### 实际检查

页面明确说明 small/simple changes 通常：

- review 更快、更彻底；
- 更容易 reasoning about impact；
- rejected 时浪费更少；
- merge/rollback 更容易；
- design 更容易逐步 polish。

它同时说明“small”不是一个绝对 LOC rule，而是一个 self-contained change，并指出 reviewer 的 context 与作者不同。

### 课程吸收

这和 M10 非常一致，因此 Process 旁支用它支持：

> small batch 的真正价值是保持 semantic scope bounded，让 reviewer 可以恢复 correctness argument，而不是追求某个固定行数。

### 不照搬

Google 页面提到 100 行通常 reasonable、1000 行通常太大，但本课程**不采用这些数字作为 gate**。语言、generated code、mechanical refactor、test fixture 等场景差异太大。

---

## 7. Kanban sources — WIP / flow

Kanban University 官方 Guide：

https://kanban.university/kanban-guide/

辅助核查（Microsoft Learn）：

https://learn.microsoft.com/en-us/devops/plan/what-is-kanban

访问：2026-09-06。

### 实际检查

Kanban University 当前 guide 把：

- limiting Work in Progress；
- managing flow；
- pull；
- balancing utilization and flow

作为明确实践，并指出过高 utilization/WIP 会带来 delay/context switching。

Microsoft 当前文档也以 software delivery 语境解释 WIP limit、pull、lead/cycle time 和 bottleneck。

### 课程吸收

Process 旁支使用 WIP 不是为了教 Kanban board，而是帮助解释：

- Agent 产生的未 review patch 也是 inventory/WIP；
- implementation capacity 增长不等于 review/integration capacity 增长；
- bottleneck 已经在下游时，继续 push 新 patch 可能拉长 lead time。

### 不照搬

- 不规定固定 WIP number；
- 不要求看板；
- 不把“降低 WIP”写成所有情景单调最优；
- 不把任何 Kanban vendor/tool 当课程依赖。

---

## 8. ISO/IEC 25010:2023 — Product quality model

官方 ISO 页面：

https://www.iso.org/standard/78176.html

访问：2026-09-06。

版本：**ISO/IEC 25010:2023, Edition 2, published 2023-11**。

### 实际检查

官方摘要明确说明该标准定义 product quality model，由 **9 个 characteristics** 及 subcharacteristics 组成，用于 requirements specification、design objectives、testing objectives、quality control、acceptance criteria 和 product-quality measurement。

当前 2023 edition 的九个 characteristics 为：

- Functional suitability；
- Performance efficiency；
- Compatibility；
- Interaction capability；
- Reliability；
- Security；
- Maintainability；
- Flexibility；
- Safety。

### 课程吸收

[Software Quality](../extensions/software-quality-models.md) 只把这个模型作为**遗漏检查和共同语言**：quality 不是一个分数，同一 design 会同时影响多个 attribute。

还吸收了一个更重要的用法：quality model 可以帮助 requirements/design/testing/acceptance 对齐，而不是“上线前 QA 打分”。

### 不照搬

- 不要求背 subcharacteristics；
- 不建立 9 维打分表；
- 不给 attribute 随意分配权重并计算“总质量”；
- 不声称 ISO model 覆盖所有 domain-specific quality concern。

**状态：选择性采用，作为 quality vocabulary。**

---

## 9. OWASP Cheat Sheet — Threat Modeling

URL：

https://cheatsheetseries.owasp.org/cheatsheets/Threat_Modeling_Cheat_Sheet.html

访问：2026-09-06。

### 实际检查

当前页面把 threat modeling 描述为持续维护的 structured process，而不是一次性的 security workshop，并使用四个核心问题：

1. What are we working on?
2. What can go wrong?
3. What are we going to do about it?
4. Did we do a good enough job?

页面还强调 system modeling 应识别 data flows、processes、stores、external entities 和 trust boundaries，并把 STRIDE 作为一个 threat-identification technique，而非唯一方法。

### 课程吸收

[Security Engineering](../extensions/security-engineering.md) 采用：

- system model + adversarial lens；
- asset/trust boundary/data flow；
- threat → response/mitigation → verification；
- threat model 需要随着系统更新；
- STRIDE 只作为 prompts，不是 security proof。

这与 M09/M12 的 system modeling 很自然地连接。

### 不照搬

- 不要求所有项目使用 STRIDE；
- 不列完整 attack taxonomy；
- 不把 threat ranking 公式化成可靠概率计算；
- 不声称一次 threat-model review 就证明系统安全。

**状态：主干采用（旁支层的 threat-modeling entry point）。**

---

## 10. NIST SP 800-218 — Secure Software Development Framework

SSDF project：

https://csrc.nist.gov/projects/ssdf

v1.1 final：

https://csrc.nist.gov/pubs/sp/800/218/final

访问：2026-09-06。

### 版本状态

截至本轮审计：

- **SP 800-218 v1.1**：Final，2022-02；
- **SP 800-218 Rev. 1 / v1.2**：2025-12 发布 initial public draft，仍不是 final。

因此课程对稳定 normative claim 使用 **v1.1 final**；只记录 v1.2 正在更新，不把 draft 写成已经发布的最终要求。

### 实际检查

v1.1 / project 页面强调 secure development practice 应进入整个 SDLC。v1.1 更新项明确包含：

- secure software development environment；
- documented security requirements；
- tracking security risks / design decisions；
- collecting/sharing provenance data for components of releases。

### 课程吸收

Security/Configuration 旁支用它支持：

- dependency/build/release 是 trust/supply-chain boundary；
- provenance 不只是 debugging metadata，也服务 security assurance；
- secure requirement/design/evidence 应贯穿 lifecycle。

### 不照搬

- 不要求个人/小型项目完整实施 NIST SSDF；
- 不把 federal acquisition context 直接套到所有软件；
- 不把 SBOM/attestation 当成本课程默认基础设施。

**状态：选择性采用；final/draft 状态严格区分。**

---

## 11. ACM Code of Ethics and Professional Conduct

官方页面/PDF：

https://www.acm.org/code-of-ethics

访问：2026-09-06。

当前 Code：2018 revision（官方仍作为当前 ACM Code 使用）。

### 实际检查

重点检查：

- public good / avoid harm；
- honesty / trustworthiness；
- respect work, copyright, patent, trade secret, license；
- privacy；
- confidentiality；
- professional competence / quality；
- rules / responsibilities of leaders。

特别与本课程相关的是：privacy 不只是 secrecy，还包括 legitimate purpose、data minimization、retention 和 protection；professional responsibility 也不是“做完 assigned task”这么窄。

### 课程吸收

[Professional Practice](../extensions/professional-practice-ethics-law.md) 使用：

- implementation delegation 不自动转移 responsibility；
- risk/limitation 应诚实沟通；
- privacy/confidentiality 是 information-flow/design concern；
- 对外部 work/license 应保留 provenance 与 attribution awareness。

### 不照搬

- 不把 Code 当成算法；
- 不从伦理原则直接推出具体法律结论；
- 不把某个行业/司法辖区的义务写成通用规则。

**状态：主干采用（professional responsibility 的规范性背景），但保留情境判断。**

---

## 12. GitHub Docs — Licensing a repository

URL：

https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository

访问：2026-09-06。

### 实际检查

GitHub 文档明确提醒：公开 repository 若要让他人自由使用、修改、分发，需要适当 license；**没有 license 不等于自动开源许可**。

### 课程吸收

Professional Practice 旁支只保留最低限度工程提醒：

> public visibility != permission to copy/modify/distribute；Agent 找到可见代码时不能把 provenance/license 一起忽略。

### 限制

GitHub Docs 不是法律意见，也不能覆盖具体 license compatibility。真实产品中的复杂 copyright/license 问题应检查具体 license、组织 policy，并在需要时咨询专业人员。

**状态：用于纠正常见误解，不作为法律课程来源。**

---

## 13. C4 Model — official site

首页：

https://c4model.com/

Abstractions：

https://c4model.com/abstractions

Diagrams：

https://c4model.com/diagrams

Review checklist：

https://c4model.com/diagrams/checklist

访问：2026-09-06。

### 实际检查

C4 官方将自己定位为 architecture diagramming 的 abstraction-first 方法：

- software system；
- container；
- component；
- code；

并明确说明 notation-independent / tooling-independent。不同 diagram level 对应不同 audience/question；官方也说不必画全四层，很多团队 context/container 已足够。

Review checklist 强调：title、diagram type、scope、element meaning、relationship label/direction 等必须能被读者理解。

### 课程吸收

[Models、Notation 与 UML](../extensions/models-notation-and-uml.md) 使用：

- 不混 abstraction level；
- diagram 必须声明 scope/question；
- relationship 应有语义；
- 只画真正有价值的 view；
- tooling/notation 不是核心。

### 不照搬

- 不要求课程统一使用 C4；
- 不要求四层图全画；
- 不用 C4 替代 state machine、sequence/data-flow/compatibility matrix 等更适合具体问题的模型。

**状态：选择性采用（architecture visualization discipline）。**

---

## 14. 为什么没有为每个旁支找一本“主教材”

本轮刻意没有做：

```text
Requirements -> 一本经典书
SCM -> 一本经典书
Process -> 一本经典书
...
```

原因有两个。

第一，这些旁支的目标不是再造八门小课，只需要给 M00–M13 补一个可靠 mental model。SWEBOK/current standards/primary practice documents 已经足以验证“这个问题存在且范围是什么”。

第二，很多经典书在某一历史组织形态下非常强，但把完整方法移植到 Agent-era 小团队可能引入不必要 ceremony。后续如果某个旁支扩展到独立 lab/case study，再对该主题做更深的 book/paper audit 更合适。

---

## 15. 本轮明确拒绝的推论

材料审计后，课程仍然**不接受**下面这些推论：

- “SWEBOK 有一个 KA，所以本课程必须有一个 module。”
- “某个 standard 有 quality/security taxonomy，所以逐项打勾就能证明 correctness。”
- “Agile 重视 working software，所以 documentation/modeling 不重要。”
- “Kanban 限 WIP，所以所有团队都应该用同一个 board/limit。”
- “Google 建议 small CL，所以 100 行是 universal threshold。”
- “C4/UML 是 modeling language，所以 architecture 图越多越工程化。”
- “用了 NIST/OWASP checklist，所以系统已经 secure。”
- “公开 GitHub repository 可以被 Agent 自由复制。”
- “AI 已经成为 SE core，所以 Requirements/Management/Quality/Communication 会自然消失。”

本轮真正支持的是更窄的结论：

> **传统 Software Engineering 中有一批问题仍然真实存在；应该把它们重新连接到 boundary、contract、invariant、change、evidence 和 authority，而不是恢复旧课程的术语/流程中心主义。**
