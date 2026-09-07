# M12 — Agentic Software Engineering：让 Agent 执行变化，而不是接管判断

M11 留下了一个很具体的 production 问题：TaskForge 一次接受 12 个 job，最后 12 个都成功，queue 也回到 0，所以 naive dashboard 报 `healthy=true`；但按照 M11 已经声明的 start-latency SLI，只有 2 个 accepted jobs 在 2 秒内第一次被 worker claim。

现在假设团队决定继续处理 overload。最省事的下一步似乎是把一句话扔给 coding agent：

> Add admission control so TaskForge stops overloading itself. Keep tests green.

这句话并不荒唐。一个能力很强的 Agent 也许真的能读懂代码、写出 patch、补测试，并让 CI 全绿。问题恰恰在这里：**即使 patch 看起来很好，我们仍不知道它有没有替团队做本来没有授权给它的产品和系统决策。**

M12 不把重点放在“怎样写一个更长的 prompt”。我们要解决的是更接近软件工程的问题：当实现能力越来越便宜时，怎样把一个 change 变成可委派、可停止、可验证、可独立审查的工作系统，同时让 compatibility、product semantics、SLO、release、production action 等 authority 仍然有明确 owner。

本章继续使用真实的 TaskForge starter。先复现两个 teaching probes：

```bash
cd labs/taskforge
PYTHONPATH=src uv run --with pytest --no-project python tools/m11_production_probe.py
PYTHONPATH=src uv run --with pytest --no-project python tools/m12_orchestration_probe.py
```

第二个 probe 会稳定给出这条教学链上的五个结果：vague task 是 `INSUFFICIENT_CONTRACT`，engineered task 只是 `STRUCTURALLY_COMPLETE`，unsafe plan 被 `REJECT_PLAN`，bounded plan 则 `STOP_AND_ESCALATE`；只有在 durable human decision 出现后，authorized plan 才得到 `AUTHORIZED_TO_IMPLEMENT`。

注意这个 probe 的 authority 很窄：它是一个教学用 structural policy checker，不是“Agent workflow safety verifier”。它能稳定暴露我们放进去的几类错误，却不能证明任务语义完整、实现正确、reviewer 没漏问题，更不能替人做产品决定。

## 1. Vague task 的危险不是 Agent 太笨，而是 decision space 没有边界

先不要给 Agent 任何特殊规则，直接看真实 TaskForge。当前 public submit 只是一个很浅的 wrapper：

```python
def submit_job(command: str) -> dict[str, str]:
    job_id = service.submit(command)
    return {"job_id": job_id}
```

而 `service.submit()` 做的事也很直接：分配 `job-N`，递增 `next_job_number`，创建 `Job` 并放进内存 `state.jobs`。`metrics.queued_count()` 只是从同一个 authoritative state 中统计 `QUEUED`；worker 则把第一个 queued job 变成 `RUNNING`。

于是“加 admission control”至少立刻留下这些没有答案的问题：什么时候算 overload？谁拥有 threshold？拒绝发生在创建 `Job` 前还是后？public caller 怎样区分 rejection 和 acceptance？legacy `submit_job()` 要不要改变？两个 concurrent submit 都看到一个空位时怎么办？worker 在 admission check 中间 claim 掉 job 又怎么算？M11 那个 accepted-job start-latency SLI 要怎样继续解释？

如果任务只写“make it robust”，Agent 仍然必须继续工作。它就会自然地把这些 unknown 变成自己的 assumptions。强模型可能猜得更合理，但**“猜得合理”不等于“被授权决定”**。

这也是为什么仅仅拿一个成功 patch 回头证明 prompt 足够，是循环论证。那只能证明某一次 Agent 在某个上下文里碰巧选了一个可接受解释；它没有证明下一次 Agent 不会选另一个同样 plausible、却破坏 compatibility 或 measurement contract 的解释。

到这里我们才需要给这个问题一个名字：对于较大的工程变化，我们真正需要的不是一句 natural-language request，而是一份 **delegation contract**——它不要求穷举所有实现细节，但必须把 Agent 可以探索和决定的空间，与必须停止、升级、等待新 authority 的空间分开。

## 2. Delegation contract 要约束“什么可以决定”，不只是“写什么代码”

