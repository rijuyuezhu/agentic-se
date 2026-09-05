# M04 — API、Error 与 Boundary Design：让边界吸收复杂度

> 这一章不是 REST API 教程，也不是“异常处理最佳实践”。
>
> 真正目标是：**学会设计一个边界，使 caller 只需要理解稳定、可行动的语义，而不必继承内部实现的全部复杂度。**

---

# 0. 从 TaskForge 现在的接口开始

当前 TaskForge 有这样几个函数：

```python
submit(command: str) -> str
get(job_id: str) -> Job
list_jobs() -> list[Job]
cancel(job_id: str) -> bool
```

乍看很简单。

但问几个真实 caller 问题：

```text
Q1: submit("") 合法吗？
Q2: get("job-does-not-exist") 会发生什么？
Q3: cancel(...) 返回 False 到底意味着什么？
Q4: running 和 succeeded 都 cancel 失败，caller 能区分吗？
Q5: service 内部把 dict 换成 SQLite 后，KeyError 还会继续存在吗？
Q6: client timeout 后不知道 submit 成没成功，能安全 retry 吗？
Q7: 两次完全一样的 command，是 retry，还是用户真想创建两个 job？
```

当前实现没有给这些问题一个完整、稳定的答案。

这说明：

> **function signature 很短，不等于 API contract 很简单。**

真正复杂的东西可能只是被隐藏在：

```text
caller 猜测
implementation accident
exception type
string message
timing assumption
implicit retry behavior
```

里。

M04 要解决的就是这些“边界上的隐性复杂度”。

---

# 1. API 不只是函数名和参数列表

很多人看到 API，会想到：

```python
create_job(command: str) -> Job
```

但真正的 API contract 至少包含：

```text
input domain
output semantics
side effects
error semantics
state transition
concurrency semantics
retry semantics
compatibility promise
observability
```

例如：

```text
create_job(command)
```

你至少应该知道：

- `command` 能否为空？
- 空白是否 normalize？
- 成功意味着 job 已 durable，还是只进入内存 queue？
- job id 何时分配？
- caller timeout 后能否重试？
- retry 会不会产生两个 job？
- 同一个 request id 重发时返回旧结果还是报 AlreadyExists？
- validation failure 是否有 side effect？
- unknown internal failure 暴露什么？

所以：

> **API 设计，本质上是在分配 knowledge、responsibility 和 uncertainty。**

---

# 2. Boundary 为什么如此重要

boundary 是两个不同 responsibility / trust / representation 区域之间的接口。

例如：

```text
CLI args
   ↓
application boundary
   ↓
domain core
```

或者：

```text
HTTP JSON
   ↓
RPC/API boundary
   ↓
service
```

或者：

```text
scheduler
   ↓
worker protocol
   ↓
remote process
```

boundary 最重要的工作之一，是把：

```text
外部世界的模糊性
```

转换成：

```text
内部世界的更强假设
```

例如：

```text
raw string
  ↓ parse / validate / normalize
Command
```

或者：

```text
OSError / KeyError / sqlite exception
  ↓ translate
JOB_NOT_FOUND / UNAVAILABLE / CONFLICT
```

一个好的 boundary 不只是“转发调用”。

它应该承担一部分 **semantic compression**。

---

# 3. Shallow boundary：最危险的“薄封装”

假设你写：

```python
def get_job(job_id: str):
    return service.get(job_id)
```

这确实是一个 wrapper。

但它隐藏了什么？

几乎什么都没隐藏。

caller 仍然需要知道：

- `service.get` 返回 mutable `Job`；
- unknown id 产生 `KeyError`；
- Job representation；
- internal lifecycle enum；
- 后续 persistence 改造可能改变 exception。

这就是 shallow boundary。

它增加了一层调用：

```text
interface count +1
```

却没有显著减少 caller cognitive load。

好的 boundary 更像：

```text
internal details
   │
   │  many cases
   ▼
[ boundary ]
   │
   │  stable semantic contract
   ▼
caller
```

这和 M02 的 deep module 是同一个方向。

---

# 4. “Pull complexity downward” 到底是什么意思

不是：

> server 永远应该比 client 更复杂。

而是：

> **把 complexity 放到拥有最多 information、最能统一处理、最能稳定维护 invariant 的那一层。**

例如 retry dedup。

如果 API 不支持 request identity：

```text
client A 写 reconciliation
client B 写 reconciliation
client C 猜 timeout 是否成功
client D 用 payload hash
client E 干脆不 retry
```

complexity 被复制到每个 caller。

如果 service boundary 能提供：

```text
request_id
+
idempotent replay contract
```

那么：

```text
复杂度集中到一处
callers 简化
contract 一致
failure behavior 更可验证
```

服务实现可能更复杂，**系统整体却更简单**。

这就是工程中的“局部复杂度增加，整体复杂度下降”。

---

# 5. Boundary 的第一份工作：把 raw input 变成更精确的 representation

假设 core 函数接受：

```python
def execute(command: str):
    ...
```

而 `command` 其实要求：

```text
必须含至少一个非空白字符
```

如果全系统都只传 `str`，那么每个地方都可能问：

```python
if not command.strip():
    ...
```

于是 invariant 变成：

```text
“某处应该已经检查过”
```

这很危险。

## 5.1 Validate-and-forget

```python
def validate_command(command: str) -> None:
    if not command.strip():
        raise ValueError("empty command")
```

调用：

```python
validate_command(command)
run(command)
```

问题是 `run` 看到的仍然是 `str`。

它无法从 representation 区分：

```text
raw string
validated command
```

检查获得的信息被丢掉了。

## 5.2 Parse into a domain value

更好的形态：

```python
@dataclass(frozen=True)
class Command:
    value: str

    @classmethod
    def parse(cls, raw: str) -> "Command":
        if not raw.strip():
            raise InvalidCommand(...)
        return cls(raw)
```

core：

```python
def run(command: Command):
    ...
```

现在 boundary 做：

```text
raw string
   ↓
parse
   ↓
Command
```

