# M04 Instructor Analysis — TaskForge Public Boundary

> **Spoiler warning**：完成 `labs/04-api-error-boundary.md` 前不要读。

本文件不是唯一正确答案。

它的目的，是证明本 lab 的 contract 可以用一个小而完整的设计实现，并记录 reference design 的真实 trade-off 与未解决问题。

---

# 0. Reference validation summary

课程维护者在临时 TaskForge 副本中实现了本文 reference design，并实际运行：

```text
原有 core tests: 6
M04 reference tests: 12
总计: 18 passed
```

没有修改课程仓库中的 starter `public_api.py` 为答案版本；学生仍然能从有问题的 baseline 开始。

reference test 覆盖：

```text
blank command → INVALID_ARGUMENT + no side effect
blank request id → INVALID_ARGUMENT + no side effect
unknown get → NOT_FOUND
unknown cancel → NOT_FOUND
cancel running → FAILED_PRECONDITION(status=running)
cancel succeeded → FAILED_PRECONDITION(status=succeeded)
cancel queued → success
no request id + same command → two jobs
same request id + same intent → one job
retry after job becomes running → same job, current view
same request id + different intent → CONFLICT + no new job
public JobView frozen/detached
```

---

# 1. Starter 的真实 contract reconstruction

M04 starter：

```python
submit_job(command: str) -> dict
get_job(job_id: str) -> dict
list_jobs() -> list[dict]
cancel_job(job_id: str) -> dict
```

但 signature 没写出的行为很多。

## submit

当前：

```text
任何 str 都接受
```

包括：

```text
""
"   "
```

side effect：

```text
分配 id
插入 jobs dict
```

没有 request identity。

所以：

```text
same payload twice
→ job-1 + job-2
```

注意这**不应该直接被叫 bug**。

在没有 request identity contract 时，两次调用本来就可以代表两个 distinct logical requests。

问题是：

```text
如果第一次 response lost，caller 无法表达“这一次是 retry，不是新的 intent”。
```

## get

known：返回 detached dict view。

unknown：

```text
KeyError
```

这个 error 来自：

```python
state.jobs[job_id]
```

所以是 representation-specific failure。

## list

返回 detached dict views。

这里 starter 已经比 core `service.list_jobs()` 更安全：

caller 改 list/dict 不会直接改 authoritative Job。

## cancel

known QUEUED：

```text
{"cancelled": True}
```

known RUNNING / terminal：

```text
{"cancelled": False}
```

unknown：

```text
KeyError
```

因此 boundary 混合了：

```text
exception channel
+
boolean channel
```

caller 需要知道 service implementation 才能完全解释结果。

---

# 2. Starter 不是“完全 shallow”

一个重要教学点：不要二元评价。

starter `public_api._view`：

```python
return {
    "id": job.id,
    "command": job.command,
    "status": job.status.value,
    "exit_code": job.exit_code,
}
```

它确实隐藏了：

```text
mutable Job identity
```

所以：

```python
view = get_job(id)
view["status"] = "succeeded"
```

不会修改 internal state。

这是一个真实的 boundary improvement。

但它没有隐藏：

```text
KeyError semantics
cancel failure ambiguity
input validity ambiguity
retry uncertainty
```

所以 boundary 可以：

```text
某些维度 deep
某些维度 shallow
```

不要只给 architecture 打一个“好/坏”标签。

---

# 3. Reference behavior table

