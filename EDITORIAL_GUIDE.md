# 教材编辑指南

本指南约束 `modules/` 主讲义及后续新增的教材型 `extensions/`。它服务于一个具体目标：让读者不是拿到一组已经切好的工程结论，而是沿着问题、失败和比较逐步形成可迁移的 engineering judgment。

它不是“去 AI 味”规则，也不以 AI detector、段落长度、bullet 百分比或标题数量作为质量指标。判断标准始终是：一个有 CS 背景、但还没有本章 mental model 的读者，能否自然地跟上推理，并在新场景中复用它。

## 1. Reader model 与 voice

默认读者已经会编程，知道 Git、测试和基本系统概念，但不假设有工业软件工程经验。他们需要的是从“我大概知道这个词”走到“我能在真实 repo 里判断它什么时候成立、什么时候不成立”。

正文采用作者带读者共同分析问题的 voice。可以直接提出问题，也可以明确给出判断，但不要连续使用口号式反差代替论证。尤其避免把一段推理压成连续的“不是 X，而是 Y”“不要 A，要 B”“真正重要的是 Z”。这类句式只在确实需要纠正常见误解时使用一次，随后必须展开原因、条件和后果。

术语可以保留工程中自然使用的英文，如 `contract`、`invariant`、`boundary`、`retry`、`rollback`、`failure domain`。普通中文句子不应为了显得技术化而堆叠可替换的 English noun phrases。同一术语在同一模块内保持稳定 spelling。

## 2. Example drives abstraction

主讲义优先采用下面的教学顺序：

1. 先让读者看到一个具体、可信的问题；
2. 让一个 plausible intuition 真正撞到边界，而不是立刻宣布它错了；
3. 追踪后果，直到读者需要做一个 distinction；
4. 再给这个 distinction 命名或引入已有术语；
5. 解释适用条件、代价和不能推出的结论；
6. 用第二个不同场景检查这个 abstraction 是否可迁移；
7. 最后才压缩成 review question、definition 或 checklist。

这不意味着每个概念都要编故事。一个章节应有少量持续案例，而不是每三段换一个 toy example。小例子主要用于验证已经形成的概念，不能替代主线。

### 2.1 Running example 的职责

一个 running example 应跨越多个相邻概念，并随着新条件加入而自然变难。好的 running example 会让后面的概念看起来像前面问题的继续，而不是作者突然想起一个新术语。

例如 M04 中，TaskForge 的 `submit/get/cancel` 可以从一个简单本地 API 逐步加入：invalid input、mutable state、storage replacement、timeout、retry、request identity 和 concurrent staleness。读者应该感到是同一个 API 被现实条件不断逼出更精确的 contract。

不要为了维持单一故事而硬塞所有概念。当一个 abstraction 已经在主故事中形成，应允许一个简短的 transfer case，例如 `delete resource`、`create_vm` 或 session lifecycle，证明它不是 TaskForge 特例。

### 2.2 不要伪造戏剧性

不使用虚构个人经历、假装来自某次事故的故事、夸张对话或“想象你凌晨三点被叫醒”式叙事来制造人味。案例的可信度来自清楚的 system state、caller goal 和 failure condition，而不是人物表演。

## 3. Paragraph、heading、list 与 fence

### 3.1 Paragraph 是默认 reasoning unit

如果几句话存在因果、转折、限定或递进关系，默认写成 prose paragraph。不要仅因为每句话都“值得强调”就拆开。

一个段落通常应完成一个完整动作，例如：建立场景、追踪一个失败、比较两个设计、解释一个 qualifier。段落可以短，也可以长；关键是它结束时一个 reasoning step 已经完成。

### 3.2 Heading 表达章节结构，不表达每个观点

每个 Markdown 页面只有一个 `#` 标题。

- `##` 表示读者正在进入一个新的主要问题或 episode；
- `###` 表示这个主要问题内部确实需要单独导航的子问题；
- 一个只有两三段、且不能独立成为 TOC 入口的观点通常不需要 heading。

