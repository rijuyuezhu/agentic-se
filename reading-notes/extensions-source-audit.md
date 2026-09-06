# Extensions Source Audit — 传统 Software Engineering 旁支

> 本文件记录 `extensions/` 真正检查过的来源、访问时状态、课程吸收的 claim 和明确不照搬的部分。
>
> 审计日期：**2026-09-06**。
>
> 目标不是证明“传统 SE 仍然正确”，而是回答：**哪些长期存在的 Software Engineering 问题仍会直接影响真实代码库和 Agent-assisted development 的工程判断？**

## 0. 审计原则

本轮遵循仓库已有 `MATERIALS_REVIEW.md` 的标准，并额外加三条约束。

第一，**knowledge map 不是教学优先级**。SWEBOK 可以证明一个领域在软件工程共同知识里有稳定位置，但不能据此推出它应该占本课程一章。

第二，**curriculum 目录只能证明“还在教”，不能证明“怎样教”**。因此这轮除了看 CMU MSE 的 requirements / plan of study，还实际打开当前 Course Offerings 所链接的最近 syllabus，检查 assignment、in-class activity、grading/rubric 和 learn-by-doing 结构。大学课程仍然只作为教学设计 sanity check，不自动升级成课程权威。

第三，**会变化的网页必须记录日期和版本状态**。尤其 NIST SSDF、SWEBOK 和当前 university curriculum，未来同一 URL 可能变化。

---

## 1. IEEE Computer Society — SWEBOK Guide v4.0a

官方主页：

https://www.computer.org/education/bodies-of-knowledge/software-engineering

官方 Topics / Table of Contents：

https://www.computer.org/education/bodies-of-knowledge/software-engineering/topics

官方 v4.0a PDF：

https://ieeecs-media.computer.org/media/education/swebok/swebok-v4.pdf

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

这一项没有只看 Topics 页。我们进一步检查了 v4.0a PDF 的 **Chapter 15 — Software Engineering Economics** 正文。

与旁支直接相关的内容包括：

- engineering decision-making 明确要求先理解真实问题、识别可行 alternatives、定义 selection criteria、比较并在实施后 monitor outcome；
- replacement decision 把 sunk cost 列为必须额外考虑的因素；相关概念部分明确区分 sunk cost、opportunity cost，并给出 software TCO 的定义；
- multiple-attribute decision-making 专门处理不能都换算成 money 的多个 criteria，并区分 compensatory / non-compensatory techniques；
- estimation 一节明确说 estimate 天生带 uncertainty，质量要求是“足以支持正确 decision”，而不是假装精确；
- decisions under risk 包含 expected value of perfect information，用来说明信息本身可能有决策价值。

**课程吸收：** sunk cost、opportunity cost、TCO、multiple criteria、estimation uncertainty 和“信息可能改变 decision”都有直接来源依据。`reversibility → option value`、把 probe 当成轻量 information-buying action，以及把 Agent review capacity 视作稀缺资源，则不是 SWEBOK 原句，会在后面的 claim provenance 中明确标成 course synthesis / adaptation。

**不照搬：** 不教授完整财务、cash-flow、MARR、EVM，也不把 expected-value / AHP 等计算技术变成必修；旁支只保留会改变 software change 判断的部分。

### 对 SWEBOK 的总体判断

**状态：选择性采用，作为 gap map，不作为课程权威。**

SWEBOK 最有价值的是提醒我们：传统 SE 研究的对象比 coding/design/testing 更宽。它不应该直接决定本课程课时，更不能把 consensus topic list 变成 universal best practices。

这就是为什么 `reading-notes/traditional-se-gap-map.md` 对 Architecture/Testing/Maintenance/Operations 判为“已覆盖”，而不是继续为每个 KA 增加旁支。

---

## 2. Carnegie Mellon MSE — 当前 curriculum 与实际教学方式 sanity check

Program requirements：

https://mse.s3d.cmu.edu/applicants/mse-as/requirements.html

Plan of Study：

https://mse.s3d.cmu.edu/applicants/mse-as/plan.html

Current Course Offerings（页面说明 syllabus 链接指向最近可用版本）：

https://mse.s3d.cmu.edu/applicants/course-offerings.html

本轮实际打开的 syllabus：

- 17-626 Requirements for Information Systems, Fall 2025: https://mse.s3d.cmu.edu/0_documents/syllabi/fa2025/17626.pdf
- 17-643 Quality Management, Spring 2025: https://mse.s3d.cmu.edu/courses/0_syllabi/17643-quality-management.pdf
- 17-622 Agile Methods, Fall 2025: https://mse.s3d.cmu.edu/0_documents/syllabi/fa2025/17622.pdf

