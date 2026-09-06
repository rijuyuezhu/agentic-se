# M00 — 软件工程到底在优化什么？

这门课不会从 UML、Scrum 或某个设计模式名词开始。我们先追一个更基础的问题：一个程序已经“能跑”以后，为什么还会越来越难改？如果 Agent 可以把实现速度再提高一个数量级，这个问题会消失，还是会变得更尖锐？

我们会一直围绕 TaskForge 的一个小需求展开。它最开始只像几行代码，随后不断加入真实系统里无法回避的条件。等这些条件把原来的直觉逼到极限，再给我们需要的工程概念命名。

## 1. 一行 `cancel(job_id)` 什么时候不再只是编程题

假设 TaskForge 现在只是一个很小的后台任务程序：

```text
submit(command)
   ↓
queue
   ↓
worker
   ↓
run command
   ↓
store result
```

产品提出一个很自然的需求：增加 `cancel(job_id)`。

如果整个程序只有两百行，而且 job 只存在一个进程的内存里，最直接的实现可能就是：

```python
jobs[job_id].cancelled = True
```

worker 真正执行前再检查：

```python
if job.cancelled:
    return
```

在这个世界里，问题主要是 programming：状态放在哪里、分支怎么写、测试怎样覆盖。实现也许十分钟就能完成。

现在只改一个条件：worker 可能已经开始执行 command。`cancelled = True` 还代表什么？如果 subprocess 仍在跑，把 job 标成 cancelled 是不是在对 caller 撒谎？于是我们加一个 `CANCELLING` 状态，worker 在安全点观察 cancellation request，再决定何时进入 terminal state。

接着再改一个条件：`cancel` 和 worker 从 QUEUED 切到 RUNNING 可能同时发生。现在不能只问“哪条 if 先执行”，还要问系统允许哪些 transition、谁拥有决定权，以及 caller 最终应该观察到什么。

再加入 crash/restart。client 已经收到“取消成功”，daemon 随后崩溃。如果 cancellation request 只写在内存里，重启后它消失了。那之前的 success 到底承诺了什么？

再把 worker 放到另一台机器上。再允许 client 因 timeout 重试请求。再考虑旧 client 不认识新状态、数据库里已有旧 row、外部 command 已经产生不可撤销 side effect。原本的“一行功能”开始要求我们回答一组彼此关联的问题：

- 哪个组件对 job lifecycle 拥有最终 authority？
- `cancel` 成功时，caller 可以依赖什么事实？
- 哪些状态组合永远不能出现？
- 并发 transition 冲突时，哪一个结果合法？
- crash、timeout 和 retry 之后，之前的承诺还成立吗？
- 新旧代码、旧数据和不同 client 同时存在时，行为怎样保持可解释？

这里发生了一个重要变化。我们不再只是在构造一段能完成计算的代码，而是在维护一个会长期变化、被多个组件和修改者共同依赖的软件系统。

可以把 **programming problem** 粗略理解为：怎样构造程序，使它在给定条件下完成所需计算。数据结构、算法、parser、kernel、单个函数的正确性都属于这个范围。

而本课程所说的 **software engineering problem** 更关心：当软件会持续变化时，怎样让人仍然能够理解它、说明它应该满足什么、局部修改它，并拿出足够证据相信修改没有破坏别处。

两者不是竞争关系。Software engineering 建立在 programming 之上。只是系统的寿命、规模、状态和修改者数量上升以后，“我能写出这段代码”不再足以推出“这个系统还能被安全地继续改”。*Software Engineering at Google* 强调的时间维度与这里很接近：软件工程的问题会在代码跨越更长时间尺度以后显现出来。

## 2. 复杂度通常在“下一次修改”时才暴露

回到刚才新增的 `CANCELLING`。假设你改完 domain model 后发现，还必须修改 serializer、数据库 schema、CLI rendering、API response、metrics、migration 和一批 tests。

这不自动证明设计很差。一个真实的新状态本来就可能影响多个 externally observable surface。更值得追问的是：**这些修改中，哪些来自需求本身，哪些只是因为同一份知识被复制到了太多地方？**

软件特别容易把这种问题积累起来，因为局部修改的表面成本很低。加一个 flag、复制一段判断、临时 hardcode 一个特殊 case、再包一层 adapter，单独看都可能是当时最便宜的决定；代价往往要到后来的修改者必须同时理解这些历史分支时才出现。没有哪一次 commit 明显“把系统搞坏”，但 system model 会被一点点侵蚀，直到没人能确信一个局部 change 的影响面在哪里结束。

所以复杂度不只来自某个函数本身很难读。它也来自很多局部合理决定长期叠加以后，knowledge 被复制、时序被隐含、依赖变得不可发现。

