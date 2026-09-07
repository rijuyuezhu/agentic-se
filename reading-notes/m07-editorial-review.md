# M07 Editorial Review

这份记录服务于 issue #2 的 M07 rewrite。它不是作者自我 approve 的替代品，而是把本轮 scope、merge-base semantic mapping、provenance boundary、dependency sweep、自审修正与 validation evidence 留给独立 reviewer。

本分支从 `main` 的 `b7f30ed` 开始。M07 module / lab / case / source audit / teaching probe 自最初引入它们的 `1f74ad7` 起没有发生过内容漂移；因此 `b7f30ed` 既是本轮实际 merge-base，也保留了原 M07 的完整 technical baseline。本轮没有修改 M08，也没有扩大到 compatibility / migration 章节。

## 1. 为什么这一批只做 M07

M07 是课程第一次把前六章的 state / ownership / contract / evidence 放进真正的时间轴：两个 operation overlap 时，最后 state 不再足以说明 history；operation 中途 interruption 时，local bookkeeping 与 external effect 也不再天然同生共死。它的主要 proof obligations 是 interleaving、atomic decision、safety/liveness、failure horizon、timeout knowledge 与 retry semantics。

M08 转向 compatibility、migration、schema/protocol evolution，design authority 和 evidence surface 都不同。把 M07/M08 合在一批只会扩大 reviewer 需要同时重建的 reasoning model，因此本轮 scope 只包含：

- `modules/07-concurrency-lifecycle-failure.md` 的案例驱动 rewrite；
- 因真实 starter/probe 核对发现 temporal inconsistency 后，对 M07 Lab / instructor analysis / source audit 做最小 precision correction；
- 不改 production teaching code，不实现 Lab reference solution，不改后续模块。

## 2. Baseline evidence：先验证教材正在描述的真实 starter

重写前实际检查了：

- `src/taskforge/concurrent_claim.py`：`after_observe` 位于 `QUEUED` observation 与 `RUNNING + owner` commit 之间；starter 是明确的 check-then-act；
- `tools/m07_interleaving_probe.py`：两个 thread 通过 `threading.Barrier(2)` 都先观察同一个 queued job，能够 deterministic 地制造 two-success history；
- `src/taskforge/effect_delivery.py`：`completed_jobs` 是 process-local `set`；`deliver_once()` 先调用 external callback，再可选抛出 `SimulatedCrash`，最后才写 completion；
- `SimulatedCrash` 只是同进程异常；probe 捕获后在同一 Python process retry，并没有真正杀掉 / restart process。

重写前运行：

```text
PYTHONPATH=src uv run --with pytest --no-project python -m pytest -q
=> 6 passed

PYTHONPATH=src uv run --with pytest --no-project python tools/m07_interleaving_probe.py
=> [RACE REPRODUCED] one queued job produced two successful claims: worker-A, worker-B
=> [FINAL STATE] one RUNNING job and one recorded owner can hide the bad history
=> [CRASH REPRODUCED] effect happened, completion record was lost, retry produced a duplicate effect
=> [ORDER REVERSAL] recording completion first avoids duplication but can lose the effect
```

这组 evidence 是本轮 narrative 的起点，不把 instructor reference 当成 starter 的真实现状。

## 3. Narrative change：由两个 bad history 推出 abstraction

旧版有 33 个 page-level H1，主要节奏是“概念标题 → 定义 → 小例子 → 下一术语”。新版保留同一知识体系，但用两个真实 teaching target 连接 reasoning：

1. 一份 queued work 为什么能产生两个 successful claim，而最终 state 仍看起来正常；
2. 一个 external effect 已经发生、completion write 尚未发生时，为什么 retry 会重复；把语句倒过来又为什么不能凭空得到 exactly-once。

第一条先逼出 operation history，再命名 race；随后 sequential state-machine edge 不够表达 concurrent conflict，才需要 atomic semantic decision 和 linearization intuition。修掉 one-job safety 后再出现 two-job progress pressure，才引入 safety/liveness。确定性 barrier evidence 紧跟这条 race 主线。

