# Professional Practice：责任、沟通、隐私与许可

Coding agent 能生成一个 patch，不能回答一个更根本的问题：**如果这个 patch 造成损害，谁对“为什么允许它进入系统”负责？**

软件工程不只是技术能力，也是一种有后果的专业活动。系统会处理用户数据、影响业务决策、控制资源、改变公共服务，有时还会进入医疗、交通、金融等高风险环境。Professional Practice 最值得本课程保留的内容，就是让工程判断不仅对“代码能不能工作”负责，也对风险、沟通、权限和影响负责。

这篇旁支不是法律意见，也不是职业伦理考试。它只讨论几个会直接改变真实 software change 决策的问题。

## 1. Implementation 可以委托，responsibility 不能自动委托

假设你告诉 Agent：

> 修复这个并发 bug，测试通过后直接发布。

Agent 成功写出 patch、通过 CI，也自动触发 release。后来才发现它改变了一个旧 client 依赖的 error semantic。

“是 Agent 改的”并不能回答：

- 谁定义了允许的 scope？
- 谁有 authority 改 public behavior？
- 谁检查了 compatibility evidence？
- 谁授权 release？
- 哪个风险在何时被接受？

Agent 可以承担 implementation role，但组织仍然需要明确 human/system authority。M12 的 `capability / permission / authority` 区分在这里变成责任边界。

如果一个流程无法回答“最后是谁基于什么 evidence 接受了这个 change”，那么自动化程度越高，责任链越模糊。

## 2. Professional judgment 包含“不要假装知道”

工程师经常受到一种隐形压力：issue 已经排期，manager 在等 estimate，Agent 也给出了 confident plan，于是最好不要说“还不知道”。

但对高 consequence change，明确暴露 uncertainty 是专业行为的一部分。

例如：

> 我们确认新 server 能读旧 schema，但尚未验证 frozen v1 binary 是否能读 expand-only schema。在这个事实确认前，不能承诺任意时刻可 rollback。

这句话没有立即给出解决方案，却比“应该没问题”更有价值，因为它让 decision maker 知道当前 evidence boundary。

Professional communication 不要求悲观，而要求**claim 与 evidence 对齐**。

## 3. Risk communication：不要把重要 qualifier 藏在脚注里

技术团队经常把风险写成：

> tests passed，建议上线；另有少量兼容风险。

如果“少量兼容风险”其实意味着旧客户端可能损坏，这种摘要会系统性误导决策。

高质量 risk communication 应让 consequence 可见：

- 什么事实已确认；
- 什么仍是假设；
- 失败影响谁；
- 是否可逆；
- 需要谁接受 residual risk；
- 哪个 observation 会触发 stop/rollback。

这也是为什么 M10 要按 severity、consequence、reproducer 写 review finding，而不是只给 “LGTM / needs work”。

## 4. 不要批准你无法合理支持的 claim

ACM/IEEE 的专业伦理材料反复强调 competence、quality、public interest、honesty 和披露风险。把它转成日常工程语言，就是：

> **不要因为流程要求一个 yes/no，就把证据不足伪装成确定性。**

例如：

- 没跑过 production-like load，就不要声称“性能问题已解决”；
- 只测试当前 binary，就不要声称“向后兼容”；
- 只看 Agent summary，就不要声称“独立 review 已完成”；
- 没检查 license，就不要声称“可以直接复制进产品”；
- 没有 threat model，就不要把“用了 sandbox”写成“安全”。

Professional judgment 很多时候表现为**拒绝过度 claim**。

## 5. Privacy：数据最小化也是 architecture decision

隐私常被误解成“加一条 privacy policy”。工程上更早的问题是：系统到底为什么要收集、保留、复制这些数据？

ACM Code of Ethics 对 privacy 的讨论强调 legitimate purpose、data minimization、retention、access、correction 和保护免受未授权披露。

映射到系统设计，可以问：

- 为了这个 feature，我们真的需要把完整用户内容发送给外部 Agent/service 吗？
- log 是否记录了原本只需要 request id 的敏感 payload？
- debug artifact 会保存多久？
- test fixture 是否复制了真实用户数据？
- telemetry label 是否意外形成高敏感/高基数用户标识？
- data merge 是否产生原本不存在的新隐私风险？

这些不是“上线后合规再看”的问题。它们会直接决定 data flow 和 retention model。

## 6. Confidentiality：有权限看到，不等于可以到处复制

工程师经常能访问 source、incident、customer data、credential、internal design。Agent workflow 又增加了新的复制路径：prompt、tool log、external API、session transcript、benchmark artifact。

因此一个实用原则是：

> **只把任务真正需要的数据放进相应 context。**

如果 Agent 只需要分析 schema shape，就不应顺手把生产数据 dump 给它；如果 reviewer 只需要 patch 和 deterministic reproducer，就不应默认附带用户敏感日志。

Confidentiality 不是单纯“不能泄密”，而是 information boundary design。

## 7. Licensing：公开可见不等于可任意复制

