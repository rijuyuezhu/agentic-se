# M12 Instructor Analysis — 当正确实现仍不足以证明正确委派

这份 instructor analysis 不是标准答案模板。M12 真正要评的是：学生能否区分事实、specification 与未决 judgement；能否让 Agent 在明确 authority 内高效工作；能否把正确 stop 当成成功；能否用不完全同源的 evidence/review 去挑战 candidate；以及 human/policy owner 是否在最后仍拥有真正的 product decision。

TaskForge admission case 的价值恰恰在于：最终 reference implementation 很小。若学生只交十几行 lock 代码，即使代码完全正确，也没有完成 M12。

## 1. 为什么 vague task 不能靠“Agent 恰好做对了”来辩护

`vague-task.json` 只要求“加 admission control、保持 tests green”。这没有决定 public rejection semantics、legacy compatibility、threshold ownership、side-effect timing、concurrency scope、measurement、write scope、oracle ownership 或 release authority。

因此真正的问题不是信息量少，而是 **decision space 未被 bounded**。

假设某个强 Agent 恰好做出与 instructor reference 一样的实现，也只能说明这一 run 选择了一个可接受 interpretation。它不能证明 prompt 排除了这些同样 plausible 的替代路径：直接改 legacy `submit_job()`、把 overload 当 exception、把 threshold 写成 global constant、在 reject 前先 allocate id、把 M11 target 调低、删掉旧 probe、自己 merge/deploy。

评分时不要因为最终 patch 正确就反向给 vague task 高分。委派质量要看它在实现**之前**约束了什么。

## 2. Engineered task 的价值：把已有 judgement 写成 contract，把未知保留为未知

`engineered-task.json` 不只是“更长 prompt”。它做了四件关键事。

第一，它保护已有系统语义：legacy path 默认兼容；rejection 必须零 job-state side effect；accepted work 继续进入已有 lifecycle；不能建立第二套 lifecycle authority；M11 start-latency SLI 仍按原 accepted-job population 解释。

第二，它限制 implementation blast radius：只允许修改列出的 TaskForge code/tests/tools，不允许把数据库、RPC、message queue、production deployment 之类架构变化偷带进来。

第三，它把 evidence 先写在 candidate 前面：legacy compatibility、accepted lifecycle、rejection side effect、concurrency、M11 measurement 都有 claim-oriented evidence obligation。

第四，也是最重要的，它允许 `STOP_AND_ESCALATE`。Task contract 不要求 implementation Agent 在所有情况下交 patch。

这里仍有未决问题，所以 `m12_orchestration_probe.py` 对 engineered task 只返回 `STRUCTURALLY_COMPLETE`。Instructor 必须明确告诉学生：这个结果只说明 fixture 满足 structural checker 的字段要求，不等于“现在已经有完整产品 specification”。

## 3. Unsafe plan 的根因是 authority drift，而不是“Agent 方案不优雅”

Unsafe plan 降低 M11 target、改 measurement population、删除旧 probe、修改 release workflow，并准备 merge/deploy。这些动作表面上都能帮助“完成任务”，但它们越过了不同 owner。

最典型的是把 99% target 改成 15%。代码甚至可能完全没 bug，dashboard 也真的会绿；但它没有改善 accepted-job start latency，只是改了 success definition。类似地，如果 candidate 把已经 accepted 且很慢的 jobs 从 SLI population 中移除，也是在重写 specification，而不是修系统。

这里要纠正旧教材里一个容易误导的说法：**pre-acceptance admission rejection 不属于 M11 accepted-job start-latency denominator，本身不是 denominator gaming。** M11 的 cohort 从来就是 accepted jobs。真正要保护的是：不要偷偷重定义 accepted-work population，也不要把 admission rejection 说成 start-latency success。若产品关心 rejection/availability，应另建对应 SLI。

删除 M11 probe 也不是普通 cleanup，因为它是当前 accepted-work behavior 的 evidence。只有在先证明 harness 已因 version-specific source shape 失效、而它原保护的 product contract 已被其它 evidence 接住时，才可以把“fixture stale”与“product regression”区分开。

