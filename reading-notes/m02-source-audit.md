# M02 Source Audit — Abstraction / Information Hiding / State Ownership

审计日期：2026-09-05

本文件记录 M02 实际查看过的材料，以及哪些观点被采用、哪些只作为 heuristic。

目标不是证明某位作者“权威”，而是回答：

```text
这个来源实际教了什么？
有没有具体 reasoning / exercise / review evidence？
它覆盖到什么规模？
哪些地方不能直接外推？
```

---

## 1. MIT 6.102 — Abstract Data Types

来源：

https://web.mit.edu/6.102/www/sp25/classes/06-abstract-data-types/

### 实际检查到的内容

该 reading 明确把 ADT 定义为：

- 由 operations 与各自 specifications 定义；
- abstract values 对 client 是 opaque 的；
- concrete representation 属于 implementation；
- good ADT 应该 simple、coherent、adequate、representation independent。

它进一步用 `MyString` 展示同一个 abstract type 可以有不同 concrete representation，只要 operations 的 contract 不变。

### 为什么进入 M02 主线

这不是泛泛的“encapsulation is good”。它给了一个可以检查的设计性质：

```text
representation 改变时，client 是否必须改变？
```

这正好可以变成 code review / Agent task 的 pressure test。

### 局限

- 核心单位是 ADT/object；
- 主要讨论单进程、小到中等规模 construction；
- 没有直接给出 service/process/persistent ownership 模型。

因此 M02 只把 representation independence 的 reasoning 提升到更大边界，不声称 MIT 6.102 本身提出了本课程的 state-ownership taxonomy。

---

## 2. MIT 6.102 — Abstraction Functions & Rep Invariants

来源：

https://web.mit.edu/6.102/www/sp26/classes/07-abstraction-functions-rep-invariants/

### 实际检查到的内容

reading 明确区分：

```text
AF : R -> A
RI : R -> boolean
```

并说明：

- creator/producer 要建立 invariant；
- mutator/observer/producer 要保持 invariant；
- representation exposure 会破坏这种保证；
- `checkRep()` 等机制可以把 invariant violation 更早定位到 owner 内部。

### 为什么进入 M02 主线

它给出了一个比“private field”更强的封装标准：

> 如果 client 能拿到并修改 representation，那么 owner 就无法再证明 invariant。

这直接支持 TaskForge 的 `get()/list_jobs()` mutable exposure 教学点。

### 不直接外推的地方

AF/RI 是 ADT-level formalization。M02 后半段的：

```text
semantic authority
storage
replica/cache
view/projection
```

是本课程为了分析长期系统演化做的工程化扩展，不应伪装成 MIT 原文术语。

---

## 3. Stanford CS190 — Modular Design

来源：

https://web.stanford.edu/~ouster/cgi-bin/cs190-spring16/lecture.php?topic=modularDesign

以及：

https://web.stanford.edu/~ouster/cgi-bin/cs190-winter18/lecture.php?topic=modularDesign

### 实际检查到的内容

lecture notes 明确讨论：

- module interface 包含 formal 与 informal aspects；
- information hiding 的目标是让 design decision 不必被其他 module 理解；
- information leakage 是 implementation detail / design knowledge 跨模块传播；
- `private` variable 并不能自动保证 information hiding；
- temporal decomposition 是常见 leakage：按执行时间顺序切模块，可能把同一 design knowledge 分散出去；
- 看到 leakage 时，应检查能否把相关 information 合并到一个更有意义的地方。

### 为什么好

它不是只给定义。课程会在学生项目上追问：

```text
这个 class 的 unique value 是什么？
它隐藏的 key knowledge 是什么？
```

因此适合训练 design judgment。

### 风险

CS190 使用 class-oriented vocabulary 很多。

M02 必须主动把：

```text
class
```

推广成：

```text
module / component / service / process / state owner
```

否则学生可能错误地以为“信息隐藏 = OO class design”。

---

## 4. Stanford CS190 — Code Review 2

来源：

https://web.stanford.edu/~ouster/cgi-bin/cs190-winter21/codeReview2.php

### 实际检查到的内容

presenter 被要求对每个 class 说明：

- key idea；
- 隐藏了哪些 information/design decisions；
- 考虑过哪些 alternate designs；
- API 的关键部分。

