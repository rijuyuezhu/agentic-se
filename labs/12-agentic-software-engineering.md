# M12 Lab — 从一句 Prompt 到可审查的 Delegation Workflow

M11 已经给了一个稳定矛盾：TaskForge 接受 12 个 job，12 个最终都成功，ending queue 也回到 0，但只有 2/12 accepted jobs 在教学目标的 2 秒内第一次被 claim。M12 不要求你直接“修性能”；它要求你把下一次 change 组织成一个 Agent 可以快速执行、却不能悄悄接管 product / SLO / compatibility / release authority 的工程流程。

本 Lab 的目标不是比 prompt engineering 技巧，也不是证明“多 Agent 一定更好”。你最终要交的是：一个真实 system model、一份 bounded delegation contract、一次正确 escalation、一个经授权的 candidate、claim-oriented verification evidence、一个 separate Review Agent 的独立 reasoning、parallel-review comparison 与 human adjudication。

## 0. 需求与实验边界

产品方向只有一句话：

> 当 burst overload 已经让 accepted work 的 start latency 大量违约时，为 TaskForge 增加一个显式 admission / backpressure seam，使 caller 可以选择在过载时拒绝新 work，而不是无限接受。

但这还不是完整 specification。Lab 故意让一些决定先保持 unresolved，再观察 Agent 是否会擅自补全。

实验必须遵守以下边界：

1. `labs/taskforge` 当前 canonical starter 是 baseline；不要把你的 feature 直接提交回 starter。
2. 真正实现必须在 disposable branch / worktree / copy 中进行。
3. 不得为了让结果变绿而重定义 M11 已声明的 start-latency SLI target、accepted-work population 或 measurement semantics。
4. 不得删除、弱化 failing historical evidence 来制造完成感。
5. implementation Agent 不拥有 merge、release、deployment 或 credential authority。
6. 第一轮 Review Agent 必须是 separate context/session，不修改 frozen candidate；runtime/static verification 不能替代这条 review reasoning path。
7. `STOP_AND_ESCALATE`、`UNKNOWN`、`NO_PATCH` 都可以是正确输出。
8. 本 Lab 的 admission decision 只形成一个 bounded teaching contract，不代表 TaskForge 的最终产品架构。

## 1. Phase 0 — 复现 canonical baseline

先在未修改的 starter 中运行：

```bash
cd labs/taskforge
PYTHONPATH=src uv run --with pytest --no-project python -m pytest -q
PYTHONPATH=src uv run --with pytest --no-project python tools/m11_production_probe.py
PYTHONPATH=src uv run --with pytest --no-project python tools/m12_orchestration_probe.py
```

记录 raw output。你至少应确认：

- core tests 为 6 个并通过；
- M11 naive dashboard 仍然是 `healthy=true`、12/12 eventual success、ending queue 0；
- M11 start-latency evidence 仍然是 `good=2 bad=10 total=12 sli=0.167 target=0.990`；
- M12 orchestration probe 依次出现 `INSUFFICIENT_CONTRACT`、`STRUCTURALLY_COMPLETE`、`REJECT_PLAN`、`STOP_AND_ESCALATE`、`AUTHORIZED_TO_IMPLEMENT`。

如果 baseline 已经不同，先停止并解释差异，不要在未知 baseline 上继续做 candidate。

### Baseline note

在你的 Lab submission / disposable workspace 中写一个很短的 `baseline.md`；不要为了记录 baseline 往 canonical starter 新增文件。它只记录可以重放的事实：base commit、三条命令、关键输出、当前工作树是否 clean。不要把“系统很慢”“应该用 bounded queue”之类解释混进去。

## 2. Phase 1 — 只看 vague task，先预测它会逼 Agent 猜什么

打开：

```text
agent-contracts/m12/vague-task.json
```

在看 engineered task 前，列出至少 8 个 Agent 必须自己猜的 decision。至少覆盖这些类别：public rejection shape、legacy compatibility、capacity threshold ownership、side-effect timing、concurrency、M11 measurement、write scope、tests/evaluator、merge/deploy authority。

然后预测三种“可能 tests 全绿但仍不该接受”的 patch。不要只写 syntax bug。参考的 failure shape 可以是：

- 把 M11 target 降低到当前数据能过；
- 把已经 accepted 且很慢的 jobs 从 start-latency population 中静默剔除；
- 接受 work 但不再记录它，使 dashboard 看起来更好；
- 改 public behavior 却没有 compatibility decision；
- 删除暴露 failure 的旧 probe。