| operation | case | public result | side effect | retry |
|---|---|---|---|---|
| submit | blank command | INVALID_ARGUMENT / INVALID_COMMAND | none | retry same input useless |
| submit | blank supplied request_id | INVALID_ARGUMENT / INVALID_REQUEST_ID | none | fix request |
| submit | no request_id | new JobView | one new job | unsafe after unknown outcome |
| submit | new request_id | new JobView, replayed=false | one new job + request record | safe under current in-process assumptions |
| submit | same id/same command | same job, replayed=true | no additional job | safe |
| submit | same id/different command | CONFLICT / REQUEST_ID_REUSED | none | caller must choose new id or original intent |
| get | known | JobView | none | safe |
| get | unknown | NOT_FOUND / JOB_NOT_FOUND | none | retry only if higher-level creation race expected |
| cancel | QUEUED | CancelResult(status=cancelled) | one transition | not defined as generic replay-safe API in reference |
| cancel | RUNNING | FAILED_PRECONDITION / JOB_NOT_CANCELLABLE | none | no blind retry |
| cancel | terminal | FAILED_PRECONDITION / JOB_NOT_CANCELLABLE | none | no blind retry |
| cancel | unknown | NOT_FOUND | none | no blind retry |

---

# 4. Reference public error model

reference 使用：

```python
class ApiCode(str, Enum):
    INVALID_ARGUMENT = "INVALID_ARGUMENT"
    NOT_FOUND = "NOT_FOUND"
    FAILED_PRECONDITION = "FAILED_PRECONDITION"
    CONFLICT = "CONFLICT"
```

以及：

```python
ApiError(
    code=...,
    reason=...,
    message=...,
    metadata=...,
)
```

这里刻意分两层。

## code

表示 broad caller recovery category：

```text
INVALID_ARGUMENT
NOT_FOUND
FAILED_PRECONDITION
CONFLICT
```

## reason

表示 domain-specific stable identity：

```text
INVALID_COMMAND
INVALID_REQUEST_ID
JOB_NOT_FOUND
JOB_NOT_CANCELLABLE
REQUEST_ID_REUSED
```

为什么不直接一个巨大 enum？

因为未来如果换成 RPC：

```text
code
```

可以映射到 canonical protocol status。

而：

```text
reason
```

保留 TaskForge domain distinction。

---

# 5. 为什么不每个 lifecycle state 一个 exception class

一种机械实现可能是：

```text
JobRunningError
JobSucceededError
JobFailedError
JobCancelledError
```

reference 没这么做。

原因：对 public `cancel` caller 来说，它们共同表示：

```text
当前 job 不能进行 QUEUED→CANCELLED transition
```

caller 如果需要展示具体原因，可以读：

```text
metadata.status
```

因此 reference：

```text
code = FAILED_PRECONDITION
reason = JOB_NOT_CANCELLABLE
metadata.status = running/succeeded/failed/cancelled
```

这样新增 terminal state 时，不一定要新增 exception taxonomy。

---

# 6. 为什么 `NOT_FOUND` 不直接保留 KeyError

`KeyError` 的来源：

```text
Python dict
```

不是：

```text
TaskForge domain
```

如果 storage 未来换成 SQLite，unknown job 可能变：

```text
fetchone() returns None
```

甚至远端 store：

```text
RPC NOT_FOUND
```

public contract 应保持：

```text
JOB_NOT_FOUND
```

所以 reference 只在理解的 domain seam catch：

```python
try:
    service.get(job_id)
except KeyError:
    raise JOB_NOT_FOUND
```

而不是：

```python
except Exception:
    raise INTERNAL
```

---

# 7. Input parsing reference

reference 用：

```python
@dataclass(frozen=True)
class Command:
    value: str

    @classmethod
    def parse(cls, raw: str) -> "Command":
        if not raw.strip():
            raise INVALID_COMMAND
        return cls(raw)
```

为什么保留原字符串，不 `strip()` 后存？

因为 lab 不应该顺便决定：

```text
shell command whitespace normalization
```

是不是 semantic equivalence。

reference 只承诺：

```text
必须至少有一个 non-whitespace character
```

而不承诺：

```text
leading/trailing whitespace 被 normalize
```

这减少 M04 的 scope。

---

# 8. 这个 `Command` 真的让 invalid state “不可表示”吗？

严格说：**没有。**

Python caller 仍然可以：

```python
Command("   ")
```

所以这里更多是：

```text
boundary discipline
+
precise internal representation
```

而不是 Haskell/Rust 意义上的完全 static proof。

为什么仍有价值？

因为 public path：

