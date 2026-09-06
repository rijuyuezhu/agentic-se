# M04 Editorial Pilot Review

这份记录服务于 issue #2 的 M04 pilot。它不是“作者自己 approve 自己”的替代品，而是把重写前后的 semantic mapping、已检查的 provenance boundary 和仍需 reviewer 独立判断的阅读问题显式留下来。

对照基线是 `main` 的 `653d0a1`；Editorial Guide 在本分支先独立提交，再开始改 M04。技术来源仍以 [`m04-source-audit.md`](m04-source-audit.md) 为准，本文件不新增 technical provenance。

## 1. Pilot 为什么选 M04

M04 原文的技术内容完整，但编辑结构尤其原子化。基线有 3043 行、77 个正文 H1、209 个 `text` fence 和 76 个 `---`。这些数字只用来定位结构问题，不是重写的验收指标。

M04 还有一个适合作为 pilot 的特点：已有 TaskForge `submit/get/cancel` boundary 可以自然承担 running example。原文中的大量概念其实可以被同一条问题链连接：

1. 四行函数签名看似简单；
2. raw input、mutable state 和 implementation exception 开始泄漏给 caller；
3. `cancel=False` 无法表达 lifecycle semantics；
4. timeout 让 caller 失去对 side effect 是否发生的判断；
5. blind retry 因而逼出 logical request identity；
6. request identity 又带来 idempotency state ownership、retention 和 compatibility 问题；
7. 最后把这些语义变成 behavior table、tests 和 Agent task contract。

这条线不需要改变 M04 的知识体系，只需要把原先被微型 section 切开的 reasoning 重新组织起来。

## 2. 当前结构变化

本轮不是按固定数字优化 Markdown。下面只记录结果，帮助 reviewer 快速确认重写确实改变了叙事单位：

| diagnostic | baseline | pilot |
|---|---:|---:|
| lines | 3043 | 643 |
| bytes | 48,566 | 43,113 |
| page-level H1 | 77 | 1 |
| H2 | 29 | 13 |
| H3 | 0 | 30 |
| `text` fences | 209 | 5 |
| `---` separators | 76 | 0 |

行数下降远大于字节数下降，主要原因是普通 prose 不再被拆成一两句一段再夹 `text` fence，而不是大规模删掉技术内容。

当前 `text` fence 主要用于真正需要等宽布局的状态机、时序或可复用 Agent task artifact；普通结论和简单 `A -> B` 不再默认借 code fence 高亮。

## 3. Narrative mapping：旧知识点现在落在哪里

这里按 reasoning cluster 映射，而不是机械列 75 个旧标题。一个 cluster 中如果多个旧 section 只是同一推理链的连续步骤，就在新版合并成一个 episode。

