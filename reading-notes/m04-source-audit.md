# M04 Source Audit — API、Error 与 Boundary Design

> 目标：不是搜集“API 最佳实践”，而是确认哪些原始材料真的能支撑 M04 的核心判断。
>
> 本模块只把实际检查过正文/规范的材料升级成主线。仅凭“很有名”不进入主线。

---

# 0. 本模块要回答的问题

M04 关注五个问题：

1. 一个 boundary 应该吸收多少复杂度，而不是向 caller 泄漏多少复杂度？
2. 哪些 invalid states 应在 boundary 被消除，而不是进入 core 后反复检查？
3. error 是 implementation accident，还是 caller 可以依赖的 contract？
4. retry 在什么语义下才安全？
5. 怎样把内部细粒度 failure 翻译成外部稳定、可操作的 error semantics？

需要特别避免五种口号化理解：

- “每种错误都定义一个 exception class”；
- “fail fast 所以越早抛越好”；
- “POST 不幂等 / PUT 幂等，所以 HTTP method 决定一切”；
- “同样参数就是 duplicate request”；
- “make illegal states unrepresentable 意味着所有 invariant 都必须塞进 type system”。

---

# 1. Stanford CS190 — Error Handling

**状态：主干采用（error complexity / caller ownership）**

原始讲义：

- https://web.stanford.edu/~ouster/cgi-bin/cs190-spring15/lecture.php?topic=errorHandling

## 实际检查了什么

逐项检查了讲义中：

- error source taxonomy；
- 为什么 error/exception 会成为 complexity source；
- defensive programming / “punt to caller” 如何增加 exception 数量；
- define errors out of existence；
- mask errors；
- collapse errors；
- defer reporting；
- “before throwing, think how caller will handle it”。

## 实际内容支持什么

讲义不是在教“异常语法”，而是在问：

> **系统里到底应该有多少 distinct failure cases 需要上层理解？**

它明确指出，程序员容易通过两种方式把问题变糟：

```text
看到可疑情况就抛异常
+
自己不想处理就把异常传给上层
```

结果是：

```text
exception count ↑
caller branches ↑
rare handlers ↑
untested failure paths ↑
```

这和本课程的 complexity framing 一致。

## 最值得吸收的三点

### 1. Define errors out of existence

不是所有“不符合实现偏好”的情况都必须成为 caller-visible error。

有时可以重新定义 API semantics，让那个 case 不再需要特殊处理。

这不是“吞异常”，而是改变 abstraction contract。

### 2. Collapse errors

如果多个低层错误对 caller 的可行动策略相同，那么外部 boundary 未必应该暴露所有低层 distinction。

例如：

```text
errno A / errno B / socket detail C
          ↓
external operation unavailable
          ↓
caller: retry later
```

这里更稳定的 semantic distinction 是“caller 应该做什么”，不是“底层碰巧哪个 syscall 失败”。

### 3. Error ownership 要从 caller action 反推

讲义有一个特别强的 review question：

> 抛出一个 error 前，先想 caller 会怎样处理它。

本课程将它推广成：

```text
如果两个 error 对 caller 的允许动作完全一样，
它们是否真的需要成为两个 public contract cases？
```

反过来：

```text
如果同一个 error code 实际需要两种完全不同恢复策略，
这个 contract 是否过度 collapse？
```

## 局限

这份讲义来自 2015 年，例子带有 Java/Tcl/RAMCloud 时代背景。

它没有系统讨论：

- machine-readable error schema；
- request id；
- idempotency token；
- retry across network uncertainty；
- public API compatibility。

所以它只负责“error complexity / ownership”这一层，不独立承担整个 M04。

---

# 2. Stanford APOSD discussion — Define errors out of existence

**状态：主干采用，但作为 design heuristic，不作为定律**

原始课程讨论页：

- https://web.stanford.edu/~ouster/cs190-winter23/lectures/aposd/

## 实际检查了什么

页面要求学生阅读 APOSD 主要章节并讨论：

- interface vs implementation；
- deep/shallow classes；
- abstraction；
- dependencies；
- define errors out of existence；
- pull complexity downwards；
- design it twice。

其中页面对 “define errors out of existence” 明确加了一个重要限制：

```text
use this idea judiciously
```

也就是作者自己的课程材料并不把它当无条件规则。

## 本课程怎么用

我们把它和 M02 的 deep module / information hiding 连起来：

```text
shallow boundary:
caller 要知道很多 failure mechanism

better boundary:
内部吸收 mechanism complexity
对外暴露少量稳定 semantic outcomes
```

但不会把所有 error 都“定义没”。

例如：

