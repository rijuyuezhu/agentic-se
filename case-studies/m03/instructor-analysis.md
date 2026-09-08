---
id: case-M03
type: case_study
visibility: instructor
related: [M03]
---
# M03 Instructor Analysis — TaskForge Testing

> **Spoiler warning**：完成 [`../../labs/03-testing-evidence.md`](../../labs/03-testing-evidence.md) 前不要读。
>
> 这不是唯一正确答案。它记录一条 instructor reference reasoning：怎样从一套全部绿色的 tests 中同时找到 **missing claims** 与 **overspecified claims**，再用 mutation / fail-before evidence 检查自己的 oracle 是否真的有区分力。对应来源边界见 [`../../reading-notes/m03-source-audit.md`](../../reading-notes/m03-source-audit.md)。

M03 的 starter 不缺“测试文件”。它已经有 6 个通过的 tests，而且这些 tests 保护了真实行为。真正的问题是：**绿色只说明这些 tests 问过的问题得到预期答案；它不会自动告诉我们还漏了哪些问题，也不会告诉我们某个 assertion 是否把 implementation accident 错当成 contract。**

## 1. 先审现有 tests：有些 claim 缺失，有些反而太强

Baseline：

```text
6 passed
```

它已经覆盖 success/failure exit-code mapping、queued-only cancellation、FIFO claim、basic submit lifecycle 和 invalid finish transition。因此 instructor 不应把它简单评价成“差测试”；更精确的说法是：它对若干已表达 claim 有区分力，但 contract coverage 不完整，而且至少有一处 overspecification。

现有 tests 中最有信息量的三个审计点是：

| Existing test behavior | 它实际保护什么 | Instructor judgment |
|---|---|---|
| submit 后 assert `job-1`, `job-2` | ID format + ordering + queued count 混在一起 | 本 M03 exercise 只承诺 opaque / unique / stable lookup token；exact `job-N` 是 overspecification |
| `claim_next()` 返回第一个 submitted job | FIFO claim | Lab 明确把 FIFO 当 contract，因此 assertion 合理 |
| cancel test 用 `queued` / `running` 变量名，但两次 claim 后两者都已 running | scenario 仍可能测对行为，但命名与 assert 时真实 state 不一致 | 应让 test structure 反映真实 behavior partitions，而不是创建时意图 |

同一行 assertion 是否 brittle，不取决于它“看起来具体”，而取决于 specification 是否授权这种具体性。M03 Lab 与前一章的 ownership exercise 也可以对同一个 implementation detail给出不同 exercise contract；测试 authority 来自当前 task/spec，不来自代码恰好长什么样。

## 2. Mutation probe 把“测试跑到这里了”升级成“合理小 bug 会不会被发现”

Canonical mutation probe 实际得到：

```text
SURVIVED terminal_forgets_cancelled
SURVIVED submit_drops_command
SURVIVED list_jobs_hides_terminal
KILLED   finish_reverses_success_rule
KILLED   cancel_reports_success_without_transition
KILLED   claim_uses_lifo

summary: 3 killed, 3 survived
```

这 6 个 mutants 是课程选择的 fault hypotheses，不是完整 bug universe。它们的价值在于让三种不同 gap 变得可执行。

### Cancelled state 没有连接到 terminal semantics

`terminal_forgets_cancelled` 删除 `CANCELLED` from `Job.terminal`，现有 suite 仍绿。原因不是 cancellation 完全没测：cancel test 已经检查 status 变成 `CANCELLED`；terminal count 也测过，但只在 succeeded path 上。缺的是组合 claim：**cancelled job 也属于 terminal population。**

一个 behavior-oriented test 可以先走真实 public/service lifecycle，再观察 metrics：

```python
def test_cancelled_job_counts_as_terminal() -> None:
    job_id = service.submit("sleep 1")
    assert service.cancel(job_id) is True
    assert service.get(job_id).status == JobStatus.CANCELLED
    assert metrics.terminal_count() == 1
```

它没有直接锁死 `Job.terminal` helper 的实现方式，而是在当前 semantic boundary 上保护 system-level terminal meaning。

### Submit contract 从未观察 command

`submit_drops_command` 把 stored command 改成空字符串，现有 tests 仍然只看 ID、listing IDs 和 queued count，所以 mutant 与 oracle observationally equivalent。

最小补洞来自 input contract 本身：

```python
def test_submit_preserves_command() -> None:
    command = "printf 'hello world'"
    job_id = service.submit(command)
    assert service.get(job_id).command == command
```

Expected value来自 caller 提供的 input，不需要复制 production implementation 来算 oracle。

### Listing 只在“全部 active”这个 partition 被观察

`list_jobs_hides_terminal` 只返回 non-terminal jobs。Existing list test 恰好发生在两个 jobs 都 queued 的 state，于是“all jobs”和“only active jobs”得到相同 observation。

