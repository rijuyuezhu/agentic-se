# M05 — Refactoring 与 Evolutionary Design：把变化本身设计成可证明的序列

M04 刚把注意力放在 API boundary：一个看起来很小的接口，如果把 error、retry 和内部 representation 泄漏给 caller，很快就会变成复杂度扩散点。现在我们换一个角度。即使当前行为已经足够清楚，测试也能跑，仍然会遇到另一个常见问题：**下一次需求应该直接补上去，还是先改变结构？**

TaskForge 正好有一个很小却很典型的例子。当前 text dashboard 的实现是正确的，已有 probe 也能稳定锁住输出；但 `render_dashboard()` 同时负责读取 jobs、统计各状态、解释 active/terminal、拼 status label 和最终文本。现在需求只有一句：

> 增加 JSON dashboard。

这看起来像一个几十行的小功能。也正因为它小，我们很容易在没有设计 change sequence 的情况下直接开始写。

## 1. 一个能工作的 direct patch，为什么还值得停一下

先看现有代码中最关键的一段：

```python
for job in jobs:
    if job.status == JobStatus.QUEUED:
        queued += 1
        status_text = "queued"
    elif job.status == JobStatus.RUNNING:
        running += 1
        status_text = "running"
    elif job.status == JobStatus.SUCCEEDED:
        succeeded += 1
        status_text = f"succeeded({job.exit_code})"
    elif job.status == JobStatus.FAILED:
        failed += 1
        status_text = f"failed({job.exit_code})"
    elif job.status == JobStatus.CANCELLED:
        cancelled += 1
        status_text = "cancelled"
```

后面还会计算：

```python
active = queued + running
terminal = succeeded + failed + cancelled
```

如果直接增加 `render_dashboard_json()`，最省事的路线当然是复制这套遍历和统计逻辑，再把最后的 string formatting 换成 dict / `json.dumps()`。这条路线并不荒唐：initial diff 很小，不引入新 type，需求很快能交付。如果 JSON 只是一段很快删除的 debug code，长期 duplication 甚至可能完全值得接受。

真正值得停一下的原因是：这里会复制的不只是 syntax。第二个 renderer 也必须知道哪些状态算 active、哪些算 terminal、每个 status 怎样计数，以及 job order 从哪里来。如果以后真实需求再加入一个状态，这些判断就可能在两个 renderer 中独立演化。

这时我们第一次遇到本章真正的压力：**当前 feature 很容易实现，但它暴露了一个结构问题；我们是否应该在加行为之前，先做一个结构变化？**

先不要回答。M05 的重点不是默认选择“先改结构”或“直接加功能”，而是学会把这个选择变成可审查的工程判断。

## 2. 说“先重构”以前，先确定什么叫 refactoring

工程里“我先重构一下”经常实际包含 rename、move files、改 API、修 bug、换 error、加 feature，最后所有 tests 一起变绿。这样做有时能得到更好的最终代码，但把它统称为 refactoring 会丢掉一个很有价值的区分。

Fowler 对 refactoring 的定义很窄：改变内部结构，使软件更容易理解和修改，同时保持 observable behavior 不变。它通常不是一次大手术，而是一串小的 behavior-preserving transformations，每一步之后都重新验证系统仍处于 working state。

这个窄定义的价值不在术语洁癖，而在 proof obligation。只要一个 change step 声称自己是 pure refactoring，我们就获得了一个很强的 debugging/review rule：**这一小步没有 intended behavior change，因此任何不符合既有 behavior 的变化都需要解释。**

换句话说，重构并不是“改完以后 tests 还能过”这么宽的概念。它是在声明：在本次讨论的 compatibility boundary 上，before 和 after 对外仍应等价。

可以把这个 claim 写成一个提醒，而不是数学证明：

```text
same relevant inputs + same relevant environment
        ↓
old implementation and new implementation
        ↓
same allowed observations
```

难点马上转移到了最后四个字：**allowed observations 是什么？**

## 3. TaskForge 的 text dashboard 到底有哪些行为要保持

M05 starter 已经有一个 behavior probe。当前 baseline 实际运行是：

```text
[OK] empty:  sha256=eaadf634b7104332
[OK] queued: sha256=ec17ac5523b4b8bd
[OK] mixed:  sha256=1181854b1e08cc1c
all existing text dashboard behavior preserved
```