```text
str → Command.parse → Command
```

明确建立一个 validation seam。

core code 可以选择只接 `Command`，减少 validate-everywhere。

但 instructor 不会声称：

```text
Python type system 已证明 invalid Command 不存在
```

---

# 9. Reference JobView

```python
@dataclass(frozen=True)
class JobView:
    id: str
    command: str
    status: str
    exit_code: int | None
```

为什么不用 internal `Job`？

因为 public boundary 不应交出 authoritative mutable handle。

为什么 `status` 用 string 而不是 internal `JobStatus`？

这是一个可争论选择。

reference 选择 string 是为了模拟：

```text
future serialization boundary
```

另一合理设计是 public enum。

重要的是：

```text
public representation
```

不要被 internal mutable object identity 绑定。

---

# 10. Request identity reference

reference 记录：

```python
@dataclass(frozen=True)
class _RequestRecord:
    command: Command
    job_id: str

_request_records: dict[str, _RequestRecord]
```

它 authoritative 地回答：

```text
request_id 被哪个 submit intent 使用？
该 logical request 对应哪个 job？
```

它**不维护**：

```text
job.status
job.exit_code
```

这些仍由 Job state owner 决定。

所以没有形成 duplicated job authority。

---

# 11. 为什么不用 `hash(command)` 当 request id

因为：

```text
echo same
```

两次调用可能真的是：

```text
two different requested jobs
```

reference semantics：

```python
submit_job("echo same")
submit_job("echo same")
```

得到：

```text
job-1
job-2
```

这是正确的。

只有 caller 显式：

```python
request_id="req-1"
```

才声明：

```text
这些 transmissions 属于同一个 logical request
```

---

# 12. Same request ID + different intent

reference：

```text
req-1 + "echo A"
→ job-1
```

然后：

```text
req-1 + "echo B"
→ CONFLICT / REQUEST_ID_REUSED
```

并验证：

```text
job count 仍然是 1
job-1 command 仍是 A
```

为什么不能直接返回 job-1？

因为这样会把 caller 的新 intent B 静默解释成 A。

为什么不能执行 B？

因为这会破坏：

```text
one request identity → one logical intent
```

所以 conflict 是必须保留的 distinction。

---

# 13. Retry response：current view，而不是 exact snapshot

第一次：

```text
req-1 → job-1 queued
```

worker claim：

```text
job-1 running
```

caller retry：

```text
req-1 + same command
```

reference 返回：

```text
job-1 running
replayed=true
```

为什么？

因为真正需要的 guarantee 是：

```text
same logical creation
same job identity
no duplicate job
```

不是：

```text
response bytes 永远与第一次一模一样
```

这也避免为了保存旧 response 再增加一个 history state owner。

---

# 14. `replayed` 是否必须存在？

不一定。

reference 加：

```python
SubmitResult(job=..., replayed=True/False)
```

主要用于教学：让 caller / test 可观察 dedup path。

真实 API 可以选择不暴露它。

问：

```text
caller 真需要知道它是首次执行还是 retry replay 吗？
```

如果不需要，暴露 `replayed` 本身就是额外 compatibility surface。

所以 student 不暴露它也可以，只要 idempotency contract 能被证明。

---

# 15. Validation order 是 reference 的关键 correctness point

reference：

```python
parsed = Command.parse(command)
request_id = validate_request_id(request_id)
```

然后才：

```python
service.submit(...)
```

因此测试：

```text
blank command
→ error
→ list_jobs() == []
```

以及：

```text
blank request id
→ error
→ list_jobs() == []
```

都通过。

这比只检查 exception 更强。

---

# 16. Cancel reference

流程：

```text
service.cancel(job_id)
```

如果 unknown：

```text
KeyError → JOB_NOT_FOUND
```

如果 True：

```text
return cancelled view
```

如果 False：

```text
read current job
→ FAILED_PRECONDITION
→ metadata.status
```

这使 public caller 不再看到：

```text
False = ???
```

---

