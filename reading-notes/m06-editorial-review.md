# M06 Editorial Review — Legacy Takeover 的 feedback-first 重写

> 本记录用于 issue #2 的 M06 主讲义 editorial rewrite。它记录 merge-base semantic mapping、source boundary、cold-reader / dependency sweep 和作者侧 self-corrections；不替代独立 reviewer，也不新增 technical provenance。

## 1. 为什么 M06 单独成批

M05 与 M06 连续，但不适合放进同一 semantic-review batch。

M05 的起点是：

```text
observable behavior 已较清楚
+ existing tests / exact dashboard probe
→ 怎样把 structural change 与 behavior change 拆成可证明 sequence
```

M06 故意撤掉这个前提：

```text
requested change 已知
+ 部分 preservation obligation 已知
+ concrete old behavior 不完整
+ relevant feedback 不足
→ 怎样先获得可信 observation，再决定是否/怎样修改
```

因此 M06 的核心 review question 不再只是“change topology 是否清楚”，而是“作者凭什么把 UNKNOWN 升级为 OBSERVED / MUST-PRESERVE / NEW SPEC”。这是一套独立的 evidence-authority 问题。

M07 又会进入 concurrency/lifecycle/crash temporal model，应继续单独 review；本批不提前承担它的 correctness burden。

## 2. 新版 running problem

新版只沿着 TaskForge `legacy_audit.publish_daily_audit()` 的 `failed-only` 需求推进：

```text
M05 的 known-behavior discipline
→ 发现 M06 只知道要 preserve 某些旧 semantics，却不知道 concrete old value
→ read-only 看 legacy_audit 的 ambient dependencies / effects
→ 运行 starter probe
→ observation 与 intended product contract 分离
→ legacy condition framing
→ effect sketch / targeted feedback
→ 遇到 observability + nondeterminism
→ sensing / separation
→ 观察现有 module/env/tempdir control points
→ seam / enabling point
→ characterization 的 oracle 与 negative control
→ 决定是否需要 formalize production seam
→ reference 允许 no production seam change
→ 新 failed-only contract + invalid-input no-effect
→ test fixture authority / fidelity
→ hermeticity vs fidelity
→ hypothesis/history/runtime evidence
→ Agent staged takeover
→ review epistemic chain
```

与旧版相比，术语没有被删除，而是尽量等到 running problem 已经产生对应压力后才命名。

## 3. Merge-base semantic preservation map

### 3.1 M05 舒适前提 / legacy change 的 unknown

旧版 §0–§3 的核心：

- M05 有 known behavior + baseline evidence；M06 没有同样条件；
- legacy 不是情绪词；
- observed behavior != correct behavior；
- observed behavior 也不能无意识改变；
- declared contract 与 actual dependency surface 可能不一致。

新版落点：§1–§3。

额外 precision：lab 本身已经明确要求 preserve existing ordering/file naming/append/formatting semantics，因此不能把这些维度写成“完全没有 normative authority”。新版区分：

```text
preservation obligation: specified by lab requirement
concrete old value: discovered through characterization
long-term product contract: not established by this lab alone
```

### 3.2 Characterization test

旧版 §4、§13–§15 的核心：

- characterization 记录当前行为，不证明其正确；
- bug 可以在新 spec 下被有意识改变；
- experiment 要 controlled/repeatable/high-signal；
- freeze nondeterminism；
- boundary behavior 往往比 private helper 更值得第一批保护；
- safety net 要通过 deliberate break / mutant 证明有牙齿。

新版落点：§2、§7、§9。

新版还实际检查了 starter probe：它 assert fragments + stdout write counts，同时打印 hashes；**打印 fingerprint 不等于 exact-byte assertion**。正文明确这个证据边界，避免把 probe output 自然化成比代码真实更强的 oracle。

### 3.3 Targeted feedback / change-test-observation points / pinch point

旧版 §5、§6、§11 的核心：

- 不先追全局 coverage；
- 围绕当前 change point 画 effect region；
- change point、test/control point、observation point 可以不同；
- 找高 leverage / pinch point，而不是全系统拆开。

