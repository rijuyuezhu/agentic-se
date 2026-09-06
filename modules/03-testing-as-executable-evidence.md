# M03 — Testing：测试是可执行证据，不是宗教

M02 让我们看见一个很具体的 design bug：TaskForge 的 `service.get()` 返回 authoritative mutable `Job`，caller 因而可以绕开 lifecycle owner 直接改 status。更有意思的是，仓库原来的六个 tests 全部通过。

这给 M03 一个比“怎样写更多 pytest”更好的起点：**为什么一组真实、稳定、全绿的测试，完全没有阻止一个我们已经明确不想要的 behavior？**

答案不是“六个太少”。如果把同样六个测试复制一百遍，问题仍然存在。真正缺的是一条 executable claim：read boundary 不应把 authoritative mutation authority 交给 caller。

因此这一章把 testing 放回 software engineering 的主线里。我们不会问“unit test 还是 integration test 更高级”，也不会背一个 coverage 或 pyramid 比例。我们要学的是：面对 contract 和风险，怎样选择一组成本可接受的 observations 与 oracles，使错误的未来变化更难悄悄通过，同时尽量不阻碍合法的未来变化。

M03 的实验使用仓库里的 **TaskForge v0 baseline** 作为共同 negative control。它仍然保留 M02 已经分析过的 ownership defect。若你刚刚在自己的 M02 lab 分支里修过它，做 M03 的 fail-before exercise 时应从干净的 v0 revision/副本开始，而不是把个人前一章 patch 当成课程共享 baseline。这样每个 evidence claim 都能指向同一个可复现起点。

## 1. 六个绿灯实际声明了什么？

先看最朴素的一条：

```python
job_id = service.submit("echo hi")
assert service.get(job_id).status == JobStatus.QUEUED
```

它做了四件事：建立 scenario，执行 action，观察结果，再把 observation 与一个 expected result 比较。最后这部分通常叫 **oracle**：什么结果出现时，我们认为这次 execution 符合预期？

这里真正被执行的 claim 是：`submit(command)` 之后，通过当前 read boundary 观察到的 status 是 `QUEUED`。

如果系统还有另一条 contract——“caller 读到 job 后不应自动获得修改 authoritative state 的权限”——但任何 test 都没有观察这一点，那么 suite 全绿并不奇怪。tests 不会因为文件名叫 `test_...` 就自动理解未被表达的 requirement。

这也是 testing 最重要的边界：**test 是 executable evidence，不是 correctness 本身。** 两个 `abs()` example 通过，不能推出所有整数都满足 specification；同样，1000 个 TaskForge executions 通过，也不能证明你从未提出过的 property。

一个更完整的 correctness argument 可能同时包含：

```text
specification / protocol
+ type or static checks
+ tests
+ invariant reasoning
+ code review
+ runtime / production evidence
```

M03 只负责把 tests 这一类 evidence 用得更精确，而不是让它垄断“正确性”这个词。

### Oracle 的 authority 从哪里来？

expected result 不能凭空获得 authority。它可能来自 explicit specification、invariant、产品 requirement、external standard/protocol、已确认必须兼容的旧 behavior、reference implementation 或 domain expert judgment。

最危险的来源是直接令 **oracle = 当前 implementation 输出**。

例如 production 写成：

```python
def normalize_name(name):
    return name.strip().lower()
```

Agent 又在 test 里写：

```python
expected = name.strip().lower()
assert normalize_name(name) == expected
```

如果 `.lower()` 本来就是错误需求理解，implementation 和 test 会一起错。test 很精确，却没有独立 oracle。

所以 review 一个 test，第一问往往不是“assert 对不对”，而是：**这个 expected behavior 的 authority 是谁？**

## 2. 一个 test suite 的质量，更接近“它能区分什么”

MIT 6.102 在 testing reading 里把 suite 质量拆成 correctness、thoroughness 和 size。最有价值的不是背三个词，而是把 test suite 看成一个 **discriminator**。

设想有一组符合 contract 的 legal implementations，以及很多我们想排除的 buggy implementations。好的 suite 希望：合法实现不要因为 test 偷绑了 implementation detail 而被误杀；有意义的错误实现尽量不能偷偷通过；同时不靠堆大量重复 case 获得这种区分力。

TaskForge 原 tests 正好同时暴露了两种问题。

### 一边是 gap：重要错误可以通过

如果 `Job.terminal` 忘了 `CANCELLED`：

```python
return self.status in {SUCCEEDED, FAILED}
```

