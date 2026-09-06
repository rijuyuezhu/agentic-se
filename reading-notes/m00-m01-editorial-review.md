# M00–M01 editorial rewrite review record

这份记录用于 issue #2 的第一批 post-pilot rewrite。它不是作者自我 approve，而是把 semantic mapping、dependency review 和仍需独立判断的部分显式留给 reviewer。

本批只改 M00–M01，没有顺手带上 M02–M03。原因不是它们“更容易”，而是这两章共同承担课程入口到第一套 contract reasoning 的连续前置链；M02/M03 各自已有独立 source audit、lab 和 case study，而且体量明显更大，放进同一 PR 会降低 semantic review 的可定位性。

## 1. Provenance boundary

M00、M01 当前没有独立的 `m00-source-audit.md` / `m01-source-audit.md`。因此本轮 editorial rewrite 的 provenance review 使用三个已有 authority：

1. merge-base `main` 上的原 M00/M01；
2. [`../COURSE_DESIGN.md`](../COURSE_DESIGN.md) 对 M00/M01 的知识目标；
3. [`../MATERIALS_REVIEW.md`](../MATERIALS_REVIEW.md) 已完成的材料审查。

本轮没有因为 prose 重写新增新的主知识线。M00 继续使用已经审查过的 APOSD complexity vocabulary 与 *Software Engineering at Google* 的 time/evolution perspective；M01 继续以 MIT 6.102 的 specification / AF-RI 训练为主要外部校准。PR review 阶段另外做了两处 precision clarification：重新核对 MIT 6.102 Spring 2026 后收紧 precondition-violation 语义；并对当前 state-machine artifact 明确它只建模所画出的 state dimension。后者是对本章自有 candidate/diagram 的 scope 说明，不升级成新的外部定律。

特别保护的 limitation 包括：

- change amplification / cognitive load / unknown unknowns 是有用 design vocabulary，不是 empirical law 或机械评分公式；
- deep module 不等于简单的 interface-size metric，也不推出应该提前设计万能 framework；
- stronger specification 不是自动更好，weaker specification 也不等于故意写模糊文档；
- “make illegal states unrepresentable” 不是所有 invariant 都必须进入 type system；
- repository 作为 transition boundary 只是候选设计，不是“所有业务规则都塞 repository”的 pattern rule。

## 2. Diagnostics，而不是 acceptance metrics

| chapter | diagnostic | baseline | rewrite |
|---|---|---:|---:|
| M00 | lines | 660 | 289 |
| M00 | bytes | 16,007 | 20,487 |
| M00 | page-level H1 | 14 | 1 |
| M00 | H2 / H3 | 16 / 5 | 9 / 15 |
| M00 | `text` fences | 11 | 3 |
| M00 | `---` | 19 | 0 |
| M01 | lines | 950 | 381 |
| M01 | bytes | 18,270 | 24,581 |
| M01 | page-level H1 | 19 | 1 |
| M01 | H2 / H3 | 30 / 5 | 11 / 28 |
| M01 | `text` fences | 36 | 2 |
| M01 | `---` | 28 | 0 |

这里字节数反而上升，说明目标不是“缩短教材”。行数大幅下降主要来自把微型 definition block、普通 prose fence 和 separator 重新组合成完整 reasoning paragraph。

剩余 fence 逐项检查过：它们用于 code、TaskForge/Agent artifact、state machine 或确实需要等宽布局的 protocol，不再把普通自然语言结论当视觉组件。

## 3. M00 narrative mapping

### baseline：`cancel(job_id)` opening → programming vs SE

rewrite 继续从 TaskForge cancellation 开始，但不在第一屏马上给 programming / software engineering 定义。故事先经历：

`naive flag → running-job pressure → explicitly hypothetical CANCELLING candidate → concurrent transition → crash/restart → remote/retry/old client/migration`

直到“代码怎么写”已经不足以回答问题，才区分 programming problem 与 software engineering problem。

### baseline：软件为什么容易失控

第一版 rewrite 曾把这段压得过薄，直接从“新增 `CANCELLING` 要改很多文件”进入 change amplification。semantic review 后恢复了原文中很重要的因果：局部修改表面成本很低，因此 flag、copy、hardcode、adapter 等 individually reasonable decisions 可以长期累积，最后侵蚀 system model。PR review 又进一步把 `CANCELLING` 明确降为 working candidate：它用于追踪 change cost，不代表在 M01 建立 specification criterion 之前课程已经决定 running cancellation 必须这样设计。