# 17. Reference cancel 有一个未来 race

当前 TaskForge 单线程，所以：

```text
cancel() returns False
      ↓
get current job
```

之间不会变化。

未来并发后：

```text
cancel false
      ↓
state changes
      ↓
get sees another state
```

于是 error metadata 可能不严格描述 cancel check 当时的 state。

这是一个真实的 check-then-observe race。

为什么 reference 不现在修？

因为 M04 的 scope 是：

```text
boundary semantics
```

不是：

```text
atomic lifecycle transition API
```

M07 会把 transition result 改成原子返回：

```text
Cancelled
NotCancellable(observed_state)
NotFound
```

或者等价结构。

这就是 staged course design：不要提前吃掉后续教学问题。

---

# 18. Reference request registry 不是 crash-safe

当前 sequence：

```text
1. service.submit(command)
2. _request_records[request_id] = (...)
```

如果进程在 1 与 2 之间 crash：

```text
job 已创建
request record 没写
```

restart 后 retry：

```text
可能创建 duplicate job
```

所以 reference **不能声称 durable idempotency**。

它只证明：

```text
single-process, no-crash baseline 下的 request dedup semantics
```

这条限制必须写进 design memo。

M07/M08 后可以考虑：

- same transaction；
- durable unique request record；
- recovery；
- retention。

---

# 19. Reference request registry 也不是 concurrency-safe

两个并发请求：

```text
T1: get(req) → none
T2: get(req) → none
T1: create job-1
T2: create job-2
T1: write record
T2: write record
```

结果：

```text
two jobs
```

这破坏 idempotency。

为什么 M04 不解决？

同样因为 concurrency 是 M07。

但 student 必须知道：

> **“dict 里有 request id”不等于并发下完成了幂等性。**

---

# 20. Reference reset_for_tests 暴露另一个 ownership lesson

reference 提供：

```python
def reset_for_tests():
    service.reset_for_tests()
    _request_records.clear()
```

这是因为测试 state 现在跨两个 semantic owners：

```text
job state
request identity state
```

如果测试只调用：

```python
service.reset_for_tests()
```

request registry 会残留。

这提醒我们：

```text
test fixture lifecycle
```

也是 lifecycle contract。

未来更成熟设计会让 state 实例化而不是 module global。

但 M04 不顺便重构所有 global state。

---

# 21. Error metadata reference

例如：

```text
JOB_NOT_CANCELLABLE
metadata = {
  job_id,
  status,
}
```

为什么不放：

```text
internal Python class
memory address
state dict index
stack trace
```

因为 public metadata 是 compatibility/security surface。

只暴露 caller 需要且能稳定承诺的 context。

---

# 22. Error message 测试策略

reference tests 检查：

```text
code
reason
required metadata
```

不锁死完整 message。

原因：

```text
human wording
```

不是当前 machine contract。

如果未来产品要求 exact localized message compatibility，那才应另建相应 contract/tests。

---

# 23. Why exception-oriented reference?

reference 使用 Python exception：

```text
success return
failure raises ApiError
```

理由：

- 和 Python ergonomics 一致；
- 不需要引入自制 Result framework；
- public `ApiError` 已把 machine semantics 显式化；
- later RPC boundary 可以自然 serialize。

但这不是唯一答案。

一个非常合理的替代：

```text
Result[JobView, ApiError]
```

尤其如果：

- 项目已有 Result idiom；
- caller 需要 exhaustive match；
- language type system 能很好表达 union。

课程不把 exception-vs-Result 变成宗教。

---

# 24. Why four broad codes?

reference 没复制全部 gRPC codes。

因为 TaskForge 目前只需要：

```text
INVALID_ARGUMENT
NOT_FOUND
FAILED_PRECONDITION
CONFLICT
```

以后出现：

- storage outage；
- remote worker unavailable；
- permission；
- deadline；

才有理由增加：

```text
UNAVAILABLE
PERMISSION_DENIED
DEADLINE_EXCEEDED
```

不要为了“完整”先建立一个 20-code enum 然后只用 4 个。