之后 core 的 assumption 更强。

这就是 “parse, don't validate” 背后的真正工程价值：

> **把已经证明过的事实保存在 representation 中，而不是让下游靠记忆继续相信它。**

---

# 6. “Make illegal states unrepresentable” 不应被宗教化

这个原则很强，但非常容易被 Agent 过度执行。

例如：

```text
job status + exit code
```

可能存在非法组合：

```text
QUEUED + exit_code=0
RUNNING + exit_code=7
```

你可以设计：

```python
QueuedJob(...)
RunningJob(...)
SucceededJob(exit_code=0)
FailedJob(exit_code=int)
CancelledJob(...)
```

通过 sum type 把一些非法状态消掉。

这可能很好。

但不代表每个 invariant 都值得这样做。

例如：

```text
request_id 在过去 24 小时内唯一
```

这依赖：

- 时间；
- durable store；
- 其他请求；

不可能只靠一个本地 type 完成证明。

所以更准确的原则是：

> **尽可能让 representation 承载已经建立的 invariant，但不要把系统世界假装成纯类型世界。**

合法工具包括：

```text
type / constructor
encapsulation
transaction
state machine
runtime validation
unique constraint
lock
idempotency record
test
```

选哪一个取决于 invariant 的实际 owner。

---

# 7. Error 到底是什么

最差的理解：

> error 就是 exception。

更好的理解：

> **error 是 operation 无法按其 normal success contract 完成时，boundary 向 caller 暴露的语义信息。**

表示手段可能是：

```text
exception
Result/Either
status code
error object
sentinel
callback
stream terminal status
```

这些只是 encoding。

真正重要的是：

```text
caller 可以区分哪些情况？
caller 每种情况允许做什么？
```

---

# 8. 从 caller action 反推 error taxonomy

假设 internal errors 有：

```text
FileNotFoundError
PermissionError
sqlite3.OperationalError
WorkerDisconnected
TimeoutError
KeyError
```

最简单的 boundary 是全部透传。

这样 caller 必须学会内部 implementation taxonomy。

但 caller 可能真正只有三种动作：

```text
A. 修正请求
B. 稍后 retry
C. 报给用户/运维
```

那么 public error taxonomy 更可能围绕：

```text
INVALID_ARGUMENT
NOT_FOUND
FAILED_PRECONDITION
UNAVAILABLE
INTERNAL
```

再用 machine-readable reason 补 domain distinction。

例如：

```text
code = FAILED_PRECONDITION
reason = JOB_NOT_CANCELLABLE
metadata = {status: running}
```

而不是直接：

```text
ValueError("cannot cancel")
```

---

# 9. Collapse errors 与 preserve distinctions

error design 有两个相反风险。

## 9.1 过度细分

```text
SOCKET_READ_EOF
SOCKET_READ_RESET
SOCKET_WRITE_EPIPE
SQLITE_BUSY
WORKER_CHANNEL_CLOSED
...
```

caller 其实全部只能：

```text
retry later
```

这时细分只是泄漏 implementation complexity。

## 9.2 过度 collapse

例如：

```text
ERROR
```

但实际可能是：

```text
INVALID_ARGUMENT → 修请求
NOT_FOUND → 停止 retry
UNAVAILABLE → retry
CONFLICT → re-read then decide
PERMISSION_DENIED → 请求权限
```

如果 caller action 不同，就必须保留 distinction。

所以可以使用一个 review heuristic：

> **如果两个 failure 需要不同 caller action，它们通常不应无条件 collapse。**

反过来：

> **如果两个 failure 的 public action 与 compatibility promise 完全相同，先问是否真的值得让 caller 区分。**

---

# 10. Human message 与 machine contract 必须分开

脆弱 API：

```python
try:
    cancel_job(id)
except Exception as e:
    if "running" in str(e):
        ...
```

为什么危险？

message 的目标是给人读。

它可能因为：

- wording 改善；
- localization；
- context 增加；
- punctuation；

而变化。

machine 应该依赖：

```text
stable code
stable reason
structured metadata
```

例如：

```json
{
  "code": "FAILED_PRECONDITION",
  "reason": "JOB_NOT_CANCELLABLE",
  "message": "Job job-3 cannot be cancelled while running.",
  "metadata": {
    "job_id": "job-3",
    "status": "running"
  }
}
```

这里：

```text
message
```

可以改善。

而：

```text
reason + metadata keys
```

属于 machine contract。

---

# 11. Error translation：边界不是 exception forwarding service

假设 storage 以后变成 SQLite：

```python
sqlite3.IntegrityError
```

可能由很多原因触发：

```text
duplicate request id
foreign key failure
buggy schema assumption
```

如果 boundary 直接把它暴露给 client：

```text
client coupling → SQLite
```

以后换 PostgreSQL：

```text
exception 改了
client broken
```

正确思路：

```text
internal failure
   ↓ classify with domain context
public semantic failure
```

例如：

```text
UNIQUE(request_id) violation
      ↓
IDEMPOTENCY_CONFLICT
```

或者：

```text
storage temporarily unavailable
      ↓
UNAVAILABLE
```

关键是 boundary 需要足够 context 才能正确翻译。

所以 error translation 往往也是 **ownership 问题**。

---

# 12. 哪一层应该处理 error？

一个非常实用的问题：

> 哪一层拥有足够 information 决定正确的下一步？

例如：

```text
worker socket EOF
```

socket 层知道：

```text
connection closed
```

但它可能不知道：

```text
这个 worker 是可以重连？
job 是否可 retry？
side effect 是否已发生？
```

所以 socket 层通常不应该决定：

```text
retry job
```

它只能报告更低层 fact。

上层 scheduler 拥有更多 workflow semantics，才可能做正确决策。

这叫 **error ownership**。

---

# 13. Error handling 的四种方向

面对 failure，不只有“throw”。

## 13.1 Eliminate

重新定义 abstraction，让 case 不再是 error。

例如：

```text
delete missing item
```

如果 contract 是：

```text
after delete, item must be absent
```

