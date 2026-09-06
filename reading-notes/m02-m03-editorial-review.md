# M02–M03 Editorial Review Record

这份记录服务于 issue #2 的顺序编辑批次。它记录 M02–M03 重写前后的 semantic mapping、自审发现和 dependency sweep；不替代独立 reviewer，也不新增 technical provenance。

本批基线是 `main` 的 `a21a0a4`。技术来源仍分别以 [`m02-source-audit.md`](m02-source-audit.md) 和 [`m03-source-audit.md`](m03-source-audit.md) 为准；lab normative scope 仍由 [`../labs/02-state-ownership.md`](../labs/02-state-ownership.md) 与 [`../labs/03-testing-evidence.md`](../labs/03-testing-evidence.md) 决定。

## 1. 为什么按 M02–M03 顺序成批

本轮没有按页面长度或格式碎片程度挑最容易的章节，而是按概念依赖继续 M00–M01：

- M01 已经建立 contract / invariant / authority-gap 的问题，但还没有回答“谁有资格改变 authoritative state”；M02 正好接这个问题。
- M02 的 running pressure 是 TaskForge v0 六个 tests 全绿，但 `service.get()` 暴露 authoritative mutable `Job`，caller 仍能绕过 lifecycle rule 改状态。
- M03 直接复用这件事：如果一个已经明确的 ownership defect 能在全绿 suite 下存在，那么 testing 的下一问就不是“多写几个 pytest”，而是怎样建立有 authority 的 executable evidence。

因此两章共享一条故事线：

```text
contract / invariant
  -> 谁拥有事实和 mutation authority
  -> read boundary 为什么不能泄漏 authority
  -> tests 为什么没发现它
  -> oracle / partition / boundary / fidelity
  -> fail-before / negative control / remaining risk
```

M05 以后没有混入本批，避免一次 PR 同时审 refactoring / legacy / concurrency 等更多 authority。

## 2. M02 semantic mapping

| baseline concept cluster | rewrite placement | preservation note |
|---|---|---|
| abstraction / representation independence | §1–§2 | 由 `service.get()` mutable alias 与 dict→SQLite pressure 逼出；保留 contract 可能合法包含 performance/ordering/durability 的 limitation |
| interface 不只是 signature | §2 | 保留 formal + informal interface、ordering/state/failure/staleness 等语义面 |
| information hiding / leakage | §3 | 用现有 `Job.terminal` 作为已局部化 knowledge 的正例，再对比仍分散的 transition / collection knowledge |
| change amplification / representation exposure | §3 | 区分 unavoidable public-contract change 与 duplicated-knowledge accidental change；保留 mutable representation exposure |
| temporal decomposition | §3 | 保留按 runtime phase 拆 module 可能复制 cohesive design knowledge 的风险，不写成“阶段拆分永远错” |
| deep module / shallow wrapper | §4 | 保留 heuristic；明确不支持“大类更好”或 depth score |
| DRY vs knowledge duplication | §4 | 继续区分 duplicated syntax 与 duplicated design knowledge |
| state ownership taxonomy | §5 | authority / storage / replica-cache / view-projection 明确分开；标注为 course synthesis |
| storage != semantic authority | §5 | 保留 database 可承担部分 invariant enforcement 的 qualifier，不把 application owner 写成唯一部署形态 |
| request transition != authoritative transition | §5 | 用 future remote-worker report 做 foreshadowing，但不提前命名后续 attempt/lease abstraction |
| split authority / global mutable state | §6 | 保留“物理上一份 object 也可能有多个 semantic writers”以及 ambient authority |
| observer != resource owner | §6 | 保留 CS190 Raft review 的 socket-lifecycle reasoning，不把 failure detection 自动等同于 recovery authority |
| semantic operation API / query-command asymmetry | §7 | owner 接受 domain operation；read projection/cache 可以存在，但不得成为第二 write authority |
| design it twice | §8 | 比较 Job-local transition 与 Registry-like owner；没有把 Registry pattern 升成唯一答案 |
| dependency direction | §8 | 只有在隐藏真实 variation / knowledge 时才值得增加 boundary；拒绝 interface-for-interface’s-sake |
| read-only reconnaissance / authority map | §9 | 恢复为可复用 Agent artifact；先读 owner/writer/invariant/projection/recovery，再修改 |
| M02 lab contract | §9 | 明确保留 job-N / monotonic ID / insertion-order claim 是本次 ownership exercise 的 Must preserve，并保留所有 non-goals |
| review questions / provenance | §10 | 按 representation / hiding / ownership / change 重新编组；source-backed 与 course synthesis 边界保留 |