- 权限拒绝；
- 用户输入真的非法；
- 并发 conflict；
- durable write 失败且无法确认 outcome；

这些往往必须成为 caller-visible information。

关键不是“少报错”，而是：

> **只暴露 caller 需要知道、能够采取行动、并且系统能长期稳定承诺的 distinction。**

---

# 3. Google AIP-193 — Errors

**状态：主干采用（external error contract）**

原始规范：

- https://google.aip.dev/193

## 实际检查了什么

检查了：

- canonical status code；
- human-readable message；
- machine-readable ErrorInfo；
- reason/domain identity；
- metadata；
- error message compatibility；
- details evolution；
- partial errors guidance；
- why standardized errors simplify client handling。

## 最重要的内容

### 1. Error identity 不能依赖 message parsing

AIP-193 要求提供 machine-readable error identity，并明确把动态信息放到 metadata，而不是逼 client parse message。

这对 Agent 时代尤其重要：

```text
"cannot cancel job-12 because state is running"
```

如果这是唯一 contract，Agent 很容易生成：

```python
if "running" in str(exc):
    ...
```

这是极脆弱的 coupling。

更好的 boundary 是：

```text
code = FAILED_PRECONDITION
reason = JOB_NOT_CANCELLABLE
metadata.status = running
```

人类文本可以改善，而 machine contract 仍稳定。

### 2. “same error” 应从 client action 考虑

AIP-193 对 `(reason, domain)` 的说明里有一个非常适合本课程的判断：

两个 error 是否应视为“同一个”，应考虑 client 预期采取的 resolution/action。

这与 Stanford “think how caller will handle it” 独立收敛到同一个设计中心：

> **error taxonomy 应围绕 caller semantics，而不是 implementation taxonomy。**

### 3. Error metadata 自己也会成为 compatibility surface

一旦 client 观察到某些 machine-readable metadata key，它们就可能形成依赖。

这正好为 M08 compatibility 铺路：

```text
错误不是旁路文本。
错误 schema 本身也是 API。
```

## 不照搬什么

本课程不会要求 TaskForge 实现完整 `google.rpc.Status`。

我们吸收的是设计结构：

```text
stable category
+
stable machine reason
+
context metadata
+
human message
```

而不是绑定 gRPC/Proto。

---

# 4. Google AIP-194 — Automatic retry configuration

**状态：主干采用（retryability semantics）**

原始规范：

- https://google.aip.dev/194

## 实际检查了什么

检查了：

- 哪些 operation 可以自动 retry；
- 为什么 repeated execution 的 state effect 是核心；
- retryable / non-retryable status categories；
- transactional request 为什么不能只 retry 单个 RPC；
- `UNAVAILABLE` / `INVALID_ARGUMENT` / `ABORTED` 等的差别。

## 为什么重要

很多代码把 retry 写成：

```python
for _ in range(3):
    try:
        return call()
    except Exception:
        sleep(...)
```

这不是 resilience；它是在扩大 side effect uncertainty。

AIP-194 强调：

```text
能否 retry
!=
是不是发生了 error
```

而取决于：

```text
operation semantics
+
重复执行是否会造成 unintended state change
+
failure category
```

## 本课程的推广

我们不教“记住哪些 gRPC code 可 retry”。

而是训练三个问题：

1. caller 在 failure 时知道 original operation 是否执行过吗？
2. 如果不知道，重复请求是否仍满足 contract？
3. retry 应发生在当前 layer，还是更高层 transaction/workflow？

这三个问题比背 code table 更可迁移。

---

# 5. Google AIP-155 — Request identification

**状态：主干采用（request identity / dedup contract）**

原始规范：

- https://google.aip.dev/155

## 实际检查了什么

检查了：

- customer-provided request ID 的用途；
- deduplication；
- retry safety；
- auditing；
- duplicate request 应返回之前 successful result 的语义；
- request ID lifetime；
- stale success response。

## 关键结论

AIP-155 明确把 request ID 视为 idempotency guarantee 的一种基础：

```text
same request identity
→ duplicate execution can be detected
→ retry need not create duplicate effect
```

这里最重要的是 **identity 是 contract 的一部分**。

这不是：

```text
服务器看到两个 payload 一样
→ 猜它们是 duplicate
```

而是：

```text
caller 显式声明：这两次发送属于同一个 logical request
```

## 与 M02 state ownership 的连接

引入 request dedup table 后会出现一个很好的 ownership 问题：

```text
job state owner
!=
request identity owner
```

dedup state 是一份新的 state，但不一定是 duplicated authority。

如果它只 authoritative 地回答：

```text
request_id 对应哪个 logical operation / result
```