新版落点：§4。

新版明确 effect sketch 是 **change-scoped projection**，不是完整 system/state model；没画到的 state/error/lifecycle dimension不意味着不存在。

### 3.4 Sensing / separation

旧版 §7 的核心 distinction 完整保留：

- sensing = 能运行但看不到/难判断 effect；
- separation = 无法在受控环境运行，因为拖入不希望真实使用的 dependency；
- remediation 不同；
- external effect 不等于必须 mock。

新版落点：§5，并直接绑定 TaskForge 的 stdout、filesystem、clock、hostname；database 只作为 transfer case。

### 3.5 Seam / enabling point / seam techniques

旧版 §8–§10：

- seam 不是 interface 同义词；
- enabling point 是 alternate behavior 被选择的位置；
- parameter/module/filesystem/process 等都可能提供 seam；
- 最小 seam，不建立全套 provider graph。

新版落点：§6、§8。

Technique catalog 被压成 transfer examples，符合 source audit：课程吸收 decision process，不要求背 WELC 的语言年代特定 catalog。

### 3.6 “找到 seam”不等于“新增 production seam”

旧版和 instructor case 的重要 design judgment：

- Python module binding + env + tempdir + stdout capture 已足够建立 current feedback；
- reference 不需要 `AuditRuntime/ClockProtocol/...`；
- `_select_jobs()` 也可接受但非必要；
- formalized seam / helper 只能由 current pressure 支撑。

新版 §8、§9 保留，并把它提升为本章最关键的 design-decision dependency：读者先看到 existing control path 确实能工作，之后才比较 formalize / no production change / small runtime context 三类 candidate。

### 3.7 Unit / integration、hermeticity / fidelity、test doubles

旧版 §18–§20：

- legacy takeover 不必从 unit test 开始；
- high-level characterization production diff 小且 fidelity 高，但慢/定位差/setup 重；
- hermeticity 与 fidelity 有 trade-off；
- 不为了 cheap deterministic dependency 开 seam；
- interaction-only mocks 可能保护 implementation choreography。

新版落点：§11，并在 §8 的 “什么时候不值得新增 seam” 前置一个紧贴 design decision 的限制。

### 3.8 Hypothesis-driven exploration / history evidence

旧版 §22–§23：

- read-only static summary 不足；
- hypothesis → probe → observation → model update；
- history/issue/old PR 有价值但不是 oracle。

新版落点：§12。

### 3.9 Agent workflow / task contract / independent review

旧版 §24–§27：

- read-only reconnaissance；
- runtime probes；
- characterization；
- minimal seam only if needed；
- explicit behavior change；
- independent review；
- bad prompt 不应混 understand/structure/behavior；
- remaining unknowns 要留下。

新版落点：§13–§14，并显式允许 `no production seam change`，避免 Agent task contract 自己预设 design conclusion。

### 3.10 Architecture relation / gradual de-legacy

旧版 §28–§32：

- legacy != architecture rewrite；
- 局部反馈改善可以很小；
- 系统不是一次从 legacy 变 modern；
- 多次 change 累积 boundary/feedback/contract knowledge。

新版落点：§15–§16 与 final reasoning chain。

## 4. Source / provenance spot check

### Michael Feathers / WELC

Source-backed：

- working with feedback 的 priority；
- sensing / separation distinction；
- seam / enabling point；
- characterization test；
- targeted testing / change-related feedback；
- dependency-breaking technique catalog 的存在。

新版没有把课程扩展版 legacy definition 归给 Feathers。

### Martin Fowler — Legacy Seam

Source-backed usage：

- seam 的现代 restatement；
- function-parameter 等现代 example；
- seam 可服务 test substitution 以外的 probe / observability / displacement。

新版只把“以后可能成为 migration boundary”保持为 conditional future use，不据此授权当前创建 framework。

### Software Engineering at Google

Source-backed usage：

- hermeticity 的 determinism/isolation；
- larger testing 中 fidelity 与 hermeticity 是不同维度；
- excessive test-double / interaction coupling 的维护问题。

新版没有推出固定 test pyramid 或“integration 永远优于 unit”。

