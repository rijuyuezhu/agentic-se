# M05 Editorial Review — Refactoring 与 Evolutionary Design

> 本记录用于 issue #2 的 M05 教材重写自审。它不新增技术来源，也不替代独立 reviewer；目标是让“压缩了大量碎片标题以后，哪些语义被保留、哪些依赖被重新排序”可以被检查。

## 1. 为什么这一批只做 M05

M05 与 M06 在课程顺序上连续，但不是同一个 semantic-review unit。

M05 的前提是：当前 behavior 已经比较清楚，core tests 与 dashboard behavior probe 都可运行。它训练的是在这种条件下怎样区分 structural change 与 behavioral change，怎样比较 direct feature 与 preparatory path，并把一次变化拆成可独立验证的 checkpoints。

M06 刻意拿走这些前提：现有行为不完整、feedback 弱、环境依赖难控制，于是要建立 characterization、sensing/separation 与 seam reasoning。它使用另一套 running case `legacy_audit.py`，主干 provenance 也换成 Feathers/WELC。

把两章放进同一 rewrite PR 会让 reviewer 同时审“behavior-preserving 的证据 authority”和“行为未知时怎样建立 authority”。因此本批只重写 M05，M06 留给下一批顺序处理。

## 2. Baseline 与 running pressure

重写前实际运行：

```bash
cd labs/taskforge
PYTHONPATH=src uv run --with pytest --no-project python -m pytest -q
PYTHONPATH=src uv run --with pytest --no-project python tools/m05_behavior_probe.py
```

结果：core suite `6 passed`；dashboard probe 三个 scenario 分别为：

```text
empty   eaadf634b7104332
queued  ec17ac5523b4b8bd
mixed   1181854b1e08cc1c
```

当前 `render_dashboard()` 是故意设计的 M05 fixture：行为对当前 contract 是正确的，但读取 jobs、解释 lifecycle、累计 counts、计算 active/terminal、构造 text-specific status label 与最终 formatting 混在一个函数里。

新版主线以一个单一压力推进：**增加 JSON dashboard。** 直接复制现有逻辑是 plausible path；先隔离 shared facts 也是 plausible path。读者先看到两个都能工作的选择及其代价，再形成 refactoring / Two Hats / preparatory refactoring / semantic checkpoint / change topology 等判断工具。

## 3. Merge-base semantic preservation map

下面按原 M05 的 concept cluster，而不是旧 heading 数量，对照新版落点。

