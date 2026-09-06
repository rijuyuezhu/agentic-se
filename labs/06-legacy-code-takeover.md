# Lab 06 — Legacy Takeover：Characterize First, Change Second

> 这一实验故意不给你一个“应该长什么样”的 architecture。
>
> 你接到的是一个**已经能运行、但几乎没有局部 feedback 的旧模块**。任务不是先重构，而是先判断：现在它到底做什么、哪些行为可能有人依赖、为了当前变化最少需要控制哪些依赖。

---

# 0. 场景

目标模块：

```text
labs/taskforge/src/taskforge/legacy_audit.py
```

它负责每天把 TaskForge 当前 job 状态 append 到一个 audit 文件。

它直接依赖：

```text
TaskForge global state
environment variables
UTC clock
hostname
filesystem
stdout
```

它没有 unit tests。

新需求：

> **增加 `failed-only` audit scope。默认 scope 必须保持现有行为；failed-only 只输出 FAILED job，但保留现有 ordering、file naming、append 和 formatting semantics。**

不要一看到这个要求就开始写 feature。

---

# 1. 第一条规则：第一次阅读禁止修改 production code

先运行：

```bash
cd labs/taskforge
PYTHONPATH=src uv run --with pytest --no-project python tools/m06_legacy_probe.py
```

当前课程 baseline 已验证：

```text
[OK] empty
[OK] mixed
[OK] append
legacy audit characterization probe passed
```

注意：这个 probe 不是最终测试设计答案。

它首先是一个 reconnaissance instrument。

---

# 2. Read-only Reconnaissance

阅读：

```text
legacy_audit.py
service.py
state.py
model.py
worker.py
m06_legacy_probe.py
```

写一份 `takeover-notes.md`，至少回答：

## 2.1 Entry point

- 谁调用 `publish_daily_audit()`？
- 当前 repo 是否存在别的 caller？
- 函数返回值有没有 caller？

## 2.2 State reads

列出所有读到的状态：

```text
state.jobs
TASKFORGE_AUDIT_DIR
TASKFORGE_AUDIT_OWNER
clock
hostname
filesystem previous content
```

区分：

```text
semantic input
runtime context
ambient dependency
```

## 2.3 Side effects

至少列：

```text
mkdir
append file
stdout
```

## 2.4 Nondeterminism

哪些东西会让同一 test input 在两台机器得到不同结果？

## 2.5 Error semantics

例如：

- output directory 无权限？
- malformed env path？
- file write 失败？

当前函数如何表现？

不要主动“修好”。先记录。

---

# 3. Behavior Inventory

使用 probe 和你自己的小实验，建立表：

| Behavior | Observed | Specified? | Classification |
|---|---|---|---|
| empty state still writes file | ? | no | unknown |
| file name uses UTC date | ? | no | unknown |
| owner default is `unknown` | ? | no | likely intentional? |
| jobs preserve insertion order | ? | no | possible compatibility |
| exit None renders `-` | ? | no | formatting quirk |
| file ends each block with `--\n` | ? | no | format surface |
| same-day second run appends | ? | no | likely important |
| stdout contains path | ? | no | possible operator surface |

不要把 `Observed` 自动写成 `MUST`。

---

# 4. 画 Effect Sketch

这次 change point 是：

```text
job selection by scope
```

画出：

```text
scope
  ↓
selected jobs
  ├─ count
  ├─ numbering
  ├─ ordering
  ├─ status/exit rendering
  ├─ written bytes
  └─ stdout count
```

然后标：

```text
哪些已有 characterization 覆盖？
哪些是新 feature test 必须覆盖？
```

---

# 5. 区分 Sensing 与 Separation

填写：

| Problem | Sensing / Separation / Both | Why |
|---|---|---|
| current time | ? | ? |
| hostname | ? | ? |
| filesystem append | ? | ? |
| state.jobs | ? | ? |
| stdout | ? | ? |

