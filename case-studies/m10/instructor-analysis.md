---
id: case-M10
type: case_study
visibility: instructor
related: [M10]
---
# M10 Instructor Reference — 这份“9 passed”为什么仍然应该 Request Changes

> Spoiler warning：先完成 [Lab 10](../../labs/10-code-review-change-engineering.md) 的 first-pass review，再读本文件。
>
> 这是一份 reference reasoning，不是“标准答案 comment 列表”。真正要学的是：finding 怎样从 brief、baseline、diff 与 evidence 独立推出。

## 1. Verdict：方向合理，当前 patch 不能 merge

Candidate 的 architecture-enabling direction 是合理的：

```text
normal service / worker / metrics / audit access
                 ↓
             JobAuthority
                 ↓
          current in-memory state
```

它没有提前引入 RPC、DB、queue 或 remote deployment machinery，符合 M09 的 KISS direction：先 localize normal transition policy/direct-state knowledge，再讨论 future process split。

但我会给：

```text
REQUEST_CHANGES
```

有两个 root-cause blockers：

1. `sorted(state.jobs)` 把 submission/FIFO semantics 换成 lexical job-ID order；
2. unknown cancel 从现有 `KeyError` 改成 `False`，与“structural / behavior-preserving” change contract 冲突。

第一个 root cause 会同时表现为 list、claim、snapshot、audit consequence；不要把它们机械写成四个 blocker。

## 2. Review authority 来自 brief + baseline，不来自“这肯定是坏 PR”

Reviewer brief 明确：

```text
structural / architecture-enabling refactor only
existing observable behavior unchanged
current scheduling semantics unchanged
snapshot compatibility unchanged
M07 concurrent_claim.py is an explicit historical exception
no RPC/database/queue/remote worker yet
```

所以至少有两个 proof obligations：

```text
localization direction actually improves
behavior preservation actually holds
```

Candidate 在第一项上大体合理，在第二项上失败。

如果学生只写“老师肯定藏了 bug，所以 request changes”，没有完成 review。相反，如果学生因为“新 architecture 很 clean”而 approve，也没有完成 review。

## 3. Author CI 确实是 9 passed

实际运行：

```bash
cd labs/taskforge
PYTHONPATH=src uv run --with pytest --no-project \
  python tools/m10_review_case.py
```

结果：

```text
[AUTHOR CI]
......... [100%]
author-supplied CI is green
```

因此 finding 不能写成“作者没跑 tests”。真正问题是：**这 9 个 tests 没有覆盖这次 refactor 的关键 semantic partitions，而且其中一个新 test 直接把未经批准的新 behavior 写成 oracle。**

## 4. Finding 1：stable lexical order 不是 submission order

Candidate：

```python
def list_jobs(self) -> list[Job]:
    return [state.jobs[job_id] for job_id in sorted(state.jobs)]
```

以及：

```python
def claim_next(self) -> Job | None:
    for job_id in sorted(state.jobs):
        ...
```

Author comment 说 stable ordering 更 deterministic。这不是足够理由：baseline insertion order 已经 deterministic，而且 M03 已把 relevant semantics 明确成：

```text
list_jobs preserves submission order
claim_next is FIFO among queued jobs
```

需要问的是：

```text
lexical job-ID order == submission order ?
```

对 `job-1` / `job-2` 碰巧成立，对 `job-9 → job-10` 开始失效。

## 5. 最小高信息量反例

创建 12 个 jobs。Expected submission order：

```text
job-1
job-2
...
job-9
job-10
job-11
job-12
```

Candidate list order：

```text
job-1
job-10
job-11
job-12
job-2
...
job-9
```

Scheduler 同理：第一次 claim `job-1`，第二次不是 `job-2`，而是 `job-10`。

这个 partition 有价值，因为它直接命中 implementation assumption 的边界：**identifier digit width changes**。它比“随机再跑几个 jobs”更能证明 reviewer 理解了 mechanism。

Reviewer reveal probe 实际确认：

```text
ordering-regression
fifo-regression
snapshot-order-consequence
```

