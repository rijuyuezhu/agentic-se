# Lab 04 — 给 TaskForge 一个真正的 Boundary

> 对应 M04：API、Error 与 Boundary Design。
>
> 本实验的重点不是“写一个漂亮的 Python API”。重点是：**先把 caller-visible semantics 定义清楚，再让实现承载这些 semantics。**

---

# 0. 你拿到的 starter

目录：

```text
labs/taskforge/
```

M04 新增：

```text
src/taskforge/public_api.py
tools/m04_boundary_probe.py
```

先不要改代码。

运行：

```bash
cd labs/taskforge
PYTHONPATH=src uv run --with pytest --no-project python tools/m04_boundary_probe.py
```

当前 baseline 应展示类似：

```text
blank submit: {'job_id': 'job-1'}
unknown get: EXCEPTION KeyError: 'job-404'
unknown cancel: EXCEPTION KeyError: 'job-404'
cancel running: {'cancelled': False}
cancel succeeded: {'cancelled': False}
same payload twice: first='job-1', second='job-2'
```

然后确认原测试仍通过：

```bash
PYTHONPATH=src uv run --with pytest --no-project python -m pytest -q
```

课程仓库 baseline 已实际验证：

```text
6 passed
```

---

# 1. 第一阶段：只读 reconstruction

禁止立刻定义 `ApiError`。

先写 `m04-current-contract.md`，回答：

## 1.1 Public operations

当前 `public_api.py` 暴露：

```text
submit_job
get_job
list_jobs
cancel_job
```

为每个 operation 填：

| operation | accepted input | success | failure | side effect |
|---|---|---|---|---|
| submit_job | ? | ? | ? | ? |
| get_job | ? | ? | ? | ? |
| list_jobs | ? | ? | ? | ? |
| cancel_job | ? | ? | ? | ? |

注意区分：

```text
implemented behavior
```

和：

```text
intended public contract
```

当前代码存在，不代表它就是未来必须兼容的 contract。

---

# 2. 找出 boundary 已经隐藏了什么

不要把 starter 简单评价成“差”。

它其实已经做了一件有价值的事：

```text
service.get() → mutable Job
```

经过：

```text
public_api._view(...)
```

变成 serialization-friendly detached dict。

验证：

```python
view = public_api.get_job(job_id)
view["status"] = "succeeded"
assert public_api.get_job(job_id)["status"] == "queued"
```

这说明：

```text
boundary 可以比 underlying service 更强
```

这也是 M02 → M04 的连接。

写进报告：

> 为什么“service 仍有 representation exposure”不意味着 public boundary 也必须泄漏 authority？

---

# 3. 找出 boundary 没隐藏的 implementation accidents

重点检查：

```python
public_api.get_job("missing")
public_api.cancel_job("missing")
```

它们为什么是 `KeyError`？

追到：

```text
public_api
→ service
→ state.jobs[job_id]
→ dict semantics
```

回答：

1. 如果 `state.jobs` 改成 SQLite，`KeyError` 是否自然仍存在？
2. caller 是否应该依赖 Python dict 的 missing-key behavior？
3. 这是 domain error 还是 representation accident？

---

# 4. 分析 `cancelled: False` 到底丢了什么

构造至少四个 partition：

```text
unknown
QUEUED
RUNNING
terminal
```

如果想更完整：

```text
SUCCEEDED
FAILED
CANCELLED
```

分别运行 `cancel_job`。

回答：

```text
caller 看到的 observation 是否足以决定下一步？
```

特别比较：

```text
RUNNING → False
SUCCEEDED → False
```

它们对 UI / scheduler / admin tool 的意义可能一样吗？

不要先假设必须拆成不同 exception class。

先写 caller actions。

---

# 5. 新 feature request

产品现在提出：

> TaskForge 将来会通过 RPC 暴露给远端 client。client 可能因为 timeout 重发 submit。我们希望：
>
> 1. 输入错误在 side effect 前失败；
> 2. external caller 不依赖 Python implementation exceptions；
> 3. cancel failure 能表达 caller 可行动的原因；
> 4. 可选 request identity 允许安全 retry submit；
> 5. public read 不暴露 mutable authority。

你的任务不是直接实现。

先 review 这个 feature request。

---

# 6. 先写 desired behavior table

至少覆盖：

| operation | case | required semantics |
|---|---|---|
| submit | whitespace-only command | reject before side effect |
| submit | no request id | each call is a new logical request |
| submit | new request id | create exactly one job |
| submit | same id + same intent | same logical job, no duplicate |
| submit | same id + different intent | conflict, no new job |
| get | known id | detached public view |
| get | unknown id | stable NOT_FOUND semantic error |
| cancel | queued | transition to cancelled |
| cancel | unknown | NOT_FOUND |
| cancel | running | FAILED_PRECONDITION + status context |
| cancel | terminal | FAILED_PRECONDITION + status context |

