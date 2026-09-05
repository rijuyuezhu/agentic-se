# M03 — Testing：测试是可执行证据，不是宗教

> 这一章的目标不是把你训练成“更会写 pytest/JUnit 的人”。
>
> 真正目标是：**面对一个软件 contract 和一组风险，你能设计一组成本可接受、语义清楚、能区分正确与错误变化的 executable evidence。**

---

# 0. 从一个令人不舒服的事实开始

上一章的 TaskForge baseline 有 6 个测试：

```text
......
6 passed
```

它们验证了：

- job id 单调增长；
- submit 后进入 queued；
- worker claim 第一个 queued job；
- finish 成功/失败记录 exit code；
- running job 不能 cancel；
- non-running job 不能 finish。

看起来不错。

但同时：

```python
job = service.get(job_id)
job.status = JobStatus.SUCCEEDED
```

caller 可以直接把系统里的 authoritative state 改掉。

测试仍然全绿。

这不是 pytest 的 bug。

也不是“我们测试写得太少”这么简单。

真正发生的是：

> **测试从来没有提出过“read API 不应授予 mutation authority”这条 claim。**

所以它当然不会失败。

这一章最核心的一句话是：

> **一个 test 只会保护它真正检查的 claim。它不会因为文件名叫 `test_...` 就自动理解你的系统。**

---

# 1. Testing 在软件工程里到底是什么

一个测试可以粗略看成：

```text
setup
  ↓
action
  ↓
observation
  ↓
oracle
  ↓
pass / fail
```

其中最重要、最容易被忽略的是 **oracle**。

oracle 回答：

> “观察到什么结果时，我们认为实现符合预期？”

例如：

```python
job_id = submit("echo hi")
assert get(job_id).status == QUEUED
```

这里 oracle 是：

```text
submit(command) 之后，该 job 的 observable status 必须是 QUEUED
```

如果你的 oracle 错了，测试越稳定，可能越危险。

---

# 2. Test 不是 correctness proof

假设一个函数：

```python
def abs(x: int) -> int:
    ...
```

你写：

```python
assert abs(1) == 1
assert abs(-1) == 1
```

两条测试通过，不能推出：

```text
∀x, abs(x) 满足 specification
```

它只证明：

```text
在这两个具体 execution 上，观察结果符合 oracle
```

所以 testing 的逻辑形态通常不是：

```text
proof of correctness
```

而更像：

```text
attempt to find counterexamples
+
regression evidence for known claims
```

一个成熟的 correctness argument 可能同时使用：

```text
specification
+ type/static checking
+ tests
+ code review
+ invariant reasoning
+ production evidence
```

不要让 tests 垄断 “correctness” 这个词。

---

# 3. Test suite 的真正问题：它能区分什么？

MIT 6.102 的一个非常好的 framing 是：测试集不只是“有没有测试”，而要看它能否有效地区分合法和错误实现。

我们把这个概念推广一下。

设：

```text
L = 所有符合 contract 的实现
B = 我们关心的一类错误实现
T = test suite
```

好的 T 希望做到：

```text
对 L：尽量不误报
对 B：尽量能拒绝
```

这比 coverage percentage 更接近本质。

## 3.1 Correctness of tests

一个合法实现不应该因为测试偷绑 implementation detail 而失败。

例如 contract 只承诺：

```text
list_jobs() 返回所有 job，不承诺顺序
```

如果 test 写：

```python
assert list_jobs() == [job1, job2, job3]
```

那么把内部 dict 换成 hash set 后 test 失败，未必是 production regression。

可能只是 **test 自己发明了 contract**。

## 3.2 Thoroughness

另一个方向：错误实现是否能偷偷通过？

例如：

```python
def is_terminal(status):
    return status in {SUCCEEDED, FAILED}
```

忘了 `CANCELLED`。

如果 tests 只检查 succeeded/failed，这个 bug 就活着。

## 3.3 Small / high-information

1000 个重复的 happy-path test 不一定比 10 个有结构的 test 更强。

例如：

```text
x = 1
x = 2
x = 3
...
x = 1000
```

有时不如：

```text
partition:
  x < 0
  x = 0
  x > 0

boundary:
  -1, 0, 1
```

重点不是 case 少，而是每个 case 有明确理由。

---

# 4. 从 Spec 到 Test：先找 partition

一个常见的坏习惯是：