OpenAI 当前 Codex best-practices 文档给了一个很实用的最小 prompt envelope：`Goal / Context / Constraints / Done when`。这对很多任务已经足够好，也说明 prompt 的关键不是礼貌或字数，而是让目标、上下文、限制与完成条件可见。M12 在此基础上做的是**课程综合**，不是声称存在一个业界标准字段表：对涉及 compatibility、concurrency、production evidence 或 release authority 的 change，我们还需要把更容易被悄悄猜掉的 decision rights 写出来。

TaskForge 的 engineered task 因此包含这些信息：

| Contract surface | 它要消除的危险猜测 |
|---|---|
| Goal / context | 到底要改变哪个 observable behavior，为什么现在要改 |
| Non-goals | 哪些相邻问题这次故意不解决 |
| Contracts / invariants | 哪些已有 semantics 不能被“顺手优化” |
| Allowed write paths | Agent 的 implementation blast radius 到哪里 |
| Forbidden actions | 哪些动作即使技术上能做也不在本次授权内 |
| Evidence contract | 每个完成 claim 要靠什么独立可检查 evidence |
| Stages | 什么时候只读，什么时候才允许写 |
| Stop conditions | 哪些状态出现后继续实现反而算失败 |
| Escalate when | 哪类 ambiguity 必须交给相应 owner |
| Authority matrix | exploration / implementation / review / human 各能决定什么 |
| Done when | 何时可以结束，而不是何时“看起来差不多” |

这张表不是要求所有 typo fix 都写十一节文档。一个局部、低风险、可逆、已有测试明确覆盖的小改动，可以把 contract 压成几句话。真正不能压掉的是语义：如果一个 task 仍然存在 public API、SLO、security、migration、production action 等未决问题，那么“prompt 很短”不是简洁，而是把 decision state 藏进了 Agent 的隐式推理。

同理，也不要把“先写 plan”升级成宗教。复杂、歧义大、跨多步的 change 往往值得先 plan；小而可逆的 change 可能直接进入实现更经济。关键判断是：**当前工作是否已经大到需要一个 durable artifact 来承载 decisions、unknowns、evidence 与 handoff state。**

## 3. Unsafe plan 暴露了三种不同的边界：Capability、Permission、Authority

现在看 M12 的 `unsafe-agent-plan.json`。它并不是故意写成明显的语法垃圾；相反，它会提出很多“为了尽快把系统变绿”而很诱人的动作：降低 M11 target、改 SLI population、删掉暴露旧 failure 的 probe、修改 release workflow、自己 merge、自己 deploy。

这时三个经常混在一起的概念才真正需要分开：

| 概念 | 问题 |
|---|---|
| **Capability** | Agent 技术上会不会做这件事？ |
| **Permission** | 当前工具、sandbox、credential、filesystem policy 是否允许它做？ |
| **Authority** | Agent 是否被允许替系统 owner 作出这个语义决定？ |

一个 Agent 可能完全有能力编辑 SLO probe；workspace 也可能允许它写那个文件；但这两件事都不能自动推出“它有 authority 重定义什么叫 acceptable service”。反过来，一个任务可能明确授权 Agent 修改某个 local API，但 sandbox 仍暂时不给写权限；这是 permission 不足，不是 authority 不足。

这种区分在 Agent 系统里格外重要，因为 **tool surface 本身就是 action surface**。给 Agent shell、GitHub write、cloud deploy、database admin 或 MCP tool，不只是“让它获取更多上下文”，而是在增加它可以实际产生的 side effects。当前 Codex 的公开说明甚至明确提醒：它自己的 shell sandbox 只约束 Codex-provided shell；外部 MCP tools 需要各自负责 guardrails。这个事实是当前产品实现细节，未来会变化；课程采用的稳定结论更窄：**不能因为一个 tool 出现在 Agent 上下文里，就默认它的 privilege 与本次 engineering authority 完全一致。**

所以好的系统通常会让两层同时收紧：任务 contract 说清“你不该决定什么”，tool/policy layer 再尽量让“你不该做什么”难以误做。只靠 prompt 是脆弱的；只靠权限也不够，因为很多危险决定发生在仍然合法的写路径中。

这也不是“所有重要动作必须人工点按钮”。当 policy 很成熟、blast radius 有界、动作可逆、evidence 可机器检查、rollback 真实可用时，组织完全可以授权 Agent 自动 merge 某类低风险 change，甚至自动 rollout 某个 bounded cohort。要保留的是 **authority transfer 的可解释性**，不是人工点击本身。

