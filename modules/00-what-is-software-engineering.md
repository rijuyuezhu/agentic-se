# M00 — 软件工程到底在优化什么？

## 学习目标

学完这一章，你应该能够：

- 区分 programming problem 和 software engineering problem；
- 用 **change amplification / cognitive load / unknown unknowns** 分析复杂度，而不是只看代码行数；
- 理解“模块化”的真正目标是限制一个修改所需理解的系统范围；
- 解释为什么 Agent 降低 implementation cost 后，system modeling 和 verification 反而更重要；
- 对一个需求先问“它会改变哪些 contract/invariant”，而不是马上问“代码写在哪里”。

---

# 1. 从一个看似简单的需求开始

假设你有一个后台任务系统：

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

现在需求说：

> 增加 `cancel(job_id)`。

如果这是一个 200 行程序，你可能很快就写：

```python
jobs[job_id].cancelled = True
```

然后 worker 执行前检查：

```python
if job.cancelled:
    return
```

功能似乎完成了。

但真实系统里立刻出现一串问题：

- job 已经开始执行了怎么办？
- cancel 和 worker “开始执行”同时发生怎么办？
- job 被取消后状态是 `cancelled` 还是 `failed`？
- process crash 后重启，取消状态是否还在？
- cancel API 重试两次是否安全？
- worker 在另一台机器上怎么办？
- subprocess 已经产生 side effect 怎么办？
- 客户端看到 `cancel()` 成功，究竟意味着“请求已记录”还是“进程已停止”？
- 旧版本 client 是否认识新增状态？
- 数据库里已经存在的 rows 怎样迁移？

注意：这些问题大多不是“代码怎么写”的问题。

它们是在问：

- **状态是谁拥有的？**
- **操作的 contract 是什么？**
- **状态机有哪些 invariant？**
- **并发下哪个动作先发生算数？**
- **失败时系统承诺什么？**
- **已有用户会观察到什么变化？**

这就是从 programming 进入 software engineering 的地方。

---

# 2. Programming 与 Software Engineering

一个故意简化但有用的区别：

## Programming

关注：

> **怎样构造一个程序，使它在给定条件下完成计算？**

典型问题：

- 数据结构怎么选？
- 算法复杂度是什么？
- 这个 parser 怎么写？
- 这个 kernel 怎么优化？
- 这个 function 是否正确？

## Software Engineering

关注：

> **怎样让一个会长期变化的软件系统仍然可以被理解、验证和安全修改？**

典型问题：

- 修改这个 feature 为什么需要碰 12 个模块？
- 为什么两处都认为自己拥有同一份状态？
- 这个 API 到底保证什么？
- 这个 test 是在保护 behavior，还是锁死 implementation？
- 这个 failure 为什么能跨 4 层泄漏？
- 这个 migration 能不能逐步部署和回滚？
- 三个月后另一个人如何知道这个奇怪分支为什么存在？

两者不是对立的。

软件工程建立在 programming 之上。但当系统规模、寿命、并发修改者数量增加后，**“写出正确代码”不再等于“构建出可持续的软件”。**

---

# 3. 软件为什么特别容易失控

软件和许多工程对象不同：它的修改成本在表面上非常低。

你不需要重新浇筑混凝土，只要：

```text
edit → compile → deploy
```

于是每个人都很容易做一个局部看起来合理的决定：

- “这里加个 flag 就行”；
- “先复制一份代码，以后再抽象”；
- “这个特殊用户先 hardcode”；
- “这里再加一层 adapter”；
- “异常先 catch 掉”；
- “这个 global cache 顺手从另一层访问一下”。

任何单个决定可能都不致命。

真正危险的是：**复杂度通常是一点一点累积的。**

最后你发现：

```text
需求 X
  ↓
改 A
  ↓
A 隐式依赖 B
  ↓
B 的状态也被 C 修改
  ↓
C 的测试 mock 了 D 的内部调用
  ↓
改 D 后测试失败，但用户行为没变
  ↓
没人敢确认哪一个 failure path 才是 intended behavior
```