第二条先运行真实 failpoint，再区分同进程 interruption 与真实 process crash；在明确 failure horizon 后才讨论 record/effect ordering、at-most/at-least candidates、effect authority、timeout 与 retry load。最后把这套 temporal model迁移到 running cancellation 与 owner restart/recovery，而不是一开始先列 cancellation / lease 术语。

## 4. Merge-base semantic mapping

这里按 reasoning cluster 映射，不机械保留 33 个旧标题。

| baseline cluster | rewrite location | preservation note |
|---|---|---|
| §0 two “final state looks fine” bugs；§1 concurrency；§2 race definition | §§1, 6 | double claim 与 effect interruption 仍是两个 running targets；race 只在 bad history 已建立后命名；concurrency 不收窄成 threads |
| §3 concurrent protocol；§4 check-then-act | §2 | sequential state machine 不足、edge 需要 conflict/decision semantics、message passing 也可能有 stale-observation protocol race 均保留 |
| §5 atomicity；§6 linearization point | §§2–3 | function boundary 不等于 atomicity boundary；先建立“哪些 facts 必须一起生效”的需求，再引入 Herlihy-Wing conceptual model；不要求 formal proof |
| §7 safety/liveness；§9 lock rationale；§10 critical section | §4 | one-job safety 与 two-job progress 分开；lock 只是 candidate；re-check、critical-section scope 与 blocking I/O qualifier 保留 |
| §8 shared memory/message passing authority | §§1–2 | mutation confinement 不自动解决 protocol race；semantic operation 应位于 authority 内部 |
| §20 deterministic interleaving；§22 final state；§23 history testing | §§1, 5 | 真实 `Barrier` 先复现 race；oracle 检查 receipts/history 而不只检查 final status/owner；stress-only limitation 保留 |
| §24 all writers；§25 deadlock review | §§4, 11 | writer map、跨 representation invariant、lock-order cycle / liveness review 均保留 |
| §11 crash vs exception；§12 failure window | §6 | `finally` 与 process death distinction、effect/record ordering analysis 保留；并进一步修正 starter failpoint vs real restart 的 evidence scope |
| §13 timeout as knowledge failure | §8 | timeout 仍只说明 caller 未确认 outcome，不推出 operation failed；与 M04 request identity 连接但不把 request dedup扩大到 downstream effect |
| §14 delivery guarantees；§15 idempotency | §7 | at-most/at-least/transaction/idempotent-sink candidates 保留；exactly-once 必须具体到 effect boundary；sink guarantee 不升级成 whole-job guarantee |
| §16 retry load；§17 backoff/jitter | §8 | retry amplification、明确 max-attempt wording、backoff/jitter 对 schedule 的影响保留；duplicate semantics 与 load/liveness proof obligation 分开 |
| §18 cancellation；§19 lease/heartbeat | §9 | cancel accepted 与 work stopped 分离；`CANCELLING` 与 independent cancellation-request projection 都是 candidate；lease/heartbeat/fencing 只作为 restart pressure 下的后续 reasoning，不升级为唯一 architecture |
| §21 deterministic failure injection | §§6, 11 | explicit failpoint 保留，同时明确它的 failure model；不让“deterministic”变成“证明了真实 restart” |
| §26–§28 Agent pseudo-fix / task contracts | §10 | invariant、interleaving、linearization、safety/liveness、non-goal、evidence 继续作为 task contract；不要求固定 primitive |
| §29 review checklist | §11 | 按 authority/projection、interleaving、safety/liveness、failure/retry、evidence 重组 |
| §30 lab targets | §12 | double claim 与 external effect 两种不同 answer type 均保留；前者可 local atomic decision，后者缺任意 external callback exactly-once mechanism |
| §31 previous modules；§32 mental model | §14 | M01–M06 continuity 保留，并用一条 invocation → commit → effect → interruption → response → timeout → retry 时间轴收束 |

## 5. Provenance / source-course-synthesis boundary