原 suite 仍可能全绿，因为它分别测试过 cancelled status，也测试过 succeeded job 会被 terminal metrics 计数，却没有连接 `CANCELLED -> terminal semantics` 这两个事实。

这不是“代码没执行到”的同义词，而是 oracle/partition 没有提出组合 claim。

### 另一边是 overspecification：合法变化会被误杀

原 test 还写：

```python
assert first == "job-1"
assert second == "job-2"
```

M02 lab 为了把 ownership refactor 隔离成单变量练习，曾**刻意把这个格式列入那次 change 的 Must preserve**。M03 lab 换了一个问题：它在后半段为本次 testing exercise 明确采用一份 TaskForge v0 contract，其中 ID 只要求在当前 lifetime 内 unique、stable、可作为 lookup token，并把具体格式视为 opaque。

这意味着同一行 assertion 的合理性取决于你正在保护哪一份 contract。对 M02 的局部 behavior-preserving exercise，它是有意 preservation constraint；对 M03 lab 后半段显式采用的 exercise contract，它就过度指定了 `job-N` representation。

这不是课程前后自相矛盾，而是一个很重要的工程事实：**局部 migration/refactor 可以暂时保留一组更强的 observable behavior，以减少一次 change 的变量；另一个有明确 authority 的 exercise 或 contract review 又可以采用不同的 contract scope。** 这并不自动决定产品最终应该承诺什么；不能做的是在没有说明 authority 的情况下悄悄切换。

M03 lab 因此会把 ID test 改为保护 distinct + stable lookup，而不冻结 prefix、numbering 或 serialization。相对于本 lab 采用的 contract，test 并没有变“弱”；它只是允许更多合法 implementation，同时继续拒绝 contract-breaking implementation。

## 3. 不要先想 example，先问 spec 把 state space 分成了什么

“再补几个 case”很容易变成拍脑袋。更可迁移的方法是从 specification 找 **behavior partitions**：哪些输入、系统状态或 failure condition 会改变 operation 的语义结果？

以 TaskForge v0 的 `finish(job_id, exit_code)` 为例，lab 给出的 contract 是：只有 `RUNNING` job 可以 finish；`exit_code == 0` 进入 `SUCCEEDED`，非零进入 `FAILED`，并保存 exact exit code。

于是至少有两类 dimension：

```text
job state:
  QUEUED
  RUNNING
  SUCCEEDED
  FAILED
  CANCELLED

exit_code:
  0
  negative nonzero
  positive nonzero
```

这里的“input”已经不只是函数参数。它还包括 operation 之前的 system state、lifecycle history、dependency behavior，后续还会包括 concurrency interleaving、version/compatibility state 等。

这也是 M01 state/model reasoning 对 testing 的直接影响：**如果 contract 依赖两个 state dimension，test partition 也不能偷偷只看其中一个。** 某个 artifact 若只投影 public status，就明确它没有覆盖额外 durable flag 或其他 execution/recovery state；不要靠读者猜 omitted dimension 是不存在还是没测。

### Boundary value 为什么高信息量？

很多 bug 聚集在行为区域的边缘：`<` 与 `<=`、empty/non-empty、0/nonzero、first/last、before/after timeout、first/last retry、old/new version、transition 前后。

所以如果 rule 是：

```python
retries < MAX_RETRIES
```

相比随便测 `retries = 2`，`MAX_RETRIES - 1 / MAX_RETRIES / MAX_RETRIES + 1` 往往更有区分力。

但不要把 partition 机械做成笛卡尔积。TaskForge `5 个 states × 3 个 exit-code classes` 不意味着必须写 15 个 almost-identical tests。要问的是：哪些组合真的触发不同 contract outcome？哪些 case 能低成本排除一类 plausible bug？

可以把目标叫作 **high-information suite**：case 数量不是越少越好，而是每个 case 都有理由。

### Scenario、Claim、Mechanism 分开想

写 test 时一个很实用的分层是：

```text
scenario  ->  现实中发生了什么？
claim     ->  我们究竟要保护哪条语义？
mechanism ->  用 pytest / fake / Hypothesis / fixture 怎样执行？
```

如果一上来先问“我要不要 mock”，通常已经跳过了最重要的两层。

## 4. Test behavior，而不是把 production method 做成目录

按方法名组织测试很自然：有 `submit()`，就写 `test_submit()`。问题是这个 test 很快会同时检查 ID、queue、command、metrics、persistence、logging，最后变成一个 100 行的“方法说明书”。

更稳定的单位通常是 behavior：