核心 pytest baseline 仍是：

```text
6 passed
```

hash 本身不是 contract。真正重要的是 probe 里的 expected text。它锁住了 default/custom title、summary line、每种 status count、`<none>`、job 顺序、`succeeded(0)` / `failed(7)` 这种 text-specific label，以及 command 原样输出。

所以在本 lab 的 structural phase，我们可以把一个局部、明确的 claim 写出来：

> `render_dashboard(title)` 的既有 text output 必须 byte-for-byte 不变。

这比“功能应该差不多一样”强得多，因为 reviewer 知道该比较什么；同时它又比“整个 TaskForge 的一切行为都不能变化”窄得多。M05 不会趁机重做 lifecycle、service API、M04 public error semantics 或 state ownership。

这一步很容易被忽略。很多人先按 IDE 的 rename/extract 操作，最后才试图证明 behavior 没变；更稳妥的顺序是反过来：**先做 behavior inventory，再决定哪些结构变化可以戴 refactoring hat。**

### Observable behavior 不只等于返回值

Dashboard 是一个简单例子，它主要把 text 当 observation。但真实系统里 observable surface 可能还包括 exception/error code、写入的文件或数据库状态、输出顺序、callback 时机、配置优先级、RPC 次数、持久化格式等。性能和资源行为在某些系统里也可能是明确 promise；如果 caller 或生产 workload 依赖某个 latency/complexity boundary，把 `O(log n)` 换成 `O(n²)` 也不能仅凭“返回值一样”就当作低风险结构整理。

这里的限定很重要：不是任何内部 timing、lock order 或 call count 都天然属于 public contract。问题始终是**谁能观察、谁已经依赖、这次 change 是否承诺保持它**。

M01 已经提醒过 documented contract 与 implementation accident 不同。维护已有系统时还要再谨慎一点：某个从未写进 README 的行为，也可能已经被真实 consumer 依赖。M08 会专门讨论 compatibility 和 migration；M05 这里只建立一个保守习惯——当你声称 pure refactoring 时，不要因为“文档没写”就自动把可观察旧行为判成可随意改变。

## 4. 两顶帽子：让一个 change step 只承担一个主要证明问题

Fowler 的 refactoring workflow 用 “Two Hats” 做了一个很实用的区分。

戴 **refactoring hat** 时，目标是改 structure、保留 behavior。戴 **adding-function hat** 时，目标本来就是改变 behavior：新的 spec 进入，旧 expectation 可能需要更新，新 behavior tests 应该经历 fail-before / pass-after。

真实工作当然可以在一天、甚至一小时内不断切换两顶帽子。问题不是“feature 和 refactoring 必须隔一周”，而是一个具体 change step 是否同时要求 reviewer回答两个不同问题。

假设一个 diff 同时做了这些事：rename symbols、移动依赖、改变 error type、增加 retry、改变 timeout default。reviewer 看到一行改动时，会同时问：这是机械 rename 还是 semantic move？retry 是否新增 side effect？timeout 是否改变 compatibility？任何 test failure 到底来自哪个 intended delta？

如果改成更清晰的 sequence：

```text
C1  isolate/move existing behavior, no intended behavior change
C2  verify existing callers and outputs unchanged
C3  add retry behavior under a new contract
C4  change timeout policy separately if still needed
```

每一步的 correctness argument 会窄很多。这里最重要的不是 commit 数量，而是 **semantic separation**：结构等价和新行为不要在同一步互相掩护。

这也是为什么“顺手修个 bug”最好不要藏在 pure refactor 里。你可以先加 regression test、修 bug，再继续结构变化；也可以先把结构不变地搬好，再单独修 bug。顺序取决于依赖关系，但 reviewer 应始终能看出哪一步理论上不该改 behavior，哪一步就是要改 behavior。

M04 的 error boundary 提供了一个更具体的检查。假设你只是在移动 error-translation plumbing，只要 public error semantics 保持相同，它仍可能属于 structural change；但如果原来会向 caller 暴露 `KeyError`，现在改成稳定的 `ApiError`，即使新行为更合理，也已经改变了 boundary contract。更清晰的 sequence 是先在 externally-same 的前提下整理 plumbing，再把 intentional error-contract change 放进单独的 behavior step，而不是把两件事都写成“refactor error handling”。