访问：2026-09-06。

### 先检查 curriculum：AI 进 core 后，哪些问题还保留

当前 on-campus MSE 从 Fall 2027 起把 Software Engineering with AI 与 Specifications、Requirements、Management、Quality、Architecture/Design、Communications 同时列为 core。Plan of Study 还把 gathering / analyzing / prioritizing requirements from a real-world industrial customer、project management、technical/nontechnical communication，以及 human/AI resources 的组合列入 learning outcomes。

这只能支持一个很窄的判断：把 AI 纳入 core，并没有使 Requirements/Management/Quality/Communication 自动消失。它不能证明这些课程的具体教学法适合我们。

### 再检查实际教学：学生到底做什么

**17-626 Requirements** 不是从背 requirement taxonomy 开始。最近公开 syllabus 的学习目标要求学生和潜在用户交互、分析 user/marketing data、识别 requirements conflict/risk，并在 alternatives 间 reconcile。作业让学生从 interview transcript / technical article 中提炼 goals 与 refinements，从 system failure 中识别 obstacles/mitigations，并产出 scenario、persona、activity diagram、use cases；课堂还有 persona/obstacle generation 和 design walkthrough 等活动。也就是说，它训练的是**从不完整 evidence 逐步形成和检验 requirement model**。

**17-643 Quality Management** 也不是单纯列 quality attributes。最近公开 syllabus 强调 scenario-based critical thinking、engineering judgment 和完整论证；每周 assignment 会让学生实际安装/使用 quality tool，再分析结果、解释 trade-off，并把经验连接到 project-level decision。这里值得借鉴的是 **tool result != conclusion，学生必须解释 evidence 对 engineering claim 的意义**。

**17-622 Agile Methods** 明确采用 lecture track + running group assignment 的 learn-by-doing 结构，配合课堂活动、group preparation/results 和 peer evaluation。它证明 process 可以通过实际协作 feedback 来训练，而不是只背方法名；但课程也包含大量 Scrum/Kanban/estimation technique 的具体机制，这些并不因此自动适合本课程主线。

### 本课程吸收的是教学机制，不是 CMU packaging

这三门课共同支持的教学设计启示是：

- 让学生从不完美输入中提炼模型，而不是先给完整答案；
- 让 artifact 被实际使用、walk through、分析和 revision；
- 让工具/diagram/process 产出的结果回到 engineering judgment；
- 训练 conflict、trade-off 和 evidence interpretation，而不是只检查术语记忆。

这与当前 Extensions 的组织方式相容：旁支仍然从 concrete failure/decision problem 出发，再引入传统术语。

### 不照搬

- 不采用 CMU 的学分、grading 或课程顺序；
- 不因为 17-626 使用 persona/use case/activity diagram，就把这些 artifact 变成本课程强制模板；
- 不因为 17-622 教 Scrum/Kanban/planning practice，就把某个 process framework 升级为默认答案；
- 不把 university course existence 或学生作业量当成主题本身正确的理论证据。

**状态：curriculum + teaching-method sanity check，不作为理论权威。**

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

## 4. Economics / Risk — 从高层资源继续追到正文与 research framing

IEEE Software Engineering Management：

https://www.computer.org/resources/software-engineering-management

IEEE Software Engineering Economics course description：

https://www.computer.org/product/education/software-engineering-economics-course/

SEI real-options architecture report：

https://insights.sei.cmu.edu/library/quality-attribute-based-economic-valuation-of-architectural-patterns/

SEI technical-debt research overview：

https://www.sei.cmu.edu/blog/10-years-of-research-in-technical-debt-and-an-agenda-for-the-future/

访问：2026-09-06。

### 实际检查

IEEE Management resource 用来确认 estimation、resource allocation、risk、measurement/monitoring/control 属于 software engineering management 的稳定问题域；Economics course description 则确认这里讨论的是 business context 中的 software engineering decision，而不只是 finance。

具体经济概念不再依赖这两个高层页面：sunk cost、opportunity cost、TCO、multiple-attribute decision、estimate uncertainty 和 information value 以前面的 **SWEBOK v4.0a Chapter 15 正文**为主要依据。