> “我来想几个例子。”

更好的问题是：

> **spec 把输入/状态空间分成了哪些行为区域？**

例如 TaskForge `finish(job_id, exit_code)`：

假设 contract 是：

```text
precondition:
    job exists
    job.status == RUNNING

postcondition:
    exit_code == 0  → SUCCEEDED
    exit_code != 0  → FAILED

invariant:
    terminal job has a final exit_code unless CANCELLED
```

那么至少可以得到这些 partition：

```text
job state:
  QUEUED
  RUNNING
  SUCCEEDED
  FAILED
  CANCELLED

exit_code:
  0
  negative
  positive
```

注意这里的 input 已经不只是函数参数。

它包括：

- 参数；
- 之前的 system state；
- dependency state；
- lifecycle history。

真实软件测试必须学会在 **state space** 上 partition。

---

# 5. Boundary values：bug 喜欢边界

很多实现错误不是随机分布的。

它们集中在：

- `<` vs `<=`；
- empty vs non-empty；
- zero vs non-zero；
- first / last；
- max size；
- before/after timeout；
- first retry / last retry；
- old version / new version；
- before/after lifecycle transition。

例如：

```python
if retries < MAX_RETRIES:
```

最有价值的 case 通常不是：

```text
retries = 2
```

而是：

```text
MAX_RETRIES - 1
MAX_RETRIES
MAX_RETRIES + 1
```

这也是为什么 mutation testing 常喜欢做：

```text
<  ↔ <=
== ↔ !=
+1 ↔ -1
```

因为这些小变化高度模拟真实 boundary bugs。

---

# 6. 一个 test 的三层结构

我建议把 tests 看成三层：

```text
scenario
claim
mechanism
```

## 6.1 Scenario

发生了什么现实情景？

例如：

```text
Given 一个 queued job
When client 请求 cancel
Then job 进入 cancelled
```

## 6.2 Claim

你真正要保护的语义是什么？

```text
queued job 可取消
cancel 成功后 observable status 为 CANCELLED
```

## 6.3 Mechanism

pytest/JUnit/Hypothesis/mock/fake/fixture 只是实现这个 claim 的 mechanism。

如果你一上来先想：

> “我要不要 mock？”

你已经跳过最重要的两层。

---

# 7. Test Behavior，不要机械 Test Method

production code：

```python
def submit(command):
    ...
```

最幼稚的测试组织方式：

```python
def test_submit():
    ...
```

然后这个测试慢慢变成：

```text
100 行
检查 id
检查 queue
检查 duplicate
检查 empty command
检查 metrics
检查 persistence
检查 logging
```

因为你是按 method，而不是 behavior 组织。

更好的形式：

```python
def test_submit_queues_new_job(): ...
def test_submit_assigns_fresh_id(): ...
def test_submit_rejects_empty_command(): ...
def test_submit_does_not_mutate_existing_jobs(): ...
```

注意：

```text
method : behavior
```

不是 1:1。

一个 behavior 也可能横跨多个 methods：

```text
submit → claim → finish
```

整个 lifecycle 才是一个 meaningful scenario。

---

# 8. “通过 public API 测”到底是什么意思

这条规则经常被误解成：

> “只能测试语言 public method。”

不是。

真正的问题是：

> **这个 unit 对其真实 client 的 semantic boundary 在哪里？**

例如一个 package 内部：

```text
service.py
storage.py
codec.py
helpers.py
```

如果真实 client 只使用：

```python
service.submit()
service.get()
```

那么测试 `helpers._serialize_job()` 的具体字符串格式，很可能是在绑定 implementation。

如果未来：

```text
JSON → SQLite
```

client 行为没变，但 50 个 tests 全坏了，这些 tests 其实充当了错误的 architecture constraint。

## 8.1 一个有用的问题

看到一个 test 时问：

> **如果这个 test 因未来 refactor 失败，真实 user 是否也应该认为系统坏了？**

如果长期答案都是：

```text
No
```

它可能测错了边界。

---

# 9. 但不要把“public API testing”机械化

有些 internal component 本身就有独立 contract。

例如：

```text
parser
scheduler
cache eviction policy
serialization codec
```

如果它是一个稳定可复用的 semantic unit，直接测试它当然合理。

所以真正的问题不是：

```text
public/private keyword
```

而是：

```text
这个 boundary 是否是我们打算长期维护的 contract？
```