性能 optimization 也值得类似处理。它往往刻意改变 time、memory、I/O、parallelism 或 cache behavior，所以即使 functional result 保持，工程上也通常值得单独 review，并带 functional-equivalence evidence 与 benchmark/resource evidence，而不是藏在 cleanup 里。

## 5. 回到 JSON dashboard：先比较两条都 plausible 的路径

现在我们终于有资格讨论 design，而不是用“DRY”直接替代判断。

### Path A：直接加 JSON

实现可以保持现有 text renderer 完全不动，在新的 `render_dashboard_json()` 中重新统计 jobs。它的优点是真实存在的：diff 小、没有额外的结构准备成本、没有新 abstraction、behavior change 可以很快落地。

代价也很具体：两个 renderer 都会拥有 status/count interpretation。如果 terminal 定义以后变化，两个地方必须同步；如果第三个 renderer 出现，change amplification 继续上升。

### Path B：先隔离 shared facts，再加 JSON

另一个 candidate 是先把“两个 renderer 真正需要共同理解的 semantic facts”放到一个内部 boundary：可能是一个 pure fact builder、normalized records、internal snapshot model，或者更小的 count structure。然后让现有 text renderer 先消费它，并用 behavior probe证明 text 一字不变；只有这个 structural checkpoint 绿了，才新增 JSON renderer。

这里刻意不宣布 `DashboardSnapshot` 是标准答案。Instructor case study 用 frozen dataclasses 做了一条 reference path，是因为它在当前 fixture 上把 raw facts 和 text presentation 分得比较清楚。但只要其他 design 能集中真正重复的 knowledge、保持 projection scope 清楚、且不制造新的 authority，也可以成立。

如果选择 snapshot/read model，还要把 M02 的 ownership rule 带进来：它只投影当前 dashboard 需要观察的 facts，并不因为多了一份 representation 就获得写入 job lifecycle 的 authority。这个 scope 也必须说清楚——某个未来 state dimension 没被 dashboard 投影，不代表那个 state 不存在。这样的 projection 应能从 TaskForge 的 authoritative state 重新构建；反过来，如果“重构 dashboard”顺手引入一份可独立修改的 `status_by_job` cache，而且两边都可能被写，那就制造了第二份 truth source。即使最终 text/JSON 都能渲染，这仍然是 ownership regression，而不是结构改善。

这和 M02 的 design-decision discipline 是同一条规则：**当前 pressure 可以让一个 candidate 变得有吸引力，但不能凭 repeated use 把它自然化成唯一 architecture。**

尤其不要为了“两个 renderer”顺手建立 `RendererRegistry`、factory、strategy hierarchy、provider layer。当前真正共享的是 fact construction，而 text 和 JSON 的 composition shape 其实不同。一个更抽象的 renderer lifecycle 是否值得存在，要等真实 change pressure 提供证据。

### `status_text` 暴露了 abstraction 应该在哪里

这个例子里最有教学价值的一处细节是：

```text
succeeded + exit_code=0
```

是 semantic facts；而：

```text
succeeded(0)
```

只是 text presentation。

JSON contract 需要 raw status 和独立 `exit_code`。如果这个 shared model 保存的是 `"succeeded(0)"`，JSON renderer 反而要从 text string 重新解析 domain facts。这说明 abstraction direction 反了：presentation 泄漏进了应该服务多个 representation 的 shared layer。

同理，active/terminal/status counts 是否应该共享，也不能只用“两个地方代码一样”判断。Instructor reference 把 counts 集中，是因为这些 counts 代表两个 renderer 都需要一致理解的 reporting/domain policy；如果未来两个 presentation 对 counts 的定义本来就要独立演化，合并它们反而可能制造错误 coupling。

所以 M05 仍然沿用 COURSE_DESIGN 里对 DRY 的限制：要问 duplicate 的是 syntax，还是 knowledge / policy。

## 6. Preparatory refactoring：为一个近端变化铺路，而不是借题发挥

Fowler 所说的 preparatory refactoring，核心情形就是：当前结构让一个马上要做的 feature 很别扭，于是先把结构移动到更适合承载这个 feature 的形状，再进入真正的 behavior change。

