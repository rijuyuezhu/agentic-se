# M12 Source Audit — Agentic Software Engineering

> 本文件记录 M12 真正检查过的一手/近一手材料、课程吸收的具体 claim、以及明确不升级成课程定律的内容。
>
> 目标不是证明“某家 Agent 最强”，而是回答：**当 coding agent 已经能读仓库、改代码、跑命令、并行工作时，什么 engineering discipline 仍然必须由 harness / process / human authority 明确表达？**

> Freshness note (2026-09-07)：本轮 rewrite 重新核对了当前 OpenAI Codex guidance、GitHub Copilot code-review instruction behavior 与 2026 METR productivity material。下面凡属 current product behavior 的 claim 都按当前文档表述，不升级成稳定行业规则。

---

## 0. 本章审计问题

M12 不是一个产品使用教程。

本轮材料审计围绕这些问题：

1. 一个复杂 coding task 的 durable context 应该怎样表达？
2. 为什么“长 prompt”不等于 reliable harness？
3. planning artifact 在长任务里有什么真实作用？
4. parallel agents 什么时候有帮助，什么时候只增加 coordination cost？
5. sandbox / approval / tool permission 与 engineering authority 是什么关系？
6. Agent 的 self-test / benchmark pass 为什么不能自动等于 mergeable？
7. 长时间、多 context window 的任务怎样留下可恢复的 progress state？
8. 怎样把“Agent 能做什么”与“Agent 被授权做什么”分开？
9. 怎样评估 agent workflow，而不是只看最后 patch 是否碰巧过 grader？
10. 当前关于 AI productivity 的证据到底支持什么、又不支持什么？

---

# 1. OpenAI Codex — Best practices

URL:

https://learn.chatgpt.com/guides/best-practices

本轮实际检查的当前内容包括：

- prompt default fields；
- planning guidance；
- `AGENTS.md`；
- sandbox / approval；
- testing / validation / review；
- MCP context。

当前文档给出的 prompt default 是：

```text
Goal
Context
Constraints
Done when
```

这组字段很适合本课程，但课程不会把它当成完整 change specification。

M01–M11 已经说明，复杂变更还可能需要：

```text
non-goals
behavior table
invariants
authority ownership
compatibility window
failure semantics
production evidence
rollback / stop conditions
```

所以 M12 的判断是：

> `Goal / Context / Constraints / Done when` 是一个很好的最小 task envelope，不是软件工程 contract 的完整上限。

文档还明确建议：

- complex / ambiguous task 先 plan；
- `AGENTS.md` 保存 durable repository guidance；
- instruction 应 practical、concise，反复出现的问题再固化；
- sandbox / approval 默认保持较紧，只有在明确需要时扩大；
- 不要停在“make a change”，还应 test、run checks、confirm result、review diff。

课程吸收：

```text
prompt text
!=
workflow architecture
```

真正稳定的 guidance 应逐渐转化为 repository artifact / executable command / test / policy，而不是每次靠人记得重新说一遍。

本章不会照搬的内容：

- 特定 Codex slash command；
- 特定 reasoning level；
- 特定 UI 操作；
- “某种 Codex 配置就是所有 Agent 的正确配置”。

这些属于产品层实现，可能快速变化。

---

# 2. OpenAI Codex — `AGENTS.md`

URL:

https://learn.chatgpt.com/docs/agent-configuration/agents-md

本轮实际检查：

- Codex 在工作前读取 `AGENTS.md`；
- global → project root → current directory 的层级发现；
- closer instruction 覆盖更上层 guidance；
- guidance 是按目录 scope 组合的，而不是只有单一 root prompt。

这提供一个很具体的工程启示：

> **Agent context 也需要 modularity 和 scope。**

如果把所有知识塞进根目录一个 5000 行 instructions 文件：

- unrelated subsystem rule 会污染当前任务；
- local exceptions 难表达；
- stale guidance 难发现；
- reviewer 难知道某条规则到底影响哪个路径。

