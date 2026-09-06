# M04 — API、Error 与 Boundary Design：让边界吸收复杂度

M03 里我们把测试看成关于 contract 的可执行证据。到了这一章，问题向外移动了一层：一个系统即使内部状态和测试都还算清楚，只要 boundary 把内部细节、失败机制和不确定性原样交给 caller，复杂度仍然会迅速扩散。

这一章不是 REST API 教程，也不试图总结“异常处理最佳实践”。我们会一直跟着 TaskForge 的一个很小的 public boundary，看它怎样随着真实约束加入而变得不再“小”。目标是学会判断：哪些复杂度应该被 boundary 吸收，哪些 distinction 必须留给 caller，哪些承诺在 timeout、retry、并发和实现替换以后仍然说得通。

## 1. 一个四行接口，究竟承诺了什么

先看 TaskForge 现在最自然的一组操作：

```python
submit(command: str) -> str
get(job_id: str) -> Job
list_jobs() -> list[Job]
cancel(job_id: str) -> bool
```

如果只看函数名和类型，这个 API 很容易让人产生“已经很简单”的感觉。可一旦站到 caller 一侧，问题马上出现。

`submit("")` 合法吗？全是空格呢？成功返回 job id 时，job 已经 durable，还是只写进了一个内存字典？`get("missing")` 是返回 `None`、抛 `KeyError`，还是某种稳定的 `NOT_FOUND`？最麻烦的是 `cancel`：`False` 到底表示 job 已经 running、已经 succeeded、已经 cancelled，还是根本不存在？这些情况如果需要不同的下一步，caller 就不能只拿到一个布尔值。

再把实现变化和分布式条件加入进来。今天 `get` 的内部实现可能直接索引字典，因此未知 id 会冒出 `KeyError`；明天换成 SQLite，失败形态就会改变。如果 client 发出 `submit` 后超时，它也不知道“请求失败了”，只能知道“没有收到确认”。server 也许根本没执行，也许已经创建了 job，只是 response 丢在路上。此时重发同一条 command 会不会创建第二个 job？而两条文本完全相同的 command，又怎么区分“第一次请求的 retry”和“用户本来就想启动两个相同任务”？

这些问题都没有出现在四行 signature 里，但它们都是 API 的一部分。一个 public operation 实际上还在分配 input domain、side effect、state transition、error semantics、retry semantics、compatibility promise，以及失败时谁承担 uncertainty。

这也是为什么 boundary 不能只理解成“多包一层函数”。假设我们写：

```python
def get_job(job_id: str):
    return service.get(job_id)
```

它当然增加了一个调用层，但 caller 仍然需要知道 `service.get` 的 exception、内部 `Job` representation、mutable state 和 lifecycle enum。storage 一换，caller 也跟着变。这种 wrapper 是 shallow 的：interface count 增加了，caller 要理解的知识却几乎没减少。

有价值的 boundary 会做 semantic compression。它允许内部有很多 mechanism-level cases，但对外只暴露稳定、可行动、可以长期承诺的语义。例如内部可能出现 `KeyError`、SQLite constraint failure、worker disconnect 或 socket error；caller 不一定需要知道它们来自哪一层，而需要知道的是“请求无效”“资源不存在”“当前状态不允许这项操作”“系统暂时不可用”，以及每种情况自己下一步能做什么。

这和 M02 的 deep module 是同一个方向：接口的价值不在于看起来短，而在于它隐藏了多少 caller 不应该继承的知识。

### 1.1 Boundary 不是越厚越好

这里先加一个限制。把 mechanism complexity 拉进 boundary，并不意味着 service 应替 caller 做所有决定。

例如 `cancel(job_id)` 得知 job 已经 running。UI 可能只需要显示“已开始，无法取消”；scheduler 可能选择等待；admin tool 可能有额外权限去终止 worker。boundary 可以稳定地报告 `FAILED_PRECONDITION`，并带上 `status=running`，但它不应该擅自把“running”解释成“杀掉 worker”。后者是 caller 才拥有的 policy。

因此这章讨论的不是“server 永远更复杂”这一类规则，而是一个更具体的问题：**把复杂度放到拥有足够信息、可以统一维护 invariant 的最低一层，同时不要偷走只有上层才知道的业务决策。**

一个好 boundary 的两端都可能失败。太薄，implementation leakage 和 recovery burden 会扩散给每个 caller；太厚，又可能把 policy 藏进 magic behavior，导致 caller 无法预测系统到底替它做了什么。

## 2. 先把 raw input 变成 core 可以相信的东西

回到 `submit(command: str)`。假设 TaskForge 的 command 至少要包含一个非空白字符。最直接的做法是在入口检查：

```python
def validate_command(command: str) -> None:
    if not command.strip():
        raise ValueError("empty command")
```

然后：

```python
validate_command(command)
run(command)
```

这比完全不检查好，但有一个容易忽略的问题：`run` 收到的仍然只是 `str`。从 representation 上看，它无法知道这个字符串是 raw input，还是已经通过 boundary 验证的 command。以后另一个 caller 直接调用 `run(raw)`，同一个 proof obligation 又回来了。检查确实发生过，但检查获得的信息没有留下来。