关键限定是“马上要做的 feature”。如果 JSON dashboard 的真实压力只要求抽一小段 shared facts，那么它并不能自动授权你全仓 rename、重做 package layout、统一 exception hierarchy、引入 dependency-injection framework。

判断某个 structural change 是否真的是 preparation，可以问：它是否直接降低当前 feature 的 duplication、branching 或 evidence cost？能否在 feature 之前独立证明 behavior unchanged？有没有明显更小的变化也能解决同一个 pressure？如果 feature 明天被取消，这个 refactor 是否仍值得保留，可以作为帮助暴露动机的问题，但不是必须回答 yes 的门槛。

这里没有“永远 tidy first”的规则。Beck 在 *Tidy First?* 中刻意把 timing 写成 First / After / Later / Never：

- **First**：当前结构明显放大近端 feature，而准备动作小且容易验证；
- **After**：需求本身很小，当前结构足以安全修改，或者只有做完 feature 才看清真正 duplication；
- **Later**：问题真实存在，但这次 change 不依赖它，先记录 trigger/owner；
- **Never**：某些稳定、即将删除、生成或短期 migration code 的“不漂亮”根本不值得清理。

这些不是四个流程模板，而是提醒：结构整理的 timing 本身也是 trade-off。软件工程优化的是总 change cost，不是代码美观最大化。

因此对于 TaskForge，课程推荐学生认真尝试 preparatory path，是因为 fixture 故意让 duplicated interpretation 足够明显；这不应该被迁移成“第二个 renderer 出现时总要抽 snapshot”。如果 JSON 明确只是一次性 debug output，direct patch 完全可能更经济。

## 7. “小步”不是 LOC 阈值，而是 reviewer 能建立窄 correctness argument

Small change 很容易被机械理解成 `LOC < 100`。Google Engineering Practices 明确不把固定行数当硬规则，这和我们这里的需求很一致。

想象两个 diff。第一个在 500 个文件里机械地把同一个 private symbol 重命名；第二个只有 20 行，但同时加 retry、改 timeout、移动 transaction boundary、增加 fallback。行数更大的那个未必更难 review。

更有用的尺度是 semantic size：**一个 reviewer 能否围绕一个主要目的，建立一个 self-contained correctness argument。**

M05 为这种中间状态使用一个课程自己的名字：**semantic checkpoint**。它不是 Fowler、Google 或 Beck 的 canonical term，而是课程 synthesis，用来提醒我们检查每一步是否：

- 代码处于 coherent、可运行状态；
- 本步骤只有一个主要 structural/behavioral purpose；
- relevant evidence 可以独立运行；
- 如果失败，suspect range 足够窄；
- 必要时 rollback 不会同时撤掉无关的已验证变化。

对于 dashboard，一条合理 change sequence 可能是：

```text
S0  current text renderer + existing behavior probe
 |
 | evidence / inventory only
 v
S1  isolate shared dashboard facts
 |
 | structural, text output must stay identical
 v
S2  migrate text renderer onto that structure
 |
 | still structural; re-run old probe
 v
S3  add JSON renderer + JSON behavior tests
```

S1/S2 也可以合并，只要它仍然是一个窄、可独立证明的 structural step。真正重要的是不要把整个 sequence 压成一句“refactor dashboard and add JSON”。

这条序列一旦写出来，我们得到第二个重要课程 synthesis：**change topology**。设计不只描述最终 tree 里有哪些 modules/types；还要描述系统怎样从旧状态走到新状态，以及中间每个状态是否可运行、可 review、可回退。

最终 architecture 很漂亮，但迁移路径要求主干连续坏三天，仍然可能不是可执行设计。

## 8. 为什么 checkpoint 比“最后 tests 绿了”更强

M03 已经建立过一个前提：green tests 是 evidence，不是 correctness proof。M05 把它放进 change sequence 里以后，这个区别更重要。

如果一个 2000 行 mixed patch 最后有一个 test fail，debug search space 是多个同时变化的语义维度。如果十个 checkpoint 里前四个都稳定，只有第五个第一次出现 drift，那么 investigation 会自然集中在 `S4 -> S5`。