## 4. STOP_AND_ESCALATE 不是失败；它是工程系统的一种正确输出

`engineered-task.json` 比 vague task 完整得多，但它故意没有替 owner 做完所有产品决定。Agent 做完 read-only reconnaissance 后，`bounded-agent-plan.json` 会明确停在两个问题上：

1. overload 在 public boundary 上应该用什么稳定、machine-readable 的 result/error shape？
2. opt-in admission policy 的 capacity threshold 到底由谁提供、取什么值？

这两个问题不是“Agent 再聪明一点就能搜出来”的事实。第一个会改变 caller contract；第二个是在当前教学系统根本没有 production capacity model 的情况下选择 product policy。继续猜，反而是在越权。

于是 orchestration probe 返回 `STOP_AND_ESCALATE`。这正是本章最想训练的一个动作：**当缺的是 authority，不要把它伪装成缺更多 reasoning。**

接下来 `human-decision.json` 给出 durable decision `M12-ADMISSION-001`。它把剩余空间缩小为一个具体教学 contract：legacy `submit_job()` 不变；新增 opt-in `submit_job_admitted(...)`；accepted result 含 `accepted=true` 与 `job_id`；overload result 是 machine-readable `OVERLOADED`；threshold 由 caller/config owner 提供且必须是非负整数；negative threshold 在产生 side effect 前 `ValueError`；rejected admission 不创建 `Job`、不消耗 job id；admitted submissions 之间的 check + create 必须互斥。

这里有三个特别容易被正文写坏的 qualifier。

第一，**opt-in overall direction 已经来自 engineered task；human decision 进一步确定 exact public shape、threshold ownership/domain 与 concurrency scope。** 不能把这一段讲成 Agent 自己“想到了最合理 API”。

第二，这不是 TaskForge 的“最终架构”。legacy `submit_job()` 明确可以绕过 admission；互斥保证只覆盖 admitted submissions 彼此。worker 可以在这段时间 claim work，使一个 admission decision 变得 conservative 或很快 stale，但在已承诺的 scope 内不能让两个 admitted contenders 同时越过一个 slot。若以后产品要求“所有 submission 都受同一 global occupancy invariant”，那是新的 architecture/migration decision，不是把这把 lock 扩大一点就自然得到的结论。

第三，M11 的 denominator 必须说准确。M11 start-latency SLI 的 population 本来就是 **accepted jobs**。新的 admission rejection 发生在 acceptance 之前，因此“rejected request 不进入 accepted-job start-latency denominator”本身不是 gaming；否则我们反而改写了 M11 的 specification。真正不允许的是偷偷改变既有 accepted-work 定义、把已经 accepted 且很慢的 work 从 population 丢掉，或把 admission rejection 重新包装成 start-latency success。产品若关心 rejection/availability，就应该另外定义 admission/availability SLI，而不是让一个 start-latency SLI偷偷承担两个 contract。

这个 distinction 很重要：**保持旧 SLI specification** 与 **为新 product behavior 设计新 measurement** 可以同时成立。

## 5. Read broadly, write narrowly：先建立 change model，再动代码

Agent 最适合替人省掉的一大类工作，是大规模机械 exploration：读目录、追 call graph、搜索 symbol、找 tests、跑 probes、比历史行为。但“读得多”不应自然变成“改得多”。M12 把这条纪律写成：**read broadly, write narrowly**。

TaskForge reconnaissance 至少要把下面这条真实 path 读通：

```text
public_api.submit_job
        -> service.submit
        -> state.next_job_number + state.jobs

worker.claim_next
        -> same state.jobs

metrics.queued_count
        -> projection over same state.jobs

m11_production_probe
        -> accepted submission -> first claim evidence
```

这张图会直接约束实现：如果 rejection 必须零 job-state side effect，那么 admission check 必须发生在 `service.submit()` 分配 id / 创建 job 之前；如果不能引入第二个 lifecycle authority，就不该为了方便又造一套独立 job registry；如果 legacy path 明确不变，就不能靠偷偷重写 `submit_job()` 来“统一入口”。

Reconnaissance 输出也应该区分三种语气：`OBSERVED` 表示从当前代码/运行结果读到的事实；`SPECIFIED` 表示来自 task/human decision 的规范；`UNKNOWN` 表示仍缺 owner 决定或证据。把三者混成一段 confident summary，是 Agent workflow 里很常见的 provenance loss。