因此 unsafe plan 的 root cause 可以概括成：implementation authority 膨胀成了 specification、oracle、release 与 production authority。

## 4. 为什么 bounded plan 的正确输出是 Stop

`bounded-agent-plan.json` 完成了足够 reconnaissance，并明确留下两个 open questions：public overload result shape，以及 capacity threshold ownership/value。

这两个问题都不是从 current code 能“发现”的事实。Public shape 会影响 caller compatibility；threshold 则是 product/capacity policy，而 canonical TaskForge 没有任何可信 production capacity model。Implementation Agent 若自己选一个常见答案，实际上是在把 unknown 伪装成 observed fact。

因此 `STOP_AND_ESCALATE` 应给正分。课程要惩罚的不是“问人”，而是：本来缺 authority，却为了保持 execution momentum 把它变成 assumption。

Instructor 也不要要求 Agent 事事停下来。若 task contract 已明确把某类 design choice delegated 给 implementation role，那么 Agent 可以自己选择并解释 tradeoff。**模型信心不是 authority grant；task/decision record 才是。**

## 5. `M12-ADMISSION-001` 究竟授权了什么

Human decision record 将剩余空间局部闭合。Reference interpretation 是：

- legacy `submit_job()` 不变；
- 新增 opt-in admitted operation，reference 名为 `submit_job_admitted(...)`；
- accepted result machine-readable，并返回 `job_id`；
- overload result machine-readable，code 为 `OVERLOADED`；
- threshold 由 caller/config owner 提供；
- threshold 必须是 nonnegative integer；negative value 在任何 mutation 前 `ValueError`；
- rejected admission 不创建 `Job`，不消耗 id；
- admitted submissions 之间的 check + job creation 串行化；
- legacy submissions 不在该 concurrency guarantee 内；
- worker claim 可以并发发生，可能让决定 conservative/stale，但不能导致 admitted-to-admitted over-admission；
- M11 target 与 accepted-job start-latency specification 不变。

两点 provenance/authority qualifier 必须保留。

**Opt-in API 不是唯一正确架构。** 这是为 bounded teaching lab 选择的兼容性较小方案；代价是存在两个 submission path，legacy 可以 bypass。未来如果要 mandatory global admission，需要新的 compatibility/migration/architecture decision。

**Caller-owned threshold 也不是 universal best practice。** Reference 这么做只是因为 starter 没有 production capacity model。真实系统完全可能由 config service、autoscaler、queue owner 或 policy engine 拥有这个值。

Human decision record 本身也不是“最终架构 authority”。它只是一次 bounded feature decision，未来可以被新的、更高层 decision supersede。

## 6. Reference implementation 为什么很小，却仍需要精确 scope

Instructor reference 只在临时 TaskForge 副本中实现，不进入 canonical starter。核心 seam 可以写成：

```python
_admission_lock = threading.Lock()


def submit_admitted(command: str, *, max_queued_jobs: int) -> str | None:
    if max_queued_jobs < 0:
        raise ValueError(...)

    with _admission_lock:
        queued = sum(
            job.status == JobStatus.QUEUED
            for job in state.jobs.values()
        )
        if queued >= max_queued_jobs:
            return None
        return submit(command)
```

Public wrapper 再把 `None` 投影成 `{"accepted": false, "code": "OVERLOADED"}`，accepted id 投影成 `{"accepted": true, "job_id": ...}`。

为什么 lock 只保护 admitted path？因为 promised scope 只是“concurrent admitted calls 对彼此串行化 check + create”，不是“所有 TaskForge mutation 在一个 global lock 下线性化”。把 legacy submit、worker claim、所有 state mutation 全部塞进去，会悄悄扩大 architecture claim。

Worker 可能在 admitted request counting/creation 附近 claim queued work。当前 contract 接受这一点：它可能让 admission 决定偏保守，或让读取很快过时。如果需求升级为“所有 submission/claim 在一个 global occupancy linearization point 上精确一致”，当前设计就不够，需要回到 M07/M09 重做 ownership 与 concurrency model。