M02 的 abstraction judgment 在这里直接决定 M03 的 test boundary。

---

# 10. State testing vs Interaction testing

假设：

```python
create_user("alice")
```

一个 interaction test：

```python
mock_db.put.assert_called_once_with("alice")
```

它验证的是：

```text
实现调用了某个具体 collaborator API
```

一个 state/outcome test：

```python
assert get_user("alice") is not None
```

它验证：

```text
最终 observable outcome 成立
```

多数业务逻辑中，后者更接近 contract。

---

# 11. 为什么 interaction test 容易 brittle

假设实现从：

```python
db.put(key, value)
```

改成：

```python
db.transaction(lambda tx: tx.insert(key, value))
```

真实行为没变。

但：

```python
assert_called_once_with(...)
```

会失败。

这意味着 test 在宣布：

```text
“调用 db.put” 是 contract
```

可真实用户可能根本不关心。

这就是 **test-induced accidental contract**。

---

# 12. 什么时候 interaction 本身就是 contract

不要反过来变成 “interaction testing 永远错”。

例如：

```text
付款系统必须恰好向支付网关发一次 charge request
```

这里 external interaction 本身就是 observable side effect。

又如：

```text
审计系统必须写 audit event
```

或：

```text
收到 SIGTERM 时必须向 worker 发 cancellation signal
```

此时应该测试 interaction。

但要测的是：

```text
external protocol obligation
```

不是内部 helper choreography。

---

# 13. Test Double：你模拟掉了什么风险？

常见 doubles：

- fake：简化但可工作的替代实现；
- stub：预设返回；
- spy/mock：记录/验证 interaction。

名字不是重点。

重点是：

> **把真实 dependency 换掉后，你失去了哪些 fidelity？**

例如把 SQLite 换成 dict：

你可能失去：

- transaction semantics；
- uniqueness constraints；
- filesystem errors；
- locking；
- schema migration behavior；
- SQL type coercion。

如果这次 test 只关心：

```text
business rule
```

可以接受。

如果这次风险恰恰是：

```text
transaction rollback
```

那这个 fake 就把最重要的东西 mock 掉了。

---

# 14. Fidelity：测试世界离真实世界多远

可以把 test 环境看成：

```text
fast / controlled / cheap
        ↑
        │
        │ trade-off
        ↓
realistic / high-fidelity / expensive
```

典型：

```text
pure unit
  ↓
in-process fake
  ↓
real SQLite in temp dir
  ↓
real process
  ↓
real network service
  ↓
production-like deployment
```

没有一个位置永远正确。

测试设计的问题是：

> **针对这条风险，最低需要多高 fidelity？**

---

# 15. Test Size 与 Test Scope 分开

这是一个非常有用的二维模型。

## Size

测试运行成本/资源：

```text
small → medium → large
```

可能受：

- process 数量；
- thread；
- disk I/O；
- network；
- external service；
- runtime；
- nondeterminism

影响。

## Scope

test 想验证多大范围：

```text
narrow component
  ↓
multiple collaborating components
  ↓
whole-system behavior
```

不要直接把：

```text
small == unit
large == e2e
```

当定义。

---

# 16. 为什么不教“测试金字塔答案”

你可能见过：

```text
        E2E
      Integration
    Unit Unit Unit
```

这个 intuition 有价值：

```text
越大通常越慢、越贵、越难诊断
```

但它不能告诉你：

- SQLite integration 要不要很多？
- compiler 项目应该怎么测？
- distributed protocol 怎么测？
- UI 组件必须 browser 才能验证怎么办？
- hardware driver 怎么办？

所以课程不用固定比例。

统一问：

```text
1. risk 是什么？
2. 哪个 boundary 会出错？
3. 什么 evidence 能观察它？
4. 最低需要什么 fidelity？
5. feedback cost 可以多高？
```

---

# 17. Coverage：一个被严重误用的数字

Line coverage 回答：

> “哪些行至少执行过？”

它没有回答：

> “执行后有没有 assert meaningful outcome？”

例如：

```python
def authorize(user):
    if user.is_admin:
        return True
    return False
```

测试：

```python
def test_authorize_runs():
    authorize(User(is_admin=True))
    authorize(User(is_admin=False))
```

可以覆盖 100%。

但没有 oracle。

你可以把实现改成：

```python
return True
```

test 仍通过。

所以：