一种更强的设计，是让 boundary 产生更精确的 domain value：

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class Command:
    value: str

    @classmethod
    def parse(cls, raw: str) -> "Command":
        if not raw.strip():
            raise InvalidCommand(...)
        return cls(raw)
```

core 则接受：

```python
def run(command: Command):
    ...
```

现在 `Command` 不只是给 `str` 换了一个名字。如果所有 `Command` 都只能通过维护 invariant 的 constructor/factory 建立，那么 `run` 可以把“至少含一个非空白字符”当作已经完成的 boundary work，而不是每层重新检查。

这就是 “parse, don't validate” 在这里值得采用的部分：已经证明的事实，尽可能由 representation 承载，让下游不需要靠记忆继续相信“某处应该检查过”。

### 2.1 但不要把所有 invariant 都塞进 type

这个思路非常容易被机械化。比如 job lifecycle 确实可以设计成不同 variant：

```python
QueuedJob(...)
RunningJob(...)
SucceededJob(exit_code=0)
FailedJob(exit_code=int)
CancelledJob(...)
```

这样可以让 `QUEUED + exit_code=0` 之类组合更难出现。在支持 algebraic data type 的语言里，这种设计有时非常漂亮；在 Python 里也可以用受控 constructor、dataclass 和 encapsulation 获得一部分收益。

但有些 invariant 根本不属于单个本地 value。例如“一个 `request_id` 在某个 retention interval 内只能绑定一个 logical intent”依赖 durable state、时间以及其他请求。你不能靠定义一个 `RequestId` class 就证明全局唯一性；它还需要 store、transaction/constraint、ownership 和 runtime checks。

更一般地说，type、constructor、transaction、state machine、lock、unique constraint、idempotency record 和 test 都可以承担 invariant。应选哪个，取决于这个事实由谁拥有、需要观察哪些外部状态、违反时在哪里最容易被发现。

### 2.2 Validation 的顺序也是 contract

如果 boundary 真要承诺 invalid input 没有 side effect，那么 validation 不能发生在 mutation 后面。下面这段代码的 bug 不只是“顺序不优雅”：

```python
def submit(command, request_id):
    allocate_id()
    write_job()
    validate_request_id(request_id)
```

如果最后一步发现 `request_id` 非法，API 可能返回 `INVALID_ARGUMENT`，但 job 已经创建。caller 很容易把 validation error 理解成“请求在任何 effect 前被拒绝”，而实现并没有做到。

所以对很多 boundary，一个健康的 baseline 是先 parse/validate，再检查 authorization 和 precondition，最后才 commit side effect。当然到了 distributed workflow，mutation 可能跨多个组件，不能总得到这么干净的原子边界；M07 会继续处理 crash window 和 recovery。但在 M04 这里，至少要把“这个 error 是否保证 no effect”变成显式 contract，而不是靠 error 这个词暗示。

## 3. `cancel=False` 为什么不是一个小问题

现在把注意力转到 `cancel(job_id) -> bool`。假设 TaskForge 的 lifecycle 是：

```text
QUEUED --claim--> RUNNING --finish--> SUCCEEDED / FAILED
   |
 cancel
   v
CANCELLED
```

如果只允许 `QUEUED -> CANCELLED`，那么 caller 至少面对这些输入状态：unknown、QUEUED、RUNNING、SUCCEEDED、FAILED、CANCELLED。只有一个 `False` 时，很多不同 semantic case 被挤在一起。

这会直接把工作推回 caller：

```python
try:
    ok = cancel(job_id)
except KeyError:
    ...

if ok is False:
    job = get(job_id)
    if job.status == ...:
        ...
