# M02 Reference Analysis — TaskForge v0

> **Spoiler warning**：先完成 `labs/02-state-ownership.md` 的 Part 1，再看本文件。

这不是唯一正确答案，而是一份 instructor reference，用来检查实验题本身是否 grounded。

---

## 1. 当前 authority map

### Job identity

当前事实：

```text
job-N
```

生成位置：

```text
service.submit()
```

依赖：

```text
state.next_job_number
```

问题：allocator 是 module-level mutable global；`reset_for_tests()` 也能直接重写它。

### Job collection

当前 storage/authority 实际是：

```text
state.jobs: dict[str, Job]
```

但并没有真正的单一 semantic owner，因为多个模块拿到内部 `Job` 后直接 mutation。

### Job status

production writers：

```text
service.cancel()
worker.claim_next()
worker.finish()
```

额外绕过路径：

```text
service.get()
service.list_jobs()
worker.claim_next()
```

都会返回 authoritative mutable `Job`，所以任何 caller 也能成为 writer。

因此严格来说，writer set 不是只有源码里出现 `.status =` 的几个函数，而是：

```text
所有拿到 Job reference 的 caller
```

这正是单纯 grep 不足以证明 authority 的例子。

### Exit code

writer：

```text
worker.finish()
```

但同样可通过 exposed mutable `Job` 绕过。

### Metrics

`metrics.py` 目前只是 reader：

```text
queued_count()
terminal_count()
```

它直接依赖 `state.jobs` representation，因此虽然没有 mutation authority，仍有 information leakage。

---

## 2. 当前 lifecycle

从实现可以推导：

```text
QUEUED
  ├── claim_next() -> RUNNING
  └── cancel()     -> CANCELLED

RUNNING
  ├── finish(0)    -> SUCCEEDED
  └── finish(!=0)  -> FAILED
```

`cancel()` 对：

```text
RUNNING
SUCCEEDED
FAILED
CANCELLED
```

返回 `False`。

`finish()` 对非 `RUNNING` 抛 `ValueError`。

但这些规则并没有一个统一 lifecycle owner。

更严重的是 query exposure 可以直接制造：

```text
QUEUED -> SUCCEEDED
QUEUED -> FAILED
CANCELLED -> RUNNING
```

等任意非法 transition。

实际验证：

```python
job_id = service.submit("echo hi")
job = service.get(job_id)
job.status = JobStatus.SUCCEEDED
assert service.get(job_id).status == JobStatus.SUCCEEDED
```

baseline 中这个 mutation 成功。

所以“当前没有 public `succeed_queued_job()` 函数”并不等于这个非法 transition 不可达。

---

## 3. 当前设计知识如何泄漏

### Leakage A — collection representation

以下模块都知道全局状态是：

```text
dict[str, Job]
```

- `service.py`
- `worker.py`
- `metrics.py`

如果换 SQLite，这三个模块都需要直接重写。

### Leakage B — lifecycle rules

`service.cancel()` 知道：

```text
running/terminal 不可 cancel
```

`worker.claim_next()` 知道：

```text
queued 可以 -> running
```

`worker.finish()` 知道：

```text
只有 running 能 finish
exit_code == 0 -> succeeded
```

这些 rule 分布在不同 owner candidate 中。

新增 `CANCELLING` 时需要跨模块 reasoning。

### Leakage C — insertion-order scheduling

`worker.claim_next()` 通过直接遍历 dict values 实现：

```text
first queued by insertion order
```

当前 behavior 与 Python dict insertion ordering 绑定。

这个行为到底是不是 contract，需要课程设计者/需求方明确，而不能仅凭实现猜。

本 lab 为了可重复变更练习，把它明确列入 Must preserve。

### Leakage D — terminal set

`Job.terminal` 目前把 terminal knowledge 局部化得相对好：

```text
SUCCEEDED / FAILED / CANCELLED
```

这反而是一个正例。

但它并不足以完整拥有 lifecycle，因为 transition permission 仍在别处。

---

## 4. 哪些是 contract，哪些是 accident

### 本 lab 明确视为 contract

为了让 refactor 是 behavior-preserving 的：

- ID 形式 `job-N`；
- 单调递增；
- claim insertion order；
- queued 可 cancel；
- running/terminal 当前不可 cancel；
- finish only from running；
- exit code 0/nonzero 的结果语义。