```python
def test_submit_queues_new_job(): ...
def test_submit_preserves_command(): ...
def test_cancelled_job_counts_as_terminal(): ...
def test_running_job_cannot_be_cancelled(): ...
```

一个 method 可以实现多个 behavior，一个 behavior 也可能跨多个 methods。`submit -> claim -> finish` 整条 lifecycle 有时才构成 meaningful scenario。

Google 的 unit-testing materials 用“test behaviors, not methods”表达了同一方向。它的长期维护意义在于：production decomposition 可以变化，只要 stable behavior 没变，相关 test 理想上不需要跟着每次移动 helper。

### “通过 public API 测”不是 Python visibility 规则

真实问题是：**这个 unit 对它的 client 承诺的 semantic boundary 在哪里？**

如果 package 内部有 `service.py / storage.py / codec.py / helpers.py`，而真实 client 只使用 `service.submit()` 与 `service.get()`，那么大量测试 `helpers._serialize_job()` 的 exact internal string 可能在冻结 implementation。

但一个 internal parser、scheduler 或 codec 如果本身就是稳定 semantic component，当然可以有直接 unit contract。是否值得直接测试，不由名字前有没有 underscore 决定，而由你是否准备长期维护那个 boundary 决定。

这就是 M02 的 abstraction judgment 在 M03 的第一个直接用途：**test boundary 取决于 architecture boundary。**

## 5. Interaction test 的问题不是“用了 mock”，而是你在保护什么

假设业务要求 `create_user("alice")` 后 user 可被读到。一个 test 写：

```python
mock_db.put.assert_called_once_with("alice")
```

它保护的是当前 collaborator choreography。另一个 test 从 client boundary 观察：

```python
create_user("alice")
assert get_user("alice") is not None
```

它更直接保护 final outcome。

如果 implementation 从 `db.put(...)` 改成 transaction API，真实 behavior 不变，但前一个 test 失败，那么 test 已经把“调用某个 helper exactly once”升级成 accidental contract。

Google 的 unit-testing materials 因此偏向 observable state/outcome，而不是内部 interaction。但这不是“interaction testing 永远错”。如果 operation 的真实 contract 本来就是 external side effect，例如：

```text
向 payment gateway 发 charge request
写一条 audit event
向 remote worker 发 cancellation request
```

interaction 本身就是 observable obligation。此时需要验证的是 **external protocol semantics**：发送了什么、何时发送、允许几次、失败怎样解释，而不是 private helper 的调用顺序。

这个 distinction 后面会和 M04 的 idempotency、M07 的 cancellation/concurrency、M11 的 runtime evidence 连接起来。

## 6. Test double 是用 control 换 fidelity；先问你模拟掉了什么

fake、stub、spy、mock 的名词差异不是 M03 的考试重点。更重要的是：把真实 dependency 换掉以后，哪些 risk 从测试世界里消失了？

把 SQLite 换成 dict 可能让 test 更快、更 deterministic，也可能同时丢掉：transaction semantics、uniqueness constraint、filesystem errors、locking、schema/migration behavior、SQL type coercion。

如果本次只想隔离 lifecycle business rule，这种 fidelity loss 可能完全合理；如果要验证的风险就是 transaction rollback，dict fake 恰好把最重要的东西删掉了。

因此 test design 不应从“unit/integration/e2e 选哪一个”开始，而可以从一条更直接的链开始：

```text
risk
  -> desired observable evidence
  -> minimum sufficient fidelity
  -> feedback / maintenance cost
```

Google 的 larger-testing materials 很有价值的一点是把 fidelity 看成连续变量。你可以有 pure in-process test、真实 SQLite temp DB、真实 process、真实 network service、production-like deployment；没有一个层级天然更高级。

### Test size 与 scope 是两个维度

Google 还把 **size** 和 **scope** 分开。size 更接近运行资源/成本：process、thread、disk、network、外部 service、runtime、nondeterminism；scope 则是 test 想验证多大范围的 collaborating behavior。因此 **small 不等于 unit，large 也不等于 end-to-end**。

一个 narrow test 可能因为真实 device/browser 而不 small；一个 broad-scope in-process simulation 也可能很快。

这也是为什么本课程不教固定 test-pyramid 比例。Google 自己给出的比例也是 rough guideline，并明确不同团队会因 architecture 和风险而调整。我们吸收的是 reasoning，不复制组织政策。

### Failure injection 是 double 的高价值用途

有些 failure 在真实系统里很难稳定制造，例如 disk full、permission error、timeout、partial response。一个受控 seam：

