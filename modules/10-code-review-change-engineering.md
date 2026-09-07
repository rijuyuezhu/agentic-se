# M10 — Code Review 与 Change Engineering：为什么“9 passed”仍然不能替你 Approve

> 一个 PR 不是一堆 changed lines。它是一份**有边界的工程论证**：作者声称某个具体 change 应该进入系统，并用实现、测试、迁移/回滚说明和其他 evidence 支撑这个 claim。
>
> M10 训练的不是“多找几个问题”，而是：**另一个人怎样独立判断这份论证是否成立。**

前九章已经分别问过 correctness、ownership、test oracle、API contract、refactor、legacy evidence、concurrency、compatibility 和 architecture。M10 把这些问题压缩到一个最常见的工程单位：一个真实 change。

这次 TaskForge 给你的 candidate 很诱人。它准备把 lifecycle logic 收敛到 `JobAuthority`，作者写着：

```text
Risk: Low. Internal refactor.
Evidence: 9 passed.
```

方向听起来合理，CI 也真的是绿的。问题是：**这仍然不足以决定 merge。**

## 1. 先看 review brief：你到底被要求接受什么

M10 的 review case 位于：

```text
labs/taskforge/review-cases/m10/
```

先读 `reviewer-brief.md`，不要先相信 author description。brief 的 change contract 很窄：

- 为未来 remote worker 做一个 architecture-enabling structural refactor；
- normal lifecycle logic/direct-state access 向一个 in-process semantic seam 收敛；
- externally observable behavior 不变；
- scheduling semantics 不变；
- snapshot compatibility 不变；
- M07 `concurrent_claim.py` 是明确的 historical fault-injection exception；
- 本轮不加 RPC、database、queue 或 remote-worker mechanism。

这一步已经产生两个不同 proof obligations：一是 architecture/locality direction 是否真的改善，二是 behavior-preserving claim 是否真的成立。它们不能互相替代；完全可能出现“architecture direction reasonable，但 behavior-preserving claim false”的情况。

一个 reviewer 如果因为“大方向对”就放过 behavior regression，仍然是在错误 approve。

同样，reviewer 也必须先审 issue/change contract 本身。如果真正需求只是“未来可能 remote”，candidate 却顺手引入 transport、queue、deployment topology，那么即使代码每一行都正确，也可能是 **wrong scope / speculative architecture**。Review 从来不只发生在 diff 之后。

## 2. Approval 的含义不是“我没看到红灯”

有意义的 approval 更接近：

> 基于我实际 review 的 scope 与 evidence，我认为这次 change 的工程 claim 成立，未解决风险已被识别，并且在当前 acceptance standard 下可接受。

因此 reviewer 至少要知道五件事：scope、claim、source of truth、evidence，以及 residual risk。

如果你只负责部分 files / aspects，也必须明确披露自己的 review scope；不能把 partial review 的 LGTM 伪装成 whole-change approval。一般情况下，最终 approval 前仍应理解自己被分配 review 的 human-written code；对超出能力范围的 specialist surface，要确认有 qualified reviewer 覆盖，例如明确写 `Need specialist review for <specific surface>`。

Review completion 不是“所有 comment thread 都 resolved”，而是当前 change 在实际 approval scope 内的 material claims、remaining implementation 和 code-health concerns 都已有足够的独立判断者与 evidence owner。

因此后面反复强调的 **risk-first** 是 review 的优先级策略，不是 sampling 策略：先找最可能推翻整份 change 的问题，可以避免低价值逐行工作；但在 change 进入可接受状态前，仍要完成自己承担的剩余 review scope。

## 3. Author description 很重要，但它只是 claim

`agent-pr-description.md` 说：

```text
- add JobAuthority as the single owner of lifecycle state;
- preserve all current behavior;
- use stable job-id ordering;
- unknown cancel returns False;
- 9 passed;
- low risk.
```

这里已经有一个值得停下来的矛盾：`preserve all current behavior` 和 `change unknown cancel semantics` 不可能同时自动成立。