### Course synthesis

新版明确标记：

- `Legacy condition = change without enough trustworthy change-relevant feedback` 是课程扩展 framing；
- effect sketch；
- Agent staged takeover / task contract；
- “write authority 依赖 evidence” expression。

它们不冒充单一来源原话。

## 5. Abstraction dependency sweep

### Characterization

Starter tool 的真实输出包含 `legacy audit characterization probe passed`，因此 reader 会在正式定义前看到字符串。新版显式说这是工具标签，先不要求理解；随后在观察 empty/mixed/append 后才解释 characterization 的认识论位置。

### Legacy condition

章节标题不可避免使用 Legacy，代码名也叫 `legacy_audit`；但课程自己的 formal `Legacy condition` definition 放到 §3，之前先让 reader 遇到“知道 preservation obligation、却不知道 concrete old behavior”的 feedback gap。

### Sensing / separation

第一次 canonical naming 在 §5。§1–§4 只描述“看不到 effect / 控制不了 nondeterminism”的底层现象和 control/observation points，不提前要求 Feathers vocabulary。

### Seam / enabling point

第一次 canonical teaching naming 在 §6。此前 narrative 只说 control point / controlled environment，不出现 canonical seam decision。§6 先展示 starter probe 真实使用 module/env/tempdir，再命名 seam/enabling point。

### M07 temporal vocabulary

新版不提前引入 linearization、race、lease、fencing、attempt identity 等 M07+ canonical constructs。结尾只说明下一章会加入 concurrency/cancellation/retry/crash/restart pressure。

## 6. Design-decision dependency sweep

### Production dependency abstraction

开场 `Clock/FileSystem/AuditRepository` 只作为常见冲动，不作为答案。真正 decision criterion 在 §5–§8 建立：当前 problem 是 sensing 还是 separation？已有 control point 是否足够？新增 concept 是否解决 current risk？

之后才比较：

1. broad provider object graph；
2. no production structural change（instructor reference）；
3. conditional small runtime context。

因此 no-production-seam reference 不会因为前文 repeated wording 提前获得 design authority。

### `_select_jobs()`

只在 §9 新 behavior 已清楚后出现，明确是 acceptable-but-not-required candidate；没有把 pure helper 当“为了可测试必须抽”的规则。

### Observed behavior / compatibility

新版不会因为 current behavior 被 characterization 就把它升级成 permanent public contract；同时也不会因为“只是 observed”就忽略 lab 更宽的 `default scope must preserve existing behavior` obligation。ordering / file naming / append / formatting 又被 requirement 特别点名，因此是更显眼的 review surface，但不是 preservation surface 的全部。

## 7. State/model projection 与 temporal consistency sweep

### State/model projection

两个需要显式 scope 的 artifact 已处理：

- §4 effect sketch 明确只是 current change 的 effect-region projection；
- §10 audit file 明确只是 reporting projection，不是 job lifecycle 的第二 authority，未投影的 state dimension不等于不存在。

Test fixture 继续通过 `submit → claim_next → finish` 等合法 authority 构造 lifecycle state，不用 direct state mutation“作弊”。

### Temporal consistency

M06 没有新增 acceptance/completion/recovery 分期 contract，不应借本章发明 M07 的 temporal model。

本章唯一明确的 effect-order guarantee 是 lab 的 invalid scope：必须在 filesystem mutation 前 reject。新版把它绑定到 M04 no-effect-on-rejection reasoning，没有泛化成“所有 errors 都 no effect”。

Append 是跨 invocation 的 observed/preserve surface，但不被重新解释成 durability/exactly-once promise。

## 8. Cold-reader flow

新版 cold-reader 路线：

```text
我知道需求要求 preserve 旧 semantics
→ 但旧 semantics 到底是什么？
→ 静态阅读只能提出问题
→ 运行 probe 得到 observations
→ observation 与 product contract 不同，但可和 preservation requirement 组合成 local change contract
→ 这正是 change-without-feedback 的 legacy condition
→ 围绕 failed-only 画 effect region
→ 发现问题既有“看不见”也有“控制不了”
→ sensing / separation
→ starter probe 原来已经利用 control points
→ 这类结构机会叫 seam
→ 但是否要把它 formalize？
→ reference 甚至选择不改 production structure
→ 有反馈以后才进入 failed-only contract
→ review evidence authority，而不是只看 final diff
```

