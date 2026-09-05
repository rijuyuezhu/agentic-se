# M06 Source Audit — Legacy Code、Characterization Test 与 Seam

> 本模块的问题不是“怎样把旧代码写漂亮”，而是：**当现有行为不清楚、测试不足、依赖难以控制时，怎样先获得足够 feedback，再安全地改变系统。**
>
> 仍沿用本课程的材料审计规则：经典程度不是证据；只有实际检查过正文、样章、官方文档或足够具体的公开内容，才进入主线。

---

# 0. 本模块要回答的问题

M06 需要回答六个工程问题：

1. “legacy code” 对本课程来说到底意味着什么？
2. 当我们不知道正确 specification 时，characterization test 在证明什么？
3. 为什么很多旧代码“难测”其实是 dependency / observability 问题？
4. seam 是什么？它和“为了测试到处依赖注入”有什么区别？
5. 怎样选择 change point、test point、sensing point，而不是把整个系统一次性拆开？
6. Agent 接管陌生 legacy repo 时，怎样避免一上来就重构、补 mock、重写？

本模块特别避免以下口号化理解：

- “legacy code = 年代久远的代码”；
- “legacy code = 烂代码”；
- “先把测试覆盖率补到 80% 再改”；
- “characterization test 就是把当前所有 bug 永久合法化”；
- “seam = interface / dependency injection framework”；
- “为了 unit test 必须把所有 I/O 都 mock 掉”；
- “Agent 能读完整 repo，所以不需要先建立 feedback”。

---

# 1. Michael Feathers — Working Effectively with Legacy Code

**状态：M06 主干来源。**

已实际检查：

- InformIT 官方书页和完整目录：
  - https://www.informit.com/store/working-effectively-with-legacy-code-9780132931779
- InformIT 公开样章 `Changing Software and Legacy Code`：
  - https://www.informit.com/articles/article.aspx?p=359418
- InformIT 公开样章 `Testing Effectively With Legacy Code`：
  - https://www.informit.com/articles/article.aspx?p=359417
- seam 小节：
  - https://www.informit.com/articles/article.aspx?p=359417&seqNum=2
  - https://www.informit.com/articles/article.aspx?p=359417&seqNum=3
- O'Reilly 公开预览：Chapter 3 `Sensing and Separation`：
  - https://www.oreilly.com/library/view/working-effectively-with/0131177052/ch03.html
- O'Reilly 公开预览：Chapter 4 `The Seam Model`：
  - https://www.oreilly.com/library/view/working-effectively-with/0131177052/ch04.html
- O'Reilly glossary：
  - https://www.oreilly.com/library/view/working-effectively-with/0131177052/gloss.html
- O'Reilly 目录 / Chapter 13 位置：
  - https://www.oreilly.com/library/view/working-effectively-with/0131177052/toc.html
- Pearson/InformIT sample PDF 的目录，确认 Chapter 13 内确实包含 `Characterization Tests`、`Targeted Testing` 与 writing characterization tests heuristic：
  - https://www.informit.com/content/images/9780131177055/samplepages/0131177052.pdf

## 1.1 为什么这本书仍然值得放主干

不是因为它 2004 年出版后“很经典”，而是因为它处理的问题与 Agent 时代仍然高度同构：

```text
我需要改一个系统
↓
我不知道哪些行为有人依赖
↓
我没有快速 feedback
↓
我又很难把目标代码单独运行
↓
怎样把风险逐步压低？
```

书的目录本身就不是按 pattern 名称组织，而是按真实困境组织：

```text
I can’t get this class into a test harness
I don’t know what tests to write
Dependencies on libraries are killing me
I don’t understand the code well enough to change it
My application has no structure
I need to change a monster method
How do I know that I’m not breaking anything?
```

这与本课程强调的“从工程问题出发，而不是背规则”非常匹配。

## 1.2 “legacy code = code without tests”如何使用

Feathers 最著名的 operational definition 是把 legacy code 与缺乏 tests 联系起来。

本课程**吸收它作为风险 framing，但不把它当字典定义**。

原因是现实里有三种情况：

```text
A. 20 年旧系统，但关键行为有强测试、稳定 contract、快速反馈
B. 昨天生成的新模块，没有可靠 oracle，只有 happy-path smoke test
C. 测试很多，但全是 implementation-coupled mocks，无法支持安全变化
```

按工程风险看，B/C 可能比 A 更“legacy”。

因此本课程采用更宽的定义：

> **Legacy condition = 你需要改变代码，但缺少足够快速、可信、与目标变化相关的 feedback。**

年龄、语言和 style 都不是核心变量。

## 1.3 Working with Feedback

书的 Part I 明确把 `Working with Feedback` 放在 seam 之前。

这是一个非常重要的顺序：

```text
不是：
先重构成 testable architecture
再写测试

而是：
先问怎样尽快得到 feedback
必要时只做最小 dependency breaking
再把 change 放进 feedback loop
```

这会成为 M06 的主线。

## 1.4 Sensing 与 Separation

Chapter 3 公开预览明确讨论：目标对象很难放进 test harness，常常不是因为算法复杂，而是因为构造它会拖进越来越多 collaborators，最后接近整个系统。