SEI 的 architecture real-options 工作把 architecture pattern 的 future value 解释为 real options：保留未来采取某种 design action 的权利而非义务。它说明“architecture 可以因为保留未来选择而有经济价值”不是本课程凭空发明的方向；但旁支把这个想法简化成 `reversible change → option value`，仍然是**教学性的 course adaptation**，不是要求学生对每个 compatibility bridge 做金融期权定价。

SEI technical-debt research 则把 debt 的核心 consequence 放在未来 change / evolvability cost，而不是“代码不漂亮”。旁支进一步把它具体化成 future change/review/incident cost，是对本课程 M05/M08/M10/M11 语境的 adaptation。

### Claim provenance：来源支持与课程 synthesis 的边界

**直接有来源框架支撑：**

- sunk cost / opportunity cost / TCO / multiple criteria / estimation uncertainty：SWEBOK Chapter 15；
- information can have decision value：SWEBOK decisions-under-risk / EVPI；
- architecture can retain future option value：SEI real-options framing；
- technical debt should be discussed through future change/evolution consequence：SEI technical-debt research。

**课程 synthesis / operationalization：**

- “reversibility 是 option value”：把 SEI 的 architecture-level real-options reasoning 压缩成 change-engineering heuristic；
- “先跑一个便宜 probe，看它是否会改变 decision”：把 information-value 概念接到本课程 evidence loop，不是正式 EVPI 计算；
- “Agent 让 implementation 便宜后，human review / product / security attention 可能成为 bottleneck”：来自 M10/M12 与 process 旁支的系统性推论，不归因给 IEEE/SEI；
- “technical debt 应优先写成 future change/review/incident cost”：是本课程把 technical-debt future-cost frame 落到 review/change engineering 的表达方式。

### 不照搬

没有进入 finance、cash-flow、MARR、EVM、完整 portfolio economics，也不要求 real-options valuation 或 formal EVPI/AHP。这里保留的是 decision frame，而不是经济学计算课程。

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

## 11. Security controls / Agent security — 把 threat model 继续落到 permission surface

NIST SP 800-53 Rev. 5, AC-6 Least Privilege：

https://csrc.nist.gov/pubs/sp/800/53/r5/upd1/final

OWASP Authentication Cheat Sheet：

https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html

OWASP Authorization Cheat Sheet：

https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html

OWASP Secrets Management Cheat Sheet：

https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html

OWASP LLM Prompt Injection Prevention Cheat Sheet：

https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html

OWASP AI Agent Security Cheat Sheet：

https://cheatsheetseries.owasp.org/cheatsheets/AI_Agent_Security_Cheat_Sheet.html

访问：2026-09-06。

### 实际检查

NIST AC-6 的稳定核心是：用户/进程只获得完成 assigned organizational tasks 所必要的 authorized access。旁支据此使用 least privilege，不把“Agent 不是恶意用户”当成扩大权限的理由。

OWASP Authentication / Authorization 两份 cheat sheet 明确把“确认 identity”和“决定该 identity 可访问什么”分开；Authorization guidance 还强调 least privilege / deny-by-default / 每次 request 验证权限。旁支因此可以可靠地区分 authentication 与 authorization。

Secrets Management 把 secret 看成有 lifecycle 的敏感资产，而不是普通 config value，覆盖 creation、storage、access、rotation/revocation 等问题。旁支据此讨论 repo/prompt/log 中的 credential 暴露、scope、expiry 和 revocation。

LLM Prompt Injection Prevention 与 AI Agent Security 则把间接 prompt injection、untrusted external content、tool misuse、excessive permission、sensitive-data exposure 和 high-impact action controls 放在同一个 Agent security surface 上。AI Agent guidance 特别要求工具/权限保持最小化，并强调不能只依赖模型“自觉遵守”安全意图。

### Claim provenance：来源支持与课程 synthesis 的边界

**直接有来源框架支撑：**

- least privilege / narrow permission：NIST AC-6 + OWASP Authorization；
- authentication != authorization：OWASP Authentication / Authorization；
- secret 需要 storage/access/rotation/revocation lifecycle：OWASP Secrets Management；
- untrusted content 可通过 prompt injection 驱动 Agent misuse tools：OWASP LLM Prompt Injection / AI Agent Security；
- tool boundary 应自行 enforce authorization、high-impact action 需要额外 controls：OWASP AI Agent Security，并与 M12 已审计的 Agent-tool guidance 相互印证。

**课程 synthesis / terminology：**

