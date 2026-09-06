# M08 Editorial Review — Compatibility / Migration Rewrite

## 1. Scope decision

本批只重写 M08，不把 M09 architecture 合并进来。

原因不是“每次只做一章”的机械规则，而是两章的核心 pressure 不同：M08 要回答的是 **old/new producers、consumers 与 durable artifacts 在时间上共存时，change contract 怎样成立**；M09 开始讨论 architecture / boundaries / coupling，是另一类 design authority。把两者合成一批会让 compatibility 的 temporal proof surface 与 architecture judgment 混在一起，也让 reviewer 很难判断 provenance 和 abstraction dependency。

本批 base 是 PR #12 merge 后的 `main`：`a9b697e`。M08 在此之前没有 editorial rewrite；`git log --follow` 显示其主要教学内容来自 `7eca6e8`，传统 SE extension 后续由 `653d0a1` 补充。

## 2. Baseline evidence before editing

先对真实 starter 和 teaching probe 建立 baseline：

```text
cd labs/taskforge
PYTHONPATH=src uv run --with pytest --no-project python -m pytest -q
=> 6 passed

PYTHONPATH=src uv run --with pytest --no-project python tools/m08_compat_probe.py
=> [OLD DATA READABLE] historical v1 fixture remains readable
=> [OLD READER ACCEPTS CURRENT WRITER] frozen R1 accepts default W1
=> [EXPECTED BREAK] frozen R1 rejects teaching v2
=> [STARTER LIMIT] current starter reader also rejects v2
=> [FAIL CLOSED] unknown future schema version rejects
```

Historical fixture SHA256 before editing：

```text
0cd8f674d54b3da7919c2a9f7b911fdea5b109399438595c471a6baee90d2ecc
```

真实代码 seam：

- `snapshot.py` 当前 `SCHEMA_VERSION = 1`；
- v1 wire job 是 flat `command`；
- current `loads_snapshot()` 只接受 v1；
- current default writer 只写 v1；
- `_legacy_v1_reader()` 是不可随当前 change 修改的 deployed-consumer model；
- teaching v2 `task={kind:"shell", command:...}` 只存在于 Lab/probe scenario，不是当前 production model。

这些事实决定了正文不能把“实现 R2/W2”写成已经发生的 product state，也不能把 `W2 -> R1` 的失败当作 parser bug。

## 3. Editorial shape before / after

Baseline module 约 1900 行，44 个 page-level H1（页面标题 + `# 0` 到 `# 43`），大量 `---` 和普通自然语言 `text` fence。虽然 technical surface 很完整，但 reader 经常经历“定义 → 口号 → 小表 → 下一微节”，snapshot running case 在中段才重新成为主线。

Rewrite 后 module 是一个页面标题，主要 reasoning cluster 为：

1. real v1/v2 mixed-version break；
2. compatibility matrix / surface / direction；
3. durable data、version marker 与 semantic fail-closed；
4. 从 `W2 -> R1` failure pressure 推出 staged migration；
5. cross-version evidence；
6. rollback 随 data universe 改变；
7. dual-read / lazy / eager / dual-write 等 mechanism 由 authority/failure model 决定；
8. SemVer 的 communication boundary；
9. dependency 作为第二个跨时间 contract；
10. migration completion / deprecation / anti-backsliding；
11. config/API transfer cases；
12. Agent task contract；
13. review questions；
14. source/course-synthesis boundary。

Case study 也从 answer-key-like 737 行压成一条 reference design analysis：先 freeze old world，再读 probe/matrix，再解释 boundary normalization、rollout authority、四个 operational events、rollback、rejected dual representation、evidence 与 dependency judgment。

Lab 保持操作手册结构，只修 semantic timeline，不为了 editorial style 把 deliverables/checklist prose 化。

## 4. Semantic-surface mapping

原 43 个微节没有按编号一一搬家，而是按 dependency 重新挂接：