```text
coverage = execution evidence
≠ semantic verification
```

---

# 18. Coverage 应该怎么用

好的用途：

> **帮助发现你甚至没执行过的区域，然后追问为什么。**

例如：

```text
error branch 从未覆盖
```

你应该问：

```text
这个 failure 是不可能发生？
还是我们没有 failure test？
```

coverage 是：

```text
gap detector
```

不是：

```text
quality KPI
```

---

# 19. Branch coverage 也不是充分条件

即使每个 branch 都走过：

```python
if x > 0:
    ...
else:
    ...
```

也可能遗漏：

- x = 1 边界；
- integer overflow；
- interaction with state；
- two branches 的组合；
- sequencing；
- concurrency。

更多 coverage 指标可以减少 blind spot，不能替代 semantic reasoning。

---

# 20. Mutation Testing：反过来问测试有没有牙齿

传统 coverage：

```text
test 有没有经过这段 code？
```

mutation testing：

```text
如果这里出现一个小而 plausible 的 bug，test 会失败吗？
```

例如原始：

```python
return retries < MAX_RETRIES
```

mutant：

```python
return retries <= MAX_RETRIES
```

如果 tests 全绿：

```text
surviving mutant
```

这通常说明：

- boundary case 没测；
- oracle 太弱；
- 这行可能根本不影响 observable behavior；
- 或 mutant 与原实现语义等价。

---

# 21. 不要追 Mutation Score

mutation testing 也可以被 Goodhart 化。

危险做法：

```text
mutation score 98% → 测试很好
```

问题：

- equivalent mutants；
- trivial mutants；
- 工具无法表达真正重要 failure；
- 为 kill mutant 写出无业务意义的 brittle test。

所以我们只把它用作：

> **“你说这组 tests 很强？那我放几个具体 bug 看看。”**

这是 diagnostic，不是宗教。

---

# 22. Regression Test：先证明 bug 真的存在

修 bug 的理想 workflow：

```text
1. reproduce
2. add regression test
3. prove test fails on old code
4. fix
5. prove test passes
```

这里非常重要的是：

```text
fail-before
```

因为 Agent 很容易写出一个新 test，然后告诉你：

> “测试通过，说明 bug 修复了。”

但它可能从来没验证过 test 能重现 bug。

这类 test 是最危险的“绿灯装饰”。

---

# 23. Agent 任务必须要求 fail-before evidence

对于 bug fix，可以明确要求：

```text
Before modifying production code:
- add or identify a regression test that fails on the current revision;
- show the failure and explain which contract it encodes.

After the fix:
- rerun exactly that test;
- run the relevant broader suite;
- show both results.
```

这个约束非常有效。

它让 Agent 不能只交：

```text
patch + green CI
```

而要交：

```text
counterexample + corrected behavior
```

---

# 24. Property-Based Testing：让工具帮你找没想到的输入

Example-based：

```python
assert sort([3, 1, 2]) == [1, 2, 3]
```

Property-based：

```text
对很多生成的 list：
  output 有序
  output multiset == input multiset
```

工具自动搜索反例。

关键变化：

```text
examples → properties
```

这直接依赖 M01 的 contract/invariant 能力。

---

# 25. 好 property 从哪里来

常见来源：

## 25.1 Round trip

```text
decode(encode(x)) == x
```

## 25.2 Reference implementation

```text
optimized(x) == slow_but_obviously_correct(x)
```

## 25.3 Invariant

```text
任何合法 job history 中：
terminal → not queued/running
```

## 25.4 Conservation

```text
输入元素 multiset == 输出元素 multiset
```

## 25.5 Idempotence

```text
normalize(normalize(x)) == normalize(x)
```

## 25.6 Metamorphic relation

你不一定知道绝对答案，但知道变换前后关系：

```text
f(permutation(x)) 与 f(x) 应满足某关系
```

---

# 26. Property-Based Testing 也可能制造假信心

如果你定义 domain：

```text
status ∈ {QUEUED, RUNNING}
```

但真实系统还有：

```text
FAILED, CANCELLED, SUCCEEDED
```

那 generator 永远找不到 terminal bug。

或者 property 写：

```python
assert len(result) >= 0
```

它几乎没信息量。

所以：

> **自动生成 input 不等于自动生成正确 oracle。**

稀缺的仍然是人定义的语义。

---

# 27. Shrinking 为什么重要