因此 M12 会使用：

```text
repository invariants
  +
path-local constraints
  +
task-specific contract
```

三层 context model。

这不是说每个 repo 都必须采用 `AGENTS.md` 这个文件名。

真正的课程 claim 是：

> durable agent guidance 应有明确 scope、precedence 和 ownership。

---

# 3. OpenAI Codex — ExecPlans / `PLANS.md`

URL:

https://developers.openai.com/cookbook/articles/codex_exec_plans

本轮检查的核心不是模板格式，而是：

- complex / long-running work 可以使用 self-contained execution plan；
- plan 是 living document；
- 使用者可以在长 implementation 开始前验证 approach；
- plan 应假设后续执行者只拥有当前 working tree + plan，而没有隐藏记忆。

这个“没有隐藏记忆”的假设非常重要。

课程将其改写成：

> **Durable plan 的质量，可以用“新的 engineer / Agent 能否只凭 repository artifact 恢复正确工作状态”来检验。**

这与 M06 legacy takeover、M08 migration、M09 ADR 是同一条线。

M12 不要求每个复杂任务都写长篇 ExecPlan。

应该按任务规模选择：

```text
small, reversible change
→ concise task contract

cross-cutting / multi-stage / long-running change
→ durable plan artifact
```

也就是说：

> planning artifact 的目的不是增加 ceremony，而是降低 hidden state。

---

# 4. OpenAI Codex — Subagents

URL:

https://learn.chatgpt.com/docs/agent-configuration/subagents

本轮实际检查：

- subagent workflow 把 noisy intermediate work 从主线程移走；
- context pollution / context rot 是明确考虑的问题；
- read-heavy exploration、tests、triage、summarization 是较好的并行起点；
- parallel write-heavy workflow 要更谨慎，因为会增加 conflict 和 coordination overhead；
- subagent 本身增加 token / tool work 成本；
- prompt 应明确分工以及最终返回什么 summary/output。

这给 M12 一个直接的 parallelism 原则：

```text
parallelize independent questions
before
parallelizing shared mutable code
```

例如：

```text
Agent A: recover state ownership
Agent B: audit compatibility surface
Agent C: map tests / evidence
```

通常比：

```text
Agent A/B/C simultaneously edit service.py
```

更容易获得净收益。

这与传统 parallel software development 完全同构：

- shared mutable workspace 是 coordination surface；
- merge conflict 只是显性 conflict；
- semantic conflict 更危险。

课程不会把“multi-agent”本身作为 maturity 标志。

如果一个 agent + 一个清晰 task 已经足够：

```text
更多 agents
→ more cost + more coordination
```

未必更好。

---

# 5. OpenAI — Unrolling the Codex agent loop

URL:

https://openai.com/index/unrolling-the-codex-agent-loop/

本轮检查的关键内容：

- agent loop 是 user → model → tool → new context → model 的反馈循环；
- 软件 Agent 的主要输出不一定是 assistant text，而可能是环境中的代码变更；
- context window / compaction 是 harness responsibility；
- instructions、tools、input 共同决定当前 agent 的执行环境；
- Codex shell sandbox 只约束 Codex 提供的 shell tool；MCP 等外部 tool 必须自己实现 guardrails；
- sandbox / approval / cwd 等会改变 Agent 的可执行 action / permission surface；它们可以用于 enforcement，但不会自动授予 engineering authority。

课程吸收：

> **Tool availability / sandbox policy 是 authority enforcement design 的一部分，不只是 convenience；但 tool permission 本身不是 engineering authority grant。**

例如：

```text
read repo
run unit tests
write feature branch
```

与：

```text
merge main
rotate credentials
delete production data
deploy release
```

不是同一类能力。

因此 M12 会明确区分：

```text
capability
permission
authority
```

- Capability：Agent 技术上能否调用某个动作；
- Permission：当前 execution environment 是否允许；
- Authority：组织/系统语义上是否应该由它决定。