```

caller 先调用一次 `cancel`，然后为了理解失败又读一次状态。与此同时，两次调用之间 state 还可能变化。这个 branching 不是 caller 的业务需求，而是在替 service 补充一个没有表达完整的 contract。

更稳定的 public semantics 可以是：QUEUED 时成功；unknown 时 `NOT_FOUND`；RUNNING 或 terminal state 时 `FAILED_PRECONDITION`，同时提供 machine-readable reason `JOB_NOT_CANCELLABLE` 和当前 status。这里不要求一定采用 gRPC status code，也不要求一定用 exception；重要的是 caller 能稳定地区分下一步不同的情况。

### 3.1 Error taxonomy 应从 caller action 往回设计

内部 failure taxonomy 往往比 public taxonomy 大得多。storage、worker、network 和 domain code 可能分别抛出 `FileNotFoundError`、`PermissionError`、`sqlite3.OperationalError`、`WorkerDisconnected`、`TimeoutError`、`KeyError` 等。如果 boundary 全部透传，caller 就被迫学习 implementation taxonomy。

一种更可靠的设计方法，是先问 caller 有哪些不同动作。某些输入需要修正；某些资源不存在以后不应继续 retry；某些临时不可用允许稍后重试；某些 conflict 需要 re-read state 后再决定。如果两个低层 failure 对 caller 的允许动作、side-effect guarantee 和 compatibility promise 都相同，那么让它们成为两个 public cases 往往没有价值。相反，如果两个情况需要完全不同的 recovery，压成一个通用 `ERROR` 就丢掉了必要信息。

一种常见的假完整，是把每个 lifecycle branch 都变成一个 exception class：`JobAlreadyRunningError`、`JobAlreadySucceededError`、`JobAlreadyFailedError`……这只是把 state-space 映射成 class-space。error type 的数量本身不是设计质量指标；要检查的是这些 distinctions 是否改变 caller 的决定，以及内部 representation 改变后 public contract 能否保持。

这就是 Stanford error-handling material 中 “before throwing an error, think how the caller will handle it” 在本课程里的用法。它不是要求 error 越少越好，而是要求 surfaced distinction 有 semantic reason。

对于 TaskForge，我们可以让公共层看到类似这样的信息：

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

`message` 面向人，可以改措辞、增加 context、做 localization；`code`、`reason` 和约定好的 metadata key 才是 machine contract。让 client 通过 `if "running" in str(exc)` 之类字符串解析来决定控制流，相当于把 UX 文案强行变成 protocol identity。

这里还有第二个 qualifier：metadata 一旦公开，也会成为 compatibility surface。不要把所有 internal context 都塞给 caller。对外 metadata 应当是 caller 真有用、稳定可承诺并且不会泄漏 secret、filesystem path、stack trace 或内部 topology 的最小集合。丰富诊断和 public disclosure 是两个不同目标。

public boundary 同时也是 security boundary。authorization 应在承诺无副作用的 mutation 之前完成；某些过细的 `NOT_FOUND` / `PERMISSION_DENIED` distinction 甚至可能泄漏 resource 是否存在。这里不展开完整 security engineering，但 error schema 和 diagnostic metadata 都必须按外部 disclosure surface 来审查，而不是把“内部调试越丰富越好”直接外推成 public API 原则。

### 3.2 Translation 需要 domain context

假设 storage 从 dict 换成 SQLite，某次操作抛出 `sqlite3.IntegrityError`。如果 boundary 只做 exception forwarding，caller 就和 SQLite 绑定了；以后换 PostgreSQL，甚至只是 schema constraint 改名，都可能成为 API break。

可问题也不能通过：

```python
except Exception:
    raise ApiError("INTERNAL")
```

来解决。一个 integrity error 可能表示 duplicate request identity，也可能表示真正的 schema bug。前者也许应该成为 `IDEMPOTENCY_CONFLICT`，后者则可能是 internal failure。只有拥有 domain context 的那一层才知道如何分类。

因此 error handling 和 state ownership 是连在一起的。低层 socket 可以知道连接断了，却不知道 job 是否允许 retry；storage 可以知道 unique constraint 失败，却不知道这个 constraint 在 domain 里代表 duplicate intent 还是 corrupted state。负责把 mechanism failure 翻译成 public semantics 的 boundary 必须拥有足够信息，但它不必自己拥有所有恢复 policy。

### 3.3 Error 不等于 exception

到这里可以再给“error”一个更精确的定义：它是 operation 没有按 normal success contract 完成时，boundary 暴露给 caller 的语义信息。exception、`Result/Either`、status code、error object、sentinel 或 stream terminal status 都只是 encoding。

因此成熟的 error handling 不只有“throw”一种动作。某些 case 可以通过重新定义 postcondition 消失，例如 delete 的 contract 若只是“调用后 resource absent”，那么原本就不存在可以算成功；某些低层 failure 可以在 boundary 内部 mask/recover；多个 mechanism failure 可以在 caller action 相同时 collapse；而 permission denial、invalid input、conflict、ambiguous outcome 等信息又可能必须 surface。

“define errors out of existence” 是一个 design heuristic，不是定律。是否把 already-done 当成功，取决于 operation 的 postcondition 和 caller 是否需要区分 first application 与 replay，而不是取决于某个流派偏好。

## 4. API 同时也是 state-machine surface

`cancel` 的问题提醒我们：很多 public method 本质上不是“对一个对象做动作”，而是在请求 state transition。既然 TaskForge 的 `cancel` 只允许 `QUEUED -> CANCELLED`，它的 error semantics 就应该从 lifecycle model 推导，而不是实现时临时写几条 `if`。

这也解释了为什么 state-specific API 有时值得考虑。比起：

```python
finish(job_id, exit_code)
```

一个 worker protocol 也许可以先拿到 lease：

```python
lease = claim_next(worker_id)
finish(lease, exit_code)
```

`lease` 至少表达了“这个 worker 曾成功获得该 attempt 的 authority”，比任意 caller 拿一个字符串 id 就能 `finish` 更强。类似地，有些系统会用 `QueuedJobRef`、`ConnectedClient` 或 capability object 表达允许的 operation。

但 representation 不能让时间停止。client 刚刚读取 `status=QUEUED`，下一毫秒 worker 就可能 claim 成 RUNNING。即使 client 手里有一个叫 `QueuedJobRef` 的对象，也不一定能证明 server 此刻仍 queued。对远端 mutable state，read result 只是 observation；如果 operation 需要“只有版本仍为 X 才执行”，就需要 expected version、CAS、lease 或 transaction 之类原子机制。

这就是为什么“make illegal states unrepresentable”不能被宗教化。一个 local type 能证明什么，要看它的 freshness 和 authority boundary。

### 4.1 Temporal coupling 是隐藏的 state machine

另一个很常见的 boundary 问题不是错误码，而是 caller 被迫记住调用顺序：

```python
client = Client()
client.configure(...)
client.connect()
client.authenticate()
client.start()
client.submit(...)
```

这里已经存在一个 state machine，只是它没有被 API 直接表达。caller 必须知道 configure、connect、authenticate、start 的时序，任何一步顺序错了才得到 `InvalidStateError`。

有时可以用 factory 把一组稳定、无业务选择的 transition 吸收到 boundary 内部：

```python
client = connect(config, credential)
client.submit(...)
```

有时不同 phase 确实代表不同 authority，那么 staged type 或 capability object 更合适。关键问题始终是：这个顺序是 caller 需要控制的 policy，还是 implementation 让 caller 背下来的 mechanism？

### 4.2 “方便”参数也可能扩大 state space

一个万能接口看起来很 flexible：

```python
submit(
    command,
    retry=True,
    create_if_missing=True,
    wait=True,
    timeout=None,
    force=False,
    ignore_errors=False,
)
```

但这些 flags 的组合会形成越来越大的 semantic state space，其中一些互相矛盾，一些只有在特定 lifecycle 才有意义。好的 abstraction 往往宁可提供更明确的 operation 和少量 orthogonal options，而不是让 caller 自己拼 hidden protocol。

默认值也是 contract。`retry=True` 不是 UI convenience；它暗含哪些 failure 可 retry、retry budget、latency、idempotency 和 side-effect uncertainty。一个默认行为只有在大多数 caller 不理解隐藏危险也能安全接受时，才真的是“方便”。

## 5. Timeout 之后，caller 知道的比想象中少

现在把 `submit` 放到一个跨进程 boundary。client 发送 create job，server 收到并创建 `job-17`，但 response 在返回途中丢失。client 最终只看到 timeout。

```text
client          server
  |   submit      |
  | ------------> |
  |                | create job-17
  |    response    |
  | <--- X ------- |
  |
  | timeout