不要为了满足固定 heading 数量而合并或拆分。反过来，如果一页目录看起来像术语索引，而不是章节路线，通常说明 heading 太细。

### 3.3 Bullet 只用于真正并列的东西

适合 bullet 的内容包括：

- checklist；
- genuinely parallel alternatives；
- deliverables / non-goals；
- compact comparison；
- 一组读者之后需要逐项扫描的 conditions。

如果五句话必须按顺序理解，或者每一句都依赖上一句的 qualifier，就写 prose，不要做成 bullet。

### 3.4 Code fence 不是视觉高亮组件

保留 fenced block 给：

- source code；
- shell command / terminal output；
- JSON/YAML/SQL 等机器格式；
- 状态机、时序或确实需要等宽布局的小型 ASCII diagram；
- 必须逐行对照的 protocol / artifact。

一句普通结论、`A != B`、简单箭头链、自然语言列表默认不要放进 `text` fence。若一句话需要强调，优先让上下文证明它重要；只有真正承担章节转折的结论才考虑 blockquote 或 bold。

## 4. Definition、warning、aside 与 exercise

### Definition

术语应尽量在读者已经遇到它所解决的问题后出现。定义要说明它区分了什么，并立即回到当前案例。不要连续堆多个定义。

### Warning / limitation

重要 limitation 应留在正文推理附近，而不是集中丢到章末。特别是以下词出现时要主动检查条件：`always`、`never`、`safe`、`idempotent`、`exactly once`、`no side effect`、`must`。

### Aside

历史背景、语言特有技巧或较远的延伸，如果拿掉不影响当前推理，可以做短 aside；不要让 aside 产生新的主线依赖。

### Exercise

主讲义内的小问题可以在关键转折处让读者先判断，再继续正文。完整 deliverable、validation command、rubric 留给 `labs/`，不要把 lab 结构复制进教材正文。

## 5. 技术 claim 与 provenance 不得在“润色”中漂移

Editorial rewrite 默认没有权限改变技术主张。每章重写前先读对应 `reading-notes/*-source-audit.md`；重写后至少做一次 claim-level spot check。

必须特别保护：

- condition；
- exception；
- non-goal；
- uncertainty；
- compatibility qualifier；
- source limitation；
- “course synthesis” 与 source-backed claim 的边界。

常见危险变形包括：

- `often / when X` 被写成 universal rule；
- “caller action 相同，可以考虑 collapse”被写成“相同 error 必须 collapse”；
- “某个 boundary 可以保证 no effect”被写成“error 都意味着 no effect”；
- “request identity 可支持某种 idempotency guarantee”被写成“request ID 实现 exactly once”；
- source 中的 heuristic 被润色成定律。

如果为了叙事必须新增技术事实，应先更新 source audit，而不是让新事实悄悄进入正文。

## 6. Original-vs-rewrite review protocol

每次 pilot 或大章重写至少做三遍不同目的的 review。

### Pass A — semantic preservation

对照 rewrite 与 merge-base 原文以及 source audit，逐项确认：

- 原有重要 claim 是否仍可找到；
- condition / limitation 是否仍在；
- 原本明确的 non-goal 是否被故事吞掉；
- 术语是否被无意改义；
- lab contract、链接、后续模块衔接是否仍成立；
- 如果 rewrite 引入了新的 contract-relevant state dimension，后续 behavior table、representation example、state machine、test partition 等 artifact 是否一致携带它；若某个 artifact 只建模其中一部分，是否明确声明自己的 projection / scope，而不是让读者误以为它是完整模型；
- 如果 contract 把一个 operation 拆成 acceptance / completion / recovery 等 temporal phase，后续 error、state transition、durability 与 evidence reasoning 是否保持同一时间模型；尤其不能让 completion failure retroactively 改写一个只承诺 acceptance 的既有 success，除非 contract 本来就这样定义。

### Pass B — cold-reader flow

暂时不看旧结构，只顺读新文。每进入一个术语时问：

- 读者此刻已经知道为什么需要它了吗？
- 这段是在推进当前问题，还是只是作者想把一个知识点塞进来？
- 前一节最后的问题是否自然导致这一节？
- running example 是否真的发生了新情况，而不是换皮重复？