因此小步不只是为了 Git history 整齐。它降低了 failure localization 和 review 的不确定性，并允许 rollback 只撤掉真正有问题的阶段。

但每个 checkpoint 的 evidence 也必须与 claim 匹配。rename 可能需要 compiler/type checker、tests、repository search 和 external compatibility decision；error-translation plumbing 的 structural move除了跑 tests，还要检查 public error code set 是否漂移；serialization move 可能更需要 schema/golden/differential evidence。

对于 dashboard，当前 structural claim 很窄，所以 `m05_behavior_probe.py` 是一个很强的 safety net：它直接比较现有 text bytes。但它仍然不是全知 oracle。三个场景没有专门探索 command 中的特殊字符、Unicode title 或巨大 job list。Instructor case 的判断是：reference structural move并不 parse/transform command/title，只是搬运 facts，因此 code reasoning 与现有 high-information scenarios 组合后，在当前 lab 风险下足够。若重构开始处理 escaping/parser，这些 partitions 就必须升级。

这就是 M03 的 evidence principle 在 M05 的直接应用：**证据强度要围绕本次 change 的风险，而不是围绕“测试数量”或 coverage percentage。**

## 9. Differential 与 golden evidence：它们证明的是“保持旧行为”

当 claim 恰好是 before/after behavior equivalent 时，differential testing 很自然：给 old/new 同一组输入与环境，比较 output 或 side effects。

```python
assert old_render(snapshot) == new_render(snapshot)
```

对于 text renderer、serializer、compiler output 等，golden/snapshot 也很方便，因为它会敏感地发现空格、排序、字段和文本 drift。M05 behavior probe 本质上就是这种 evidence 的一个小版本。

但这类证据必须诚实解释。它证明的是“新实现保持了当前观测到的旧行为”，不是“旧行为本来就是正确 spec”。如果旧 implementation 有 bug，differential test 会忠实地帮你保存 bug。这一点会在 M06 的 characterization test 中成为主线。

同样危险的是 implementation 改了以后顺手 update golden，然后 CI 重新变绿。在 pure structural phase，golden drift 默认应该被当作需要解释的 behavior change，而不是自动批准新的 expected output。

### Weak tests 下还能不能 refactor

可以，但 proof obligation 更难。对 IDE 能安全完成的局部 rename，static tooling + search 也许已经提供足够强的 evidence；对 control flow、transaction boundary、state machine ownership 等变化，weak tests 会显著放大风险。

这时更有用的问题不是“先把 coverage 补到 90% 吗”，而是：当前 change 最危险的 observable behavior 是什么？能否先建立 characterization、golden、differential run 或其他 targeted probe？能否把 structural change 再缩小？

如果你连“现在行为是什么”都不能可靠回答，M05 的舒适前提已经消失。下一章 M06 就从这里开始：先建立 feedback，再谈结构改善。

## 10. Reversibility：一个 change sequence 还要考虑怎样撤

比较两种 rollout history。

第一种，一个 commit 同时 rename API、迁移 caller、加 feature、删 old API。feature 出问题时，rollback 往往会把已经完成且可能正确的 caller migration 一起撤掉。

第二种：

```text
C1  add a compatible internal boundary/path
C2  migrate callers while behavior stays compatible
C3  add the feature through the new boundary
C4  remove the old path later, after evidence exists
```

如果 C3 出问题，rollback C3 可以很局部。

这并不意味着任何 change 都要被拆成四个 deploy。M08 会更完整地处理 compatibility/migration。M05 这里只要求把 reversibility 当成 design dimension：同样能到达最终状态的两条路径，rollback granularity、review cost 和 intermediate validity 可能非常不同。

如果要粗略讨论 refactoring ROI，也不必假装能精确算钱。至少可以比较：现在做这一步的 cost，与近端/future change amplification 的下降、risk reduction、review/understanding benefit，以及 rollback option。Beck 的 economics/optionality framing 在这里有启发性，但本课程不会把它写成精确 ROI 定律。

## 11. Design it twice：比较路径，不是实现两套生产代码

M02 已经使用过 “design it twice” 来训练 design judgment。M05 把它应用到 change sequence。

