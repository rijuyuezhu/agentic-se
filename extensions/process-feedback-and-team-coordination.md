---
id: ext-process-feedback
type: extension
visibility: student
related: [M00, M10, M12]
---
# Process、Feedback 与 Team Coordination：流程的价值在于改变反馈结构

假设一个团队有十个 coding agent。每个 Agent 每天都能产出一个看起来完整的 PR。两周后 dashboard 显示“并行任务数”创了新高，但真正 merge 的 change 反而变少：review queue 越来越长，多个 PR 修改同一层，后来的 change 建立在尚未接受的前一个 patch 上，测试环境排队，产品决策来不及做。

团队非常忙，系统却没有更快地产生可信的软件变化。

Software Process 值得保留的核心，不是记住某个方法有几个角色、几个会议，而是理解：**我们怎样组织 work，使高信息量的 feedback 尽早到来，同时控制 WIP、handoff 和 shared-state coordination cost。**

M00–M13 关心的是一次 software change 怎样被正确理解和验证；团队 workflow 则高度依赖人数、ownership 和组织约束。只有当 work 开始在多人/多 Agent 之间排队、handoff 或冲突时，这套 flow reasoning 才成为主要问题，因此放在旁支更合适。

## 1. Process 是 feedback architecture

M00–M13 本身已经隐含了一套 process：先理解，再写 change contract，再实现，再建立 evidence，再独立 review。这个顺序不是仪式，而是因为后一步的成本依赖前一步是否正确。

如果 system model 错了，越早收到反证越便宜；如果一直到 production 才发现 contract 理解错了，已经产生的 code、test、migration 和 rollout work 都可能变成 rework。

所以评价一个 process 时，首先不要问：

> 它叫 Agile、Scrum、Kanban 还是 Waterfall？

先问：

> **什么事实会证明我们方向错了？这个事实多久能回来？回来以后 change 还容易调整吗？**

这就是 feedback loop。

## 2. Iteration 的价值不是“每两周开一次会”

Agile Manifesto 强调 frequent delivery、responding to change、customer collaboration 和持续技术改进。这些原则最值得保留的部分，是**缩短从假设到 evidence 的距离**。

例如你要改一个旧 protocol。两种实施方式：

### Big-bang

先重写 server、worker、client、schema，最后一起 integration。

### Staged

先加兼容 reader 和 fixture；再部署 expand-only schema；再加新 writer；最后观察旧 consumer 退出并收缩旧路径。

第二种不一定“更 Agile”，但它在工程上提供了更多中间 observation point。每一步都可以证明一小部分假设，失败时 blast radius 和 rollback surface 更小。

Iteration 的真正价值就在这里，而不是 sprint 本身。

## 3. Small batch 为什么帮助 review

Google 的 engineering review guidance 明确建议 small, self-contained changes：它们更容易被彻底 review、更容易理解 impact、更容易 rollback，也更少让作者在错误方向上积累大量 work。

这个原则可以从 cognition 解释。

Reviewer 没有作者完整的 working memory。一个 PR 越大，reviewer 越容易从：

> “我能重建这个 change 的 correctness argument”

退化成：

> “大体看起来合理，tests 也绿了。”

Small batch 不是追求小 diff 数字，而是让**一个 change 的 semantic claim 足够 bounded，reviewer 能在有限上下文中独立验证。**

因此 50 行但跨五个 contract surface 的 change 可能并不小；500 行机械 rename 如果 behavior boundary 非常清楚，反而可能容易 review。

## 4. WIP：开始更多工作不等于完成更多工作

Kanban 把 Work in Progress（WIP）当作显式约束，强调 flow 而不是让所有资源永远 100% 忙碌。

软件团队里 WIP 很容易被低估，因为它不像工厂库存那样占仓库。它表现为：

- 正在写但未 review 的 branch；
- 等产品 decision 的 issue；
- 等 CI slot 的 PR；
- 已 merge 但未 rollout 的 migration；
- 一半完成的 refactor；
- Agent 已生成但没人读过的 patch；
- blocked incident follow-up。

这些工作都在占用 mental state、merge surface 和未来 coordination。

当 WIP 太高，常见结果不是“吞吐更高”，而是：

```text
等待时间上升
→ context 切换增加
→ change 变旧
→ merge conflict 增加
→ reviewer 更难恢复上下文
→ lead time 继续上升
```

所以“再开三个 Agent 并行写”不是免费的 capacity expansion。

## 5. Bottleneck 会移动

Agent 时代最重要的 process 变化之一，是 implementation 不再总是 bottleneck。

原来：

```text
spec → 人写代码很慢 → review → test
```

现在可能变成：

```text
spec
  ↓
Agent A/B/C/D 同时产出
  ↓
review queue
  ↓
shared test environment
  ↓
product/security decision
```

如果 bottleneck 已经是 human review，再把 Agent 数量翻倍只会增加 queue。

因此 process design 要观察 end-to-end flow，而不是局部 utilization。一个团队可以让 Agent “利用率很高”，同时让用户等待更久。

## 6. Pull 比 push 更适合有限 review capacity

Kanban 的 pull 思想很简单：下游有 capacity 时再拉入新 work，而不是上游不断把任务推入系统。

映射到 Agent workflow，可以是：

> 当前有两个 PR 正在等待独立 semantic review，就先让空闲 Agent 做 read-only reconnaissance、test triage、docs/source audit，而不是再制造第三个跨边界 patch。

这并不是一个普适的“最多两个 PR”规则。真正应该显式的是：

