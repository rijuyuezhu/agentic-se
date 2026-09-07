# M04 Instructor Analysis — TaskForge Public Boundary

> **Spoiler warning**：完成 [`../../labs/04-api-error-boundary.md`](../../labs/04-api-error-boundary.md) 前不要读。
>
> 这不是唯一正确答案。它记录一条实际实现并验证过的 reference path，用来说明 M04 的 contract 可以在不引入 RPC、数据库或并发框架的前提下闭合；具体 source / course-synthesis 边界见 [`../../reading-notes/m04-source-audit.md`](../../reading-notes/m04-source-audit.md)。

M04 的 reference 不是从“应该定义什么 exception class”开始的。先看 starter，会发现它已经有一个有价值的 public boundary：内部 `Job` 是 mutable authoritative object，但 `public_api._view(...)` 把它投影成 serialization-friendly dict，所以 caller 修改返回值不会直接修改内部 state。问题是，这个 boundary 只隐藏了 representation 的一部分；`KeyError`、`cancelled=False`、invalid input 和 retry uncertainty 仍然把内部机制或未定义语义推给 caller。

因此本 Lab 真正要解决的是：**哪些 distinction 应该成为 caller 可以长期依赖的 contract，哪些 complexity 应该被 boundary 吸收。**

## 1. 先恢复 starter，而不是先设计新 error model

M04 starter 暴露四个 public operations：

```python
submit_job(command: str) -> dict
get_job(job_id: str) -> dict
list_jobs() -> list[dict]
cancel_job(job_id: str) -> dict
```

它们的 signature 很短，但真实行为比 signature 多得多。

| Operation | Current behavior | Caller-visible consequence |
|---|---|---|
| `submit_job` | 任意 `str` 都接受，包括 `""` 和空白；每次调用都分配新 job ID 并插入 state | same payload twice 会得到两个 jobs；当前没有 retry identity |
| `get_job` | known ID 返回 detached dict；unknown ID 穿出 `KeyError` | caller 依赖 Python dict missing-key behavior |
| `list_jobs` | 返回 detached dict views | public read 已经不携带 mutable `Job` authority |
| `cancel_job` | `QUEUED` 返回 `{"cancelled": True}`；running/terminal 返回 `False`；unknown 抛 `KeyError` | failure 同时使用 exception channel 与 boolean channel |

这里有两个容易被错误改写成“bug”的事实。

第一，same command twice 创建两个 jobs **不是**天然错误。没有 request identity contract 时，两次 transmission 完全可以代表两个不同 logical requests。真正的问题只在 response 丢失或 timeout 以后出现：caller 没有办法表达“这次发送是在重试刚才那个 logical request，而不是请求再创建一个相同 job”。

第二，starter 也不是“完全没有 boundary”。`public_api._view(...)` 已经把 authoritative `Job` identity 隔离在 public API 后面。下面这种 caller-side mutation 不会修改内部状态：

```python
view = public_api.get_job(job_id)
view["status"] = "succeeded"
assert public_api.get_job(job_id)["status"] == "queued"
```

所以这里的诊断不是“boundary 好 / 坏”二选一，而是：它在 mutable representation 上已经比较 deep，在 error identity、input validity、cancel semantics 和 retry uncertainty 上仍然 shallow。

## 2. `KeyError` 和 `False` 暴露的是不同类型的边界问题

Unknown `get` / `cancel` 最终来自：

```text
public_api
  -> service
  -> state.jobs[job_id]
  -> Python dict KeyError
```

如果底层 storage 改成 SQLite，missing row 可能表现为 `fetchone() is None`；换成远端 store 又可能是 RPC `NOT_FOUND`。因此 `KeyError` 不是稳定的 TaskForge domain identity，而是当前 representation 的 accident。