property-based tester 找到一个复杂 failure：

```text
[100, -30, 7, 7, 2, ...]
```

如果能 shrink 到：

```text
[0, 0]
```

debugging value 大幅提高。

这提醒我们：测试 evidence 不只要能失败，还要有：

```text
diagnostic value
```

一个 test suite 每次失败都只说：

```text
E2E failed
```

与一个精确指出 contract boundary 的失败，工程价值完全不同。

---

# 28. Flaky Test：错误的证据通道

flaky test：

```text
代码不变
有时 pass
有时 fail
```

它的问题不只是烦。

更深层是：

```text
fail signal 不再可信
```

工程师最终会学会：

```text
“再跑一次就行”
```

于是测试系统失去 authority。

这和 distributed system 里的 unreliable signal 很像。

测试基础设施本身也需要可信度。

---

# 29. 常见 flaky 来源

- wall clock；
- sleep-based synchronization；
- real network；
- shared global state；
- test order；
- random seed；
- filesystem race；
- process cleanup；
- eventual consistency；
- resource exhaustion。

解决方法不是：

```text
retry 5 次
```

而首先是：

> **找出 nondeterminism 属于 SUT contract，还是 test harness 泄漏。**

M07 会专门处理 concurrency/lifecycle testing。

---

# 30. Tests 也会成为 change amplification 来源

production refactor 5 行：

```text
30 个 tests 失败
```

如果 user-visible behavior 没变，这通常是信号：

```text
tests know too much
```

常见原因：

- direct test of private helper；
- exact internal call sequence；
- huge shared fixture；
- snapshot of irrelevant fields；
- mock every collaborator；
- hardcoded internal serialization；
- constructor plumbing copied everywhere。

测试不是天然“好债务”。

烂测试一样是 technical debt。

---

# 31. DAMP vs DRY：测试为什么可以重复一点

production code 很强调去掉 duplicated knowledge。

但 tests 的第一任务之一是让 reader 快速看到：

```text
given / when / then
```

如果为了 DRY，把 test 写成：

```python
run_case(CASE_17, MODE_B, flags=DEFAULT_EXCEPT_FOO)
```

你得跳 6 个 helper 才知道发生什么，维护成本可能更高。

所以 test abstraction 要问：

> **它是在去掉 irrelevant setup，还是把 scenario 意图藏起来了？**

适当 duplication 可以换 clarity。

---

# 32. Snapshot / Golden Test：什么时候有价值

适合：

- compiler pretty-printer output；
- generated UI tree；
- serialization format；
- complex textual report；
- CLI output。

它们可以用低成本保护 large observable surface。

但风险：

```text
expected snapshot changed
→ update snapshot
→ test green
```

如果 reviewer 没有真正理解 diff，snapshot 只是在记录新行为，不是在验证正确行为。

所以 golden update 本质上是一种 **contract review**。

不能自动 approve。

---

# 33. Testing Failure，而不只 Testing Happy Path

真实系统最危险的 behaviors 常常是：

- dependency timeout；
- disk full；
- permission denied；
- process killed；
- duplicate request；
- retry after partial side effect；
- malformed input；
- stale version；
- network partition。

如果你的 test portfolio 全是：

```text
正常输入 → 正常输出
```

它只覆盖了世界最配合你的那部分。

---

# 34. Failure injection 的设计原则

不要为了制造 failure 而把测试变成 flaky。

优先：

```text
controlled failure seam
```

例如：

```python
class FailingStore:
    def save(self, ...):
        raise DiskFull(...)
```

这能稳定验证：

```text
error translation / retry / rollback
```

然后再用高-fidelity integration test 验证真实 storage boundary。

---

# 35. Test Oracle 从哪里来

这是 testing 最深的问题之一。

oracle 可能来自：

1. explicit spec；
2. invariant；
3. previous compatible behavior；
4. reference implementation；
5. external standard/protocol；
6. product requirement；
7. domain expert judgment。

最危险的是：

```text
oracle = 当前 implementation 输出
```

这会产生 tautological test。

---

# 36. Agent 特别容易写出 tautological test

例如 production：

```python
def normalize_name(name):
    return name.strip().lower()
```

Agent 写 test：

```python
expected = name.strip().lower()
assert normalize_name(name) == expected
```

如果 implementation 里的 `.lower()` 本来就是 bug，test 会复制同一个 bug。

oracle 不独立。