- 哪个 stage 是当前 bottleneck；
- 有多少 WIP 会开始破坏反馈速度；
- blocked work 怎样暴露；
- 什么 work 可以安全并行。

## 7. Parallelism：优先并行独立问题，而不是共享可变状态

这和 M07 的 concurrency 非常像。

三个 Agent 并行回答：

```text
A: 找 state owner
B: 找 compatibility consumer
C: 找 test/evidence gap
```

它们主要共享 read-only repo，结果可以由主线程合并。

三个 Agent 同时修改：

```text
service.py
schema.py
public_api.py
```

则需要协调 assumptions、接口、branch、merge 顺序和测试状态。并行度增加的同时，协调成本也上升。

因此一个实用原则是：

> **先并行化 independent questions，再并行化 shared mutable implementation。**

这不是 Agent-specific trick，而是把 concurrency/ownership reasoning 应用到了 engineering process 本身。

## 8. Handoff 是一种隐藏的 context boundary

团队协作常用“开发做完交测试”“Agent 写完交 reviewer”。每次 handoff 都可能丢失信息。

一个坏 handoff：

> 已完成，请 review。

一个好 handoff 至少让接收者知道：

- change claim；
- base/baseline；
- must-preserve behavior；
- changed surface；
- actual evidence；
- known limitation；
- unresolved decision。

M10/M12 的 evidence packet 本质上就是在减少 handoff hidden state。

Process 不应该追求“没有 handoff”，而应让 handoff 的 contract 清楚，并把能固化的信息放进 repository artifact，而不是依赖作者在线解释。

## 9. Ownership：谁写、谁 review、谁决定，不是同一件事

传统团队常说 code ownership。Agent workflow 需要更细地拆开：

- **implementation ownership**：谁负责产出 candidate change；
- **review ownership**：谁负责独立 challenge；
- **semantic authority**：谁能改变 public contract/business rule；
- **operational authority**：谁能 deploy/rollback/rotate credentials；
- **evidence ownership**：谁负责让 claim 可复现。

一个人或一个 Agent 可以拥有多个角色，但不要因此把角色混成“他负责这个功能，所以他什么都能决定”。

特别是 independent review，如果 reviewer 只是实现 Agent 的延长线，反馈回路会失去独立性。

## 10. Scrum、Waterfall、Kanban 应该怎样看

这些方法不值得作为宗教争论。

### Waterfall 提醒了什么

大型工程需要区分需求、设计、实现、验证等不同 concern，也需要知道某些 decision 会对后续工作产生强依赖。问题在于把这些活动理解成一次性、不可回返的阶段，在高不确定软件中容易让 feedback 太迟。

### Agile 提醒了什么

变化会持续发生，应该通过较短反馈、working software 和持续协作降低假设长期未经验证的风险。问题在于如果“Agile”只剩 ceremony，而 architecture、testing、review 和 technical excellence 被削弱，它不会自动产生可持续系统。

### Scrum 提供了什么

它提供一套具体 team cadence/role/work organization。对某些团队很有用，但本课程没有理由要求记角色和事件名称。

### Kanban 提供了什么

它特别清楚地把 WIP 和 flow 放进系统视角。对 Agent 并行工作非常有启发，但也不意味着所有团队都必须画同样的 board。

正确问题始终是：**这个 mechanism 改善了哪一个反馈或协调问题？**

## 11. Process metric 很容易被 gaming

如果你奖励：

```text
PR 数量
story point
Agent completed tasks
LOC
review count
```

团队会自然优化这些数字，即使 end-to-end value 没有改善。

更值得观察的是 flow 和 outcome，例如：

- 一个 change 从 ready 到 trustworthy/mergeable 的 lead time；
- review queue age；
- rework round；
- rollback / regression；
- blocked time；
- correct escalation；
- user-facing SLI。

这些指标也不完美。M11 的原则仍然适用：measurement 必须从真正关心的 outcome 往回设计，而不是从工具容易导出的数据开始。

## 12. 一个小型 Agent Team 该怎样开始

对 1 个 controller + 少量 Agent/worker 的场景，不需要引入企业级 process framework。

可以从很小的规则开始：

1. 一个 write-heavy change 有一个明确 owner；
2. read-heavy reconnaissance 可以并行；
3. PR/change 保持 semantic scope bounded；
4. 超过 review capacity 时停止制造新大 patch；
5. semantic decision 进入 durable decision record；
6. independent reviewer 不先接受 implementation Agent 的 summary；
7. merge/deploy 仍有明确 authority；
8. 重复出现的 process friction 再固化成 CI/tool/policy。

只有当真实 friction 证明需要时，再增加 board、WIP policy、release train 或更正式的 planning。

## 13. 判断流程是不是 ceremony

一个 process rule 应该能回答至少一个问题：

- 它让什么错误更早被发现？
- 它保护了什么 authority boundary？
- 它减少了什么 coordination hidden state？
- 它限制了什么危险 WIP？
- 它留下了什么 durable evidence？
- 它改善了什么 user/engineering outcome？

如果答案只是“行业都这么做”“Scrum 要求”“这是 best practice”，应该重新审视它。

## 14. 这篇旁支不教什么

这里不教 Scrum certification、完整项目排期、组织设计，也不会规定 sprint 长度、daily standup 或统一 WIP 数字。

本课程只保留 Process 最可迁移的一层：**把软件开发本身看成一个有 queue、WIP、feedback latency、authority 和 handoff 的系统，然后像设计软件一样设计这个工作系统。**

材料来源与取舍见 [`reading-notes/extensions-source-audit.md`](../reading-notes/extensions-source-audit.md)。