完成 change model 后才进入 narrow write。M12 reference implementation 放在教学用 disposable copy 中，不进入 canonical starter；它的一种做法是在 service owner path 里对 admitted submissions 串行化“看 queue → 决定 → 若接受则 create job”这个 critical section。**这只是对当前 bounded contract 的一个实现，不是课程强制的 admission architecture。**

## 6. Evidence contract 要先于“全绿”，否则 Candidate 会拥有自己的 Oracle

如果 completion rule 只是“tests pass”，Agent 的最短路径可能是改 implementation，也改 test；改 behavior，也改 evaluator；改 failure，也删 probe。于是 green 仍然可能是真的，但它回答的是 Candidate 自己重新定义的问题。

所以 M12 让 evidence 与 claim 配对：

| Claim | 至少要看到的 evidence |
|---|---|
| legacy path 没被静默改写 | public behavior regression |
| admitted accept 仍进入原 lifecycle | public result + authoritative state transition |
| overload rejection 没 side effect | no `Job` + no id consumption |
| invalid threshold fail-before-side-effect | boundary test |
| one-slot concurrency scope 成立 | deterministic interleaving / explicit concurrency evidence + critical-section review |
| M11 contract 没被偷偷改 | M11 probe / SLI specification path 未被重定义 |

并发尤其不能只靠“一千次 stress 没失败”。随机 stress 很有价值，但 absence of observed race 不等于 atomicity proof。M12 instructor reference 同时使用 deterministic negative control 来展示 naive check-then-create interleaving 怎样 over-admit，再用 focused test 与 code review 检查真正 critical section。这里也没有把单个 test 升级成数学证明；我们只是让不同 failure mode 由不同 evidence path 覆盖。

同理，历史 probe 失败也不能机械解释为 regression。一个旧 harness 可能是当前 product contract，也可能只是过去某个 patch shape 的教学 artifact。M12 要求先做 applicability classification：它今天仍然保护哪条语义？如果旧 harness 绑定了已不存在的内部函数名，它的失败可能说明 fixture stale；但如果它保护的 public behavior 仍在 contract 里，就不能借“历史测试过时”把它删掉。

最终 evidence packet 不只是贴命令输出，而要能让 reviewer 重建 reasoning：**claim → command/probe → observed result → scope → known gap**。Agent summary 可以是索引，但不能替代 raw diff、test output、probe、decision record 等 evidence。

## 7. Self-review 有价值，但 acceptance 需要一条不完全同源的检查路径

Implementation Agent 在交付前当然应该 self-review：重新看 diff、找 accidental scope drift、跑 targeted + regression tests、检查未跟踪文件。这会消灭很多便宜错误。课程拒绝的是另一种推论：

> “Implementer 已经自己 review 过，所以 acceptance 已经独立。”

同一个上下文、同一个错误理解、同一套 candidate-controlled tests 很容易产生 correlated failure。所谓 **independent review**，核心不是“必须换一个模型供应商”，而是让至少一条 acceptance path 不依赖 implementer 的同一套结论。它可以是 fresh-context reviewer、separate agent session、human reviewer、runtime probe、static checker、different model，或者这些组合。

M12 Lab 的 reviewer 第一轮先拿 base revision、delegation contract、human decision、candidate diff 和 raw evidence；不先拿 implementer 的“我觉得已经正确”的 conclusion summary。原因不是 summary 有毒，而是 anchoring：如果 reviewer 一开始就继承 implementer 的 framing，很容易只验证那套 framing。

Reviewer 也没有无限 authority。它可以提出“legacy path bypasses admission”这个事实，但在当前 `M12-ADMISSION-001` scope 下，这不是 blocker，因为 legacy bypass 明确是 non-guarantee；若 reviewer因此强行要求改 legacy semantics，它反而越过了 compatibility authority。Review finding 是 evidence-backed challenge，不是新的 specification。

最终仍然需要 adjudication：finding 是否真实？严重度如何？它打中了哪条已承诺 contract？修复需要扩大 authority 吗？**独立 review 减少 self-certification，不等于把 product authority 从 implementer 转交给 reviewer。**

## 8. Evaluator、review instructions 与 tool policy 都属于 trust boundary