## 3. M03 semantic mapping

| baseline concept cluster | rewrite placement | preservation note |
|---|---|---|
| test as executable evidence / oracle authority | §1 | 从“六个绿灯仍漏 ownership defect”开始；明确 tests 不等于 correctness proof |
| correctness / thoroughness / size | §2 | 用 legal-vs-buggy implementation discriminator 解释，不把术语变成 checklist |
| gaps vs overspecification | §2 | supplied mutant survivor 与 exact `job-N` assertion 同时承担两侧压力 |
| behavior partitions / boundary values | §3 | input 扩展到 pre-state/history/failure；不机械展开笛卡尔积 |
| behavior vs method / public boundary | §4 | test semantic client boundary，而不是按 private decomposition 建目录；internal stable component 仍可有自己的 contract |
| interaction testing | §5 | 偏好 observable outcome，但 external side effect/protocol 本身是 contract 时 interaction 可以是正确 oracle |
| doubles / fidelity / size-vs-scope | §6 | 用 risk→evidence→minimum fidelity→cost 组织；保留 fake 会删除真实 failure semantics 的 limitation |
| failure injection | §6 | 保留 deterministic seam 的价值，同时明确还需更高 fidelity evidence |
| coverage | §7 | line/branch coverage 只提供 execution/gap evidence，不证明 oracle 或 semantics |
| mutation / negative control | §8 | 保留实际 3 killed / 3 survived baseline 以及补三条 behavior tests 后 6/6 supplied mutants killed；明确不是 completeness proof |
| fail-before -> pass-after | §9 | 以 M02 representation exposure 为 regression；先红再比较 fix candidate；不让 testing chapter 替 architecture 做决定 |
| property-based testing / shrinking | §10 | Hypothesis 作为 counterexample search；保留 property/domain 仍可能写错、shrinking 提升 diagnostic value 的 limitation |
| maintainability / DAMP / DRY | §11 | test 也会制造 change amplification；适当 duplication 可换 scenario clarity |
| snapshot / golden | §11 | 保留适用场景与 brittleness，明确 source audit 不支持 universal policy |
| flaky tests / test lifetime | §12 | flaky 破坏 signal authority；contract 的 eventual behavior 与 harness sleep 猜 timing 分开；test lifespan 跟 contract lifespan |
| speed / fidelity / portfolio | §13 | 不教固定 pyramid 比例；portfolio 由风险决定 |
| specification gap / characterization | §14 | testing 是严格 client；unknown-ID 等若无 authority 先暴露 spec gap；characterization 不等于永久正确性 |
| Agent task / independent review | §15 | task artifact 明确 claim、oracle、partition、boundary、fidelity、negative control、limits |
| reusable evidence record | §16 | 将 remaining risk 作为必须字段，而不是“all tests pass”结束 |
| M03 lab / case study | §17 | 保留实际 mutation output、opaque-ID exercise、representation-exposure fail-before、defensive-snapshot limitation |
| cross-course evidence language | §18 | 把 M04/M05/M06/M07/M08/M11/M12 的后续 evidence dependency 重新连接起来 |

## 4. Source / provenance spot check

### M02

- MIT 6.102 ADT / AF-RI materials 只承担 operation/specification、representation independence、representation exposure 与 invariant maintenance 等 source-backed reasoning。
- Stanford CS190 materials 继续承担 formal+informal interface、information leakage、temporal decomposition、deep-module heuristic、design-it-twice 和 Raft ownership review 等范围。
- `semantic authority / storage / replica-cache / view-projection / writer map / recovery rule` 仍明确标成 course synthesis，没有包装成 MIT/Stanford 原术语。
- Parnas 仍只作为 Stanford notes 的历史指向；source audit 没有完成一手逐段审计，因此正文没有把它单独升级成已核验 technical authority。

