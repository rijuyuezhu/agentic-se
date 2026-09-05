# M03 Instructor Analysis — TaskForge Testing

> **Spoiler warning**：先完成 `labs/03-testing-evidence.md` 再看。
>
> 这不是唯一正确答案。它的用途是验证 lab 题目本身是否存在清楚、可论证、可实际运行的解，并展示 instructor 应该如何评阅 reasoning。

---

# 1. Baseline 不是“测试太少”，而是 claims 有洞

原始 suite：

```text
6 passed
```

这 6 个 test 已经能保护一些真实 behavior：

- success/failure exit-code mapping；
- queued-only cancellation；
- FIFO claim；
- submit basic lifecycle；
- invalid finish transition。

所以不能简单说：

> “这是一套差测试。”

更精确：

> **它对已编码的几个 claim 有一定区分力，但 contract coverage 不完整，而且包含至少一个潜在 overspecification。**

这是 M03 希望学生形成的语言。

---

# 2. Existing Test Audit

## 2.1 `test_submit_assigns_monotonic_ids_and_queues_jobs`

它混合了至少四条 claim：

1. submit 返回 id；
2. id 按 `job-1`, `job-2` 格式增长；
3. list 顺序与 submission 一致；
4. 两个新 job 都 counted as queued。

问题在第 2 条。

M03 contract 只承诺：

```text
opaque + unique + stable lookup token
```

所以：

```python
assert first == "job-1"
```

把 implementation choice 升级成了 contract。

更稳健的测试应保护：

```python
assert first != second
assert service.get(first).id == first
assert service.get(second).id == second
```

是否需要验证 submission order，则由 `list_jobs()` contract 单独测试。

## 2.2 `test_worker_claims_first_queued_job`

本 lab 已明确 FIFO 是 contract，所以：

```python
assert claimed.id == first
```

是合理 semantic assertion。

如果真实产品没有 FIFO promise，这条则应重新审查。

这正说明同一行 test 是否 brittle，取决于 contract，不取决于 syntax。

## 2.3 `test_cancel_only_queued_job`

变量命名：

```python
queued = submit(...)
running = submit(...)
claim_next()
claim_next()
```

两次 claim 后：

```text
queued variable  → RUNNING job
running variable → RUNNING job
```

变量名描述的是创建时意图，而不是 assert 时真实状态。

建议改成：

```python
first = ...
second = ...
```

或者分成多个 behavior tests：

```text
running job cannot be cancelled
queued job can be cancelled
```

这样 scenario 更清楚。

---

# 3. Baseline Mutation Probe 的实际结果

课程仓库上实际运行：

```bash
PYTHONPATH=src uv run --with pytest --no-project python tools/mutation_probe.py
```

得到：

```text
SURVIVED terminal_forgets_cancelled
SURVIVED submit_drops_command
SURVIVED list_jobs_hides_terminal
KILLED   finish_reverses_success_rule
KILLED   cancel_reports_success_without_transition
KILLED   claim_uses_lifo

summary: 3 killed, 3 survived
```

这三个 survivor 不是随机挑的。

它们分别代表：

```text
model/invariant gap
observable data gap
cross-lifecycle listing gap
```

---

# 4. Survivor 1 — `terminal_forgets_cancelled`

mutant：

```python
@property
def terminal(self):
    return self.status in {
        SUCCEEDED,
        FAILED,
        # CANCELLED missing
    }
```

为什么 baseline 通过？

现有 tests 的 `terminal_count()` 只在 succeeded path 中验证：

```python
assert metrics.terminal_count() == 1
```

取消测试虽然验证：

```python
status == CANCELLED
```

但从未连接：

```text
CANCELLED → terminal semantics
```

因此两个局部 claim 各自存在，却缺少组合 claim。

一个足够的 behavior-oriented test：

```python
def test_cancelled_job_counts_as_terminal() -> None:
    job_id = service.submit("sleep 1")

    assert service.cancel(job_id) is True

    assert service.get(job_id).status == JobStatus.CANCELLED
    assert metrics.terminal_count() == 1
```

这里我们没有直接测试 `Job.terminal` implementation。

它从 service + metrics observable behavior 保护 system-level terminal semantics。

---

# 5. Survivor 2 — `submit_drops_command`

mutant：

```python
state.jobs[job_id] = Job(id=job_id, command="")
```

现有 test 观察：

- id；
- list id；
- queued count。

完全没有观察 command。

所以 mutant 与现有 oracle observationally equivalent。

足够的 test：

```python
def test_submit_preserves_command() -> None:
    command = "printf 'hello world'"

    job_id = service.submit(command)

    assert service.get(job_id).command == command
```

这里 expected 来自 input contract，不是从 implementation 重新计算。

---

# 6. Survivor 3 — `list_jobs_hides_terminal`

mutant：

```python
return [job for job in state.jobs.values() if not job.terminal]
```

为什么现有 suite 通过？