### baseline：change amplification / cognitive load / unknown unknowns

三者现在都由具体 pressure 引出：

- 在明确标记的 `CANCELLING` 候选设计下，跨 surface 修改逼出 change amplification；
- temporal-coupled connection API 展示复杂度怎样被推给 caller；
- `normalize_user_id` 的 hidden consumers 展示 unknown unknowns。

正文明确说这些是 useful lenses，不是 empirical laws 或质量分数。

### baseline：Boundary / Contract / Invariant / Change

旧版先列四个对象再分别解释。rewrite 先让 cancellation story 和 complexity symptoms 建立需要，再把四个对象作为对已有问题的压缩：

- Boundary：哪些 knowledge 能被隔在另一侧；
- Contract：caller 到底允许依赖什么；
- Invariant：跨 operation 仍不能破坏什么；
- Change：升级/迁移中间状态是否也合法。

课程工作定义仍保留，并新增显式 qualifier：这是一种课程组织模型，不声称整个 SE 学科只能由四个词定义；requirements/process/economics/security/professional practice 等仍然重要。

### baseline：modularity / Agent / over-abstraction / future-proofing

全部保留，但重新接回前面的 complexity model：

- modularity 被解释为限制一次 change 所需传播的 knowledge；
- shallow wrapper chain 用于说明“模块多”不等于 modular；
- Agent section 由 implementation bandwidth 与 engineering understanding 的不同瓶颈展开；
- vague Agent task 与 structured engineering artifact 保留对照，但 artifact 是可复用结构，不再拆成两个 answer-key 小节；
- “更多 abstraction”与 speculative extensibility 的反例继续作为 limitation。

原 review questions 与三个 exercises 继续存在，只保留真正适合扫描/执行的结构化形式。

## 4. M01 narrative mapping

### baseline：“这个函数对不对？” → specification

rewrite 改成与 M00 同一个 cancellation story：reviewer 面对两种都能跑的 `cancel` semantics，发现只读 implementation 无法判断谁正确。读者先遇到缺口，再命名 specification。

requirements/stakeholder 上游问题仍通过旁支链接明确留在 scope 外，没有把“谁有权决定语义”偷换成实现者自行决定。

### baseline：contract / precondition / postcondition / partial function

signature 先暴露信息不足，再把 contract 定义为 responsibility boundary。`divide(a, b)` transfer case 先建立 `b != 0` 的 precondition，随后才命名 partial function：type signature 给出较大的 representation domain，而 spec 决定 operation 实际 contract domain。

第一版 rewrite 语义上已经表达这个事实，但漏掉了 `COURSE_DESIGN.md` 明确要求的 `partial function` 术语；semantic review 后恢复，而且放在 reader 已经需要 distinction 的位置。

### baseline：side effect / error / temporal / concurrency

这些不再是四个平行定义 subsection。TaskForge 先把 contract 的 **state dimension** 写成候选 behavior table，再继续补 time/error/concurrency/repetition；这样 table 不冒充完整 contract，但其中每一行本身必须给出精确 observable semantics：

- running candidate 明确保持 public `status=running`，并 durable 写入 `cancellation_requested=true`；
- success 到底对应哪个时间点；
- `False` 压缩多种 failure 后 caller 无法决定下一步；
- finish/cancel race 不能用“线程调度决定”代替 contract；
- repeated call 的行为也必须定义。

`idempotency` 只在 repeated-call problem 已经出现后被命名，并明确把完整 request-identity / unknown-outcome reasoning留给 M04。

### M01 candidate cancel contract 与 M04 lab

M01 当前 behavior table **不是 M04 lab normative contract**。M00 的 `CANCELLING` 只是用于追踪 change cost 的 hypothetical representation；M01 故意换成 `status=running + durable cancellation_requested=true`，并保留 already-cancelled success；M04 lab 后来再采用更 strict 的 cancel semantics。

正文直接把三套设计都放回 decision space，并在 exercise 中要求学生不要照抄候选表，而要比较不同 contract strength / semantics。这样跨章 narrative 展示的是“pressure 可以先出现，criterion 决定 design”，而不是前一章偷偷替后一章选答案。

### baseline：representation / protocol / durable invariant

三类 invariant 全部保留。PR review 后又把原来位于 tests 之后的两个 enforcement/artifact 话题重新挂回产生它们的 invariant：representation invariant 后立刻讨论用更精确 representation 排除一部分 local illegal state；protocol invariant 后立刻引入 state machine 作为可 review artifact；durable invariant 完成后再统一进入 enforcement point。