那么“原来就不存在”可以自然算成功。

这使 delete 更接近 idempotent semantics。

但这是不是正确 contract，要看 product semantics。

## 13.2 Mask / recover

boundary 内部自动恢复：

```text
read replica fails
→ try another replica
```

caller 不需要知道每次 replica failure。

## 13.3 Collapse / translate

多个 mechanism errors：

```text
network reset
worker channel closed
service restart
```

都翻译为：

```text
UNAVAILABLE
```

前提是 caller action 确实相同。

## 13.4 Surface

如果 caller 必须知道：

```text
permission denied
invalid argument
conflict
ambiguous outcome
```

就明确暴露。

成熟 error handling 不是“异常越少越好”，而是：

> **每个 surfaced error 都应该有清楚的 semantic reason。**

---

# 14. Temporal coupling：最隐蔽的 API complexity

假设 API：

```python
client = Client()
client.configure(...)
client.connect()
client.authenticate()
client.start()
client.submit(...)
```

caller 必须知道一个隐藏协议：

```text
configure
  ↓
connect
  ↓
authenticate
  ↓
start
  ↓
submit
```

如果顺序错：

```text
InvalidStateError
```

这叫 temporal coupling。

它把 state machine knowledge 推给 caller。

有时无法避免。

但常常可以改成：

```python
client = connect(config, credential)
client.submit(...)
```

让 constructor/factory 内部完成必要 transition。

或者：

```text
DisconnectedClient
   ↓ connect()
ConnectedClient
   ↓ authenticate()
AuthenticatedClient
```

让 representation 表达 protocol state。

选择哪一种取决于语言和复杂度。

---

# 15. API 应该让 illegal call 难发生，而不是只让它报错更漂亮

例如：

```python
finish(job_id, exit_code)
```

如果 caller 可以对 `QUEUED` job 调 finish，然后 API 只是在 runtime 报：

```text
FAILED_PRECONDITION
```

这是有用的 safety net。

但更深的问题是：

```text
为什么这个 caller 拥有 finish 任意 job 的 capability？
```

也许更好的 API 是：

```python
lease = claim_next(worker_id)
finish(lease, exit_code)
```

`lease` 本身证明：

```text
这个 worker 当前拥有完成该 job 的 authority
```

于是很多 invalid state 不再需要 caller 猜。

这把 M04 与 M02 ownership 连起来。

---

# 16. Boolean return 往往隐藏太多语义

当前：

```python
cancel(job_id) -> bool
```

`False` 可能表示：

```text
job running
job succeeded
job failed
job cancelled already
unknown job?
```

如果 unknown 抛 KeyError，其他返回 False，那么 caller 还得知道这种混合 encoding。

布尔值只有在真正二元语义时才好。

例如：

```text
contains(key) -> bool
```

但如果 caller 后续动作取决于失败原因，更适合：

```text
success result
or
structured error
```

而不是不断扩展：

```python
False
None
-1
"error"
```

---

# 17. Error type 数量不是设计质量指标

Agent 特别容易做这种“专业化”：

```python
class JobNotFoundError(...)
class JobAlreadyRunningError(...)
class JobAlreadySucceededError(...)
class JobAlreadyFailedError(...)
class JobAlreadyCancelledError(...)
class JobCannotCancelError(...)
class JobStateError(...)
```

看起来很完整。

但 caller 可能只需要：

```text
NOT_FOUND
FAILED_PRECONDITION(reason=JOB_NOT_CANCELLABLE, status=...)
```

多 exception class 可能只是把 state-space mechanically 映射成 class-space。

真正评价标准是：

```text
caller 能否做正确决策？
contract 是否稳定？
内部 representation 能否变化？
```

---

# 18. Retry 不是 error handling 的附加项

很多 API 先设计 success/error，最后才问：

```text
要不要 retry？
```

对于有 side effect 的 distributed operation，这太晚了。

因为 retry 本身会改变 API 所需语义。

最典型场景：

```text
client → create job
server creates job
response lost
client timeout
```

此时 caller 只知道：

```text
outcome unknown
```

不是：

```text
operation failed
```

这是一个极重要 distinction。

---

# 19. Failure 与 unknown outcome 不一样

考虑：

```text
INVALID_ARGUMENT
```

server 在任何 side effect 前拒绝。

caller 可以知道：

```text
job 没创建
```

但：

```text
TIMEOUT
```

往往不能推出：

```text
job 没创建
```

它只说明：

```text
caller 没拿到完成确认
```

这两个 error 的 recovery 完全不同。

所以：

> **transport failure 不等于 application failure。**

这会在 M07/M09 变得更关键。

---

# 20. 什么叫 idempotent operation

一个实用定义：

> **对同一个 logical request 重复执行，不会产生额外的 intended effect。**

注意三个词：

```text
same logical request
intended effect
extra
```

例如：

```text
delete job
```

如果 semantics 是：

```text
job 最终不存在
```

那么重复 delete 可以是 idempotent。

每次请求仍可能：

- 写日志；
- 增 metrics；
- 更新 tracing；

这不破坏 user-visible intended effect 的幂等性。

---

# 21. Idempotent 不等于 “same response bytes”

第一次 create：

```json
{
  "job_id": "job-17",
  "status": "queued"
}
```

retry 到来时，job 可能已经：

```text
running
```

第二次 response：

```json
{
  "job_id": "job-17",
  "status": "running"
}
```

bytes 不一样。

但 semantic contract 仍可能成立：

```text
这是同一个 logical create request
没有创建 job-18
```

所以幂等首先保护 effect identity。

---

# 22. 为什么 payload hash 不能普遍定义 request identity

假设：

```python
submit("python train.py")
submit("python train.py")
```

两次 payload 完全相同。

可能是：

```text
case A: 第一次 timeout，第二次是 retry
```

也可能是：

```text
case B: 用户真想启动两个独立训练任务
```

服务器单看 payload 无法知道 intent。

如果用：

```python
hash(command)
```

当 idempotency key，case B 会错误地被 dedup。