`cancelled=False` 的问题不同。它没有暴露 storage mechanism，却 collapse 了 caller 可能关心的不同状态。对于 UI、scheduler 或 admin tool，unknown job、running job 和已经 terminal 的 job 不一定允许相同后续动作。M04 不应先假设“每个 state 都要一个 exception class”，而应先问：**caller 在每种情况下一步需要做什么？**

这也是 reference error taxonomy 的出发点。它采用 broad code + domain reason + stable metadata + human message：

```python
ApiError(
    code="FAILED_PRECONDITION",
    reason="JOB_NOT_CANCELLABLE",
    message="...",
    metadata={"job_id": job_id, "status": status},
)
```

其中 `code` 表示 broad recovery category，`reason` 表示 TaskForge-specific machine identity，metadata 只保存 caller 需要且可以稳定承诺的 context；internal class、memory address、state-dict index 或 stack trace 都不应因此变成 public compatibility surface。Message 服务人类，不要求 machine client parse 文本；reference tests 固定 `code / reason / required metadata`，只要求 message 非空且有基本 actionable context，而不锁死完整文案。

Reference 使用四个 broad codes：`INVALID_ARGUMENT`、`NOT_FOUND`、`FAILED_PRECONDITION`、`CONFLICT`。这只是课程本地 vocabulary，不是说 TaskForge 必须复制完整 gRPC status taxonomy；以后真的出现 permission、deadline 或 remote availability pressure 时，再增加相应 distinction 才有理由。同样，`CONFLICT` 这个名字也不是规范本身。真正 invariant 是：**same request identity 不能被重新绑定到 different intent。**

对于 cancel，reference 把 running / succeeded / failed / cancelled 都表示为：

```text
code = FAILED_PRECONDITION
reason = JOB_NOT_CANCELLABLE
metadata.status = <current status>
```

原因不是“exception class 越少越好”，而是这些状态在当前 operation contract 下都表示 `QUEUED -> CANCELLED` transition 不能发生；若 caller 需要展示区别，可以读取 stable `status` metadata。若产品以后把 cancel 的语义改成“确保 job 不再 runnable”，那么 already-cancelled 是否应该成为 success 可以重新设计。M04 reference **没有**预先替未来产品做这个决定。

## 3. 输入 validity 要在产生 effect 之前建立

Feature request 要求 whitespace-only command 在 side effect 前失败。Reference 用一个很小的 frozen value type 建立 validation seam：

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

这里故意保留原始字符串，而不是把 `strip()` 后的结果存进去。Lab 没有 authority 决定 shell command 的 leading/trailing whitespace 是否 semantic-equivalent；它只要求 command 至少包含一个 non-whitespace character。若 caller 显式提供 `request_id`，空字符串同样是 invalid input，并且必须在任何 job/request mutation 前失败；这不是从实现倒推出的 policy，而是 reference contract 明确选择的 validation rule。

这也不能被夸成“Python type system 已经证明 invalid Command 不可表示”。Caller 仍然可以直接写 `Command("   ")`。Reference 获得的是更明确的 boundary discipline：public path 经过 `str -> Command.parse -> Command`，下游不需要每层重新解释 primitive string；运行时 invariant 仍然需要 encapsulation 和 tests 支撑。

Public read 则使用 detached / frozen representation，例如：

```python
@dataclass(frozen=True)
class JobView:
    id: str
    command: str
    status: str
    exit_code: int | None
```

这里 `status` 用 string 是为了模拟 future serialization boundary；public enum 也是完全合理的替代。真正 property 只是 public representation 不应把 internal mutable object identity 一起交给 caller。

## 4. Timeout 把问题从“same payload”推进到 request identity

到这里，input 和 error semantics 已经更清楚，但 retry 仍然没有答案。考虑一次 effectful submit：server 可能已经创建 job，response 却在网络上丢失。Caller 此时不知道 original effect 是否发生。如果它直接重发同样 command，TaskForge 又会创建第二个 job。

这时才需要 request identity。Reference contract 是：