本轮没有引入新的外部技术来源。正文继续按 `m07-source-audit.md` 的边界使用材料：

- MIT 6.102 Concurrency：shared-memory / message-passing concurrency、race framing、ordinary testing 对 race 的困难；
- MIT 6.102 Mutual Exclusion：interleaving around yield/await、mutual exclusion、safety/liveness、deadlock reasoning；Python/threading mechanism 是课程迁移；
- MIT Message Passing & Networking：mutation confinement 不等于完整 protocol correctness；
- Herlihy & Wing：invocation/response history 与 linearization-point intuition；不扩成 formal proof、nonblocking hierarchy 或“所有 workflow 必须 linearizable”；
- Google SRE：retry amplification、retry budget / limited attempts、backoff/jitter 与 cascading-failure reasoning；
- AWS backoff/jitter：synchronized retry schedule 的补充说明。

下面这些明确保持在 **course synthesis / local fixture reasoning** 一侧：

- `Barrier` / failpoint 作为 deterministic teaching evidence 的具体设计；
- TaskForge double-claim writer/owner model；
- effect-first / record-first comparison，以及 at-most/at-least/exactly-once 在具体 effect boundary 上的工程推理；
- cancellation representation candidates 与 `cancel accepted` / `work stopped` temporal split；
- lease / heartbeat / fencing 的 restart-recovery extension；
- Agent task-contract workflow；
- 本轮新增的 `completed_jobs` durability precision。

特别是 crash/restart 不能偷偷借 MIT concurrency 或 SRE retry material获得并不存在的 distributed durability authority。source audit 已增加 fixture-specific clarification：当前 `completed_jobs` 是 in-memory set，probe 直接支持 ordering counterexample，不支持“starter 已实现 restart recovery”。

## 6. Abstraction-dependency sweep

第二遍不按标题读，而是检查 canonical vocabulary 第一次出现时，读者是否已经有问题需要它。

- `race condition`：在 double-claim concrete history 和 final-state insufficiency 之后才正式命名；
- atomic semantic decision：在 protocol table 已要求“QUEUED predicate 与 committed owner/result 必须一起成立”之后出现；
- linearizability / linearization point：在读者已经需要回答“operation 到底在哪一刻算发生”之后出现；
- safety / liveness：在 lock/re-check candidate 已经能修 one-job safety、但 two-job loser 可能不 progress 后展开；
- history-oriented evidence：在 final-state oracle 已明确漏掉 two-success history 后出现；
- record/effect failure-window vocabulary：在真实 `SimulatedCrash` ordering hole 已出现后使用；
- at-most / at-least / idempotent sink：在 effect-first 与 durable-record thought experiment 已展示 duplicate/loss trade-off 后才比较；
- `CANCELLING`：先建立 cancellation acceptance 与 actual stop 是不同时间点，再作为一个 representation candidate；
- lease / fencing：只在 owner disappearance / stale-owner conflict 已产生压力后命名。

自审第一版曾在导语里提前列 `history / interleaving / atomic decision / failure window`，并在 early projection paragraph 提前点名 `lease`。两处都已收回成 problem-level wording，避免 summary-like forward leak。

## 7. Design-decision dependency / design authority

本轮专门检查了 instructor reference 是否被 prose 偷偷升级成唯一答案。

- claim fix：正文先说明 invariant / atomic-decision criteria，再列 mutex、CAS、DB conditional update、single-owner handler 等 mechanisms；之后才说 instructor reference 选择 short lock + re-check。Lab 的 Design It Twice 仍保留；
- `after_observe`：解释为什么 reference 把 teaching barrier seam 留在 lock 外，但这只是当前 deterministic fixture requirement，不把 instrumentation layout 泛化成 production rule；
- progress：增加 current first-eligible / insertion-order selection semantic qualifier，避免“loser continue”只保 liveness 却顺手改 selection behavior；
- crash guarantee：at-most / at-least / transactional coordination 是 design choices；当前 starter 不提供任意 external effect exactly-once；
- idempotent sink：只对 sink-owned logical effect ID 给 guarantee，不推成 job/process/filesystem exactly-once；
- cancellation：`CANCELLING` 与独立 cancellation-request projection 都明确是 candidate；
- lease/fencing：只有在设计真的选择 time-bounded ownership/reclaim 后才相关，而且 M07 不展开完整 distributed protocol。