好的 test 应该回到 contract：

```text
“用户名是否 case-sensitive？”
```

而不是抄实现。

---

# 37. Agent 测试的七种典型失败

## 37.1 Mirror implementation

把 production algorithm 在 test 里重写一遍。

## 37.2 Mock everything

所有真实 boundary 都被 fake 掉，最危险的 integration bug 永远不可见。

## 37.3 Assert existence, not semantics

例如：

```python
assert result is not None
```

但真正 contract 是复杂内容。

## 37.4 Coverage chasing

新增大量浅测试，只为把红色 coverage 行变绿。

## 37.5 Update tests to match patch

production 和 expected output 一起改，没有独立判断 contract 是否变了。

## 37.6 No fail-before evidence

bugfix test 从未证明能抓 bug。

## 37.7 Overfit hidden implementation

测试 private helper、exact calls、内部字段、日志顺序。

---

# 38. 给 Agent 的 Testing Task 应该怎么写

差的 prompt：

```text
给这个功能补充测试。
```

更好的 engineering spec：

```text
Goal:
Protect the documented cancellation contract.

Behavior partitions:
- queued job: cancellation succeeds and becomes CANCELLED;
- running job: cancellation is rejected and state remains RUNNING;
- terminal job: cancellation is rejected and terminal state is unchanged;
- unknown job id: preserve current error semantics.

Boundary constraints:
- test through service/worker public behavior;
- do not assert internal dict layout or helper call sequence;
- do not mock in-process TaskForge modules unless needed to inject a failure.

Evidence:
- explain why each case represents a distinct partition;
- for any regression bug, show fail-before and pass-after;
- identify at least one meaningful production mutant the suite should kill;
- run the focused tests and full suite.
```

这已经不是“写 tests”。

而是把 test design 本身 specification 化。

---

# 39. Test Review：不要只看 test 有没有 assert

review 一个 test PR 时问：

## Contract

- 这个 test 对应哪条 behavior / invariant？
- 这个 behavior 是真实 contract，还是 implementation accident？

## Oracle

- expected result 从哪里来？
- 是否独立于 production implementation？

## Partition

- 为什么选这些 case？
- boundary 呢？
- failure state 呢？

## Observability

- test 从 client 应该看到的 boundary 观察吗？
- 是否偷看内部 representation？

## Fidelity

- mock/fake 掉了什么？
- 被 mock 掉的东西恰好是不是风险来源？

## Maintenance

- harmless refactor 会不会炸一堆 tests？
- fixture/helper 是否把 scenario 隐藏了？

## Evidence

- bugfix 是否 fail-before？
- 是否有 plausible mutant 可以偷偷活下来？

---

# 40. TaskForge：重新审视现有 6 个 tests

现在看 baseline：

```python
assert first == "job-1"
assert second == "job-2"
```

问题：

> **“ID 精确使用 `job-N` 格式”是 contract 吗？还是 accidental representation？**

如果 client 对 job id 只要求 opaque + unique：

```text
UUID migration
```

会让这个 test 失败，但可能完全不应该。

这就是测试在悄悄定义 API。

---

# 41. 再看一个 test

```python
claimed = worker.claim_next()
assert claimed.id == first
```

它声明：

```text
queue 是 FIFO
```

这可能是合理 contract。

但如果产品从未承诺 scheduling order，那么它也可能是 implementation accident。

你必须先决定：

```text
TaskForge scheduler semantics 是什么？
```

再决定 test。

testing 强迫你暴露模糊 spec。

这是好事。

---

# 42. 测试设计经常是在做需求澄清

当你不知道下面哪个 test 正确：

```python
assert cancel(unknown_id) is False
```

还是：

```python
with raises(KeyError):
    cancel(unknown_id)
```

问题不是 pytest。

问题是：

```text
error contract 尚未定义
```

所以写 tests 的阻力经常暴露 API design 问题。

这也是为什么 tests 是很好的第一个 client。

---

# 43. 一组更完整的 TaskForge behavior table

示例：

| Context | Action | Expected claim |
|---|---|---|
| no jobs | submit | new observable queued job exists |
| multiple queued | claim | one eligible job becomes running |
| running + exit 0 | finish | succeeded + exit_code 0 |
| running + nonzero | finish | failed + exact exit code |
| queued | cancel | cancelled |
| running | cancel | rejected, state unchanged |
| terminal | cancel | rejected, state unchanged |
| caller reads job | mutate returned value | **must first decide whether read result is snapshot or authority-bearing handle** |