| baseline concept cluster | pilot section | preservation note |
|---|---|---|
| API 不只是 signature；boundary / shallow wrapper / pull complexity down | §1 | 由 TaskForge 四行 API 开场，先让 caller 问题出现，再引入 semantic compression；同时保留“过厚 boundary 会偷 caller policy”的反向限制 |
| parse / validate / precise representation / illegal states | §2 | 保留 `Command.parse`、validate-and-forget 的信息丢失问题，以及“不是所有 invariant 都能靠 type”限制 |
| validation before effect / no-effect contract | §2.2、§5.1、§11.4 | 保留 validation-before-mutation baseline，并把 distributed partial effect 和 no-effect limitation 放到 timeout episode 再解释一次 |
| cancel boolean、error taxonomy、collapse/preserve、human vs machine error identity | §3 | 先从 `cancel=False` 逼出 caller-action taxonomy；保留 message/reason/metadata distinction、error-class explosion critique |
| error translation / error ownership / eliminate-mask-collapse-surface | §3.2–§3.3 | 保留“拥有足够 domain context 的层才适合翻译”以及 error 不等于 exception；define-errors-out-of-existence 仍明确是 heuristic |
| API as state machine、state-specific API、staleness | §4 | 继续用 TaskForge lifecycle，保留 lease/capability 与 stale observation 的限制；没有把 type 当 freshness proof |
| temporal coupling / convenience flags / defaults | §4.1–§4.2、§6.6 | 保留 hidden state machine、factory/staged type trade-off，以及 defaults/optional request identity 会改变 semantics |
| timeout、failure vs unknown outcome、partial side effect | §5 | 由 response-lost sequence 连续推出 outcome unknown；明确 transport timeout 不能推出 server 未执行 |
| retry semantics / retry layer / backoff non-goal | §5.2 | 保留 operation + failure + layer 三方面判断；明确 backoff/jitter 留给后续模块，不用它掩盖 unsafe semantics |
| idempotency definition / response bytes / payload hash | §6、§6.1 | 保留 intended effect、same logical request；明确 logs/metrics 可重复，response bytes 可变化；payload equality 不代表 intent identity |
| request ID / same-id different-intent / dedup ownership / lifetime | §6.1–§6.3 | 保留 caller-provided identity、stable conflict、RequestRegistry 与 JobStore 各自 authority，以及 retention/lifetime coupling |
| exactly-once wording / specific effect guarantee | §6.4 | 保留 request accepted、job row、worker execution、external effect 等不同事实；只对具体 dedup effect 作承诺 |
| public/internal error vocabulary、diagnostics、observability、security | §3.1–§3.2、§6.6 | public semantic compression 与 richer internal diagnostics 现在在 error-translation episode 内一次讲完；public boundary 的 disclosure/security qualifier 保留；request identity 对 tracing/debugging 的 consequence 留在 identity episode 尾部 |
| boundary tests / semantic partitions / mutation thinking | §7 | 保留 behavior table、cancel/idempotency partitions、public error observation 与 mutation probes |
| exception vs Result / request-registry alternatives | §7.2 | 保留 design-it-twice；没有把一种 encoding 升成唯一答案 |
| Agent failure modes / task contract | §8 | 保留 wrapper proliferation、exception explosion、catch-all、string parsing、retry-everything、payload hash、validation-after-effect、type cosplay；恢复成可复用 task artifact |
| M04 lab contract | §9 | 保留 Submit/Get/Cancel normative semantics 和“不规定唯一实现”的评分依据 |
| review checklist | §10 | 重新按 Input+state / Success+error / Retry+identity / Ownership+evolution 编组，仍保留可扫描形式 |
| four transfer exercises | §11 | 原 Error taxonomy / Temporal coupling / Idempotency / No-effect 四个练习继续存在 |
| M01–M04 与后续模块连接 | §12 | 保留 contract → ownership → evidence → boundary 的关系，以及 M05/M07/M08/M09/M11 的后续压力 |

## 4. Source-audit claim spot check

以下逐项对照 `m04-source-audit.md`，重点检查最容易在 prose 化时被写成 universal rule 的地方。

### Stanford CS190 / APOSD：error complexity

**应保留的 claim**：public error taxonomy 应考虑 caller 可以采取的 action；多个低层 failure 在 public action 相同时可以考虑 collapse；define errors out of existence 是 heuristic，不是无条件规则。

**pilot**：§3.1 从 `cancel=False` 展开 caller branching；§3.3 明确 already-done 是否成功取决于 operation postcondition 和 caller 是否需要区分 replay。没有写成“error 越少越好”。

### Google AIP-193：machine-readable error contract

**应保留的 claim**：human message 与 machine identity 分离；reason/metadata 形成 compatibility surface；稳定 external vocabulary 不等于把内部诊断信息丢掉。

**pilot**：§3.1 保留 code/reason/message/metadata JSON 例子，并明确 message 可演化、machine fields 才承担 protocol identity；§3.2 把 richer internal diagnostics 与 public/internal vocabulary separation 放在 translation 当下解释；同时提醒 public metadata 是 disclosure surface。

### AIP-194 / RFC 9110：retry 与 intended effect

**应保留的 claim**：retry safety 不是“发生 error 就 retry”；取决于 operation semantics 与 failure；idempotency 约束 intended effect，不要求 logging 等内部 effect 只发生一次。

**pilot**：§5.2 明确 operation + failure + retry layer；§6 明确 log/metric/trace 可以每次发生，并拒绝用 HTTP method 标签代替业务 semantics。