Agent evaluation 本质上仍是软件测试里的 oracle 问题。一个 benchmark grader、CI job 或 reviewer Agent 都只能证明它被设计去检查的东西。SWE-bench 很有价值，因为它把真实 GitHub issue 与 repository-level patch/test 放到可重复环境里；但“通过 SWE-bench”不等于“真实 maintainer 一定会 merge”，更不等于“已验证 security、maintainability、operability 与长期 compatibility”。

2026 年 METR 的一项 maintainer study 很适合作为这个边界的经验提醒：4 位活跃 maintainer、3 个 SWE-bench Verified repo 对 296 个 AI-generated PR 做 review；在作者采用的 golden-baseline normalization 下，maintainer merge decision 平均比 automated-grader score 低约 24 percentage points，且很多 grader-passing PR 不会直接被 merge。研究自己明确限制了外推：repo/model/harness sample 有限，review 条件不完全等同真实贡献流程，Agent 也没有像真实开发者那样根据 feedback 迭代，所以这不是“Agent 永远过不了 review”的能力上限。

课程从中只取一个稳定结论：**automated acceptance evidence 不自动拥有 repository acceptance authority。**

当前 GitHub Copilot code review 还有一个很具体的产品例子：官方文档说明 PR review 会读取 **head branch** 中的 repository custom instructions / agent instructions / skills。于是 candidate branch 可以改变 reviewer 的一部分输入。这不代表 GitHub Copilot review “不可信”；它说明 reviewer configuration 自己也是 trust boundary，不能把“用了独立 reviewer Agent”当成自动独立。这个产品细节未来可能变化，所以我们把它留在 [M12 source audit](../reading-notes/m12-source-audit.md) 中持续校准，而不是把它写成普遍定律。

同样的原则适用于 Agent-generated tests。问题不是“AI 写 test 所以 test 低级”，而是 candidate 与 oracle 的 ownership 是否过于同源。Agent 可以大量生成 tests；高风险 acceptance 仍应有一部分来自 pre-existing contract、independent reviewer、external fixture、runtime behavior 或另一个不受 candidate 任意改写的 evidence source。

## 9. Context engineering 的目标是把工程状态放到可维护的位置

一个 coding Agent 的行为不只由最后一句 prompt 决定。model、system/developer instructions、repo guidance、working directory、tools、sandbox/approval、retrieved files、test output、previous decisions、progress artifacts 都在塑造下一步动作。把这些统称成“prompt”会隐藏真正的 engineering surface。

当前 Codex 文档提供两个很有用、但应当按产品事实来看的例子。第一，`AGENTS.md` 可以按目录作用域组合，更靠近 working directory 的 guidance 会覆盖更上层 guidance；这让规则可以和代码 ownership 一样局部化。第二，官方 ExecPlan guidance 把长任务 plan 当成 self-contained living document：新 session 不应依赖上一段隐藏对话才能继续。这些机制未来可能演进，但它们背后的问题很稳定：**长期工程状态不应该只存在某个一次性 context window 里。**

于是 repeated prompt rule 应该不断问“它真正属于哪一层”。例如：

- “不要直接写 `state.jobs`”如果是 architecture invariant，最终应落到 owner API、tests/fitness rules 或结构设计，而不是永远靠 prompt 提醒；
- “这个 task 不改 dashboard”是一次性 scope，留在 task contract 更合理；
- “所有 release 必须通过某组 policy”更可能属于 CI / release policy；
- 一次兼容性 tradeoff 的理由可能属于 ADR / design record。

这不是说所有 natural-language guidance 都要“编译成代码”。有些 judgement 无法机械检查，repo docs 仍然是合适载体。原则是：**越稳定、越高代价、越可机械验证的规则，越不应该只靠某次 Agent 记得。**

Progress file 也不能变成第二 authority。它适合记录“已读哪些文件、跑过什么命令、下一步是什么”，但如果真正的 product decision 已在 ADR / task contract / schema 中，progress note 只能指向它，不能偷偷出现一个不同版本的“事实”。

## 10. Multi-agent 的收益来自 decomposition，不来自 Agent 数量

最容易让多 Agent 变成噪声的方式，是让三个 Agent 同时改同一组文件，然后把 Git conflict 当主要协调机制。显式 merge conflict 只是最容易看见的冲突；两个 patch 即使修改不同文件，也可能分别改变 API producer 与 consumer、重复建立 authority、使用不同 error semantics，形成 **semantic conflict**。