面对 JSON dashboard，不妨真正写出两个方案：Direct Feature 与 Preparatory + Feature，然后比较 duplicated knowledge、initial diff、new abstractions、text-drift risk、JSON complexity、未来新增状态的 change amplification、evidence cost、review cost 和 rollback 粒度。

重点是公平比较。Direct 不应该被 caricature 成“偷懒”；Preparatory 也不能因为多了 dataclass、Protocol 或 pattern 就自动加分。

这种比较还会帮助识别什么时候“小步”不够。有时现有 abstraction 根本无法表达关键安全属性、data ownership 已经不可修补、或者每次 change 都被同一个设计错误放大，此时更大的 redesign 可能合理。但要承认这可能已经超出 pure refactoring，需要自己的 design review、migration/compatibility plan 和 rollback plan。不要用 “refactor” 这个词把高风险 redesign 包装成低风险整理。

## 12. 大目标也不要求一个巨大 atomic diff

Agent 时代很容易把“能修改 500 个文件”误解成“应该一次提交 500 个文件”。Agent 确实大幅提高 implementation bandwidth，但 review bandwidth、test closure、ownership、merge conflicts、compatibility uncertainty 和 rollback granularity并不会因此消失。

Google 的 Large-Scale Changes material 很适合校正这个直觉。大规模代码迁移常常有一个 logically-related master transformation，却仍然被 shard 成可以独立测试、review、提交的 pieces。需要特别保持来源边界：Google 的 LSC 不只等于 behavior-preserving refactoring，它也可能包含功能变化，因此 **LSC != refactoring**。

一个全仓 API migration 可以有这样的 topology：

```text
introduce compatible path
→ migrate shard A
→ migrate shard B
→ migrate shard C
→ verify no remaining old callers
→ remove old path
```

是否要这样切取决于仓库、部署和 ownership 条件；这里没有固定 shard size。课程想保留的判断是：**generation size 与 reviewable change size 是两回事。**

Rename 和 move code 也能提醒我们“机械”不等于“无风险”。rename 可能影响 reflection strings、config keys、serialization names、CLI flags、dynamic imports 和 external consumers；move code 可能改变 import cycles、initialization order、module side effects、package API 或 monkeypatch target。正确 evidence 取决于真正 observable surface，而不是 IDE 把它标成 refactor 就结束。

## 13. Agent 最危险的优势之一：它不会因为 diff 太大而累

人连续改很多文件以后会自然产生 fatigue signal；Agent 没有这个 guardrail。它可以在几秒内把一个局部需求扩成全仓 cleanup，而且通常还能给出一段听起来完整的总结。

所以对 Agent 的约束不能是“请谨慎”。更有用的是把 engineering proof structure直接写进 task contract：allowed change surface、must-preserve behavior、semantic checkpoints、每阶段 evidence、non-goals，以及哪些步骤明确禁止 behavior change。

第一次探索性 patch 也不一定需要保留。让 Agent 先自由实现一个 feature，有时会非常快地暴露 coupling、hidden behavior、missing tests 和真实 change point。如果结果把 refactor、feature、bugfix、cleanup 全缠在一起，继续在这个 diff 上 patch 并不是唯一选择。

Beck 的 “Getting Untangled” 给了一个很有价值的方向：保留已经获得的 understanding，丢掉混合实现，从 clean base 按更清晰的 sequence 重做。代码生成变便宜以后，这种选择尤其合理；不要因为“已经写了很多代码”产生 sunk-cost attachment。

这不是鼓励浪费 implementation，而是在承认：**exploration 的主要产物可以是 information。**

## 14. 一个适合 Agent 的 staged refactoring workflow

M05 把前几章的能力组合成一条工作流。它不是唯一 process，但能作为初始 guardrail。

第一阶段只做 read-only reconnaissance。Agent 需要定位 entry points、state ownership、current public behavior、relevant tests、真正的 change pressure，以及可能的 shared knowledge。未知项可以明确写 UNKNOWN，不能自动归类为 implementation detail。

第二阶段写 behavior inventory，把内容分成 `must preserve / may change / needs decision`，并为主要 claim 找 evidence。对于 dashboard，existing text bytes 是 structural phase 的 must-preserve；JSON schema 则属于后来的新行为。