Instructor 不应把“有 lock”当正确性结论。正确性来自 contract scope 与实现 critical section 的对应。

## 7. 为什么 negative threshold 必须先写进 decision，再写 test

Negative threshold 最初很容易被当成普通 input-validation nit。但如果没有提前规定，reference implementer 可能自己选择 clamp 到 0、接受所有、抛异常或返回 overload；随后 test 再照着 implementation 写，就会形成：

```text
implementation choice
    -> test expectation
    -> retroactive "contract"
```

M12 要反过来：先让 owner 明确 domain 与 failure timing，再让 Agent 写 implementation/test。于是 negative value 的意义不只是 boundary test，而是一个小型 oracle-ownership exercise。

## 8. 五个 focused tests 各证明什么、又不证明什么

临时 reference 在 6 个 core tests 之外增加 5 个 focused tests，合计实际为 `11 passed`。

**Legacy public shape** 检查 `submit_job("echo legacy") == {"job_id": "job-1"}`。它支持 compatibility claim，但不能单独证明所有 legacy behavior 都没变，所以仍要跑历史 regression probes。

**Accepted admitted submit** 检查 accepted result、`job-1` 与 `QUEUED` state，目的是证明 new boundary 没有创建 parallel lifecycle representation。

**Rejected admitted submit** 使用序列：第一次 admitted 得到 `job-1`；第二次 overload；随后 legacy submit 得到 `job-2`。这同时验证 reject 没新增 `Job` 且没消耗 allocator id。这里的 no-gap 是本 Lab contract，不应推广成全系统 ID 原则。

**Invalid threshold** 检查 negative value `ValueError`、state 仍为空、下一次 valid submit 仍得到 `job-1`，从而支持 fail-before-side-effect。

**Two contenders / one slot** 用 barrier 让两个线程竞争 `max_queued_jobs=1`，要求结果恰好一个 accepted、一个 `OVERLOADED`、总共一个 `Job`。这个 test 观察到了正确 behavior，但**单独不能证明 atomicity**。

## 9. Concurrency evidence 为什么需要 negative control + code review + behavior test

一个极 plausible 的错误实现是：先 `queued_count()`，再单独 `submit()`。若 A、B 都在 queue=0 时读取，然后 barrier 后分别 submit，就会得到 two accepted jobs。

Instructor 的 deterministic negative control 实际展示过类似结果：

```text
A observes queue=0
B observes queue=0
A submit
B submit
=> two accepted jobs under a one-slot policy
```

因此 reference concurrency argument 是组合证据：contract 先声明 admitted check+create 要串行；naive split-step 有 deterministic counterexample；reference code 把 count + reject/submit 放在同一个 admitted-path critical section；public concurrent test 又观察到 at most one acceptance。

任何一个单项都不应被夸大。随机 stress 可以补充，但“1000 次没撞到 race”不是 absence-of-race proof。

## 10. Regression evidence：M11 仍旧 2/12 不是 M12 失败

Reference 临时副本跑过 core 与 M04/M05/M06/M07/M08/M09/M11/M12 相关 probes，既有行为保持。一个容易误判的现象是：`m11_production_probe.py` 仍然显示原来的 overload gap。

这是正确的。M12 reference 只添加 opt-in mechanism；它没有把生产 synthetic burst 改成走 admitted API，也没有提供 production threshold。若为了展示“feature 修好了 production”而修改 M11 workload/target，就会把教学 evidence 伪造成 deployment result。

M12 要学生能说：**mechanism implemented != policy selected != rollout performed != production outcome proven**。

## 11. Historical harness applicability 不能机械化

Instructor reference 中，M03 mutation harness 仍能运行并产生原来的教学现象；某个 M10 replay harness 则因为 M12 合法 source evolution 不再匹配旧 patch shape，被分类为 version-scoped teaching artifact，而不是 product regression。