再加两列：

```text
side effect guarantee
retry guidance
```

最终表至少应能回答：

```text
error 时是否保证 no effect？
```

---

# 7. 明确定义 “intent”

本实验默认采用一个刻意简单的规则：

```text
submit intent = exact validated command string
```

也就是说：

```text
"echo hi"
```

与：

```text
" echo hi "
```

是否同 intent，由你对 validation/normalization 的 contract 决定。

推荐初始方案：

```text
只用 strip() 判断是否为空
但保留原 command bytes/string 作为 intent
```

这样避免在 M04 顺便发明 shell normalization 语义。

如果你选择 normalize，必须明确：

```text
哪些变化 semantic-equivalent？
```

并为它写测试。

---

# 8. 设计 input representation

至少比较两个方案。

## Design A — raw string + boundary check

```python
def submit_job(command: str, ...):
    if not command.strip():
        ...
```

优点：简单。

缺点：内部仍可能继续传 raw primitive。

## Design B — domain value

```python
@dataclass(frozen=True)
class Command:
    value: str

    @classmethod
    def parse(...):
        ...
```

优点：已经建立的 invariant 可以随 representation 传播。

缺点：Python 并不能像 Haskell 那样给你完整静态 proof；如果 constructor 可随意调用，仍可能绕过。

写一段 trade-off memo：

> 在这个 40 行 core 里，额外 `Command` type 是否值得？

课程不规定答案。

---

# 9. 设计 public error model

你需要一个 stable machine-readable contract。

最低要求：

```text
category/code
reason
human message
metadata
```

一个可能的形状：

```python
ApiError(
    code="FAILED_PRECONDITION",
    reason="JOB_NOT_CANCELLABLE",
    message="...",
    metadata={"job_id": ..., "status": ...},
)
```

但你也可以使用：

```text
Result[Success, Error]
```

或其他显式结构。

要求：

- tests 不 parse message；
- caller 不依赖 `KeyError`；
- metadata 只放公开且稳定的 context；
- 不要每个 status 一个 exception class，除非你能解释 caller action 为什么不同。

---

# 10. Error taxonomy 设计题

对于 cancel：

```text
RUNNING
SUCCEEDED
FAILED
CANCELLED
```

你至少考虑两种设计。

## A

统一：

```text
FAILED_PRECONDITION
reason=JOB_NOT_CANCELLABLE
metadata.status=...
```

## B

细分：

```text
JOB_RUNNING
JOB_ALREADY_FINISHED
JOB_ALREADY_CANCELLED
```

写：

- caller action；
- compatibility cost；
- extensibility；
- test complexity；
- 新增 lifecycle state 时的影响。

选择一个并解释。

---

# 11. Request identity contract

扩展 submit：

```text
request_id: optional
```

本实验要求：

## 没有 request_id

```text
每次调用 = 新 logical request
```

所以：

```text
same command twice
→ two jobs
```

这是合法行为，不是 bug。

## 新 request_id

```text
create one job
record request identity → intent → job identity
```

## same request_id + same intent

```text
return same logical job
no extra job
```

response 可以反映 job 当前状态，不要求 bytes 完全和第一次一致。

## same request_id + different intent

```text
CONFLICT
no new job
```

---

# 12. 不允许用 payload hash 替代 request identity

禁止把：

```python
hash(command)
```

当唯一 request identity。

因为：

```text
same command twice
```

可能是真正两个独立 job。

如果你仍想使用 hash，它只能作为：

```text
intent comparison / integrity aid
```

而不是 logical request identity 本身。

---

# 13. Ownership map

实现前画：

```text
Job lifecycle fact
owner = ?

Request identity fact
owner = ?

Public error translation
owner = ?

Input validity
owner = ?
```

推荐思考：

```text
request registry
```

是否是 duplicated authority？

如果它只回答：

```text
request_id → original intent / job_id
```

而 job store 回答：

```text
job_id → lifecycle state
```

它们是两个 semantic facts。

不要因为“single source of truth”口号把所有 state 强塞进一个 dict。

---

# 14. Request registry lifetime

当前 TaskForge 纯内存。

本实验不要求：

- persistence；
- retention window；
- cleanup；
- multi-process consistency；
- concurrency safety。

但 design memo 必须明确这些是 **non-goals / deferred problems**。

并说明：

```text
一旦 TaskForge restart，当前 in-memory idempotency guarantee 会怎样？
```

不要声称“exactly once forever”。

---

# 15. 先写 fail-before tests

至少新增以下 tests。

## Input