注意第二条的口径：**M11 的 population 本来就是 accepted jobs。admission rejection 发生在 acceptance 前，因此 rejected request 不进入 accepted-job start-latency SLI 本身不是 gaming。** Gaming 是偷偷改既有 specification，例如把已 accepted 的 slow work 从 population 丢掉，或重定义“accepted”来让数字变绿。

### 可选实验：真的把 vague task 给 Coding Agent

如果你有可用 coding agent，可以在一次性 copy 中只给 vague task，观察它会做哪些 assumptions。这个实验不能作为“某模型好/坏”的 benchmark；你只记录：它做了哪些未授权决定、哪些问题主动问了、哪些问题直接猜了、它的 tests 实际保护了什么。

## 3. Phase 2 — Read-only reconnaissance，建立 change model

现在先不允许写 source。至少阅读：

```text
src/taskforge/public_api.py
src/taskforge/service.py
src/taskforge/state.py
src/taskforge/metrics.py
src/taskforge/worker.py
src/taskforge/production_signals.py
tools/m11_production_probe.py
tools/m12_orchestration_probe.py
tests/test_taskforge.py
agent-contracts/m12/*.json
```

你需要追通以下行为：

```text
public_api.submit_job
        -> service.submit
        -> next_job_number + state.jobs

worker.claim_next
        -> same state.jobs

metrics.queued_count
        -> projection over same state.jobs

M11 production evidence
        -> accepted submission -> first claim
```

搜索并回答：谁真正分配 `job_id`？谁真正创建 `Job`？queue depth 是 authoritative state 还是 projection？worker claim 会怎样改变 queued count？当前有没有任何 submit lock？legacy public result shape 是什么？

### Reconnaissance brief

每条结论必须标成以下三类之一：

- `OBSERVED`：由当前 code / test / probe 直接看到；
- `SPECIFIED`：由 task contract 或 durable decision 明确要求；
- `UNKNOWN`：仍需 owner 决定或还没有证据。

至少保留 3 个 `UNKNOWN`，除非你真的能指出它们在哪个 authority source 中已被解决。不要因为“可以合理推断”就把 unknown 写成 observed fact。

## 4. Phase 3 — 比较 engineered task：它约束的是 decision space

打开：

```text
agent-contracts/m12/engineered-task.json
```

不要评价“这个 prompt 更详细”。逐项回答：vague task 中哪些 decision 现在被绑定了？哪些仍然没有？

重点核对：

- goal 是否只要求一个 opt-in admission path，而没有宣称它会修复 M11 SLO；
- legacy behavior 是否要求保持兼容；
- rejection 是否必须在 `Job` creation / id consumption 前发生；
- 是否禁止第二套 lifecycle authority；
- allowed write paths 是否明确；
- production / merge / release 是否仍是 forbidden actions；
- evidence 是否按 claim 组织；
- stop/escalation 是否允许 Agent 在未解决产品决定时不写 patch。

运行：

```bash
PYTHONPATH=src uv run --with pytest --no-project python tools/m12_orchestration_probe.py
```

`STRUCTURALLY_COMPLETE` 只能解释为“fixture 包含 checker 要求的字段与最小内容”。它**不能**解释为“产品语义完整”或“现在就已授权 implementation”。把这条 limitation 写进报告。

## 5. Phase 4 — Review unsafe plan：找 authority drift，不要骂“Agent 笨”

打开：

```text
agent-contracts/m12/unsafe-agent-plan.json
```

先自己 review，再运行 probe。对每个问题至少给出：

| Finding | Contract / authority 被越过 | 为什么 green tests 也不能洗掉 |
|---|---|---|
| 例：降低 M11 target | measurement/product authority | 改的是 success definition，不是系统行为 |

至少覆盖五类：scope drift、authority drift、oracle capture / evidence weakening、public semantics、production action。

然后运行 orchestration probe，比较它的 `REJECT_PLAN` 与你的 review。特别记录 probe **漏掉** 了什么：这是一个 string/structure-oriented teaching checker，不是 semantic reviewer。

## 6. Phase 5 — Bounded Agent 应该停在真实未决问题上

打开：

```text
agent-contracts/m12/bounded-agent-plan.json
```

它显式留下两个 `open_questions`：

1. public boundary 如何稳定表示 overload；
2. capacity threshold 由谁拥有、取什么值。

解释为什么 implementation Agent 不应该“选一个常见设计然后继续”。你的答案必须触及 owner / compatibility / product policy，而不是只说“prompt 没写清楚”。