- old §0–§4：v1/v2 accident、compatibility bool、surface、direction、durable data → 新 §1–§3；
- old §5–§10：version marker、no-bump cases、unknown handling、protobuf、SemVer 能/不能做什么 → 新 §3 与 §8；
- old §11–§13：dependency contract/graph/pinning → 新 §9；
- old §14–§17：parallel change、reader-before-writer、consumer inventory、rollback → 新 §4 与 §6；
- old §18–§21：lazy/eager/dual-write、dual-read、cleanup/backsliding → 新 §7 与 §10；
- old §22–§25：matrix test、golden fixture、frozen consumer、future-version fail closed → 新 §5；
- old §26–§28：config/API migration 与 breaking-cost ownership → 新 §11；
- old §29–§34：migration protocol、deployable phases、reversibility、completion evidence、permanent old reader、in-place alternatives → 新 §4/§6/§7/§10；
- old §35–§38：Agent anti-pattern、task contract、writer cutover separation、Lab target → 新 §12 + Lab/Case；
- old §39–§43：review checklist、prior-module connections、summary/preview/sources → 新 §13–§14；删除纯模板式“下一章预告”。

保留的是 technical claims 和 qualifiers，不保留旧 heading topology。

## 5. Abstraction dependency sweep

Cold-reader 主线刻意不从 SemVer、Parallel Change 或 migration taxonomy 开始。

正文先展示真实 v1 fixture/current W1/frozen R1，再给 teaching v2，运行 probe 得到 `W2 -> R1` failure。只有在“两个单独正确版本组合后仍失败”之后才命名 compatibility contract，并用 producer/consumer matrix表达问题。

Parallel Change 在 matrix 与 durable-data pressure 已建立后才出现；SemVer 更晚，作为“version number 能传达什么、不能证明什么”的 transfer concept；dependency 最后作为从 provider role 翻到 consumer role 的第二个 case。

前置 sweep 还特别检查：

- intro 没有提前要求 reader 理解 expand/migrate/contract；
- v2 `task.kind` 在被介绍为 teaching scenario 前不作为既定 product abstraction；
- writer cutover 在旧 reader failure 与 consumer migration pressure 出现后才被命名；
- Hyrum's Law 不在 public/observed behavior distinction 建立前承担 design authority。

## 6. Design-decision dependency / authority sweep

### Teaching v2 不是产品必然设计

Baseline 容易让读者把 nested `task` object 当成 TaskForge 已决定的未来 architecture。Rewrite 明确把它标成 M08 的 working migration target candidate。课程要教的是 evolution reasoning，不是强行证明这个 representation 必然正确。

### R2 dual-read / default W1 是当前 phase candidate，不是普遍 pattern

Reference/Lab 选择 capability expansion：R2 读 v1/v2、default W1 保持。这是由 `W2 -> R1` known incompatibility、可控 rollout ordering 和小型 JSON surface 推出来的 candidate；正文同时保留 lazy/eager/dual-write/new-store alternatives，并要求它们建立 authority/reconciliation model。

### Dual-read 不是普遍优于 dual-write

Rewrite 将“dual-read 通常更容易”收窄到 TaskForge case：single production writer authority + boundary normalization 能避免 split-write failure surface。对于其他系统，dual-write 仍可能是合理 candidate，但不能无 authority model。

### Contract 不等于机械删除 old reader

如果产品明确承诺长期导入 v1，v1 decoder 是 compatibility feature，而不是未完成 migration。需要明确结束的是 transitional burden。停止 W1 与停止 v1 reads 被拆成两个 independent lifecycle decisions。

## 7. State / model projection sweep

M08 没有一个像 M07 lifecycle enum 那样的单一 state model，但有两个容易冒充 complete model 的 projection。

第一是：

```text
Compatibility = surface × producer × consumer × direction × semantic expectation × time window
```

这是课程的 review aid，不是外部 source taxonomy，也不是完整系统 state；真实 project 还可能有 multiple stores、tenants、feature flags、protocol capabilities 等维度。