有 permission 不代表有 authority。

一个拥有 production shell token 的 Agent，仍然可能**没有**“看到 CI 绿就自动 deploy”的 engineering authority。

---

# 6. Anthropic — Building effective agents

URL:

https://www.anthropic.com/engineering/building-effective-agents

Published: 2024-12-19。

页面当前明确提醒：工具生态已经变化，但文章中的 architecture distinction 仍然值得参考。

本轮检查：

- workflow 与 agent 的区分；
- workflow 使用预定义 code path；
- agent 动态决定过程与工具使用；
- 建议优先选择最简单能工作的方案；
- 更高 autonomy 会带来 latency / cost / unpredictability tradeoff。

课程吸收：

> **不要把所有软件工程工作都包装成 fully autonomous loop。**

有些阶段非常适合 deterministic workflow：

```text
run exact regression suite
check forbidden path edits
validate migration matrix
secret scan
```

有些阶段适合 Agent：

```text
repo reconnaissance
hypothesis generation
implementation alternatives
failure-mode search
```

因此 M12 不追求：

```text
maximum autonomy
```

而追求：

```text
right autonomy at the right boundary
```

---

# 7. Anthropic — Effective harnesses for long-running agents

URL:

https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents

Published: 2025-11-26。

本轮检查到的实际 failure modes：

1. Agent 试图一次完成过大的 scope；
2. context window 结束时留下 half-implemented / undocumented state；
3. 新 session 无法恢复前一轮 mental state；
4. later session 看到“已经做了很多”就 premature victory；
5. Agent 会做局部/unit/curl 检查，但未必真正 end-to-end 验证。

其 harness 做法包括：

- initializer / later coding session 分离；
- feature list；
- progress artifact；
- git history；
- 一次推进一个小 feature；
- 每轮 leave clean state；
- 每轮开始先恢复 working state 并跑基本 end-to-end check。

课程吸收：

```text
context continuity
should be externalized
```

不能依赖：

```text
“这个 Agent 还记得上一轮”
```

M12 会把 durable state 分成：

```text
product state
engineering state
agent conversation state
```

真正重要的 engineering state 应尽量存在 repo / issue / plan / commit / test artifact 中，而不是只存在 chat history。

限制：

这篇文章来自一个特定 full-stack app harness 实验。

课程不会把：

- `claude-progress.txt`；
- JSON feature list；
- initializer-agent 两阶段；

作为 universal format。

吸收的是底层原则：

> incremental + recoverable + externally visible progress。

---

# 8. Anthropic — Harness design for long-running application development

URL:

https://www.anthropic.com/engineering/harness-design-long-running-apps

Published: 2026-03-24。

本轮检查到一个很重要的 meta lesson：

> harness 中每个 component 都编码了“模型自己做不到什么”的假设；这些假设可能错误，也会随着模型能力变化而 stale。

文章描述通过：

```text
remove one harness component
→ observe impact
```

来识别哪些部分真正 load-bearing。

课程因此增加：

> **Agent harness 也需要 evolutionary design。**

不能因为某个 guardrail 在 2025 年必要，就永久保留。

也不能因为新模型一次成功，就删除所有 guardrail。

更好的方法是：

```text
identify invariant / risk
→ instrument failures
→ simplify one mechanism
→ compare evidence
```

这与 M05 refactoring / M11 production evidence 完全同构。

---

# 9. Anthropic — Demystifying evals for AI agents

URL:

https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents

Published: 2026-01-09。

本轮检查：

- agent eval 不只是单轮 output test；
- Agent 多轮调用工具并修改环境，错误可能累积；
- evaluation 需要 input + grader / success logic；
- static grader 也可能错，因为 Agent 可能找到 evaluator 没预计到的合法路径。

这与 M03 的 test-oracle reasoning 很一致。

课程吸收：

```text
agent eval
=
executable claim about an agent workflow
```

而不是：

