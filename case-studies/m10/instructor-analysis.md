# M10 Instructor Reference — 这份“9 passed” Agent PR 为什么不能直接 merge

> Spoiler warning：先完成 `labs/10-code-review-change-engineering.md` 的 first-pass review，再读本文件。

---

# 1. 结论先行

Candidate PR 的 architecture direction 是合理的：

```text
service / worker / metrics / audit
        ↓
    JobAuthority
        ↓
    in-memory state
```

它符合 M09 的核心方向：先建立 deployment-neutral semantic authority boundary，而不是提前引入 RPC/database/queue。

但是当前 candidate **不能 merge**。

我会给：

```text
Request changes
```

主要有两个 root-cause blocker：

1. `sorted(state.jobs)` 把现有 **submission-order / FIFO** semantics 偷换成 lexical job-ID order；
2. unknown cancel 从 `KeyError` 改成 `False`，与“behavior-preserving / no public behavior change”的 change contract 冲突。

其中第一个 root cause 同时造成：

- list ordering regression；
- scheduler FIFO regression；
- snapshot exported ordering change；
- legacy audit ordering change。

不要把这些 symptoms 写成四个互不相关 blocker。

---

# 2. 为什么不能因为这是“教学坏 PR”就直接 Request Changes

本实验不允许：

```text
“老师肯定藏了 bug，所以我 request changes。”
```

review 必须从 reviewer brief 和 baseline contract 推导。

Reviewer brief 说：

```text
structural / architecture-enabling refactor only
existing behavior unchanged
scheduling unchanged
snapshot compatibility unchanged
M07 fault-injection artifact out of scope
```

因此最重要的 proof obligations 是：

```text
A. authority 真正被 localize
B. old semantics 继续成立
```

Candidate 在 A 上大体成功。

在 B 上失败。

---

# 3. Author CI 为什么绿

Candidate 新增三个 tests，加原 6 个 baseline：

```text
9 passed
```

实际已验证。

`tools/m10_review_case.py` 会在临时树里 apply patch 并运行 author test suite：

```text
[AUTHOR CI]
......... [100%]
author-supplied CI is green
```

所以不能把问题归咎于：

```text
作者根本没跑 tests
```

真正问题是：

> **tests 对这次 change 的 semantic risk partition 不够强，而且其中一个新 test 直接把错误的新行为写成了 oracle。**

---

# 4. Finding 1 — `sorted(job_id)` 不是 submission order

Candidate `JobAuthority.list_jobs()`：

```python
return [state.jobs[job_id] for job_id in sorted(state.jobs)]
```

Candidate `claim_next()`：

```python
for job_id in sorted(state.jobs):
```

作者 comment：

```text
Stable ordering makes downstream output deterministic.
```

这句话看起来非常合理。

但是 baseline 的 insertion order 本来就是 deterministic。

更重要的是，M03 明确将以下作为本实验的 contract：

```text
list_jobs preserves submission order
claim_next is FIFO among queued jobs
```

所以 reviewer 必须问：

```text
job ID lexical order == submission order ?
```

答案只在一小段输入区间里碰巧是 yes。

---

# 5. 为什么原 tests 看不见

原 test：

```python
first = service.submit(...)
second = service.submit(...)
assert list_ids == [first, second]
```

Candidate 新 test 也是：

```text
2 jobs
```

对于：

```text
job-1
job-2
```

lexical order 与 numeric/submission order 一致。

甚至到：

```text
job-9
```

都没有暴露问题。

真正 boundary 在：

```text
job-10
```

最小高信息量 partition 是：

```text
IDs cross a digit-width boundary
```

而不是“随机多跑几个 job”。

---

# 6. 最小反例

创建 12 个 queued jobs：

```text
job-1
job-2
...
job-12
```

Candidate `list_jobs()` 实际输出：

```text
job-1
job-10
job-11
job-12
job-2
job-3
...
job-9
```

所以：

```text
expected submission order
!=
observed lexical ID order
```

`claim_next()` 更严重。

第一次：

```text
job-1
```

第二次按 lexical order 扫 queued jobs：

```text
job-10
```

而 FIFO contract 要求：

```text
job-2
```

Actual reviewer probe：

```text
expected: [job-1, job-2]
observed: [job-1, job-10]
```

---

# 7. 这是一个 root cause，不是两个独立 bugs

可以写成：

```text
Blocker — lexical ID sorting changes ordering semantics
```

然后说明：

```text
- list_jobs no longer preserves submission order
- claim_next no longer implements FIFO
- downstream snapshot/audit consumers inherit the changed ordering
```

这样作者知道真正需要修的是：

```text
“ID 被错误用作 semantic ordering key”
```

而不只是：

```text
“某个 test expected list 错了”
```

---

# 8. Snapshot consequence 为什么值得提