PR description 的价值是把作者的 reasoning 留给 reviewer 和 future maintainer，而不是把作者变成 truth authority。最低限度，一份可审查 description 应让你分离 Problem、Intended behavior change、Intentionally unchanged behavior、Design / authority decision、Risk / migration assumptions、Evidence actually run，以及 Known limits / follow-ups。

“Low risk”不是 evidence；“internal refactor”也不是。Risk 要沿 downstream contract 判断，而不是按文件路径的“内部/外部”标签判断。

## 4. 在读 patch 前，先恢复 baseline contract

如果 reviewer 直接从 changed line 开始，最容易把 implementation accident 当成新 design freedom。M10 case 在读 patch 前至少要恢复这些事实：

| Surface | Current baseline | 本轮为什么相关 |
|---|---|---|
| `list_jobs()` | submission/insertion order | structural refactor 声称 behavior-preserving |
| `claim_next()` | queued jobs 中 FIFO | scheduling semantics 明确要求不变 |
| unknown cancel | `service.cancel()` 对 missing ID 抛 `KeyError`，public boundary 继续暴露 | 当前行为不漂亮，但仍是本轮 baseline |
| snapshot | v1 writer/reader compatibility surface | downstream durable export 依赖 list order |
| legacy audit | 已有 characterized output/order | raw-state read path 会被改路由 |
| M07 `concurrent_claim.py` | 故意 unsafe | brief 明确 out of normal-product scope |
| mutable `Job` handle | `service.get()` 返回 authoritative mutable object | M02 已知 residual authority risk，不是本 candidate 新引入 |

最后一行很重要。M02 已经建立：**每个拿到 authoritative mutable `Job` reference 的 caller 都获得潜在 write authority**。M09 又刚刚区分了 **normal transition/direct-state localization** 与 **complete mutation-capability isolation**；前者成立不等于后者成立。

因此 candidate 新建 `JobAuthority` 后，如果 `get()` / `claim_next()` 仍返回 live mutable `Job`，它并没有证明 complete authority isolation。但这个 baseline issue 不是本 structural CL 新引入的；reviewer 可以记录为 residual/FYI，而不应为了“把架构做完”强迫本 PR 顺手引入 `JobView`。

这就是 review scope discipline：**看见问题，不等于这个 PR 必须修问题。**

## 5. Author CI 真的绿，但这只能回答它问过的问题

运行：

```bash
cd labs/taskforge
PYTHONPATH=src uv run --with pytest --no-project \
  python tools/m10_review_case.py
```

真实结果是：

```text
[AUTHOR CI]
......... [100%]
author-supplied CI is green
```

所以本 case 不是“作者忘了跑 tests”。真正的问题是：**这 9 个 tests 是否覆盖了 change 的 semantic risk partition？**

机器 verification 与 human review 是不同 signal。Gerrit 的 `Verified` / `Code-Review` 分离只是一个现实 workflow 例子；它不要求你使用 Gerrit，但很好地提醒：**CI 回答的是被选中的可执行问题是否通过；review 还要判断这些是不是对的问题。**

M03 已经训练过 oracle。M10 再加一层：**tests 自己也是 change 的一部分，也必须被 review。**

一个 author/Agent 可以同时生成错误 implementation 和与之匹配的错误 oracle，然后得到漂亮的绿色 CI。

## 6. Risk-first 不是抽查：先找 semantic center，再完成剩余 scope

Candidate patch 的 semantic center 是新 `job_authority.py`。`service.py`、`worker.py`、`metrics.py`、`legacy_audit.py` 大部分是在 routing。先看 semantic center，是因为它最可能决定整份 change 是否成立；**不是**因为 routing files 从此不用 review。

如果 center 已经有 fundamental design/contract mismatch，应尽早反馈，避免先在将被重写的代码上花时间。反过来，如果 center 基本成立，reviewer 仍要继续检查被分配的其余 human-written change，确认 routing、tests、docs、error handling、maintainability 等没有引入新的问题。Risk-first = prioritization, not sampling.