第二是 `R1/R2 × W1/W2` matrix。它只投影本章 snapshot surface 与两个教学版本。`W2 -> R1 = FAIL` 的意义是给 rollout 一个 known incompatibility，不是宣称所有 future TaskForge formats 都有相同方向关系。

## 8. Temporal-consistency sweep — 本轮最重要的 semantic correction

独立顺读 source audit / module / Lab / instructor case 后发现一个旧 artifact-chain inconsistency：

- source audit 正确描述 Fowler Parallel Change 为 `Expand -> Migrate clients -> Contract`；
- baseline module §14 也先这样解释；
- 但后续 rollout state machine、Lab 与 case 又把“所有 R2 readers 已部署”塞进 `Expand`，并把 `Phase M` 改名成 `Writer migration / writer cutover`。

这会把两个不同时间事件压进错误 phase name：**consumer migration** 与 **durable producer cutover**。

直接核对 Fowler/Danilo Sato 原文后确认：Migrate 的主体是 clients/usages；原文没有把 producer 开始写新 durable representation 定义为 Migrate。因此本轮不是简单把 reviewer-style wording统一，而是保留 source taxonomy，并把 TaskForge adaptation 显式写成：

```text
Expand capability
-> Migrate readers/consumers
-> Writer cutover
-> Contract/cleanup
```

Writer cutover 是课程为 durable producer/consumer lifecycle 额外显式化的 event，不冒充 Fowler source phase。

这也修正了 rollback reasoning：capability expansion / reader migration 在仍只写 W1 时，没有扩大 durable format universe；W2 cutover 后才可能让 R1 rollback target 失效。

## 9. Source/provenance review

本轮重新 spot-check 了最容易过度引用的三类来源。

### AIP-180

确认正文确有 source compatibility、wire compatibility、semantic compatibility。课程把“先区分 surface”推广到 file/config/DB 属于 course adaptation，不把 AIP 写成通用 storage taxonomy。

### Parallel Change

直接核原文确认三阶段及其主体：Expand supplier interface、Migrate clients/usages、Contract old form。TaskForge writer cutover 明确标成课程综合。

### Kubernetes API deprecation policy

第一轮独立审查时曾怀疑 source audit 是否把 Kubernetes deprecation policy 写成了过强的 storage/rollback authority。实际抓取并核对现行原文后，**这个怀疑不成立，已撤回**：policy 确实明确写到 persisted representations 的 decode/convert obligation、preferred/storage version 前进前 old/new support overlap，以及 upgrade 后 rollback 的要求（newer-only features 有例外）。因此 rewrite 保留这条 source authority，同时仍限定：TaskForge 只借 overlap/rollback reasoning，不复制 Kubernetes machinery。

其余 source boundary 保持：SemVer 是 public-API/version communication，不是 compatibility proof；SE at Google dependency/deprecation 的组织 assumptions 不自动泛化；protobuf 只作为 representation-specific counterexample。

## 10. Evidence authority sweep

Historical fixture 与 frozen reader承担不同 authority：

- fixture 证明 past producer artifact；它 byte-for-byte immutable 是为了防 evidence drift，不自动把 whitespace 升级成 public contract；
- frozen R1 证明 deployed/old consumer boundary；它不能随当前 PR 一起“修”；
- current-current roundtrip 只能证明 current agreement，不能替代 migration evidence；
- `W2 -> R1` known failure 应保留为 executable rollout constraint，而不是为了“全绿”改成兼容；
- unknown future version / task kind 应在 semantics unknown 时 fail closed，不能把 tolerant parsing 当目标本身。

## 11. Self-corrections during rewrite