John Ousterhout 在 *A Philosophy of Software Design* 中用 change amplification、cognitive load 和 unknown unknowns 来讨论复杂度。这里把它们当成三个很有用的观察角度，而不是经验定律或可机械计算的质量分数。

### 2.1 Change amplification：一个概念为什么要改这么多地方

如果每个 caller 都自己维护一份“哪些 job state 可以 cancel”的集合，那么新增 `CANCELLING` 时，你必须找到所有复制过这条规则的位置。漏掉任何一个，系统就出现语义分叉。

相反，有些扩散是不可避免的。新状态要显示在 UI，也许就必须增加一个文案；要持久化，也许就必须更新 schema。工程判断不在于“修改文件越少越好”，而在于区分 **essential change surface** 和 **duplicated knowledge 带来的 accidental change surface**。

一个实用的警报是：如果修改一个核心概念以后，你只能靠全仓 grep 并“希望自己找全了”，就值得检查这份 knowledge 是否缺少明确 owner。这个警报不是定罪；有些横切关注点本来就会跨多个边界，但它至少提醒 reviewer 追问扩散原因。

### 2.2 Cognitive load：复杂度也可以被推给 caller

再看一个与 TaskForge 不同的小接口：

```python
conn = Connection(...)
conn.open()
conn.authenticate()
conn.begin()
conn.send(payload)
conn.flush()
conn.commit()
conn.close()
```

每个 method 单独看都很短，但如果 caller 还必须记住“authenticate 只能在 open 后调用”“失败后要 rollback”“close 前某些路径必须 flush”，那么真正复杂的东西没有消失，只是变成了 caller 脑中的隐式 protocol。

另一个 API 可能只暴露：

```python
client.request(payload)
```

内部实现更复杂，却能让每个 caller 少记很多时序细节。

这说明一个后面会反复出现的事实：**软件复杂度可以被移动。** 好的 abstraction 往往不是让所有代码都变简单，而是把不可避免的复杂度放到拥有足够信息、可以统一维护、不会让很多调用者重复承担的位置。

### 2.3 Unknown unknowns：最危险的是你不知道还该看哪里

change amplification 至少还意味着你知道有很多地方要改；cognitive load 至少意味着你知道自己需要记很多规则。更危险的是 hidden dependency 根本没有进入你的 mental model。

例如另一个系统里有：

```python
def normalize_user_id(x):
    return x.lower()
```

把它改成 preserve case 看起来只是一个局部函数变化，但某个数据库可能把大小写敏感字符串当 key，某个 cache 也许用 lower-case key，而一段离线脚本又依赖原格式。如果这些关系没有通过 interface、dependency、documentation、test、type 或明确 ownership 暴露出来，修改者甚至不知道该去找什么。

所以“代码可读”并不等于“系统可安全修改”。后者还要求 **relevant knowledge discoverable**：当一个概念变化时，修改者有办法恢复足够完整的 system model，而不是靠历史记忆和运气。

LOC、函数长度、cyclomatic complexity 之类指标仍然可能给出信号，但它们不能替代这个问题：**为了正确完成一次变化，我必须理解多少东西？我又凭什么知道自己已经理解够了？**

## 3. 三种复杂度症状把我们逼向四个工程对象

前面的例子似乎涉及很多不同问题：状态、API、数据库、并发、migration、tests。为了不让课程也变成一堆术语，我们把后续主线压缩成四个反复出现的对象：Boundary、Contract、Invariant 和 Change。

它们不是凭空挑出的四个名词，而是分别回答刚才 cancellation story 中不同的压力。

### 3.1 Boundary：哪些知识可以被隔在另一侧

如果每个 caller 都必须理解 SQLite schema、worker thread、subprocess lifecycle 和 retry 细节，TaskForge 即使目录里有很多 module，也没有真正形成有用边界。

boundary 的价值在于给修改者一个可以停止向下展开 mental model 的地方。只要对方遵守约定，我就可以暂时忽略它内部大量 mechanism。后面的 M02 和 M04 会继续讨论怎样画这种边界，以及为什么“多包一层函数”并不会自动隐藏知识。

### 3.2 Contract：边界两侧到底允许依赖什么

`cancel(job_id) -> bool` 的 signature 并没有告诉我们 success 是否表示 request durable、subprocess 已经退出，还是 merely accepted。它也没有说明 missing job、terminal job 和 running job 怎样区分。

contract 的作用就是把这些可依赖语义说清楚。它让 caller 不必知道内部怎样实现，也让 implementation 知道哪些行为不能在重构时悄悄改变。下一章会专门把这个概念展开。

### 3.3 Invariant：无论从哪条路径修改，什么都不能坏