| Case | Reference semantics | Additional effect |
|---|---|---|
| no `request_id` | 每次调用都是新 logical request | 每次创建一个 job |
| new ID + intent A | 创建 job，记录 ID → A → job identity | one job + request record |
| same ID + same intent A | 返回同一 logical job | no additional job |
| same ID + different intent B | `CONFLICT / REQUEST_ID_REUSED` | no new job；mapping 仍指向 A |

Reference 把 submit intent 定义成 **exact validated command string**。这也是教学选择，而不是 universal API law；如果未来要 normalize shell command，必须单独说明哪些变化 semantic-equivalent。

最重要的 distinction 是：**same bytes 不等于 same logical request。** 因而下面这种实现应被拒绝：

```python
request_id = sha256(command.encode()).hexdigest()
```

问题甚至不主要是 hash collision。同一个 `echo same` 可以是真正两个独立 jobs；只有 caller 显式提供同一个 request identity，才是在声明两次 transmission 属于同一个 logical operation。

Reference request registry 保存：

```python
@dataclass(frozen=True)
class _RequestRecord:
    command: Command
    job_id: str
```

它 authoritative 地回答“这个 request ID 对应什么 original intent / job identity”，但不复制 `job.status` 或 `exit_code`。因此 job lifecycle 与 request identity 是两种不同 semantic facts，拥有两个不同 owner 并不构成 duplicated job authority。

## 5. Idempotency 约束 intended effect，不要求 response bytes 永远相同

第一次 `req-1` submit 时 job 可能还是 queued；worker 随后 claim 后，caller 才重试同一个 request。Reference 返回同一个 `job_id` 的**当前 view**，所以 second response 可以显示 `running`，而不是保存第一次 response snapshot。

Reference 选择 current view 的理由很局部：当前 TaskForge 没有历史 response store；caller 真正需要的是 same logical creation / same job identity / no duplicate job；保存旧 response 还会新增一份 lifetime state。另一种“保存第一次 success snapshot”的设计也可以成立，只要 contract 明确并支付相应 state cost。

`replayed=True/False` 同样只是 reference 的教学辅助，让 test 可以直接观察 dedup path。真实 API 如果 caller 不需要知道 first delivery 与 replay 的区别，完全可以不暴露这个字段；一旦暴露，它自己也会成为 compatibility surface。

因此 M04 能声明的是：

> same request ID + same intent 在当前 in-process baseline 下不会创建第二个 `Job`。

它**不能**因此声明 exactly-once command execution。Worker crash、concurrent duplicates、durable request registry、external effects 都还没有解决。

## 6. Evidence 必须观察 side effect，而不只观察 exception 或返回值

Reference validation 在临时 TaskForge copy 中实际得到：

```text
original core tests: 6
M04 reference tests: 12
total: 18 passed
```

Canonical starter 没有被替换成答案版本。Reference tests 覆盖：

- blank command / blank supplied request ID 在 mutation 前失败；
- unknown get / cancel 被翻译成 stable `NOT_FOUND`；
- running / terminal cancel 产生 `FAILED_PRECONDITION` + status context；
- queued cancel 成功；
- no request ID + same command 仍创建两个 jobs；
- same ID + same intent 只创建一个 job；
- retry after job becomes running 仍引用同一个 job，并允许 current view 变化；
- same ID + different intent conflict 且不创建新 job；
- public view frozen / detached。

这里最关键的不是 test 数量，而是 oracle 的观察面。

只写：

```python
with raises(INVALID_ARGUMENT):
    submit_job("   ")
```

不足以证明 fail-before-side-effect，因为错误实现完全可能先 `service.submit(...)` 创建 ghost job，再抛 exception。Reference 同时检查 `list_jobs() == []`，并确认下一次合法 submit 仍能获得预期第一个 ID。

同样，same request ID 的 test 不能只比较两个 response equality。它至少要同时观察 same job identity 和 authoritative job count 仍然为 1。Same ID + different intent 还要确认 mapping 没被第二次 intent 篡改。