```text
blank command rejected
no job created
```

## Unknown

```text
get unknown → NOT_FOUND
cancel unknown → NOT_FOUND
```

## Cancel

```text
cancel queued → success
cancel running → FAILED_PRECONDITION(status=running)
terminal partition → FAILED_PRECONDITION(status=...)
```

## Idempotency

```text
no request id + same command → two jobs
same id + same command → one job / same job id
same id + different command → conflict / still one job
```

## View

证明 public result 不授予 authoritative mutation capability。

---

# 16. 必须证明 validation 在 side effect 前

测试不能只写：

```python
with raises(INVALID_ARGUMENT):
    submit_job(" ")
```

还必须：

```python
assert list_jobs() == []
```

因为下面这种错误实现也会“正确报错”：

```python
job_id = service.submit(command)
if invalid(command):
    raise InvalidArgument
```

但已经产生 ghost job。

这就是 M03 的 oracle thinking。

---

# 17. 必须证明 idempotency 的 effect，而不只返回值

差测试：

```python
assert submit(req_id="x") == submit(req_id="x")
```

如果两个不同 job 恰好 equality 比较只看 command，也可能误过。

更好：

```text
same job identity
+
job count remains 1
```

也就是同时观察：

```text
result identity
side effect cardinality
```

---

# 18. Same ID + different intent 必须是独立测试

这是最容易遗漏的 idempotency bug。

错误实现：

```python
if request_id in requests:
    return requests[request_id].job_id
```

它会让：

```text
req=x, command=A
req=x, command=B
```

第二次悄悄得到 A 的 job。

所以必须验证：

```text
CONFLICT
+
no B job created
+
request mapping remains A
```

---

# 19. Response semantic equivalence

加一个进阶测试：

```text
first submit(request_id=x) → job queued
worker claims it → running
retry same submit(request_id=x)
```

你可以选择：

### Design A

返回当前 job view：

```text
same job_id
status=running
```

### Design B

保留最初 success snapshot。

两者都可以设计成立。

本课程推荐 A，原因：

- 当前 TaskForge 没有历史 response store；
- caller 真正需要的是 same logical job identity；
- 避免额外 snapshot lifetime state。

但你必须在 contract 中写清楚。

---

# 20. 不要声称 job execution exactly-once

这个实验只做：

```text
idempotent job creation
```

不做：

```text
exactly-once command execution
```

因为 worker crash window 还没有解决。

在 design memo 里明确写：

```text
same request id prevents duplicate Job creation,
but does not yet prove the command can never execute twice.
```

这条会在 M07 回来。

---

# 21. 实现约束

为了让实验聚焦，不允许：

- 引入 FastAPI / Flask / gRPC；
- 引入数据库；
- 引入第三方 Result framework；
- 顺便重构整个 `service.py`；
- 顺便解决并发；
- 顺便做 persistence；
- 加 20 个 exception subclasses。

允许：

- 小型 dataclass / enum；
- 一个明确 request registry；
- public DTO/view；
- focused helper functions；
- 必要的 test reset hook。

目标是 **semantic design**，不是 framework design。

---

# 22. Representation exposure 不能回归

M04 starter 的一个优点是：

```text
public_api
```

已经把 internal mutable Job 转成 detached representation。

你的重构不能为了“类型更漂亮”退回：

```python
return service.get(job_id)
```

如果用 `JobView` dataclass，推荐 frozen/read-only。

测试至少验证：

```text
修改 caller-side value
不能改变 authoritative state
```

---

# 23. Internal error 不应直接穿过 public boundary

最终至少 grep / inspect：

```text
public_api.py
```

确认 unknown job 的正常 domain path 不再依赖 caller 处理：

```text
KeyError
```

但不要写：

```python
except Exception:
    raise INTERNAL
```

因为这样可能吞掉 programming bug。

只 catch / translate 你真正理解的 failure。

---

# 24. Exception vs Result：Design it twice

实现前画两个版本。

## Version A

```python
JobView | raises ApiError
```

## Version B

```python
Result[JobView, ApiError]
```

然后比较：

| criterion | exception | result |
|---|---|---|
| Python ergonomics | | |
| failure visibility | | |
| RPC mapping | | |
| boilerplate | | |
| caller misuse | | |

不要用“Rust 都用 Result”或“Python 都用 exception”作为唯一理由。

---

# 25. Public error code vs reason

推荐两层：

```text
code: broad recovery category
reason: domain-specific stable identity
```

例如：

```text
code=INVALID_ARGUMENT
reason=INVALID_COMMAND
```

```text
code=NOT_FOUND
reason=JOB_NOT_FOUND
```

```text
code=FAILED_PRECONDITION
reason=JOB_NOT_CANCELLABLE
metadata.status=running
```