一个常见误区是：

> GitHub 上能看见，所以可以复制、修改、分发。

不是这样。软件 license 决定他人获得了哪些使用、修改、分发权限以及需要满足哪些条件。GitHub 官方文档也明确提醒：没有 license 时，并不会因为 repository 公开就自动获得开源许可。

工程上至少要区分：

- code 是否有明确 license；
- 当前使用方式是否触发相应条件；
- attribution/notice/source-distribution 等义务是否需要保留；
- dependency license 是否与交付方式兼容；
- 公司/研究机构是否有额外 policy。

具体 license interpretation 可能需要法律或合规专业人员。本课程不会教你自己做复杂法律判断。

真正的工程纪律是：**不要让 Agent 因为“找到了可用代码”就把 provenance 和许可问题一起抹掉。**

## 8. Generated code 仍然需要 provenance

Agent 生成代码时，团队至少应该知道：

- 哪个 task/context 产生了它；
- 是否引用或搬运了外部材料；
- 是否存在需要保留的 attribution/license；
- 谁 review 了最终 patch；
- 最终 acceptance 依据是什么。

这里的 provenance 不一定要保存完整模型内部过程。重点是让最终 artifact 的来源和 review responsibility 不至于完全不可追踪。

如果组织对生成式工具有专门 IP/privacy policy，Agent workflow 必须服从那个 policy，而不是让模型自己判断是否可以发送/复制内容。

## 9. Safety-critical / high-impact change 需要更强的 escalation

并不是所有软件都需要同样的 professional control。

一个个人 CLI 的错误可能只让自己多跑一次命令；医疗、交通、金融控制、安全基础设施的错误可能伤害他人或造成大规模损失。

因此本课程的“按 consequence 调整 rigor”在这里尤其重要：

- 更强 independent review；
- 更明确 decision authority；
- 更严格 evidence；
- 更小 rollout blast radius；
- 更完整 audit trail；
- 必要时引入 domain/safety/security/legal expert。

不要把一套个人项目 workflow 直接推广到高风险系统。

## 10. Disagreement 也应该成为 engineering artifact

真实团队里，reviewer 和 author 会不同意。

低质量处理是：

```text
author: 我觉得没问题
reviewer: 我觉得有问题
manager: 先 merge 再说
```

更专业的做法是把 disagreement 变成可检验的对象：

```text
Claim:
  old client remains compatible

Author evidence:
  source inspection + current integration test

Reviewer concern:
  frozen v1 reader rejects unknown enum

Decision needed:
  compatibility window includes frozen v1 or not?

Authority:
  API owner
```

这会让冲突从人格/资历问题回到 contract、evidence 和 authority。

## 11. “用户要求的”也不是自动免责

Stakeholder request 很重要，但工程师不能把所有责任推回用户。

用户可能要求：

- 默认关闭 security check；
- 保存所有历史数据“以后可能有用”；
- 绕过 safety gate 以赶进度；
- 隐瞒 known limitation；
- 使用来源不明的第三方代码。

工程师至少有责任把 consequence 说清楚、记录风险，并在超出可接受边界时升级或拒绝。具体义务随组织、行业和法律环境不同，本课程不提供统一法律结论。

但“需求写在 ticket 里”不是独立 engineering judgment 的替代品。

## 12. 对 Agent 怎么建立责任边界

一个实用 Agent governance 可以很轻量：

### Agent 可以独立做

低 consequence、可逆、可验证的机械工作，例如格式化、局部 refactor、只读分析、生成测试候选。

### Agent 可以提议，但需要人决定

public contract、SLO、security policy、data retention、migration window、license-sensitive reuse、high-impact rollout。

### Agent 默认不应独立做

deploy production、删除重要数据、旋转/导出高权限 credential、接受 residual safety/security risk、代表组织作法律结论。

具体边界可以因项目改变，但必须是显式 policy，而不是“模型应该知道分寸”。

## 13. 一个 Professional Review

对高 consequence change，除了技术 checklist，还可以问：

1. 谁会受到这个 change 的影响，包括看不到代码的人？
2. 当前 claim 是否诚实反映 evidence 和 uncertainty？
3. 是否存在 privacy/confidentiality/data-minimization 问题？
4. 外部代码、模型、数据和 dependency 的 provenance/license 是否清楚？
5. 谁有 authority 接受 residual risk？
6. 如果 reviewer 不同意，disagreement 是否被写成可检验的 claim？
7. Agent 自动化是否模糊了最终 human/accountable owner？

## 14. 这篇旁支不教什么

这里不是法律课程，也不提供某个司法辖区的 copyright、privacy、employment 或 liability 结论。遇到真实法律/合规问题，应咨询合适的专业人员和组织 policy。

本课程只保留一个工程原则：**越是能把 implementation 自动化，越需要把 responsibility、risk communication、information boundary 和 decision authority 明确化。**

材料来源与取舍见 [`reading-notes/extensions-source-audit.md`](../reading-notes/extensions-source-audit.md)。