```python
class FailingStore:
    def save(self, ...):
        raise DiskFull(...)
```

可以把 failure 变成 deterministic input，精确测试 error translation、rollback 或 retry policy。随后再用更高 fidelity test 检查真实 storage boundary。

关键是别让“模拟 failure”本身制造 flaky nondeterminism。

## 7. Coverage 只能告诉你“走过”，不能告诉你“看见了什么”

考虑：

```python
def authorize(user):
    if user.is_admin:
        return True
    return False
```

一个 test 只是调用 admin 和 non-admin 两条路径，却没有任何 meaningful assert，line/branch coverage 仍然可能很高。把 implementation 改成恒 `True`，suite 甚至可能继续绿。

所以 coverage 提供的是 **execution evidence**，不是 semantic verification。一个 percentage 不会告诉你 expected result 是否正确、important state partition 是否被覆盖、interaction 是否 fake 掉了真实 risk。

这不等于 coverage 没用。它很适合作为 **gap detector / question generator**：某个 error branch 从未执行，就追问这个 failure 是否不可能，还是我们根本没设计 failure test。

更多 coverage 维度可以减少 blind spot，不能替代 contract reasoning。把 coverage 设成 KPI 以后，还可能诱导人或 Agent 为“让红行变绿”增加没有 oracle 的浅测试。

## 8. Mutation / negative control：反过来测试“测试有没有牙齿”

如果 coverage 问“有没有经过这里”，mutation testing 更接近另一个问题：**这里出现一个小而 plausible 的 bug 时，suite 会不会叫？**

例如：

```python
return retries < MAX_RETRIES
```

临时改成：

```python
return retries <= MAX_RETRIES
```

如果所有 tests 仍绿，可能说明 boundary 没测、oracle 太弱，也可能说明这个 mutant 对 observable behavior 等价。mutation result 仍然需要解释。

M03 lab 不依赖完整 mutation framework，而是提供六个语义明确的人工 mutants。TaskForge v0 的原始六个 tests 实际得到：

```text
KILLED   finish_reverses_success_rule
KILLED   cancel_reports_success_without_transition
KILLED   claim_uses_lifo
SURVIVED terminal_forgets_cancelled
SURVIVED submit_drops_command
SURVIVED list_jobs_hides_terminal
```

三个 survivor 分别揭示三种 gap：terminal semantics 没覆盖 cancelled；submission 没有观察 command preservation；listing 只在“全是 active”这个 state partition 下被观察，所以“all jobs”和“only active jobs”对现有 oracle observationally equivalent。

这时最差的反应是直接为每个 mutant 写一个 implementation-specific assertion，只求 score 变成 100%。更好的问题是：**这个 mutant 破坏了哪条真实 contract？最小有信息量的 scenario 是什么？应该从哪个 boundary 观察？**

例如 command survivor 可以从 public lookup 检查 input command 被完整保留；terminal survivor 可以走 `submit -> cancel -> terminal_count`，而不是默认直接测试 `Job.terminal` implementation；listing survivor 需要构造 terminal + active 的 mixed-state scenario。

Instructor reference 实际验证过：加入三条这样的 behavior-oriented tests 后，普通 suite 从 6 变成 9 个通过，提供的 6 个 mutants 全部被 kill。

这仍然不是 completeness proof。它只说明六个 selected fault hypotheses 现在被 suite 区分。read-authority leak、unknown-ID semantics、concurrent claim、persistence、crash、retry、remote protocol 等风险仍然没有由这六个 mutants 表达。

### Negative control 不需要正式 mutation framework

对于一次具体 bugfix，你也可以临时制造一个与 claim 相反的小改动，确认 test 确实失败。例如你声称 test 能保护“nonzero exit code -> FAILED”，就临时让 production 把非零 exit 也写成 `SUCCEEDED`。test 应该红。

这种 negative control 回答的是：**这条 evidence channel 的 fail path 真的存在吗？**

Agent 生成 test 的成本越低，这个问题越重要。50 个绿色 tests 的数量可以瞬间生成，但 selected mutants、fail-before、property-based counterexample search 和 independent review 能更 scalable 地检查它们是否真正有 discrimination ability。

## 9. Bugfix 最有价值的证据之一，是 fail-before -> pass-after

现在回到 M02 的 representation exposure：

```python
job = service.get(job_id)
job.status = JobStatus.SUCCEEDED
```