例如：

```text
stdout
```

未必是 separation problem，因为可以直接 capture。

不要因为“外部效果”就条件反射地 mock。

---

# 6. 审查 Starter Probe 自己

`m06_legacy_probe.py` 用了两种不同的 Python substitution mechanism：

```text
legacy_audit.datetime = FrozenDateTime
→ rebind legacy_audit module 自己的 datetime name

legacy_audit.socket.gethostname = ...
→ mutate 共享 socket module object 的 gethostname attribute
```

后者不是 module-local rebinding：`legacy_audit.socket is socket`，所以 patch 生效时，同一进程中其他使用该 `socket` module object 的代码也会看到替代的 `gethostname`。Probe 依靠串行执行和 `finally` restore 控制这个 blast radius。它还用 `env + tempfile` 建立 controlled experiment；环境变量本身同样是 process-scoped state。

回答：

1. 这两种 substitution 分别怎样形成 seam？
2. enabling action 在哪里？
3. `datetime` local rebinding 与 `socket.gethostname` shared-module mutation 的 isolation boundary 有什么不同？
4. 为什么当前串行 probe 仍可接受 process-wide patch？并行 tests / threads 会增加什么 risk？
5. 这些低成本 control points 是否已经足够完成 feature？
6. 哪些 seam 值得正式进入 production design，哪些可以只留在 test harness？

---

# 7. 把 Probe 提炼成 Characterization Tests

你至少要建立以下 characterization：

## C1 — Empty

保护：

```text
file creation
header shape
jobs=0
block terminator
```

## C2 — Mixed lifecycle

保护：

```text
ordering
numbering
status formatting
exit-code formatting
command text
```

## C3 — Append

保护：

```text
same-day second invocation appends
rather than overwrites
```

## C4 — Owner default

在没有 `TASKFORGE_AUDIT_OWNER` 时记录当前行为。

## C5 — Stdout

至少确认 count 与 path behavior。

### 重要

不要把 tmpdir 的随机绝对路径硬编码进 golden。

测试应该控制环境，但不把测试框架自身的随机细节变成 contract。

---

# 8. 证明 Characterization 有牙齿

临时做至少两个 mutants，例如：

```text
append → write overwrite
```

和：

```text
job ordering reversed
```

确认 characterization tests 会失败。

然后恢复。

记录：

```text
mutation
which test failed
which observed behavior it protects
```

---

# 9. Design It Twice：两种 Change Path

在写 feature 前，至少比较两种方案。

## Design A — 直接在 legacy function 里加 scope

例如：

```python
def publish_daily_audit(scope="all"):
    ...
```

内部直接：

```text
if scope == failed
```

### 分析

- 最小 diff？
- 是否需要 seam change？
- tests 是否仍依赖 monkeypatch module globals？
- 是否足够安全？

## Design B — 先抽一个小 semantic core / runtime seam

例如只抽：

```text
select_jobs(scope, jobs)
```

或者：

```text
runtime context provider
```

### 分析

- 哪个是真正 change point？
- 哪个 dependency 阻碍快速 feedback？
- abstraction 是否超出当前 change？

不要求 Design B 一定更好。

---

# 10. Structural Phase

如果你决定打开 seam，先做一个**纯 structural patch**。

要求：

```text
no failed-only behavior yet
```

验收：

```bash
PYTHONPATH=src uv run --with pytest --no-project python tools/m06_legacy_probe.py
PYTHONPATH=src uv run --with pytest --no-project python -m pytest -q
```

并运行你的 characterization suite。

所有 default behavior 必须保持。

---

# 11. 新 Behavior Contract

现在才写 failed-only contract。

建议明确：

```text
scope="all"
→ exact existing semantics

scope="failed"
→ include only jobs whose status is FAILED
→ jobs count equals selected jobs
→ numbering restarts at 01 over selected jobs
→ relative ordering among selected jobs follows existing job order
→ path/date/owner/header/block terminator unchanged
→ stdout count equals selected jobs

invalid scope
→ must fail before file mutation
```