这时系统的问题已经不是某一个函数写得不好，而是 **mental model 失效**。

---

# 4. 一个实用的复杂度模型

不要把 complexity 简单等同于 LOC、class 数、函数长度或 cyclomatic complexity。

这些都可能提供信号，但软件工程里更关键的是：

> **一个开发者为了正确完成一个变化，需要理解多少东西？能否知道自己已经理解完整？**

本课程用三个视角分析复杂度。

## 4.1 Change Amplification

一个概念上的小变化，需要修改很多地方。

例如加一种 job state：

```text
model.py
api.py
cli.py
serializer.py
worker.py
metrics.py
ui.py
migration.py
13 tests
```

这不自动说明设计差。有些变化本来就横跨系统。

真正需要问的是：

> 这些修改是否是这个需求的 **本质复杂度**，还是因为一个知识被复制到了很多地方？

典型坏味道：

- 同一状态机规则散落多个模块；
- 每层都知道数据库 schema 细节；
- 每个 client 都自己拼 protocol；
- feature flag 的语义复制到各处。

### 一个判断题

如果你修改一个概念，必须靠 grep 才能“希望找全所有地方”，那通常说明某些 knowledge 没有被一个清晰边界拥有。

---

## 4.2 Cognitive Load

做一次修改前，你必须同时记住多少事情？

例如一个 API：

```python
conn = Connection(...)
conn.open()
conn.authenticate()
conn.begin()
conn.send(...)
conn.flush()
conn.commit()
conn.close()
```

如果：

- 某些调用顺序非法；
- 某些函数只能调用一次；
- 出错后必须额外 rollback；
- close 前必须 flush；

那么接口表面上每个 method 都很简单，但 **调用者承担了大量 temporal knowledge**。

另一种设计可能只有：

```python
client.request(payload)
```

内部更复杂，但调用者更容易正确使用。

这就是一个重要思想：

> **软件复杂度可以被移动。好的 abstraction 往往不是消灭所有复杂度，而是把复杂度放到最合适、最少重复、最容易验证的位置。**

---

## 4.3 Unknown Unknowns

这是最危险的一种：

> 你甚至不知道自己还应该知道什么。

例如你修改：

```python
def normalize_user_id(x):
    return x.lower()
```

看起来完全局部。

但系统某处可能把大小写差异用作数据库 key；另一个脚本依赖原始格式；某个 cache 在升级时不会 invalidation。

如果这些依赖没有通过：

- interface；
- documentation；
- type；
- test；
- ownership；
- build/dependency graph；

被显式表达，那么修改者甚至不知道要去找它们。

这就是为什么“代码可读”还不够。

你需要让 **relevant knowledge discoverable**。

---

# 5. 软件工程的四个核心对象

本课程把大量术语压缩成四个问题。

## 5.1 Boundary — 在哪里切开？

一个模块/服务/对象应该负责什么？

边界的目的不是让目录好看，而是：

> **让修改者可以忽略边界另一侧的大部分细节。**

如果一个模块 API 很小，但所有调用者都必须知道内部 schema、线程模型和 retry 规则，那它并没有真正隐藏复杂度。

---

## 5.2 Contract — 边界两侧承诺什么？

例如：

```python
cancel(job_id) -> bool
```

这个签名远远不够。

你还需要知道：

- job 不存在怎么办？
- 已完成 job 能否 cancel？
- 返回 `True` 的含义是什么？
- 操作是否 idempotent？
- concurrent cancel 怎么办？
- side effect 在返回前是否完成？

contract 决定两边能否独立演化。

---

## 5.3 Invariant — 永远不能坏的性质是什么？

例如 job system：

- 一个 job 同时最多只能有一个 active worker；
- terminal state 不能回到 running；
- `finished_at != None` 时状态必须 terminal；
- 每个 side-effecting execution 都有唯一 attempt id；
- successful API acknowledgement 必须对应 durable state，或者 contract 必须明确不是这样。