```

这里最重要的事实不是“发生了错误”，而是 **outcome unknown**。`INVALID_ARGUMENT` 如果能在任何 mutation 前被检测，caller 可以知道 job 没创建；network timeout 通常只能说明 caller 没拿到完成确认，不能推出 server 没执行。

这一区分会改变 recovery。若 caller 把所有 error 都理解为 no effect，就可能在 timeout 后重发一个 effectful request，从而创建重复 job。

### 5.1 Partial side effect 让 public semantics 更难

即使没有网络，单次 server operation 也可能包含多步 effect。例如：

```text
1. allocate job id
2. persist job
3. publish to queue
```

如果第 3 步失败，API 返回 `UNAVAILABLE` 时，job 到底存在吗？queue 有没有后续 reconciliation？caller 重试是新建、继续旧 operation，还是触发 duplicate？这些是 M07 会继续处理的 atomicity/recovery 问题，但 M04 必须先要求 public contract 对 outcome 诚实。

“no side effect on error” 是很强的保证。对 validation、authorization 或某些 precondition failure，如果实现能确定它们都发生在 mutation 前，可以明确写 no effect；对 `DEADLINE_EXCEEDED`、`UNAVAILABLE` 或跨多个 component 的失败，则可能只能承诺 outcome unknown。不要因为返回值放在 error channel 里，就让读者和 caller 自动脑补“什么都没发生”。

### 5.2 Retryability 不是 error code 的单变量函数

常见的坏实现是：

```python
except Exception:
    retry()
