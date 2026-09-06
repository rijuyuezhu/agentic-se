# Lab 03 — Testing as Executable Evidence

> 目标：不是“给 TaskForge 多写几个 pytest”。
>
> 你要训练的是：**从 contract / risk 设计 tests，审查现有 tests 是否绑错边界，并用 meaningful mutants 验证 test suite 是否真的能发现错误变化。**

预计时间：3–6 小时。

工作目录：

```bash
cd labs/taskforge
```

---

# 0. 实验规则

1. **先不要改 production code。**
2. 先运行 baseline tests 和 mutation probe。
3. 每新增一个 test，都要能用一句话说明它保护哪条 contract。
4. 不允许用“为了提高 coverage”作为 test 的唯一理由。
5. 不允许测试 `state.jobs`、`state.next_job_number` 等内部 representation 来快速 kill mutants。
6. 对 bug/regression exercise，必须保留 **fail-before → pass-after** evidence。
7. 如果使用 Agent，让 Agent 的输出只是候选 patch；你必须独立判断 oracle、boundary 和 fidelity。

---

# 1. 先建立 baseline

运行：

```bash
PYTHONPATH=src uv run --with pytest --no-project python -m pytest -q
```

应看到：

```text
6 passed
```

记录当前测试文件：

```text
tests/test_taskforge.py
```

不要因为 6 个 test 都绿就写“系统正确”。

你的第一项作业就是解释：

> 这 6 个 tests **实际证明了什么，又没有证明什么？**

---

# 2. Audit 现有 6 个 tests

为每个 test 填表：

| Test | Behavior claim | Oracle | Boundary | Possible overspecification | Missing neighboring partitions |
|---|---|---|---|---|---|
| `test_submit_...` | | | | | |
| `test_worker_claims_...` | | | | | |
| ... | | | | | |

至少回答下面这些问题。

## 2.1 ID format 是 contract 吗？

现有 test：

```python
assert first == "job-1"
assert second == "job-2"
```

假设真实 API 只需要：

```text
id 对当前系统唯一、稳定、可作为 lookup token
```

那么：

```text
job-1 → UUID
```

是否应该导致 test 失败？

你必须明确写出结论。

不要回答：

> “看情况。”

要写：

```text
如果 contract 是 X，则 test 合理/过度指定，因为 Y。
```

## 2.2 FIFO 是 contract 吗？

现有：

```python
assert claimed.id == first
```

它实际上把：

```text
oldest queued job is claimed first
```

编码成 contract。

这可能是合理的 scheduler contract，也可能只是当前 dict insertion order 的 accident。

在本实验后续部分，我们**明确假设 FIFO 是 TaskForge v0 contract**。

## 2.3 为什么 cancel test 命名有点 confusing？

认真读：

```python
queued = service.submit("sleep 1")
running = service.submit("sleep 2")
worker.claim_next()
worker.claim_next()
```

执行两次 claim 后，变量 `queued` 和 `running` 分别处于什么状态？

变量名是否帮助你理解，还是误导你？

这是 test clarity 的问题，不是 correctness 问题。

---

# 3. M03 使用的 TaskForge v0 Contract

为了避免“测试题本身需求不清”，本 lab 后半段采用以下 contract。

## Submission

`submit(command)`：

- 创建一个新 job；
- job id 对系统当前 lifetime 唯一；
- id 是 **opaque token**，不承诺具体字符串格式；
- 原始 `command` 必须完整保留；
- 新 job 初始为 `QUEUED`；
- 新 job 的 `exit_code` 为 `None`。

## Listing

`list_jobs()`：

- 返回所有已提交且未被显式删除的 jobs；
- 包括 terminal jobs；
- 返回 submission order。

## Lookup

`get(job_id)`：

- 返回当前 observable job data；
- caller 读取 job **不应自动获得修改 TaskForge authoritative state 的权限**。

当前 baseline 违反最后一条。这是已知 design bug，不是假装现状已经正确。

## Scheduling

`claim_next()`：

- 选择最早提交的 `QUEUED` job；
- transition `QUEUED → RUNNING`；
- 没有 queued job 时返回 `None`。

## Completion

`finish(job_id, exit_code)`：