```text
score = truth
```

M12 会要求对 Agent workflow 的 eval 同样问：

- grader 测了什么？
- 哪些 failure 没覆盖？
- agent 能否 game evaluator？
- evaluator 是否把一个合法 alternative 判成错误？
- prod acceptance criteria 是否比 benchmark 更丰富？

---

# 10. Anthropic — Building a C compiler with a team of parallel Claudes

URL:

https://www.anthropic.com/engineering/building-c-compiler

Published: 2026-02-05。

这是一篇 capability / harness experiment，不是 controlled software-engineering textbook。

但实际内容对 M12 很有用：

- 16 agents / ~2000 sessions；
- fresh container + shared git upstream；
- task locking；
- agent specialization；
- extremely high-quality tests / verifier；
- context 输出要被控制，避免大量无用 test output；
- parallelism 在独立 failing tests 上有效，在单一 shared bottleneck 上反而让 agents 互相覆盖；
- 作者明确警告：tests pass 很容易让人误以为 job done；production deployment 仍需要 personally verified engineering judgment。

课程吸收的不是规模数字。

核心是：

```text
Agent throughput
is bounded by
verification quality + task decomposition + coordination surface
```

尤其：

> verifier 越弱，Agent 越可能高效地完成错误目标。

这正是 M03 / M10 的结论在 Agent scale 下的放大版。

---

# 11. SWE-bench original paper

URL:

https://arxiv.org/abs/2310.06770

本轮使用它只建立 benchmark scope：

- 真实 GitHub issues；
- repo-level code changes；
- test-based evaluation；
- 需要跨函数 / class / file 理解与修改。

这说明 agentic coding 已经不只是 autocomplete benchmark。

但 M12 **不会用 SWE-bench score 直接代表真实工程 competence**。

原因见下一节。

---

# 12. METR 2026 — Many SWE-bench-Passing PRs Would Not Be Merged into Main

URL:

https://metr.org/notes/2026-03-10-many-swe-bench-passing-prs-would-not-be-merged-into-main/

Published: 2026-03-10。

这是 M12 最重要的 empirical counterweight 之一。

本轮实际检查的结果与 limitation：

- 4 名 active maintainers；
- 3 个 SWE-bench Verified repositories；
- review 296 个 AI-generated PRs；
- test-passing / automated-grader score 与 maintainer merge judgment 存在明显 gap；
- 文章 summary 用“roughly half”描述很多 test-passing AI PR 仍不会被 maintainer merge；
- automated grader 平均比 maintainer judgment 高约 24 percentage points（其具体 normalization / sample caveat 见原文）；
- rejection 不只有 code quality，也包括 break other code / core functionality；
- 研究明确不声称这是 agent fundamental capability ceiling；Agents 没有像真实 human contributor 一样多轮接收 reviewer feedback；
- 只覆盖 SWE-bench 的部分 repo / model / harness，maintainer judgment 自身也有 noise。

课程吸收：

> **Automated acceptance evidence 和 repository acceptance authority 是不同东西。**

这不是反对 Agent，也不是反对 benchmark。

相反，它支持 M10/M12 的核心流程：

```text
implementation
→ automated evidence
→ independent review
→ feedback / iteration
→ merge decision
```

而不是：

```text
benchmark/test pass
→ merge
```

---

# 13. METR — Developer productivity evidence

Early-2025 study:

https://metr.org/blog/2025-07-10-early-2025-ai-experienced-os-dev-study/

2026 methodology update:

https://metr.org/blog/2026-02-24-uplift-update/

课程使用这组材料的目的不是宣称：

```text
AI makes developers slower
```

或：

```text
AI now gives X% speedup
```

因为当前 evidence 明确不支持这么粗暴的结论。

实际情况：