三个 symptom 应聚合成一个 root cause。

## 6. 为什么这个 root cause 会穿过 diff 之外

`JobAuthority.list_jobs()` 看起来像 internal helper，但 dataflow 是：

```text
list_jobs
  ├─ service/public read path
  ├─ dashboard/readers
  ├─ snapshot export
  └─ legacy audit
```

因此 lexical sorting 不是“内部排序偏好”。它改变了 scheduler semantics，并进入 durable/observable artifacts。

一个合格 blocker 可以写成：

```text
Blocker — lexical job-ID sorting breaks the existing submission/FIFO contract

`list_jobs()` and `claim_next()` sort `job-N` identifiers lexically. Once IDs
cross job-9 -> job-10, that order diverges from submission order: after job-1,
the next claim becomes job-10 rather than job-2. The same root cause changes
list/snapshot/audit ordering. This CL is explicitly behavior-preserving, so
please preserve the existing submission/FIFO semantics or split an intentional
ordering change into its own contract change.
```

Notice required outcome 没有规定唯一 implementation。

## 7. 为什么 candidate tests 没抓到它

新 authority test 只创建两个 jobs：

```text
job-1
job-2
```

这一区间里 lexical order 与 submission order 恰好相同，所以 test 不能 discriminate 正确与错误实现。

这不是“test 数量太少”的一般抱怨，而是 input partition 错过了 known risk boundary。

修正后的 evidence 至少应该跨过 `>9` ID，并同时检查 list 与 FIFO，而不是简单复制：

```python
assert list_ids == sorted(expected)
```

那只会把 implementation assumption 写进 oracle。

## 8. Finding 2：unknown cancel 偷带了 public behavior change

Baseline `service.cancel()`：

```python
job = state.jobs[job_id]
```

unknown ID 会 `KeyError`。`public_api.cancel_job()` 没 translation，所以 external-style boundary 也暴露这一差异。

Candidate：

```python
try:
    job = state.jobs[job_id]
except KeyError:
    return False
```

并新增：

```python
assert service.cancel("job-missing") is False
```

`False` 也许比 `KeyError` 更好，但 brief 说本轮 behavior-preserving，author description 也说 no public behavior change intended。因此这不是“改得更好就可以”的问题，而是 **scope violation**。

第二条 blocker 可以写：

```text
Blocker — this structural refactor changes unknown-cancel behavior

The existing path raises KeyError for an unknown job and public_api exposes that
behavior. JobAuthority.cancel() converts it to False, while the review brief
says externally observable behavior is unchanged. Keep the existing behavior
in this structural CL; if the product wants new error semantics, split an
explicit API-contract change with its own caller/compatibility reasoning.
```

## 9. 一个 passing test 为什么反而可能是 regression evidence

Candidate test：

```python
assert service.cancel("job-missing") is False
```

当然会 pass。但 oracle 的来源是：

```text
candidate's newly chosen behavior
```

不是：

```text
requested change contract
```

所以这个 green test 是一个 clue：author 在 behavior-preserving refactor 中为新 behavior 建 oracle。

Reviewer 要问：

> Why is this behavior allowed to change in this CL?

而不是“有 test 就说明合理”。

## 10. 哪些不是 blocker：scope discipline 比“多找问题”更重要

### `JobAuthority` abstraction 本身

不是 blocker。把 normal transition/direct-state access localize 到一个 in-process seam 是合理 M09 direction。

### `legacy_audit` 改走 service/read path

只要 observable ordering 保持，不是 blocker；它减少 raw representation knowledge leakage。

### `service.get()` / `claim_next()` 仍返回 mutable `Job`

这是 M02 已知 baseline authority risk。严格说，live mutable `Job` 是 authority-bearing handle，所以 candidate **没有证明 complete mutation-capability isolation**。

但这不是 candidate 新引入的问题，而且当前 CL 的 bounded claim 是 authority localization，不是 redesign read model。可以写：

```text
FYI / residual M02 risk
```