`snapshot.dumps_current_snapshot()` 使用：

```python
for job in service.list_jobs()
```

所以 authority 的 internal-looking ordering change 会穿过：

```text
service list
→ snapshot serialization
→ durable/exported artifact
```

Reviewer probe 实际看到 snapshot job IDs 同样变成：

```text
job-1, job-10, job-11, ...
```

这说明 M09 的一个 lesson：

> **一个 local helper change 可以沿 dataflow 泄漏到 long-lived surface。**

不过这里最好把 snapshot symptom 放进 ordering blocker 的 consequence，而不是独立再开 blocker。

---

# 9. Legacy audit consequence

Candidate 把：

```python
jobs = list(state.jobs.values())
```

改成：

```python
jobs = service.list_jobs()
```

这个 architectural routing 本身是合理的。

但是由于 `service.list_jobs()` 被 lexical sort 污染，M06 audit output 也会在 `job-10` 后重新排序。

M06 characterization 只有最多 4 jobs，所以现有 fingerprint 仍然会绿。

这再次说明：

```text
characterization coverage
```

有 scope。

它不是所有未来输入 partition 的证明。

---

# 10. 一个好的 blocker comment

例如：

```text
Blocker — lexical sorting changes the existing ordering contract

`JobAuthority.list_jobs()` and `claim_next()` now use `sorted(state.jobs)`.
TaskForge's current contract is submission-order listing and FIFO claiming;
string job IDs are identifiers, not ordering keys. Once IDs reach `job-10`,
the order becomes `job-1, job-10, ..., job-2`, so the second claim can be
`job-10` rather than `job-2`. The same change also leaks into snapshot/audit
ordering through `service.list_jobs()`.

Please keep this architecture refactor behavior-preserving; if ordering is meant
to change, that needs a separate behavioral change with a new contract and
compatibility discussion.
```

这里没有规定作者必须用哪种容器。

required outcome 是：

```text
preserve semantic order
```

---

# 11. Finding 2 — unknown cancel 被偷偷改了

Baseline `service.cancel()`：

```python
job = state.jobs[job_id]
```

unknown ID：

```text
KeyError
```

`public_api.cancel_job()` 不做 translation，所以 external-style boundary 也会看到这个异常。

M04 已明确这是一个不理想、故意保留的 starter behavior。

Candidate 改成：

```python
try:
    job = state.jobs[job_id]
except KeyError:
    return False
```

并且新增：

```python
assert service.cancel("job-missing") is False
```

---

# 12. 新行为可能更好吗？

可能。

但这不是本 review 的关键。

Reviewer brief 说：

```text
structural refactor only
existing externally observable behavior unchanged
```

Candidate description 同时说：

```text
preserve all current behavior
no public API changes intended
```

所以：

```text
KeyError -> False
```

本身就是 scope violation。

即使未来真的要重新设计 unknown cancel，应该作为：

```text
explicit M04-style behavior change
```

回答：

```text
unknown / running / terminal 应怎样区分？
public error identity 是什么？
caller compatibility 怎么办？
```

不应塞在 architecture refactor 里。

---

# 13. 一个 passing test 如何成为 regression evidence

Candidate test：

```python
def test_cancel_missing_job_is_false():
    assert service.cancel("job-missing") is False
```

它当然 pass。

但 oracle 来源是：

```text
candidate's new desired behavior
```

而不是：

```text
requested contract
```

因此这个 green test 反而是一个 clue：

> author 在一份声称 behavior-preserving 的 patch 里新增了一个新的 behavioral assertion。

高质量 reviewer 会问：

```text
Why is this new behavior part of this refactor?
```

而不是因为有 test 就放心。

---

# 14. 一个好的第二 blocker

```text
Blocker — this refactor changes public cancel behavior

`JobAuthority.cancel()` converts an unknown job from the existing `KeyError`
path into `False`, and the new test explicitly blesses that behavior. The
review brief and PR description both say this is behavior-preserving, and
`public_api.cancel_job()` exposes the difference to callers.

Please keep the current behavior in this structural CL. If unknown-ID semantics
should be redesigned, split that into an explicit API behavior change with its
own contract and tests.
```

---

# 15. 哪些东西不是 blocker

## 15.1 `JobAuthority` 这个 abstraction 本身

不是 blocker。

方向合理。

不要因为 implementation 有 bug 就说：

```text
“authority abstraction 不应该存在”
```

---

## 15.2 `legacy_audit` 改走 service read path

不是 blocker。

只要 ordering 保持，它减少 raw-state knowledge leakage。

---

## 15.3 `service.get()` 继续返回 mutable `Job`

这是 M02 已知 baseline design issue。

Candidate 没有引入它。

而且 current PR scope 是 authority localization。

可以：

```text
FYI / follow-up
```