要区分它们，需要 mixed-state scenario：

```python
def test_list_jobs_includes_terminal_jobs() -> None:
    finished = service.submit("true")
    worker.claim_next()
    worker.finish(finished, 0)

    active = service.submit("sleep 1")

    assert [job.id for job in service.list_jobs()] == [finished, active]
```

这里还使用了本 exercise 明确承诺的 submission-order contract；如果 ordering 不在 specification 中，oracle 就应该改成不依赖顺序的比较。

## 3. 三个新 tests kill 三个 survivor，但这仍然不是 completeness proof

Instructor 在临时副本中加入上面三条 behavior tests 后，mutation probe 实际变成：

```text
summary: 6 killed, 0 survived
```

普通 suite 变成：

```text
9 passed
```

这证明 6 个 supplied fault hypotheses 现在都有对应 evidence channel；它**不**证明 TaskForge testing 已完整。至少还有 representation exposure、unknown-ID semantics、concurrent claim/cancel、persistence/restart、worker crash、retry、retention、ID reuse、command encoding、remote protocol 等风险没有被这组 mutants 表达，其中很多会成为后续模块的主问题。

Mutation score 因此不应被升级成另一个 coverage percentage。一个 surviving mutant 可能暴露真实 missing claim，也可能只是 equivalent / irrelevant fault；一个全 killed 的 selected set 也只是说明这组具体 counterexamples 被排除了。Concurrency/interleaving、crash/retry 等 temporal risk 会在 M07 获得新的 evidence model；M03 这里只把它们保留为当前 suite 的 remaining risk。

## 4. 测试还能从另一边失败：把合法实现错误地排除

原 submit test 精确要求：

```python
assert first == "job-1"
assert second == "job-2"
```

但 M03 exercise contract 把 ID 视为 opaque、unique、stable lookup token。于是 UUID、ULID 或其它 opaque database key 都可能是 legal implementation，exact string assertion 却会把它们判错。

更合适的 oracle 是：

```python
def test_submit_returns_distinct_stable_ids() -> None:
    first = service.submit("echo first")
    second = service.submit("echo second")

    assert first != second
    assert service.get(first).id == first
    assert service.get(second).id == second
```

这不是把 test “写弱了”，而是把接受集合重新对齐 specification。Testing 的 correctness 与 thoroughness 是两个方向：既要排除我们不允许的实现，也不能因为测试自身偏好误杀合法变化。

## 5. 更关键的 regression：6 个绿灯下 caller 仍能直接改 authoritative state

M02 已经暴露过 read-authority leak：

```python
job_id = service.submit("echo hi")
view = service.get(job_id)
view.status = JobStatus.SUCCEEDED
assert service.get(job_id).status == JobStatus.SUCCEEDED
```

M03 要做的不是直接选一个 architecture fix，而是先设计一个**只保护 authority isolation property** 的 regression oracle。

错误写法是无条件假设 observation 一定 writable；那会把 frozen `JobView` 这种合法 candidate 误杀。Reference oracle 允许两种合法结果：mutation attempt 被 read-only view 拒绝，或者它只修改 detached observation；无论哪种，authoritative state 都必须保持 `QUEUED`。

```python
def test_get_does_not_expose_authoritative_mutable_job() -> None:
    job_id = service.submit("echo hi")
    observed = service.get(job_id)

    try:
        observed.status = JobStatus.SUCCEEDED
    except Exception:
        # M03 没规定 read-only rejection 的具体 mechanism。
        pass

    assert service.get(job_id).status == JobStatus.QUEUED
```

这里 catch 只包住 deliberate mutation attempt；它不是 production error-handling pattern。M03 contract 没有 authority 要求 `FrozenInstanceError` 或其它具体 exception identity，所以 oracle 不应该绑定它。

同一问题也存在于 `service.list_jobs()[0]`。Contract 是“read boundary 不自动授予 authoritative mutation authority”，而不是“只修 `get()` 这个函数”。因此 reviewer 必须检查所有相关 read surfaces。

## 6. Design it twice：defensive snapshot 与 immutable view 都能满足当前 property

Reference 比较两条真实可行路线。

| Candidate | 优点 | 限制 / cost |
|---|---|---|
| defensive snapshots，例如 `dataclasses.replace(job)` | diff 小、现有 `Job`-shaped API 基本兼容、立即切断 alias | type 仍看起来 mutable；nested mutable fields 未来可能让 shallow copy 再次泄漏 |
| frozen `JobView` | read-only boundary 在 type 上更清楚；internal entity 与 external/read representation 分开 | change surface 更大，可能影响已有 caller type assumptions；当前 toy system 可能过度设计 |