第三阶段 design it twice。至少比较 direct patch 与 preparatory-refactor + patch，讨论 change amplification、new abstraction、evidence cost、review complexity 和 rollback。

第四阶段才允许 structural checkpoints。每个 checkpoint只做一个主要结构目的，不引入 intended behavior change，并运行与 claim 匹配的 focused evidence；必要时再跑 full regression。

第五阶段单独进入 behavior change。新 JSON contract 应由新 tests 支撑，旧 text probe 仍需重跑，以确认 feature 没意外改变 existing output。

最后独立 review 不只看 final tree，也看 change sequence：哪些 commit/patch 声称 behavior-preserving？evidence 是否真支持这个 claim？有没有夹带 semantics drift？有没有 speculative abstraction？

这种 reasoning 也应该进入 change description，而不是只留在作者脑中。一个有用的 structural commit/PR message 至少说明：为什么现在需要这一步、它声称保持哪些 behavior、用什么 evidence 支持、以及明确不包含哪些后续 behavior change。对 dashboard 来说，`isolate dashboard fact construction from text rendering` 比 `cleanup` 更可检索；再配上 “text bytes unchanged / behavior probe + core tests / no JSON yet”，既帮助当前 reviewer，也帮助未来 archaeology。

一个具体 task contract 可以写成：

```text
Goal:
- add JSON dashboard output

Current behavior to preserve during preparatory phase:
- existing text output stays byte-for-byte identical
- job ordering unchanged
- no lifecycle changes
- no M04 public error/API behavior changes

Phase 1 — reconnaissance:
- inspect dashboard implementation and behavior probe
- identify duplicated domain/reporting knowledge
- compare direct vs preparatory path
- do not edit yet

Phase 2 — structural only:
- isolate only the shared facts justified by the JSON pressure
- do not add JSON behavior yet
- after each checkpoint, run the existing dashboard probe and core tests

Phase 3 — feature:
- add JSON output according to the lab contract
- test parsed JSON semantics rather than whitespace/key order
- re-run the old text probe

Non-goals:
- no state-ownership redesign
- no unrelated error-semantics changes
- no dependency/framework addition

Review:
- report any behavior drift explicitly
- show evidence per checkpoint, not only a final "all tests pass"
```

这个 artifact 的价值不是 prompt 更长，而是它把 Agent 的 implementation search space 限制在我们已经建立的 contract 和 evidence authority 内。

## 15. Review 一个“纯重构”时，真正要问什么

到这里可以把前面的推理压缩成 review questions。看到一个 structural PR，不必先数 LOC 或 pattern；先检查五件事。

**Intent / pressure**：为什么现在做？它服务哪个近端 change？如果没有这个 feature，是否只是 aesthetic cleanup？

**Behavior**：作者声称保持哪些 observations？有没有未写文档但可能已被 consumer 使用的 compatibility surface？error、ordering、persistence、timing 等 qualifier 是否在 move 中被吞掉？

**Structure**：change amplification 或 knowledge duplication 真下降了吗？还是只增加 abstraction count？新的 projection 是否仍然只是 projection，没有变成第二份 state authority？

**Evidence**：tests、golden、search、schema diff、benchmark、trace 等是否与本步骤 claim 匹配？如果声称 pure refactor，old/new differential evidence 能否抓住 drift？

**Topology / scope**：structure 与 behavior 是否分开？每个中间状态能运行和 review 吗？rollback 是否局部？是否夹带 bugfix、feature、formatting churn 或 unrelated cleanup？

Formatting 也属于这里。一个真实结构改动只有几十行时，顺手格式化几十个文件会淹没 visual signal。formatter change 可以做，但最好和需要 semantic reasoning 的 diff 分离。

## 16. TaskForge M05 Lab：把选择真正做一遍

实验见 [`../labs/05-refactoring-evolutionary-design.md`](../labs/05-refactoring-evolutionary-design.md)。它不会只要求你“写 JSON”。你需要先跑现有 core tests 和 behavior probe，写 behavior inventory，公平比较 Direct 与 Preparatory 两条路线，再设计 structural checkpoints。

如果选择 preparatory path，structural phase 的硬约束是：不增加 `render_dashboard_json`，不改变 existing text output，不改变 service/model/public-api semantics，也不引入第三方 dependency。每个 checkpoint 都要重跑 behavior probe 与 core suite。