但不应该凭它 block 当前 PR。

---

## 15.4 M07 `concurrent_claim.py` 仍然直接写 state

Reviewer brief 明确说：

```text
historical fault-injection artifact out of scope
```

所以不能写：

```text
Blocker: authority 不是唯一 writer，因为 concurrent_claim 还在写。
```

这会把教学/diagnostic scope 与 product path 混淆。

M09 已经训练过这种 exception discipline。

---

# 16. M09 baseline probe 为什么会红，但不是 regression blocker

`m09_architecture_probe.py` 是对 **pre-refactor topology** 的 executable inventory。

它期待：

```text
direct state deps = concurrent_claim, legacy_audit, metrics, service, worker
```

合法引入 `JobAuthority` 后，这个 expected topology 本来就应该变化。

实际 corrected reference 中运行它：

```text
m09_probe_rc=1
```

这不意味着 authority refactor 错。

意味着：

```text
historical characterization has been superseded
```

后续应该：

- 更新成新的 architecture fitness rule；或
- 将旧 probe 标记为 baseline-only。

例如新 rule 更可能是：

```text
normal product path may not import state directly;
job_authority + named fault-injection modules are allowed exceptions.
```

---

# 17. M03 mutation harness 同样会失效

M03 `mutation_probe.py` 会寻找 baseline source 中的 exact mutation sites。

把 lifecycle logic 合法移动到 `JobAuthority` 后：

```text
m03_probe_rc=1
```

原因不是产品 regression，而是：

```text
historical teaching harness no longer matches source topology
```

这再次证明：

> **tests/probes themselves have contract lifetime and version scope.**

不要形成“所有历史工具必须永久绿”的 cargo cult。

---

# 18. Corrected reference 我实际跑了什么

在临时副本：

1. apply candidate patch；
2. 保留 `JobAuthority`；
3. `list_jobs()` 恢复 insertion/submission order；
4. `claim_next()` 恢复 FIFO scan；
5. `cancel()` 恢复 unknown `KeyError`；
6. candidate unknown-cancel test 改成 preservation assertion；
7. 新增跨 `job-10` 的 ordering/FIFO test。

然后实际执行：

```text
.......... [100%]
```

即：

```text
6 original tests
3 candidate tests（其中 cancel oracle corrected）
1 new boundary-order test
--------------------------------
10 passed
```

---

# 19. Corrected reference 的旧证据

实际继续运行：

## M04

```text
unknown get: KeyError
unknown cancel: KeyError
```

保持。

## M05

三个 dashboard fingerprints：

```text
unchanged
```

## M06

三个 legacy audit fingerprints：

```text
unchanged
```

## M07

historical double-claim / crash-window probe：

```text
unchanged
```

因为那个 fault-injection module 明确 out of scope。

## M08

compatibility baseline：

```text
historical v1 readable
W1 -> frozen R1 still pass
naive W2 break still reproduced
future schema fail closed
```

全部保持。

这才是比较完整的 architecture-refactor evidence。

---

# 20. 为什么 corrected test 要跨 `job-9 -> job-10`

不是因为课程迷信 12 这个数字。

而是从 implementation risk 推导 boundary：

```text
string lexical ordering
```

与：

```text
numeric creation sequence
```

第一次明显分叉发生在 decimal width change。

所以：

```text
9 / 10
```

是 semantic boundary。

这比随机造 100 jobs 更有解释力。

---

# 21. First-pass review 的理想结构

一个高质量 first-pass 可以很短：

```text
Decision: Request changes

The direction of centralizing lifecycle authority is sound, but this CL is not
behavior-preserving as described.

Blocker 1: `sorted(state.jobs)` replaces submission/FIFO order with lexical ID
order. A 12-job counterexample makes the second claim `job-10` instead of
`job-2`; the same ordering leaks into snapshot/audit output.

Blocker 2: unknown cancel changes from the existing `KeyError` path to `False`,
and the new test blesses that new behavior despite the stated no-behavior-change
scope. Please split any error-semantics redesign from this structural CL.

Non-blocking: the remaining direct-state access in `concurrent_claim.py` is an
explicit M07 fault-injection exception, so I am not asking to remove it here.
```

这已经比 25 个 line comments 强。

---

# 22. Candidate Description 的主要问题

Author description 同时写：

```text
preserve all current behavior
```

以及：

```text
treat cancelling an unknown job ... return False
```

这两句其实已经相互冲突。

一个 reviewer 如果只看 prose 的总体语气，很容易忽略。

应该把 claim 拆开：

```text
behavior preservation
new error normalization
```

然后马上发现：

```text
两者不能同时成立
```

这也是为什么 review 要把自然语言 summary 转成可验证 proposition。

---

# 23. “Low risk” 为什么不是 evidence

PR 写：