- `capability / permission / engineering authority` 三层模型来自 M12；上述安全资料直接支撑前两层以及 tool boundary，但不会把“谁有权改变 SLO/public contract”命名成同一套 engineering-authority taxonomy；
- “prompt injection 的共同本质之一是把 data 当成 authority-bearing instruction”是本课程用 M12 context/precedence 模型解释 injection 的教学表述，不是 OWASP 原句；
- “sandbox 开着 != 系统安全”是把 process isolation、tool authorization、credential scope 和 semantic authority 合并后的课程结论。

### 不照搬

不把 OWASP/NIST controls 当成 security proof，也不扩展成完整 IAM、cryptography、AppSec 或 penetration-testing 课程。这里的目标只是在普通 software change 中建立足够强的 trust/permission reasoning。

---

## 12. ACM Code of Ethics and Professional Conduct

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

## 13. GitHub Docs — Licensing a repository

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

## 14. C4 Model — official site

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

## 15. OMG UML 2.5.1 — UML 本身到底提供什么

OMG formal specification page：

https://www.omg.org/spec/UML/

Normative UML 2.5.1 PDF：

https://www.omg.org/spec/UML/2.5.1/PDF

访问：2026-09-06。

当前 OMG formal version 是 **UML 2.5.1（2017-12）**。版本较旧并不构成问题：这里检查的是 UML language 本身的稳定 scope，而不是当前工具生态。

### 实际检查

规范不是一张“图标表”。它把 UML 定义成有 formal syntax/semantics 的 modeling language，并把规范主体组织成 structure、behavior，以及 use cases、deployments、information flows 等不同 modeling concern；behavior 部分进一步包含 state machines、activities、interactions 等模型。

这足以支持旁支中最窄的事实性 claim：UML 确实提供 structural / behavioral 的多种 view，sequence/state-machine/component/deployment/class 等 notation 可以在相应问题上表达有用信息。

### 课程吸收与 synthesis 边界

**来源支持：** UML 有丰富的 structural / behavioral modeling vocabulary；不同 diagram/model element 有定义过的语义，而不只是任意 boxes-and-arrows。

**课程 synthesis：** “只学能解决当前 engineering question 的小子集”“如果 prose/code 已更清楚就不要为了规范画图”“model 必须与 source/runtime evidence 交叉验证”都是本课程的 modeling discipline，不是 OMG 要求。

### 不照搬

不要求掌握完整 UML metamodel，不要求统一 notation，也不把 UML artifact 自动视为 source of truth。课程仍然允许 state table、ASCII sequence、dependency graph、C4 view 或其他更适合当前问题的表示。

---

## 16. Claim provenance — 八个旁支的 normative frame 从哪里来

本节不是逐句 bibliography。它记录的是**会改变学生工程判断的主要 normative frame**到底来自已审计来源，还是来自 M00–M13 与这些来源重新组合后的 course synthesis。具体 TaskForge/Agent 例子只是教学实例，不需要伪装成外部事实。

### Requirements / Stakeholders

**Source-backed frame：** 正文 §1–§3、§5–§8 的 requirement/source/stakeholder/elicitation/conflict/validation/traceability/evolution 主要来自 SWEBOK Requirements；当前 CMU 17-626 syllabus 进一步证明这类能力可以通过 interview evidence、goal/refinement、obstacle、scenario/use-case 和 walkthrough 实际训练。

**Course synthesis：** 正文 §4 的 `OBSERVED / REQUESTED / DECIDED` 三分法，以及 §9–§10“先 review issue 是否把 solution 偷换成 requirement，再委托 Agent”的 workflow，是把 M01/M10/M12 的 evidence/authority discipline 移到 requirements 上游。

### Configuration / Baseline / Release

**Source-backed frame：** 正文 §1–§3、§5–§7 的 configuration item、baseline、change tracking/status accounting、release composition/recreation 来自 IEEE SCM；release component provenance 与 secure lifecycle 由 NIST SSDF 支撑。

**Course synthesis：** 正文 §4 把 mixed-version system 写成一组 artifact/version state，§8 把 reproducibility 限定为“先说清要复现什么 property/provenance”，§9–§11 把 rollback/review 问题改写成“哪些 configuration item 真正可逆、证据基于哪个 baseline”，都是 M08/M10/M13 reasoning 的延伸，而不是 IEEE SCM 原句。

### Engineering Risk / Estimation / Economics

**Source-backed frame：** 正文 §2、§4–§11 的 sunk cost、opportunity cost、TCO、multiple-attribute decision、uncertain estimates、information value 主要来自 SWEBOK Chapter 15；architecture future option 来自 SEI real-options；technical debt 的 future change/evolution cost 来自 SEI technical-debt research。