```

能否 retry 至少同时取决于 operation semantics、failure category，以及当前 layer 是否拥有足够的 workflow information。`INVALID_ARGUMENT` 重发通常没有意义；`UNAVAILABLE` 对一个 idempotent operation 可能可以 retry；`CONFLICT` 往往需要先 re-read state，再做 higher-level decision，而不是 blind retry 同一写操作。

retry 发生在哪一层也同样重要。假设一个 workflow 是 reserve quota、create job、record billing，底层 SDK 如果只看到 `create job` 失败就无限重试，它可能破坏上层 transaction 的语义。一个有用的经验是：让 retry 发生在**拥有足够 transaction semantics 的最低层**。这不是“越底层越自动越好”。

exponential backoff、jitter、retry budget 和 retry storm 很重要，但不是本章重点。如果 operation 本身不支持安全重复，再漂亮的 backoff 也只是更慢地重复 side effect。

## 6. Idempotency 从“同一个 logical request”开始

回到刚才的 timeout。我们希望 caller 可以重发 `submit`，但又不创建 `job-18`。此时“幂等”必须成为 API semantics，而不能只靠一个 HTTP method 标签代替分析。

一个实用的定义是：**对同一个 logical request 重复发送，不产生额外的 intended effect。** 这里的三个限定都重要：same logical request、intended effect、extra。

它并不要求所有内部 side effect 都只发生一次。每次 attempt 仍可以写 log、增加 metric 或产生 trace。它也不要求 response bytes 一样。第一次 `submit` 返回时 job 也许还是 queued；retry 到达时同一个 job 已经 running。只要 caller 仍然得到同一个 logical creation result，并且没有第二个 job 被创建，幂等 contract 仍然可能成立。

### 6.1 Payload equality 不能替 caller 猜 intent

假设两次请求都是：

```python
submit("python train.py")
submit("python train.py")
```

它们可能是第一次 response timeout 后的 retry，也可能是用户真想启动两个相同训练任务。server 仅凭 payload bytes 无法区分这两种 intent。

因此把：

```python
sha256(command)
```

当通用 idempotency key 会把第二种合法需求错误 dedup。AWS 的 retries case study 特别强调了这一点：semantic request identity 最可靠的来源通常是 caller 明确告诉 service“这些 transmissions 属于同一个 logical request”。

TaskForge 可以引入 caller-provided `request_id`，并把 contract 写清楚：对同一个 caller，重复使用同一个 `request_id` 表示同一个 logical request。

server 记录 `request_id`、原始 intent 和 result identity。第一次 `req-abc + "python train.py"` 创建 `job-17`；后来同一 id、同一 intent 的 retry 返回同一个 job identity，而不再创建 job。

### 6.2 Same id + different intent 必须有定义

假设第一次请求使用 `request_id=req-abc`、command 为 `"echo first"`，随后 caller 又复用 `req-abc`，却把 command 改成 `"rm -rf /tmp/x"`。

service 既不能静默执行新的 intent，也不能假装它与旧请求相同并返回旧结果。更合理的 contract 是把 request identity 已被另一 intent 占用当成稳定 conflict，例如 `IDEMPOTENCY_CONFLICT`，并且不创建新的 job。

这里需要维护的 invariant 是 one request identity -> one intent。它需要一个明确的 state owner。

### 6.3 Request registry 不一定是 duplicated authority

M02 之后，看到新的 `request_id -> ...` store 应该本能地问：是不是又造了一份 source of truth？答案取决于它 authoritative 地回答什么。

Job store 回答 `job-17` 当前 lifecycle state；request registry 回答 `req-abc` 代表哪个 logical create request，以及它解析到哪个 result identity。这是两个不同 semantic facts。它们当然需要保持一致，但并不因为有两张表就自动构成 duplicated authority。

反过来，如果 request registry 开始自己复制维护 job 的 current status，就更值得警惕。这里的原则是 semantic fact 和 lifetime，而不是“全系统只能有一张 dict”。request identity 的 retention 也可能比 job lifetime 长；如果把 request id 仅作为 Job metadata，删除 job 时是否还能识别 late retry 就会变成新的 coupling。

### 6.4 “Exactly once” 必须追问 exactly once 什么

一句 “exactly-once execution” 很容易把多个不同 guarantee 混在一起：request accepted once、job row created once、worker 执行 command once、external side effect once、client 观察 success once。这些不是同一件事。

TaskForge 的 idempotent submit 最多可以明确承诺：在 request-id retention interval 内，同一 request id 和同一 command 解析到同一个 job id，不创建额外 job。它并不能由此推出 worker command 永远只执行一次；后者需要 attempt fencing、lease、recovery 等 M07 范围的机制。

因此 API 文档不要只写 “This API is idempotent.” 更可测试的表述应该写出具体 effect，例如：

> 当提供 `request_id` 时，在 request-id retention interval 内，使用同一 `request_id` 和同一 command 重复提交会解析到同一个 `job_id`，并且不会创建额外 job。

一旦 guarantee 写到这个粒度，测试和 review 才有共同对象。

### 6.5 迁移到另一个场景：`create_vm`

把 TaskForge 换成：

```python
create_vm(cpu=4, memory=16)
```

client timeout 后，参数 hash 仍然无法告诉 server 第二次调用是在 retry 原来的 VM，还是创建另一台配置相同的 VM。这个例子说明 request identity 不是 TaskForge 特例，也不是 command string 的偶然问题；只要 operation 有 side effect、delivery/outcome 存在不确定性，而且 retry 有实际价值，就需要认真区分 transmission equality 和 logical intent identity。

相反，纯函数、无 side-effect query、本地 atomic call，或者 caller 可以直接确认 outcome 的操作，通常不值得为了“看起来专业”引入 request-id store。

## 7. Public boundary 应隐藏 mechanism，但保留诊断能力

到这里我们已经把 validation、error semantics、retry 和 idempotency 都拉进同一条 TaskForge story。还有一个容易产生误解的地方：对外做 semantic compression 不等于把内部信息丢掉。

假设 caller 只需要看到 public category `UNAVAILABLE` 和稳定 reason `WORKER_UNAVAILABLE`。

内部仍然可以记录 worker id、socket errno、last heartbeat、attempt id、trace id 和 stack。public error code 服务的是 caller recovery；root-cause taxonomy 和 operator diagnosis 是另一组 concern。强迫一个 public code 同时承担 caller action、根因分类和 incident debugging，通常会得到一个既不稳定又难用的 error surface。

request identity 也能帮助 observability。若 `request_id` 是 contract 的一部分，log、trace 和 audit 可以围绕 logical request 关联多个 network attempts；否则 production debugging 常常只能根据 timestamp 猜“这两个 attempt 到底是不是同一件事”。M11 会继续讨论 telemetry，但 identity 设计从 API 层就已经开始影响可观察性。

### 7.1 Internal vocabulary 与 external vocabulary 可以不同

内部函数保留 `StorageBusy`、`WorkerDisconnected`、`LeaseExpired` 等更细的 failure distinctions 可能对 recovery、metrics 和 diagnosis 很有用；跨 public boundary 后，它们可以根据 caller semantics collapse 成较少的 category。boundary translation 正是两套 vocabulary 的 separation point。

这种 separation 也给内部实现留下 evolution freedom。public test 如果要求 unknown job -> `NOT_FOUND`，它就不应该同时要求底层一定抛 `KeyError`。storage 从 dict 换 DB 时，internal exception 可以完全变化，只要 public contract 不变。

### 7.2 Convenience API 可以存在，但不能伪造 guarantee

TaskForge 完全可以保留一个简单的：

```python
submit(command)
```

并把每次调用视为新的 logical request。问题只在于文档必须诚实：如果 caller 在 outcome unknown 后自行 retry，可能创建 duplicate job。

另一个显式 API 可以要求 request identity，并给出更强的 dedup guarantee。也可以设计成一个 function 加 optional `request_id`，但那就必须说清楚 `None` 到底代表“无 dedup guarantee”“server 生成 identity”还是其他 semantics。optional parameter 可能切换整个 reliability contract，不应因为语法上可省略就让语义也变模糊。

## 8. 把这些语义变成可执行证据

M04 的目标不是设计一张漂亮的 error taxonomy 图。boundary contract 如果不能被 test 和 review 独立检查，很容易退化成文档愿望。

一个很有效的起点，是先写 behavior table，再写实现：

| operation | input/state | result | side effect | retry |
|---|---|---|---|---|
| submit | blank | `INVALID_ARGUMENT` | none | no point |
| submit | no request id | new job | one job | unsafe after unknown outcome |
| submit | new request id | new job | one job + request record | safe under stated contract |
| submit | same id + same intent | same job identity | no additional job | safe |
| submit | same id + different intent | `IDEMPOTENCY_CONFLICT` | none additional | no |
| get | unknown id | `NOT_FOUND` | none | normally no need |
| cancel | QUEUED | success | status -> CANCELLED | repeat semantics must be defined |
| cancel | RUNNING / terminal | `FAILED_PRECONDITION` | none | no blind retry |

这个表逼我们同时写 success、negative semantics、side effect 和 retry，而不是只描述 happy path。

### 8.1 Tests 应按 semantic partition，而不是实现 branch

对 `cancel`，只测一个 success 和一个 failure 太粗。由 state machine 自然得到的 partitions 至少包括 unknown、QUEUED、RUNNING、SUCCEEDED、FAILED、CANCELLED。每个 partition 的 public result 和 side effect 都应该有答案。

对 request identity，则要区分 no id、new id、same id + same intent、same id + different intent，以及如果系统承诺 retention 后的 late retry，retention boundary 前后又分别怎样。

测试应该观察 public boundary，而不是绑定 internal exception。若 contract 是 unknown job -> `NOT_FOUND`，测试应检查 public error identity，而不是 `pytest.raises(KeyError)`。

还可以继续复用 M03 的 mutation thinking。故意把 `NOT_FOUND` 变成 `INTERNAL`，把 same-id retry 改成创建新 job，把 same-id/different-intent 改成静默返回旧 job，或者把 blank-command validation 移到 job 创建以后。如果测试仍然全绿，就说明这些 semantics 还没有成为 executable contract。

### 8.2 Design it twice：encoding 不是唯一答案

课程不会规定 public failure 必须用 Python exception。两种都合理的方案例如：

```python
view = api.get_job(job_id)
# failure: raise ApiError(code=..., reason=..., metadata=...)
```

另一种方案让结果显式出现在 value 中，例如 `Ok(JobView)` 或 `Err(ApiError)`。

exception-oriented boundary 的 success path 更自然，但 type signature 不直接显示 failure，未来跨 RPC 还要 serialization；显式 `Result` 更容易把 failure 当普通 data 检查，却可能在 Python 里增加 verbosity，甚至诱导团队自造一套没必要的 framework。

同样，request registry 可以是独立 module/store，也可以是 service-owned subcomponent。把 `request_id` 直接放进 Job metadata 会减少 store 数量，却可能把 request-history retention 与 job lifecycle retention 绑在一起。这里没有 pattern-name 标准答案。你需要说明 ownership、lifetime、compatibility 和 failure behavior 的 trade-off。

## 9. Agent 为什么特别容易把 API 做“完整”却没做对

coding agent 面对“给它加个 public API”这类任务，很容易产生表面上很专业的 patch：多一层 wrapper、每个 branch 一个 exception class、所有 error 都 catch 成 `INTERNAL`、给所有 network call 加 retry decorator、用 payload hash 当 idempotency key，再创建几个 dataclass 让类型看起来更丰富。

这些改动都有共同问题：它们先选择了 implementation shape，再补语义。

wrapper proliferation 没有减少 caller knowledge；exception-class explosion 把 lifecycle state-space mechanically 映射成 class-space；catch-all translation 销毁 caller 必须知道的 distinction；string parsing 把 human message 变成 protocol；retry-everything 忽略 operation semantics；parameter hash 无法表达 caller intent；validation after effect 破坏 no-effect assumption；所谓 type-safe wrapper 如果 public constructor 仍允许建立非法 value，也只是 type cosplay。

因此给 Agent 的 M04 task 不应是“把 API 做健壮一点”。更好的 task contract 会要求它先回答：public operations 是什么、raw input 在哪里 parse、每个 public error 对 caller 允许什么 action、哪些 failure 保证 no effect、哪些可能 unknown outcome、哪些 internal errors 不能穿过 boundary、哪些 operation 可以 retry、logical request identity 怎样定义、same-id/same-intent 与 same-id/different-intent 分别怎样处理，以及这些新增 state 由谁拥有。

把这些要求交付给 Agent 时，可以写成一个可 review 的 artifact，而不是藏在聊天上下文里：

```text
Before implementation, map the current public boundary and internal failure sources.