这是 YAGNI 与 stable vocabulary 的平衡。

---

# 25. `CONFLICT` 是否一定是正确名字？

不一定。

如果未来直接映射 gRPC，可能用：

```text
ALREADY_EXISTS
FAILED_PRECONDITION
ABORTED
```

或 domain reason。

reference 使用 `CONFLICT` 是课程本地 vocabulary。

真正 invariant 是：

```text
same request identity cannot be rebound to different intent
```

具体 protocol code 是 encoding decision。

不要让 status-code naming 掩盖 semantic reasoning。

---

# 26. 为什么没有把 cancel already-cancelled 定义成 success

这是一个刻意选择。

可以设计：

```text
cancel(CANCELLED) → success
```

这样重复 cancel 更接近：

```text
ensure cancelled
```

但当前 TaskForge 原语 `cancel` 的语义更像：

```text
perform QUEUED→CANCELLED transition
```

所以 reference 保留：

```text
already cancelled → FAILED_PRECONDITION
```

这样更忠实于现有 state machine。

如果产品以后说：

```text
cancel API 的 postcondition 只是“job not runnable”
```

就可以 design it twice 并改变 contract。

---

# 27. “Define errors out of existence” 在这里怎么用

reference **没有**把所有 error 消掉。

它只考虑：

```text
是否有些状态可以自然算 operation already satisfied
```

最后选择没有改 cancel semantics。

这恰好说明 heuristic 的正确用法：

```text
先问 product semantics
```

不是：

```text
错误越少越高级
```

---

# 28. Public view 与 internal model 可以独立演化

reference public：

```text
JobView
```

internal：

```text
Job
```

以后 internal 可能新增：

```text
lease_owner
attempt_count
created_at
```

不需要自动成为 public fields。

反过来 public 也可以提供 derived field：

```text
terminal
```

而不要求 internal storage 直接存它。

这就是 representation independence 在 API boundary 的应用。

---

# 29. Fail-before 应怎样理解

对于全新 API shape，第一次写：

```python
submit_job(..., request_id="req-1")
```

starter 会直接：

```text
TypeError: unexpected keyword argument
```

这是一个红灯，但信息量有限。

更有价值的 regression-style red test 是：

```text
blank command does not create job
```

starter 会：

```text
创建 job
测试失败
```

以及：

```text
same request identity retry does not duplicate effect
```

在添加 minimal signature/scaffolding 后，应先看到 duplicate effect，再修。

所以 “fail-before” 不是形式主义：

> 关键是证明 test 的 oracle 能观察到我们真正要修的旧行为。

---

# 30. Reference evidence 为什么是 18 tests 而不是 coverage 数字

因为我们想证明的是具体 claims：

```text
validation order
error translation
cancel partition
request identity
conflict
side-effect cardinality
view authority
```

即使 coverage 100%，如果没有：

```text
same id + different intent
```

这个 test，最危险的 idempotency bug 仍可能存活。

所以 instructor 不把 coverage percentage 当验收结果。

---

# 31. 一个应该被 review 拒绝的“看起来很聪明”的实现

```python
def submit_job(command):
    request_id = sha256(command.encode()).hexdigest()
    if request_id in seen:
        return seen[request_id]
    ...
```

问题不是 hash collision。

更根本：

```text
same bytes
!=
same logical intent
```

这会错误 dedup 两个独立相同 command。

这类 bug 很容易由 Agent 生成，因为它把“技术去重”误当“语义去重”。

---

# 32. 一个应该被 review 拒绝的 catch-all

```python
try:
    ...
except Exception as exc:
    raise ApiError("INTERNAL") from exc
```

问题：

- programming bug 被隐藏；
- expected domain error 与 unexpected bug 混淆；
- tests 可能只看到统一 INTERNAL；
- operator diagnosis 更困难。

应该只翻译：

```text
你理解其 domain meaning 的 failure
```

未知 bug 让它 fail loudly，并在真正 RPC entry point 做最后的 INTERNAL safety translation/logging。