所以 request identity 最可靠的来源通常是：

```text
caller explicitly says:
these transmissions belong to the same logical request
```

---

# 23. Request ID 是 intent，不只是 UUID

`request_id` 的关键不是 UUID 长什么样。

而是 contract：

```text
same caller
+
same request_id
→ same logical request
```

于是 server 可以记录：

```text
request_id
→ original intent
→ result identity
```

例如：

```text
req-abc
→ command="python train.py"
→ job-17
```

retry：

```text
req-abc + same intent
→ job-17
```

而不是创建 job-18。

---

# 24. Same request ID + different intent 是什么？

这是 idempotency 设计里必须明确的 edge case。

第一次：

```text
request_id = req-abc
command = "echo first"
```

后来：

```text
request_id = req-abc
command = "rm -rf /tmp/x"
```

不能简单返回旧结果，也不能执行新 intent。

因为 request identity 已经被占用。

更合理的是：

```text
IDEMPOTENCY_CONFLICT
```

或者类似 stable semantic error。

这条 invariant：

```text
one request identity → one intent
```

必须由 idempotency state owner 维护。

---

# 25. Idempotency state 是 duplicated authority 吗？

M02 后你应该本能警惕：

```text
又加一张 request_id map？
是不是第二份 state authority？
```

答案：不一定。

看它 authoritative 地回答什么事实。

job store：

```text
job-17 当前 status 是什么？
```

request record store：

```text
req-abc 代表哪个 logical create request？
```

这是两个不同 semantic facts。

可以：

```text
JobStore owns job lifecycle
RequestRegistry owns request identity
```

只要不要让 RequestRegistry 自己也复制维护 job lifecycle。

这就是 ownership reasoning，而不是“全系统只能有一张表”。

---

# 26. Retryability 是 operation property + failure property

错误做法：

```python
except Exception:
    retry()
```

更正确的判断：

```text
operation 可以安全重复吗？
+
这个 failure 是 transient 吗？
+
当前 layer 有足够语义判断吗？
```

例如：

```text
INVALID_ARGUMENT
```

同样请求 retry 没意义。

```text
UNAVAILABLE
```

如果 operation idempotent，通常可 retry。

```text
CONFLICT
```

通常需要：

```text
重新读取 state
→ 再做 higher-level decision
```

而不是 blind retry 同一写操作。

---

# 27. Retry 应在哪一层发生？

假设：

```text
transaction:
  reserve quota
  create job
  record billing
```

`create job` 返回 conflict。

如果底层 SDK 自己无限 retry `create job`，可能破坏整个 workflow 的语义。

有时正确策略是：

```text
abort current transaction
restart whole workflow
```

所以：

> **retry layer 应该是拥有足够 transaction semantics 的最低层。**

不是越底层越自动越好。

---

# 28. Backoff / jitter 不是 M04 的重点

retry 还有：

- exponential backoff；
- jitter；
- budget；
- deadline；
- retry storm；

这些会在 M07/M11 深入。

M04 只先建立一个更基础的事实：

> **如果 operation semantics 本身不支持安全重试，再漂亮的 backoff 也只是更慢地重复 side effect。**

---

# 29. API boundary 与 internal boundary 不一样

内部函数可以有更丰富、更贴近 implementation 的 failure types。

例如：

```text
StorageBusy
WorkerDisconnected
LeaseExpired
```

跨 public boundary 后，可能 collapse 为：

```text
UNAVAILABLE
```

但内部保留 distinction 可能有助于：

- logging；
- recovery；
- metrics；
- targeted retry。

所以：

```text
internal vocabulary
!=
external vocabulary
```

boundary translation 正是 separation point。

---

# 30. Error translation 不应销毁诊断信息

“对外 collapse”不代表“内部什么也不留”。

例如外部：

```text
UNAVAILABLE
reason=WORKER_UNAVAILABLE
```

内部日志可以有：

```text
worker_id
socket errno
last heartbeat
attempt id
trace id
stack
```

可以同时做到：

```text
public API stable
+
production diagnosis rich
```

不要把“信息隐藏”误解成“丢信息”。

---

# 31. Boundary validation 必须发生在 side effect 前

假设：

```python
def submit(command, request_id):
    allocate_id()
    write_job()
    validate_request_id(request_id)
```

这是非常危险的顺序。

如果 `request_id` 非法：

```text
API 返回 validation error
```

但 job 已经被创建。

caller 通常会假设：

```text
INVALID_ARGUMENT → no side effect
```

所以 boundary 的一般结构应尽量是：

```text
parse / validate
      ↓
authorization / precondition
      ↓
commit side effect
      ↓
produce result
```

当然在 distributed world 中不能总是这么完美，但这是重要 baseline。

---

# 32. Partial side effect 让 error semantics 变难

假设：

```text
1. allocate job id
2. persist job
3. publish to queue
```

第 3 步失败。

API 返回：

```text
UNAVAILABLE
```

那么 job 已经存在吗？

如果 caller retry，会怎样？

这就是：

```text
partial failure
```

M04 先要求你意识到它。

M07 会进一步讨论：

- atomicity；
- rollback；
- retry；
- recovery；
- outbox；
- crash windows。

但一个好 API 在 M04 阶段至少应该明确：

```text
success/failure 对 side effect existence 到底承诺什么
```

---

# 33. “No side effect on error” 是强 contract，不要随便承诺

很多 API 文档隐式给人感觉：

```text
报错 = 什么都没发生
```

但真实系统未必能做到。

如果你真的能保证：

```text
INVALID_ARGUMENT
NOT_FOUND
FAILED_PRECONDITION
```

在 mutation 前被检测，那么可以明确承诺：

```text
no effect
```

但对于：

```text
DEADLINE_EXCEEDED
UNAVAILABLE
```

可能只能承诺：

```text
outcome may be unknown
```

这一区分极其重要。

---

# 34. API design 是 state machine design 的一部分

TaskForge job lifecycle：