这也是为什么 `18 passed` 比 coverage percentage 更有意义：即使 branch coverage 100%，如果漏掉 same-ID/different-intent partition，最危险的 semantic dedup bug 仍然可以存活。

## 7. Reference implementation 刻意留下几个 failure window

M04 的 reference 是 bounded design，不是提前完成 M07/M08/M09。

### Cancel 的 check-then-observe race

Reference 先调用现有 `service.cancel(job_id)`；如果它返回 `False`，再读 current job 来构造 status metadata。当前单线程 starter 里这两个动作之间不会变化；并发后可能出现：cancel check 观察一个 state，随后 read metadata 时已经变成另一个 state。

这是真实 race，但本 Lab 不顺手把 cancel 改成 atomic transition-result API。M07 才负责让 operation 可以原子返回类似 `Cancelled / NotCancellable(observed_state) / NotFound` 的 semantic result。

### Request registry 不是 crash-safe

Reference sequence 近似是：

```text
1. create job
2. write request_id -> intent/job record
```

若 process 在两步之间 crash，job 已创建而 request record 没有持久化；restart 后 retry 仍可能创建 duplicate job。因此 reference 只声称 single-process/no-crash baseline 下的 request dedup semantics。

### Request registry 也不是 concurrency-safe

两个并发 requests 可以同时观察 `request_id` absent，然后分别创建 job，再覆盖 mapping。结果仍可能有两个 jobs。这不是遗漏掉 M04 核心要求，而是明确留给 M07 的 concurrency pressure。

### Test fixture lifecycle 也多了一个 owner

Reference 提供统一 test reset，是因为 state 现在至少跨 job lifecycle owner 与 request-identity owner。只 reset job state 而不清 request records 会让 tests 相互污染。这提醒学生：fixture lifecycle 本身也需要和 production state ownership 对齐。

这些 limitation 必须写出来。它们不能被一句“request ID makes submit idempotent”盖掉。

## 8. 几条看起来合理、但应被 review 拒绝的路径

**Catch-all translation**：

```python
try:
    ...
except Exception as exc:
    raise ApiError("INTERNAL") from exc
```

它把 expected domain failure 与 programming bug 混成一个 channel，可能隐藏 defect 并让 operator diagnosis 更难。Reference 只翻译自己理解其 domain meaning 的 failure；真正 RPC entry point 未来仍可以有最后的 INTERNAL safety boundary，但那是另一层 responsibility。

**Every state one exception class**：`JobRunningError`、`JobSucceededError`、`JobFailedError`、`JobCancelledError` 看起来精确，却未必对应不同 caller action。Taxonomy 应由 caller semantics 驱动，不由内部 enum 数量驱动。

**Payload hash as request identity**：它错误地把 same representation 当 same intent，会 dedup 两个本来独立的相同 command。

**“Exactly once jobs”**：reference 没有解决 concurrent duplicate submit、process crash、durable request identity、worker re-execution 或 arbitrary external effects。把 in-process creation dedup 洗成 exactly-once execution 是 guarantee drift。

**为了“完整”一次引入更多 mechanism**：SQLite transaction、unique durable request table、lock、RPC、retry middleware、tracing 都可能在后续成为合理设计，但 M04 当前没有 authority 一次性把它们加进来。那样会让 boundary semantics 淹没在 mechanism 中。

## 9. Exception vs Result、cancel replay 等都不是课程宗教

Reference 使用 Python exception 表达 failure，是因为这符合当前语言 ergonomics，也不需要自制 Result framework；`ApiError` 已经提供 machine-readable semantics，未来可以映射到 RPC wire representation。

但 `Result[JobView, ApiError]` 也是合理替代，尤其当项目已有 Result idiom、caller 需要 exhaustive match，或 language type system 更适合 union modeling 时。课程评分的是 boundary semantics，不是 exception-vs-Result 阵营。