再次运行 orchestration probe，确认得到：

```text
BOUNDED PLAN: STOP_AND_ESCALATE
```

把这个状态当作正向 evidence：Agent 已经把缺失 authority 外部化，而不是把它藏进 patch。

## 7. Phase 6 — 读取 Human Decision Record，并做 authority-transfer audit

现在才打开：

```text
agent-contracts/m12/human-decision.json
```

确认 decision id：

```text
M12-ADMISSION-001
```

这份记录对本 Lab 授权的 feature contract 是：

### Legacy path

`submit_job()` 保持原有 public behavior。它可以绕过 admission；**这不是当前 contract 的 bug，而是明确 non-guarantee**。未来若产品要求所有 submission 都受 admission，必须新开 compatibility / migration decision。

### Opt-in admitted path

新增 public operation，reference 名为 `submit_job_admitted(...)`。具体 Python signature 可以不同，只要行为满足本 decision record。

Accepted result 必须可机器区分，并包含原 lifecycle 的 `job_id`，例如：

```json
{"accepted": true, "job_id": "job-7"}
```

Overload result 必须可机器区分，例如：

```json
{"accepted": false, "code": "OVERLOADED"}
```

### Threshold ownership and domain

`max_queued_jobs` 由 caller / config owner 提供；当前 Lab 不让 implementation Agent 发明 production capacity policy。值必须是 nonnegative integer；negative value 要在任何 job-state side effect 前抛 `ValueError`。

这不是“threshold 永远应该 caller-owned”的普遍原则，而是因为 canonical TaskForge 目前没有可信 production capacity model。

### Rejection side effects

Rejected admission：

- 不创建 `Job`；
- 不消耗 `job_id`；
- 不改变 legacy lifecycle semantics。

“No id consumed” 是本 Lab 明确 contract，不是所有真实系统都必须保证无 gap 的 universal ID rule。

### Concurrency scope

admitted submissions 之间的 admission-check + job-creation 要互斥，使 two contenders / one available slot 不会都 accepted。

边界必须写清：

- legacy `submit_job()` 不在这个互斥保证内；
- worker 可以 concurrent claim queued work；
- worker interleaving 可能让某次 admission decision conservative 或很快 stale；
- 当前只承诺 admitted-to-admitted 不 over-admit，不承诺全系统 exact global occupancy snapshot。

### M11 measurement boundary

M11 target 与 accepted-job start-latency specification 不变。Rejected admission 要作为 rejection 报告，不能重分类成 successful accepted work。

同时说明：因为 rejection 发生在 acceptance 前，它自然不属于 accepted-job start-latency denominator；若产品要评价 admission availability/rejection，需要另建 SLI specification。不要把两类 behavior 塞进一个 denominator。

### Authority-transfer table

提交一张表：

| Decision | Before record | After `M12-ADMISSION-001` | Still human/policy only? |
|---|---|---|---|
| exact public overload shape | unresolved | bounded | no, within record |
| threshold owner/domain | unresolved | bounded | value/policy owner still external |
| admitted concurrency scope | underspecified | bounded | stronger global guarantee still unresolved |
| legacy semantics | protected | protected | yes for any future change |
| M11 SLO specification | protected | protected | yes |
| merge/deploy/credentials | forbidden | forbidden | yes |

## 8. Phase 7 — Authorized implementation，只在 disposable workspace 中做

现在打开：

```text
agent-contracts/m12/authorized-agent-plan.json
```

确认它引用 `M12-ADMISSION-001`，没有 unresolved open question，且 write scope 没扩大。orchestration probe 应返回 `AUTHORIZED_TO_IMPLEMENT`。

然后在 disposable workspace 中实现**最小** feature。不要顺手：

- 改 database / RPC / message queue；
- 把 threshold 变成新的 global product config；
- 重写 legacy submit；
- 改 M11 target/specification；
- 新建第二套 authoritative job state；
- merge / deploy。

Reference instructor implementation 只是一个可能方案：在 service owner path 中，用很小的 synchronization seam 串行化 admitted submissions 的 check + create。你可以选择不同实现，只要能说明它为何满足同一个 bounded contract。

## 9. Phase 8 — 先定义 focused evidence，再看“全绿”

Candidate 至少需要以下 claim-specific evidence。

### Legacy compatibility

证明已有 `submit_job("...")` public shape / lifecycle 没被静默改写。

### Accepted admitted submit