这不是让学生背结论。Candidate 不同，applicability 也可能不同。正确做法是问：这个 historical harness 原本保护什么 semantic contract？今天那个 contract 仍在吗？失败是 behavior 变了，还是 harness 只绑定了旧内部形状？是否已有新的、更直接 evidence 接住同一 promise？

“旧测试红了所以一定不能改”与“旧测试红了所以删掉”都是懒惰判断。

## 12. Reviewer 最容易犯的错：把自己的偏好升级成 specification

一个常见 reviewer finding 是：

> legacy `submit_job()` 可以绕过 admission，因此实现不安全，必须 blocker。

事实前半句成立，但当前 human decision 明确只承诺 admitted-to-admitted scope，legacy bypass 是 non-guarantee。因此在没有其它 contract 的前提下，这应记录成未来 mandatory-admission architecture concern，而不是本次 blocker。

真正的 blocker 例子包括：rejection 已经消耗 id；two admitted contenders 可同时 accepted；candidate 改了 legacy public shape；negative threshold mutation 后才失败；candidate 改 M11 accepted-work definition 让 evidence 变绿。

Independent review 的目的不是“找得越多越好”，而是找到**能击中 promised behavior 的 counterexample**。

## 13. Reviewer 的输入顺序也是 independence design

第一轮 reviewer 最好先拿 base、task contract、human decision、candidate diff、raw evidence，而不是先看 implementer summary。这样可以减少 framing/anchoring correlation。

Independent 也不要求必须换模型。Fresh context、separate session、different role、human、runtime probe、static checker 都可以贡献不同 failure path。相反，即使换了模型，如果两边完全继承 candidate-controlled instructions、tests 与 conclusions，也可能高度相关。

当前 GitHub Copilot code review 会从 PR head branch 读取 custom instructions / agent instructions / skills，是一个很好的 product-specific trust-boundary例子：review Agent 的 configuration 本身可能由 candidate branch 影响。Instructor 应把它讲成当前产品机制，不要升级成“AI review 天生不独立”的普遍定律。

Reviewer finding 最终仍需要 adjudication。Reviewer 不是新的 product owner。

## 14. Multi-agent exercise 真正评的是 decomposition

M12 推荐把 read-only review 拆成 public API/compatibility、concurrency/side effect、evidence/oracle 三条 path，因为这些问题有相对独立的 evidence surface。三个 reviewer 可以并行，然后集中 adjudicate。

如果学生只是让三个人同时改 `service.py` 和 `public_api.py`，再展示 Git 能 merge，不应给高分。Git conflict 只是 text collision；semantic conflict 还包括 producer/consumer 选择不同 error contract、两个 agent 分别新增 competing state owner、一个改 API 另一个按旧 API 写 consumer。

评分时看：subtask boundaries 是否清楚、shared mutable surface 是否被压小、输出是否有 evidence contract、最后 integration authority 是否明确。Agent 数量本身没有分。

## 15. Evals 与 productivity：数据只能支持有限结论

METR 2026 maintainer study 可以用来说明 automated grader 与 maintainer acceptance 不是同一 oracle。要保留样本事实：4 位活跃 maintainer、3 个 SWE-bench Verified repo、296 个 AI-generated PR；golden-baseline normalization 下，maintainer merge decision 平均约比 automated-grader score 低 24 percentage points。也要一起讲限制：repo/model/harness sample 有限、review 环境不是完整现实贡献流程、Agent 没有 feedback iteration、研究不声称 fundamental capability ceiling。

Productivity study 同样不能被写成 slogan。Early-2025 RCT 在特定 experienced OSS developer/repo setting 观察到约 19% slowdown，同时 participants perceived speedup；2026 follow-up 又因 adoption 带来的 selection effects，明确认为 task-level current speedup estimate 难以可靠解释。

到 2026 年 5 月，METR 对 349 名 technical workers 的 self-report survey 给出很高的 median perceived value uplift，但作者同时强调 convenience sample、selection bias，以及 perception 无法直接验证真实 counterfactual productivity。Instructor 应利用这个“看起来互相张力”的 evidence 教学生：不要挑一条数字替 workflow 做结论。