```text
QUEUED
  ↓ claim
RUNNING
  ↓ finish
SUCCEEDED / FAILED

QUEUED
  ↓ cancel
CANCELLED
```

那么 public API 其实定义了 state machine transitions：

```text
cancel(job_id)
```

不是“一个普通函数”。

它代表：

```text
QUEUED → CANCELLED
```

因此 error semantics 可以直接来自 transition model：

```text
unknown job
→ NOT_FOUND

RUNNING / terminal
→ FAILED_PRECONDITION(JOB_NOT_CANCELLABLE, status=...)
```

而不是随实现写几个 if。

---

# 35. State-specific API 可以降低 invalid transition complexity

当前 API：

```python
cancel(job_id: str)
```

caller 可以对任何 id 调用。

另一种设计：

```python
queued_job.cancel()
```

或者：

```python
cancel(QueuedJobRef)
```

这样 type/representation 帮你消除一部分 invalid transition。

但代价是：

- object freshness；
- distributed staleness；
- more types；
- conversion complexity。

所以不要机械采用。

对远端 mutable state 来说：

```text
“我手里拿的是 QueuedJobRef”
```

也不代表 server 此刻仍 queued。

这说明 type proof 的有效范围必须明确。

---

# 36. Staleness：边界 contract 不能假装时间停止

client 读取：

```text
status=QUEUED
```

下一毫秒 worker 可能 claim：

```text
status=RUNNING
```

然后 client：

```text
cancel
```

返回：

```text
FAILED_PRECONDITION
```

这不是 API 自相矛盾。

这是 mutable concurrent system 的事实。

所以：

> **read result 是 observation，不是永恒 capability。**

如果 operation 需要基于旧状态保证原子条件，应使用：

- expected version；
- lease；
- CAS；
- transaction；

而不是 caller 的旧 snapshot。

M07/M08 会再展开。

---

# 37. Error message 是 UX，error reason 是 protocol

例如：

```text
reason = JOB_NOT_CANCELLABLE
```

message 可以从：

```text
cannot cancel running job
```

改进成：

```text
Job job-17 is already running and can no longer be cancelled.
```

如果 client 依赖 `reason`，这次文案改动没有 compatibility break。

如果 client parse message：

```text
改文案 = 破 API
```

所以：

> **不要让 human text 被迫承担 machine identity。**

---

# 38. Error metadata 也是 API surface

一旦你提供：

```json
{
  "reason": "JOB_NOT_CANCELLABLE",
  "metadata": {
    "job_id": "job-17",
    "status": "running"
  }
}
```

client 可能依赖：

```text
metadata.status
```

未来删除这个 key，就可能是 compatibility break。

所以不要无脑把全部 internal context 都塞进 public metadata。

public metadata 应是：

```text
caller 有用
稳定可承诺
不泄密
```

的最小集合。

---

# 39. Public boundary 也是 security boundary

虽然本课程不展开安全工程，但 boundary 设计必须至少意识到：

- 不要把 stack trace 直接给外部 caller；
- 不要泄漏 filesystem path / secret / internal topology；
- error distinction 有时本身会泄漏 resource existence；
- authorization 应在 side effect 前；
- machine metadata 同样需要审计。

所以：

```text
rich diagnostics
```

和：

```text
public disclosure
```

不是同一个目标。

---

# 40. API 越“方便”不一定越好

考虑一个万能函数：

```python
submit(
    command,
    retry=True,
    create_if_missing=True,
    wait=True,
    timeout=None,
    force=False,
    ignore_errors=False,
    ...
)
```

它似乎很 flexible。

但 combination state-space 爆炸：

```text
2^N options
```

很多组合可能：

- 没意义；
- 冲突；
- 语义难解释；
- 测试难覆盖。

更好的 abstraction 往往不是更多 flags，而是：

```text
明确 operation
精确 input
少量 orthogonal options
```

这就是降低 illegal combinations。

---

# 41. Optional parameter 很容易制造隐式 protocol

例如：

```python
submit(command, request_id=None)
```

看起来很简单。

但必须明确：

```text
request_id=None
→ no dedup guarantee?
→ server generates id?
→ retry unsafe?
```

如果 `request_id` provided：

```text
same id + same intent → replay
same id + different intent → conflict
```

optional 不代表语义 optional。

它可能切换整个 reliability contract。

因此文档和 type 应尽量让这一区别显式。

---

# 42. Defaults 是 API semantics

如果 API 默认：

```text
retry=True
```

那你就在 contract 中决定：

- 哪些 error 可 retry；
- retry budget；
- idempotency；
- latency；
- side effect uncertainty。

所以 default 不是 UI 小事。

一个好的 default 应该：

```text
大多数 caller 可以安全接受
不要求 caller 理解隐藏危险
```

如果安全性依赖 caller 提供 request ID，那么 default retry 也必须与它协调。

---

# 43. Convenience API 可以存在，但不能伪造 guarantee

例如：

```python
submit(command)
```

可以作为 convenience。

但如果它没有 request identity，文档必须诚实：

```text
如果 response outcome uncertain，自动 retry 可能创建 duplicate job
```

另一 API：

```python
submit_once(command, request_id)
```

提供更强 guarantee。

不要让两个函数都叫：

```text
safe submit
```

却实际语义不同。

---

# 44. “Exactly once” 是危险词

很多系统喜欢说：

```text
exactly-once execution
```

但要问：

```text
exactly once 什么？
```

- request accepted once？
- job row created once？
- worker executes command once？
- external side effect once？
- client observes success once？

这些不是同一个事实。

idempotent create job 只能保证：

```text
same logical create request
→ no duplicate job creation
```

它并不自动保证：

```text
job command itself never executes twice
```

后者是 M07 的执行/lease/recovery 问题。

---

# 45. API guarantee 必须写到具体 effect

差的文档：

```text
This API is idempotent.
```

好的文档：

```text
When request_id is supplied, repeated submit requests with the same
request_id and the same command resolve to the same job_id and do not
create additional jobs within the request-id retention interval.
```

这样才能测试。

也才能 review。

---

# 46. API design 与 observability 的关系