证明：public result 是 accepted；对应 `Job` 存在；job 仍进入 canonical `QUEUED → RUNNING → terminal` lifecycle，而不是进入第二套状态机。

### Rejected admitted submit

证明：返回 machine-readable overload；无 `Job`；无 id consumption；下一次成功创建仍得到原本应得到的下一个 id。

### Invalid threshold

证明 negative threshold 在任何 mutation 前 fail，且 exception/return semantics 与 decision record 一致。

### Concurrent admitted submissions

构造 “two contenders / one available admission slot”。不能只写一个随机 thread stress 然后因为 1000 次没撞出 race 就宣布 atomic。

优先提供 deterministic interleaving seam、barrier-controlled negative control，或至少可以由 reviewer 独立检查的 critical-section reasoning。若使用 stress，写明它只能提高暴露概率，不能单独证明 absence of race。

### M11 specification not gamed

检查 candidate 没有修改 M11 target、accepted-work definition、production probe 或相关 evaluator 来制造绿色结果。这里不要错误要求 admission rejection 进入 accepted-job start-latency denominator；那会反过来改变 specification。

## 10. Phase 9 — Regression evidence 与 historical applicability

至少运行 canonical core + 这些仍适用的 probe：

```bash
PYTHONPATH=src uv run --with pytest --no-project python -m pytest -q
PYTHONPATH=src uv run --with pytest --no-project python tools/m04_boundary_probe.py
PYTHONPATH=src uv run --with pytest --no-project python tools/m05_behavior_probe.py
PYTHONPATH=src uv run --with pytest --no-project python tools/m06_legacy_probe.py
PYTHONPATH=src uv run --with pytest --no-project python tools/m07_interleaving_probe.py
PYTHONPATH=src uv run --with pytest --no-project python tools/m08_compat_probe.py
PYTHONPATH=src uv run --with pytest --no-project python tools/m09_architecture_probe.py
PYTHONPATH=src uv run --with pytest --no-project python tools/m11_production_probe.py
PYTHONPATH=src uv run --with pytest --no-project python tools/m12_orchestration_probe.py
```

不要因为 M12 feature 没部署进 `run_deterministic_burst()`，M11 仍然显示 2/12 就说实现失败。这个 Lab 只实现 opt-in mechanism，不提供 production threshold、也不改变 M11 synthetic workload。**不能 fake production outcome。**

对任何额外 historical harness，都先分类：

| 类型 | 处理 |
|---|---|
| 仍保护当前 public / semantic contract | failure 可能是真 regression，必须调查 |
| 绑定旧 patch shape / internal symbol 的教学 artifact | 记录 inapplicable 原因，不把 harness failure 冒充 product regression |

Instructor reference 中，M03 mutation harness 仍可形成有意义的 applicable check；某些 M10 replay harness 会因合法 source shape 变化失效。你不能机械复制这个结论，必须根据你自己的 candidate 重新判断 applicability。

## 11. Phase 10 — Implementation Agent evidence packet 与 self-review

Implementation Agent 最终提交：

```text
Base revision
Task contract version
Human decision id
Changed files
Claim -> evidence mapping
Commands actually run
Observed results
Known limitations / non-guarantees
Open risks
Historical probes classified inapplicable + why
```

禁止只写“all tests passed, implementation is robust”。

交给 reviewer 前，implementer 自己再看一次 diff，至少检查：write scope、SLO/evaluator、第二 state authority、legacy compatibility、concurrency scope、untracked files、unexpected generated artifacts。Self-review 是必需 hygiene，但不算 independent acceptance。随后把**完整 pre-review candidate state** 冻结并记录稳定标识（例如 disposable workspace 的 commit/hash 或等价 snapshot reference）；snapshot 必须包含本次 candidate 的新增/未跟踪文件。Phase 11 和 Phase 13 都以这一份冻结状态为输入，不在第一轮 review 中边改边审。

## 12. Phase 11 — Review Agent：第一轮不要继承 implementer conclusion

这一步是本 Lab 的 canonical two-Agent exercise：**Implementation Agent 与 Review Agent 必须是不同 context/session**。可以使用同一个 model 的新 session，不要求更换 vendor。Human reviewer 在真实工程里当然可以承担 review，但本 Lab 的 human 已被指定为下一阶段 adjudicator，因此不能用 human 或 checker 跳过 Review Agent。

Review Agent 第一轮输入按以下顺序准备：

1. base revision；
2. engineered task；
3. `M12-ADMISSION-001`；
4. candidate diff；
5. raw tests/probes/evidence。