最后一条很重要。

不要：

```text
先 append 半个文件
再发现 scope invalid
```

---

# 12. Feature Red Test

先写：

```text
mixed jobs
scope=failed
```

预期只输出 failed job。

确认：

```text
FAIL before implementation
```

再实现。

---

# 13. Invalid-input Test

例如：

```text
scope="banana"
```

要求：

```text
error
+
no output file created/changed
```

这复用了 M04 的 no-effect-on-rejection 思维。

---

# 14. Full Evidence

最终至少提供：

```text
1. original core tests
2. M06 characterization tests
3. legacy probe
4. failed-only focused tests
5. invalid-scope no-effect test
```

如果你改过 M05 dashboard 等无关区域，说明 scope 已经失控。

---

# 15. Agent 对照实验

让两个 Agent 分别处理同一需求。

## Agent A — 模糊任务

```text
Clean up legacy_audit.py, make it testable, and add failed-only mode.
```

记录它：

- 新建多少 abstraction？
- 是否改现有格式？
- 是否补 characterization？
- 是否先验证旧行为？
- 是否把 tests 绑到新实现？

## Agent B — Engineering Contract

```text
Phase 1: read-only reconnaissance; no edits.
Phase 2: characterize existing empty/mixed/append/default-owner/stdout behavior.
Phase 3: open at most the minimal seam needed for deterministic focused tests;
         no behavior change.
Phase 4: add failed-only scope with explicit red-before test.

Preserve:
default scope has no intended behavior change; preserve existing default behavior.
The listed characterization scenarios are evidence for this obligation, not its boundary.

Non-goals:
no audit format redesign;
no broad DI framework;
no state-store rewrite;
no dashboard/public-api cleanup.

Evidence:
show characterization before feature,
show seam-only behavior preservation,
show failed-only red→green,
show full suite.
```

比较两个 diff。

重点不是 Agent B 是否写得更少，而是：

> **哪个 diff 更容易证明“只改变了我们想改变的东西”？**

---

# 16. Independent Review Checklist

reviewer 不看作者 reasoning，独立回答：

- [ ] 当前 legacy behavior 是否先被观察，而不是靠猜？
- [ ] characterization 是否区分 observed 与 intended？
- [ ] 是否有 targeted effect sketch？
- [ ] sensing / separation 是否区分正确？
- [ ] seam 是否比当前 change 更大？
- [ ] structural phase 是否真的无 behavior change？
- [ ] failed-only 是否有 fail-before？
- [ ] invalid scope 是否无副作用？
- [ ] old append/ordering/format semantics 是否保留？
- [ ] tests 是否主要检查 behavior，而非新 helper 的内部调用？
- [ ] 是否有“顺便修复”的旧 quirk？
- [ ] remaining unknowns 是否被记录？

---

# 17. 评分重点

这份 lab 不按“最后 architecture 漂不漂亮”评分。

重点是：

| 能力 | 权重 |
|---|---:|
| takeover model / unknowns | 20% |
| characterization quality | 25% |
| seam judgment | 20% |
| staged change discipline | 15% |
| feature correctness | 10% |
| review / evidence quality | 10% |

一个只改 15 行但证据很强的方案，可能比一个“重构得很优雅”的 400 行方案得分更高。

---

# 18. 完成标准

完成 M06 后，你应该能解释：

1. 为什么 legacy condition 本质是 feedback problem；
2. characterization test 与 specification test 有什么认识论区别；
3. sensing 和 separation 分别是什么；
4. seam 与 enabling point 是什么；
5. 为什么不应该一接手旧代码就“make it testable”；
6. 如何围绕当前 change 建 targeted safety net；
7. 如何给 Agent 一个先观察、后改变的工作协议。

如果这些都能做到，你已经开始具备真正的 legacy takeover 能力。