而 job store authoritative 地回答：

```text
job 当前 lifecycle state
```

两者是两个不同 semantic facts。

这会成为 M04 TaskForge lab 的一个重点。

---

# 6. AWS Builders' Library — Making retries safe with idempotent APIs

**状态：主干采用（真实 distributed retry case study）**

原始文章：

- https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/

## 实际检查了什么

检查了：

- retrying and side effects；
- unknown outcome after timeout；
- reducing client complexity；
- why parameter hashing is insufficient；
- caller-provided client request identifier；
- semantic equivalence of retried responses；
- late arriving requests；
- same client request ID, different intent。

## 这是本模块最重要的 idempotency case study

### 1. 真正难点是 unknown outcome

典型 distributed failure：

```text
client sends create
        ↓
server may execute
        ↓
response is lost / timeout
        ↓
client does not know whether effect happened
```

此时：

```text
retry?
```

不是“网络编程细节”，而是 API semantics 问题。

### 2. 同样参数不等于同一个 intent

AWS 文章明确比较了 parameter-derived synthetic token 和 caller-provided token。

两个内容完全一样的请求可能是：

```text
retry same operation
```

也可能是：

```text
please create another identical resource
```

因此 payload equality 不能普遍代表 request identity。

这个 distinction 非常适合 Agent：

Agent 很容易看到：

```python
hash(request)
```

然后认为已经“实现幂等”。

课程要求它先回答：

> hash equality 到底代表 same intent，还是只是 same bytes？

### 3. Idempotency 不要求 response bytes 完全相同

AWS 文章区分了 byte identity 和 semantic equivalence。

retry 时资源状态可能已经从 `pending` 变 `running`，response 可以不同，但 caller 仍应得到“同一个 logical creation result”。

这也是课程会采用的定义：

> **幂等首先约束 intended effect / logical operation identity，不要求所有内部事件和 response bytes 相同。**

### 4. 幂等会把复杂度从 caller 拉进 service boundary

这是与 APOSD “pull complexity downward” 的具体连接。

没有 idempotent contract：

```text
每个 caller
都要写 reconciliation / dedup / uncertainty handling
```

有稳定 request identity：

```text
service boundary 吸收 dedup complexity
callers 可以安全使用统一 retry policy
```

这不是“让 server 更简单”，而是：

> **把 complexity 放到更有 information、能统一处理它的 owner。**

## 局限

这是 Amazon 大规模分布式系统经验，不代表每个本地函数都需要 idempotency key。

对于：

- 纯函数；
- 无 side effect query；
- 本地 atomic call；
- caller 可直接确认 outcome 的操作；

引入 request-id store 可能是无意义复杂度。

课程会把它限制在“effectful operation + uncertain delivery/outcome + retry 有实际价值”时使用。

---

# 7. RFC 9110 — HTTP idempotent semantics

**状态：辅助采用（术语校准）**

原始规范：

- https://www.rfc-editor.org/rfc/rfc9110.html#name-idempotent-methods

## 实际检查了什么

检查了 RFC 9110 §9.2.2 的定义和 retry rationale。

它定义 idempotent method 的核心是：

```text
multiple identical requests
have the same intended effect
as one such request
```

并明确说明：

- logging 等内部 side effects 可以每次发生；
- idempotency 关注 user-requested intended effect；
- idempotency 的价值之一是 connection failure 后能安全重发；
- 非幂等 method 不应自动 retry，除非客户端知道该具体 operation 的 semantics 实际安全，或知道原请求未被执行。

## 为什么只作为辅助材料

本课程不是 HTTP API 课。

RFC 的价值是校准一个常见误解：

```text
idempotent
!=
函数内部绝对没有任何 side effect
```

也不是：

```text
POST 永远不能做成安全 retry
```

HTTP method 是 protocol contract 的一层；业务 operation 仍然需要自己的 semantic reasoning。

---

# 8. Alexis King — Parse, don't validate

**状态：选择性主干采用（boundary parsing / illegal states）**

原文：

- https://lexi-lambda.github.io/blog/2019/11/05/parse-don-t-validate/

## 实际检查了什么

检查了：

- partial vs total function；
- weaken result vs strengthen argument；
- `NonEmpty` worked example；
- validation 丢弃已获得信息的问题；
- boundary parsing；
- shotgun parsing；
- “use a data structure that makes illegal states unrepresentable”；
- “push burden of proof upward as far as possible, but no further”；
- 作者自己对过度 type-level modeling 的限制说明。

## 为什么值得放入 M04

这篇文章不是因为 slogan 有名，而是它给出了非常清楚的 executable reasoning：

```text
validateNonEmpty :: [a] -> IO ()
```