如果 request_id 是 contract 的一部分，它也应该进入：

- log；
- trace；
- audit；
- debugging context。

这样你能回答：

```text
这两个 network attempts 是否属于同一个 logical request？
```

没有 logical identity，很多 distributed debugging 只能靠 timestamp 猜。

所以好的 API identity 同时改善 reliability 和 observability。

---

# 47. Error code 不是 root cause

例如：

```text
UNAVAILABLE
```

对 caller 是 recovery category。

内部 root cause 可能是：

```text
DNS
socket reset
worker restart
storage failover
```

不要要求一个 public code 同时承担：

```text
caller action
+
root cause taxonomy
+
operator diagnosis
```

这些是不同 concern。

可以通过：

```text
public code/reason
internal logs/traces
incident diagnostics
```

分别处理。

---

# 48. API 文档应记录 negative semantics

很多文档只写 happy path：

```text
submit creates a job
```

更关键的是：

```text
blank command → INVALID_ARGUMENT, no job created
unknown get → NOT_FOUND
cancel running → FAILED_PRECONDITION
same request id + same intent → same logical result
same request id + different intent → CONFLICT, no new job
```

这些 negative semantics 决定真实系统是否可组合。

---

# 49. Boundary tests 应该测 semantic partitions

对 `cancel`，不要只测：

```text
one success
one failure
```

应该从 state machine partition：

```text
unknown
QUEUED
RUNNING
SUCCEEDED
FAILED
CANCELLED
```

然后问每个 partition 的 contract。

对 idempotency：

```text
no request id
new request id
same id + same intent
same id + different intent
late retry
```

这是 M03 test partition 直接复用到 M04。

---

# 50. Boundary tests 不应该绑定 internal exception

如果 public contract 是：

```text
unknown job → NOT_FOUND
```

测试不应该要求：

```python
with raises(KeyError):
```

因为 storage 从 dict 变 DB 后，KeyError 本来就可以消失。

测试应在 public boundary 观察：

```text
ApiError.code == NOT_FOUND
```

这样内部 representation 可以自由演化。

---

# 51. Error contract 也需要 mutation thinking

可以故意注入：

```text
NOT_FOUND → INTERNAL
FAILED_PRECONDITION → False
same request id retry → creates new job
same id different intent → returns old job
blank command → creates job then errors
```

问：

```text
测试会失败吗？
```

如果不会，说明 error semantics 只是文档愿望，不是 executable contract。

---

# 52. Agent 最容易犯的 API 设计错误

## 52.1 Wrapper proliferation

需求：

```text
加 public API
```

Agent：

```python
def api_get(id):
    return service.get(id)
```

文件增加了，abstraction 没增加。

## 52.2 Exception-class explosion

每个 branch 一个 class，caller 更难处理。

## 52.3 Catch-all translation

```python
except Exception:
    raise ApiError("INTERNAL")
```

把本应暴露的 invalid argument / not found / conflict 全部吞掉。

## 52.4 Stringly-typed machine behavior

```python
if "not found" in str(exc):
```

## 52.5 Retry everything

```python
@retry(Exception)
```

## 52.6 Parameter-hash idempotency

没有先定义 logical request identity。

## 52.7 Validation after effect

先创建，再发现 input 无效。

## 52.8 Type cosplay

创建很多 dataclass/NewType，但 constructor 仍公开、invariant 仍可绕过，于是只是名字更漂亮。

---

# 53. 给 Agent 的 M04 task contract

以后不要说：

```text
帮我把 API 做健壮一点。
```

更好的模板：

```text
Before implementation, map the current public boundary and internal failure sources.

Desired contract:
- define accepted input domain;
- define normalization rules;
- list public success outcomes;
- list public error categories and caller actions;
- state whether each error guarantees no side effect or may have unknown outcome;
- identify internal errors that must not escape;
- define retryability per operation;
- define logical request identity;
- define same-id/same-intent behavior;
- define same-id/different-intent behavior;
- state non-goals.

Then provide:
1. behavior table;
2. state/ownership impact;
3. tests that fail before the change;
4. implementation;
5. focused and full-suite evidence;
6. review of compatibility and hidden coupling.
```

这会显著减少“先写代码再发明语义”。

---

# 54. M04 的 TaskForge feature request

本章实验会给 TaskForge 增加一个 external-style boundary。

初始 boundary 故意很 shallow：

```text
submit_job(command)
get_job(job_id)
list_jobs()
cancel_job(job_id)
```

它会保留一些问题：

- raw `str` 直接进入 core；
- blank command 被接受；
- `KeyError` 穿过 boundary；
- `cancel=False` 模糊；
- 没有 request identity；
- timeout 后 submit 无法安全 retry；
- public error contract 不存在。

学生要把它升级成一个明确 contract。

---

# 55. 实验目标 contract

本课程不会规定唯一代码结构，但要求最终 semantics 至少满足：

## Submit

```text
blank/whitespace-only command
→ INVALID_ARGUMENT
→ no job created
```

无 request identity：

```text
每次 submit 都是新的 logical request
```

有 request identity：

```text
new id + valid intent
→ create one job

same id + same intent
→ return same job identity
→ no additional job

same id + different intent
→ IDEMPOTENCY_CONFLICT
→ no additional job
```

## Get

```text
known id → immutable/read-only public view
unknown id → NOT_FOUND
```

## Cancel

```text
QUEUED → cancelled
unknown → NOT_FOUND
RUNNING / terminal → FAILED_PRECONDITION
```

并且 failure metadata 至少能告诉 caller 当前 status。

---

# 56. 为什么“不规定唯一实现”

你可以选择：

```text
exceptions
Result objects
frozen DTOs
protocol-specific response objects
```

request registry 也可以：

```text
独立 module
store abstraction
service-owned subcomponent
```

评分不看你用了什么 pattern 名称。

看的是：

```text
contract 是否完整
ownership 是否清楚
invalid state 是否局部化
retry semantics 是否真实
internal implementation 是否被隔离
测试是否证明 contract
```

