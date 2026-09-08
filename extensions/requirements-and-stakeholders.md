---
id: ext-requirements
type: extension
visibility: student
related: [M01, M10, M12, M13]
---
# Requirements Engineering：contract 从哪里来

M01 从一个重要事实开始：没有 specification，就无法判断 implementation 是否正确。但这句话还留下了一个更上游的问题：**谁来决定 specification 应该是什么？**

想象你维护一个任务执行系统。有人提 issue：

> 网络失败时自动重试三次。

这句话很具体，甚至已经带着实现方向。一个能力很强的 coding agent 可以立刻找到网络调用，加一个 retry loop，再补几条测试。

但工程上真正重要的问题可能还没有被问出来。用户想解决的是偶发连接失败，还是任务最终完成率太低？一次“网络失败”能否证明远端没有执行？任务有没有外部 side effect？三次是谁决定的？重试后用户愿意多等多久？某些任务是否必须禁止自动重试？

如果这些问题没有答案，“自动重试三次”更像一个**被提前选择的 solution**，而不是已经验证过的 requirement。

Requirements Engineering 研究的正是这段从现实问题到可实现 contract 的距离。

它不进入主线，是因为 M01 已经训练了 specification 形成之后的 contract reasoning，而并非每一次 change 都需要重新做 stakeholder discovery；当 issue 本身的来源、冲突或 product/domain authority 不清楚时，再进入这条上游旁支更合适。

## 1. Requirement 不是实现愿望的同义词

一个有用的区分是：

- **need / problem**：现实世界里什么状态需要改善；
- **requirement**：为了满足这个 need，系统必须具有什么可验证的性质或约束；
- **design / implementation choice**：我们准备用什么机制满足 requirement。

三者经常被一句 issue 混在一起。

例如：

> “把 PostgreSQL 换成 Redis，这样 dashboard 必须在 100 ms 内返回。”

这里至少混了两个层次。`dashboard 在给定条件下满足 latency target` 可以成为 requirement；`换 Redis` 是 design proposal。它也许是好方案，也许完全没有解决真实 bottleneck。

这不是要求你对用户说“你不懂需求”。相反，用户提出的 solution 往往包含很重要的 domain knowledge。工程纪律只是要求：**不要在证据不足时，把一个 proposal 自动升级成 must-preserve contract。**

## 2. Stakeholder 不只是“最终用户”

软件的要求通常来自多个来源，而且这些来源不一定同意彼此。

继续看 retry 的例子：最终用户希望任务尽量成功；运维人员担心 retry storm；财务系统 owner 担心重复扣款；安全团队不允许 worker 获得某些 credential；旧 client 依赖现有 error code；业务负责人又要求本周上线。

这些都可能形成真实约束。

所以在接手一个 change 时，第一步不一定是写更详细的 issue，而是先问：

> **哪些人、系统、协议、法规或历史 consumer 有资格对这个行为提出约束？**

这里的 stakeholder 可以是人，也可以通过 durable artifact 表现出来：公开 API、schema、旧 binary、SLO、合同、监管要求、已有自动化流程。M08 所说的 compatibility consumer，其实就是 requirement source 的一种。

## 3. Elicitation：不是“让用户把需求再说清楚一点”

Elicitation 的目标是发现尚未进入 issue 的事实、目标和约束。它不是某一种固定会议。

面对一个真实 change，可以从几类证据出发。

### 观察当前工作

用户口头描述的流程，和系统真实运行的流程可能不同。看真实 request、日志、操作手册、support ticket、失败案例，常常比问“你想要什么功能”更有信息量。

### 追问 concrete scenario

“系统要更可靠”很难实现；“用户提交任务后，即使 worker 在 claim 后重启，也不能让同一个 payment command 被无条件重复执行”就开始形成可分析的场景。

好问题通常会把抽象愿望放进具体环境：

- 谁发起？
- 处于什么前置状态？
- 哪个事件发生？
- 用户随后观察到什么？
- 哪些结果不可接受？

### 读历史，而不只读最新 issue

Git history、旧设计文档、deprecated API、事故记录和兼容测试能告诉你：当前奇怪行为是不是过去某个 decision 的结果。

### 做小型 prototype 或 probe

有时最大的不确定性不是“用户说不清”，而是大家都不知道现有系统能做到什么。一个只读 probe、mock integration 或 disposable prototype 可以先把 unknown 变成 observation，再决定 requirement。

这也是为什么 Requirements Engineering 不等于“写一份长 SRS”。它首先是一种**减少错误假设的调查活动**。

## 4. 把 OBSERVED、REQUESTED、DECIDED 分开

Agent 时代很容易发生一种语义污染：issue 中的句子、当前实现、Agent 的猜测和最终产品决策被写进同一份 plan，过几十分钟后已经没人知道哪条是事实。

一个简单但很有用的做法，是在高风险 change 里明确区分：

| 类别 | 含义 | 例子 |
|---|---|---|
| `OBSERVED` | 从代码、运行或历史中看到的事实 | v1 client 遇到未知状态会 crash |
| `REQUESTED` | stakeholder 当前提出的目标或方案 | “失败时自动重试三次” |
| `CONSTRAINT` | 已有外部/组织边界 | worker 不能获得 payment DB credential |
| `ASSUMPTION` | 暂时用于推进、但尚未证实 | 网络 timeout 通常发生在执行前 |
| `DECISION` | 有 authority 的人已经选定的语义 | opt-in job 采用 at-least-once |
| `UNKNOWN` | 必须调查或升级的问题 | overload 时 submit 的公开返回形状 |

这不是要求所有项目维护一张正式表格。真正重要的是：**不要让不同 epistemic status 的句子在 Agent context 中变成同样可信。**