因此正文没有把“reference 做了什么”改写成“学生必须这么做”。

## 8. State / model projection sweep

M07 很容易因为并发需要新增 owner/cancel/recovery facts，而让一张简单 state machine 冒充 complete model。本轮明确留下三个 scope marker：

1. §2 lifecycle operation table 是本章当前 claim/cancel/finish conflict 的 **projection**，不是 TaskForge 完整 state；其中 current starter 的 `finish` 只要求 `RUNNING`，没有 claimant-identity check；owner-restricted finish 只能作为 future protocol candidate；
2. starter 的 `Job.status` 与 `claim_owners` 分处两个 mutable location 是 teaching fixture，用来暴露跨 representation invariant，不是 production two-authority recommendation；
3. cancellation 可以用 lifecycle state，也可以用 orthogonal request-state projection；选择哪种 representation 取决于 caller distinction / transition semantics，不机械把所有维度塞进一个 enum。

Review checklist 也直接要求 reviewer 问“这是完整 state 还是明确 scope 的 projection”。

## 9. Temporal-consistency sweep

本章的核心风险不是 state 名字本身，而是不同阶段被 prose 混成一个时刻。

### Claim

`observe QUEUED`、commit `RUNNING + owner`、return success receipt 被区分；stale observation 必须在 commit boundary re-check。最终一个 owner 不能抹掉已经发生的 two-success history。

### Effect delivery / crash

本轮独立核对真实代码后发现 baseline Lab/Case 有一个 temporal precision seam：`SimulatedCrash` 是同进程 exception，而 `completed_jobs` 是 in-memory set；原 failure table 的 `restart/retry outcome` 容易让读者误以为 completion record 能跨真实 process restart 保留。

当前修正后：

- effect-first starter table只声称同进程 failpoint / retry 的 ordering evidence；
- record-first 表被明确标成 **durable-record thought experiment**，需要额外 assumption：record 能跨目标 failure horizon 留存；
- Option B at-most-once candidate 明确要求 durable、竞争 caller 不能重复创建的 attempt record；当前 starter set 不满足；
- real restart 还需要 durable work identity / recovery trigger；
- 即使 record durable，record-first 也只把 duplicate window 换成 loss window，仍不是 exactly-once。

这项修正同步进入 module、Lab、instructor analysis 与 source audit，而没有修改 teaching code 来伪装已有 durability。

### Cancellation

`cancel request accepted`、signal / stop、cleanup、terminal record 保持为不同 temporal facts。若 public `CANCELLED` 意味着 command 已不再执行，就不能在“request 仅被接受”时提前写它；后续 termination failure 也不能 retroactively 把 acceptance success 改写成“当初没有接受”，除非 contract 明说如此。

finish 与 cancellation acknowledgment overlap 时，谁赢是 product contract / conflict semantics，而不是“最后一次 write wins”。

## 10. Cold-reader flow review

当前因果链是：

```text
one queued job -> two success receipts
        ↓
final state cannot explain correctness
        ↓
race / concurrent protocol
        ↓
which facts must commit together?
        ↓
linearization intuition
        ↓
one-job safety fixed, but can work still progress?
        ↓
safety + liveness + deterministic history evidence
        ↓
external effect happened but completion write did not
        ↓
what exactly survives this interruption?
        ↓
delivery guarantee / effect authority
        ↓
timeout + retry add ambiguity and load
        ↓
cancellation / owner restart reuse the same temporal questions
```

M04–M06 的内容只在故事需要时回接，例如 timeout/request identity、state ownership、executable evidence；没有先做“前情知识点回顾”再进入 M07。

仍需 independent cold-reader 特别检查：

