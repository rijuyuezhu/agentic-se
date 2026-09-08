---
id: source-M05
type: source_audit
visibility: student
related: [M05]
---
# M05 Source Audit — Refactoring 与 Evolutionary Design

> 审计/复核日期：**2026-09-06**。

> 目标：确认哪些材料真的能支撑“怎样安全改变已有软件的内部结构”，而不是因为某本书或某个流派很有名就照搬。
>
> 本模块特别区分三件事：**refactoring、behavior change、large restructuring/migration**。如果材料把它们混成一个词，本课程不会照抄。

---

## 0. 本模块要回答的问题

M05 关注：

1. 什么才算 refactoring？
2. 为什么 small step 比“大改完再测试”更容易建立 correctness argument？
3. structure change 与 behavior change 为什么值得分开？
4. 什么时候应该先重构再加功能，什么时候应该直接改，甚至什么都不整理？
5. 大范围机械变更怎样保持每个中间状态可测试、可 review、可回退？
6. Agent 能一次改很多文件后，为什么 change decomposition 反而更重要？

需要避免的口号：

- “重构就是把代码写漂亮”；
- “技术债必须先还完再开发”；
- “每次 feature 前都应该先做一轮 cleanup”；
- “small PR 就等于低风险”；
- “测试绿了，所以 structural change 一定 behavior-preserving”；
- “Agent 可以一次性全仓重构，因为它不会累”。

---

## 1. Martin Fowler — Refactoring, 2nd ed. / Refactoring Guide

**状态：主干采用（refactoring 的定义、small-step mechanics、preparatory refactoring）**

实际检查：