先问 `submit / get / list / cancel / claim / finish / metrics-read path` 这些 semantic operations 是否偷偷加入了新 policy，特别寻找新的 ordering、error translation、default、authority capability 或 failure behavior。

这是 refactor 最常偷带 behavior change 的地方。

Candidate 中最显眼的一行看起来甚至像“改进”：

```python
return [state.jobs[job_id] for job_id in sorted(state.jobs)]
```

comment 说 stable ordering 更 deterministic。问题是：baseline insertion order 本来就 deterministic，而且 **job-ID lexical order 不是 submission order**。

## 7. `job-9 → job-10` 是比“再多跑点 tests”更好的反例

对于：

```text
job-1
job-2
```

lexical order 恰好等于 submission order。到 `job-9` 也没暴露问题。

第一个高信息量边界是 digit width 改变：

```text
job-9
job-10
```

创建 12 个 jobs 后，candidate 的排序变成：

```text
job-1
job-10
job-11
job-12
job-2
...
```

于是同一个 root cause 会同时影响 `list_jobs()` ordering、`claim_next()` FIFO、snapshot exported order 和 legacy audit order。

成熟 review 不应把它机械写成四个同等级 blocker。更好的聚合是指出一个 root cause——lexical job-ID sorting 替代了 semantic submission/FIFO order——再说明它分别造成 list order regression、scheduler regression、durable snapshot ordering change 和 audit ordering change。

这比“comment 越多越认真”更接近 change engineering。

## 8. Context beyond diff：internal-looking helper 可以穿过 durable/public surface

只看 `job_authority.py`，`sorted(...)` 像一个内部实现细节。沿 dataflow 往外走：

```text
JobAuthority.list_jobs
  ├─ service.list_jobs
  ├─ public API
  ├─ dashboard/readers
  ├─ snapshot export
  └─ legacy audit
```

reviewer 才会看到它的真实 blast radius。

这就是为什么 code review 不等于 diff review。你要追的是：

```text
changed line
  ↓
semantic operation
  ↓
callers / authority / durable surface / failure path
  ↓
compatibility / rollback consequence
```

对 architecture-heavy change，还要问 Stanford CS190 类似的问题：knowledge 移到了哪里、是否被复制、谁现在拥有这个 decision、哪些 caller 因此必须知道更多。这里不是为了套 modularity 术语，而是为了识别 hidden coupling。

## 9. 第二个 blocker：更“友好”的 error handling 仍然是 scope violation

Baseline：

```python
job = state.jobs[job_id]
```

missing ID 会抛 `KeyError`；`public_api.cancel_job()` 没有 translation，所以 external-style boundary 也看到这个异常。

这个 contract 并不漂亮，M04 早就指出过。但 candidate 改成：

```python
try:
    job = state.jobs[job_id]
except KeyError:
    return False
```

并新增 test：

```python
assert service.cancel("job-missing") is False
```

新行为也许更好，但这不是判断 blocker 的关键。brief 和 author description 都说这是 behavior-preserving structural refactor。因此，`KeyError -> False` 本身就是 undeclared behavior change。

更好的 change topology 是把它拆成一个显式 M04-style API redesign：先定义 unknown/running/terminal semantics、error identity、caller compatibility，再写对应 tests。不能因为“顺手更友好”就把新 policy 混进 refactor。

这个 passing test 反而是很有价值的 review clue：它证明 author 正在给一个本来没有获准改变的行为写新 oracle。

## 10. Architecture direction、implementation correctness、change packaging 要分别判

Candidate 并不是“整体设计错了”。更准确的判断是：architecture/localization direction reasonable，但 implementation preservation 和 change packaging 都已经 broken。

`JobAuthority` 作为 in-process semantic seam 符合 M09 的 boundary-enabling direction：normal transition logic/direct-state access 可以逐步 localize，worker 不再需要直接理解 storage representation。