如果我们已经把“read 不授予 authoritative mutation authority”确定为 M03 lab contract，那么 oracle 必须允许两种结果：read-only observation 可以拒绝 caller 的 mutation attempt；writable observation 也可以接受本地修改，但修改不能穿透到 authoritative state。一个保持这两种实现都合法的 regression test 可以写：

```python
job_id = service.submit("echo hi")
observed = service.get(job_id)

try:
    observed.status = JobStatus.SUCCEEDED
except Exception:
    # 本 lab contract 允许 read-only observation 拒绝 mutation。
    pass

assert service.get(job_id).status == JobStatus.QUEUED
```

这里 `except Exception` 只包住一次故意的 mutation probe，不是在建议测试代码普遍吞掉异常。之所以不检查 `FrozenInstanceError`、`AttributeError` 或其他特定类型，是因为 M03 contract 没有规定“拒绝修改时必须怎样报错”。如果未来 public contract 明确承诺某个 exception type，再为那条更强的 promise 单独写 test。

在 v0 baseline 上，assignment 会成功并直接改 authoritative object，因此最后一条 assertion **必须先失败**。对 defensive snapshot，assignment 可以成功但只改本地副本；对 immutable `JobView`，assignment 可以被拒绝。两种情况下 authoritative status 都保持 `QUEUED`，所以同一条 regression test 都应通过。

然后才比较 fix。例如一种最小 candidate 是 read API 返回 defensive snapshots；另一种是把 internal mutable entity 与 external immutable `JobView` 分开。两种都可能满足 property，但有不同 trade-off：change size、type clarity、nested mutable fields、performance、API compatibility、future persistence。

注意 design-decision dependency：**M03 的 testing chapter 不应该因为写 regression test，就偷偷决定 observation 必须 writable，或 immutable `JobView` 永远是唯一 architecture。** test 保护的是 isolation property；copy、frozen projection 或别的实现都应属于 legal implementation set，只要 contract 没要求更强的 identity/type/mutation-attempt semantics。

实现 candidate fix 后，再保存三层 evidence：focused regression 由红变绿；相关 full suite 仍绿；mutation probe 没有因为修 ownership 而失去已有 discrimination。Instructor case study 已经在临时副本实际验证 defensive snapshot candidate 的 red -> green；这轮又额外验证同一个 oracle 接受 immutable view candidate。两种 candidate 仍各自保留 limitation，而不是因为 test 通过就升级成永久终局。

这也是为什么“all tests pass”通常是太弱的 bugfix summary。它没有告诉 reviewer 新 test 是否曾经能抓住旧 bug，也没有说明哪个 contract 被保护。

## 10. Property-based testing：把“想 example”进一步推成“定义 domain + property”

Example-based test 最大的限制之一是：你通常只测试自己想得到的输入。Property-based testing 把工作重心改成：定义 input domain，定义对整个 domain 应成立的 property，让工具搜索反例，再把失败 example shrink 成更容易理解的 case。

TaskForge 一个合适的 property 是：对任意非零 integer exit code，running job finish 后都应 `FAILED`，并保存 exact exit code。这里 property 的 authority 来自 completion contract，generator domain 则必须明确排除 0。

Hypothesis 可以帮你覆盖大量正/负非零值，并在失败时 shrink counterexample。但它没有自动解决 oracle problem。你完全可以写错 property，也可以把 generator domain 错误限制成 `{QUEUED, RUNNING}`，于是工具永远见不到 terminal-state bug。

所以 property-based testing 更像 **counterexample search engine**，不是自动证明。

常见 property 来源包括 round-trip、reference implementation equivalence、invariant、conservation、idempotence、metamorphic relation。它们仍然要回到 domain semantics：为什么这个 relation 应该成立？

Shrinking 也提醒我们 evidence 不只要“能失败”，还要有 diagnostic value。一个巨大的 generated case 如果最终能缩成最小反例，debugging 成本会明显下降；相反，一个 whole-system test 每次只报 `E2E failed`，即使 fidelity 很高，也可能很难定位哪条 contract 被破坏。

## 11. Test 本身也会制造 change amplification

如果 production refactor 只改了几行，真实 observable behavior 没变，却有几十个 tests 因 private helper、exact call sequence、internal serialization 或 snapshot noise 全部失败，那么 test suite 已经成为 architecture coupling 的一部分。

Google 的 unit-testing materials 把 maintainability 放得很重，因为 tests 也是长期资产。一个非常好用的 review question 是：

> 如果这条 test 因未来 refactor 失败，真实 user/client 也应该认为 contract 被破坏吗？

