# Software Quality：把“质量更高”拆成可讨论的 contract

“这个实现质量更高。”

这句话在 review 里很常见，也几乎没有直接可验证的信息。有人说的是 correctness，有人说的是 latency，有人担心 maintainability，有人其实只是不喜欢代码风格。

Software Quality 这个传统领域最值得本课程保留的，不是额外建立一个 QA 流程，而是一个基本纪律：**quality 不是单一分数。先说清楚你关心哪一种可观察性质，再讨论 trade-off 和 evidence。**

## 1. Quality 不等于 Testing

M03 已经把 testing 当作 executable evidence。但测试只是获得 evidence 的一种机制，quality 是被评价的对象。

例如：

- 一个算法可以功能正确，却慢到不满足用户 latency；
- 一个 API 可以可靠，却让调用者极难正确使用；
- 一个服务可以性能很好，却需要过高权限；
- 一个模块可以测试覆盖率很高，却因为 duplicated authority 很难维护；
- 一个系统可以在正常输入下完全正确，却在 dependency failure 时无法安全退化。

所以“tests green”只能支持某些 quality claims，不能自动推出“系统质量高”。

## 2. Quality attribute 是把形容词变成工程对象

ISO/IEC 25010:2023 提供了一套产品质量参考模型，包含九个高层特征：functional suitability、performance efficiency、compatibility、interaction capability、reliability、security、maintainability、flexibility 和 safety。

这张表的价值不是要求你给每个项目打九项分数，而是提醒：**同一个设计往往同时影响多个不同维度。**

例如一个 aggressive cache：

- performance efficiency 可能提高；
- reliability 可能因为 stale data 变差；
- maintainability 可能因为 invalidation rule 复杂化；
- security 可能因为敏感数据驻留更久而改变；
- compatibility 可能因为缓存 key/schema 变化产生迁移问题。

如果 review 只问“cache 能不能提速”，就遗漏了真正的 design surface。

## 3. 从 attribute 继续走到 scenario

“可靠性高”“可维护性强”仍然太抽象。

更有用的写法会把 quality attribute 放进具体 scenario：

> 当一个 worker 在 claim 后、提交结果前 crash，系统重启并允许重新调度，但 stale attempt 不得覆盖新 attempt 的最终状态。

这是 reliability/failure correctness 的一个具体场景。

或者：

> 新增一种 terminal job state 时，状态语义只需要在一个 lifecycle owner 中修改；public serializer 和 metrics 从统一查询接口读取，而不是各自复制状态机判断。

这开始把 maintainability 变成 change scenario，而不只是“代码干净”。

一个通用的 quality scenario 可以考虑：

```text
context / precondition
→ stimulus
→ system response
→ observable measure or invariant
```

不是每个 attribute 都要写成数字。有些适合 latency/error ratio，有些适合 compatibility fixture、change amplification、authority invariant 或 independent review。

## 4. Quality attribute 会冲突

设计经常不是“质量高 vs 质量低”，而是不同质量属性之间的 trade-off。

例如：

- 更强 durability 可能增加 latency；
- 更广 backward compatibility 可能增加当前 code path 和 test matrix；
- 更严格 authorization 可能增加操作摩擦；
- 更强 abstraction 可以降低 cognitive load，但抽象过早也可能降低直接性；
- 更丰富 telemetry 可以改善 diagnosis，却增加 cost 和 data exposure。

因此 architecture discussion 里“这个方案质量更高”不如：

> 方案 A 用额外兼容层换取 rollout reversibility；代价是未来两个 release 需要同时维护 old/new reader。我们认为这个临时 maintainability cost 值得支付，因为 frozen client 无法同步升级。

这里 quality trade-off 已经变成可 review 的 argument。

## 5. Quality model 是检查遗漏的地图，不是 scoring formula

ISO/IEC 25010 一类 quality model 很适合在设计或 review 时问：

> 我们是不是只优化了最显眼的一个属性，漏掉了其他重要 consequence？

但不要轻易把九个 attribute 做成：

```text
quality = 0.2 * reliability + 0.15 * security + ...
```

不同系统的价值和风险不同。Payment system、compiler、个人 CLI、医疗设备对 quality attribute 的优先级不会一样。

权重本身是 product/risk decision，不是从标准中自动得到的数学常数。

## 6. Quality requirement 应该进入普通 change contract

Quality 不应该等 feature 做完后再由“QA”补一次检查。

如果 latency、compatibility、security、maintainability 或 safety 对某个 change 是核心要求，它们应该在设计和 task contract 里提前出现。

例如：

```text
Goal:
  add batch query

Must preserve:
  v1 response schema
  p99 latency under stated load budget
  caller-visible ordering

Design constraint:
  query path must not acquire writer authority

Evidence:
  compatibility fixture
  deterministic ordering tests
  load probe
```

这比最后一句“注意代码质量”有效得多。

## 7. Process quality 和 product quality 不要混淆

“我们有严格 code review”“我们使用 TDD”“我们的 CI 有很多 gate”描述的是过程和控制机制。它们可能提高获得某些产品质量的概率，但不能代替产品 evidence。

反过来，一次 product benchmark 很好也不能证明 process 可持续。

因此 review 时要问两层：

1. **Product claim**：最终系统表现出什么属性？
2. **Process/evidence claim**：我们通过什么活动获得对这个属性的信心？

把两层分开，可以避免“做了正确流程，所以产品一定正确”的推理跳跃。

## 8. Agent 时代的 quality gate 应保护 claim，不是保护格式

Agent 可以轻易满足大量机械 gate：lint、format、coverage threshold、模板字段。如果 gate 和真实 quality claim 没有连接，它只会训练 Agent gaming checklist。

高价值 gate 更像：

- public behavior compatibility fixture；
- mutation 能否杀掉关键 contract 破坏；
- forbidden dependency/authority edge 检查；
- schema compatibility probe；
- performance/SLO regression threshold；
- security policy / artifact provenance check。

也就是说，自动化 gate 应尽可能保护**已知重要属性**，而不是把“可自动检查”误当成“最重要”。

## 9. 一个 Quality Review

当 PR 声称“改善质量”时，可以问：

1. 具体是哪一个 quality attribute？
2. 对谁、在什么条件下重要？
3. 它怎样变成 observable scenario / invariant / measure？
4. 这个优化牺牲了什么其他属性？
5. 当前 evidence 真正覆盖哪个 claim？
6. 是否把 process compliance 当成 product correctness？
7. 如果 trade-off 需要优先级判断，谁有 authority？

如果这些问题回答不出来，“quality”可能只是审美词。

## 10. 这篇旁支不教什么

这里不建立独立 QA 组织模型，也不要求背 ISO 标准的所有 subcharacteristic。M03、M09、M11 已经分别深入 testing、architecture 和 production reliability。

这篇旁支只补一层共同语言：**把“好软件”拆成不同、可能冲突、必须用场景和 evidence 表达的质量属性。**

材料来源与取舍见 [`reading-notes/extensions-source-audit.md`](../reading-notes/extensions-source-audit.md)。