不应该为了它强制本 PR 引入 `JobView` 或 defensive copy。否则 reviewer 自己制造 scope creep。

### `concurrent_claim.py` 仍直接写 state

Reviewer brief 明确把它定义为 M07 historical fault-injection exception。它不属于 normal product-path architecture rule，因此不能用 whole-repo grep 写成“authority 不是唯一 writer”的 blocker。

## 11. M09 / M03 historical probes 为什么可能红

合法 authority refactor 会改变 source topology。于是旧 M09 baseline inventory 可能不再看到：

```text
service, worker, metrics, legacy_audit direct-import state
```

M03 某些 mutation harness 也可能因为 mutation site 被移动而失效。

这类 red signal 需要先判断 evidence lifetime：

```text
long-lived behavioral contract?
historical topology characterization?
source-site teaching harness?
```

如果 change 正是合法改变 topology，旧 inventory 应升级成新的 fitness rule或标记 baseline-only，而不是要求 architecture 永久停在旧结构。

相反，M05 observable fingerprints、M06 characterized audit behavior、M08 compatibility fixture 等如果仍属于当前 preservation claim，就继续是有效 regression evidence。

## 12. Candidate description 自己也有 contradiction

它同时写：

```text
preserve all current behavior
```

和：

```text
unknown cancel returns False
```

reviewer 应把 prose 转成 proposition，而不是被整体语气锚定。

同样：

```text
single owner of lifecycle state
```

如果被理解为 complete capability isolation，也比当前 implementation 实际证明的更强。更准确的 CL1 description 应说 normal transition logic/direct-state access 被 localize，并把 mutable-handle authority issue列为 known residual，而不是靠 module name 宣称“single owner 已完成”。

## 13. Corrected change topology

更可 review 的 sequence：

```text
CL 1 — Authority localization only
  add in-process JobAuthority
  route normal service/worker/metrics/audit access
  preserve submission/FIFO semantics
  preserve existing unknown-ID behavior
  preserve snapshot/audit observable contracts
  add architecture fitness evidence
  add >9-job ordering/FIFO evidence
  record mutable Job exposure as residual M02 issue

CL 2 — Optional error-contract redesign
  only if product chooses new unknown-ID semantics
  specify boundary/error identity
  analyze caller compatibility
  add behavior-change tests

CL 3 — Future remote worker
  define protocol/version policy
  timeout/retry/idempotency
  worker credentials/auth
  deployment/failure model
```

每个 CL 的 proof obligation不同，review/rollback boundary也更清楚。

## 14. 一个 corrected CL1 description 应该长什么样

```text
Problem
TaskForge's normal lifecycle transition logic and raw-state knowledge are spread
across service/worker/read paths, making a future worker boundary harder to
preserve.

Scope
Introduce an in-process JobAuthority seam and route normal product access
through it. No transport, persistence, or public API redesign is included.

Behavior intentionally unchanged
- submission-order list_jobs
- FIFO claim_next
- current unknown-ID behavior
- snapshot v1 format/order
- characterized audit behavior
- M07 fault-injection artifact remains an explicit exception

Evidence
- core suite
- >9-job list/FIFO regression
- relevant public-boundary behavior
- M05/M06 observable fingerprints
- M08 compatibility baseline
- new direct-state architecture fitness rule

Known residual
Returned mutable Job handles remain an M02 authority-capability issue; this CL
localizes normal transition/direct-state implementation but does not redesign
observation objects.

Follow-up
Remote-worker protocol/failure semantics are a separate future change.
```

这比：

```text
Risk: Low
```

更可 review，因为 risk boundary 被展开成了 propositions。

## 15. Reveal probe 的四个 output 应怎样解释

运行：

```bash
PYTHONPATH=src uv run --with pytest --no-project \
  python tools/m10_review_case.py --reviewer-probes
```

当前会看到：

```text
ordering-regression
fifo-regression
undeclared-public-behavior-change
snapshot-order-consequence
```

reference 聚合为：

```text
Root cause A:
lexical ID sorting replaces semantic ordering
  -> list
  -> FIFO
  -> snapshot/audit

Root cause B:
error behavior change mixed into structural refactor
  -> public cancel semantics
```