### AIP-155 / AWS Builders' Library：request identity

**应保留的 claim**：caller-provided request identity 区分 logical request；payload equality 不能普遍表示 same intent；same id + different intent 必须有 stable handling；retry response 不必 byte-identical。

**pilot**：§6.1–§6.2 连续保留这些 distinctions；§6 先解释 queued → running 导致 response 可变化但 logical creation result 不变；§6.5 用 `create_vm` 做 transfer case。

### Parse, don't validate

**应保留的 claim**：已经验证出的信息应尽量保存在更精确 representation；但这是 ideal/heuristic，不代表所有 invariant 都应进入 type system。

**pilot**：§2 先展示 validate-and-forget，再给 `Command.parse`；§2.1 用 `job_id` 与 shared store 的 uniqueness/coordination 问题说明有些 invariant 不属于单个 local type。request identity 术语留到 timeout/retry 真正需要它以后才出现。

### gRPC materials

**应保留的 claim**：跨 process/network boundary 后，语言内部 exception type 通常不是合适的 external contract；课程借用的是 stable semantic vocabulary，而不是要求学生实现 gRPC。

**pilot**：§3 只使用 `NOT_FOUND` / `FAILED_PRECONDITION` 等作为可理解的 semantic categories，并明确“不要求一定采用 gRPC status code，也不要求一定用 exception”。没有把协议选择变成本章目标。

## 5. 本轮发现并修正的 semantic regression

第一版 rewrite 完成后，没有直接提交。对照旧文时发现三处被压得过薄：

1. **error type count 不是质量指标**：新版虽暗含 caller-action taxonomy，但丢了“把 lifecycle state-space mechanically 映射成 exception class-space”这个很有用的反例；已恢复到 §3.1。
2. **public boundary 也是 security/disclosure boundary**：新版最初只提 metadata 不泄 secret，不足以保留原文对 resource-existence leakage 和 authorization-before-effect 的提醒；已恢复到 §3.1。
3. **Agent task contract artifact**：新版最初把原来的 structured template 压成一句 prose；这损失了可直接迁移到 Agent workflow 的操作性；已在 §8 恢复为真正需要逐行阅读的 artifact，因此这里继续使用 `text` fence。

修补第 1、2 项时，一次精确编辑还误覆盖了两段已有 prose：caller-action taxonomy 和 human-message/machine-contract。后续 read-back 发现后已经立即恢复。这次失误本身也是为什么 issue #2 不能靠一次 bulk rewrite + format counts 验收的例子。

## 6. PR review 后的 dependency / flow refinement

独立 reviewer 对第一版 pilot 提出三点后，又重新按 Editorial Guide 的原则核了一遍，而不是直接照单修改。最后确认两类结构问题成立，并额外发现了同类遗漏：

1. **request identity 出现得太早**：不仅 §2.1/§2.2 提前用了 `request_id`，§3.2、§4.2、§5.2 也分别提前出现了 `request identity` / `idempotency` / `idempotent`。现在 §6 之前这些术语全部移除：§2.1 改用已在故事中的 `job_id` shared-state invariant，§2.2 直接用 blank command 演示 validation-after-effect；§3.2 改用 `sqlite3.OperationalError` 的不同 mechanism causes；§4–§5 只描述“重复执行是否制造额外 effect”，直到 timeout/retry 已经建立问题后才命名 idempotency。
2. **idempotency 后发生 narrative rewind**：原 §7 的 internal/external error vocabulary 与 diagnostics 实际属于 §3 的 translation 问题，因此合回 §3.2；但原 §7.2 convenience API 并不是 rewind，而是 request-identity contract 的直接 consequence，所以移动到 §6.6 而没有删除。`request_id` 对 log/trace/audit correlation 的影响只保留为 §6 尾部的一段 consequence，然后直接进入 executable evidence。
3. **mask/recover 教学上过薄**：原第一版只保留了术语。§3.3 现在增加 read replica A failure → fallback to replica B 的具体例子，并明确 fallback 全部失败时才需要 surface public failure；没有恢复成四个碎片化 subsection。