TaskForge 可能有很多 operation：submit、reserve、finish、cancel、recovery。它们可以由不同代码路径触发，但某些事实必须始终成立，例如 terminal state 不能偷偷回到 RUNNING，或者同一个 job 不应该同时存在两个都被视为 authoritative 的 active attempt。

这种跨 operation、跨代码路径仍必须保持的性质就是 invariant。它往往比某一个函数的实现寿命更长，也是之后 tests、database constraint、state machine 和 review 可以共同围绕的对象。

### 3.4 Change：设计必须在过渡状态里也说得通

很多“漂亮”的静态结构在升级时会暴露问题。新增 `CANCELLING` 后，旧 worker 能读新 row 吗？一半 worker 已升级、一半没升级时合法吗？新数据写进去以后还能 rollback 吗？

因此软件设计不是只描述一个最终架构。系统从旧版本走到新版本的过程本身也是工程对象。M05、M08、M10 和后面的 production 模块会不断回到这个视角。

到这里，可以给出本课程的工作定义：**Software Engineering 是建立、表达和维护软件中的 boundaries、contracts、invariants 与 mental models，使复杂系统能够在人或 Agent 持续修改时仍保持可理解、可验证和可演化。**

这是一种课程建模方式，不是在声称整个软件工程学科只能被这四个词定义。传统 requirements、process、economics、security、professional practice 等内容仍然重要，只是本课程把“受控变化”作为主干组织中心。

## 4. 模块化想限制的是一次修改所需知道的范围

“high cohesion, low coupling”很容易背，也很容易在 review 时失去操作性。更具体的问题是：**完成一个局部变化时，我能否只理解少数几个模块，并确信边界另一侧的细节不会突然变成隐藏前提？**

这要求的并不是“module 越多越好”。假设一次简单 storage call 被拆成 `AService -> AServiceImpl -> ARepository -> ARepositoryAdapter -> AStorageGateway`，每层都原样转发同一组参数。concrete dependency 的形状也许改变了，但 navigation、命名、同步 interface 的成本都上升，而 caller 能忽略的知识并没有增加。

这就是 shallow abstraction 的典型风险。Ousterhout 的 deep-module vocabulary 在这里很有用：我们关心的是 interface 背后隐藏了多少有意义的 complexity，而不是拿 interface 行数除以 implementation 行数算一个分数。这个原则也有边界——不能因为追求“深”就提前造一个什么都能做的万能 framework。

换句话说，modularity 的目标不是目录整齐，而是**限制 change 所需传播的 knowledge**。后面我们会用 information hiding、state ownership、dependency direction、stable contract 和 boundary-oriented evidence 把这句话变成可 review 的东西。

## 5. Agent 让 implementation 更便宜，却不会自动补上 system model

coding agent 可以让一个需求很快变成几十个文件的 patch。这个能力本身很有价值，但它不会自动提高一个系统中 contract、ownership 和 hidden dependency 的清晰度。

如果任务只有：

```text
给 TaskForge 加 job cancellation，补测试。
```

一个 Agent 可能做得很好，也可能非常合理地沿着它看到的局部 pattern 扩散实现：API 加一份判断、worker 再加一份、内存里顺手缓存一份 cancellation state，然后写一组只证明自己实现路径的 tests。这里的问题不需要归因于“Agent 笨”；task 本身就没有表达足够 engineering knowledge。

同一个任务如果在实现前先形成下面这样的 artifact，搜索空间就不同了：

```text
Current model
- durable job lifecycle has one authoritative owner
- all state transitions pass through the same transition boundary

Desired behavior
- define queued/running/terminal cancellation semantics explicitly
- successful acknowledgement has an explicit durability meaning

Must preserve
- terminal-state invariant
- no second authoritative cancellation state
- existing submit behavior unless the spec says otherwise

Unknowns to resolve before coding
- cancel vs finish race
- restart after acknowledgement
- external side effects that cannot be interrupted

Evidence
- behavior table
- race/restart cases
- tests that distinguish the required semantics from plausible wrong ones
```

有价值的不是 prompt 变长，而是人或负责设计的 Agent 先建立了 **system model、desired behavior、invariant 和 evidence plan**。实现者可以探索代码，但不需要自己猜哪些语义有权改变。

因此在 Agent 时代，瓶颈很可能从“代码写得够不够快”更多转向：我们是否知道应该为真什么？修改范围是否被合理约束？证据能否独立区分正确实现与一个看起来完整但语义错误的 patch？

本课程会反复训练一个 loop：先建立 model，再定义 task contract，随后实现，最后由独立视角检查 evidence。Agent 可以承担大量 implementation effort，但 engineering authority 不能仅由实现者自己的总结自动获得。