---

# 57. Design it twice：两种合理 API 方案

## Design A — Exception-oriented Python boundary

```python
view = api.get_job(id)
```

失败：

```python
raise ApiError(code=..., reason=..., metadata=...)
```

优点：

- Python 调用自然；
- success path 简洁；
- 可以集中 translation。

缺点：

- caller control flow 隐式；
- type signature 不直接显示 failure；
- later RPC serialization 仍需映射。

## Design B — Explicit Result

```python
result = api.get_job(id)
```

```text
Ok(JobView)
Err(ApiError)
```

优点：

- failure 显式；
- 容易映射到 wire protocol；
- tests 直接。

缺点：

- Python 代码更 verbose；
- 如果自己发明 Result framework，可能增加 incidental complexity。

两者都可以是好设计。

课程要你解释 trade-off，不要求选某个流派。

---

# 58. Design it twice：两种 request registry 方案

## A. Map request_id → (intent, job_id)

简单：

```python
requests[request_id] = (command, job_id)
```

适合当前 in-memory TaskForge。

局限：

- restart 丢失；
- 没 retention；
- concurrency 未处理。

但这些是后续模块的教学点。

## B. 把 request identity 作为 Job metadata

例如：

```text
job.request_id
```

然后按 request_id 查询。

优点：

- fewer stores。

缺点：

- request history 与 job lifecycle 被耦合；
- late retry after deletion 语义困难；
- request_id 的 retention 与 job retention 被绑死。

这个 trade-off 很值得讨论。

---

# 59. “一个 store 少一点”不一定更简单

如果：

```text
request identity lifetime
```

和：

```text
job lifetime
```

不同，那么硬塞一张表可能让 abstraction 更糟。

这和 M02 的 lifetime namespace 思维一致：

> **不同 semantic fact / lifetime 可以合理拥有不同 state owner。**

不要把“single source of truth”机械理解成“所有东西一张 dict”。

---

# 60. 先写 behavior table，再写代码

M04 lab 要求先提交这样的表：

| operation | input/state | result | side effect | retry |
|---|---|---|---|---|
| submit | blank | INVALID_ARGUMENT | none | no point |
| submit | no request id | new job | one job | unsafe after unknown outcome |
| submit | new request id | new job | one job + request record | safe |
| submit | same id/same intent | same job | none additional | safe |
| submit | same id/different intent | CONFLICT | none | no |
| get | unknown | NOT_FOUND | none | usually no |
| cancel | queued | success | status→cancelled | repeat semantics must be defined |
| cancel | running | FAILED_PRECONDITION | none | no |

这个表比 200 行实现更重要。

---

# 61. Cancel 自己是否应该 idempotent？

这里没有唯一答案。

方案 A：

```text
cancel(CANCELLED)
→ success
```

定义目标状态：

```text
ensure job is cancelled
```

那么重复 cancel 更 idempotent。

但对：

```text
SUCCEEDED
FAILED
```

不能声称 cancelled。

方案 B：

```text
only QUEUED→CANCELLED counts as success
otherwise FAILED_PRECONDITION
```

语义更严格。

本 lab 默认采用 B，以便保留 lifecycle distinction。

但你应该能为 A 做合理 argument。

这就是：

> define errors out of existence 必须结合 product semantics，而不是无条件使用。

---

# 62. “Already done” 返回 success 还是 error？

这个问题在很多 API 都存在：

```text
delete already deleted
cancel already cancelled
create already created
```

判断方式不是：“REST 通常怎么做？”

而是：

```text
operation 的 semantic postcondition 是什么？
caller 需要区分 first application 与 replay 吗？
```

如果 postcondition 只是：

```text
resource absent
```

already absent 可以成功。

如果 operation 意味着：

```text
perform a new distinct deletion event
```

就可能不同。

先定义 semantics，再选 status code。

---

# 63. Good API 会减少 caller branching

差 API：

```python
try:
    ok = cancel(id)
except KeyError:
    ...
if ok is False:
    job = get(id)
    if job.status == ...:
        ...
```

caller 被迫补全 service 没表达的语义。

更好的 boundary：

```text
cancel(id)
→ Success
→ NOT_FOUND
→ FAILED_PRECONDITION(status=...)
```

caller 不需要二次 query 才理解 failure。

这就是 information hiding 的一个具体形式。

---

# 64. 但不要替 caller 做它才知道的 policy

例如 `FAILED_PRECONDITION(status=RUNNING)` 后：

- UI 可能显示“已开始，无法取消”；
- scheduler 可能等待；
- admin tool 可能 escalate kill；

service boundary 不应该擅自决定：

```text
running 就 kill worker
```

因为这是 higher-level policy。

边界应该吸收 mechanism complexity，**不是偷走 caller 的业务决策权**。

---

# 65. Boundary 的设计张力

好 boundary 要在两端之间找平衡：

```text
过薄
→ implementation leakage
→ caller complexity

过厚
→ policy capture
→ hidden magic
→ hard-to-predict behavior
```

目标是：

> **隐藏 caller 不应该知道的 mechanism，同时保留 caller 必须决定的 policy。**

这是 M04 最重要的 design judgment 之一。

---

# 66. API review checklist

看到一个新 API / boundary，先不要看命名风格。

问：

## Input

- raw input 在哪里 parse？
- normalization 是否明确？
- invalid input 是否在 side effect 前拒绝？
- validated information 是否保存在 representation 中？

## Success

- success 到底承诺哪个 state/effect？
- 返回值是否泄漏 mutable internal representation？
- response 是否包含 caller 真正需要的信息？

## Error

- 每个 public error 的 caller action 是什么？
- 是否泄漏 implementation exception？
- machine identity 是否稳定？
- message 与 code 是否分离？
- metadata 是否过多/过少？

## Retry

- operation 的 intended effect 是什么？
- timeout 后 outcome 是否可能 unknown？
- 能否自动 retry？
- request identity 如何定义？
- duplicate / conflict 语义是什么？

## Ownership