Feathers 把测试需求拆成两个不同问题：

```text
Sensing
= 我怎样观察代码产生了什么效果？

Separation
= 我怎样让目标代码与不希望真实运行的依赖分开？
```

这一区分非常强。

例如一个函数：

```text
读取系统时间
读环境变量
写文件
打印 stdout
调用数据库
更新内存状态
```

你可能有：

```text
能调用它，但看不见内部结果      → sensing problem
根本没法调用，因为依赖真实 DB    → separation problem
```

两者需要不同技术，不应统一归类成“加 mock”。

## 1.5 Seam Model

InformIT / O'Reilly 的公开 Chapter 4 material 明确给出 seam 的核心思想：

> 一个位置，在不直接修改该位置代码的情况下，可以改变程序在这里采用的行为。

并且 seam 有 **enabling point**：实际决定替代行为的位置。

本课程把 seam 看成：

```text
production flow
    │
    ├── real dependency
    │
    └── alternate behavior
          ↑
     enabling point
```

关键不是有没有 `IClock`、`Repository` 或 DI container。

Python module binding、function parameter、filesystem path、process boundary、link-time substitution、environment adapter 都可能成为 seam。

## 1.6 Characterization Test

WELC glossary 的公开预览把 characterization test 定义为：

> 用来记录当前软件行为，并在代码变化时保存这种行为的测试。

这和 specification test 的认识论位置不同：

```text
specification test:
“根据我们认为应该成立的 contract，这个结果应该是 X”

characterization test:
“当前系统在这个受控实验中实际表现为 X；在理解清楚前不要无意改变它”
```

characterization test 首先是**观测和固定事实**，不是价值判断。

### 一个重要边界

如果 characterization test 发现：

```text
buggy_behavior = true
```

不等于课程要求永远保留这个 bug。

正确流程是：

```text
先记录当前行为
↓
判断它是 intended contract / tolerated quirk / known bug / unknown
↓
如果要改变，显式写新的 behavioral change contract
↓
让旧 characterization test 被有意识地更新/替换
```

这和“测试当前行为所以当前行为都正确”完全不同。

## 1.7 Targeted testing 比“全面补测试”更重要

WELC Chapter 11–13 的结构非常明确：

```text
我需要改哪里？
↓
哪些方法受到影响？
↓
应该在哪里放 test point？
↓
如果不知道 expected behavior，就 characterization
```

这支持本课程拒绝：

```text
先给整个 repo 补到 X% coverage
```

更现实的问题是：

> 对当前 change 的 effect graph，哪些观察点能以最低成本覆盖最高风险？

---

# 2. Martin Fowler — Legacy Seam

**状态：主干采用，用现代语言重新解释 Feathers seam。**

来源：

- https://martinfowler.com/bliki/LegacySeam.html

实际检查内容：

- seam 的 Feathers 定义；
- enabling point；
- 通过 function parameter 打开 seam 的示例；
- seam 不只用于 unit testing，也可用于 probes、observability、legacy displacement。

## 为什么重要

Fowler 2024 的总结特别适合修正一个常见误区：

```text
seam = 为 unit test 注入 mock
```

实际上 seam 可以支持：

```text
replace dependency for test
insert a probe
redirect data flow
route old implementation to new implementation
incremental modernization
```

这让 M06 与后面的 M08/M09 连起来：

> **一个为了获得 feedback 打开的 seam，未来也可能成为 migration boundary。**

但反过来不能因此提前把每个调用点都抽象成 interface。

---

# 3. Software Engineering at Google — Testing Overview / Hermetic Testing

**状态：补充采用，用来校正“隔离一切”的误区。**

已检查：

- Testing Overview：
  - https://abseil.io/resources/swe-book/html/ch11.html
- Larger Testing：
  - https://abseil.io/resources/swe-book/html/ch14.html
- CI / Hermetic Testing：
  - https://abseil.io/resources/swe-book/html/ch23.html
- Test Doubles：
  - https://abseil.io/resources/swe-book/html/ch13.html

## 3.1 为什么 legacy takeover 需要 hermeticity

Google 对 hermetic test 的解释把两个价值说得很清楚：

```text
determinism
+
isolation
```

对于 legacy code，这尤其重要。

如果 characterization test 每次运行都因为：

```text
真实时间
真实网络
共享数据库
用户 HOME
机器 hostname
外部服务状态
```

得到不同结果，那么它没有形成稳定 feedback loop。

因此打 seam 的一个实际目的就是：

> **把“环境的不确定性”与“我们想观察的 legacy behavior”分开。**

## 3.2 但 hermeticity 与 fidelity 有张力

Google Larger Testing 明确把 hermeticity 与 fidelity 视为两个不同维度，而且它们经常冲突。

所以 M06 不教：

```text
unit test 越 isolated 越高级
```

一个全 mock 的 legacy unit test 可能：

```text
非常 deterministic
但 fidelity 极低
```

反过来，一个 process-level characterization test 可能更慢，但能覆盖真实文件格式、排序、env semantics。

课程建议建立分层 feedback：