唯一检查 list 的时刻是刚 submit 两个 queued jobs 后。

在那个 state partition 中：

```text
all jobs are non-terminal
```

所以：

```text
all jobs
```

和：

```text
only active jobs
```

产生同样 output。

需要 mixed-state scenario：

```python
def test_list_jobs_includes_terminal_jobs() -> None:
    finished = service.submit("true")
    worker.claim_next()
    worker.finish(finished, 0)

    active = service.submit("sleep 1")

    assert [job.id for job in service.list_jobs()] == [finished, active]
```

这个 test 同时利用 M03 contract 中的 submission-order promise。

如果 ordering 不是 contract，则应改为 set comparison。

---

# 7. 三个 tests 实际足够 kill 三个 survivor

Instructor 实际把上述 3 tests 临时加入 suite，重新运行 mutation probe。

结果：

```text
summary: 6 killed, 0 survived
```

普通 suite：

```text
9 passed
```

因此 lab 的 mutation exercise 已实际验证，不是假设“理论上应该能 kill”。

但是：

> **6/6 supplied mutants 被 kill 仍然不意味着系统测试充分。**

只说明这 6 个具体 fault hypotheses 被覆盖。

---

# 8. 至少还有哪些风险没有被这 6 个 mutants 表达？

例如：

1. `get()` / `list_jobs()` representation exposure；
2. unknown id semantics；
3. duplicate/invalid command semantics；
4. concurrent `claim_next()`；
5. claim 与 cancel race；
6. persistence/restart；
7. worker crash between side effect and finish；
8. retry semantics；
9. job deletion/retention；
10. id reuse after reset/restart；
11. command encoding；
12. remote worker protocol。

很多属于未来模块。

所以 mutation probe 是：

```text
selected fault injection
```

不是 completeness proof。

---

# 9. Overspecification — ID Format

本 lab contract 已明确 id opaque。

因此原 test：

```python
assert first == "job-1"
assert second == "job-2"
```

应该改。

一个可能版本：

```python
def test_submit_returns_distinct_stable_ids() -> None:
    first = service.submit("echo first")
    second = service.submit("echo second")

    assert first != second
    assert service.get(first).id == first
    assert service.get(second).id == second
```

这允许：

```text
job-N
UUID
ULID
opaque database key
```

都属于 legal implementation。

测试没有变“弱”。

它是把允许实现的集合调整到与真实 contract 一致。

---

# 10. Representation Exposure Regression

当前：

```python
job_id = service.submit("echo hi")
view = service.get(job_id)
view.status = JobStatus.SUCCEEDED
assert service.get(job_id).status == JobStatus.SUCCEEDED
```

说明 caller 获得了 authoritative mutation handle。

M03 contract 明确禁止。

## Regression test

```python
def test_get_does_not_expose_authoritative_mutable_job() -> None:
    job_id = service.submit("echo hi")

    observed = service.get(job_id)
    observed.status = JobStatus.SUCCEEDED

    assert service.get(job_id).status == JobStatus.QUEUED
```

在 baseline 上应该失败：

```text
expected QUEUED
actual SUCCEEDED
```

这就是必须保留的 fail-before evidence。

同样还应该思考：

```python
jobs = service.list_jobs()
jobs[0].status = ...
```

是否也泄漏 authority。

答案是：当前也泄漏。

---

# 11. Fix Design A — Defensive snapshots

最小方案：

```python
from dataclasses import replace


def get(job_id: str) -> Job:
    return replace(state.jobs[job_id])


def list_jobs() -> list[Job]:
    return [replace(job) for job in state.jobs.values()]
```

## 优点

- diff 很小；
- 现有 `Job` API 基本兼容；
- 立刻切断 mutation alias；
- 适合当前 toy system。

## 缺点

- type 仍然显示为 mutable `Job`，caller 看不出这是 snapshot；
- 将来 `Job` 有 nested mutable fields 时 shallow copy 可能再次泄漏；
- internal entity 与 external representation 没有在类型层分离。

---

# 12. Fix Design B — Immutable `JobView`

例如：

```python
@dataclass(frozen=True)
class JobView:
    id: str
    command: str
    status: JobStatus
    exit_code: int | None
```

read boundary 返回：

```text
JobView
```

内部仍使用 mutable：

```text
Job
```

## 优点

- type 直接表达 read-only boundary；
- future nested representation 更容易控制；
- state ownership 清晰。

## 缺点

- change surface 更大；
- 可能影响已有 caller type assumptions；
- 对当前极小系统可能过度设计。

## Instructor judgment

在 M03 当前规模下，我会接受 A 作为最小修复，但要求 design memo 明确 A 的 shallow-copy 限制。

如果学生选择 B 且实现干净，也应给高分。

---

# 13. 为什么不能只 fix `get()`

因为：

```python
service.list_jobs()[0]
```

仍然是 authoritative object。

contract 是：