答案不必永远是 yes——internal component 可以有自己的 contract——但如果长期总是 no，就值得怀疑 test 绑错了 boundary。

### DAMP 与 DRY：测试有时宁可重复一点

production code 里 duplicated knowledge 往往危险；test code 的另一个目标却是让 reviewer 不跳六层 helper 就能看懂 scenario。

```python
run_case(CASE_17, MODE_B, flags=DEFAULT_EXCEPT_FOO)
```

可能非常 DRY，却把 Given/When/Then 中真正重要的区别藏起来。适当 duplication 可以换来 clarity。问题不是“test 永远不 DRY”，而是 abstraction 删除的是 irrelevant setup，还是删除了 scenario 的语义线索。

### Snapshot / golden test 的更新本质上也是 contract review

compiler output、CLI report、serialization、复杂 UI tree 这类大 observable surface 很适合 snapshot/golden test。风险是形成“snapshot changed → approve new snapshot → green”的机械循环。

如果 reviewer 没理解 diff，test 只是记录了新 behavior，并没有判断它是否正确。因此 golden update 不是机械操作，而是一次对 expected behavior authority 的 review。

当前 M03 source audit 没有选一份单一材料来建立“snapshot 必须/禁止”的规则，因此这里只保留适用场景与 brittleness limitation，不把它升级成 universal policy。

## 12. Flaky test 会破坏 evidence channel 的可信度

flaky 的深层问题不是“偶尔烦人”，而是同一 code revision 有时 pass、有时 fail，导致 fail signal 不再可信。团队最终学会“再跑一次”，测试系统就逐渐失去作为 evidence channel 的 authority。

常见来源包括 wall clock、sleep-based synchronization、real network、shared mutable global、test order、random seed、filesystem race、process cleanup、eventual consistency 和 resource exhaustion。

修复时先问 nondeterminism 属于哪里。如果系统 contract 本来就允许 eventual completion，test 需要观察正确的 temporal condition；如果只是 harness 用 `sleep(0.1)` 猜 timing，就应该修 harness。简单 retry 五次可能降低红灯频率，却没有恢复证据可信度。

M07 会把 concurrency/lifecycle 的 deterministic testing 和 failure timing 展开；M03 只先建立一个原则：**signal quality 本身就是 test design 的一部分。**

### Test 的寿命应该和 contract 匹配

稳定 public behavior 的 test 可能活很多年；一次 migration helper 的 test 可能只需要覆盖一个 release；exploratory probe 甚至不一定应该长期保留。删除已经失去 contract 对象的 test 也是维护工作。

因此“tests 越多越安全”并不成立。大量 brittle、过期或低信号 tests 会让工程师和 Agent 为了继续绿灯而保留坏 architecture，或在每次合法 change 时制造大量 mechanical churn。

## 13. 把 feedback speed 与 fidelity 放进同一张成本图

快 test 很重要。2 秒的 suite 会被频繁运行，45 分钟的 suite 会促使开发者 batch changes、少跑、甚至跳过，从而降低 feedback timeliness 和 failure localization。

但不能为了快，把 DB、filesystem、RPC、clock、serialization 全部 mock 掉，最后只剩一个 0.1 秒的虚拟世界。speed 和 fidelity 不是二选一，而是针对不同 risk 组合设计。

可以用一个不需要数字化的粗模型提醒自己：test value 受 risk mitigated、detection probability、feedback timeliness、diagnostic value 提升，也会被 execution cost、maintenance cost 和 false-signal cost拉低。

这不是要求计算分数。它只是在阻止“更大、更真实、更多 tests”被误解成单调更好。

例如未来 TaskForge 加 SQLite 后，一个合理 portfolio 可能同时有：

- narrow/fast tests 保护 lifecycle 与 policy；
- 真实 SQLite temp DB tests 保护 schema、transaction、serialization、migration；
- process-level tests 保护 startup/shutdown、signal、crash recovery；
- 少量 end-to-end scenarios 保护 `submit -> persist -> execute -> observe terminal result`。

每一层存在的理由是它覆盖不同 risk，不是 pyramid 要求某个固定比例。

## 14. Tests 也会逼你承认 specification 还没决定

TaskForge 里有一条原 test：

```python
claimed = worker.claim_next()
assert claimed.id == first
```

M03 lab 明确把 FIFO 当作 v0 contract，因此这条 assertion 合理。如果产品从未承诺 scheduling order，同一行就可能只是把 dict insertion order 固化成 public promise。

再看 unknown ID：

```python
assert cancel(unknown_id) is False
```