- §2 protocol table 到 §3 linearizability 是否足够自然，还是仍有“现在开始讲理论”的感觉；
- §6 从同进程 failpoint 转向 durable-record thought experiment 时，failure-horizon distinction 是否清楚而不过度打断叙事；
- §9 cancellation + restart 是否是前面 temporal model 的真实迁移，还是尾部又开始堆术语。

## 11. Compression / rhythm review

baseline module 1666 行，33 个 page-level H1。当前 module 约 500 行、1 个 H1；行数下降主要来自把微 section / separator / text-fence answer cards 合并成连续 episode，而不是把 33 个概念删成 14 个 bullet。

正文的 `text` fence 目前主要保留给真正需要逐行读取的 interleaving、state/sequence diagram、failure history、Agent task artifact 与 final timeline。普通结论不再默认放进 fence。

没有为追求 prose 感而删除 behavior table、failure table、task contract 或 review checklist；这些本来就是结构化工程 artifact。

## 12. 本轮 self-correction

第一版 rewrite 后没有直接提交。独立对照 dependency / real probe 时修了五类问题：

1. **abstraction leak**：导语提前列出后文 canonical vocabulary；改为只描述时间裂缝本身；
2. **future-design leak**：early projection 段提前点名 lease / attempt generation；改成 cancellation / ownership / recovery 的 generic contract dimension；
3. **selection qualifier**：Agent task constraints 最初只写 stale candidate 要继续，没显式保留 current first-eligible / insertion-order selection semantics；已补回；
4. **failure-horizon inconsistency**：真实 `completed_jobs` / `SimulatedCrash` 与 Lab/Case `restart/retry` wording 不一致；已按 §9 的 precision 统一修正，并在 source audit 标明是 repo-fixture/course-synthesis clarification；
5. **delivery-guarantee scope**：最初把 “at-least-once attempt/effect” 写得过宽，并让 lifecycle crash table 的 `Durable/local facts` 暗示了未建立的 durability。现在把 at-most/at-least 明确收窄到 attempt admission/retry；external effect guarantee 另由 effect owner / failure point 决定；lifecycle table 也改成 durability-neutral 的 state-side facts，并把“哪些 facts 跨 failure 留存”本身列为 recovery contract。

这些修正比 heading/count hygiene 更重要，因为它们直接影响 abstraction dependency、design authority 与 temporal correctness。

### PR review 后的独立复核

收到 PR review 后没有直接照单修改，而是重新核了 Herlihy–Wing 定义、当前 Lab 全 occurrence、`worker.finish()` 与 M02 authority。三条 finding 都成立，并按更窄边界修正：

1. **linearizability uniqueness**：论文定义要求存在 legal sequential history 且保持 real-time precedence，并明确允许一个 history 有多个 extension / linearization。Lab 已从“没有唯一答案就是错”改成 history-level existential check；concrete implementation 仍需要说明 candidate linearization point / region。module 与 source audit 同步补上这个 qualifier；
2. **attempt/effect artifact-chain**：做了完整 occurrence sweep。Lab 不再把 effect-first table 命名成 `at-least-once attempt/effect`；Option A 拆成 attempt/retry policy 与 sink-owned idempotent logical effect 两个独立前提；Option B 明确只直接约束 admitted attempt，不能推出 arbitrary external effect at-most-once；最终交付物也分别要求 attempt/retry policy 与 scoped external-effect guarantee；module 的 Agent task contract 同样拆开两类 design decision；
3. **finish owner authority**：真实 `worker.finish(job_id, exit_code)` 只检查 `RUNNING`，M02 的 owner 是 state write authority，不是 claimant identity。正文已把 claimant-bound finish 降为 future product/protocol candidate，没有新增 worker-owner implementation。

## 13. Final validation evidence

最终文档改动不修改 TaskForge teaching code，但仍重新运行 affected evidence：

```text
cd labs/taskforge
PYTHONPATH=src uv run --with pytest --no-project python -m pytest -q
=> 6 passed

PYTHONPATH=src uv run --with pytest --no-project python tools/m07_interleaving_probe.py
=> deterministic double-claim reproduced
=> final-state/history mismatch reproduced
=> effect-before-record duplicate reproduced
=> record-first loss trade-off reproduced
```