Desired contract:
- define accepted input domain and normalization rules;
- list public success outcomes and error categories;
- state the caller action for each public error;
- state whether each failure guarantees no side effect or may leave outcome unknown;
- identify internal errors that must not escape;
- define retryability per operation and the layer that owns retry policy;
- define logical request identity;
- define same-id/same-intent and same-id/different-intent behavior;
- identify the owner and lifetime of any new dedup state;
- state non-goals.

Before changing production code, provide a behavior table and tests that distinguish
the old behavior from the desired contract. After implementation, provide focused
and full-suite evidence plus a compatibility/hidden-coupling review.
```

然后才允许它给出 behavior table、state/ownership impact、会在旧实现上失败的 tests、implementation、focused/full-suite evidence 和独立 review。

这不是为了让 prompt 更长，而是为了把 engineering authority 从“Agent 看到代码以后自己猜”移回可以 review 的 artifact。

## 10. TaskForge M04：把 shallow boundary 升级成 explicit contract

对应实验见 [`../labs/04-api-error-boundary.md`](../labs/04-api-error-boundary.md)。实验初始 boundary 故意保留几类问题：raw `str` 直接进入 core、blank command 被接受、`KeyError` 可以穿过 public layer、`cancel=False` 模糊、没有 request identity，因而 timeout 后的 submit 无法安全 retry。

你需要把它升级成一个明确 contract。课程不要求唯一代码结构，但至少要满足下面的 semantics。

### 10.1 Submit

blank 或 whitespace-only command 应在创建 job 前得到 `INVALID_ARGUMENT`，并且没有 job 被创建。

没有 request identity 时，每次 `submit` 都是新的 logical request。这个 convenience path 不获得“unknown outcome 后安全 dedup”的保证。

提供 request identity 时：

- new id + valid intent：创建一个 job；
- same id + same intent：解析到同一个 job identity，不创建额外 job；
- same id + different intent：返回稳定的 idempotency conflict，不创建额外 job。

### 10.2 Get

known id 返回 immutable/read-only public view，而不是把 caller 直接接到 mutable internal representation；unknown id 返回 `NOT_FOUND`。

### 10.3 Cancel

本 lab 默认采用严格 semantics：只有 `QUEUED -> CANCELLED` 算 success；unknown 为 `NOT_FOUND`；RUNNING 或 terminal state 为 `FAILED_PRECONDITION`，并提供足够 metadata 让 caller 理解当前 status。

这里故意没有把“already cancelled”定义成 success。另一种 product contract 完全可以把 cancel 定义为“确保最终 cancelled”，从而让 repeated cancel 成功；但它必须解释 SUCCEEDED/FAILED 怎么处理，也必须说明 caller 是否需要区分首次 cancellation 与 replay。这个对比正好说明 define-errors-out-of-existence 需要结合 postcondition，而不是机械采用。

### 10.4 评分看什么

实现可以使用 exception、`Result`、frozen DTO、独立 request registry 或其他合适结构。评分重点不是 pattern 名，而是 contract 是否完整，state ownership 是否清楚，invalid input 和 invalid transition 是否局部化，retry semantics 是否真实，internal implementation 是否被 public boundary 隔离，以及 tests 是否真的证明这些性质。

## 11. Review 一个 boundary 时应该追问什么

学完这一章以后，面对一个新的 public API，不要先从命名或 class 数量开始。下面这些问题更接近它的 semantic surface。

### Input 与 state

- raw input 在哪里 parse / normalize？
- invalid input 是否在承诺 no effect 的 mutation 前被拒绝？
- 已经验证出的事实有没有保存在更精确的 representation 中？
- operation 实际请求的是哪个 state transition？
- read 到的 state 是 observation，还是某种带 freshness/fencing 的 capability？

### Success 与 error

- success 到底承诺哪个 observable state/effect？
- 返回值是否泄漏 mutable internal representation？
- 每个 public error 对 caller 有什么不同 action？
- 哪些 internal failures 应被 collapse/translate，哪些 distinction 必须保留？
- human message 与 machine identity 是否分离？
- metadata 是否稳定、必要且不泄密？
- 这个 error 保证 no effect，还是 outcome 可能 unknown？

### Retry 与 identity

- operation 的 intended effect 是什么？
- transport failure 后 caller 是否知道 effect 有没有发生？
- automatic retry 为什么安全？
- logical request identity 由谁声明？
- same id + same intent、same id + different intent、late retry 分别是什么 semantics？
- 文档所谓 idempotent / exactly once 到底约束哪个 effect？

### Ownership 与 evolution

- 谁拥有 validation invariant、job lifecycle、request identity 和 dedup state？
- 新的 store 是新的 semantic authority，还是复制了一份旧 authority？
- internal storage、exception 或 worker mechanism 替换后，public contract 能否保持？
- error reason、metadata、defaults 和 optional parameter 是否已经形成 compatibility surface？

这些问题不是 checklist 越长越好。它们的用途是让 reviewer 能从 caller、state owner 和 failure path 三个方向重建这个 boundary 的真实 contract。

## 12. 四个迁移练习

### 12.1 Error taxonomy critique

给你以下候选 public errors：

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

假设 public caller 只有 submit/get/cancel。为每个 error 写出 caller action，再判断哪些 mechanism distinctions 可以 collapse，哪些 lifecycle distinctions 必须保留。最后设计稳定的 machine-readable reason/metadata，并说明哪些 internal errors 根本不应成为 public error。不能用“exception class 越具体越好”作为理由。

### 12.2 Temporal coupling

考虑：

```python
s = Session()
s.set_workspace(path)
s.load_config()
s.connect()
s.authenticate(token)
s.start()
s.run(command)
```

画出 hidden state machine。哪些 transition 可以由 factory 吸收，哪些必须由 caller 控制？factory、staged type 或 capability object 能否减少非法调用？新设计如果只是 class 数量增加，却没有减少 caller knowledge，也不算改进。

### 12.3 Idempotency

考虑：

```python
create_vm(cpu=4, memory=16)
```

client timeout 后，有人提议：

```python
key = sha256(json.dumps(request))
```

作为 dedup key。解释为什么它不能区分 retry same intent 与 create another identical VM，然后给出 caller-provided request identity contract，包括 same-id/different-intent 的处理。

### 12.4 No-effect guarantee

对一个 `create account` operation，分别考虑 `INVALID_ARGUMENT`、`PERMISSION_DENIED`、`CONFLICT`、`UNAVAILABLE`、`DEADLINE_EXCEEDED`、`INTERNAL`。不要根据名字直接猜。对每一种错误，结合检测时机和可能的 mutation path，判断 API 能否保证 no side effect，还是只能说 depends / outcome unknown，并说明理由。

## 13. 把 M01–M04 连成一条 reasoning chain

M01 问的是 contract 是什么；M02 问谁拥有 state 和 invariant；M03 问什么 evidence 能区分满足 contract 与没有满足；M04 则把这些问题放到 boundary 上：如何让 caller 看到最小但足够的 semantic surface，同时允许内部 representation 和 mechanism 演化。

因此这四章不是独立的知识点列表。一个 public API 的 change specification 需要先写 observable behavior，再找到 authority/invariant，决定 boundary 里哪些知识应该被吸收，最后让 tests 对这些 semantics 形成可执行证据。

后面的课程会继续给这个 boundary 加压力。M05 会问内部重构如何不破坏 public contract；M07 会把 unknown outcome、race、cancel、crash/restart 和 recovery 拉进来；M08 会处理 error schema、request identity 和 compatibility 如何跨版本演化；M09 会把 boundary 推到 process/network 层；M11 再检查这些 retry 和 diagnostics 在 production 中到底产生了什么证据。

如果完成 M04 后只记住“应该用 structured error”和“retry 要幂等”，还不够。希望形成的判断是：面对一个看似很短的 API，你会追问它隐藏了什么 knowledge、每个 failure 对 caller 意味着什么、side effect 在失败时是否确定、logical request identity 从哪里来、state owner 是谁，以及内部实现变化以后这些承诺还能不能成立。

## 可选原始材料

本章完全自包含。下面材料用于交叉检查和进一步阅读；详细的 claim/source mapping 与 limitation 见 [`../reading-notes/m04-source-audit.md`](../reading-notes/m04-source-audit.md)。

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