`JobRepository.transition(...)` 仍只是候选 mechanism，不是 repository pattern rule。当前 state-machine 图还明确说明它只画 public status：M01 candidate 的 running cancel 只写 `cancellation_requested`，所以不会凭空出现一条 status edge；如果该 flag 影响后续合法行为，需要 annotation 或扩展 state dimension。这是对当前 artifact 的 scope qualifier，不把 state machine 冒充完整 contract。

### baseline：strong/weak spec / compatibility

`get_users()` 顺序案例继续存在。rewrite 保留两个方向的 limitation：

- 无需求的 stronger promise 会冻结 implementation freedom；
- “少承诺”不能被误用成 vague documentation。

第二遍 semantic review 还补强了一个原学习目标：implementation behavior、documented behavior 与 contract 并不等同。documentation 是 intended behavior 的 evidence，但可能过时；implementation 也可能只是 accidental behavior。长期 observable behavior 又可能形成事实 compatibility constraint，留给 M08 深入。

### baseline：tests from spec / Agent workflow，以及 invariant-adjacent tools

全部保留：

- normalize example 继续说明 test + implementation 可以一起错；
- state/repetition/concurrency/durability/failure partitions 被合并成一组 semantic dimensions，而不是五个微标题；
- illegal-state representation 已移动到 representation invariant 后，并保留 type-system limitation；
- lifecycle state machine 已移动到 protocol invariant 后，并补上“当前图只建模 status dimension”的 scope qualifier；
- Agent 的六阶段 workflow 保持结构化，因为它本来就是执行协议；
- review questions 与四个 exercises 保持可扫描形式。

## 5. Abstraction dependency sweep

### M00

正文在 TaskForge cancellation 与 complexity pressure 建立之前，没有把 `Boundary / Contract / Invariant / Change` 当作读者已掌握的术语。前置 narrative 只用自然语言问：谁负责、success 意味着什么、哪些状态合法、升级期间怎样保持可解释。

`change amplification / cognitive load / unknown unknowns` 也在“新增状态为什么扩散”“caller 为什么要背时序”“为什么不知道还该查哪里”这些问题出现以后才命名。

PR review 还暴露了 **design-decision dependency**：术语即使没有偷跑，前文也可能在 criterion 建立前把一个 candidate design 写成既定答案。当前 M00 已把 `CANCELLING` 明确标成 working assumption，并对后续 crash、change-amplification、migration 引用做了整章 sweep；M01 随后可以合法选择另一种 representation，而不会显得自相矛盾。

### M01

当前顺序是：

`两个实现都 plausible → specification → responsibility boundary → pre/postcondition → partial function → candidate state table → side effect/time/error/concurrency/repetition → idempotency pointer → invariant → representation/protocol artifacts → durable invariant → enforcement point → state ownership pointer`

专项 first-occurrence 检查确认：

- `partial function` 只在 concrete precondition 之后出现；
- `idempotency` 只在 repeated cancel 已建立问题以后出现；
- narrative 中 `Invariant` 的首次教学引入位于“单 operation spec 不够”以后（页面标题中的课程名不算 dependency）；
- `enforcement point` 在 invariant 形成以后才出现；
- `state ownership` 只在 enforcement question 已建立以后作为 M02 bridge 出现。

这不是“术语出现次数越晚越好”。如果一个术语是前置课程已经建立的 vocabulary，可以正常复用；这里检查的是当前章节自己承诺要由案例形成的 abstraction 是否被提前偷用。

## 6. 本轮自审发现并修正的 regression

1. **M00 complexity accumulation mechanism**：第一版丢掉“cheap local decisions accumulate → mental model erodes”的因果，只剩三种 complexity 标签；已恢复为连续 prose。
2. **M01 partial function term**：语义存在但课程要求的术语丢失；已在 precondition example 后恢复。
3. **M01 documented behavior distinction**：第一版虽保留 accidental implementation behavior / compatibility，但没有把 documented behavior 作为独立 evidence source 说清；已补回 documentation 可能过时/不完整、contract 不等同于文档或实现的 distinction。

精确编辑过程中，两次插入还短暂覆盖了相邻原句；每次 read-back 都立即发现并恢复。和 M04 pilot 一样，这再次说明大章 rewrite 的 review 单位必须是 reasoning cluster，而不能只检查“新增段落是否写进去了”。