如果学生在 reveal 前已经找到 A/B，是 strong independent review evidence；如果 reveal 后才发现，也应诚实记录，而不是回写历史。

## 16. Reference first-pass review

```text
Decision: Request changes

The authority-localization direction is reasonable, but the CL is not
behavior-preserving as described.

Blocker 1: `sorted(state.jobs)` replaces submission/FIFO order with lexical job
ID order. The first discriminating boundary is job-9 -> job-10; with 12 jobs,
the second claim becomes job-10 instead of job-2. The same root cause changes
list/snapshot/audit ordering.

Blocker 2: unknown cancel changes from the existing KeyError path to False, and
the new test blesses that behavior despite the structural/no-public-change
scope. Split any error-contract redesign from this CL.

Non-blocking: mutable Job exposure is a known M02 residual; concurrent_claim.py
is an explicit M07 historical exception. Neither is a new regression this CL
must repair.
```

短并不等于 shallow。这里已经包含 change model、root cause、severity、counterexample、downstream consequence 与 scope discipline。

但这份 **first-pass Request Changes** 也不应被误读成“找到 semantic center 的两个 blocker，所以其它 assigned code 永远不用看”。Risk-first 的收益是尽早发送会导致大规模 rework 的 broad feedback。等 candidate 修到可能被 approve 的状态时，reviewer 仍要完成自己承担的剩余 human-written scope，并检查 maintainability / readability / understandability / complexity 等 code-health concerns；如果只承担 partial review，要明确披露并确认其他 reviewer 覆盖剩余部分。

本 case 恰好没有需要单独展示的 Medium finding，但课程 canonical severity 仍是 `Blocker / Medium / Nit`：

- Blocker：material acceptance claim 失败或有 merge 前必须关闭的不可接受风险；
- Medium：有具体 evidence/material consequence，通常应在本 CL 修，但单独未必否定整份 change；
- Nit：non-mandatory polish。

`Important / Should fix` 可以作为 Medium 的 wording alias；`FYI` / `Optional` 是 comment intent，不是新的 severity 档。

## 17. Re-review 时不能只看 thread resolved

如果 author 发新 patch set 说“fixed all comments”，我会：

1. inspect patch-set delta；
2. 重跑 `>9` ordering/FIFO counterexample；
3. 重跑 unknown cancel baseline；
4. review 新/改 tests，确认不是只改 expected；
5. 确认 normal authority-localization goal 仍成立；
6. 检查是否偷带新的 behavior scope；
7. 完成尚未覆盖的 assigned human-written implementation，并重新检查 code health；
8. 若存在 partial/specialist scope，确认相应 qualified reviewer 已覆盖；
9. 重新判断 residual risk，而不是复用旧 approval。

Stale approval 是真实 review failure mode：conversation 被 resolve 不等于 system claim 已成立。

## 18. Instructor grading focus

优先看学生是否：

- 在 reveal 前独立恢复 brief/baseline；
- 找到 `job-9 → job-10` 这种 mechanism-driven counterexample；
- 把 list/FIFO/snapshot/audit 聚合为一个 root cause；
- 识别 unknown cancel 是 scope violation，而不是争论新 API 是否“更漂亮”；
- 接受 `JobAuthority` direction，同时不把 module name 当 complete authority proof；
- 把 mutable `Job` / M07 exception正确分类为 residual/out-of-scope，而不是 blocker；
- 会审 tests/oracles，不把 9 passed 当 correctness conclusion；
- 能设计 bounded change topology 与 re-review plan。

不按 comment 数量评分，也不要求 wording 与本 reference 一样。

## 19. 三个 lesson

**第一，review 的输入不是 diff，而是 change claim + existing system。**

**第二，green tests 是 evidence artifact，不是 acceptance authority；reviewer 还要判断 oracle、partition 和未问的问题。**

**第三，高质量 review 同时会阻止 regression，也会阻止 reviewer 自己制造 scope creep。**