第一轮先**不要**给 implementer 的“已经安全/正确”的 conclusion summary。Review Agent 应自己重建 change model，再找 counterexample。

至少主动检查：

- rejection 是否真的 fail-before-side-effect；
- accepted path 是否仍由原 lifecycle authority 驱动；
- two admitted contenders 能否同时越过 one slot；
- legacy bypass 是否只是明确 non-guarantee，而不是 reviewer 自己擅自升级成 blocker；
- candidate 是否控制了自己的 oracle；
- M11 start-latency specification 是否被静默改变；
- test 是行为 evidence，还是只 grep source string；
- 是否出现 scope drift / extra architecture。

Finding 使用：

```text
Severity
Claim / promised contract
Evidence / reproducer
Why it matters
Suggested next decision or fix scope
```

不要因为“这是 Agent 写的”而提高 severity，也不要因为“另一个 Agent review 过”就降低 severity。

### Acceptance path 的 independence：verification != review

不要把“不是 implementer 自己跑的”都叫 review。这里沿用 M10 的 distinction：

- **independent verification**：runtime probe、static checker、external fixture / oracle 等，检查被选中的可执行性质；
- **independent review**：一条重新恢复 contract / change model、主动寻找遗漏 risk partition 与 counterexample 的 reasoning path。本 Lab 由上面的 separate Review Agent context/session 承担。

两者都可以减少 correlated failure，而且最好组合使用；但 probe/checker 不能替代 Review Agent，Review Agent 也不能把自己的 finding 升级成 product specification。若 Review Agent 与 implementer 共用 candidate-controlled instructions / tests，也要把这个 trust boundary 写出来。

## 13. Phase 12 — Human adjudication：Reviewer 不是新的 Spec

对每个 finding 做三步判断：

1. finding 是否事实成立；
2. 它是否违反**已经承诺**的 contract；
3. 修复是否仍在现有 authority 内。

例如 reviewer 若说“legacy submit 可以绕过 admission，所以 blocker”，事实部分是对的，但当前 human decision 明确把 legacy path 排除在 admitted-to-admitted guarantee 外。若没有其它 contract 冲突，这个 finding 应被 adjudicate 为 non-blocking future architecture concern，而不是擅自扩大 feature scope。

反过来，如果 reviewer 能 deterministic 地证明 two admitted contenders 同时 accepted，或 rejection 已经递增 id，则直接命中当前 contract，属于真实 blocker。

记录最终 adjudication：accept / request change / follow-up / new human decision。不要只回复“reviewer is right/wrong”。

## 14. Phase 13 — Parallel Agent exercise：对同一 frozen candidate 并行问题

回到 Phase 11 开始前记录的**同一个 pre-review candidate snapshot**。这次不要把 Phase 11 的 findings、Phase 12 的 adjudication 或后续修复结论喂给 reviewer；目标是让三条 first-pass reasoning path 从同一输入独立起跑，而不是寻找第二个 candidate。

并行启动三个 read-only Review Agent context：

- Reviewer A：public API + compatibility；
- Reviewer B：concurrency + side effects；
- Reviewer C：evidence / oracle quality。

三个 Agent 都拿相同的 base、engineered task、`M12-ADMISSION-001`、frozen candidate 与 raw evidence；都不修改 candidate，只返回 findings 与 evidence references。保存一份简短的 **Parallel Review Comparison**，至少记录 candidate snapshot id，以及：

- wall-clock 是否真的下降；
- findings 的 overlap；
- disagreement / 互相矛盾的 assumption；
- synthesis / integration cost；
- 哪条 path 发现了其它 path 没发现的 semantic risk。

最后回答：如果把它们改成三个同时写 code 的 Agent，会新增哪些 shared mutable surface 和 semantic conflict？至少举一个“Git 无冲突但语义冲突”的例子。这个 write-heavy 场景只做分析，不要求再生成三份实现。

## 15. Phase 14 — Authority ladder：不要把 Human-in-the-loop 当 boolean

对以下动作设计 authority ladder：read repo、写 isolated patch、生成 tests、改 evaluator、merge、canary deploy、full deploy、schema migration、不可逆数据删除。

每个动作至少根据四个维度解释：

- reversibility；
- blast radius；
- evidence strength；
- policy maturity。

允许你的结论是“某类低风险 merge 可以 policy-authorized 自动执行”；也允许“某类数据操作长期需要人工 authority”。不要只写“AI 不安全所以都人工”。