相比旧版三十多个顶层节，reader 应更容易感觉每个 abstraction 是前一个 unresolved problem 的回答。

## 9. 本轮 self-sweep 实际修正的问题

1. **Contract authority regression — 初稿先把 ordering/append/formatting 当成纯 observed quirks，第一次修正后又把 general default-preserve clause 看窄了。** Lab 不仅点名 preserve existing ordering/file naming/append/formatting semantics，还先规定 `default scope must preserve existing behavior`。最终改成“broad local preservation obligation + probe 提供 concrete old value；named dimensions 是重点 review surface”，同时避免把 exercise-local preservation 升级成永久 product contract。
2. **Probe evidence strength — 初稿容易让 fingerprint 看起来像 exact golden。** 实际 `m06_legacy_probe.py` assert fragments 与 stdout write count，只打印 SHA。新版显式区分 printed evidence 与 asserted oracle。
3. **Abstraction dependency — starter output 提前出现 `characterization` 字符串。** 不能改真实 output；正文明确其先只是工具标签，再在 observation pressure 后正式解释。
4. **Design authority — seam 容易被教学本身 naturalize 成必须新增 production interface。** 新版把 instructor 的 `no production seam change` 作为关键合法答案，并公平保留 small runtime-context candidate。
5. **M02 state authority 容易在 legacy fixture 中丢失。** 新版恢复合法 lifecycle fixture 与 audit projection 的 authority/scope reasoning。
6. **M07 dependency — 不把 concurrency/retry/crash 在本章展开成提前的 temporal model。** 只在结尾作为下一章 pressure。

这些修正来自 merge-base/source/lab/case-study 对照，而不是格式统计。

## 10. 仍需独立 reviewer 判断

作者侧 self-review 后，仍应由 cold reviewer 独立判断：

- §1–§3 是否把“preservation obligation 已知但 concrete old behavior 未知”讲得足够自然，而不是过度认识论化；
- formal Legacy condition 放在 §3 是否比开场定义更顺；
- §4–§6 从 effect sketch 到 sensing/separation 再到 seam 的 dependency order 是否真的自然；
- §7 对 starter probe “hash 只是 printed evidence” 的精度是否帮助读者理解 oracle，而没有陷入实现细节；
- §8 的 no-production-seam reference 是否保持为 case-specific judgment，而非新的 universal anti-DI rule；
- §9–§11 是否保留足够具体的 failed-only behavior/evidence，而不是后半章又退化成概念综述；
- 约 450 行的新版是否把 WELC 中有用的 transfer judgment 压得过薄。

## 11. Validation record

本轮最终验证实际执行：

```bash
cd labs/taskforge
PYTHONPATH=src uv run --with pytest --no-project python -m pytest -q
PYTHONPATH=src uv run --with pytest --no-project python tools/m06_legacy_probe.py
```

结果：core suite `6 passed`；starter probe 继续报告 `legacy audit characterization probe passed`，fingerprints 保持为：

```text
empty:  file=7e90999a594bd448 stdout=d114f9f2994a6701
mixed:  file=7821f1fa9ec08dd4 stdout=3fd157cf98872494
append: file=4e15e48d03660f50 stdout=de715a35f8db4b21
```

同时实际检查：

- `git diff --check`：通过；
- M06 module + review record relative links：通过；
- 两个 Markdown 文件 fence balance / one page H1：通过；
- 两个目标文件 secret-pattern scan：无 finding；
- 无 `uv.lock`；
- abstraction dependency：formal sensing/separation 在 §5；seam/enabling point 在 §6；§6 前无 canonical seam/enabling-point leak；
- `linearization / fencing / lease / attempt identity / expand-contract / exactly once` 等 later-module canonical vocabulary 无 finding；
- 当前 `git status --short` 只包含 M06 module 修改与本 review record 新文件。