还是：

```python
with raises(KeyError):
    cancel(unknown_id)
```

如果我们不知道哪个正确，问题不在 pytest，而在 error contract 尚未定义。testing 的阻力经常暴露 specification gap；test 是第一个严格 client，它会逼你把一句“应该差不多这样”变成 observable decision。

这也是为什么 characterization test 需要单独理解。在 legacy code 中，可能还不知道 current behavior 是 contract、bug 还是 compatibility quirk。先冻结一部分 observable behavior 可以帮助安全修改，但它不是宣布“现状永远正确”。M06 会专门处理如何从 characterization 继续调查 authority。

## 15. 给 Agent 的 Testing Task，先给 claim space，不要只给“补测试”

Agent 特别容易产出看起来很完整的 test patch：每个 method 一个 test、所有 dependency 都 mock、expected 复制 implementation、参数化很多 cases、coverage 变高，最后总结 “all tests pass”。这些不一定是模型能力问题；模糊任务本来就没有告诉它什么 evidence 才有价值。

一个更好的任务 artifact 可以保持结构化，因为它本来就是执行协议：

```text
Goal
- protect the documented behavior, not the current decomposition

Contract / risk
- list the behavior or invariant each test should protect
- identify ambiguous semantics before choosing an oracle

Partitions
- normal, boundary, lifecycle, failure and repetition states that change outcomes
- do not expand irrelevant Cartesian products

Boundary
- observe through the intended client boundary
- do not freeze internal dict/layout/helper choreography unless that is the explicit contract

Fidelity
- explain every fake/mock and which real risks it removes
- keep real the boundary whose failure semantics are under test

Evidence strength
- for a bugfix, show fail-before before modifying production code
- after the fix, rerun the focused test and relevant broader suite
- use at least one meaningful mutant/negative control when useful

Limits
- state what the tests still do not prove
```

这个 artifact 的价值不在 prompt 更长，而在于它把 oracle authority、behavior partitions、boundary、fidelity 和 completion evidence 先变成可 review 的对象。

M03 lab 还会让你做 vague prompt 与 engineering-spec 两轮对照。评分不奖励“多生成了多少 tests”，而看 meaningful behaviors、implementation coupling、mutants、false contracts、review time 和 remaining-risk analysis。

### Agent-generated test 的独立 review

无论 test 是人写还是 Agent 写，reviewer 都应重新问：

- expected 是否从 production algorithm 抄来？
- assertion 是否只证明 result 存在，而没证明 semantics？
- dependency 是否全被 mock，恰好吞掉真正 risk？
- 是否为了 coverage/mutation score 加无业务意义 case？
- production 与 expected 是否一起改，却没有独立 contract decision？
- regression 是否真的在旧 revision 上失败过？
- 是否测试了 private decomposition 或 accidental representation？

“Agent 写的”本身不应该成为 finding；问题必须落在具体 contract、oracle、boundary 或 evidence defect 上。M10/M12 会继续把这个 review discipline 扩展到完整 change workflow。

## 16. 一个可复用的测试设计记录

面对 feature 或 bug，不需要每次写长文，但下面这张表能迫使关键 reasoning 显式化：

```text
Behavior / invariant:
Risk if broken:
Oracle source / authority:
Observable boundary:
Input + state partitions:
Boundary cases:
Failure / repetition / temporal cases:
Minimum required fidelity:
What may be faked:
What must remain real:
Regression fail-before evidence:
Meaningful mutant / negative control:
Expected runtime / determinism:
Remaining risks:
```

这里最后一行不能省。一个 test suite 无论多强，都只能对它表达过、观察得到的风险提供 evidence。

这也给出一套更紧凑的 review 顺序：

### Claim / oracle

- 每个 test 保护哪条 behavior 或 invariant？
- expected 的 authority 从哪里来？
- 有没有 implementation mirror？

### Partition / boundary

- 哪些 state、boundary、failure、repetition distinction 会改变 outcome？
- test 从真正 client boundary 观察，还是偷看 internal representation？
- 某个 state model 若只是 projection，scope 是否明确？

### Fidelity / maintainability

- doubles 移除了哪些现实风险？
- harmless refactor 会不会产生大量无意义 failure？
- helper/fixture 是减少 noise，还是隐藏 scenario？

### Strength / signal

- bugfix 是否有 fail-before？
- plausible wrong implementation 能否偷偷通过？
- test deterministic 吗？failure 有诊断价值吗？

这比“有多少 unit/integration tests、coverage 几成”更接近工程判断。

