---
id: source-M09
type: source_audit
visibility: student
related: [M09]
---
# M09 Source Audit — Architecture：边界、数据流、Authority 与 Failure Domain

> 审计/复核日期：**2026-09-07**。

> 目标：不是收集“流行架构风格”，而是确认哪些一手材料真的能支撑 M09 的核心判断：什么决定值得上升到 architecture，系统边界怎样影响 change amplification / authority / failure propagation，以及架构文档应该记录什么。
>
> 本模块继续沿用前面的规则：只把实际检查过正文的材料升级成主线；知名但未审计的材料只保留为 pointer。

---

## 0. 本模块真正要回答的问题

M09 不问：

- “微服务是不是比单体先进？”
- “应该用几层 architecture？”
- “六边形 / Clean / Onion 哪个最好？”
- “要不要画 UML？”

而问：

1. 哪些系统结构对理解和演化真的重要？
2. authority、durability、external effect、compatibility 应该在哪里形成稳定边界？
3. 哪些 dependency 可以留在进程内部，哪些一旦跨进程/网络就产生新的 protocol / availability / compatibility cost？
4. failure 会被边界 containment，还是被 retry / failover 扩散？
5. 一个 architecture decision 为什么值得被长期记录？
6. 怎样区分 architecture diagram 中的“真实 semantic boundary”和“仅仅是画了个框”？

本模块特别避免：

- “architecture = top-level folder structure”；
- “architecture = deployment diagram”；
- “architecture = microservices”；
- “模块越多越好”；
- “进程边界天然比函数边界更强”；
- “高可用 = 所有失败都 failover”；
- “画了图就完成 architecture”；
- “ADR 越多越成熟”。

---

## 1. SEI — Software Architecture as Structures for Reasoning

**状态：主干采用（architecture 的结构化定义）**

实际检查：