## 16. Phase 15 — 把重复 Prompt Rule 放到正确机制里

把下面五条 rule 分别决定放在哪里，并说明为什么：

- “不要直接写 `state.jobs`”；
- “storage schema field number 不得复用”；
- “所有 release 必须通过 release matrix”；
- “M11 start-latency SLI 的 population 是 accepted jobs”；
- “本次 task 不改 dashboard”。

可选位置包括 task contract、repo/scoped agent instructions、unit/integration test、architecture fitness rule、CI/policy-as-code、ADR、runtime guard。

不要假设一条规则只能存在一个地方；也不要把所有内容都塞进 `AGENTS.md`。稳定程度、可机械检查程度、适用 scope 与 failure cost 应决定载体。

## 17. Phase 16 — Harness simplification 与 productivity measurement

选一个你在本 Lab 用过的 harness component，例如 mandatory plan、separate Review Agent、某个 static checker、progress file。提出一个“删掉/简化它”的小实验：什么 outcome 不变才算可删？哪些 failure mode 要专门观察？cost/token/latency/review burden 怎样比较？一次成功 run 不能证明 component 永远无用。

然后设计至少 5 个本地 productivity measure。可从这些方向选：time to first correct system model、time to mergeable patch、review blocker count、rework rounds、scope violations、correct escalations、human decision time、escaped defects、automatically completed evidence work。

每个 metric 还要写一条“怎样被 game”。例如 code volume 很容易通过生成更多无价值代码增长；time-to-first-patch 可能鼓励跳过 reconnaissance；review finding count 可能鼓励 reviewer 制造 nit。

## 18. Deliverables

最终提交十项材料：

1. **Baseline + Reconnaissance Brief**：含 base、raw commands、system model、`OBSERVED/SPECIFIED/UNKNOWN`。
2. **Vague vs Engineered Analysis**：回答哪些 decision space 被 bounded，而不是比较 prompt 长度。
3. **Authority Matrix**：至少 exploration / implementation / review / human-or-policy 四类 role。
4. **Stop / Escalation Analysis**：解释 bounded plan 为什么不应继续实现。
5. **Candidate Implementation**：只在 human decision 后、只在 disposable workspace。
6. **Evidence Packet**：按 claim 映射 raw verification evidence 与 limitation。
7. **Review Agent Findings**：标明 separate Agent context/session，并给出 severity、reproducer、contract impact。
8. **Human Adjudication**：逐条决定 blocker / follow-up / new decision。
9. **Parallel Review Comparison**：同一 frozen snapshot 上三路 review 的 overlap、disagreement、wall-clock、synthesis cost 与 semantic-risk 差异。
10. **Retrospective**：哪些机械工作 Agent 很强；哪些 judgement 交给 Agent 会 authority drift；哪些重复规则下次应迁移到 durable/executable mechanism。

## 19. 评分

| 维度 | 分值 |
|---|---:|
| System model / reconnaissance | 15 |
| Delegation contract reasoning | 20 |
| Authority / escalation judgment | 20 |
| Implementation discipline | 10 |
| Verification evidence quality | 15 |
| Review Agent + human adjudication | 10 |
| Parallel review / semantic-conflict analysis | 5 |
| Harness/productivity retrospective | 5 |

不会因为 prompt 很长、用了很多 Agent、用了最贵模型、Agent 一次写对、tests 全绿、生成很多代码或完全没有人工介入而自动高分。

真正高分来自：你能让 Agent 在明确 authority 内快速工作，在语义不足时正确停止，用独立可重放 evidence 支撑 claim，并让另一条 reasoning path 有能力推翻 candidate，同时不把 reviewer 或 grader 再升级成新的 product authority。

## 20. Lab 结束时必须能回答

当 Agent 说：

> I completed the task, all tests pass, and the system is ready to deploy.

你应该能立即回答：它是 against which contract 完成的？哪些 decision 真被 delegated？哪些仍由 human/policy owner 保留？哪些是 independent verification evidence，哪些来自 independent review reasoning？candidate 是否改了自己的 evaluator？哪个 separate Review Agent context 审了 frozen candidate？三条并行 review path 的 overlap / disagreement 是什么？哪些 finding 被怎样 adjudicate？哪些 behavior 明确 out of scope？谁拥有 merge/deploy authority？如果真的 rollout，什么 production evidence 才能确认 change hypothesis？

如果你的 workflow 已经让这些答案自然产生，而不是最后靠人从聊天记录里猜回来，才算完成 M12。