代码会变，模块会重构，但 invariant 应跨实现存在。

这也是非常适合交给测试、assertion、type、database constraint、model checker 或 review checklist 的东西。

---

## 5.4 Change — 系统怎样从一个合法状态变成另一个合法状态？

软件设计最终不是静态结构题。

你必须问：

- 新版本和旧版本如何共存？
- migration 中间状态合法吗？
- rollback 怎么办？
- 数据已经写成新格式后旧代码还能读吗？
- 一半 worker 升级、一半没升级时会怎样？

**工程质量最终体现在变化过程中。**

---

# 6. “模块化”真正想得到什么

教科书经常说：high cohesion, low coupling。

这句话没错，但太容易背完就忘。

把它翻译成更有用的问题：

> **完成一个局部变化时，我能否只理解少数几个模块，并确信其他模块的细节不会突然影响我？**

这需要：

- hidden information；
- explicit contracts；
- one clear owner for mutable state；
- dependency direction；
- stable abstractions；
- tests at appropriate boundaries。

所以“模块多”不等于 modular。

极端情况下，把每 20 行代码拆一个 class，反而会产生大量 interface 和依赖，使 cognitive load 更高。

---

# 7. 为什么 Agent 让这个问题更尖锐

过去一个人一天只能产生有限代码。

所以 implementation bandwidth 本身是一个瓶颈。

Agent 可以显著扩大这个 bandwidth：

```text
需求
  ↓
Agent 搜 repo
  ↓
一次改 30 个文件
  ↓
补 40 个 tests
  ↓
CI green
```

这看起来很美好，但注意：

> **代码生成速度增加，不会自动增加你对系统的理解速度。**

甚至可能相反：

- diff 更大；
- 修改并行发生；
- Agent 会自然复制局部 pattern；
- 隐式 assumption 被更快传播；
- 测试可能只证明 Agent 自己假设的 behavior；
- reviewer 更容易被“看起来完整”的 patch 压垮。

于是 bottleneck 从：

```text
How fast can we write code?
```

移动到：

```text
Do we know what should be true?
Can we constrain the change?
Can we verify the result independently?
```

这就是为什么本课程把 **system model → task contract → evidence → review** 当成 Agent workflow 的核心。

---

# 8. 一个对比：两种 Agent 任务

## 任务 A

```text
给 TaskForge 加取消功能，补测试。
```

Agent 可能做得很好，也可能：

- 在 API、worker、DB 各自新增一套 cancel 判断；
- 引入第二份 in-memory state；
- 忘记 crash recovery；
- 测试只覆盖 happy path。

问题不在 Agent “笨”。

问题是任务本身没有表达 engineering knowledge。

## 任务 B

```text
目标：加入 job cancellation。

当前模型：
- SQLite 是 job lifecycle 的唯一 durable authority。
- worker 只能通过 JobRepository 做状态转换。
- terminal states 不能离开 terminal。

要求：
- cancel 必须幂等。
- queued -> cancelled。
- running 的 cancel 只记录 cancellation request；worker 在安全点终止后才进入 cancelled。
- API 返回成功前 cancellation request 必须 durable。
- 不新增第二份 authoritative cancellation state。

Non-goals：
- 本次不支持强杀外部不可中断 side effect。
- 不改现有 submit API。

验证：
- queued cancellation；
- running cancellation；
- repeated cancellation；
- cancel vs finish race；
- process restart after API ack；
- old rows migration。
```

这里真正有价值的不是 prompt 更长。

而是：**人先完成了一部分软件工程 reasoning。**

Agent 的搜索空间被正确约束了。

---

# 9. 软件工程不是“永远多做抽象”

一个常见误区：

> 既然 coupling 不好，那就每层都加 interface。

结果：

```text
A
↓
AService
↓
AServiceImpl
↓
ARepository
↓
ARepositoryAdapter
↓
AStorageGateway
```