## 7. PR review 后的 dependency / flow refinement

这轮独立 review 的四个 finding 没有按 comment diff 照单执行，而是分别判断 diagnosis 与 remediation：

1. **M00 提前选 `CANCELLING`**：diagnosis 成立，而且问题类别比单个 occurrence 更大。修复不是删除 running example，而是先承认“拒绝 running cancel / 接受 cancellation request”等多个 plausible design，再把 `CANCELLING` 明确降成用于追踪 change cost 的 working candidate；随后 sweep crash、change amplification、UI/schema 与 migration 中所有把它当既定事实的引用。这个案例已固化为 [`../EDITORIAL_GUIDE.md`](../EDITORIAL_GUIDE.md) 的 design-decision dependency sweep，并同步进 [`../AGENT.md`](../AGENT.md)。
2. **M01 running row 不够精确**：diagnosis 成立，但没有采用“把 running 改成 `CANCELLING`”的直觉修法。M01 刻意选择另一套 candidate：public `status` 保持 `running`，durable 写入 `cancellation_requested=true`；success 只承诺该 request 已 durable accepted。behavior table 同时明确只是 contract 的 state dimension，后续小节继续补 time/error/concurrency/repetition。
3. **§8–§9 narrative rewind**：diagnosis 成立，但没有整块搬到 §5 后。representation technique 现在紧跟 representation invariant，state machine 紧跟 protocol invariant，durable invariant 之后才统一问 enforcement point。重排时额外发现原 state-machine 图只画 status、无法表示当前 candidate 的 running cancellation request，因此补上 projection/scope qualifier，而不是假装一张图等于完整 contract。
4. **precondition violation precision**：独立重查 MIT 6.102 Spring 2026 后确认 reviewer 的 source diagnosis 成立。正文现在写成：precondition 不成立时，这份 specification 不再对该调用提供 postcondition guarantee；defensive check / fail-fast 可以存在，但除非 contract 另行承诺，caller 不能依赖它。

这里再次说明“reviewer 对问题类别的识别”与“reviewer 给出的具体搬法”是两个独立判断对象。

## 8. Cold-reader flow 自审

M00 当前主线是：

`cancel feature → running 时出现多种 plausible design → 暂借一个明确标记的 candidate 继续施压 → programming 不足 → complexity 怎样累积 → 三种 complexity symptoms → 四个工程对象 → modularity → Agent → 不要 over-design → review questions`

M01 接着同一个问题：

`实现能跑但 correctness 无法判断 → specification/contract → precise candidate state table → operation semantics → invariant → representation/protocol artifacts → durable invariant → enforcement → specification strength/compatibility → test oracle → Agent workflow`

两个模块之间的 transition 不再是“下一章开始定义新术语”，而是 M00 结尾明确留下“什么必须为真、谁保证”的问题，M01 从 reviewer 无法判断两个 implementation 谁正确开始回答。

## 9. Rhythm review

已专项搜索“真正……”“这就是……”“不是 X 而是 Y”“所以……”等强调式转折。只删除没有新增语义的作者强调；保留真实 contrast，例如 stronger contract vs vague spec、programming vs long-lived engineering concern。

bullet 主要剩在：真正 parallel 的 pressure/questions、review checklist、exercise requirements 和 Agent artifact。没有为了追求 prose 率把可执行结构打散。

## 10. 仍需 independent reviewer 判断

作者无法自证以下问题：

- M00 从 cancellation story 进入三种 complexity vocabulary 时，读者是否觉得 abstraction 是被问题逼出来，还是仍有轻微 taxonomy jump；
- M00 四个核心对象连续出现是否已经形成过多“课程总纲”感；
- M01 §4 现在把 representation technique、protocol state machine 和 durable invariant 收到同一个 invariant episode 后，是否信息密度过高；
- state-machine projection 的 scope qualifier 是否帮助读者理解 artifact 边界，还是在 M01 粒度上过早；
- M01 后半的 specification strength、tests 与 Agent workflow 是否仍属于同一条 argument；
- 是否还有 baseline 中 technically present 但 pedagogically compressed too far 的 distinction；
- prose 是否仍有过度整齐、作者不断总结的 generated-answer rhythm。

因此本批应和 M04 pilot 一样要求独立 semantic + cold-reader review。通过以后再把同一方法用于 M02/M03，而不是因为 M00/M01 格式指标变好就自动推广。