只有 structural phase 能被单独 review 后，才进入 JSON behavior。Lab 对 JSON 的 schema、raw status、`exit_code`、ordering 以及“whitespace/key order 不进入 contract”都有明确要求；这些 normative details 以 lab 为 authority，正文不在这里重复发明另一套 contract。

Instructor reference 位于 [`../case-studies/m05/instructor-analysis.md`](../case-studies/m05/instructor-analysis.md)。它实际验证了一条 normalized snapshot candidate：structural phase 的三个 text fingerprints 保持不变，core tests 仍为 6 passed；加入 JSON renderer 与两组 focused tests 后，旧 probe 仍不 drift，pytest 变为 8 passed。这个结果证明的是那条 reference sequence 在当前 evidence scope 下成立，不是证明 frozen dataclass 是唯一正确 architecture。

## 17. 来源边界与本章不能推出的结论

本章的技术来源有清楚分工。

Fowler 支撑 refactoring 的窄定义、small behavior-preserving transformations、Two Hats 和 preparatory refactoring。Kent Beck 的 *Tidy First?* 用来讨论 structure/behavior separation、batch size、First/After/Later/Never 以及混合 patch 可以丢弃重做；这些是有明确个人 design philosophy 色彩的材料，不当作实证定律。Google Engineering Practices 支撑 small/self-contained CL 的 reviewability、integration 和 rollback reasoning；Software Engineering at Google 的 Large-Scale Changes 支撑大目标被 shard 成 independently testable/reviewable/submittable pieces，但 LSC 不能和 refactoring 画等号。Stanford CS190/APOSD 继续作为 design-it-twice 与 revision mindset 的辅助来源。

`semantic checkpoint`、`change topology`、Agent task contract 与 exploration-patch workflow 是本课程基于这些材料和前置模块形成的 synthesis，不冒充任何单一来源原话。

因此本章**不能推出**以下规则：每次 feature 前必须先 refactor；small 等于固定 LOC；tests green 就证明 behavior-preserving；第二个 renderer 必须抽 class/interface；所有旧 observable behavior 都永远不能改；large-scale change 必须一个 commit；Agent 只能做小 diff。真正需要保留的是更窄的 discipline：先明确 intended delta 和 must-preserve surface，再选择一条能被逐步验证、review 和 rollback 的 change sequence。

## 18. 带走的 mental model

如果只记住这一章的一条链，可以记成：

```text
real change pressure
→ inventory current observable behavior
→ compare direct vs structural preparation
→ separate structure claim from behavior claim
→ build coherent checkpoints with matched evidence
→ add the requested behavior
→ verify old behavior did not drift
→ review the sequence, not only the final tree
```

这就是 evolutionary design 在本课程里的位置。它不是“少做 upfront thinking”，而是让真实 change pressure 提供 design information，并把系统从旧状态走向新状态的过程也当作 design object。

下一章会故意拿走本章最舒服的条件：如果旧行为根本不清楚、tests 很弱、环境又难控制，那么你甚至还没有资格轻易说“behavior-preserving”。M06 会先解决这个 feedback problem。

## 可选原始资料

本章自包含；希望核对原始观点时可看：

- Martin Fowler, *Refactoring*: https://martinfowler.com/books/refactoring.html
- Fowler, Definition of Refactoring: https://martinfowler.com/bliki/DefinitionOfRefactoring.html
- Fowler, Workflows of Refactoring: https://martinfowler.com/articles/workflowsOfRefactoring/fallback.html
- Fowler, Preparatory Refactoring: https://martinfowler.com/articles/preparatory-refactoring-example.html
- Kent Beck, *Tidy First?*: https://www.oreilly.com/library/view/tidy-first/9781098151232/
- Google Engineering Practices, Small CLs: https://google.github.io/eng-practices/review/developer/small-cls.html
- *Software Engineering at Google*, Large-Scale Changes: https://abseil.io/resources/swe-book/html/ch22.html
- Stanford CS190/APOSD: https://web.stanford.edu/~ouster/cs190-winter24/lectures/aposd/

具体来源审计与取舍见 [`../reading-notes/m05-source-audit.md`](../reading-notes/m05-source-audit.md)。