这些不是因为“现有代码这样写所以天然是 contract”，而是 lab specification 主动将其选为必须保持的 observable behavior。

### 明确不是 desired contract

- `state.jobs` 是 dict；
- `state.next_job_number` 是 module global；
- client 可以直接 mutation `Job`；
- worker 直接遍历 collection；
- metrics 直接 import state module。

这些都是 implementation decisions / design smells，不应被新的测试无意固化。

---

## 5. 两种合理 design 方向

### Design A — Job owns local transition rules

例如：

```text
Job.claim()
Job.cancel()
Job.finish(exit_code)
```

优点：

- 单对象 lifecycle invariant 靠近 data；
- transition rules 集中。

不足：

- collection、ID allocation 仍需要 owner；
- `claim_next` selection policy 不属于单个 Job；
- 后续 SQLite transaction 可能要求更高层协调 mutation + persistence；
- 如果把 mutable Job 发给 caller，仍可能 exposure。

因此即使用这种方案，也需要认真设计谁持有真实 Job instance。

### Design B — JobRegistry owns collection + lifecycle

例如语义操作：

```text
submit
get/list immutable views
claim_next
cancel
finish
reset/testing support
```

优点：

- collection、ID allocation、transition enforcement 可收敛；
- worker/metrics 不再依赖 dict representation；
- dict -> SQLite 的 change surface 更局部。

风险：

- Registry 可能逐步变 god object；
- executor/process concerns 不应该未来全部塞进 Registry；
- storage mechanism 与 business policy 是否继续在同一类，需要在 M05/M08/M09 重新判断。

对当前非常小的 TaskForge，Design B 通常是更直接的 teaching solution，但不是因为“Registry pattern 更高级”。

---

## 6. 什么不算真正修复

### Fake fix 1

把：

```python
state.jobs
```

搬进：

```python
class JobRegistry:
    jobs = {}
```

但继续让：

```python
registry.jobs[id].status = ...
```

这只是换了命名空间，没有收敛 authority。

### Fake fix 2

给 `jobs` 加 underscore：

```python
registry._jobs
```

但所有 production module 仍直接访问。

Python 的 underscore 是 convention，不是 semantic boundary。

### Fake fix 3

创建 `Repository` interface，但：

```text
service
worker
metrics
```

仍然自己解释 lifecycle rules。

这只隐藏 storage，没有隐藏 lifecycle knowledge。

### Fake fix 4

为了未来 SQLite 一次性创建：

```text
GenericRepository
UnitOfWork
EventBus
CommandBus
DependencyContainer
```

这会让 M02 baseline 从浅薄 boundary 直接跳到 speculative architecture。

没有当前 evidence 支撑。

---

## 7. Query isolation 为什么是一个合适的新 contract

当前：

```python
service.get(job_id)
```

返回 authoritative mutable object。

这不是单纯 style 问题，它会破坏 lifecycle invariant：caller 可以绕过 transition API。

因此 M02 要求把“query 不授予 mutation authority”升级成新的明确 contract。

可行实现包括：

- frozen `JobView`；
- copy；
- immutable tuple/named structure；
- 其他能证明 isolation 的设计。

这里不规定唯一 mechanism，因为课程要训练：

```text
property first, implementation second
```

---

## 8. 为什么 baseline tests 全绿仍然不够

实际 baseline：

```text
6 passed
```

它们证明了若干 examples：

- submit；
- claim；
- finish；
- cancel；
- metrics。

但没有证明：

- query isolation；
- single authority；
- representation independence；
- lifecycle rules 只有一个 enforcement point。

这正是本实验的核心教学点：

> **tests 能证明你写进去的 property；它们不会自动发现你从未表达过的 design property。**

---

## 9. Instructor sanity check

本 lab 的 M02 问题已经通过三种独立证据确认：

### Static search

搜索实际发现 production 代码中：

```text
service
worker
metrics
```

均直接依赖 `state.jobs`，且 service/worker 有多个 mutation site。

### Runtime exploit

实际执行确认：

```text
service.get() 返回对象被 caller mutation
-> authoritative state 同步改变
```

### Baseline tests

使用：

```bash
uv run --with pytest --no-project python -m pytest
```

实际得到：

```text
6 passed
```

因此这个教学例子不是“代码本来坏掉，所以当然要重构”；它满足预期条件：

```text
observable examples work
but ownership boundary is structurally weak
```

这正适合 M02。