检查之后，类型仍然只是 `[a]`。

下游仍必须重新担心 empty case。

而：

```text
parseNonEmpty :: [a] -> IO (NonEmpty a)
```

把已经验证出的知识保存在 representation 里。

这和 M01/M02 完全接得上：

```text
boundary 检查 invariant
        ↓
构造更精确 representation
        ↓
core 不再重复承担同一个 proof obligation
```

## 本课程不会机械化它

TaskForge 使用 Python，静态类型能力比 Haskell 弱。

所以我们不会假装：

```text
只要定义几个 NewType/dataclass
就让非法状态数学上不可表示
```

在 Python 中更现实的目标是：

- raw input 和 validated/domain input 用不同 representation；
- constructor/factory 集中验证；
- core functions 接受已经建立 invariant 的 value；
- 不在每一层重新 parse primitive string；
- 运行时 invariant 仍用 tests/assertions/encapsulation 保护。

原文最后也明确说这些是 ideals，不是每个 invariant 都值得通过极端 type machinery 消除。

---

# 9. gRPC Error Handling / Status Codes

**状态：辅助采用（cross-boundary error vocabulary）**

原始资料：

- https://grpc.io/docs/guides/error/
- https://grpc.io/docs/guides/status-codes/

## 实际检查了什么

检查了：

- standard error model；
- canonical status codes；
- network/library-generated failure；
- application-generated failure；
- richer details model。

## 本课程吸收什么

不是要求学生学 gRPC。

而是借它说明：

```text
跨进程 / network boundary
```

之后，Python exception type 本身通常已经不是合适的 public contract。

需要一个可序列化、跨语言、稳定的 semantic error vocabulary。

例如内部：

```text
KeyError
sqlite3.IntegrityError
OSError
WorkerGone
```

外部未必应该原样出现。

boundary 要问：

```text
caller 看见什么 category？
caller 下一步能做什么？
哪些 context 必须 machine-readable？
```

这为 M09 remote worker 和 M11 production error handling 铺路。

---

# 10. 材料之间如何拼起来

这些来源不是重复讲同一个东西，而是填不同层：

```text
Alexis King
    ↓
raw input → precise representation
invalid states 尽早在 boundary 消除

Stanford / APOSD
    ↓
减少 caller 必须理解的 error complexity
只暴露真正有意义的 distinction

Google AIP-193
    ↓
一旦 error 穿过 public boundary
需要稳定 machine-readable contract

AIP-194 + RFC 9110
    ↓
retry safety 是 operation semantics
不是 catch-all loop

AIP-155 + AWS Builders' Library
    ↓
request identity / semantic idempotency
解决 unknown outcome 与 duplicate side effects
```

这形成 M04 的主线：

```text
parse boundary input
      ↓
establish precise internal state
      ↓
perform operation under clear ownership
      ↓
translate failures into caller-action semantics
      ↓
make retry behavior explicit
      ↓
when needed, use request identity to make effects idempotent
```

---

# 11. 明确不作为本模块规则的内容

## “所有 error 都应该 exception”

不采用。

error 表达方式取决于：

- language；
- boundary；
- caller usage；
- recoverability；
- control flow frequency。

## “fail fast”

只作为局部 heuristic。

如果更好的 abstraction 可以让 error 不存在，或者 boundary 能安全恢复，机械地更早抛异常反而增加 caller complexity。

## “HTTP method 决定 idempotency”

不采用。

HTTP semantics 是一层 contract；具体 operation 仍需分析 intended effect 与 retry uncertainty。

## “same payload hash = same request”

明确反对作为一般规则。

AWS case study 直接给出了其 semantic ambiguity。

## “所有 invariant 都编码到 type system”

不采用。

成本过高、语言不支持或 invariant 与外部世界相关时，应结合 runtime checks、encapsulation、state machine 和 tests。

---

# 12. 对 Agent 的直接转化

M04 之后，一个高质量 Agent task 不应该只说：

```text
给 API 加错误处理和 retry
```

而应该要求 Agent 先回答：

```text
1. public operations 是什么？
2. raw input 在哪一层 parse？
3. 哪些 invalid states 应被拒绝，哪些应被 normalize？
4. 每个 public error 对 caller 意味着什么 action？
5. 哪些内部 error 不应穿过 boundary？
6. 哪些 operation 允许 automatic retry？为什么？
7. timeout 后 outcome unknown 时怎么办？
8. request identity 如何定义？
9. same request_id + different intent 怎么处理？
10. 怎样证明 retry 没有产生 duplicate effect？
```

然后才允许实现。

这就是本模块材料选择的最终标准。