并检查：`git diff --check`；changed Markdown 的两条 relative links 均存在；M07 module 只有一个 H1、无 page-level `---` separator；Markdown secret scan 无 finding；工作区没有新增 lockfile / temp artifact。

这些检查证明的是本轮文档与 teaching evidence 一致、基本 hygiene 闭合；它们不替代 semantic / cold-reader review。

## 14. 仍不能由作者自证的部分

本轮可以自证的是：merge-base concepts 有 mapping，来源 limitations 仍在，真实 starter/probe 已实际核过，几个 design candidates 没被偷偷升级成唯一答案，failure horizon 的新 precision 与代码一致。

仍需要 reviewer 独立判断：

- cold reader 是否真的能从 two-success history 自己重建“为什么 final state 不够”；
- linearizability 的压缩是否保留了恰当的 qualifier，而没有把 formal concept 教成模糊的“某个 commit line”；
- crash/effect 章节在加入 durability precision 后是否仍保持清晰，而不是变成 caveat 堆积；
- cancellation / lease transfer 是否超过 M07 当前需要的深度；
- baseline 里是否还有某个重要 qualifier 虽“提到了”但教学解释已经压得太薄。

因此 Draft PR 应继续要求 semantic review + cold-reader/editorial review；本文件不构成 approve。

## 15. Issue #2 closure pass — instructor-case regrouping

2026-09-07 closure review 认为 M07 module 与 technical reasoning 已经闭环，但 instructor case 仍保留初版 `Reference 结论 -> 19 个逐题解释` 的 answer-key节奏。这里不需要再次改 M07 design；只把已有 evidence / reasoning 重组为连续 engineering analysis，并让 final judgment 放回证据之后。

本轮只重组 `case-studies/m07/instructor-analysis.md`。新 spine 是：two-success history -> atomic semantic decision / linearization -> deterministic instrumentation + progress -> effect/record failure window -> effect-owner authority -> timeout/retry load -> cancellation transfer -> rejected fixes -> Review Agent -> instructor judgment。

Semantic preservation 特别复核：

- two success receipts / final-state masking 仍是第一条 history-level counterexample；
- reference short lock + re-check 仍只是 candidate mechanism，mutex/CAS/conditional update/single-owner handler 的 legal set 保持开放；
- Herlihy-Wing qualifier 仍是“存在 legal sequential explanation并保持 real-time precedence”，同一个 history 可以有多个 valid linearizations；具体 reference 才定位自己的 candidate atomic region；
- `after_observe` 放 lock 外继续只服务 deterministic teaching fixture，避免 barrier-under-lock deadlock，不推广成 production rule；
- loser `continue` 仍保护 current first-eligible/insertion-order progress semantics；
- `concurrent_claim.py` 仍是 teaching isolation，不是多个 production claim authority 的推荐；
- `completed_jobs` 仍是 in-memory set，`SimulatedCrash` 仍是 same-process failpoint；probe 不声称真实 restart recovery；
- record-first reasoning 仍明确需要额外 durable-record assumption，并且只把 duplicate window 换成 loss window；
- idempotent sink guarantee 仍只覆盖 sink-owned logical effect ID，不扩张成 whole-job / arbitrary external exactly-once；
- request identity 与 effect identity/authority 继续分开；27/64 retry-amplification wording 保留；
- `CANCELLING` 与 orthogonal cancellation-request representation 继续作为 alternatives；current `worker.finish()` 没有 claimant-identity contract，owner-bound finish 仍只作为 future protocol candidate；
- attempt/retry policy 与 external-effect guarantee 继续是两个不同 proof obligations。

Canonical validation 重新得到 core `6 passed`，M07 probe 仍稳定重放 double claim、final-state masking、effect-before-record duplicate 与 record-first loss trade-off。Historical `9 passed` 继续只表示临时 instructor reference 的 3 个 focused tests，而不是 canonical starter acceptance oracle。