| Merge-base cluster | Rewrite placement / preservation |
|---|---|
| Refactoring 的窄定义：改内部结构、保持 observable behavior | §2；明确把 narrow definition 作为 proof-obligation boundary |
| small transformations / working state | §2、§7–§8；不转写成固定 LOC |
| Agent 让 implementation bandwidth 上升，但 review/test/rollback 不会自动变便宜 | §12–§14 |
| proof obligation 与 behavior inventory | §2–§3；先实际给出 M05 probe，再声明 text byte-preservation scope |
| observable behavior 不只 return value | §3；保留 errors、state/files、ordering、timing/callback、config、RPC/persistence，以及 performance 仅在成为 promise 时进入 contract 的 qualifier |
| documented contract 与 observed compatibility surface 的张力 | §3；不再提前命名 M08 才主讲的 Hyrum's Law，但保留“未文档化行为也可能已有 consumer”的 engineering constraint |
| Two Hats / structure vs behavior | §4；bugfix、error-contract change、optimization 都作为不同 proof obligation |
| bugfix 不应藏进 pure refactor | §4 |
| M04 error boundary：`KeyError -> ApiError` 即使更好也属于 behavior/API change | §4；重新补回具体跨章例子 |
| optimization 与 functional refactor 分开 review | §4；保留 benchmark/resource evidence qualifier |
| Direct Feature 与 Preparatory + Feature 都是合法设计候选 | §1、§5、§6、§11；Direct 的低 initial cost 被正面保留 |
| duplicated knowledge ≠ duplicated syntax；abstraction count 不是成功指标 | §5；从 status/count interpretation 与 `status_text` 推出 |
| normalized dashboard model 不应包含 `succeeded(0)` 这种 presentation string | §5；raw status + exit_code reasoning 保留 |
| M02 state ownership / projection：dashboard snapshot 不能成为第二份 authority | §5；显式说明 projection 可重建，mutable second truth source 是 ownership regression |
| Preparatory Refactoring | §6；在 direct/shared-facts 两条路径都走过后才第一次正式命名 |
| Preparatory ≠ speculative cleanup | §6；限定为近端 pressure，并拒绝借 JSON 全仓 cleanup |
| First / After / Later / Never | §6；保留为 timing trade-off，不写成四个固定流程 |
| refactoring ROI / economics / option value | §10；只做粗粒度 cost/risk/review/rollback 比较，并明确不是精确 ROI 定律 |
| Small change 不是 LOC threshold | §7；以 500-file mechanical rename vs 20-line semantic mix 迁移场景检查 |
| semantic checkpoint | §7；明确标成 course synthesis，并保留 coherent/runnable/single-purpose/evidence/failure-localization/rollback criteria |
| change topology / intermediate validity | §7、§10、§12；明确标成 course synthesis |
| final tests green 不足以证明 whole mixed patch | §8；把 checkpoint 与 failure localization 绑定 |
| evidence 要与具体 structural claim 匹配 | §8；rename/error translation/serialization 使用不同 evidence |
| 当前 M05 dashboard probe 的覆盖边界 | §8；保留 special chars / Unicode title / large list 未专门 partition 的 limitation，以及“当前 reference 只搬运 facts”这一 risk-based judgment |
| differential testing | §9；same inputs/environment 比 old/new observations |
| snapshot/golden 只能证明保存旧观察，不能证明旧行为正确 | §9；同时保留“不要顺手 update golden 让 drift 变绿” |
| weak tests 下仍可 refactor，但 proof obligation 更难 | §9；targeted evidence，随后自然交给 M06 feedback problem |
| reversibility / rollback granularity | §10 |
| design it twice 比较路线，不是实现两套生产系统 | §11 |
| 更大 redesign 有时合理，但可能已超出 pure refactoring | §11；要求独立 design/migration/rollback reasoning，并把完整 migration/architecture 留给 M08/M09 |
| Large-Scale Changes 可以 shard；LSC != refactoring | §12；source limitation 显式保留 |
| rename / move code 也可能触碰 dynamic/external behavior | §12 |
| Agent 没有“改累了”的自然 guardrail | §13 |
| exploration patch 可以丢弃，information 可以是主要产物 | §13；对应 Beck Getting Untangled |
| staged Agent workflow | §14；reconnaissance → inventory → compare → structural checkpoints → feature → independent review |
| commit/PR description 服务 reviewer 与 archaeology | §14；保留 why / behavior / evidence / non-goals 四类信息 |
| Agent task contract | §14；保持 structured artifact，不 prose 化 |
| refactoring review checklist | §15；压成 Intent / Behavior / Structure / Evidence / Topology-Scope 五个 reasoning groups |
| formatting churn 应与 semantic refactor 分离 | §15 |
| M05 lab contract 与 instructor reference | §16；normative JSON schema 仍归 lab authority；reference snapshot 仍只是 candidate |

原来的分类/拆链 exercise 不再各占一个主标题；其 semantic distinctions 已分布到 §3–§12，并由 M05 lab 承担完整 deliverable。没有因为删除 exercise heading 而把其中的 timing/ordering/optimization/bugfix distinctions 删除。

## 4. Provenance / source-boundary spot check

本轮没有为“更顺”新增来源。重写后的来源分工仍与 `m05-source-audit.md` 一致：

- Fowler：refactoring narrow definition、small behavior-preserving transformations、Two Hats、preparatory refactoring；
- Kent Beck, *Tidy First?*：structure/behavior separation、batch/timing、First/After/Later/Never、Getting Untangled，以及 economics/optionality framing；正文明确这些不是实证定律；
- Google Engineering Practices：small/self-contained CL 的 reviewability/integration/rollback reasoning，并明确没有固定 LOC 阈值；
- *Software Engineering at Google* Large-Scale Changes：large logical transformation 可以 shard 成 independently testable/reviewable/submittable pieces；正文继续明确 LSC 可以含 behavior change，所以 LSC != refactoring；
- Stanford CS190/APOSD：design-it-twice / revision mindset 的辅助来源。

`semantic checkpoint`、`change topology`、Agent task contract、exploration-patch workflow 明确标成 **course synthesis**。

有一处有意的 provenance tightening：merge-base M05 用了 “Hyrum reality” heading，但 M05 source audit 并没有把 Hyrum's Law 建成这一章的独立来源，而课程规划把 Hyrum/compatibility 主讲放在 M08。新版保留 underlying constraint——未文档化但可观察的行为可能已有 consumer——但不在 M05 提前借用 canonical term。

同理，Feathers/WELC 的 seam / sensing / separation 主线保留给 M06。M05 可以说明 weak tests 需要先建立 targeted feedback，也可以轻量提到 characterization 作为一种证据，但不提前教授 seam vocabulary。

## 5. Abstraction dependency sweep

### Preparatory refactoring

第一版 rewrite 在 running pressure 刚出现时就写了 `preparatory refactoring`，随后在 Path A 又用了 `preparatory cost`，在 shared-model 例子中用了 `preparatory model`。这会让一个本应由“direct path vs structural path”压力推出的 abstraction 先变成作者 vocabulary。