**Course synthesis：** 正文 §3 的 reversible-change option-value heuristic、§7 的 probe-as-information-buying operationalization、§12 的 Agent estimation/attention boundary、§13 的 lightweight decision-record shape，以及 review/product/security attention 可能成为 bottleneck，已在本 audit §4 分开标注。

### Process / Feedback / Team Coordination

**Source-backed frame：** 正文 §2 的 iterative/frequent feedback 来自 Agile Manifesto/Principles；§3 的 small batch 对 review/rollback/feedback 的价值来自 Google Small CLs；§4、§6 以及 §10 中 Kanban/Agile 的基本 reasoning 来自已审计 Kanban/Agile sources。CMU 17-622 只作为“通过 running group work 训练 process feedback”的教学法证据。

**Course synthesis：** 正文 §1 的“process 是 feedback architecture”，§5 的 bottleneck 会移动，§7–§9 的 Agent parallelism/handoff/ownership，§10 把 Waterfall/Scrum/Agile/Kanban 都降为“mechanism 改善什么 feedback/coordination problem”的比较框架，以及 §11–§13 对 metric gaming、small Agent team 和 ceremony 的判断，是把 M10/M12 的 review/coordination constraints 系统化；其中把 Agent-generated PR inventory 当作 WIP 也是这一 synthesis 的具体应用。

### Software Quality

**Source-backed frame：** 正文 §1–§2、§7 中“quality 不等于 testing”、多维 product-quality vocabulary、product/process quality distinction 由 ISO/IEC 25010 与 SWEBOK Quality 支撑；CMU 17-643 syllabus 提供 tool-use → result analysis → engineering judgment 的实际教学例子。

**Course synthesis：** 正文 §3–§6 的 `quality attribute → local scenario/contract → evidence`、trade-off/“model 不是 scoring formula”的教学处理，以及 §8–§9“quality gate 应保护 claim 而不是格式”的 review frame，是把 ISO vocabulary 接到 M01/M03/M09/M11 的 contract/evidence loop。

### Security Engineering

**Source-backed frame：** 正文 §1–§5 的 security-through-lifecycle、asset/trust-boundary/threat-model frame 来自 SWEBOK Security、NIST SSDF 与 OWASP Threat Modeling；§6–§11 的 least privilege/AuthN/AuthZ/secrets/prompt injection/Agent tool security 来自本 audit §11 的 NIST/OWASP sources。

**Course synthesis：** 正文 §7 中 engineering authority 作为 authentication/authorization 之外的第三层、§11 的 `data != authority-bearing instruction` 解释，以及 §12–§14 将 threat-aligned evidence/trade-off/review 接回 M11/M12 Agent harness，是课程自己的组合；这些不会伪装成 OWASP/NIST taxonomy。

### Professional Practice

**Source-backed frame：** 正文 §1–§7、§9、§11 的 responsibility/honesty/risk communication/privacy/confidentiality/intellectual-work/public-good frame 来自 ACM Code；“public repository visibility 不自动授予复制/修改/分发许可”由 GitHub licensing guidance 支撑。

**Course synthesis：** 正文 §1、§8、§10、§12–§13 中“implementation delegation 不自动转移 merge/release/risk-acceptance responsibility”、generated-code provenance awareness、把 disagreement/risk limitation 写成 durable engineering artifact、以及 Agent professional-review boundary，是把 M10/M12 的 acceptance authority 扩展到 professional practice；它们不是对具体法律义务的断言。

### Models / Notation / UML

**Source-backed frame：** 正文 §3–§6 的 structural/behavioral view 与 UML vocabulary 由 SWEBOK/OMG UML 支撑；C4 为 architecture view 的 scope/abstraction/relationship clarity 提供具体实例。

**Course synthesis：** 正文 §1–§2、§7–§12 的 question-first model selection、model 不是天然 source of truth、与 source/runtime evidence 相互校验、current-state/target-state 分离，以及 Agent/model review checklist，是本课程用于防 stale/ceremonial documentation 的规则，而不是 OMG/C4 mandate。

这层 provenance 的目的不是消灭 synthesis。恰恰相反：**允许课程提出自己的 synthesis，但必须让读者知道哪里是来源支持的 frame，哪里是我们基于前面模块作出的教学性组合。**

---

## 17. 为什么没有为每个旁支找一本“主教材”

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

## 18. 本轮明确拒绝的推论

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