```text
code=CONFLICT
reason=REQUEST_ID_REUSED
```

不要把 message 当 reason。

---

# 26. Error message 测试不要过度精确

不推荐：

```python
assert str(exc) == "Job job-3 cannot be cancelled while running."
```

除非文案本身就是 compatibility contract。

推荐测试：

```text
code
reason
required metadata
```

message 只检查：

```text
非空 / 包含基本 actionable context
```

避免把文案改进变成测试破坏。

---

# 27. Agent Round A — vague prompt

在独立 branch / copy 上给 Agent：

```text
Improve TaskForge's public API error handling and make submit safe to retry.
```

不再补充。

记录：

- 它是否先读 state machine？
- 是否定义 request identity？
- 是否用 payload hash？
- 是否 catch `Exception`？
- 是否新增大量 error class？
- 是否 validation after side effect？
- 是否声称 exactly-once？
- 是否有 fail-before evidence？

不要提示它正确答案。

---

# 28. Agent Round B — engineering spec

然后重新从 baseline 做第二轮。

至少提供：

```text
Goal:
Introduce a stable public boundary contract for input errors, lifecycle errors,
and retry-safe job creation.

Semantics:
- whitespace-only command is INVALID_ARGUMENT and creates no job;
- unknown get/cancel is NOT_FOUND;
- cancel of non-QUEUED known job is FAILED_PRECONDITION with status metadata;
- no request_id means every submit is a distinct logical request;
- same request_id + same exact validated command returns the same logical job;
- same request_id + different command is a conflict and creates no new job;
- public views must not expose mutable Job authority.

Non-goals:
- persistence;
- concurrency safety;
- exactly-once command execution;
- HTTP/RPC framework;
- broad service refactor.

Evidence required:
- behavior table before code;
- fail-before tests;
- focused tests;
- full existing suite;
- proof that duplicate retry creates only one job;
- independent review of state ownership and error translation.
```

比较两轮结果。

---

# 29. Agent review checklist

对 Agent patch 逐项检查：

## Input

- blank command 是否 side effect 前拒绝？
- `request_id=""` 的语义是否明确？
- validation logic 是否散落？

## Error

- `KeyError` 是否仍作为 public domain contract？
- error reason 是否稳定？
- caller 是否需要 parse string？
- catch-all 是否吞 programming bug？

## Idempotency

- request identity 是 caller intent 还是 payload guess？
- same id/same intent 是否真正 no duplicate effect？
- same id/different intent 是否 conflict？
- retry response 是否仍引用同一个 job？

## Ownership

- request registry 是否只维护 request identity？
- 是否复制 job status？
- reset/test lifecycle 是否明确？

## Claims

- 是否把“job creation dedup”夸大成“exactly once execution”？

---

# 30. Evidence bundle

最终提交：

```text
m04-current-contract.md
m04-design-a.md
m04-design-b.md
m04-behavior-table.md
m04-agent-comparison.md
代码 diff
测试
```

并附：

```bash
PYTHONPATH=src uv run --with pytest --no-project python -m pytest -q
```

如果你修改了 probe，可以再附：

```bash
PYTHONPATH=src uv run --with pytest --no-project python tools/m04_boundary_probe.py
```

---

# 31. Instructor reference

完成实验前不要读：

```text
../case-studies/m04/instructor-analysis.md
```

它包含：

- current contract reconstruction；
- error taxonomy；
- reference request registry；
- fail-before tests；
- verified reference implementation；
- ownership review；
- 为什么没有把 cancel 自动变成幂等 success；
- 哪些问题刻意留给 M07/M08。

---

# 32. 评分重点

## 20% — Contract reconstruction

是否分清：

```text
current behavior
vs
intended API
```

## 20% — Boundary design

是否真正隐藏 implementation knowledge，而不只是多一层 wrapper。

## 20% — Error semantics

caller action、machine identity、metadata 是否清楚。

## 20% — Idempotency semantics

是否正确定义 logical request identity 和 same-id conflict。

## 10% — Evidence

是否有 fail-before、side-effect oracle、full-suite regression。

## 10% — Agent orchestration

是否能看出 vague prompt 与 engineering spec 的质量差异。

不按：

```text
exception class 数量
代码行数
pattern 名称
```

评分。

---

# 33. 实验结束时你应该真正学会的东西

不是：

> Python 怎么定义 custom exception。

而是：

> **一个边界真正有价值，是因为它把内部复杂、易变、mechanism-specific 的世界压缩成 caller 可以长期依赖的少量语义。**

以及：

> **retry-safe API 不是“加一个重试循环”，而是把 logical request identity 和 side-effect contract 设计进去。**