更好的起点是先并行**问题**。例如 M12 candidate 出现后，可以让三条 read-heavy path 独立工作：一个 reviewer 看 public API/compatibility，一个看 concurrency/side effects，一个看 evidence/oracle。它们都先不写 candidate，只返回带 file/behavior references 的 findings，再由主流程 adjudicate。

这与当前 OpenAI subagent 文档给出的经验方向一致：exploration、tests、triage、summarization 等 read-heavy 工作很适合并行；write-heavy parallelism 需要更谨慎，因为 conflict 与 coordination overhead 会增加。Anthropic 的 parallel-agent/long-running harness 经验也展示了 decomposition、verifier 与 shared-artifact coordination 的价值。这里同样不能把某个 16-agent compiler experiment 的规模数字变成通用最佳实践。

决定是否并行时，先问三个软件工程问题：任务是否真的可独立分解？subtask 的 input/output contract 是否清楚？最后谁拥有 integration decision？如果答案含糊，多 Agent 只会把一个 ambiguity 复制成多个 ambiguity。

因此 task decomposition 本身就是 engineering work。它决定哪些上下文被复制、哪些 mutable surfaces 被共享、哪些 evidence 可以并行产生、哪些 decision 必须串行等待 authority。

## 11. Harness 要能随着模型能力变化，而不是把旧 workaround 永久神圣化

一个长任务常常需要 harness：初始化上下文、选择下一步、保存 progress、运行 verifier、限制工具、触发 stop/escalation、交接新 session。Harness 很重要，但“组件越多越成熟”是错误指标。

Anthropic 的公开 long-running harness 经验反复指出一个值得保留的原则：harness 中每个组件都编码了一个关于模型弱点或工作流需求的 assumption，而 assumption 会随着模型和任务变化变旧。删掉一个 component 不能靠“我觉得现在模型更聪明”；应该做对照实验，看 outcome、failure mode、cost、latency、review burden 是否真的改善。

这也解释了 **workflow** 与 **agent** 的区别。一个固定 pipeline——先静态检查、再 unit test、再 reviewer、再 human gate——可能比让一个 autonomous Agent 自己决定所有下一步更适合稳定、高风险任务；开放探索、未知 debug path 则可能更适合 Agent 自主选择工具和顺序。目标不是把 SDLC 每一步都变成 Agent，而是为每一段工作选择最便宜、最可验证的控制结构。

Model choice 也因此不是本课程的核心 abstraction。具体模型、context window、tool reliability 会快速变化；contract、authority、evidence、rollback、decomposition、review independence 则是更稳定的工程对象。

## 12. 不要用感觉衡量 Agent productivity

“Agent 写了 3000 行代码”几乎不是 productivity evidence。它甚至可能说明 scope drift、重复实现或 maintenance burden 增加。更有意义的 outcome 是：同等质量和 contract 下 cycle time 是否下降？review effort 是否下降？rework 是否下降？escaped defects 是否变化？一个 human 能否同时可靠推进更多 independent work？

METR 的 productivity work 很好地展示了为什么这件事不能靠体感下结论。它的 early-2025 RCT 在一组熟悉自己开源仓库的 experienced developers 上观察到 AI-allowed tasks 平均花时更多，约为 19% slowdown；参与者却主观认为自己更快。METR 后续在 2026 年明确说明，更广泛的 Agent adoption 造成了严重 selection effects，使后续 task-level speedup estimate 很难解释，因此不能把 2025 的数字升级成“AI 现在让程序员变慢”。

到 2026 年 5 月，METR 又发布了一项 349 名 technical workers 的 self-report survey，受访者报告的 median value uplift 很高，但研究同时强调 convenience sample、selection bias，以及“内部自洽的感知不等于真实 counterfactual productivity”。把这些研究放在一起，最稳健的课程结论不是选一个支持自己立场的数字，而是：**Agent productivity 是本地 workflow measurement problem；模型、工具、任务选择和使用者熟练度变化太快，不能用 benchmark score、代码行数或主观感觉替代真实 outcome。**

## 13. Autonomy 是可分层的 policy，不是 Human-in-the-loop Boolean

“human in the loop”听起来像一个开关：要么 Agent 全自动，要么每一步都找人。真正的工程设计更像 authority ladder。决定一个动作能否进一步自动化时，至少要看 reversibility、blast radius、evidence strength 与 policy maturity。