最后一行故意不直接给答案。

因为 test 应该编码 design decision，而不是替你发明 decision。

---

# 44. 什么时候应该先写 Characterization Test

legacy code 里，你可能根本不知道“正确 spec”。

但你需要先安全修改。

这时可以写：

```text
characterization test
```

目标不是说：

```text
当前行为永远正确
```

而是：

```text
先把当前 observable behavior 冻结出来，避免重构时无意改变未知语义
```

然后逐项调查：

- 哪些是 contract；
- 哪些是 bug；
- 哪些是 compatibility quirk。

M06 会深入。

---

# 45. Test 的寿命应该和 Contract 匹配

一个 stable API behavior：

```text
测试可能活 10 年
```

一个内部 migration helper：

```text
测试可能只活一个 release
```

一个 exploratory probe：

```text
可能根本不应该长期保留
```

不是所有 test 都必须永生。

删除过期 test 也是工程工作。

---

# 46. Testing 的成本模型

一个 test 的价值，不只是 bug-catching probability。

粗略可以看：

```text
value
≈ risk mitigated
× detection probability
× feedback timeliness
× diagnostic value
-
execution cost
-
maintenance cost
-
false-signal cost
```

不用计算数字。

但这个模型提醒你：

```text
更大、更真实、更多
```

都不是单调更好。

---

# 47. 为什么 fast feedback 是设计目标

如果 test suite：

```text
2 秒
```

开发者会频繁运行。

如果：

```text
45 分钟
```

他们会：

- 少跑；
- batch change；
- failure 更难定位；
- 偷偷跳过。

测试速度不是 cosmetic performance。

它改变整个 engineering feedback loop。

---

# 48. 但不要为了快把风险 mock 掉

极端：

```text
all tests = 0.1 sec
```

因为：

```text
DB mocked
filesystem mocked
RPC mocked
clock mocked
serialization mocked
```

你可能得到非常快的虚拟世界。

真正 production boundary 从未一起运行。

所以：

```text
speed 与 fidelity 必须组合设计
```

不是二选一。

---

# 49. 一个 risk-based test portfolio

假设 TaskForge 后续加入 SQLite。

你可能设计：

## Narrow + fast

验证：

- lifecycle rules；
- scheduling decisions；
- error mapping。

## Storage integration

真实 SQLite temp database：

- schema constraints；
- transaction behavior；
- serialization；
- migration。

## Process-level

真实 worker process：

- startup/shutdown；
- signal；
- crash recovery。

## End-to-end

少量：

```text
submit → persist → execute → observe terminal result
```

这不是因为 pyramid 规定。

而是每一层覆盖不同 risk。

---

# 50. 一个非常实用的测试设计模板

面对 feature/bug，写：

```text
Behavior / invariant:

Risk if broken:

Observable boundary:

Input/state partitions:

Boundary cases:

Failure cases:

Oracle source:

Minimum required fidelity:

What may be mocked/faked:

What must remain real:

Regression fail-before evidence:

Meaningful mutant / negative control:

Expected runtime / determinism:
```

这份模板远比：

```text
“unit tests + integration tests”
```

有信息量。

---

# 51. Negative Control：测试测试本身

科学实验会用 control。

software testing 也应该有类似思维。

如果你声称 test 能保护：

```text
nonzero exit code → FAILED
```

那么临时把 production 改成：

```python
job.status = SUCCEEDED
```

test 应该失败。

这就是一种 manual mutation / negative control。

它回答：

> **这个 test 的 fail path 真的存在吗？**

---

# 52. 为什么 Agent 时代更应该用 negative control

因为生成 tests 的成本几乎降为零。

Agent 可以瞬间生成：

```text
50 tests
```

人不可能逐个深读。

所以需要更 scalable 的质量检查：

```text
selected mutants
property-based search
fail-before
coverage gaps
independent review
```

不是相信数量。

---

# 53. “测试越多越安全”为什么可能是错的

大量 brittle tests 会让：

```text
每次 refactor 都有大量噪声
```

结果：

- 工程师不敢改；
- Agent 为了过测试保持坏 architecture；
- 每次真实 change 顺便 update 大量 expected values；
- reviewer 无法区分 semantic change 与 mechanical churn。