### M03

- MIT 6.102 继续承担 systematic partitioning、boundary values、suite correctness/thoroughness/size 以及 testing 是 validation 方法之一。
- Google testing materials 继续承担 change-enabling / behavior-oriented testing、size vs scope、coverage limitation、test-double fidelity 与 larger-test risk reasoning；没有把其组织政策复制成固定比例。
- Hypothesis 只承担 property/domain/counterexample/shrinking reasoning，没有写成 automatic proof 或 example-test replacement。
- mutmut 只校准 mutation workflow；本 lab 的六个 fault hypotheses 仍是课程自己的 selected mutants，`6/6 killed` 明确不是 mutation completeness proof。
- strict TDD、100% coverage、固定 test pyramid、mock-everything / mock-nothing、snapshot universal rule 都没有被提升成 source-backed universal prescription。

## 5. Abstraction dependency sweep

### M02

第一版曾在 future-owner 例子里提前写出 `attempt identity` / `lease`。这两个 abstraction 由后续章节建立，M02 此处并不需要它们才能理解“report completion != accept authoritative transition”。最终改成 generic `authoritative execution/recovery state`，只保留后续压力的 foreshadowing。

`JobView` 在 §2 第一次出现时明确是“一种候选边界”，后面 projection 分析也改成“前面候选边界里的 `JobView`”，避免一个 illustrative type 因重复出现被自然化成课程 canonical representation。

M00/M01 的 `CANCELLING` / `cancellation_requested` 只在开头用于解释**它们不属于当前 repo v0 baseline**，没有被带入 M02 的实际 authority model。

### M03

M03 在读者先拥有 “tests green but ownership defect remains” 以后才引出 oracle，再由 gap/overspecification 压力推出 partitions、boundary、fidelity、mutation 和 property-based testing。后半章的 mutation / property vocabulary 不在前置 narrative 中承担解释前提。

涉及多维 state 的例子不提前命名后续执行协议字段，只说“额外 durable flag 或其他 execution/recovery state”，避免 M03 为后续 concurrency/compatibility modules 偷建 canonical model。

## 6. Design-decision dependency sweep

### M02

- `JobView`、defensive copy、frozen projection 都保持为 candidate mechanisms；正文保护的是“read 不无意授予 authoritative mutation authority”。
- Job-local transition 与 Registry-like owner 都被真实比较；Registry 对当前 toy system 较直接，但正文同时记录 god-object / future-persistence trade-off，没有把 pattern 当唯一答案。
- database constraint 可以承担部分 invariant enforcement；没有把所有 semantic authority 机械放在 application controller。
- query/read model 可以与 command authority 不对称；没有把“一份数据”误写成“一份 physical representation”。

### M03

- representation-exposure regression test 保护 isolation property，不要求 immutable `JobView` 这一种实现。
- defensive snapshot 是 case-study 验证过的最小 candidate，但 shallow-copy limitation 保留。
- M02 lab 的 exact `job-N` preservation 与 M03 lab 后半段 opaque-ID contract 被明确区分：后者只是**本次 testing exercise 的 authority**，不替未来产品 contract 做最终决定。

## 7. State/model projection 与 temporal consistency

M02 把 authority/storage/replica/view 分开后，专门写明 projection 可以只表达部分 state，但 scope 必须显式；没有画出来的 state 不能让读者猜成“不存在”。这条规则同时回连 M00/M01 的 cancellation candidate 与后续 execution/recovery state。

M03 将同一规则迁移到 test partition：如果 contract 有两个 state dimension，只测 status 不能偷偷冒充完整 state evidence。§18 继续明确 acceptance / completion / recovery 是不同 temporal phase；downstream completion failure 不能 retroactively 改写已满足 contract 的 acceptance success，也不能用最终 terminal-state test 冒充 acceptance durability evidence。

当前 TaskForge v0 本身没有这些完整 distributed phases，因此正文只把它们作为跨章 evidence rule，没有伪造 v0 已经具备的状态字段或协议。

## 8. 本轮自审实际发现并修正的问题