例如：只读 repository exploration 通常可以高度自动化；在隔离 branch 中写 scoped patch 也经常可以；生成 tests、跑 probes、整理 evidence 可以更进一步。是否自动 merge，则要看 branch protection、change type、required review 与 rollback；是否自动 deploy，要再看 canary、production SLO、stop trigger、credential scope 与回滚真实性。不可逆数据删除或高影响 schema change 可能仍需要很强的人类 authority。

这不是一条从“低级 Agent”走向“最终无人工”的成熟度路线。有些动作因为风险结构不同，会长期保留更高 gate；另一些动作则可以在 policy 足够清楚后完全自动化。

Production Agent 的 stop condition 尤其重要。Coding Agent 写坏一个隔离 branch 往往还能丢弃；Production Agent 做错 rollout、删除数据、扩大 traffic，后果可能立刻发生。因此生产 automation 要把“什么时候停止扩大影响、什么时候回滚、什么时候失去 authority”写进可执行 policy，而不是只告诉 Agent“谨慎一点”。

同样，Agent 应被允许输出 `UNKNOWN`、`STOP_AND_ESCALATE`、`NO_PATCH`。如果组织只奖励“最后必须交一个 patch”，系统就会把诚实地暴露 ambiguity 变成失败，把无依据猜测变成成功。这是激励设计问题，不是模型性格问题。

## 14. 一个完整的 Agentic Change Loop

把 TaskForge admission case 压回一条 change loop，可以看到 M12 与前面十一章并没有断开：

```text
observe a real problem
        ↓
build system/change model
        ↓
write delegation contract
        ↓
read-only reconnaissance
        ↓
unknown / authority gap ? ── yes ──> STOP + durable decision
        │ no
        ↓
scoped implementation
        ↓
claim-specific evidence
        ↓
self-review
        ↓
independent review / counterexamples
        ↓
human or policy adjudication
        ↓
merge / rollout only under explicit authority
        ↓
production evidence feeds next model
```

这里没有任何一步是因为“Agent 天生不可信”才存在。Human-written change 同样需要 contract、test、review 与 rollout。Agent 时代改变的是 scale：implementation、search、test generation、review generation 都可以变得非常便宜，于是**过去靠人类注意力隐式维持的边界，更值得被写成显式 artifact、policy 和 evidence path。**

小任务可以压缩这条 loop：不需要为了改一个 typo 建三份 JSON、两个 reviewer 和一张 authority matrix。但只要某个高代价 decision 仍然存在，压缩流程不等于压缩 owner。

M13 会把这个思想推进到更大的 capstone：当 persistence、migration、recovery、external effect 与 rollout 同时出现时，Agent implementation authority 仍然不等于 product guarantee authority。届时 task decomposition、authority record 与 evidence packet 不再只是 orchestration hygiene，而会直接决定系统是否能够安全演化。

## 15. 读完本章，应该能审查什么？

面对一个新的 Agent coding workflow，不要先问“用了几个 Agent”“prompt 多长”“是不是最强模型”。先拿一个真实 change，追下面这些问题：

- Agent 必须自己猜哪些 product / compatibility / security / SLO decisions？
- 它拥有的 tools/permissions 是否大于本次 delegated authority？
- stop/escalation 是否允许成为成功输出？
- candidate 是否能同时改 behavior 与 acceptance oracle？
- evidence 是否能由另一个上下文独立重放？
- reviewer 的 input/configuration 是否和 candidate 过度同源？
- parallel work 是否真的独立，还是把 shared semantic surface 拆给多人同时写？
- durable plan/progress 是否在记录 authority，还是偷偷成为第二 authority？
- merge/deploy/production action 的 gate 是基于风险与 policy，还是“AI/人类”这个粗标签？
- workflow 是否实际改善 cycle time、quality、review burden 与 escaped defects，而不是只增加 token、代码或活动量？

如果这些问题能回答清楚，Agent 才真正成为工程系统的一部分，而不是一个拥有模糊权限、靠善意 prompt 约束的高速实现者。

对应实践见 [M12 Lab](../labs/12-agentic-software-engineering.md)。外部材料、产品事实的时间敏感边界、METR 样本限制以及本章哪些结论属于 course synthesis，统一记录在 [M12 Source Audit](../reading-notes/m12-source-audit.md)。