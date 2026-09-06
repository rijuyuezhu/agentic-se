# Security Engineering：从 trust boundary 到 Agent authority

M09 会问：状态由谁拥有？failure 会穿过哪些边界？M12 又会问：Agent 有什么 capability、获得了什么 permission、真正拥有哪一种 decision authority？

Security Engineering 把这些问题放进一个更强的假设里：**系统不仅会偶然失败，还可能遇到主动寻找边界漏洞的人。**

一旦加入 adversary，很多“方便”的设计会改变性质。一个 debug endpoint 不再只是多一个维护面；一个可以读取任意 workspace 的 Agent tool 不再只是功能强；一个来自 dependency 的 build script 不再只是自动化。

这篇旁支不试图把你训练成安全工程师。它只补一套足以让普通 software change 不忽略安全边界的 reasoning。

## 1. Security requirement 不是“最后做一次扫描”

如果系统要保护资产，安全约束会影响 requirement、architecture、API、deployment 和 operations，而不是只影响最后的 testing。

例如一个 remote worker 的注册流程必须回答：

- 什么实体可以成为 worker？
- controller 怎样知道它是谁？
- credential 能做什么？
- credential 泄露后 blast radius 多大？
- worker 离线七天后重新上线，什么身份状态仍然有效？
- 一个被撤销的 worker 能否继续使用旧 token？

这些问题决定 protocol 和 state machine。等实现完成后再跑 vulnerability scanner，无法补回一个根本错误的 trust model。

## 2. 先说 Asset：到底什么值得保护

“系统要安全”太抽象。先问什么资产的损失会产生真实 consequence。

资产可能是：

- user data；
- credential / signing key；
- source code；
- build/release integrity；
- billing authority；
- model weights；
- availability；
- audit trail；
- human decision authority。

最后一项在 Agent 系统里尤其重要。如果一个 Agent 只能写 branch，和它可以 merge、publish、deploy、rotate secret，风险边界完全不同。

Asset list 不需要 exhaustive；它的作用是让 threat discussion 不再漂浮。

## 3. Trust boundary：在哪里从“可以相信”变成“必须验证”

Trust boundary 不是网络边界的同义词。

它可以出现在：

```text
browser -> API
service -> database
controller -> remote worker
repo -> third-party build action
Agent -> MCP/tool server
untrusted issue text -> shell command
student build -> instructor-only content
```

每穿过一个 boundary，都应该重新问：

- 对方身份是否可信？
- 输入是否可能恶意构造？
- 当前 caller 被授权做什么？
- 数据是否需要保密/完整性保护？
- failure 是否会泄露更多 capability？

这和 M04 的 boundary design 很接近，只是 adversary 会主动寻找你没有验证的 assumption。

## 4. Threat modeling：把 system model 换成 adversarial lens

OWASP 的 threat-modeling guidance 用四个很朴素的问题组织流程：

1. 我们在构建/分析什么？
2. 什么可能出错？
3. 我们准备怎么处理？
4. 我们做得够好吗？

这套问题和本课程非常兼容。

第一步仍然是 system modeling：data flow、process、store、external entity、trust boundary。区别是第二步不只问 crash/race，而会问一个有动机的攻击者怎样利用这些 flow。

例如普通 reliability review 会问：

> network timeout 后 retry 会不会重复执行？

security review 还会问：

> attacker 能否故意制造 timeout，让系统反复执行昂贵操作或放大 side effect？

同一个机制，在 adversarial environment 下多了一层 failure source。

## 5. STRIDE 是 prompt list，不是安全证明

OWASP 使用 STRIDE 作为一个常见 threat-identification 结构：spoofing、tampering、repudiation、information disclosure、denial of service、elevation of privilege。

它很适合帮助初学者系统地问“还有哪类攻击没想到”，但不要把六项打勾当作 threat model 完成。

Threat model 仍然必须绑定具体系统：

- 哪个 asset；
- 哪个 actor；
- 哪个 trust boundary；
- 哪条 data/control flow；
- 哪个 plausible attack；
- 什么 consequence；
- 什么 mitigation/evidence。

如果一个 STRIDE 表完全不引用当前 architecture，它和脱离代码的 generic checklist 一样容易失效。

## 6. Least Privilege：能力只给到完成任务所需的范围

Least privilege 的工程意义很直接：一个 component、human 或 Agent 只拥有完成其职责所必需的 capability，并尽量限制 scope 和 duration。

例如 remote worker 的职责是领取任务并回传结果，它未必需要：

- 直接写 controller database；
- 修改其他 worker identity；
- 发布 release；
- 读取所有用户 secret。

如果一个 Agent 只需要改 docs，就不应为了方便给它 production deploy credential。

这不是因为我们假设 Agent 一定恶意。正常 bug、prompt injection、错误 shell command、dependency compromise 都可能把过宽 permission 变成更大 consequence。

因此：

```text
capability
!=
permission
!=
authority
```

M12 的三层区分同时也是 security design。

## 7. Authentication、Authorization、Authority 不要混在一起

### Authentication

你是谁？例如这个 remote worker 是否真的是之前注册的 device。

### Authorization

这个 identity 根据 policy 被允许执行什么操作？

### Engineering authority

即使技术上允许调用 API，这个 actor 是否有权改变业务/SLO/public contract？