已完整检查 §1–§5：这些 occurrence 分别改成“先改结构/直接加功能”“额外的结构准备成本”“shared model”。**第一次 canonical naming 现在是 §6 标题 `Preparatory refactoring`**；此时读者已经看到 direct path、shared-facts path、duplication trade-off、projection/authority 与 `status_text` 的 abstraction pressure。

### M06 vocabulary

第二遍 sweep 又发现 reversibility 示例提前写了 `internal seam/boundary`。M05 source audit 有意把 Feathers/WELC 留给 M06，所以此处不需要借用 `seam` 才能表达 rollout path。已改成 `compatible internal boundary/path`。

正文没有提前引入 sensing / separation / enabling point。`characterization` 只在 weak-tests 与 M06 handoff 中轻量出现，不承担读者理解 M05 的前置条件；完整认识论和 technique 在 M06 才建立。

### M08/M09 boundary

新版不再用 Hyrum canonical name，也不展开 expand-contract、schema migration、deployment/data-ownership techniques。compatibility/migration 只作为 refactoring claim 的限制和后续章节指针。

## 6. Design-decision dependency sweep

M05 最容易出现的 leak 不是术语，而是把 reference architecture 写成答案。

- `DashboardSnapshot` 第一次出现就被标成 instructor **reference path / candidate**；同段保留 pure fact builder、normalized records、smaller count structure 等替代形态。
- Direct Feature 明确拥有真实优势：初始 diff 小、没有额外结构准备成本、没有新 abstraction；一次性 debug JSON 时它甚至可能是更经济的路线。
- normalized model 只在满足当前 repeated-knowledge pressure 时成立；并不推出“第二个 renderer 必须有 snapshot”。
- `RendererRegistry` / strategy hierarchy / provider layer 被作为 speculative over-generalization，而不是课程要求。
- active/terminal counts 是否共享取决于它们是不是共同 policy；“代码相同”本身不足以授权 abstraction。
- Agent task contract 约束 search space，但没有把某个 class/type 写进 acceptance criteria。

因此 reader 到 §5–§6 才拥有比较 direct/preparatory 的 criterion；此前没有把其中一条路线写成既定 architecture。

## 7. State/model projection 与 temporal consistency

### Projection / authority

新版显式恢复 M02 依赖：如果 structural candidate 使用 dashboard snapshot/read model，它只投影当前 dashboard 所需 facts，应由 TaskForge authoritative state 重建；它不获得 job lifecycle mutation authority。

这同时约束 representation scope：snapshot 没有包含某个未来 state dimension，不表示那个 state 不存在，只表示当前 dashboard projection 没承载它。重构若引入可独立写入的 `status_by_job` 并允许它与 authority 分叉，就是 ownership regression。

### Temporal consistency

M05 自身没有引入新的 lifecycle/acceptance/completion state dimension。新版明确把 `no lifecycle changes` 放进 structural-phase contract，也没有用 refactoring 去重新解释 M04 的 request temporal semantics。

对于 error/timing/optimization，正文保持同一原则：如果结构步骤改变 public error 或 externally promised timing/lifecycle behavior，它就不再能靠“pure refactor”获得无 behavior-change 的证明身份，必须进入单独 behavior step。没有让后续 feature success retroactively 把前面的 structural drift 合法化。

## 8. Cold-reader flow

暂时不看 merge-base heading，只顺读新版：

```text
existing text dashboard is correct but entangled
→ JSON request arrives
→ direct duplication is actually plausible
→ duplicated status/count knowledge creates future change pressure
→ before choosing a path, define what “refactoring” is allowed to claim
→ inspect the actual text behavior that must be preserved
→ Two Hats separates structural proof from behavioral proof
→ compare Direct vs shared-facts path fairly
→ status_text/raw facts reveal where a shared abstraction could sit
→ now name preparatory refactoring and discuss when First/After/Later/Never apply
→ sequence pressure creates semantic checkpoint / change topology
→ evidence must match each checkpoint
→ differential/golden/weak-test limitations
→ reversibility and design-it-twice
→ large-scale and Agent transfer
→ staged workflow / review / lab
→ M06 removes the known-behavior assumption
```

这里读者不需要先背 40 多个标题；后续概念都在同一个 JSON-dashboard change 上有明确前因。

## 9. 本轮 self-sweep 实际修正的问题