1. **M02 factual regression：错误把 `metrics.py` 写成复制 terminal-status set。** 实际 v0 已经通过 `Job.terminal` 局部化这份 knowledge；已改为正例，真正分散的是 transition / collection authority。
2. **M02 design naturalization：`JobView` 第一版读起来像默认答案。** 已在首次出现和 projection 段都标明 candidate scope，并与 defensive copy / frozen projection 并列。
3. **M02/M03 contract authority 过宽：第一版把 M03 lab 的 opaque-ID contract 写成“长期 public contract”。** lab 本身只为 exercise 建立 authority；已收回为 lab-specific scope，并明确不决定未来产品 promise。
4. **跨章 abstraction leak：M02 future example 提前用了 `attempt identity` / `lease`。** 已改成 generic execution/recovery state。
5. **格式残留：若干一句话 `A != B` / slogan 仍被 `text` fence 包裹。** 已改回 prose；authority map、mutation output、Agent task contract、test-design record 等真正需要结构化阅读的 artifact 保留 fence。

这些修正都来自 original-vs-rewrite sweep，不是 reviewer comment 的机械 patch。

## 9. Cold-reader flow

不看旧标题，只按新版顺序检查“为什么此刻需要下一个概念”：

**M02**：六个 tests 全绿但 caller 能直接改事实 → dict/alias 暴露说明 client 知道太多 representation → representation-change pressure 逼出 abstraction → transition knowledge 分散逼出 information hiding → hidden knowledge 仍不足以约束 writers，于是需要 ownership → split authority / ambient state 展开 owner 的后果 → semantic-operation API 与 design-it-twice 才讨论具体 placement → 最后形成可执行的 read-only authority review。

**M03**：M02 defect 在全绿 suite 下存在 → 先问每个 test 实际声明什么以及 oracle authority → 同时看到 gap 与 overspecification → spec partitions / boundary 决定 test 应观察什么 → doubles/coverage 只能提供有限 evidence → mutation 与 fail-before 反过来检查 evidence channel → property-based testing 扩展 counterexample search → maintainability/flakiness/fidelity 解释长期成本 → 最后把这些 judgment 固化成 Agent task / evidence record。

这两条链都不依赖“先背完术语再看例子”。

## 10. 仍需独立 reviewer 判断

作者侧目前可以自证的是：主要 technical clusters 有 merge-base mapping，source limitations 和 lab non-goals 仍在，M02/M03 的 authority scope 已显式区分，state projection 与 temporal phase 没有被 prose 化时抹平。

不能由本记录自证的是：

- M02 从 information hiding 转到 state ownership 是否对第一次读者足够自然；
- M02 的 course-synthesis ownership taxonomy 是否仍然太密，需不需要再借 TaskForge 多走一步；
- M03 从 supplied mutants 进入 fail-before/property-based testing 后，running example 是否仍然连续；
- M02/M03 对同一 v0 baseline 的重复说明是否恰好够用，还是影响阅读节奏；
- 哪些被压缩的解释虽然 technically present，但对 cold reader 已经太薄。

因此 PR 仍应做独立 semantic/cold-reader review，而不能用 heading、line-count 或 fence-count 当完成证明。

## 11. Validation record

在未修改 `labs/taskforge` production/tests 的前提下，本批实际执行：

```bash
cd labs/taskforge
PYTHONPATH=src uv run --with pytest --no-project python -m pytest -q
PYTHONPATH=src uv run --with pytest --no-project python tools/mutation_probe.py
```

结果与正文引用一致：baseline `6 passed`；supplied mutation probe 为 `3 killed, 3 survived`，survivors 仍是 `terminal_forgets_cancelled`、`submit_drops_command`、`list_jobs_hides_terminal`。

仓库 hygiene 还执行了：

- `git diff --check`：通过；
- changed Markdown relative-link existence check：通过；
- changed-files secret scan：无 finding；
- `git status`：除两章 rewrite 和本 review record 外无其他 tracked/untracked change；
- 测试生成的 `.pytest_cache` 被 ignore，没有进入 diff；没有生成 `uv.lock` 或其他待提交临时文件。

这些结果只证明本批编辑没有破坏当前 lab baseline / probe 和基本仓库卫生；它们不替代本文件前述 semantic/cold-reader review。