所以测试也需要设计成：

> **保护 contract，而不是冻结 architecture。**

---

# 54. M03 与前两章的关系

M01：

```text
什么 behavior / invariant 应成立？
```

M02：

```text
哪个 boundary 应隐藏什么？谁拥有 state？
```

M03：

```text
怎样建立 executable evidence，验证这些 contract，又不把内部实现误升级成 contract？
```

三章其实是一件事。

---

# 55. M03 与后续章节的关系

M04 API/error：

```text
error semantics 如何变成 behavior partitions
```

M05 Refactoring：

```text
哪些 tests 应该在 behavior-preserving change 后保持不变
```

M06 Legacy：

```text
characterization tests
```

M07 Concurrency：

```text
interleaving / lifecycle / cancellation tests
```

M08 Compatibility：

```text
old-client/new-server contract tests
```

M11 Production：

```text
测试 evidence 与 runtime evidence 如何互补
```

所以 M03 不是独立的 testing chapter。

它是全课的 evidence language。

---

# 56. Review Checklist

看到测试变更时，不要先数 tests。

问：

### Claim

- 每个 test 在保护什么 behavior？
- 这个 behavior 有来源吗？

### Oracle

- expected value 从哪里来？
- 是否只是复制 implementation？

### Partitions

- 正常/边界/失败/状态转换是否有系统划分？

### Boundary

- 是否从真实 client boundary 观察？
- 是否冻结内部 representation？

### Fidelity

- doubles 删除了哪些风险？
- 是否需要更高层验证？

### Maintainability

- harmless refactor 是否会导致无意义 failure？
- test 是否自解释？

### Strength

- regression 是否 fail-before？
- plausible bug 是否能被发现？

### Signal quality

- deterministic 吗？
- failure 能定位问题吗？

---

# 57. Agent Review Checklist

Agent 交测试时额外问：

- 有没有测试只是镜像 production implementation？
- 有没有所有 dependency 都 mock 掉？
- 有没有 assert 过弱？
- 有没有为了 coverage 加无语义测试？
- 有没有 production 和 expected 一起改？
- bugfix 有没有旧版本失败证据？
- 有没有偷偷测试 private helper？
- 有没有改现有 tests 来适配本应是 regression 的行为？
- 有没有一句“all tests pass”但没说明 tests 实际证明什么？

---

# 58. 本章 Lab

完成：

[`../labs/03-testing-evidence.md`](../labs/03-testing-evidence.md)

你会做五件事：

1. 审查现有 6 个 TaskForge tests；
2. 从 contract 设计 behavior partitions；
3. 用人工 mutants 检验 test suite 是否真的有牙齿；
4. 比较 behavior-oriented test 与 brittle implementation test；
5. 让 Agent 补测试，然后独立检查 oracle 和 fidelity。

不要先看 instructor reference：

[`../case-studies/m03/instructor-analysis.md`](../case-studies/m03/instructor-analysis.md)

---

# 59. 可选原始材料

本章自包含。想交叉检查来源时再读：

- MIT 6.102 Testing: https://web.mit.edu/6.102/www/sp26/classes/02-testing/
- Software Engineering at Google — Testing Overview: https://abseil.io/resources/swe-book/html/ch11.html
- Unit Testing: https://abseil.io/resources/swe-book/html/ch12.html
- Test Doubles: https://abseil.io/resources/swe-book/html/ch13.html
- Larger Testing: https://abseil.io/resources/swe-book/html/ch14.html
- Hypothesis: https://hypothesis.readthedocs.io/en/latest/tutorial/introduction.html
- mutmut: https://mutmut.readthedocs.io/en/latest/

详细来源审计：

[`../reading-notes/m03-source-audit.md`](../reading-notes/m03-source-audit.md)

---

# 60. 本章最终要记住什么

不是：

```text
unit test > integration test
```

不是：

```text
coverage ≥ 80%
```

不是：

```text
TDD / mocking / property testing / mutation testing
```

而是：

> **测试是一组可执行的工程声明。**
>
> **好的测试让错误的未来变化更难悄悄通过，同时尽量不阻碍正确的未来变化。**

最终你的测试设计应该能回答：

```text
What risk?
What claim?
What oracle?
What boundary?
What fidelity?
What evidence?
What does this still not prove?
```

只要最后一个问题还问得出来，你就还没有把 testing 变成宗教。