### Pass B.1 — abstraction dependency sweep

如果 cold-reader review 发现某个 abstraction 在故事真正需要它之前已经被使用，不要只修改 reviewer 点名的 occurrence。先确定这个 abstraction **应该第一次被命名的位置**，然后检查从章节开头到该位置之前的整个 narrative：

- 搜索 canonical term，以及中英文变体、缩写和明显同义表达；
- 搜索会预设该 abstraction 已经存在的 API 字段、type、error reason、example 和 descriptive phrase；
- 区分有教学目的的轻量 foreshadowing 与 accidental dependency leak；前者必须不要求读者已经理解该 abstraction，后者应改用读者此刻已有上下文中的例子，或只描述底层现象而暂不命名；
- 修改后重新顺读“前置 narrative → problem pressure → first naming”，确认术语第一次出现时确实是在回答读者已经遇到的问题；
- 再做一次全前置范围搜索，作为这个**具体 dependency constraint** 的验证证据。搜索次数只能证明“没有已知泄漏”，不能证明章节整体教学质量。

reviewer 的 diagnosis 与 remediation 也要分开判断。一个 reviewer 可能正确发现“abstraction 出现太早”，但只指出了部分 occurrence，或者给出的搬移方案会损失另一条合理 reasoning。修复时应处理问题的完整类别，而不是机械执行 comment diff。

M04 pilot 的实际案例见 [`reading-notes/m04-editorial-pilot-review.md`](reading-notes/m04-editorial-pilot-review.md) 的“PR review 后的 dependency / flow refinement”：最初只被指出 §2 提前使用 `request_id`，全章复核后又发现 §3–§5 的 `request identity` / `idempotency` / `idempotent` 同样在偷跑；最终把这些泄漏一起清理，并保留了 reviewer 原建议中不应删除的 convenience-API reasoning。

### Pass B.2 — design-decision dependency sweep

dependency leak 不只会提前泄漏术语，也会提前泄漏**尚未建立 decision criterion 的设计结论**。如果后面的章节或小节负责教读者“怎样在多个 plausible design 之间做判断”，前面的 running example 可以先制造压力，也可以暂时选择一个 concrete candidate 继续追踪后果，但不能把该 candidate 写成自然必然的答案。

遇到这种情况时：

- 先确定读者到哪里才真正拥有选择这个设计所需的 criterion / authority；
- 检查此前 narrative 是否已经把某个 state、schema、API shape、error policy、ownership arrangement 或 recovery policy 当成既定事实；
- hypothetical candidate 是允许的，但必须明确它是为了继续推理而暂时采用的 working assumption，并让其他 plausible alternatives 继续保持可见；
- 后文如果继续用该 candidate 分析 complexity、migration、testing 等问题，也要保持 conditional scope，不能因为重复引用而悄悄把它升级成课程答案；
- 当 decision criterion 建立后，应允许章节重新比较、替换甚至拒绝前面的 candidate，而不让读者感觉课程自相矛盾。

M00–M01 的 post-pilot review 给出了一个实际例子：M00 为了追踪 cancellation 的 change cost 使用 `CANCELLING` 很合适，但在 M01 建立 specification / design authority 之前，它只能是明确标记的候选设计，而不能写成“于是我们加一个 `CANCELLING`”这样的必然结论。完整记录见 [`reading-notes/m00-m01-editorial-review.md`](reading-notes/m00-m01-editorial-review.md)。

### Pass C — compression and rhythm

寻找新的生成式写作习惯：

- 连续多个对称句式；
- 每段末尾都有“所以真正重要的是……”；
- 每个概念都有一条加粗金句；
- 过度整齐的三项/五项枚举；
- 为了流畅反复总结已经说过的话；
- transition 只靠“接下来我们看……”模板推进。

删除这些东西时不能伤害 technical qualifier。目标不是让文字“更有个性”，而是让推理本身产生节奏。

## 7. 不同内容类型使用不同编辑标准

### `modules/`

教材正文。连续 prose、少量 running examples、稳定 H2/H3 层级、读者可以从头读到尾。