## 17. TaskForge Lab：把一条证据链实际跑出来

完整实验在 [`../labs/03-testing-evidence.md`](../labs/03-testing-evidence.md)。它不是让你“把 6 tests 补到 20 个”，而是让你把一条 reasoning chain 跑完整：

```text
明确 v0 contract
  -> audit 当前 tests 实际 claims
  -> 设计 behavior partitions
  -> 运行 selected mutants
  -> 解释 survivor 为什么 observationally equivalent
  -> 用 behavior-oriented tests kill meaningful gaps
  -> 审查 ID overspecification
  -> 为 representation exposure 建立 fail-before
  -> 比较至少两个 fix candidate
  -> pass-after + full-suite + mutation evidence
  -> 列 remaining risks
```

Instructor reference 在 [`../case-studies/m03/instructor-analysis.md`](../case-studies/m03/instructor-analysis.md)。它不是“标准答案 dump”，而是用真实 mutation output、red/green reproduction 和两个 ownership fix candidate 校验 lab 本身是否 grounded。

特别注意三个边界：

1. `6/6 supplied mutants killed` 只覆盖这六个 fault hypotheses，不是 mutation completeness proof；
2. defensive snapshot 是当前 toy system 的一个小 candidate，必须保留 shallow-copy 等 limitation，不升级成唯一 architecture；
3. M03 lab 后半段采用的 opaque-ID contract 是本次 testing exercise 的明确 authority，不 retroactively 声称 M02 那个单变量 refactor 当时“做错了”，也不替未来产品 contract 做最终决定。

## 18. 与后续章节的关系：M03 是全课的 evidence language

M01 训练“什么 behavior / invariant 应成立”；M02 训练“哪个 boundary 隐藏什么、谁拥有 state”；M03 则训练“怎样用 executable evidence 验证这些 contract，同时不把内部 implementation 错误升级成 contract”。三章其实是一条连续链。

后面每一章都会复用它：

- M04 把 error、unknown outcome、idempotency 变成 behavior partitions；
- M05 问 behavior-preserving refactor 后哪些 tests 理应保持；
- M06 用 characterization 建立 legacy feedback；
- M07 把 interleaving、lifecycle、cancellation、crash timing 变成 evidence；
- M08 做 old/new version compatibility tests；
- M11 把 pre-production tests 与 production telemetry/evidence 放在一起；
- M12 要求 Agent 的 test/evidence 同样接受独立 review。

尤其是 temporal consistency：如果某个 contract 明确区分 acceptance、completion、recovery，tests 也必须分别验证对应 phase。不能因为 downstream completion 失败，就把此前已经按 contract 成功的 acceptance test 改写成“其实失败”；也不能用只观察最终 terminal state 的 test 冒充 acceptance durability evidence。M01 已经用 cancellation candidate 展示过这一点，后续章节会继续复用。

到这里，testing 可以压缩成一句不太像口号、但足够可操作的话：

> **测试是一组可执行的工程声明。好的测试让我们关心的错误变化更难悄悄通过，同时尽量不给合法变化制造 accidental contract。**

真正完成 test design 时，你应该能回答：

```text
What risk?
What claim?
What oracle authority?
What state/behavior partition?
What boundary?
What fidelity?
What negative control?
What evidence phase?
What does this still not prove?
```

只要最后一个问题仍然问得出来，testing 就还没有被变成宗教。

### 可选原始材料与来源边界

本章 source mapping 与限制见 [`../reading-notes/m03-source-audit.md`](../reading-notes/m03-source-audit.md)。主干使用：

- MIT 6.102 Testing：systematic partitioning、boundary values、suite correctness/thoroughness/size，以及 testing 只是 validation 方法之一；
- *Software Engineering at Google* Testing Overview / Unit Testing / Test Doubles / Larger Testing：change enablement、behavior-oriented tests、size vs scope、coverage limitation、double fidelity 与 risk-based larger testing；
- Hypothesis 官方文档：domain/property/counterexample search/shrinking；
- mutmut 官方文档只校准 mutation-testing workflow 与工具 limitation，主实验仍使用课程自己挑选、语义明确的人工 mutants。

这些来源都不支持把 strict TDD、固定 test-pyramid 比例、100% coverage、mock-everything/mock-nothing 或 mutation percentage 写成 universal rule。Google 的经验来自大型统一基础设施；课程采用的是 reasoning，不复制其组织 policy。Hypothesis 也被当作 property-based testing 的强力补充，而不是自动证明或所有 example tests 的 replacement。