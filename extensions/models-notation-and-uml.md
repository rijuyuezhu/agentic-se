# Models、Notation 与 UML：图是 reasoning tool，不是作业格式

“画一下架构图”经常产生两种结果。

一种是漂亮但没有可检验含义的 boxes-and-arrows：`Frontend → Backend → DB`。另一种是把 UML 的符号用得很完整，却没人能从图里回答这个 change 到底会碰哪些 state owner、protocol、failure boundary。

两种图都可能形式正确，却没有帮助工程判断。

Software Models and Methods 最值得本课程保留的思想不是“应该使用 UML”，而是：**模型是为了压缩和突出与某个问题有关的系统事实；选择什么模型，取决于你正在回答什么问题。**

## 1. 模型一定会丢信息，这正是它的价值

完整代码包含太多细节。模型的作用不是复制代码，而是故意省略不重要的部分，让某一种结构更容易看见。

例如你在调查“为什么 lifecycle rule 到处重复”，可能只需要：

```text
API ──writes──> Service
Worker ──writes──> Store
Metrics ──reads──> Store
Legacy audit ──writes──> Store
```

函数内部具体算法并不重要。真正暴露问题的是：有多个 writer 绕过同一个 semantic owner。

如果你在调查 race，同一个系统则可能需要另一张图：

```text
worker A        store        worker B
   | claim?       |             |
   |------------->|             |
   |               |<------------|
   | read queued   | read queued |
   | write running | write running
```

同一个软件，需要不同模型回答不同问题。

## 2. 画图前先写一句“这张图要回答什么”

这是最简单也最有效的 modeling discipline。

例如：

> 这张图要回答：一次 `cancel(job_id)` 从 public API 到 authoritative state 的 control flow 中，哪些 component 有资格改变 lifecycle？

或者：

> 这张图要回答：rolling upgrade 时 old/new server、worker、schema 会出现哪些合法组合？

如果一句话写不出来，图很可能只是在“展示系统”。而“展示系统”通常范围太大，最后所有东西都被画进去，什么都看不清。

## 3. Structural model：谁依赖谁，谁包含谁

Structural view 适合回答相对静态的问题：

- 主要 component/module 是什么；
- dependency direction；
- ownership boundary；
- deployment unit；
- data store；
- external system；
- 哪些层知道了本应隐藏的细节。

M02 的 information hiding、M09 的 architecture map 都属于这一类。

### Dependency graph

如果问题是 change amplification，dependency graph 往往比完整 architecture diagram 更有用：

```text
public_api
  ↓
service
  ↓
repository
  ↓
schema
```

然后标出反向/旁路 edge，就能直接讨论 coupling。

### C4-style view

C4 的一个优点是用不同 zoom level 区分 system context、container、component 等视图，而不是试图在一张图里同时放 browser、service、class 和 method。它还是 notation-independent 的。

对本课程最有价值的不是“必须画四张 C4 图”，而是这个原则：

> **先选择适合当前 audience/question 的 abstraction level，不要混合层级。**

如果只需要解释外部系统和 deployment unit，画 class diagram 是噪声。

## 4. Behavioral model：系统怎样随事件变化

很多最危险的软件问题不在静态依赖，而在时间和状态。

### State machine

当合法状态和 transition 本身就是 contract 时，state machine 极其有用。

例如：

```text
queued -> running -> succeeded
   |         |
   |         -> failed
   -> cancelled
```

然后你可以直接问：

- `running -> cancelled` 是否允许？
- terminal state 是否还能改变？
- retry 是回到 `queued`，还是创建新 attempt？
- 哪个 component 拥有 transition authority？

代码中的 `if/else` 很难像这张图一样直接暴露非法 transition。

### Sequence / dynamic view

当问题依赖 ordering、cross-process interaction、retry 或 timeout 时，sequence-like view 更合适。

例如：

```text
client        controller       worker
  | submit       |               |
  |------------->|               |
  | accepted     |               |
  |<-------------|               |
  |              | claim         |
  |              |<--------------|
  |              | lease         |
  |              |-------------->|
```

它能让你追问“response 在哪一个 state change 前后发生”“timeout 后哪一方知道什么”。

### Data-flow view

当问题是 security/privacy、serialization、derived state 或 data ownership 时，data-flow 往往比 call graph 更有信息量。

## 5. Model 的语义必须比颜色和形状更重要

一个常见坏图：红色框表示“重要”，虚线表示“异步”，蓝色箭头表示“读”，但图例不存在；不同页面又换了含义。

一个可 review 的模型应该让读者知道：

- scope；
- abstraction level；
- element type；
- relationship direction；
- edge 的语义；
- 哪些是 observed fact，哪些是 proposed design。

C4 的 review checklist 也强调 title、scope、element meaning、relationship label 和 direction。这里真正值得借鉴的是**让 notation 服务共同理解**，不是采用某种固定画图软件。

## 6. UML：学“能表达什么”，不用背完整符号表

UML 是一套很丰富的 graphical modeling language。它提供 class、component、deployment、sequence、state machine 等多种结构和行为视图。