一个 CI bot 可以被授权 push release tag，但不代表它有权决定把 compatibility window 从 90 天改成 7 天。一个 Agent 有文件写权限，也不代表它能把 failing test 删除后宣布 contract 改了。

安全系统通常直接 enforce 前两层；本课程还要求 process/human governance 明确第三层。

## 8. Secure Failure：失败时不要意外扩大权限

M07/M11 已经讨论 fail-open / fail-closed 的一般 trade-off。在 security 里要更具体。

例如 auth service 暂时不可用时：

- 默认允许所有请求可以保护 availability，却破坏 access control；
- 默认拒绝所有请求保护 authorization，却可能造成 outage。

没有一个跨系统的永恒答案。正确选择取决于 asset、operation 和 consequence。

真正的纪律是：**failure semantics 必须是设计的一部分，不能由异常处理代码偶然决定。**

## 9. Dependency 和 Supply Chain 也是 trust boundary

`pip install`、`npm install`、GitHub Action、container base image、compiler plugin 都可能在 build/runtime 中获得执行能力。

NIST SSDF 把第三方 component provenance、secure development environment、release integrity 等放入 secure software development practice，就是因为最终 artifact 的安全性不只来自你写的 source。

普通项目不需要立刻建设完整 SBOM/attestation infrastructure。但至少应知道：

- dependency 来自哪里；
- version 怎样被固定/升级；
- install/build 阶段会执行什么；
- compromise 后能访问哪些 credential/artifact；
- release 是否能追溯到 source 和 component set。

这与 [Configuration、Baseline 与 Release](configuration-baselines-and-release.md) 是同一条 supply-chain evidence 链。

## 10. Secrets 不是普通 configuration

Secret 既是 configuration，又具有额外的 confidentiality 和 rotation/lifetime requirement。

高风险 anti-pattern 包括：

- 把真实 credential 写进 repo；
- 把 secret 复制进 prompt/issue/log；
- 给 Agent 提供超出任务需要的全局 token；
- 在错误输出中打印 authorization header；
- credential 撤销后长期有效的 cached session 没有策略。

一个好的 secret boundary 应让系统能回答：谁可以读取、谁可以使用、能访问什么、何时过期、如何撤销，以及 audit 能记录什么而不泄露 secret 本身。

## 11. Prompt Injection 不是“模型问题”而已

当 Agent 读取 issue、网页、README、tool output，再拥有 shell/API capability 时，untrusted text 可能试图改变它的行动。

这和传统 injection 的共同点是：**把数据误当成了 authority-bearing instruction。**

因此 Agent harness 需要：

- 明确 instruction provenance / precedence；
- 对外部内容默认视为 data；
- tool server 自己 enforce authorization，而不是相信模型“会遵守”；
- destructive action 有额外 gate；
- secret 不进入不必要的 context；
- high-consequence decision 需要独立 human/系统 policy。

“模型很聪明”不能替代 trust boundary。

## 12. Security evidence 要和 threat 对齐

一次安全扫描通过，只能说明这个工具在它能识别的 pattern 上没有发现问题。

更完整的 claim 链应该是：

```text
asset + threat
→ security requirement
→ design mitigation
→ implementation/control
→ verification evidence
```

例如：

```text
Threat:
  stolen worker credential impersonates worker indefinitely

Requirement:
  credential is revocable and scoped to one worker identity

Design:
  server-side identity record + rotatable token

Evidence:
  revoked credential fails; re-enrollment uses new credential;
  other worker identity cannot be mutated
```

这比“run SAST”更接近 security correctness argument。

## 13. Security 和 Usability/Availability/Cost 也会 trade off

安全不是无限提高越好。

一个每次操作都要求人工审批的系统也许非常难被滥用，但可能让正常运维在事故时无法及时恢复。一个每小时旋转 credential 的方案也许减少暴露窗口，却可能增加复杂 failure mode。

因此 security decision 仍然要回到 risk：asset value、threat plausibility、impact、mitigation cost、operational consequence。

这也是为什么安全 requirement 需要有 authority 的风险决策，而不是让 implementation Agent 自动选择“最安全”的行为。

## 14. 一个最小 Security Review

对一个新的边界、tool 或 integration，可以先问：

1. 最重要的 asset 是什么？
2. 新增/改变了哪些 trust boundary 和 data/control flow？
3. 哪些输入或 actor 不能默认可信？
4. 当前 identity 怎样 authentication？authorization 到什么 scope？
5. permission 是否超过职责需要？
6. dependency/tool 如果被 compromise，blast radius 多大？
7. failure 时会不会意外放宽权限或泄露信息？
8. mitigation 用什么 evidence 验证？
9. 哪些 residual risk 需要 human/security authority 接受？

对于小工具，答案可能很短。问题的价值是防止“这只是内部功能”成为不做 threat reasoning 的借口。

## 15. 这篇旁支不教什么

这里没有系统讲密码学、web vulnerability、penetration testing、SOC、合规框架或完整 secure SDLC。遇到安全敏感系统，应学习专门材料并请有经验的安全人员参与。

本课程只保留一个最重要的连接：**system model 一旦加入 adversary，boundary、authority、dependency、artifact provenance 和 failure semantics 都必须重新检查。Agent 不是这个规则的例外。**

材料来源与取舍见 [`reading-notes/extensions-source-audit.md`](../reading-notes/extensions-source-audit.md)。