1. **Abstraction leak — `preparatory refactoring` 提前命名。** 已把 §1–§5 前置范围中的 canonical/derived wording 收回普通描述，并验证 first naming 在 §6。
2. **M02 preservation 太薄 — projection/ownership 只剩 review checklist。** 已在 shared-model episode 恢复 concrete reasoning：read model 可重建且不获得 write authority；mutable second truth source 是 regression。
3. **M04 preservation 太薄 — error behavior 只在 generic list 中出现。** 已恢复 `KeyError -> ApiError` 的具体例子，说明“更好的 error”仍然是 behavior/API change，不能藏在 structural refactor。
4. **M06 abstraction leak — reversibility 例子提前出现 `seam`。** 已换成普通 `compatible internal boundary/path`；M06 保持 canonical seam authority。
5. **Merge-base communication artifact 被压掉。** 已在 staged workflow 恢复 structural commit/PR message 的 why / behavior / evidence / non-goals 与 archaeology value，而没有重新建立独立碎片小节。
6. **Provenance tightening — M05 原文的 Hyrum canonical heading 超出本章 source audit。** 保留 underlying compatibility caution，但把 Hyrum 正式 terminology 留给 M08。

这些修正来自 original-vs-rewrite/source/dependency sweep，而不是用 line count 或 heading 数量证明质量。

## 10. 仍需独立 reviewer 判断

作者侧目前可以检查的是：merge-base technical clusters 有新版落点，lab normative contract 没被正文重写，source/course-synthesis 边界保持，Direct/Preparatory legal set 仍然开放，projection 不产生第二 authority，M06/M08 vocabulary 没被不必要偷跑。

仍需要 cold reviewer 独立判断：

- §1–§6 从“direct patch 很合理”到 preparatory refactoring 的形成是否自然，而不是作者刻意拖延术语；
- §7 同时引入 semantic checkpoint 与 change topology 是否信息密度过高；
- §8–§10 的 evidence/reversibility 是否仍然紧跟 dashboard story，而不是退化成概念综述；
- source-boundary paragraph 是否足够清楚但没有打断正文节奏；
- 460 行左右的新版是否把旧版有用的 transfer judgment 压得太薄。

## 11. Validation record

本轮最终验证实际执行：

```bash
cd labs/taskforge
PYTHONPATH=src uv run --with pytest --no-project python -m pytest -q
PYTHONPATH=src uv run --with pytest --no-project python tools/m05_behavior_probe.py
```

结果：core suite `6 passed`；M05 behavior probe 仍为 `empty=eaadf634b7104332`、`queued=ec17ac5523b4b8bd`、`mixed=1181854b1e08cc1c`，并报告 `all existing text dashboard behavior preserved`。

同时实际检查：

- `git diff --check`：通过；
- 对 M05 module 与本 review record 显式运行 relative-link check：通过；
- 两个 Markdown 文件 fence balance / one page H1：通过；
- 两个目标文件 secret-pattern scan：无 finding；
- 无 `uv.lock` 等测试临时文件；
- M05 前置 dependency sweep：§6 前无 `preparatory` canonical term；全文无 M06 `seam / sensing / enabling point` canonical leak；
- `git status --short` 只包含 M05 module 修改与本 review record 新文件。

## 12. Issue #2 closure pass — instructor-case narrative

2026-09-07 的独立 #2 closure review 认为 M05 module 已完成 case-driven rewrite，但 `case-studies/m05/instructor-analysis.md` 仍保留初版 24 个逐题 reference sections。内容本身正确，问题是 case-study 阅读单位仍像 answer-key，而不是围绕一次 dashboard change 展开 engineering argument。

本轮只重写 instructor case，没有修改 canonical starter、Lab contract、module 或 source audit。新结构围绕同一条 change spine：baseline evidence → direct JSON alternative → normalized-facts candidate → projection/authority → structural-only checkpoint → JSON behavior → `status_text` abstraction test → change topology → evidence limits → direct-vs-preparatory timing → exploration discard → Agent/review → judgment。

Original-vs-rewrite sweep 特别保留：

- direct feature path 的真实低 initial-cost 优势，不把它写成 strawman；
- `DashboardSnapshot` 只是 read-time projection，不获得 lifecycle write authority；
- raw `status + exit_code` 与 text-specific `succeeded(0)` 的 abstraction direction；
- reference 不建立 Renderer hierarchy/registry，原因来自当前 shared knowledge，而不是反 pattern 口号；
- structural phase 与 JSON phase 分别有独立 proof obligation；即使 `KeyError -> ApiError` 更好，它仍是 caller-visible behavior change，不能混进 pure refactor；
- behavior probe 只覆盖当前 selected surface，special chars / Unicode title / large list 等 limitation 仍显式保留；
- differential/golden evidence 只能证明 selected observations 被保持，不能替 desired-contract authority；
- `First / After / Later / Never`、Design it Twice、exploration patch discard 都保持 conditional workflow，而不是 universal rule；
- semantic checkpoint / change topology 继续明确属于 course synthesis。

Canonical validation 仍为 core `6 passed`，M05 behavior fingerprints 仍是 `empty=eaadf634b7104332`、`queued=ec17ac5523b4b8bd`、`mixed=1181854b1e08cc1c`。Historical reference 的 `8 passed` 仍只描述临时 instructor implementation 的局部 evidence。
