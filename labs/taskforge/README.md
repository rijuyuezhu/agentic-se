# TaskForge

TaskForge 是本课程的贯穿实验系统。

它不是“最佳实践示例仓库”，而是一个**经过设计的、会逐步演化的 teaching system**：每个版本只引入足够支撑当前模块的复杂度，并故意保留后续课程需要发现和修复的问题。

## 当前版本：v0 / M02–M07 teaching baseline

core 仍只有四类行为：

- submit job；
- worker claim job；
- worker finish job；
- query/cancel/metrics。

它目前完全在内存中运行，不包含：

- SQLite；
- HTTP；
- async；
- remote worker；
- retry；
- crash recovery。

这些不是遗漏，而是刻意的 non-goals。课程先把 **abstraction / ownership / testing / boundary semantics** 看清，再逐步加入 mechanism complexity。

## 运行测试

如果有 `uv`，最省事：

```bash
PYTHONPATH=src uv run --with pytest --no-project python -m pytest
```

或者先安装 editable test dependencies：

```bash
python -m pip install -e '.[test]'
python -m pytest
```

课程仓库的 baseline 已实际运行过：`6 passed`。这个数字只说明当前 observable examples 通过；它**不**说明 M02 的 ownership 设计已经良好。

## 重要规则

第一次阅读时不要立刻重构。

先完成 `../02-state-ownership.md` 的 read-only reconnaissance：

1. 列出所有 state writers；
2. 列出所有 state readers；
3. 写出 lifecycle invariant；
4. 区分 contract 与 implementation accident；
5. 画 authority map。

如果一看到 module global 就直接“套 repository pattern”，你会错过本实验最重要的训练：**先建立 system model，再决定 abstraction。**

## 为什么 baseline tests 不直接把所有设计问题测出来

因为设计问题往往不是“当前输入会返回错误值”。

一个实现可以：

```text
所有 tests 都绿
```

同时仍然具有：

```text
高 change amplification
information leakage
split authority risk
representation exposure
```

M02 的目标就是学会在 bug 出现之前识别这类结构风险，并把其中能够转化为 contract 的部分补成可执行证据。

## M03：用 meaningful mutants 检查测试是否有“牙齿”

完成 M02 后，进入 [`../03-testing-evidence.md`](../03-testing-evidence.md)。

课程提供一个**不会修改工作区**的小型 mutation probe：

```bash
PYTHONPATH=src uv run --with pytest --no-project python tools/mutation_probe.py
```

baseline 已实际验证：

```text
3 killed, 3 survived
```

这里的目标不是追 mutation score，而是逐个解释：

```text
这个 mutant 破坏了哪条 contract？
现有 oracle 为什么看不见？
怎样用最小、behavior-oriented 的 test 暴露它？
```

## M04：starter public boundary

M04 新增一个刻意较浅的 external-style boundary：

```text
src/taskforge/public_api.py
```

它已经做对一件事：把 mutable internal `Job` 转成 detached public view，因此不会重新暴露 M02 的 authoritative object handle。

但它仍故意保留：

```text
blank command accepted
KeyError leaks across boundary
cancel failure collapses to False
no request identity / idempotency contract
```

运行：

```bash
PYTHONPATH=src uv run --with pytest --no-project python tools/m04_boundary_probe.py
```

然后进入 [`../04-api-error-boundary.md`](../04-api-error-boundary.md)。

这里仍不加入 HTTP/gRPC framework；M04 要训练的是 API semantics，而不是框架配置。

## M05：把 change sequence 本身当作设计对象

M05 增加：

```text
src/taskforge/dashboard.py
tools/m05_behavior_probe.py
```

`dashboard.py` 当前功能正确，但故意把 status/count interpretation 和 text formatting 缠在一起。新需求是增加 JSON renderer；课程要求先比较 direct duplication 与 preparatory refactoring 两条路径。

运行：

```bash
PYTHONPATH=src uv run --with pytest --no-project python tools/m05_behavior_probe.py
```

课程 baseline 已实际验证：

```text
[OK] empty: sha256=eaadf634b7104332
[OK] queued: sha256=ec17ac5523b4b8bd
[OK] mixed: sha256=1181854b1e08cc1c
all existing text dashboard behavior preserved
```

M05 的 structural phase 不允许更新这些 expected outputs 来“让测试变绿”；如果真的要改变 text behavior，那应成为独立 behavior change。

完整实验：[`../05-refactoring-evolutionary-design.md`](../05-refactoring-evolutionary-design.md)。

## M06：故意引入一个 legacy integration module

M06 新增：

```text
src/taskforge/legacy_audit.py
tools/m06_legacy_probe.py
```

`legacy_audit.py` 没有 unit tests，直接读取 global job state、env、UTC time、hostname，并 append 文件和写 stdout。这里不是为了展示“坏代码”，而是为了制造真实 takeover 条件：**现有行为有人可能依赖，但我们没有完整 spec。**

先不要重构。运行：

```bash
PYTHONPATH=src uv run --with pytest --no-project python tools/m06_legacy_probe.py
```

课程 baseline 已实际 characterize：

```text
empty
mixed lifecycle
same-day append
```

probe 利用 Python module binding、环境变量和 temporary directory 控制 nondeterminism，因此第一阶段不需要修改 production code。完整实验见 [`../06-legacy-code-takeover.md`](../06-legacy-code-takeover.md)。

## M07：把 race 与 crash window 变成 deterministic evidence

M07 新增：

```text
src/taskforge/concurrent_claim.py
src/taskforge/effect_delivery.py
tools/m07_interleaving_probe.py
```

`concurrent_claim.py` 故意保留 check-then-act race；probe 用 `threading.Barrier` 强制两个 worker 都先观察同一个 `QUEUED` job，因此不会靠 `sleep()` 或压力循环碰运气。`effect_delivery.py` 则故意把 external effect 与 local completion record 分开，用 explicit failpoint 展示 crash 后 retry duplication。

运行：

```bash
PYTHONPATH=src uv run --with pytest --no-project python tools/m07_interleaving_probe.py
```

课程 baseline 已实际验证：

```text
one queued job -> two successful claim receipts
effect happened -> crash -> retry -> duplicate external effect
record-first ordering -> possible lost effect
```

完整实验见 [`../07-concurrency-lifecycle-failure.md`](../07-concurrency-lifecycle-failure.md)。