> caller read 不应自动获得 authoritative mutation authority。

不是：

> `get()` 这个函数特殊地 copy。

所以 review 必须找 **所有 read boundary**。

这是 M02 ownership reasoning 在 M03 regression testing 中的直接应用。

---

# 14. Fail-before / Pass-after 该怎样保存

高质量 bugfix evidence：

```text
Before:
  focused test: FAIL
  failure: observed mutation changed authoritative status QUEUED → SUCCEEDED

Patch:
  return snapshots at service read boundaries

After:
  focused test: PASS
  full suite: PASS
  mutation probe: supplied fault mutants still killed as expected
```

差的 evidence：

```text
all tests pass
```

因为它没有证明新 test 真的关联旧 bug。

Instructor 已在临时副本实际验证这一流程：

```text
baseline + 2 个 authority-leak regression tests:
    2 failed

只把 service.get()/list_jobs() 改为返回 defensive snapshots 后：
    8 passed
```

因此这里的 red→green 是实际执行过的 reference，不是仅凭代码阅读推测。

---

# 15. 关于 `Job.terminal`：直接 unit test 可以吗？

可以有两种合理判断。

## 判断 A — 不直接测

如果 `Job` 只是 internal representation，terminal property 是 implementation helper：

```text
通过 service/metrics behavior 测
```

更 resistant to refactoring。

## 判断 B — 直接测

如果项目明确把 `Job` model 当公共 domain object，`terminal` 是独立 semantic contract：

```python
assert Job(... CANCELLED).terminal
```

也合理。

评分关键不是选 A 还是 B。

而是学生能否说明：

> **这个 unit boundary 为什么值得成为长期 contract。**

---

# 16. Interaction Testing 的参考判断

对于：

```text
cancel queued job → CANCELLED
```

不要测：

```text
status setter called exactly once
```

因为我们关心 outcome。

但未来如果 TaskForge 有：

```text
cancel remote process
```

外部协议要求：

```text
exactly one cancellation request sent to remote worker
```

那么这个 interaction 就可能是 contract 本身。

因此 instructor 不应机械扣“用了 mock”。

要问：

```text
mock/interaction 是否对齐 external semantic boundary？
```

---

# 17. Optional Hypothesis Reference

一个合理 property：

```python
from hypothesis import given, strategies as st


@given(st.integers().filter(lambda code: code != 0))
def test_any_nonzero_exit_code_fails(code: int) -> None:
    service.reset_for_tests()
    job_id = service.submit("anything")
    worker.claim_next()

    worker.finish(job_id, code)

    job = service.get(job_id)
    assert job.status == JobStatus.FAILED
    assert job.exit_code == code
```

更好的 generator 可以直接排除 0，而不是 filter：

```python
st.integers(max_value=-1) | st.integers(min_value=1)
```

这个 property 比只测 `7` 增加了：

```text
对整个 nonzero integer domain 搜索反例
```

但它仍然不验证：

- queued finish rejection；
- success code；
- persistence；
- concurrency。

---

# 18. Agent Vague Prompt 常见结果预期

不保证每个 Agent 都这样，但应重点检查：

- 给每个 method 加一个 test；
- 直接 import `state`；
- 重复现有 happy paths；
- 为 exact id format 加更多 assertions；
- 加大量 parametrization，但 partitions 没变；
- 没有发现 `command`；
- 没有 run mutation probe；
- representation exposure test 写出后立即同时修改 production，缺 fail-before；
- 最终总结只说 “X tests pass”。

这些不是“Agent 笨”。

它反映 vague task 本身没有指定 engineering objective。

---

# 19. Engineering-Spec Agent Prompt 的真正价值

不是 prompt 更长。

而是它提前声明了：

```text
authority
contract
non-goals
observable boundary
validation semantics
review expectations
```

这样 Agent 的 search space 被结构化。

这正是整门课想训练的人类能力。

---

# 20. Instructor 评分时不要奖励什么

不要因为下面这些自动给高分：

```text
+30 tests
100% line coverage
Hypothesis used
mock framework used
mutation 100%
strict AAA format
```

这些都是 mechanism。

要奖励：

- test 对应真实 contract；
- partition 有理由；
- oracle 独立；
- meaningful mutant 被 kill；
- legal refactor 不被误杀；
- fail-before 真实；
- remaining risks 说得清楚。

---

# 21. 本 Lab 最重要的 instructor conclusion

原 suite：

```text
6 passed
3/6 selected mutants survive
```

只增加三个 behavior-oriented tests：

```text
9 passed
0/6 selected mutants survive
```

再增加 representation-exposure regression：

```text
baseline 必须先红
```

然后 production ownership boundary 才有理由修改。

这整条链展示的是：

```text
contract
  ↓
test claim
  ↓
negative control / mutant
  ↓
observable failure
  ↓
production change
  ↓
pass-after evidence
```

而不是：

```text
write more tests
```

这就是 M03 想教的 testing。