本课程只要求学生测自己的 outcome：cycle time、rework、review effort、escaped defects、scope violations、correct escalations、human decision burden 等。Code volume、token count、Agent count 与“感觉快”都不能独立成为 productivity proxy。

## 16. Human gate 的目标是保留 novel judgement，不是保留所有机械工作

M12 的 authority ladder 不是“Agent 永远低权限”。若一个 judgement 已经稳定到可以写成明确 policy、可机器检查 evidence、bounded action 与可靠 rollback，那么把它自动化是合理的 engineering improvement。

例如 isolated read、scoped patch、test execution 常常可以高度自动；某类低风险 merge 也可能被 branch policy 自动授权；bounded canary 在强 stop trigger 下可能进一步自动化。另一方面，不可逆数据删除、全量 schema migration、未知 blast-radius production action 可能仍需要更高 human authority。

Instructor 要看学生是否用 reversibility、blast radius、evidence strength、policy maturity 做判断，而不是用“AI safe/unsafe”二元分类。

Correct escalation 也必须得分。若 rubric 事实上奖励“Agent 最终总能交 patch”，学生会学到错误激励：隐藏 uncertainty 比暴露 uncertainty 更容易成功。

## 17. Source audit 对本章的 authority 边界

本章外部材料只能支撑它们真正支撑的部分。

OpenAI 当前 Codex material 支撑：清楚的 goal/context/constraints/done-when、复杂任务 planning、durable `AGENTS.md`/ExecPlan、subagent read-heavy parallelism、sandbox/approval/tool surface 等当前产品实践。M12 扩展出的十一项 delegation contract、`STOP_AND_ESCALATE` 状态机与四角色 authority matrix 是**课程综合**，不是 OpenAI 标准。

Anthropic material 支撑：workflow/agent distinction、simplest adequate orchestration、long-running progress/context artifacts、parallel team/harness 的具体经验。它不证明“多 Agent 更好”或固定 team size。

SWE-bench/METR 支撑 automated eval 与 maintainer acceptance gap 的经验事实，但不支撑“benchmark 无用”或“AI 不能写 mergeable code”。

GitHub review instructions 是当前 product fact，必须随产品文档校准。

Capability / Permission / Authority 三分法、read broadly/write narrowly、authority ladder、claim-oriented evidence packet 等，是课程为了把前面 M00-M11 的软件工程原则映射到 Agent workflow 而做的 synthesis。不要伪装成某一 vendor 的 quoted framework。

详细 provenance 见 [M12 Source Audit](../../reading-notes/m12-source-audit.md)。

## 18. 实际验证记录与 instructor acceptance bar

Canonical starter 在本轮审计中实际复现：

```text
core tests: 6 passed
M11: good=2 bad=10 total=12 sli=0.167 target=0.990
M12 vague: INSUFFICIENT_CONTRACT
M12 unsafe: REJECT_PLAN
M12 bounded: STOP_AND_ESCALATE
M12 authorized: AUTHORIZED_TO_IMPLEMENT
```

Instructor reference 曾在临时副本中验证：

```text
6 core + 5 focused M12 tests = 11 passed
one-slot naive negative control -> 2 accepted
M04/M05/M06/M07/M08/M09/M11/M12 applicable regressions -> pass/unchanged teaching behavior
M03 mutation harness -> still applicable in that reference
M10 replay harness -> version-scoped/inapplicable after that source evolution
```

线程返回 `job-1` / `job-2` 的顺序不重要；negative control 重要的是 accepted count 变成 2，证明 naive split check/create 可以 over-admit。

最后的评分标准可以压成一句话：**M12 不追求让 Agent 尽量少问人，而是让它尽量少做未经授权的猜测；不要求 human 保留机械工作，而要求 novel judgement 有明确 owner，并把已经稳定的 judgement 逐步迁移到 contract、tests、policy 与 tool guardrails。**