- 谁拥有 validation invariant？
- 谁拥有 job lifecycle？
- 谁拥有 request dedup state？
- 是否出现 duplicated authority？

## Evolution

- internal storage 换实现时 public contract 是否可保持？
- error reason/metadata 是否形成 compatibility surface？
- 新状态加入后 error taxonomy 会不会爆炸？

---

# 67. 从 M01 到 M04 的连接

M01：

```text
什么是 contract？
```

M02：

```text
谁拥有 state / invariant？
```

M03：

```text
什么 evidence 能区分正确与错误实现？
```

M04：

```text
这些 contract 应该怎样穿过 boundary，
让 caller 看到最小但足够的 semantic surface？
```

四章不是独立知识点。

它们组合成：

```text
spec
 ↓
ownership
 ↓
boundary
 ↓
executable evidence
```

---

# 68. 从 M04 到后续课程

M05 Refactoring：

```text
如何在保持 public contract 下改变 boundary internals？
```

M07 Concurrency/Failure：

```text
unknown outcome、race、cancellation 下 contract 是否成立？
```

M08 Compatibility：

```text
error code / metadata / idempotency semantics 怎样演化？
```

M09 Architecture：

```text
当 boundary 变成 process/network boundary 后，哪些 contract 必须更明确？
```

M11 Production：

```text
retry / overload / diagnostics 在现实中怎样表现？
```

所以 M04 是从“单进程 software design”走向“系统工程”的桥。

---

# 69. 本章小练习 A：Error taxonomy critique

给出：

```text
JobNotFound
JobQueuedError
JobRunningError
JobSucceededError
JobFailedError
JobCancelledError
StorageMissingError
StorageBusyError
StoragePermissionError
```

任务：

1. 假设 public caller 只有 submit/get/cancel。
2. 为每个 error 写 caller action。
3. 找出可以 collapse 的 case。
4. 找出不能 collapse 的 case。
5. 设计 machine-readable reason + metadata。
6. 说明哪些 internal error 不应成为 public error。

禁止以“exception class 越具体越好”作为理由。

---

# 70. 本章小练习 B：Temporal coupling

API：

```python
s = Session()
s.set_workspace(path)
s.load_config()
s.connect()
s.authenticate(token)
s.start()
s.run(command)
```

请回答：

- hidden state machine 是什么？
- 哪些 transition 可以自动做？
- 哪些必须由 caller 控制？
- 能否用 factory / staged type / capability object 降低非法调用？
- 新设计是否真的减少 caller knowledge，还是只是 class 数量增加？

---

# 71. 本章小练习 C：Idempotency

API：

```python
create_vm(cpu=4, memory=16)
```

client timeout。

有人提议：

```python
key = sha256(json.dumps(request))
```

作为 dedup key。

请解释为什么这并不能区分：

```text
retry same intent
```

和：

```text
create another identical VM
```

然后设计 caller-provided request identity contract。

---

# 72. 本章小练习 D：No-effect guarantee

给出 operation：

```text
create account
```

可能错误：

```text
INVALID_ARGUMENT
PERMISSION_DENIED
CONFLICT
UNAVAILABLE
DEADLINE_EXCEEDED
INTERNAL
```

请为每个 error 填：

```text
can guarantee no side effect?
yes / no / depends
```

并写出理由。

目标是意识到：

> “API 返回 error”与“operation 没发生”不是同义词。

---

# 73. 本章结束后的能力标准

完成 M04 后，你应该能够面对一个 API 变更问出：

```text
这到底是 boundary 还是 wrapper？
它隐藏了什么 knowledge？
raw input 在哪一层变成 domain value？
哪些 illegal states 被 representation 消掉？
每个 public error 对 caller 有什么行动意义？
哪些 internal failure 被正确翻译？
timeout 后 outcome 是否确定？
retry 是否安全？
logical request identity 是什么？
dedup state 谁拥有？
错误 schema 自己是否形成 compatibility contract？
```

如果这些问题答不出来：

```text
“API 看起来很干净”
```

没有太大意义。

---

# 74. 本章最重要的十句话

1. **API 是责任、知识和不确定性的边界，不只是函数签名。**
2. **好的 boundary 应吸收 mechanism complexity，而不是把它重命名后转发给 caller。**
3. **已经验证出的事实应尽量保存在更精确的 representation 中。**
4. **error taxonomy 应围绕 caller action，而不是 implementation exception taxonomy。**
5. **human message 与 machine-readable error identity 应分开。**
6. **failure 不一定意味着 no effect；timeout 尤其可能意味着 outcome unknown。**
7. **retry safety 是 operation semantics，不是 catch-all loop。**
8. **same payload 不等于 same intent；request identity 应明确进入 contract。**
9. **idempotency 保护 logical effect，不要求所有内部 side effect 或 response bytes 完全相同。**
10. **Agent 写 API 前，先让它写 behavior table、error semantics、retry contract 和 ownership map。**

---

# 75. 可选原始材料

本章完全自包含。以下材料用于交叉检查和进一步阅读：

- Stanford CS190 Error Handling: https://web.stanford.edu/~ouster/cgi-bin/cs190-spring15/lecture.php?topic=errorHandling
- Stanford APOSD discussion: https://web.stanford.edu/~ouster/cs190-winter23/lectures/aposd/
- Google AIP-193 Errors: https://google.aip.dev/193
- Google AIP-194 Automatic retry configuration: https://google.aip.dev/194
- Google AIP-155 Request identification: https://google.aip.dev/155
- AWS Builders' Library — Making retries safe with idempotent APIs: https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/
- RFC 9110 §9.2.2 Idempotent Methods: https://www.rfc-editor.org/rfc/rfc9110.html#name-idempotent-methods
- Alexis King — Parse, don't validate: https://lexi-lambda.github.io/blog/2019/11/05/parse-don-t-validate/
- gRPC Error Handling: https://grpc.io/docs/guides/error/
- gRPC Status Codes: https://grpc.io/docs/guides/status-codes/

详细审计见：

`reading-notes/m04-source-audit.md`