但不要把这句话升级成“complete authority isolation achieved”。

Candidate 的 `get()` / `claim_next()` 仍返回 live `Job`，所以 M02 capability risk 还在。它是已知 baseline residual，不应作为本 PR blocker；同样，M07 `concurrent_claim.py` 是 reviewer brief 明确保留的 historical exception，也不能拿 whole-repo grep 强迫清除。

Review 的成熟度很大一部分来自这种分类：introduced regression、necessary prerequisite、pre-existing issue、historical/diagnostic exception，以及 out-of-scope cleanup。

## 11. Historical probe 也有 lifetime，不能把所有旧绿灯永久冻结

合法 authority refactor 会改变 source topology。因此 M09 的 baseline inventory probe 可能开始“红”：它原本期待 `service/worker/metrics/...` 直接 import `state`，而新 architecture 正是要改变这一点。

M03 某些 mutation harness 也可能绑定具体旧 source site。

这不自动等于 product regression。Reviewer 要问：这个 probe 在证明长期 contract，还是只在 characterize 某个历史 topology/source seam？

- M05 dashboard observable fingerprints、M06 audit characterization、M08 compatibility fixture 等可能仍是当前 change 的 regression evidence；
- M09 direct-import inventory 如果被合法 architecture change supersede，就应更新成新的 fitness rule或标记 baseline-only。

“所有历史 tests 永远不许变”与“不要无证据删 tests”一样，都是错误的极端。

## 12. Severity 是工程后果，不是语气强弱

`COURSE_DESIGN.md` 要求学生能写 `Blocker / Medium / Nit` 的证据标准，因此本章把 **Blocker、Medium（也可写 Important / Should fix）和 Nit** 作为 canonical severity。

`Optional / Consider`、`FYI` 可以继续作为 comment intent，但它们不是第四、第五档 severity。平台当然不必真的提供这些 label；重要的是 author 能知道哪些问题阻止 merge、哪些 material 问题应在本 CL 修、哪些只是 polish。

**Blocker**：证据表明当前 change 的 material engineering claim 不成立，或存在必须在 merge 前关闭的不可接受风险。

**Medium**：有具体 evidence 和 material consequence，通常应在本 CL 修正，但该 finding 本身未必足以否定整个 change；例如局部 maintainability regression、重要但 bounded 的 missing validation，或会明显增加后续维护成本的 design issue。是否最终 blocking 仍取决于 cumulative risk，而不是 label 名字。

**Nit**：非 mandatory polish / minor clarity / personal-style-adjacent improvement；缺少它不应被伪装成 code-health blocker。

Blocker 通常需要连接到 material engineering consequence，例如：

- requested contract regression；
- invariant violation；
- hidden compatibility/migration break；
- incorrect failure semantics；
- security/authority violation；
- evidence 无法支撑 material claim；
- current change scope 本身错误；
- 明确的 code-health regression。

下面这类意见通常不是 blocker：“我更喜欢另一个变量名”“我会换一种 pattern”“这个 helper 我会拆成两个”。

如果几个方案工程上等价，reviewer preference 不应伪装成 mandatory requirement。Google reviewer guidance 的 code-health principle也不是“追求完美”，而是不要让系统随 change 累积明确退化。

重要 finding 最好包含：

```text
Severity
Observation/location
Contract / engineering reason
Consequence
Evidence / minimal reproduction
Required outcome
```

最后一项通常写“什么必须变真”，而不是替作者规定唯一 implementation。

## 13. Small change 指的是 bounded claim，不是固定 LOC

一个 change reviewable，不是因为它 `< 100 LOC`，而是因为它围绕 **one coherent engineering claim**，拥有 bounded consequences 和 independently reviewable evidence。

M10 candidate 更好的 topology 是：

```text
CL 1 — authority localization only
  add in-process JobAuthority
  route normal service/worker/metrics/audit access
  preserve insertion/FIFO/error semantics
  add architecture fitness + >9 ordering evidence

CL 2 — optional error-contract redesign
  only if product wants new unknown-ID semantics
  define public contract + caller compatibility

CL 3 — future remote worker
  protocol / retry / auth / timeout / idempotency / deployment
```