- [1. Martin Fowler — Refactoring, 2nd ed. / Refactoring Guide — source 1](https://martinfowler.com/books/refactoring.html)
- [1. Martin Fowler — Refactoring, 2nd ed. / Refactoring Guide — source 2](https://martinfowler.com/bliki/DefinitionOfRefactoring.html)
- [1. Martin Fowler — Refactoring, 2nd ed. / Refactoring Guide — source 3](https://martinfowler.com/bliki/RefactoringBoundary.html)
- [1. Martin Fowler — Refactoring, 2nd ed. / Refactoring Guide — source 4](https://martinfowler.com/bliki/RefactoringMalapropism.html)
- [1. Martin Fowler — Refactoring, 2nd ed. / Refactoring Guide — source 5](https://martinfowler.com/articles/workflowsOfRefactoring/fallback.html)
- [1. Martin Fowler — Refactoring, 2nd ed. / Refactoring Guide — source 6](https://martinfowler.com/articles/preparatory-refactoring-example.html)

### 实际内容支持什么

Fowler 对 refactoring 的定义很窄：

```text
internal structure changes
+
observable behavior unchanged
```

而且不是“一次大手术”，而是一串小的 behavior-preserving transformations。

这意味着：

```text
系统连续坏两天
然后一次性重新跑通
```

不应被本课程称为 refactoring；那更接近 restructuring / rewrite。

Fowler 的材料还明确解释了 small steps 的工程意义：

- 每一步错误空间更小；
- 出问题时最近一步就是高概率 suspect；
- 系统在重构过程中保持 working；
- 可以在较长时间里渐进完成，而不需要建立一个长期 broken branch。

### Two Hats

`Workflows of Refactoring` 明确区分：

```text
Refactoring hat:
    observable behavior 不变

Adding-function hat:
    observable behavior 改变
```

它不是说真实开发里不能频繁切换两顶帽子，而是说**某一个具体 change step 应知道自己在做哪一种事**。

这和本课程 M05 的 change ledger 直接对应：

```text
step 1: characterize old behavior
step 2: structural move
step 3: structural move
step 4: new behavior
```

如果 step 2 顺手改了 semantics，那么 reviewer 的证明负担会突然变大。

### Preparatory Refactoring

Fowler 的 preparatory refactoring 例子支持一个很强但有边界的 workflow：

```text
当前结构让目标 feature 很别扭
        ↓
先把结构移动到更适合承载 feature 的形状
        ↓
再做真正的 behavior change
```

它不是“先清理所有看不爽的代码”。

课程采用的判断标准是：

> 这次 structural change 是否直接降低即将发生的 behavior change 的复杂度/影响面？

如果答案只是“以后也许有用”，优先级要显著降低。

### 局限

Fowler 的 catalog 很有用，但 M05 不会要求背七十多个 refactoring 名称。

原因：

- 名称不是判断力；
- IDE 已能机械完成很多局部 refactoring；
- Agent 也很擅长 symbol move / rename / extraction；
- 真正困难的是决定 **为什么改、改到什么边界、怎样证明没改 behavior、怎样切片**。

所以 catalog 只作 lookup reference。

---

## 2. Kent Beck — Tidy First? (2023)

**状态：选择性主干采用（structure/behavior separation、batch size、timing、reversibility）**

实际检查了 O'Reilly 可公开访问的目录和正文预览：

- [2. Kent Beck — Tidy First? (2023) — source 1](https://www.oreilly.com/library/view/tidy-first/9781098151232/)
- [2. Kent Beck — Tidy First? (2023) — source 2](https://www.oreilly.com/library/view/tidy-first/9781098151232/part01.html)
- [2. Kent Beck — Tidy First? (2023) — source 3](https://www.oreilly.com/library/view/tidy-first/9781098151232/ch16.html)
- [2. Kent Beck — Tidy First? (2023) — source 4](https://www.oreilly.com/library/view/tidy-first/9781098151232/ch18.html)
- [2. Kent Beck — Tidy First? (2023) — source 5](https://www.oreilly.com/library/view/tidy-first/9781098151232/ch19.html)
- [2. Kent Beck — Tidy First? (2023) — source 6](https://www.oreilly.com/library/view/tidy-first/9781098151232/ch20.html)
- [2. Kent Beck — Tidy First? (2023) — source 7](https://www.oreilly.com/library/view/tidy-first/9781098151232/ch21.html)
- [2. Kent Beck — Tidy First? (2023) — source 8](https://www.oreilly.com/library/view/tidy-first/9781098151232/ch23.html)

### 为什么它值得加入

它比很多“clean code”材料更明确地区分：

```text
behavior change
vs
structure change
```

Chapter 16 `Separate Tidying` 直接讨论把二者混在一起会让 change 难以理解。

Chapter 18 `Batch Sizes` 不给固定行数，而是讨论：

- 为下一次行为变化到底需要多少结构变化；
- 多大的 batch 容易 integrate/deploy；
- batch 增大时 review、冲突、失败定位成本怎样上升。

Chapter 19 更进一步强调 tidy 的 rhythm 通常应该很短；如果在行为变化前连续整理很久，很可能已经脱离了“为当前变化铺路”的最小集合。

Chapter 21 的标题本身很重要：

```text
First / After / Later / Never
```

也就是说 Beck 并不主张“永远 tidy first”。它要求把 timing 当 trade-off。

### Getting Untangled

Chapter 20 对 Agent 时代尤其有价值：

当 structure change 与 behavior change 已经缠在一起时，选项包括：

- 直接交一个混合 change；
- 花力气重新拆分；
- 丢弃混合实现，根据已经获得的理解重新做一条更清晰的 change chain。

课程会保留第三个选项。

这是一个很反直觉但实际重要的 Agent workflow：

> Agent 第一次探索性实现可以只是为了获得理解；如果 diff 已经不可 review，**不要因为代码已经生成就产生 sunk-cost attachment**，可以让 Agent 从 clean base 重新按 staged plan 实现。

### 局限

`Tidy First?` 是一本有明确个人哲学色彩的小书，不是实证定律汇编。

尤其：

- “tidying”是 Beck 自己定义的 refactoring 子集；
- 书的个人级开发节奏不能直接映射到所有组织/发布流程；
- economics / optionality 的比喻有启发性，但不能假装成精确 ROI 模型。

本课程主要吸收它的 **change separation 与 timing framework**。

---

## 3. Google Engineering Practices — Small CLs

**状态：主干采用（reviewability / rollback / independently working changes）**

实际检查：

- [3. Google Engineering Practices — Small CLs — source 1](https://google.github.io/eng-practices/review/developer/small-cls.html)
- [3. Google Engineering Practices — Small CLs — source 2](https://google.github.io/eng-practices/review/developer/cl-descriptions.html)
- [3. Google Engineering Practices — Small CLs — source 3](https://google.github.io/eng-practices/review/reviewer/looking-for.html)

### 实际内容支持什么

Small CLs 页面给出的理由不是“GitHub 看起来整洁”，而是具体工程成本：

- review 更快、更彻底；
- 更容易 reasoning about impact；
- bug probability 更低；
- 如果方向错误，浪费更少；
- merge conflict 更少；
- rollback 更简单。

它对 “small” 的定义也不是固定 LOC：

> 一个 self-contained change。

页面甚至明确说：

- 100 行常常合理；
- 1000 行常常太大；
- 但没有 hard-and-fast rule；
- 一行复制到几百个文件可能比 20 行复杂 side effect 更容易 review。

这正好支持课程的观点：

```text
semantic size != diff line count
```

### 对 refactoring 的直接建议

页面明确提出：

- 可在 refactoring 前先独立提交 tests，以确认现有行为；
- test refactor / framework work 也可拆开；
- 如果 feature change 太大，考虑先做 refactoring-only CL 为后续铺路；
- 每个中间 CL 提交后系统仍应正常工作。

这与 Fowler 的 technical small-step reasoning 形成组织层面的补充。

---

## 4. Software Engineering at Google — Large-Scale Changes

**状态：主干采用（当“small local refactoring”扩展到全仓/跨团队时）**

实际检查：

- [4. Software Engineering at Google — Large-Scale Changes — source 1](https://abseil.io/resources/swe-book/html/ch22.html)
- [4. Software Engineering at Google — Large-Scale Changes — source 2](https://abseil.io/resources/swe-book/html/ch09.html)

### 为什么 M05 要提前讲一点 LSC

Agent 时代一个典型诱惑是：

```text
既然 Agent 可以修改 500 个文件，
那就一次性改 500 个文件。
```

Google 的 Large-Scale Changes 章节提供了非常现实的反例。

其核心观察是：代码库和参与者变大后，**可实际提交的最大 atomic change 反而下降**，因为：

- test closure 变大；
- review ownership 变复杂；
- merge conflict 增多；
- 一个原子回滚难以做到；
- 多仓库时原子提交甚至不存在。

Google 因而把 logically-related master change **shard 成可以独立测试、review、提交的 pieces**。

这一点非常适合迁移到 coding agent：

```text
Agent 可以生成 master transformation
        ↓
工程系统仍应把它切成 independently verifiable shards
```

不是因为 Agent 打字慢，而是因为验证、review、integration 和 rollback 才是瓶颈。

### 重要边界

Google 自己也明确说明：LSC 不只包含 behavior-preserving refactoring，也可能包含功能影响。

因此：

```text
LSC != refactoring
```

课程不会混用这两个词。

---

## 5. Stanford CS190 / APOSD — Design it Twice 与 revision

**状态：辅助采用（设计探索与 revision mindset）**

实际检查：

- [5. Stanford CS190 / APOSD — Design it Twice 与 revision — source 1](https://web.stanford.edu/~ouster/cs190-winter24/)
- [5. Stanford CS190 / APOSD — Design it Twice 与 revision — source 2](https://web.stanford.edu/~ouster/cs190-winter24/lectures/aposd/)

课程描述明确使用：

```text
implementation → review → revision
```

而 APOSD discussion 中包含 `Design it twice`。

M05 吸收的不是“每次实现都真的写两套生产代码”，而是：

> 在结构变化成本还低时，至少认真构造两个 design candidate，再比较 change amplification、dependency、reversibility 和 migration path。

这与 M02 的 design judgment 联动。

局限同前：这是 Ousterhout 的设计哲学，不当作普适定律。

---

## 6. 本轮不进入主干的材料

### Working Effectively with Legacy Code

不是因为不好，而是主要价值在：

- characterization tests；
- seams；
- dependency breaking；
- difficult-to-test legacy takeover。

这些更适合 M06，避免 M05/M06 重复。

### Clean Code

M05 不用它定义 refactoring。

原因不是“完全没价值”，而是其小函数/cleanliness framing 容易把 structural change 的目标误写成 aesthetic cleanliness；本模块更需要行为保持、change sequence 和 reviewability 的精确定义。

### 大型架构重写案例

暂时不进入 M05。

它们经常把 migration、compatibility、deployment、data ownership 混在一起，更适合 M08/M09。

---

## 7. M05 最终采用的 synthesis

```text
Fowler
  ↓
什么叫 refactoring；small behavior-preserving steps；preparatory refactoring

Kent Beck / Tidy First?
  ↓
structure vs behavior；batch size；first/after/later/never；untangle/restart

Google Small CLs
  ↓
reviewability；integration；rollback；self-contained change

Google Large-Scale Changes
  ↓
大变更也应被 sharding，而不是追求巨大 atomic diff

Stanford CS190
  ↓
design it twice；review → revision
```

课程自己的 Agent 层再加：

```text
Agent exploration
    ↓
behavior inventory
    ↓
refactoring plan with semantic checkpoints
    ↓
small structural patches
    ↓
independent evidence after every checkpoint
    ↓
behavior change in a separate patch
    ↓
final cross-diff review
```

核心不是“让 Agent 少写代码”。

恰恰相反：

> **因为 Agent 可以瞬间制造巨大 diff，所以我们更需要人为控制 change topology。**
