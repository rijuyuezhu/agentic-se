---
id: lab-M02
type: lab
visibility: student
related: [M02]
---
# Lab 02 — 收敛 TaskForge 的 State Ownership

本实验对应 M02。

目标不是“把 global variable 换成 class”。

目标是训练下面这条完整链路：

```text
建立 system model
→ 识别泄漏的 design knowledge
→ 找出所有 mutable authority
→ 写 change contract
→ design it twice
→ 最小重构
→ 用 evidence 验证 boundary 真的成立
```

实验代码：

```text
labs/taskforge/
```

---

## Part 0 — Baseline

先运行：

```bash
cd labs/taskforge
uv run --with pytest --no-project python -m pytest
```

记录：

- baseline test 数量；
- 是否全部通过；
- 当前代码总行数；
- `state.jobs` 和 `state.next_job_number` 的所有 read/write site。

不要修改代码。

---

## Part 1 — Read-only Reconnaissance

提交一份不超过两页的 `ownership-map.md`。

必须回答：

### 1. 当前有哪些 authoritative facts？

至少考虑：

- job identity；
- job command；
- job status；
- exit code；
- next job number。

对每个事实写：

```text
Fact:
Current writers:
Current readers:
Current invariant:
Persistence:
Derived copies/views:
Recovery rule:
```

如果某项当前不存在，明确写 `none`，不要猜未来实现。

### 2. Job lifecycle 是什么？

从代码和 tests 反推状态机。

不要只画 happy path。

需要包含：

- queued；
- running；
- succeeded；
- failed；
- cancelled；
- 哪些 transition 当前被拒绝；
- 哪些非法 transition 只是“碰巧没有入口”，而不是由 owner 明确禁止。

### 3. 谁在维护 lifecycle invariant？

列出具体函数。

如果答案不是一个地方，解释这意味着什么。

### 4. 哪些 API 泄漏 representation？

特别检查：

```python
service.get()
service.list_jobs()
worker.claim_next()
```

问：

- 返回值是否携带 mutable authority？
- caller 能否绕过 lifecycle rule？
- 如果底层从 dict 改 SQLite，现有 caller 哪些假设会失效？

### 5. 哪些当前行为是 contract，哪些只是 implementation accident？

例如：

```text
job-N ID 格式
ID 单调递增
claim insertion order
返回 mutable Job object
module global
```

不能只凭“tests 里出现了”就判定为 contract。

写出你的理由。

---

## Part 2 — Design It Twice

在改代码前，必须给出至少两个 design。

### Design A

可以考虑：

```text
Job object owns its own lifecycle
```

### Design B

可以考虑：

```text
JobRegistry owns job collection + transitions
```

你也可以提出第三种方案。

对每个方案比较：

| 维度 | 问题 |
|---|---|
| Information hiding | 隐藏了哪些 design decisions？ |
| State authority | 哪个组件是唯一 mutable owner？ |
| Change amplification | 新增 `CANCELLING` 要改哪里？ |
| Representation independence | dict -> SQLite 时哪些 client 需要变？ |
| Testability | lifecycle policy 能否独立验证？ |
| Failure evolution | 后续 persistence/remote worker 会不会被当前 API 卡住？ |
| Complexity cost | 新增了多少名字、接口和 dependency？ |

最后选一个，并解释为什么另一个在**当前 TaskForge** 下较差。

禁止用下面这些句子作为理由：

```text
“更符合 SOLID”
“用了 repository pattern”
“更 clean”
“更 enterprise”
```

必须落到具体 dependency / invariant / change cost。

---

## Part 3 — Change Contract

实现前写一个短 spec。

至少包括：

### Must preserve

- `submit()` 的外部功能；
- `job-N` ID 格式；
- ID 单调递增；
- claim 当前的 insertion-order 行为；
- queued job 可 cancel；
- running/terminal job 当前不可 cancel；
- finish 只有 running job 可以执行；
- exit code 决定 succeeded/failed。

### Required design properties

- mutable job collection 只有一个 authoritative owner；
- ID allocator 与 job collection 的一致性由同一明确 owner 管理，或给出更强的替代设计理由；
- production code 不允许绕过 owner 直接修改 lifecycle state；
- query API 不向 caller 暴露 authoritative mutable `Job`；
- metrics 只能 read，不获得 mutation authority；
- worker 通过 semantic operation claim/finish，而不是直接操作 collection。