- early-2025 RCT 在一组 experienced open-source developers / mature familiar repos 中观测到 19% slowdown；
- 参与者自己却主观认为被加速；
- 2026 follow-up 明确指出后续实验遭遇严重 selection effects，数据不再能可靠估计 current effect；
- 后续 raw data 对 late-2025 tools 给出一些 speedup signal，但作者明确认为 size estimate 很不可靠；
- 使用多 Agent 并行还让传统“单 task time-spent”测量变得更困难。

课程真正吸收：

> **不要用“感觉更快”评估 Agent workflow。**

要测量：

```text
cycle time
review time
rework
escaped defects
change size
handoff cost
rollback / incident rate
maintainer acceptance
```

并根据实际 workflow 调整 measurement model。

## 13.1 METR 2026-05 — self-reported technical-worker survey

Primary source:

https://metr.org/blog/2026-05-11-ai-usage-survey/

Published: 2026-05-11。

本轮 rewrite 新增核对这份更新材料，因为它提供了一个很好的 measurement counterexample，而不是因为它给出了一个可复制的 productivity 数字：

- survey 覆盖 349 名 technical workers；
- 三种 self-reported value-uplift measure 的 median 落在约 `1.4x–2x`；
- median self-reported speed change 约为 `3x`；
- 作者明确区分 value 与 raw speed，并指出 task substitution 会让两者偏离；
- 结果是 self-report；样本是 convenience sample，存在 selection bias；
- 不同问法虽然有一定内部一致性，但这不能验证 respondents 对“没有 AI 时会怎样”的 counterfactual perception 就是真实 causal productivity effect。

课程吸收：

> **主观 speed/value uplift 是 workflow evidence 的一种，但不能单独替代可观测的 cycle time、review/rework、quality、acceptance 与 escaped-defect evidence。**

因此 M12 同时保留 early-2025 RCT、2026 selection-effect update 与这份 2026 self-report survey，而不是挑一个最支持“AI 很快”或“AI 很慢”的数字。

---

# 14. GitHub Copilot Code Review docs

URLs:

https://docs.github.com/en/copilot/concepts/agents/code-review

https://docs.github.com/en/copilot/tutorials/customize-code-review

本轮使用的不是 GitHub 的产品结论，而是几个具体 operational fact：

- automated review 可以读取 repository custom instructions / `AGENTS.md` / skills；
- GitHub 文档自己明确说明 AI review 具有 nondeterminism、context limit，specific instructions 比 vague directives 更可靠；
- code review 能连接 MCP / repository context；
- repository instruction 本身也进入 review context。

这里出现一个值得课程特别强调的 subtle risk：

> **如果 reviewer 的 instruction 来自 candidate branch，那么 change 可以同时修改 code 和 reviewer context。**

GitHub 当前文档明确说明 Copilot review 使用 head branch 中的 instructions / skills。

所以组织如果把 Agent review 当作 required control，需要考虑：

```text
who owns reviewer policy?
can the change under review modify it?
```

这与 classic CI 的：

```text
PR can edit its own workflow / tests
```

属于同一类 authority problem。

课程不会因此说“AI review 没用”。

结论是：

> reviewer configuration 也必须被纳入 trust boundary。

---

# 15. 本章综合模型

这些材料来自不同厂商、研究团队和时间点，但共同指向一个稳定结构：

```text
                Human / Team Engineering Authority
                              │
          defines contract / permissions / acceptance / escalation
                              │
                              ▼
                  ┌─────────────────────┐
                  │     Agent Harness   │
                  │ context / tools     │
                  │ sandbox / plan      │
                  │ progress / verifier │
                  └─────────────────────┘
                       │          │
              exploration       implementation
                       │          │
                       └────┬─────┘
                            ▼
                      durable artifact
                 code / tests / plans / logs
                            │
                            ▼
                    independent evidence
                            │
                            ▼
                    independent review
                            │
                            ▼
                      human decision
```

课程的核心判断仍然是：

> **Agent 可以替代越来越多 implementation effort，但 engineering authority 只有在我们显式设计 transfer 时才会转移。**

---

# 16. M12 明确拒绝升级成“定律”的说法