三个 CL 的 proof obligation 完全不同。把它们绑在一起只会放大 reviewer mental model、rollback ambiguity 和 author/reviewer coordination cost。

这也是 “small changes” 真正有价值的原因：不是 worship diff size，而是让 change boundary 接近一个可独立判断的 engineering proposition。

## 14. Change type 决定 proof obligation，不要套 universal checklist

同样一句“tests pass”，对不同 change type 意义不同：

| Change type | Reviewer 主要问什么 |
|---|---|
| behavior-preserving refactor | 哪些 observable semantics 必须保持？有没有 characterization/regression evidence？ |
| bug fix | 是否有 fail-before / pass-after？修的是 root cause 还是 symptom？ |
| migration | old/new coexistence matrix、rollout/rollback order 是否闭合？ |
| concurrency change | 哪些 history/interleaving 被允许？crash/retry semantics 是否改变？ |
| architecture change | authority、knowledge、failure/deployment boundary 是否真的改变？代价和 migration 是什么？ |

这张表不是另一张 checklist，而是提醒 reviewer：**review depth 由 change type 和 risk model 驱动。**

## 15. 一个高信息量 Review Funnel

面对大 change，不要从 naming comment 开始。更有效的顺序是：

1. 先判断这个 change 是否应该存在，issue/change contract 是否自洽；
2. 明确它究竟声称改变什么、什么必须保持；
3. 找到 semantic center，并沿 callers / authority / durable / failure surfaces 追 blast radius；
4. 判断 tests/probes 能否区分正确实现与 plausible-but-wrong implementation；
5. 记录 residual risk；
6. 完成剩余 assigned implementation 和 code-health review；
7. 最后才把 mandatory findings 与 true nits / optional polish 分开。

如果 Stage 0–4 已经发现 fundamental mismatch，就应该尽早给 broad feedback，而不是先花四十分钟改 variable names。这只是调整投入顺序；如果 broad design 通过，最终 approval 前仍要完成自己承担的其余 human-written scope，或明确说明 partial scope 并确认其他 reviewer 已覆盖剩余部分。

这里的 **code health** 也不是 nit 的同义词。明确的 maintainability、readability、understandability、complexity regression 可以是 Medium，严重时也可以 blocking；只有真正 non-mandatory 的 polish 才是 Nit。

## 16. Reviewer probe 应该验证你的 reasoning，而不是替你 reasoning

Lab 故意要求先写 first-pass review，再运行：

```bash
PYTHONPATH=src uv run --with pytest --no-project \
  python tools/m10_review_case.py --reviewer-probes
```

probe 会稳定暴露：

```text
ordering-regression
fifo-regression
undeclared-public-behavior-change
snapshot-order-consequence
```

但真正要评估的是：

```text
ALREADY FOUND
NEW FINDING
SAME ROOT CAUSE
NOT A BLOCKER
```

如果你只在看完 reveal output 后把四个 ID 重写成四条 comment，你没有完成 independent review；你只是在解释答案。

Targeted probe 的价值是围绕 uncertainty 选择高信息量输入。`job-9 → job-10` 比“随机 fuzz 1000 次”更能说明你理解了 failure mechanism。

## 17. Agent 生成 PR 的特殊风险：confidence 不是 provenance

Agent 可以非常快地同时生成：

- implementation；
- tests；
- PR summary；
- risk assessment；
- “all checks passed”结论。

这些 artifact 可能共享同一个错误 assumption，所以**数量多不等于独立 evidence 多**。

Reviewer 对 Agent-generated change 尤其要防 confident summary、implementation-derived tests、藏在 feature work 里的 broad cleanup、silent assumption completion，以及 tool-output laundering。

例如 Agent 说“CI green, therefore behavior-preserving”，就是把工具真正给出的 `9 selected tests passed` 洗成更强的 `all relevant behavior preserved`；后一句没有 provenance。