```text
Risk: Low. Internal refactor.
```

但是它改变：

```text
scheduler ordering
public boundary behavior
snapshot ordering
legacy audit ordering
```

所以：

```text
internal-looking implementation location
!=
internal semantic consequence
```

risk assessment 必须从 downstream contract 来。

---

# 24. 更好的 Change Topology

我建议：

## CL 1 — Authority localization only

```text
add JobAuthority
route service/worker/metrics/audit
preserve insertion/FIFO/error behavior
add architecture fitness rule
add >9 ordering regression test
```

Proof obligation：

```text
semantic authority localized
+
behavior preservation
```

## CL 2 — Optional error-contract redesign

如果真的决定改 unknown cancel：

```text
new public error semantics
caller contract
M04-style tests
compatibility considerations
```

Proof obligation：

```text
new behavior is intentional and well-specified
```

## CL 3 — Future remote worker

```text
protocol
retry
idempotency
security credentials
failure semantics
```

Proof obligation 完全不同。

这种拆法让每个 review 都有 bounded mental model。

---

# 25. 一个 corrected PR description 示例

```text
Problem
TaskForge lifecycle mutations are spread across service and worker modules,
which makes the authority model harder to preserve when a remote-worker
transport is introduced later.

Scope
Introduce an in-process JobAuthority and route normal product lifecycle access
through it. No transport, persistence, or public API redesign is included.

Behavior intentionally unchanged
- submission-order list_jobs
- FIFO claim_next
- existing unknown-ID behavior
- snapshot v1 format/order
- legacy audit output for existing scenarios
- M07 fault-injection artifact remains outside the normal product path

Evidence
- core suite
- >9-job ordering/FIFO regression
- M04 boundary probe
- M05 dashboard fingerprints
- M06 audit fingerprints
- M08 compatibility probe

Known tool updates
M09 topology inventory and M03 baseline mutation harness are version-specific;
they must be replaced/retired rather than treated as product regressions after
this structural move.

Follow-up
A later design/change will define the remote-worker protocol and failure model.
```

注意它没有写：

```text
Risk: Low
```

而是把 risk boundaries 展开成可 review 的 claims。

---

# 26. Reviewer Probes 的结果如何解释

`tools/m10_review_case.py --reviewer-probes` 实际返回四个 symptoms：

```text
ordering-regression
fifo-regression
undeclared-public-behavior-change
snapshot-order-consequence
```

成熟 review 不应该机械输出四个同等级 blocker。

更合理：

```text
Root cause A:
ID lexical sorting replaces semantic ordering
  -> list
  -> FIFO
  -> snapshot/audit

Root cause B:
error behavior change mixed into structural refactor
  -> public cancel semantics
```

这也是本实验为什么专门要求 root-cause aggregation。

---

# 27. Agent reviewer 的典型失败

模糊 prompt：

```text
Review this PR. Is it ready?
```

常见输出：

```text
- good separation of concerns
- tests pass
- authority abstraction improves maintainability
- maybe add docstrings/type hints
- LGTM with small comments
```

为什么？

因为 Agent 很容易被：

```text
author description
new clean abstraction
green tests
```

共同 anchor。

---

# 28. 更好的 Agent review contract

强制：

```text
reviewer brief first
baseline contract reconstruction
change type classification
independent test-oracle audit
counterexample construction
pre-existing vs introduced distinction
root-cause severity ordering
```

这样 Agent 才比较像 independent reviewer，而不是 author-summary editor。

---

# 29. 这章最关键的三个 lesson

## Lesson 1

```text
A green test can validate the wrong contract.
```

## Lesson 2

```text
A good architecture direction does not excuse behavior regressions hidden in the migration path.
```

## Lesson 3

```text
Review quality is determined by the strength of the acceptance argument,
not by comment count, diff-reading effort, or CI color.
```

---

# 30. Instructor grading notes

高分答案应当：

- 在 reveal probe 前独立发现至少主要 ordering risk；
- 能构造 `job-10` boundary，而非只说“sorted 可能有问题”；
- 明确 unknown cancel 是 scope/contract issue，而不是单纯争论哪种 API 更好；
- 认可 `JobAuthority` direction；
- 不把 M07 historical exception 当 blocker；
- 不要求顺便修 M02 所有旧债；
- 知道 M09/M03 historical harness 可能需要 supersede；
- 将 snapshot/audit symptoms 聚合到 ordering root cause；
- 能提出更清晰的 CL sequence。

中等答案通常：

- 能看到两个代码问题；
- 但没有解释 contract/source；
- 或把所有 symptoms 分开罗列；
- 或要求大量无关 cleanup。

低分答案通常：

```text
9 tests pass, LGTM
```

或者：

```text
这是教学 case，所以一定 request changes
```

两者都没有真正 review。