1. **Source suspicion retracted**：最初怀疑 Kubernetes audit overclaim；核原文后确认 audit 的核心 claim有直接 source support，因此没有因怀疑而弱化正文。
2. **Phase-name collision**：发现 Fowler Migrate 与 TaskForge writer cutover 被旧 artifact chain 混用；拆成 source 3-phase + course 4-event timeline。
3. **Irreversibility overclaim**：baseline 把 writer cutover概括为“irreversible boundary”。Rewrite 改为 conditional：当前 teaching candidate 下 `W2 -> R1` 失败，所以 cutover 会缩小 rollback-compatible target set；有 down-conversion/compatible rollback reader 时并非普遍不可逆。
4. **V2 design authority**：nested task object 被降回 explicit teaching candidate，不伪装成前置模块已决定的 future TaskForge model。
5. **Contract overreach**：把“contract 阶段必须真的发生”改成 transitional burden 必须有 explicit removal/support decision；intentional long-term v1 reader 可保留。
6. **Rollback scope**：Lab Case A 的“为什么容易 rollback”收窄到 snapshot-format surface，避免从 W1 durability事实推出 whole-release rollback 一定简单。

## 12. Cold-reader / rhythm review

Rewrite 只保留真正需要 scan 的 matrix、timeline、Agent contract 和 reviewer checklist。普通 `A != B`、两行结论和箭头链不再大量使用 `text` fences。Technical fences 留给 JSON、shell、ASCII pipeline 和 artifact contracts。

章节不再用“定义 compatibility → 定义 surface → 定义 backward/forward...”启动，而是让 frozen old reader failure持续驱动前半章；SemVer/dependency 是后半章迁移概念的第二个应用场景，不是脱离 running case 的 extension appendix。

## 13. Final validation evidence

完成最后 semantic sweep 后重新运行：

```text
cd labs/taskforge
PYTHONPATH=src uv run --with pytest --no-project python -m pytest -q
=> 6 passed

PYTHONPATH=src uv run --with pytest --no-project python tools/m08_compat_probe.py
=> historical v1 fixture readable
=> default W1 accepted by frozen R1
=> frozen R1 rejects teaching W2
=> current starter R1 rejects teaching W2
=> unknown future version rejects

sha256sum fixtures/m08/snapshot-v1.json
=> 0cd8f674d54b3da7919c2a9f7b911fdea5b109399438595c471a6baee90d2ecc
```

Hygiene / structure：

- `git diff --check` PASS；
- changed Markdown fences balanced；
- relative Markdown links resolve；
- module 430 行、1 个 H1、0 个 page-level `---`；
- instructor case 245 行、1 个 H1、0 个 page-level `---`；
- stale phase/overclaim sweep 对 `Phase M = Writer`、`Expand phase only`、`irreversible boundary`、`contract 阶段必须真的发生` 等均无残留；
- Markdown secret scan 无 finding；
- 无新增 `uv.lock` / temp artifact。

这些检查只能证明 artifact/evidence consistency 和基础 hygiene；不能替代独立 cold-reader/semantic review。

## 14. 仍需要 independent reviewer 判断

本 review record 不是 self-approval。尤其值得 reviewer 独立判断：

- real starter/probe pressure 是否足够自然地 earn compatibility matrix，而不是 abstraction 仍来得太早；
- teaching v2 target 是否一直保持 candidate scope，没有在后文被自然化成 product truth；
- source 三阶段 Parallel Change 与 TaskForge 四个 operational events 的关系是否既准确又不会让读者混乱；
- writer cutover 的 rollback-boundary描述是否足够精确，没有从当前 matrix 推成 universal irreversibility；
- historical fixture / frozen consumer 的 evidence authority 是否区分得当；
- `ignore unknown` / fail-closed、protobuf counterexample 的 representation qualifiers 是否保住；
- permanent v1 import 与 unfinished compatibility debt 是否真正按 product policy 区分；
- SemVer/dependency section 是否已经成为 running model 的迁移应用，而不是另一个 detached mini-chapter；
- 大幅压缩后是否有任何 condition、non-goal、compatibility qualifier 或 source limitation 被写没。