- 只允许 `RUNNING` job；
- `exit_code == 0` → `SUCCEEDED`；
- `exit_code != 0` → `FAILED`；
- 保存原始 exit code。

## Cancellation

`cancel(job_id)`：

- 只允许 `QUEUED` job；
- 成功时 transition 到 `CANCELLED` 并返回 `True`；
- 其他 lifecycle state 返回 `False` 且 state 不变。

## Terminal semantics

```text
SUCCEEDED
FAILED
CANCELLED
```

都属于 terminal。

---

# 4. 设计 Behavior Partitions

现在不要看现有 tests。

从上面的 contract 独立设计一个 behavior table。

至少覆盖：

## submit

```text
first submission
multiple submissions
command preservation
initial lifecycle fields
```

## claim

```text
no queued jobs
one queued job
multiple queued jobs / FIFO
terminal jobs mixed with queued jobs
```

## finish

```text
RUNNING + 0
RUNNING + positive nonzero
RUNNING + negative nonzero
QUEUED
SUCCEEDED
FAILED
CANCELLED
```

## cancel

```text
QUEUED
RUNNING
SUCCEEDED
FAILED
CANCELLED
```

## list

```text
empty
active jobs
mixed active + terminal
submission order
```

## read authority

```text
caller mutates object returned by get/list
```

对于每个 partition，标：

```text
Must test now
Useful but redundant
Leave for later module
```

不要机械地把笛卡尔积全部展开。

目标是 **high-information suite**。

---

# 5. 运行 Mutation Probe

课程提供一个小型人工 mutation harness：

```bash
PYTHONPATH=src uv run --with pytest --no-project python tools/mutation_probe.py
```

它不会修改你的工作区；每个 mutant 都在临时目录运行。

baseline 应得到：

```text
3 killed, 3 survived
```

具体 survivor：

```text
terminal_forgets_cancelled
submit_drops_command
list_jobs_hides_terminal
```

这三个 mutant 都对应本 lab 已明确写进 contract 的行为。

因此在本实验中：

> **它们存活不是“equivalent mutant”，而是真正的 test gap。**

---

# 6. 不要立刻写 test：先解释每个 survivor

对每个 survivor 写：

```text
Mutant:

Broken contract:

Why current suite still passes:

Smallest useful scenario:

Observable oracle:

Would testing internal state make this easier?
Why should/shouldn't we do that?
```

例如你不能只写：

```text
submit_drops_command 没有 command test。
```

要写到：

```text
当前 submit test 只观察 id、list 中的 id 和 queued_count，
从未观察 job.command；因此 mutation 对所有现有 oracle 都 observationally equivalent。
```

这才是 test reasoning。

---

# 7. Kill 三个 Survivor

新增 tests，但有约束：

## 7.1 `terminal_forgets_cancelled`

不要直接：

```python
assert Job(..., status=CANCELLED).terminal
```

除非你论证 `Job.terminal` 本身是稳定 public unit contract。

本 lab 默认更希望你从 TaskForge behavior 测：

```text
submit → cancel → terminal_count / observable status
```

这样 test 保护的是 system semantics，而不是 property implementation。

## 7.2 `submit_drops_command`

从公开 lookup/list behavior 检查：

```text
submit command → retrieved job command unchanged
```

不要直接查看 `state.jobs`。

## 7.3 `list_jobs_hides_terminal`

构造：

```text
一个 terminal job
+
一个 active job
```

然后验证 listing 仍包含两者。

注意同时考虑：

```text
ordering contract
```

---

# 8. 重新跑 Mutation Probe

```bash
PYTHONPATH=src uv run --with pytest --no-project python tools/mutation_probe.py
```

如果你正确覆盖三条 contract，预期：

```text
6 killed, 0 survived
```

但**不要写：**

> mutation score 100%，所以测试完美。

反而写：

```text
这 6 个 mutants 代表哪些风险？
它们仍没有覆盖哪些风险？
```

至少列 5 个未覆盖方向。

例如：

- read authority leak；
- unknown id error semantics；
- concurrent claim race；
- persistence；
- process crash；

后几项会在后续模块进入。

---

# 9. 一个有意的 Overspecification Exercise

给现有 ID test 做 design review。

目前：

```python
assert first == "job-1"
assert second == "job-2"
```