M10 可以让 Agent 帮忙 inventory callers、运行 probe、整理 diff，但 acceptance authority 仍需要独立 reviewer model。如何进一步设计 agent context、task boundary、parallel implementation/review 和 merge conflict，留到 M11；本章只要求**不要让生成者同时成为自己 claim 的唯一验证者。**

## 18. Re-review 不是检查“fixed all comments”

新的 patch set 到来时，旧 approval 不能机械复用。至少要重新 inspect patch-set delta、rerun blocker reproduction、确认没有新增 behavior scope、review changed tests/oracles，并确认 intended architecture/change goal 仍然成立。

特别注意一种常见假修复：production code 没解决 root cause，只把 expected output 改成当前实现，于是原 blocker test 重新绿了。

Re-review 关注的是 engineering proposition 是否现在成立，而不是 conversation state 是否显示 resolved。

## 19. 一个够用的最终 review 可以很短

M10 case 的高质量 first-pass 不需要几十条 comment：

```text
Decision: Request changes

The authority-localization direction is reasonable, but this CL is not
behavior-preserving as described.

Blocker 1: lexical job-ID sorting replaces the existing submission/FIFO order.
A >9-job counterexample makes the second claim job-10 instead of job-2; the
same root cause leaks into list/snapshot/audit order.

Blocker 2: unknown cancel changes from the existing KeyError path to False,
while the brief says public behavior is unchanged. Keep current semantics in
this structural CL or split an explicit API behavior redesign.

Non-blocking: mutable Job exposure is a known M02 residual, and
concurrent_claim.py is an explicit M07 historical exception; neither is a new
regression that this CL must repair.
```

这份 review 的价值来自 change model、root-cause findings、severity、evidence 和 scope discipline，而不是 comment 数量。

## 20. Lab：把 review 变成可复现的工程过程

完整实验见 [Lab 10](../labs/10-code-review-change-engineering.md)。你会：

1. 只读 reviewer brief，先写 change contract；
2. 从真实 starter 恢复 baseline；
3. 验证 author CI 的确 green；
4. review author description、tests 和 semantic center；
5. 在 reveal probe 前写 first-pass review；
6. 再用 reviewer probes 检查自己的 blind spot；
7. 聚合 root cause、校准 severity；
8. 设计 corrected change topology 与 re-review plan。

Instructor reference 在 [M10 case analysis](../case-studies/m10/instructor-analysis.md)。不要在 first-pass 前读它。

## 21. 来源边界：哪些是 source-backed，哪些是课程综合

详细审计见 [M10 source audit](../reading-notes/m10-source-audit.md)。

Google Engineering Practices 支撑 code health、broader-context review、review tests themselves、risk-first navigation、small/coherent CL、good descriptions 和 comment intent；*Software Engineering at Google* Chapter 9 支撑 code review 的长期 correctness/comprehensibility/ownership/history 价值，以及不同 change type 需要不同 review reasoning；Gerrit 文档只用于说明 machine verification 与 human code-review signal 可以被 workflow 明确分开；Stanford CS190 支撑在 design review 中检查 knowledge leakage、interface 与 modularity；GitHub review material只作为 governance mechanism 示例。

以下是课程综合或 TaskForge-specific reasoning，而不是来源中的原句定律：

- PR = bounded engineering argument；
- `claim -> oracle -> evidence -> residual risk -> decision` review model；
- review funnel；
- severity/evidence comment template；
- root-cause aggregation；
- `job-9 → job-10` risk partition；
- historical probe lifetime 分类；
- TaskForge corrected CL topology；
- Agent summary / tool-output laundering 分析。

这些来源不能推出：CI green 就能 approve、所有 PR 必须小于固定 LOC、所有 baseline defects 必须在当前 PR 修、reviewer 必须重写作者方案、某个 approval 数量等于 review quality，或 `JobAuthority` 这个名字本身就证明 authority isolation。