同样，reference 没把 `cancel(CANCELLED)` 定义成 success。当前 primitive 更接近“执行 `QUEUED -> CANCELLED` transition”，所以 already-cancelled 仍是 failed precondition。如果产品 contract 以后改成 postcondition-style “ensure not runnable”，就应该重新 design it twice，而不是把 reference choice冻结成 API law。

这正是 “define errors out of existence” 的正确使用方式：它是一个 design question，不是“error 越少越高级”的规则。

## 10. 最终 ownership map 比 class diagram 更重要

Reference path 完成后，可以把关键 facts 压缩成：

| Fact | Authority |
|---|---|
| raw API input validity | public boundary / parser |
| job lifecycle | existing TaskForge job state/service owner |
| request identity → original intent / job | request registry |
| public error vocabulary | public boundary |
| public detached representation | public boundary |

这里没有要求一个 component 拥有所有 state。重要的是每个 semantic fact 有明确 owner，而且 request registry 不复制 job status。

Public `JobView` 与 internal `Job` 也因此可以独立演化。未来 internal model 可以新增 `lease_owner`、`attempt_count`、`created_at` 而不自动变成 public fields；public boundary 也可以提供 derived field，而不要求 storage 直接保存它。这才是 representation independence 在 API boundary 上的意义。

M04 reference 仍然明确留下这些债务：request-registry persistence / retention、concurrent same-ID submit、atomic create+record、cancel observation race、remote serialization、retry backoff/budget。它们分别会在后续 concurrency、compatibility、architecture、production 模块中重新出现。

## 11. 对 Agent 的判断：任务 contract 比“更聪明的 retry patch”重要

如果只给 Agent：

```text
Improve TaskForge's public API error handling and make submit safe to retry.
```

它很容易产生技术上 plausible 的答案：retry decorator、payload hash、catch-all、很多 custom exceptions，或者只测试返回值而不检查 side-effect cardinality。问题不一定是 Agent 不会编码，而是 task 没有告诉它什么 semantics 才算正确。

更强的 engineering spec 会先固定这些 obligations：blank input fail-before-side-effect；unknown external error 不依赖 `KeyError`；cancel failure 保留 machine-readable caller context；same request identity + same intent 不产生 duplicate job；same identity + different intent 必须 conflict；public view 不携带 mutable authority；persistence/concurrency/exactly-once execution 都是 non-goal。

这样 Agent 的任务从“想一个重试方案”缩小成“实现并证明这个 contract”。实现完成后，reviewer 仍应独立检查 request identity 是 caller intent 还是 payload guess、error translation 是否吞 bug、side-effect oracle 是否完整，以及文档有没有把 creation dedup 夸成 execution guarantee。

## 12. Instructor judgment

高质量答案不要求复制 reference types 或 status-code naming。它应该能让 reviewer 看见一条完整 reasoning chain：

1. 先从 starter 恢复 implemented behavior 与 representation leak；
2. 从 caller action 设计 stable error semantics；
3. 在 timeout / unknown outcome pressure 出现后才引入 request identity；
4. 证明 input failure 在 side effect 前发生，retry 没有 duplicate creation；
5. 把 request identity 与 job lifecycle authority 分开；
6. 明确 crash、concurrency 和 external-effect guarantees 的边界；
7. 不用 framework、pattern 名字或 test count 代替 contract reasoning。

低质量答案通常会反过来：先写 exception classes、catch everything、retry everything、用 payload hash 猜 identity、只测 happy path，最后把一份 in-memory dedup table写成 exactly-once guarantee。

M04 最终要训练的不是“Python 怎么定义 `ApiError`”，而是两种可迁移判断：**boundary design 要把 mechanism-specific complexity 压缩成 caller 可以长期依赖的少量语义；retry-safe effectful API 必须从 logical request identity 和 unknown outcome 开始，而不是从重试循环开始。**