本 lab contract 已明确：id 是 opaque token。

因此请把 test 改成只保护：

- distinct；
- stable lookup；
- submission 返回的 token 对应正确 job。

而不保护：

```text
prefix
numbering
具体 serialization
```

然后回答：

> 为什么“测试更少具体细节”反而让 contract protection 更强？

提示：因为它允许更大的 legal implementation set，同时仍拒绝 contract-breaking implementations。

---

# 10. Regression Exercise — Representation Exposure

当前 baseline：

```python
job = service.get(job_id)
job.status = JobStatus.SUCCEEDED
```

会直接修改内部 authoritative object。

根据本 lab contract，这是 bug。

## Step A — 写 regression test

要求：

```text
submit job
get observable job
尝试把 returned observation 的 status 改成 SUCCEEDED
  - mutation 被拒绝：允许
  - mutation 成功：也允许，但只能影响 detached/local observation
再次 get
authoritative status 仍是 QUEUED
```

也就是说，oracle 保护的是 **authority isolation**，不是“返回值必须可写”。不要写一条只有 defensive snapshot 能通过、但 immutable view 会因为拒绝 assignment 而失败的 test。反过来，也不要把某个具体异常类型写成要求；本 lab contract 没承诺 read-only view 必须用哪种 exception 表达拒绝。

先运行，保留失败证据。旧 baseline 的 mutation attempt 会成功并穿透到 authoritative object，因此最后的 authoritative-state assertion 应该失败。这一步必须在 production fix 之前完成。

## Step B — 设计至少两个 fix

例如可能方向：

### Design A

read API 返回 defensive copy/snapshot。mutation attempt 可以成功，但只修改 detached observation。

### Design B

内部 mutable entity 与外部 immutable view 分离。mutation attempt 可以直接被 read-only boundary 拒绝。

不要默认 A 一定最好，也不要为了保住 Step A 的 test 而把“observation 必须 writable”偷偷升级成新 contract。

比较：

- change size；
- future persistence；
- type clarity；
- performance；
- API compatibility；
- accidental identity semantics。

## Step C — 实现最小修复

要求：

- 原有 public behavior 保持；
- 新 regression test 通过；
- 原 6 tests + 你新增的 M03 tests 全通过；
- 不允许只是让 test 不能 import `JobStatus`。

## Step D — pass-after

保存：

```text
focused regression test
full suite
mutation probe
```

三组 evidence。

---

# 11. 一个故意很差的 Test

考虑：

```python
def test_cancel_implementation(monkeypatch):
    calls = []

    class FakeJob:
        ...

    # patch state.jobs
    # patch Job.status setter
    # assert setter invoked once with CANCELLED
```

回答：

1. 它在保护 “cancelled outcome” 还是 “当前实现 choreography”？
2. 如果未来把 lifecycle transition 放进 `JobStore.transition()`，真实 behavior 不变，这个 test 会怎样？
3. 如果 setter 被调用后另一个 bug 又把状态改回 QUEUED，它能发现吗？
4. 什么情况下 interaction test 反而合理？

请把它重写成 behavior-oriented test。

---

# 12. Optional — Coverage Experiment

这部分不是必做。

运行 coverage：

```bash
PYTHONPATH=src uv run --with pytest --with coverage --no-project \
  python -m coverage run -m pytest -q
PYTHONPATH=src uv run --with coverage --no-project \
  python -m coverage report -m
```

记录 coverage。

然后故意创建一个**没有 meaningful assert** 的 test，使更多行被执行。

再次运行 coverage。

回答：

> coverage 提升了，semantic confidence 是否同幅度提升？为什么？

完成后删除这个坏 test。

---

# 13. Optional — Property-Based Testing

安装运行时依赖即可，不写入课程项目依赖：

```bash
PYTHONPATH=src uv run --with pytest --with hypothesis --no-project python -m pytest -q
```

尝试为一个适合的 property 写 Hypothesis test。

推荐方向：

```text
对任意非零 exit code：
RUNNING job finish 后必须 FAILED，且保存 exact exit code
```

你要明确：

- generator domain；
- property；
- 为什么排除 0；
- Hypothesis 相比写 `7` 一个 example 增加了什么；
- 它仍然没有证明什么。