---

# 33. 一个应该被 review 拒绝的“exactly once”声明

reference patch 若写：

```text
TaskForge now guarantees exactly-once jobs.
```

必须 request changes。

它最多做了：

```text
same request ID + same intent
→ in-process duplicate submit does not create a second Job
```

它没有解决：

- concurrent duplicates；
- process crash；
- durable request registry；
- worker re-execution；
- external command side effects。

所以正确 claim 必须窄。

---

# 34. Agent Round A 可能出现的典型问题

vague prompt：

```text
Improve error handling and make submit safe to retry.
```

常见生成模式：

1. `@retry` 包住 submit；
2. payload hash 当 idempotency key；
3. catch-all Exception；
4. 10 个 custom error class；
5. 没有 same-id/different-intent test；
6. 只 assert return value，不 assert job count；
7. 文档声称 exactly-once。

这些不是模型“不会写代码”。

而是 task specification 没告诉它：

```text
什么 semantics 才算正确
```

---

# 35. Agent Round B 为什么更强

engineering spec 明确：

```text
same request identity
same intent
no duplicate job
```

以及：

```text
same identity + different intent = conflict
```

它把 search space 从：

```text
“想一个重试方案”
```

缩小成：

```text
“实现并证明这个 contract”
```

这就是 Agent 时代 SE 的核心价值之一。

---

# 36. M04 reference 的最终 ownership map

```text
raw API input
  owner of validation: public boundary / Command parser

job lifecycle
  owner: existing TaskForge job state/service

request identity
  owner: request registry

public error vocabulary
  owner: public boundary

human diagnostics
  owner: public boundary + internal logs (future)
```

这里没有要求一个 component 拥有所有东西。

而是每个 semantic fact 只有清楚 owner。

---

# 37. 当前刻意留下的债务

## 37.1 Request registry persistence

没有。

## 37.2 Idempotency retention window

没有。

## 37.3 Concurrent same-ID submit

未解决。

## 37.4 Atomic create + request-record

未解决。

## 37.5 Cancel observation race

未解决。

## 37.6 Remote serialization

未实现。

## 37.7 Retry backoff/budget

未实现。

这些不是遗漏。

它们分别服务后续：

```text
M07 concurrency/failure
M08 migration/compatibility
M09 architecture/process boundary
M11 production/reliability
```

---

# 38. 为什么课程不现在把这些全修完

如果 M04 直接实现：

- SQLite transaction；
- unique request constraint；
- lock；
- durable registry；
- remote RPC；
- retry middleware；
- tracing；

学生会看到一坨 mechanism。

但本章真正要学的是：

```text
API semantics
error ownership
boundary compression
request identity
```

教学系统必须控制 incidental complexity。

---

# 39. Instructor grading signals

高质量答案通常会：

- 先写 behavior table；
- 明确 no-effect guarantees；
- 不把 KeyError 当 domain contract；
- 用 caller action 设计 error taxonomy；
- same payload 与 same intent 分开；
- explicit request identity；
- same ID/different intent conflict；
- tests 检查 side-effect cardinality；
- public view detached；
- 对 crash/concurrency 限制诚实。

低质量答案通常会：

- 先写 exception classes；
- 全 catch；
- retry everything；
- payload hash；
- claim exactly-once；
- 只测 happy path；
- 把新 framework 当 architecture。

---

# 40. 本 lab 最终真正想训练的判断

不是：

```text
如何写 ApiError
```

而是：

> **Boundary design 是把内部机制、失败和不确定性压缩成稳定的 caller semantics。**

以及：

> **Idempotency 不是一个 retry decorator；它从“什么叫同一个 logical request”开始。**

如果学生能在未来面对任何 Agent-generated API patch 时先问：

```text
same bytes 还是 same intent？
error 对 caller 意味着什么？
outcome failure 还是 unknown？
谁拥有 dedup state？
这个 guarantee 到底覆盖哪个 effect？
```

M04 就达到了目的。