Instructor 对当前 M03 会接受 defensive snapshot 作为最小修复，只要 design memo 明确 shallow-copy limitation；选择 `JobView` 且 compatibility / read semantics 处理干净也同样合理。

这正是 testing chapter 不应该替 architecture 做决定的地方。Regression test 先定义 property 和 legal implementation set，再让 design judgment 选择 mechanism。

## 7. Fail-before / pass-after 必须保存“这个 test 曾经真的抓到旧 bug”

高信息量 evidence 不只是：

```text
all tests pass
```

而是类似：

```text
Before:
  focused authority-isolation test -> FAIL
  observed mutation changed authoritative QUEUED -> SUCCEEDED

Patch:
  detach service read results

After:
  focused test -> PASS
  full suite -> PASS
```

Instructor 当时在临时 copy 中实际验证过 defensive-snapshot path：加 `get()` / `list_jobs()` 两个 authority-leak regressions 后 baseline 是 `2 failed`；只把两个 service read boundaries 改成 defensive snapshots 后，suite 变成 `8 passed`。这个 historical record只证明当时的 snapshot candidate，不应被改写成“当时也实现并跑过 immutable view”。

后续为了检查 regression oracle 本身有没有过度规定 implementation，又单独做了 candidate probe：

```text
get():
  baseline authoritative alias -> FAIL
  defensive snapshot           -> PASS
  frozen JobView               -> PASS (mutation rejected)

list_jobs():
  baseline authoritative alias -> FAIL
  defensive snapshots          -> PASS
  frozen JobView list          -> PASS (mutation rejected)
```

这条追加 evidence 只证明 oracle 接受声明的 legal candidate set；它不是 `JobView` architecture 的完整 compatibility test。

## 8. Test boundary 仍然需要 judgment，不能变成新的教条

### 是否直接 unit-test `Job.terminal`？

如果 `Job` 只是 internal representation，through service/metrics behavior 测 terminal semantics 往往更 resistant to refactoring；如果项目明确把 `Job` model 当公共 domain object，`terminal` 本身就是长期 semantic contract，那么直接 unit test 也合理。Instructor 评分应看学生能否说明**为什么这个 boundary 值得长期冻结**，而不是统一要求“只能测 public method”。

### Interaction test 是否天然坏？

对于普通 `cancel queued -> CANCELLED`，assert internal setter 被调用几次通常是在测试实现 choreography。但若未来 contract 是“对 remote worker 恰好发出一条 cancellation request”，external interaction 本身就是 observable effect。判断标准是 interaction 是否对齐真正的 semantic boundary，而不是用了 mock 就扣分。

### Property-based testing 是否自动更强？

一个适合 M03 的 property 是“任意 nonzero exit code 都使 running job failed，并保留该 exit code”。Hypothesis 可以生成整个 nonzero integer domain并 shrink counterexample；这增加了 counterexample search，却仍不覆盖 queued finish、zero success、persistence 或 concurrency。Generator/domain/property 自己都可能写错，所以 property-based testing 是 search engine，不是 automatic proof。

## 9. Agent 很容易生成更多 tests，但不一定增加新的 evidence

Vague task 常见结果包括：按 production method 一一生成 tests、重复 happy path、继续锁死 exact ID、加很多 parametrization 但 partitions 没变化、没有观察 command、没有运行 mutation probe，或者在写 representation-exposure test 的同时立刻改 production，于是失去 fail-before evidence。

问题不在“Agent 笨”，而是 objective 没有约束 claim / oracle / partition / boundary / evidence。更强的 engineering task 应先要求：

- 当前 contract 与允许实现集合；
- 哪些 meaningful fault hypotheses 还没有 observation；
- oracle expected 从哪里来；
- behavior partitions 与 boundary states；
- test double / fidelity limitation；
- negative control 或 fail-before；
- pass-after + regression evidence；
- remaining risks 与不能证明的事情。

Agent 可以快速生成 candidate tests、mutation harness、Hypothesis strategies；acceptance 仍要独立检查它是否只是让 implementation 和 matching oracle 一起变绿。

## 10. Instructor judgment

不要因为 `+30 tests`、100% line coverage、用了 Hypothesis、用了 mock framework、mutation 100% 或严格 AAA format 就自动给高分。这些都是 mechanisms。

高质量答案应该让一条 evidence chain 可被重建：

```text
contract / allowed implementation set
        ↓
behavior partition + oracle
        ↓
meaningful negative control / mutant
        ↓
observable fail-before
        ↓
scoped production change
        ↓
pass-after + regression evidence
        ↓
remaining risk
```

M03 的最终结论不是“写更多测试”。更接近的是：**测试是一组可执行工程声明；好的 suite 会让错误的未来变化更难悄悄通过，同时尽量不阻碍 specification 允许的正确变化。**