以下都不会成为本课程 rule：

## 16.1 “Prompt 越长越好”

错误。

需要的是：

```text
relevant + scoped + durable + testable context
```

---

## 16.2 “一定先让 Agent 写 plan”

错误。

小而可逆的 change 可能直接实现更便宜。

计划的收益必须超过 ceremony。

---

## 16.3 “两个 Agent 一定比一个 Agent 好”

错误。

parallel write-heavy task 可能增加 semantic/merge coordination cost。

---

## 16.4 “实现 Agent 不能 review 自己”

作为唯一 acceptance authority：通常不够独立。

但 self-review 仍然有价值。

更准确：

```text
self-review
+
independent acceptance path
```

---

## 16.5 “所有 production action 都必须人工点按钮”

不是 universal rule。

如果某动作：

- scope bounded；
- reversible；
- policy explicit；
- evidence machine-checkable；
- blast radius small；
- automated action 本身长期验证可靠；

则可以把 authority 显式委托给 automation / Agent。

真正的问题是：

> authority transfer 是否经过设计，而不是是否有人类 click。

---

## 16.6 “SWE-bench score 就是软件工程能力”

错误。

benchmark 是 evidence source，不是完整 real-world acceptance model。

---

## 16.7 “AI 一定提高/降低开发效率”

当前 evidence 强烈依赖：

- model/tool generation；
- developer familiarity；
- task type；
- repo maturity；
- workflow；
- measurement method；
- whether parallelism is used。

课程不把任何单一 uplift 数字写成未来恒定事实。

---

# 17. 对 M12 教学设计的直接影响

M12 应当训练学生产出这些 artifacts：

```text
1. Read-only reconnaissance brief
2. Human-approved system/change model
3. Agent Task Contract
4. Authority matrix
5. Staged implementation plan
6. Evidence contract
7. Stop / escalation conditions
8. Implementer output
9. Independent reviewer findings
10. Human adjudication record
```

比“写一个好 prompt”重要得多。

---

# 18. TaskForge M12 适合施加的 pressure

前面模块已经具备：

- M04 public boundary；
- M07 concurrency / crash；
- M08 compatibility；
- M09 architecture；
- M10 review；
- M11 user-centered SLO / overload evidence。

因此 M12 的任务不应该再是一个孤立 helper。

适合的需求：

> **在 TaskForge accepted-job start-latency SLO 已经明显要被违反时，引入一个 opt-in admission / overload-protection seam；pre-acceptance rejection 必须显式报告，不能被重分类成 accepted-work success，也不能借机静默重定义既有 accepted-job SLI population。若产品要评价 rejection / admission availability，应另行声明对应 SLI specification。**

这个 change 天然要求重新判断：

```text
API semantics
queue authority
concurrency
accepted-job SLI specification / admission-rejection measurement
error contract
backpressure
compatibility
review
production evidence
```

所以它很适合拿来测试 Agent orchestration，而不是测试编码速度。

---

# 19. Source-quality conclusion

M12 不需要一部“Agentic Software Engineering 圣经”。

当前最可靠的组合是：

- **OpenAI Codex current docs**：实际 coding-agent context / plan / permissions / subagent workflow；
- **Anthropic engineering reports**：long-running harness / multi-agent failure modes / verifier / incremental progress；
- **SWE-bench original**：repo-level benchmark scope；
- **METR 2026 maintainer-review study**：automated grader 与 real acceptance 的 gap；
- **METR productivity studies**：不要用 subjective speedup 感觉代替 measurement；
- **GitHub current docs**：AI reviewer context / instructions / trust-boundary 的具体产品事实。

它们共同支持本课程自己综合出的结论：

> **Agentic Software Engineering 的核心，不是让 Agent 更像一个自主程序员；而是把 software-engineering knowledge 转化为可被 Agent 消费、可被机器验证、可被独立 review、并且不会越过未经授权 authority boundary 的工作系统。**