```text
cheap local characterization
+
focused seam-based tests
+
少量 high-fidelity regression probe
```

而不是只追一个层级。

## 3.3 Test doubles 的边界

Google Test Doubles 章节明确总结了 mock framework 过度使用造成的大量维护成本，并出现“容易写、难维护、很少抓 bug”的经验。

这对 Agent 特别重要，因为 Agent 很擅长快速生成：

```text
mock_clock
mock_fs
mock_repo
mock_worker
mock_every_method
```

然后得到一个看起来很精细的绿色测试集。

M06 要问的是：

> 这些 doubles 是否真的帮助 sensing / separation，还是只是复制 implementation interaction？

---

# 4. 本模块怎样使用 WELC，而不是照搬 2004 年的技术目录

WELC 的很多具体 dependency-breaking techniques 带有当时的 Java/C++/C# 背景。

例如：

```text
subclass-and-override
link seam
preprocessor seam
extract interface
parameterize constructor
```

这些技术今天仍可能有价值，但本课程不会要求记 technique catalog。

我们抽取更稳定的 decision process：

```text
1. 明确 change point
2. 画 effect sketch / dependency cone
3. 找 observation point
4. 找阻止测试的 dependency
5. 选择最小 seam
6. 先 characterization
7. 验证 characterization 真能失败
8. 再做 behavioral change
9. 重新判断哪些旧行为应该继续保护
```

具体 technique 由语言和系统决定。

---

# 5. M06 的课程 synthesis

本模块把来源综合成以下模型：

```text
                unknown existing system
                         │
                         ▼
                 define change point
                         │
                         ▼
                  effect / risk sketch
                         │
              ┌──────────┴──────────┐
              ▼                     ▼
         sensing problem       separation problem
              │                     │
              └──────────┬──────────┘
                         ▼
                    minimal seam
                         │
                         ▼
                characterization
                         │
                         ▼
               fast trustworthy loop
                         │
                         ▼
                requested behavior change
                         │
                         ▼
                 regression evidence
```

这里最重要的顺序是：

> **先使变化可观察、可验证，再使设计漂亮。**

---

# 6. Agent 时代的额外推论

这是本课程自己的综合，不冒充来源原话。

## 6.1 Agent 的“理解能力”不能替代 feedback

即使 Agent 可以一次读几十万行代码，也不意味着：

```text
它知道所有用户依赖的 runtime behavior
它知道 production 环境中的隐含约束
它知道哪条旧行为其实是 accidental contract
```

所以 legacy takeover 不能退化成：

```text
read repo
→ summarize architecture
→ refactor
```

更可靠的是：

```text
read
→ hypothesize
→ probe
→ characterize
→ falsify/update model
→ change
```

## 6.2 Agent 特别适合做 effect sketch，但必须要求证据

Agent 可以快速搜索：

```text
callers
writers
readers
filesystem paths
env vars
error strings
serialization formats
historical tests
```

但结果应成为一个可检查的 effect sketch，而不是“我已经理解了”。

## 6.3 不要让 Agent 一次性“make it testable”

这是本模块最重要的 Agent anti-pattern 之一。

模糊任务：

```text
Refactor this legacy module to make it testable and clean.
```

非常容易得到：

```text
new interfaces
new dependency container
new DTOs
new exceptions
new test framework helpers
new behavior
```

全部混在一个 diff。

更好的任务是：

```text
Goal:
open one seam around clock/host/filesystem needed for this change.

Must preserve:
current output bytes under the three characterized scenarios.

Non-goals:
no broad architecture cleanup;
no new public API;
no unrelated naming changes.

Evidence:
show fail-before / pass-after or stable characterization fingerprints.
```

---

# 7. 本模块不采用为“定律”的说法

| 说法 | 本课程处理 |
|---|---|
| legacy code 就是旧代码 | 拒绝；核心是 change without trustworthy feedback |
| legacy code 就是没有任何 tests 的代码 | 作为 Feathers 的强 operational framing，不当完整定义 |
| characterization test 证明当前行为正确 | 拒绝；它首先记录事实 |
| 所有旧行为都必须保留 | 拒绝；需分类 contract / quirk / bug / unknown |
| seam 就是 DI interface | 拒绝；seam 是可替换行为的结构机会 |
| 测试越 isolated 越好 | 拒绝；需要 hermeticity/fidelity trade-off |
| 先全面补 coverage 再改 | 拒绝；优先 targeted feedback around change |
| Agent 可以先大规模重构再补测试 | 拒绝；先 feedback，再 change |

---

# 8. 对 M06 课程设计的直接影响

M06 TaskForge 实验会故意提供一个 `legacy_audit.py`：

- 直接读 TaskForge global state；
- 直接读取环境变量；
- 直接读取系统时间和 hostname；
- 直接创建目录、追加文件；
- 直接打印 stdout；
- 没有 unit tests；
- 行为里混合了一些“看起来奇怪但可能已有用户依赖”的格式细节。

新需求不会先让学生“重构”。

第一阶段只能：

```text
read → run → observe → characterize
```

第二阶段才允许为当前变化打开最小 seam。

第三阶段才实现新行为。

这正是本模块要训练的能力。