### `labs/`

执行文档。deliverables、must preserve、non-goals、commands、evidence packet 和 rubric 应继续结构化。只统一 terminology、heading 和必要说明，不为了“像书”而 prose 化。

### `reading-notes/`

审计记录。provenance、claim/source mapping、limitations 优先于叙事，不应用教材标准衡量。

### `case-studies/`

更接近 engineering analysis：先给背景与 evidence，再展开 alternatives、rejected paths 和 judgment。可以保留必要表格和 checklist，但避免只给“标准答案 bullet list”。

### `extensions/`

如果它承担教材型解释，遵守 `modules/` 的主要规则；如果本质是 reference，则明确采用 reference 结构，不假装 narrative。

## 8. 轻量 glossary / preferred spelling

以下是当前主线的默认写法；有充分上下文时可以使用中文解释，但不要随机切换同义词。

| Preferred | 说明 |
|---|---|
| boundary | 边界；强调责任、表示、trust 或 failure 的分界时保留英文 |
| contract | 契约；指可依赖语义时保留英文 |
| invariant | 不变量 |
| caller | 调用方；讨论 API interaction 时保留英文通常更精确 |
| state ownership | 状态所有权 / authority 的归属 |
| failure boundary / failure domain | 按具体语境区分，不互换 |
| retry | 重试；正文可中英混用，但同一段尽量稳定 |
| rollback | 回滚 |
| compatibility | 兼容性 |
| request identity | logical request 的身份，不等于 payload equality |
| idempotency | 幂等性；必须说明约束的是哪个 intended effect |
| unknown outcome | 结果未知；不能简写成 failure |

这个表不是完整术语表。发现跨章不一致时再增补，而不是预先维护一个庞大 vocabulary。

## 9. Style calibration：我们借鉴什么，不照搬什么

编辑时可用几类成熟材料校准阅读节奏，但它们不是本课程 technical claim 的新 provenance。

- MIT 6.102 readings：常从具体代码或对象出发，在例子已经暴露问题后引入较正式的概念，并在同一对象上继续推理。参考 `https://web.mit.edu/6.102/www/sp26/classes/07-abstraction-functions-rep-invariants/`。
- *Software Engineering at Google*：章节常先给实践问题和动机，再讨论 trade-off 与规模效应，最后才压缩为总结；其 Documentation 章还明确强调 audience 与 beginning/middle/end。参考 `https://abseil.io/resources/swe-book/html/ch10.html` 与 `ch11.html`。
- *Designing Data-Intensive Applications*：值得借鉴的是围绕“要解决什么系统问题、有哪些路线、trade-off 是什么”组织概念，而不是围绕产品名或术语索引组织章节。作者对章节 maps 的解释见 `https://martin.kleppmann.com/2017/03/15/map-distributed-data-systems.html`。
- Stanford CS190：继续作为重要技术与 design-judgment 来源；但它的公开 lecture notes 本来就是课堂提纲式 bullets，因此不作为本轮正文文体模板。

本课程自己已有的 M00 `cancel(job_id)` 开场也是重要 calibration：一个看似简单的需求逐步暴露 lifecycle、concurrency、durability、retry、compatibility 等问题，再由问题逼出软件工程概念。

## 10. Pilot 的完成标准

一次 pilot rewrite 不能因为 H1、bullet 或 fence 下降就宣告成功。至少同时满足：

- 页面只有一个 H1，H2/H3 可以形成可信的章节目录；
- 有清楚的 running problem，主要概念由它推动；
- 至少若干核心 abstraction 经过第二场景迁移，而不是只在主故事里成立；
- 原 source audit 的重要 claims、limitations 与 course-synthesis 边界没有漂移；
- 普通自然语言不再依赖 `text` fence 充当 callout；
- checklist、behavior table、真正 diagram 等结构化 artifact 仍保持结构化；
- 人工顺读时，读者经历的是问题逐渐变难并形成判断，而不是更长版本的知识点列表。

如果上述最后一条不成立，就继续重写，不用格式统计为文本辩护。