这轮修改后，§6 之前搜索 `request_id`、`request identity`、`logical intent`、`retention`、`idempotent*` 均为 0 次。这个数字本身不是质量指标，但它能验证“request identity 第一次命名发生在故事需要它之后”这一具体 dependency constraint。

## 7. Cold-reader flow review

第二遍 review 暂时不看旧标题，只按新版顺序问“读者为什么此刻需要下一个概念”。目前的因果链是：

- 四行 API 先暴露 caller 需要猜测的事实；
- raw input 说明 boundary 必须建立 stronger assumption；
- `cancel=False` 说明 error contract 不能只用一个粗 signal；
- lifecycle/staleness 说明 API 还在表达 state transition；
- timeout 破坏 caller 对 effect existence 的判断；
- retry 于是逼出 logical request identity，而不是作者突然开始讲 idempotency；
- identity state 进一步逼出 ownership/lifetime；
- 最后 behavior table/tests 才成为前面语义的 executable evidence。

这比基线“概念 → 定义 → 小例子 → 金句 → 下一个标题”的局部节奏更连续。

仍需 independent reviewer 特别检查：

- §3 error taxonomy 到 §4 state-machine surface 的过渡是否自然，还是仍像两个概念块拼接；
- §6 在 identity、ownership/lifetime、guarantee scope、transfer case、convenience contract 连续展开后是否仍保持同一 episode，而不是变成新的术语清单。

这两个判断不能通过 heading 数量回答。

## 8. Rhythm / generated-answer smell review

重写后专门搜索了连续的“真正……”“不是 X，而是 Y”“所以……”“这就是……”等表达。不是为了把某些词清零，而是检查它们是否在替 reasoning 做强调。

已删除多处没有新增语义的“真正”以及重复反差句，例如把“真正有价值的 boundary”改为直接说明 boundary 做什么；保留的 contrast 主要用于真实 semantic distinction，例如 timeout 只能推出 outcome unknown，不能推出 operation failed。

当前 bullet 主要集中在：Agent task artifact、lab normative contract、review questions 和 source list。它们本来就是 parallel/checklist/reference 信息，没有为了“像教材”强行 prose 化。

## 9. 与其他教材的 calibration

本轮只借鉴教学组织方式，不把这些材料当成 M04 technical provenance。

- MIT 6.102 的 readings 常让一个具体 representation / operation 先产生问题，再引入 formal vocabulary；这支持 M04 先让 `submit/cancel` 失败，再命名 boundary/error/idempotency distinctions。
- *Software Engineering at Google* 的长章通常先建立实践动机，再讨论 trade-off、规模效应和 exceptions，适合作为“不要把结论切成连续 slogans”的节奏参考。
- *Designing Data-Intensive Applications* 更常围绕一个系统问题及不同路线的 trade-off 展开，而不是按术语索引逐个定义；M04 的 timeout → retry → identity 重排借鉴的是这种 problem-oriented organization。
- Stanford CS190 继续作为 M04 的技术和 design-judgment 来源，但其公开 lecture notes 本来就是课堂提纲式 bullets，因此没有把它当正文 prose 模板。

对应 style calibration URL 已记录在 [`../EDITORIAL_GUIDE.md`](../EDITORIAL_GUIDE.md)。

## 10. 仍然不能由作者自证的部分

这个 pilot 目前可以自证的是：technical claims 有可追踪映射，主要 source limitations 仍在，lab contract 没有被 prose 化掉，Markdown hierarchy 已适合 canonical page/TOC。

它不能由格式统计或本文件自证的是：

- 一个第一次学习 API boundary 的读者是否真的更容易跟上；
- prose 是否仍残留过度整齐、过度解释的生成式节奏；
- running example 是否在 600+ 行长度内仍有足够连续性；
- 哪些解释被压缩后虽然 technically present，但教学上已经太薄。

因此 PR 应要求至少一轮独立 semantic review 和一轮 cold-reader/editing review。只有 reviewer 能从新版独立重建本章 argument，并在需要时从 baseline/source audit 找到遗漏，pilot 才值得推广到 M00–M13。