但每一层都只转发参数。

这可能降低了某种 concrete dependency，却增加：

- 文件数量；
- navigation cost；
- naming burden；
- interface synchronization；
- indirection。

所以课程一直会追问：

> **这个 abstraction 隐藏了什么真实复杂度？**

如果答案是“没有，只是为了符合模式”，它很可能是 shallow abstraction。

---

# 10. 设计不是预测所有未来

另一个误区：

> 软件会变化，所以我们应该提前让所有东西 extensible。

这会产生 speculative complexity。

更现实的目标是：

1. 当前 contract 清楚；
2. 当前知识有明确 owner；
3. 修改有测试/证据；
4. 对真正昂贵、难逆转的决定保留余地；
5. 当未来需求真实出现时，可以安全 refactor。

也就是说：

> **不是准确预测未来，而是降低改变主意的成本。**

---

# 11. 第一套 Review Questions

以后每看一个模块，都先问：

### Boundary
- 这个模块隐藏了什么？
- 调用者还被迫知道哪些本应隐藏的细节？

### Contract
- 合法输入是什么？
- 输出/错误/side effects 的语义是什么？
- 哪些只是当前 implementation behavior，并未承诺？

### Invariant
- 哪些性质绝不能破坏？
- 谁负责维护它？
- 代码/测试/数据库/类型系统哪里表达了它？

### Change
- 最可能的下一类变化是什么？
- 如果它发生，需要改多少地方、理解多少上下文？
- 有没有 unknown dependency 让我们无法确信影响面？

这四组问题会贯穿整个课程。

---

# 12. 练习

## Exercise 1 — “功能正确”够不够？

找一个你最近写过或维护过的项目，选一个已经完成的 feature。

不要看 diff，先写：

1. feature 改变了哪些 externally observable behavior？
2. 哪些 invariants 必须保持？
3. 哪个模块拥有新状态？
4. 如果把实现完全重写，哪些 test 理论上仍应通过？
5. 哪些 test 如果失败，反而可能说明它们绑定了 implementation detail？

## Exercise 2 — Change amplification map

选一个概念，例如 `job status`、`user role`、`config path`。

在 repo 中列出所有知道这个概念的模块，并标记：

```text
authoritative owner
read-only consumer
duplicate knowledge
serialization boundary
test-only knowledge
```

问：如果新增一个 value，哪些修改是本质必要，哪些是知识泄漏造成的？

## Exercise 3 — Agent 对照实验

对同一中等规模任务做两次：

A. 只给功能描述，让 Agent 实现；

B. 先让 Agent **禁止修改代码**，只建立：

- system map；
- state owner；
- contract；
- invariants；
- affected boundaries；

你人工修正后，再让它实现。

比较：

- diff 大小；
- 被错误修改的文件数；
- review comment 数；
- 测试是否更接近 behavior；
- 是否更容易解释 patch 为什么正确。

---

# 13. 本章结论

把本章压缩成一句话：

> **软件工程是在变化中管理复杂度。**

代码不是最终对象，**可持续修改的软件系统** 才是。

当代码生成越来越便宜时，这个目标不会过时，反而更加重要：

- implementation 可以被大量自动化；
- system model 仍需要被建立；
- contract 仍需要被决定；
- invariants 仍需要被识别；
- evidence 仍需要被解释；
- change 最终仍需要有人承担 engineering authority。

下一章开始，我们把这些抽象词落到第一个可推理工具：**Specification / Contract / Invariant**。

---

## 可选原始资料

本章不依赖这些资料，但推荐用于交叉检查：

- Stanford CS190 Introduction: https://web.stanford.edu/~ouster/cgi-bin/cs190-winter21/lecture.php?topic=intro
- A Philosophy of Software Design 官方页: https://web.stanford.edu/~ouster/cgi-bin/aposd.php
- Software Engineering at Google 前言: https://abseil.io/resources/swe-book/html/pr01.html