### Non-goals

本实验禁止顺便加入：

- SQLite；
- async/thread lock；
- HTTP；
- remote worker；
- retry；
- new status；
- dependency injection framework。

这条限制很重要：

> **设计练习的价值来自减少变量，而不是一次性“架构升级”。**

---

## Part 4 — Implement

实现你的设计。

建议采用 small-step change：

1. 先建立 owner，但保持现有调用路径；
2. 把一个 writer 迁移进去；
3. 跑 tests；
4. 迁移剩余 writers；
5. 收紧 query boundary；
6. 删除旧 mutable access path；
7. 再跑 tests 和 search evidence。

每一步尽量保持可运行。

---

## Part 5 — Required New Evidence

除了 baseline tests，至少增加以下证据。

### 1. Query isolation test

证明：

```text
caller 修改 query result
```

不会改变 authoritative state。

你可以使用 frozen view、copy 或其他设计；但解释 trade-off。

### 2. Transition ownership test

至少验证一个非法 transition 确实由 owner 拒绝，而不是因为“当前没有一个 caller 恰好去做”。

### 3. Repository search evidence

用搜索证明 production code 中：

```text
没有模块绕过 owner 直接写 job lifecycle state
```

注意：

> grep 只能证明你没有找到某种 syntactic write；它不能单独证明完整 correctness。

因此必须同时提供 design argument。

### 4. Representation-change thought experiment

写 5–10 行：

```text
如果下一模块把 dict 换成 SQLite，哪些 production clients 不需要改？
哪些地方仍然会改？
为什么？
```

---

## Part 6 — Agent Version

这个实验要做两遍中的一部分。

### Round A — Vague prompt

在一个干净副本上，让 coding Agent：

```text
重构 TaskForge 的状态管理，让它更干净、更可维护。
```

记录：

- Agent 先读了什么；
- 它是否建立 writer map；
- 是否改了 observable behavior；
- 是否过度抽象；
- 是否真正消除了 direct writer；
- tests 是否足以证明它的结论。

不要为了让 Round A 好看而给额外提示。

### Round B — Engineering spec

重新从 baseline 开始，把 Part 1–3 的成果提供给 Agent。

要求 Agent：

1. 先复述 current authority map；
2. 指出 planned change surface；
3. 实现；
4. 给 tests + search + diff summary；
5. 主动列出它不能证明的事情。

比较两轮：

```text
patch size
unnecessary churn
contract drift
number of review findings
review time
```

不要只比较“谁写得代码少”。

---

## Part 7 — Independent Review

实现完成后，假设这是别人写的 PR。

重新 review，至少检查：

- 是否真的只有一个 mutable owner；
- owner 是语义 owner，还是只是把 globals 包进一个 class；
- lifecycle knowledge 是否仍被复制；
- read API 是否仍泄漏 mutable object；
- tests 是否把 implementation accident 固化成 contract；
- abstraction 是否过深/过浅；
- 是否为了未来 SQLite 过早造了 generic repository framework；
- non-goals 是否被破坏；
- change 是否足够局部。

至少写一个你最担心的 future change：

```text
add CANCELLING
add SQLite
add remote worker
```

并用它 pressure-test 当前设计。

---

## 评分标准

### 25% — System model

不是看图漂亮，而是 writer/read/invariant 是否准确。

### 20% — Design argument

必须比较至少两个真实可行设计。

### 25% — Implementation

重点是 authority 是否真正收敛，不是 class 数量。

### 20% — Evidence

测试、搜索、thought experiment 是否与 claim 对得上。

### 10% — Agent comparison

能否具体说清楚 vague prompt 与 engineering spec 导致的差异。

---

## 完成标准

如果你最后只能说：

> “我把 globals 改成了 JobRegistry，所以现在更面向对象了。”

这个 lab 没完成。

你应该能够说：

> **“TaskForge 中 job lifecycle 的 authoritative mutation 现在只经过 X；Y/Z 只能发 semantic command 或读取 immutable projection；因此 lifecycle invariant 有唯一 enforcement point。将 representation 从 dict 换成 SQLite 时，service/worker/metrics 的哪些接口不需要变化，我可以逐一解释并用 tests/search 支撑。”**

这才是本实验要训练的能力。