## 6. 软件工程也不是“更多 abstraction”或“预测所有未来”

看到 coupling、change amplification 和 hidden dependency 以后，一个很自然但危险的反应是：那就多加 interface、多做 extension point、把所有东西都 generic 化。

这会把另一种复杂度提前带进系统。每一层 abstraction 都需要命名、导航、同步 contract，也会创造新的错误组合。如果它没有隐藏真实复杂度，只是因为某个 pattern “看起来正规”，那它可能让系统更难理解。

同样，软件会变化也不意味着我们应该准确预测每种未来需求。为几十个从未出现的 variation point 预留机制，会让今天每一次修改都承担 speculative complexity。

更现实的目标是：当前 contract 足够清楚；重要 knowledge 有明确 owner；修改有能区分对错的 evidence；真正昂贵、难逆转的决定被识别出来；未来需求真的出现时，我们仍有安全 refactor 和 migration 的路径。

所以“为变化设计”更接近 **降低改变主意的成本**，而不是提前把未来全部编码进去。后面的 evolutionary design 模块会专门讨论这个边界。

## 7. 从今天开始可以使用的四组 Review Questions

在还没有学完后续细节以前，先用四组问题检查任何模块或 change：

### Boundary

- 这个模块让 caller 可以忽略哪些知识？
- caller 是否仍被迫知道本应属于内部的 schema、时序或 failure mechanism？

### Contract

- 合法输入、成功、错误和 side effect 分别意味着什么？
- 哪些 behavior 是调用者可以依赖的，哪些只是当前 implementation accident？

### Invariant

- 哪些性质在所有合法状态中都必须成立？
- 谁拥有这些事实，哪里负责 enforcement？

### Change

- 下一次相关变化会扩散到哪里，为什么？
- 有哪些 dependency 可能根本没有进入我们的 system model？
- rollout、migration 或 rollback 期间是否仍保持合法状态？

这些问题目前还很粗。M01–M04 会依次把 contract、ownership、evidence 和 boundary 变成更精确的推理工具。

## 8. 三个练习：不要先从代码量评价工程质量

### 8.1 “功能正确”够不够

找一个你最近写过或维护过的 feature。暂时不要看 diff，先写出它改变了哪些 externally observable behavior、哪些 invariant 必须保持、谁拥有新增 state，以及如果实现完全重写哪些 tests 理论上仍应通过。

再回头看真实 patch。哪些改动只是实现方式，哪些地方其实暴露了你之前没有写出来的 contract？

### 8.2 画一张 change-amplification map

选一个 repo 中真实概念，例如 `job status`、`user role` 或 `config path`。列出知道它的模块，并区分：authoritative owner、read-only consumer、serialization boundary、test-only knowledge、疑似 duplicate knowledge。

然后假设新增一个 value。逐项解释哪些修改是需求本身不可避免的，哪些只是 knowledge leakage 造成的。不要用“改了 N 个文件”直接下结论。

### 8.3 做一次 Agent 对照实验

对同一个中等规模 change 做两轮。第一轮只给功能描述，让 Agent 直接实现。第二轮先禁止修改代码，只让它建立 system map、state owner、current contract、invariants 和 affected boundaries；你修正这个 model 后再允许实现。

比较两轮的 diff、错误修改位置、review comment、测试 oracle 和你自己解释“为什么这个 patch 正确”所需要的时间。这个练习的目标不是证明第二种 prompt 永远更好，而是观察 **implementation effort 与 engineering understanding 是否是同一个瓶颈**。

## 9. 继续往下：先回答“什么必须为真”

如果把本章压缩成一句话，可以说：**软件工程是在变化中控制复杂度，使系统仍然能够被理解、验证和安全修改。**

TaskForge 的 cancellation 让我们看到，困难很快从“代码怎么写”转向“系统应该承诺什么、哪些状态合法、谁负责保持这些事实”。下一章就从这里继续：在判断一个 implementation 对不对之前，我们先学会写清楚 Specification、Contract 与 Invariant。

### 可选原始材料

本章的 design vocabulary 与材料取舍可先看 [`../MATERIALS_REVIEW.md`](../MATERIALS_REVIEW.md)，尤其是 Stanford CS190 / *A Philosophy of Software Design* 与 *Software Engineering at Google* 的审查记录。进一步可读：

- Stanford CS190 Introduction: https://web.stanford.edu/~ouster/cgi-bin/cs190-winter21/lecture.php?topic=intro
- *A Philosophy of Software Design* 官方页: https://web.stanford.edu/~ouster/cgi-bin/aposd.php
- *Software Engineering at Google* 前言: https://abseil.io/resources/swe-book/html/pr01.html