- SEI: Three Roles and Three Failure Patterns of Software Architects
  - [1. SEI — Software Architecture as Structures for Reasoning — source 1](https://insights.sei.cmu.edu/blog/three-roles-and-three-failure-patterns-of-software-architects/)
- SEI historical reflection on software architecture definition
  - [1. SEI — Software Architecture as Structures for Reasoning — source 2](https://insights.sei.cmu.edu/blog/reflections-on-20-years-of-software-architecture-a-presentation-by-linda-northrop/)

### 实际内容

SEI 给出的核心定义不是“最高层模块图”，而是：

> architecture 包含 **为了对系统进行推理所需要的 structures**；每个 structure 包含 elements、elements 之间的 relations，以及 elements / relations 的 properties。

较早定义强调：

- software elements；
- externally visible properties；
- relationships among elements。

并明确指出，仅与 element 内部实现有关、不会被其他 element 依赖的 private details，不属于 architecture concern。

### 本课程吸收

M09 因此把 architecture 看成：

```text
用于回答系统级问题的稳定 reasoning model
```

而不只是一张模块图。

不同 concern 需要不同 view：

```text
change view       -> dependency / knowledge boundary
runtime view      -> control/data flow
state view        -> authority / durability / replica
failure view      -> fault containment / propagation
compatibility view-> producer / consumer / version
```

这也解释为什么“唯一正确的 architecture diagram”通常是个错误目标。

### 限制

SEI 的定义本身不告诉我们 TaskForge 应该拆成几个 process，也不会自动得出 microservice/monolith 选择。

它提供的是：

> architecture 应该保留哪些 **可用于推理的重要结构**。

---

## 2. Martin Fowler / Ralph Johnson — Architecture Is the Important Stuff

**状态：主干采用（architectural significance / evolutionary architecture）**

实际检查：

- [2. Martin Fowler / Ralph Johnson — Architecture Is the Important Stuff](https://martinfowler.com/architecture/)

### 实际内容

Fowler 总结 Ralph Johnson 的观点：architecture 不容易被客观地等同于“最高层”或“必须最早决定的东西”。更有用的问题是：

> 哪些 design elements 是真正重要的？哪些如果不受控制，会造成严重问题？

Fowler 同时强调：好的 architecture 应支持自身 evolution，而不是把 architecture 与 programming 分离。

### 本课程吸收

本模块把 architectural significance 写成一个定性 heuristic：

某个决定越具有下面特征，越值得上升为 architecture concern：

1. **blast radius 大**：错了会影响多个模块/服务/用户；
2. **reversal cost 高**：迁移昂贵、需要兼容窗口、数据回写或停机；
3. **coordination cost 高**：需要多个 owner / repo / deployable 同步；
4. **failure consequence 大**：会改变故障传播方式；
5. **authority consequence 大**：会改变谁拥有某条 truth / invariant；
6. **long-lived contract**：数据、协议、配置或外部 caller 会长期依赖；
7. **unknown-consumer risk**：无法轻易枚举所有依赖者。

不是公式，也不产生一个分数；它是 review checklist。

### 课程拒绝的误读

不是：

```text
“改起来困难” = architecture 一定设计得好
```

恰恰相反，困难可能来自 accidental coupling。

也不是：

```text
“architect 说重要” = architectural
```

重要性要能够回到系统 consequence。

---

## 3. Stanford CS190 — Modular Design / Information Leakage

**状态：主干复用（dependency / knowledge boundary）**

实际检查：

- [3. Stanford CS190 — Modular Design / Information Leakage — source 1](https://web.stanford.edu/~ouster/cgi-bin/cs190-spring16/lecture.php?topic=modularDesign)
- current course page:
  - [3. Stanford CS190 — Modular Design / Information Leakage — source 2](https://web.stanford.edu/~ouster/cs190-winter24/)

### 实际内容

CS190 的 modular-design framing：

- 系统分成相对独立的模块；
- interface 包含其他模块必须知道的一切，不仅是 method signature，还包括行为、side effects、constraints 等 informal dependency；
- information leakage 表示 design knowledge 被多个模块共同依赖；
- 发现 leakage 时应考虑把相关 knowledge 聚合到一个地方；
- simple API 往往比 simple implementation 更重要。

### 本课程吸收

M02 已经把这些用于 class/module-level information hiding。

M09 将它提升到 system scale：

```text
architecture boundary
!=
process boundary
```

真正重要的是 boundary 是否做到：

```text
knowledge locality
+ authority clarity
+ stable contract
+ controlled failure propagation
```

一个 in-process module 可以是很强的 semantic boundary；一个独立 service 也可能因为 shared database / backdoor reads / synchronized deployment 而根本没有形成真正独立的 boundary。

### 限制

CS190 主要讨论软件 design/modularity，不直接给 distributed failure-domain 设计规则。因此本章的 failure-domain 部分需要额外来源。

---

## 4. AWS Well-Architected — Cell-based Architecture / Scope of Impact

**状态：主干采用（failure domain / isolation 是 architecture concern）**

实际检查：

- [4. AWS Well-Architected — Cell-based Architecture / Scope of Impact — source 1](https://docs.aws.amazon.com/wellarchitected/latest/reducing-scope-of-impact-with-cell-based-architecture/what-is-a-cell-based-architecture.html)
- [4. AWS Well-Architected — Cell-based Architecture / Scope of Impact — source 2](https://docs.aws.amazon.com/whitepapers/latest/aws-fault-isolation-boundaries/control-planes-and-data-planes.html)

### 实际内容

AWS 的 cell-based architecture guidance 将 workload 分成多个独立 cell：

- 每个 cell 处理 workload 的一个 subset；
- cells 不共享 state；
- routing 按 partition key 将 request 分配到 cell；
- failure / bad deployment 可以被限制在某个 cell 的 scope 内；
- partition key 应与 workload 的 natural grain 对齐，以尽量减少 cross-cell interactions。

AWS 另一份 fault-isolation 文档还明确区分 **control plane** 与 **data plane**：术语来自网络；control plane 负责创建/修改资源与规则、执行 orchestration，data plane 承担服务的主要功能。AWS 强调两者可以有不同的 complexity / availability profile。

### 本课程吸收

这里最重要的不是“大家应该做 cell architecture”，而是几个 architecture questions：

#### 1. Scope of impact 是设计对象

不能只问：

```text
组件会不会失败？
```

而要问：

```text
它失败时谁一起失败？
```

#### 2. Isolation boundary 需要和 state / traffic grain 对齐

如果你画了多个 cell，却仍共享同一个 hot mutable authority，或每次请求都跨 cell 协调，那么这个 isolation boundary 很可能只是部署上的框。

#### 3. Control plane / data plane 是一个有条件的 reasoning lens

TaskForge 不是网络设备，也不是 AWS 服务，因此本课程不会把术语机械套用。课程借它区分两类 responsibility：lifecycle/control authority 负责决定和记录 job 的合法状态变化；remote worker 负责执行 command 与接触 external effect，接近 **data/execution plane**。这个映射属于课程综合。它的用途是检查 privilege、availability 与 failure coupling，而不是规定必须拆成两个 service。

### 限制

TaskForge M09 不会实现 production cell architecture。

它借这个材料训练：

```text
failure containment must correspond to real dependency/state boundaries
```

而不是复制 AWS topology。

---

## 5. Google SRE — Cascading Failures

**状态：主干采用（failure propagation / fallback / retry 可改变 failure domain）**

实际检查：

- [5. Google SRE — Cascading Failures](https://sre.google/sre-book/addressing-cascading-failures/)

### 实际内容

Google SRE 明确描述：

- 局部 overload 可以造成 server failure；
- load balancer / scheduler 的自动反应可能把流量推到其他 cluster；
- 其他 cluster 随即 overload；
- local failure 因为系统 coupling 被扩散成 service-wide failure。

这和 M07 retry amplification 是同一类系统现象。

### 本课程吸收

一个“可靠性机制”是否真的可靠，不能只从局部 happy-path 名字判断：

```text
failover
retry
fallback
replication
```

都可能改变 dependency graph 和 failure propagation graph。

所以 architecture review 要问：

```text
failure X
→ component A reacts how?
→ traffic/state moves where?
→ destination capacity / authority 是否成立？
→ blast radius 变大还是变小？
```

### 限制

不是“不要 failover”。

而是：

> failover 本身也是一个需要 capacity / ownership / isolation reasoning 的 architectural mechanism。

---

## 6. Martin Fowler — Monolith First

**状态：案例材料（deployment boundary 不等于 semantic boundary）**

实际检查：

- [6. Martin Fowler — Monolith First](https://martinfowler.com/bliki/MonolithFirst.html)

### 实际内容

Fowler 的文章强调：

- microservices 有额外 premium；
- service decomposition 依赖 good, stable boundaries；
- 过早选择 distributed service boundaries 可能在 domain boundary 尚未理解时引入额外复杂度。

### 本课程吸收

M09 明确区分：

```text
semantic boundary
process boundary
deployment boundary
failure boundary
```

它们可能重合，但**不应该默认重合**。

例如：

```text
Job Authority
```

可以先是一个进程内 module boundary。

只有当需求真的要求：

- 独立 scale；
- 独立 failure containment；
- 独立 deploy / ownership；
- security boundary；
- remote execution；

才需要进一步考虑 process/network boundary。

### 限制

`Monolith First` 是经验性文章，不是定理。

课程不会升级成：

```text
所有系统必须 monolith first
```

它只用于反对：

```text
“service = architecture maturity”
```

---

## 7. MartinFowler.com — DIP in the Wild

**状态：主干采用（dependency inversion 的实际用途）**

实际检查：

- [7. MartinFowler.com — DIP in the Wild](https://martinfowler.com/articles/dipInTheWild.html)

### 实际内容

Brett Schuchert 对 Dependency Inversion Principle 的概括包括：high-level policy 不应依赖 low-level detail，依赖应指向更接近 domain 的 abstraction。文章特别强调，DIP 不是“有 interface 就完成了”，也不是 Dependency Injection / IoC 的同义词；把一个 JDBC connection 注入 domain code 仍然可能是错误的 dependency shape。文章的实际例子是把数据库 detail 藏到 domain-relevant repository 后面，让 storage mechanism 可以变化而不污染高层 policy。

文章同时有一个重要 qualifier：abstraction 有成本，design principle 应按 context 使用，不能为了原则本身制造 speculative flexibility。

### 本课程吸收

TaskForge 的 remote-worker case 正好给出一个 system-scale application：

```text
bad dependency shape:
worker -> jobs table / DB credential / storage representation

better dependency shape:
worker -> claim / finish / heartbeat semantics
        -> Job Authority owns storage detail
```

这里所谓“dependency inversion 的真实用途”不是给每个 class 加 interface，也不是引入 DI framework，而是让 **execution-side code 依赖 domain-level lifecycle contract，而不是低层 persistence detail**。这使 storage migration、privilege separation 和 network boundary 可以在不泄漏 row/schema knowledge 给 worker 的前提下演化。

### 限制

DIP 不自动证明 Job Authority 这个 architecture 一定正确。它只帮助判断 dependency 应朝哪个 abstraction level 指向；是否值得建立该 boundary，仍要由 remote execution、authority、security、failure 与 evolution requirements 支付。

---

## 8. Martin Fowler — Architecture Decision Record (2026)


**状态：主干采用（architecture reasoning preservation）**

实际检查：

- [8. Martin Fowler — Architecture Decision Record (2026)](https://martinfowler.com/bliki/ArchitectureDecisionRecord.html)

### 实际内容

Fowler 2026 的 ADR 页面将 ADR 定义为短文档，记录单个相关 decision，并包含：

- decision；
- context / rationale；
- significant ramifications / consequences；
- serious alternatives；
- status；
- 在 decision 被替代时通过 superseding record 保留历史，而不是改写旧记录。

他特别强调写 ADR 不只是为了 archival；写作本身会迫使参与者明确 trade-offs 和 disagreement。

### 本课程吸收

M09 不要求“每个技术选择一个 ADR”。

只有当决定具有明显 architectural significance 时，才值得记录，例如：

- Job lifecycle truth 的 authoritative owner；
- durable state 是 source of truth 还是 export snapshot；
- external effect 的 idempotency responsibility；
- worker 与 authority 的 protocol boundary；
- failure isolation / shard key；
- compatibility window / irreversible migration。

TaskForge M09 lab 会让学生写一个**短 ADR**，而不是写宏大的 architecture spec。

### 特别适合 Agent 时代的一点

代码保留的是：

```text
what exists
```

但 Agent 很容易重新提出过去已经 rejected 的方案。

ADR 保留：

```text
why this
why not alternatives
what assumption would trigger reconsideration
```

因此它是跨 human/Agent session 的 reasoning boundary。

### 限制

ADR 本身不会让错误 architecture 变正确。

大量低价值 ADR 反而会制造 documentation noise。

---

## 9. Parnas 1972 — 本轮处理方式

历史论文：

- D. L. Parnas, *On the Criteria To Be Used in Decomposing Systems into Modules* (1972)

**状态：historical pointer，不升级为本模块新的 primary-source authority。**

原因：本轮搜索能找到多个课程材料和二手引用，但没有获得一个我愿意当作权威、完整正文逐段审计的原始出版版本。

M02/M09 关于 information hiding 的课程主张已经有 Stanford CS190 / Ousterhout 的实际正文支撑，因此没有必要为了“经典性”伪装成已经 primary-audited。

这继续遵循用户要求：

> famous != audited

---

## 10. 本模块的综合模型：Architecture = Consequential Boundaries

下面是课程综合，不归因于单一来源。

一个 boundary 越同时承担下面几种 responsibility，它越接近 architectural boundary：

```text
Knowledge boundary
  谁需要知道什么？

Authority boundary
  谁能决定 truth / transition？

Durability boundary
  crash 后什么仍然存在？

Compatibility boundary
  哪些 producer / consumer 独立演化？

Failure boundary
  failure 能传播到哪里？

Security boundary
  哪些 trust / privilege 在这里改变？

Ownership boundary
  哪个团队/组件对 contract 负责？
```

强 architecture 不意味着这些边界必须全部重合。

但如果它们**互相矛盾且没有明确模型**，系统通常会产生 hidden coupling。

例如：

```text
service A 声称拥有 Job lifecycle
但 service B 直接写 shared DB
snapshot exporter 被当恢复源
worker 又可以直接修改 authoritative row
```

此时画四个漂亮 service box 不会解决 split authority。

---

## 11. Architecture View 不是“一张全能图”

课程综合采用多-view：

### View A — Responsibility / knowledge

```text
谁知道 command representation？
谁知道 retry policy？
谁知道 persistence schema？
```

### View B — Authority / state

```text
source of truth
writer
replica
snapshot
cache
```

### View C — Runtime data/control flow

```text
submit → schedule → execute → finish → observe
```

### View D — Failure propagation

```text
process crash
storage unavailable
worker timeout
external sink duplicate
bad deployment
```

### View E — Evolution / compatibility

```text
producer version
consumer version
migration window
rollback target
```

为什么？

因为单张图如果同时表达这些 concern，通常要么过密，要么把最重要的信息藏掉。

---

## 12. Source audit 之后 M09 可以严谨教授什么

可以：

- architecture 是用于 system-level reasoning 的重要 structures，不是“大盒子图”；
- architectural significance 可从 blast radius / reversal / coordination / authority / long-lived contract 等 consequence 判断；
- semantic boundary 与 process/deployment boundary 必须区分；
- information hiding 在系统级仍然是核心；
- dependency inversion 的实际用途是让 high-level/domain policy 依赖 domain-relevant abstraction 而不是 low-level detail；它不等于 DI framework / interface ceremony；
- control plane / data plane 可以作为 privilege / availability / failure-coupling lens，但 TaskForge 的 lifecycle-control vs data/execution 映射属于课程综合，不是通用 topology 定律；
- failure domain / scope of impact 是 architecture property；
- retry/failover 可能扩大 failure propagation；
- architecture 需要多个 concern-specific views；
- ADR 用于保留 consequential decision 的 context / alternatives / consequences；
- architecture 应支持 evolution，而不是冻结未来。

不能当作定律：

- microservices better；
- monolith always first；
- every subsystem needs ADR；
- every process boundary is a fault boundary；
- every shared database is wrong；
- every architecture should match one named pattern；
- architecture can be designed once at project start and then left alone。

---

## 13. M09 TaskForge teaching target

TaskForge 前几章已经自然暴露了 architecture pressure：

```text
state.py                 shared mutable lifecycle representation
service.py               submit/get/cancel
worker.py                lifecycle writer
concurrent_claim.py      competing claim authority
snapshot.py              durable export / compatibility surface
effect_delivery.py       external side-effect boundary
public_api.py             external API surface
legacy_audit.py           side-channel reader
```

这正适合 M09：

学生不再修一个局部 bug，而要先回答：

```text
Job truth 到底在哪里？
snapshot 是 source of truth 还是 derived artifact？
worker 是 authority 还是 authority client？
external effect dedup 应由谁拥有？
哪些 dependency 只是进程内 implementation，哪些值得 network boundary？
如果 storage / worker / effect sink 各自失败，blast radius 如何？
```

本章的目标不是把 TaskForge 改成“完整分布式系统”，而是形成一个**可以指导后续 implementation 的 architecture decision model**。