## 5. Negotiation：冲突不是异常，而是 Requirements 的日常状态

“把所有 stakeholder 的要求都满足”通常不是可行目标。

用户想要零等待，运营希望低资源成本，安全希望更少权限，兼容性要求旧 client 不变，开发者希望实现简单。这些要求可能同时合理，却不能同时最大化。

因此 requirements analysis 不只是找遗漏，还要找：

- contradiction：两条要求不能同时成立；
- tension：可以同时成立，但成本急剧上升；
- dependency：A 只有在 B 先决定后才能定义；
- priority：资源有限时哪个行为必须保护；
- authority：谁有权在冲突中做最终取舍。

这里尤其要避免一种 Agent anti-pattern：

> 发现冲突 → 自己选一个“最合理”的解释 → 继续实现。

如果选择会改变 public behavior、SLO、数据语义、安全边界或业务规则，正确结果常常是 `STOP_AND_ESCALATE`，而不是更聪明地猜。

## 6. Requirement 要能被 validation，而不只是看起来明确

一句 requirement 写得很正式，不代表它已经好到可以实现。

例如：

> 系统应快速、可靠地处理所有任务。

几乎无法据此判断实现是否合格。

更好的 requirement 会逐渐连接到可观察 evidence。例如：

> 对 `automatic_at_least_once` 类任务，在指定负载范围内，99% accepted jobs 在 2 秒内开始第一次 attempt；worker crash 后允许重新 claim，但 stale attempt 不得提交 final state。

这里已经出现了：scope、行为、时间、失败语义和可测量结果。

但也不要走到另一极端：为了“可测量”而给所有东西编一个数字。某些 requirement 更适合用 state invariant、compatibility fixture、review rule、formal property 或 scenario acceptance test 表达。

M03 的核心可以直接搬到这里：**validation method 是 requirement 设计的一部分。** 如果你完全说不出未来凭什么知道它被满足，那么 requirement 很可能还没有成熟。

## 7. Traceability 的目的不是做 Excel 链接墓地

传统 Requirements Engineering 经常强调 traceability。低质量做法是维护一张巨大矩阵，里面每个 REQ-123 都链接到若干 test case，最后没人相信它。

真正有价值的 traceability 回答的是：

> 一个重要行为为什么存在？谁要求它？哪个 design decision 实现它？什么 evidence 保护它？如果它改变，哪些 consumer 和 artifact 要重新检查？

在现代代码库里，这个链可以由多种 artifact 共同承担：

```text
user / operational need
        ↓
issue / decision record
        ↓
public contract or invariant
        ↓
implementation boundary
        ↓
test / probe / production SLI
        ↓
release / migration gate
```

不需要给每一行代码建立 trace。应该优先追踪那些**改变后会产生高 consequence 或跨边界影响**的 decision。

## 8. Requirements Evolution：需求会变化，不能只在项目开头“做完”

真实软件中，新 evidence 会不断出现：用户行为不同于预期、旧 consumer 比想象中更多、成本超预算、攻击面扩大、法规变化、Agent 发现当前 architecture 根本无法满足原约束。

因此 requirement 不是项目开始时冻结、之后只能服从的圣旨。它也需要版本、review、change authority 和历史理由。

这正好连接到 [Configuration、Baseline 与 Release](configuration-baselines-and-release.md)：如果 requirement 本身属于受控 artifact，那么改变 requirement 和改变 code 一样需要知道“哪个版本正在生效、谁批准了改变、哪些 evidence 因此失效”。

## 9. 对 coding agent 怎么用

Requirements 阶段很适合让 Agent 做**read-heavy reconnaissance**，不适合让它独立拥有产品语义。

一个有用的分工是让 Agent：

- 从 repo 恢复 current behavior；
- 搜索可能的 consumer 和 compatibility surface；
- 汇总相关 issue/history/test；
- 构造 behavior table；
- 列出互相矛盾的 evidence；
- 提出需要 human decision 的问题。

而人保留：

- stakeholder priority；
- public behavior 的新语义；
- business/risk trade-off；
- 哪些 unknown 可以接受；
- 最终 requirement authority。

高质量的 reconnaissance 结果不应该是“我建议这样做”，而应首先把 `OBSERVED / REQUESTED / ASSUMPTION / UNKNOWN` 分开。

## 10. 一个实用的 Issue Review

在开始实现一个非平凡 issue 前，可以用下面几问快速检查：

1. 这句话描述的是 need、requirement，还是已经预选的 implementation？
2. 谁会观察这个 change？是否漏了旧 client、运维流程、数据、协议或安全 stakeholder？
3. 当前行为中哪些是 evidence-backed contract，哪些只是 accidental behavior？
4. issue 内部是否有冲突、无法验证的词或未经授权的 policy decision？
5. 有哪些重要 unknown？应该 probe、prototype，还是升级给有 authority 的人？
6. 如果 requirement 改变，哪些 test/SLO/migration/compatibility artifact 需要一起改变？
7. 我们最终会用什么 evidence 证明 requirement 被满足？

如果这些问题能在实现前暴露一个错误假设，Requirements Engineering 就已经产生了价值。

## 11. 这篇旁支不教什么

这里没有教完整的需求文档模板、use-case notation、story-point 写法或产品管理流程。不是因为这些工具永远没用，而是它们只有在帮助团队发现、协商、记录和验证真实约束时才有价值。

本课程真正希望保留的能力是：**不要从一句看似具体的需求直接跳到 patch；先确认现实问题怎样被可靠地转译成可验证、可拥有、可演化的 contract。**

材料来源与取舍见 [`reading-notes/extensions-source-audit.md`](../reading-notes/extensions-source-audit.md)。