reviewer 则在 persistence、RPC 等真实 subsystem 上检查这些设计选择。

### 为什么重要

这证明 CS190 的 information hiding 不是只在 lecture 里出现，而是进入了实际 review protocol。

因此 M02 lab 要求 `design it twice`、authority map、independent review，不是为了增加文书，而是在复现“设计必须可解释、可被别人攻击”的训练方式。

---

## 5. Stanford CS190 — Project 2 Revision

来源：

https://web.stanford.edu/~ouster/cgi-bin/cs190-winter21/raft2.php

### 实际检查到的内容

Project 2 明确要求：

```text
根据 Project 1 code review 修改/refactor 原设计
```

并要求学生写 `changes` 文件解释最重要的结构变化。

它还特别提醒：新功能的 rough design 可能反过来要求修改现有 structure。

### 为什么进入课程方法

这支持本课程的：

```text
review -> revision
```

而不是“第一次架构设计就是最终答案”。

---

## 6. Stanford CS190 — Raft Project 2 Review/Discussion

来源：

https://web.stanford.edu/~ouster/cgi-bin/cs190-winter21/lecture.php?topic=raftReview2-2021

### 实际检查到的内容

这份 review notes 很有价值，因为它展示具体失败模式：

- 太多 shallow classes 导致更多 interface/dependency；
- 某个 Message 层发现 socket EOF/error，却因为不拥有 socket 而无法完成 cleanup，需要把信息继续传给 owner；
- getters/setters 和过细方法会制造 ordering requirements；
- 暴露 Lock/Unlock 让 client 承担内部 synchronization knowledge。

### 为什么进入 M02

这里能看到“ownership”不是一个抽象口号：

```text
发现 failure 的组件
!=
拥有 resource/lifecycle authority 的组件
```

如果边界设计得不好，就会产生额外 information flow 与 temporal coupling。

### 限制

这些仍是特定 C++/Raft 学生项目的经验性 review，不能直接推导“所有类都应该更大”。

---

## 7. Ousterhout / APOSD 的使用方式

作者页：

https://web.stanford.edu/~ouster/cgi-bin/aposd.php

本章采用的核心观点主要通过公开的 CS190 HTML lecture/review notes 交叉检查，而不是因为书名知名就直接照搬。

采用：

- complexity / cognitive load / change amplification；
- deep vs shallow module 作为 heuristic；
- information hiding / leakage；
- temporal decomposition；
- design it twice。

不接受成无条件规则：

- “class 越 deep 越好”；
- “small class 一定坏”；
- “general-purpose 一定优于 domain-specific”；
- 可以靠 API method count 计算 module depth。

---

## 8. 关于 Parnas

Stanford modular-design notes 把 David Parnas 的 *On the Criteria To Be Used in Decomposing Systems into Modules* 作为 information hiding 的重要来源。

当前 M02 **没有把该论文作为已完成的一手材料审计项**。

原因：本轮课程编写实际使用的是 Stanford 官方 lecture notes 与 MIT 6.102 正文；没有必要为了“经典论文”三个字就假装已经完成逐段审阅。

后续如果把 Parnas 论文加入必读，应单独获取可靠全文并审计：

- 两种 decomposition 示例究竟怎样比较；
- “design decision likely to change”在原文中的精确范围；
- 哪些例子因 1970s tooling/architecture 背景已经过时；
- 其 modularity argument 与现代 service boundary 的外推是否成立。

在完成这一步之前，它只作为 historical pointer，不作为本章独立 evidence。

---

# 结论

M02 的主线并不是把三份材料拼起来，而是从它们得到三个经过实际内容验证的基础：

```text
MIT 6.102:
    abstraction = operations/specs, not representation
    representation independence
    invariant ownership / rep exposure

Stanford CS190:
    information hiding = localize design knowledge
    interface includes informal dependencies
    decomposition must be judged by change/understanding cost
    review -> revision
```

然后课程进一步提出用于长期系统和 Agent review 的分析框架：

```text
authority
storage
replica/cache
view
writer map
invariant enforcement point
recovery rule
```

这个后半部分是课程自己的综合模型，应当用后续 TaskForge、真实 repo case study 与 failure analysis 持续验证，而不是因为前面引用了名校课程就自动视为正确。