不要为了“用 Hypothesis”而给所有 tests property-化。

---

# 14. Agent Experiment — Vague Prompt

在一个干净分支/副本中，让 Agent 做：

```text
给 TaskForge 补充更完整的测试。
```

记录：

- Agent 先读了什么？
- 是否先问/推断 contract？
- 是否测试 internal state？
- 是否 mock？
- 是否复制 implementation 到 expected？
- 是否注意到 command preservation？
- 是否注意到 cancelled terminal？
- 是否发现 read authority leak？
- mutation probe 改善了多少？

不要告诉 Agent mutants 名字。

---

# 15. Agent Experiment — Engineering Spec

重新从同一 baseline，让 Agent 收到：

```text
Do not modify production code yet.

1. Read the public behavior in labs/03-testing-evidence.md section 3.
2. Build a behavior/partition table before writing tests.
3. Tests must use TaskForge's service/worker/metrics boundaries rather than state.py.
4. Treat job ids as opaque; do not assert the job-N format.
5. Add tests that protect command preservation, terminal semantics including CANCELLED,
   and listing of terminal jobs.
6. Run tools/mutation_probe.py and explain every surviving mutant semantically.
7. Do not optimize for a mutation percentage; explain what the supplied mutants do not test.
8. For representation exposure, first add a regression test and prove fail-before.
   Do not fix production code until that evidence exists.
9. After any fix, show focused pass-after, full-suite result, and mutation probe output.
10. Do not claim correctness from green tests alone; list remaining risks.
```

比较两轮：

| Dimension | Vague | Engineering spec |
|---|---:|---:|
| tests added | | |
| meaningful new behaviors | | |
| implementation coupling | | |
| mutants killed | | |
| false/accidental contracts added | | |
| review time | | |
| remaining-risk analysis | | |

---

# 16. Independent Review

无论你还是 Agent 写的 patch，都做一次独立 review。

至少检查：

## Contract

- IDs 是否被错误固定格式？
- FIFO 是否有意保护？
- command 是否保留？
- terminal semantics 是否完整？

## Oracle

- 是否有 expected 从 implementation 复制？
- assert 是否真的验证 final outcome？

## Boundary

- tests 是否直接写 `state.jobs`？
- 是否测试 private decomposition？

## Mutation

- survivor 为什么存活/被 kill？
- 为 kill mutant 新增的 test 是否真的有业务意义？

## Regression

- representation exposure 是否有 fail-before？
- fix 是否仅让该 test 过，还是恢复了 ownership boundary？

## Maintainability

- test 名称是否描述 behavior？
- fixture/helper 是否隐藏重要 scenario？

---

# 17. 提交内容

你最终应交：

```text
1. baseline test audit
2. behavior partition table
3. survivor analysis
4. improved tests
5. before/after mutation probe output
6. overspecification analysis
7. representation-exposure fail-before/pass-after evidence
8. design comparison for the fix
9. vague-vs-engineering Agent comparison
10. independent review
11. remaining risks
```

---

# 18. 评分标准

不是按 test 数量。

## 25% — Contract reasoning

- 是否知道自己在保护什么；
- 是否避免 accidental contract。

## 20% — Partition quality

- 是否有 systematic state/boundary/failure coverage；
- 是否避免机械笛卡尔积。

## 20% — Test strength

- meaningful mutants 是否被发现；
- regression 是否 fail-before。

## 15% — Maintainability

- behavior-oriented；
- boundary 正确；
- 不 brittle。

## 10% — Evidence quality

- 输出可复现；
- 没有“tests passed 所以正确”的过度结论。

## 10% — Agent orchestration

- prompt 是否提供 engineering constraints；
- review 是否独立。

---

# 19. 实验结束后你应该形成的习惯

以后看到：

```text
Tests: 182 passed
Coverage: 94%
```

你的第一反应不应该是：

> “很好。”

而应该是：

```text
182 个什么 claims？
94% 的代码被执行后验证了什么？
哪些 plausible failures 会偷偷通过？
哪些 legal refactors 会被误杀？
哪些 boundary 被 fake 掉了？
这个 bugfix test 在旧代码上真的失败过吗？
```

这才是 Software Engineering 语境里的 testing。