本课程不要求系统学习所有 UML notation，因为多数真实 software change 只需要其中很小一部分表达能力。

但这不意味着 UML 一文不值。

如果团队已经共享 UML vocabulary，那么：

- sequence diagram 可以精确表达 interaction ordering；
- state machine diagram 可以表达 lifecycle；
- component/deployment view 可以表达边界和部署关系；
- class diagram 在 OO domain model 中可能非常有效。

问题不在“是不是 UML”，而在：

> 读者能否从这个 notation 得到比 prose/code 更清楚、且与当前 engineering question 有关的信息？

如果答案是否定的，就没有必要为了规范而画。

## 7. Model 不是 source of truth 的天然替代品

图最危险的 failure mode 是 stale。

代码已经把 writer 从 service 移到 repository，architecture diagram 还显示旧路径；schema 已经扩展到 v2，migration diagram 还是第一版。此时图不再降低 cognitive load，而是在制造错误 mental model。

因此长期模型需要明确 maintenance strategy：

- 谁拥有它；
- 什么时候更新；
- 哪些事实能从代码自动验证；
- 哪些只是 explanatory view；
- stale 后 consequence 多大。

短期 whiteboard model 可以在一次 design session 后自然失效；长期 architecture map 则应该更接近 repository artifact，并进入 review。

## 8. Model 和 Evidence 要互相校验

一张图不是因为“画得合理”就是真的。

例如你画出：

```text
all lifecycle writes -> JobService
```

接下来应该用 repository search 或 instrumentation 验证：是否真的没有旁路 writer？

你画出：

```text
old client -> new server supported
```

应该用 frozen binary/compatibility fixture 验证。

因此本课程把 model 当作 hypothesis organizer：它帮助你明确自己认为系统是什么样，然后用 source/runtime evidence challenge 它。

这比把图当 documentation decoration 更可靠。

## 9. Current-state 与 Target-state 不要画在一起假装已经实现

Architecture proposal 经常把未来设计画得很漂亮，然后在讨论中逐渐被当作当前事实。

一个简单办法是明确区分：

- **as-is / observed**：从当前 source/runtime 恢复的模型；
- **to-be / proposed**：如果 decision 被批准并 implementation 成功，希望达到的状态；
- **migration states**：从 as-is 到 to-be 中间允许出现的配置。

M08/M09 特别需要第三类。两个 endpoint 的 target diagram 都正确，不代表中间 rollout state 是安全的。

## 10. 对 Agent 怎么用模型

Agent 很适合生成 candidate model，但输出必须可验证。

例如要求 Agent：

> 找出所有修改 `Job.state` 的路径，生成 writer map；每条 edge 附 source location。不要提出 refactor。

这比：

> 给我画一下这个项目架构。

有用得多，因为前者定义了 question 和 evidence contract。

Agent 还可以并行生成不同 view：

- dependency/ownership；
- lifecycle state machine；
- compatibility matrix；
- data-flow/trust boundary。

然后人对照 source/runtime 交叉检查。不要因为 diagram 看起来完整就把它当成 authoritative model。

## 11. 怎样选择模型

可以从问题倒推：

| 你要回答的问题 | 常见有用模型 |
|---|---|
| 谁拥有状态，哪些模块越界写入？ | dependency / ownership graph |
| 哪些状态转换合法？ | state machine |
| timeout/retry/race 的 ordering 是什么？ | sequence / dynamic view |
| 数据从哪里来、经过哪里、在哪里跨 trust boundary？ | data-flow diagram |
| 系统和外部环境怎样连接？ | context view |
| major applications/data stores 怎样分工？ | container/deployment view |
| rolling upgrade 哪些版本组合合法？ | compatibility matrix / migration state model |
| 一个 request 的实际 control flow 经过哪些层？ | call/control-flow sketch |

没有“高级项目必须使用更多种图”的规则。**能用一个小模型回答问题，就不要画一个模型博物馆。**

## 12. Model Review Checklist

在接受一张长期模型前，可以问：

1. 它明确要回答什么问题？
2. scope 和 abstraction level 是否一致？
3. element/edge 的语义是否清楚？
4. observed 与 proposed 是否区分？
5. 有哪些 claim 可以用 source/runtime evidence 验证？
6. 是否遗漏了真正决定 contract/failure 的关键边界？
7. 如果代码变化，这张图怎样被发现需要更新？
8. 删除这张图后，团队会失去什么 decision capability？如果答案是“没有”，也许它不值得维护。

## 13. 这篇旁支不教什么

这里不要求背 UML diagram taxonomy，也不指定 PlantUML、Mermaid、draw.io 或 C4 tooling。工具应该服从 audience、diffability、维护成本和表达需要。

本课程只保留 Modeling 最重要的一条：**好的模型不是系统的缩略海报，而是为了回答某个 engineering question，刻意选择 abstraction、暴露关键关系，并能被 evidence challenge 的 reasoning artifact。**

材料来源与取舍见 [`reading-notes/extensions-source-audit.md`](../reading-notes/extensions-source-audit.md)。
