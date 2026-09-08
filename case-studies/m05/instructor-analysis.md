---
id: case-M05
type: case_study
visibility: instructor
related: [M05]
---
# M05 Instructor Reference — Staged Refactoring of TaskForge Dashboard

> **Spoiler warning**：完成 [`../../labs/05-refactoring-evolutionary-design.md`](../../labs/05-refactoring-evolutionary-design.md) 前不要读。
>
> 这不是唯一正确设计。它记录一条实际执行并验证过的 reference change sequence，以及为什么 reference 没有继续“抽象到底”。对应 technical provenance 与 source limitations 见 [`../../reading-notes/m05-source-audit.md`](../../reading-notes/m05-source-audit.md)。

M05 的 starter 没有 broken behavior。相反，`render_dashboard()` 对当前 contract 是正确的；问题只在一个新的 JSON dashboard request 出现后变得可见：现有函数同时读取 jobs、解释 lifecycle、累计 counts、决定 active/terminal policy、生成 text-specific status label，再拼最终文本。最直接的方案是复制这套逻辑写 JSON；另一条路线是先把两个 renderer 真正共享的 facts 收敛出来，再增加新 behavior。

两条都能工作，所以本章不是“找到唯一 clean design”，而是训练如何把 **structural claim** 与 **behavioral claim** 分开，并让 reviewer 能逐步验证它们。

## 1. Baseline：先证明旧 dashboard 现在确实工作

Canonical starter 的 behavior probe：

```bash
cd labs/taskforge
PYTHONPATH=src uv run --with pytest --no-project python tools/m05_behavior_probe.py
```

当前记录为：

```text
[OK] empty: sha256=eaadf634b7104332
[OK] queued: sha256=ec17ac5523b4b8bd
[OK] mixed: sha256=1181854b1e08cc1c
all existing text dashboard behavior preserved
```

Core suite 同时是 `6 passed`。这组 evidence 的意义不是“代码已经设计得很好”，而是给后面的 behavior-preserving claim 建立一个明确 baseline。

Reference 在 structural phase 把 must-preserve surface 定义为 `render_dashboard(title)` 的当前 observable text behavior，包括 default/custom title、summary 字段与顺序、per-status counts、active/terminal 定义、`jobs:` 行、empty 时 `<none>`、job insertion order、各 status label、succeeded/failed 的 `status(exit_code)` 形式，以及 command 原样输出。

Non-goals 同样重要：这一阶段不改变 service、worker、model、M04 public API，不修 state ownership，不增加 JSON behavior。即使旁边存在更漂亮的 API 设计，也不能借“重构”把它偷偷带进来。

## 2. Direct JSON path 是真实 alternative，不是 strawman

最直接的实现可以在 `render_dashboard_json()` 中重新读取 `service.list_jobs()`，再复制 count/status classification：

```python
def render_dashboard_json(...):
    jobs = service.list_jobs()
    queued = 0
    running = 0
    ...
```

这条路线有真实优势：initial diff 最小、不增加新 internal model、实现快。如果 JSON 只是一次性 debug output，复制十几行可能比建立共享 abstraction 更经济。

问题在于当前 duplication 不只是 syntax。Text renderer 已经知道：

- `active = queued + running`；
- `terminal = succeeded + failed + cancelled`；
- 每个 `JobStatus` 如何进入 counts；
- list order 就是当前 dashboard order；
- succeeded/failed 的 exit code 如何进入 presentation。

如果 JSON 再独立解释一遍这些 facts，未来加入新的 lifecycle state 时，两个 renderer 会拥有两份需要同步修改的 policy knowledge。这才是 preparatory pressure；不是因为“duplicate code 看起来不 DRY”。

## 3. Reference 共享的是 normalized facts，不是 rendering framework

Reference 选择一个很小的 read-time projection：

```text
DashboardSnapshot
├── title
├── counts
└── jobs
```

其中每个 job 保存 raw semantic facts：`id`、`command`、`JobStatus`、`exit_code`。它**不**保存类似 `"succeeded(0)"` 的 text presentation string。

这个 distinction 很关键。`status=SUCCEEDED + exit_code=0` 是两个 renderer 都可能需要的事实；`succeeded(0)` 则是 text representation。如果 snapshot 只保存 presentation string，JSON renderer 反而要把文本重新拆回结构化数据，dependency direction 就倒过来了。

Reference 也把 counts 放进 snapshot，因为当前 `active / terminal / per-status count` 是两个 renderers 都必须一致理解的 reporting policy。另一个合理 design 是 snapshot 只保存 jobs、每个 renderer 自己算 counts；如果这些 counts 根本不是 shared policy，那样可能更简单。Reference choice 来自当前 repeated-knowledge pressure，不是“snapshot 应该包含统计值”的通用规则。

同样，reference **没有**创建 `Renderer` interface、`TextRenderer` / `JsonRenderer` hierarchy、registry 或 provider layer。两个 output 的 composition shape 本来就不同：一个是 text lines，一个是 nested JSON data。当前真正共享的是 fact construction，而不是一个复杂 polymorphic rendering lifecycle。为了 pattern consistency 强行建立 renderer framework，只会把这次很小的 change 变成新的 shallow abstraction。

## 4. Snapshot 是 projection，不是第二份 job authority

M02 的 state-ownership lesson在这里必须继续成立。`DashboardSnapshot` 只是从 current TaskForge state 生成的 read-time projection；它不能成为另一份独立可写的 job lifecycle truth。

Reference 使用 frozen dataclass 来强化这一点，但 frozen 本身不是 architecture proof。真正 contract 是：snapshot 可以从 authoritative job state 重建，renderer 只消费它，不通过 snapshot 反向修改 lifecycle。如果某个 candidate 为 dashboard 另建一个 independently mutable `status_by_job` registry，并允许它和 TaskForge job state 分叉，那就是 ownership regression，即使 JSON 输出暂时看起来正确。

这也说明“多一份 data structure”不等于“多一份 authority”。Projection 与 authoritative state 的区别由 write semantics 和 recovery/update rule决定，不由对象数量决定。

## 5. 第一顶 hat：只改变结构，并证明 text behavior 没变

Reference 第一阶段新增 `DashboardCounts`、`DashboardJob`、`DashboardSnapshot` 和 `_build_snapshot(title)`，然后把原 `render_dashboard()` 改成：

```text
build normalized snapshot
        ↓
text-specific formatting
```

此时没有 JSON function。Structural phase 的 claim 很窄：internal representation / fact construction 被重排，但当前 observable text behavior 保持。

在临时 reference copy 中，这一阶段重新运行 behavior probe，三个 fingerprint 仍是：

```text
empty   eaadf634b7104332
queued  ec17ac5523b4b8bd
mixed   1181854b1e08cc1c
```

Core tests 仍是 `6 passed`。因此 evidence 支持的是“在当前 probe/test observation surface 上没有发现 text behavior drift”，而不是形式证明所有可能 input 都等价。

这个 qualifier 很重要。Current probe 没有单独 partition command 中含 `|`、newline、Unicode title、超大 job list 等情况。Reference 仍认为当前 structural move 可接受，是因为它只搬运这些 facts，没有新增 parser、escaping 或 normalization。如果 refactor 开始改变字符串处理，这些 partition 的优先级就会立刻上升。

## 6. 第二顶 hat：现在才增加 JSON behavior

Structural checkpoint 通过以后，reference 才新增 `render_dashboard_json(...)`：

```text
_build_snapshot
    ↓
JSON-specific mapping
    ↓
json.dumps
```

JSON renderer 使用 raw status / exit code，而不复用 text-only `status_text`。Reference focused evidence 使用两个高信息量 cases：empty state 覆盖 zero schema；mixed lifecycle 一次构造 succeeded、failed、cancelled、running、queued，随后同时检查 title、counts、order、raw statuses、exit codes 和 commands。

加入 JSON behavior 后，旧 text behavior probe 再跑一次，fingerprint 仍未改变；full pytest 在临时 reference copy 中变为 `8 passed`：原有 6 个 core tests + 2 个 JSON tests。

“只有两个新 tests”不是偷懒的证明，也不是固定最佳数量。Mixed fixture 恰好把多个相关 contract 压进一个信息密度很高的 state；如果 JSON 逻辑以后出现更独立的 branches 或 parsing，test partitions 也应该继续扩展。M03 的原则仍然成立：test count 本身没有 authority，重要的是 oracle 能区分哪些 plausible-wrong implementations。

## 7. 为什么 `status_text` 是一个有信息量的 abstraction test

一个诱人的“复用”方式是让 snapshot 保存 `succeeded(0)`，这样 text renderer 很方便。但 JSON contract 需要的是：

```json
{
  "status": "succeeded",
  "exit_code": 0
}
```

如果 JSON 必须 parse `succeeded(0)`，说明 shared representation 已经把 presentation decision 偷带进 semantic fact layer。

反过来，把 `status` 与 `exit_code` 保留为 raw facts，让 text renderer 自己生成 `succeeded(0)`，JSON renderer 自己构造 fields，两个 outputs 才真正共享“知道什么”，而不是强行共享“怎么画出来”。

这类判断比“有没有抽出 helper”更重要。Duplicated syntax 可以很便宜；duplicated policy knowledge 才更可能导致 future change amplification。

## 8. Change topology 是这次 reference 的核心产物

Reference 实际采用的 sequence 可以压成：

```text
S0 starter
  ↓ observe current behavior
S1 behavior inventory + existing probe
  ↓ structural-only change
S2 normalized dashboard facts + migrate text renderer
  ↓ verify old output unchanged
S3 add JSON renderer + JSON tests
  ↓ verify old text behavior again
```

如果是实际 repo，这可以是两个 PR，也可以是一个 PR 里的两个清楚 commits。Git 形式不是规范；关键是 reviewer 能分别建立两个 engineering arguments：

- structural step 为什么有 evidence 支持 behavior preservation；
- JSON step 的新 behavior contract 是否正确。

如果把 `refactor dashboard + add JSON + rename title + change ordering + fix M04 KeyError` 混成一个 change，即使最终 tests 全绿，reviewer 也要同时判断多个互不相同的 proof obligations。尤其 `KeyError -> ApiError` 即使是更好的 public boundary，也仍然改变 caller-visible API/error semantics，不能因为它“顺便更合理”就藏进 pure structural step。Change 很可能不是因为 LOC 多而难 review，而是因为 semantic claims 被堆在一起。

这就是本课程所说的 semantic checkpoint / change topology：它们是 course synthesis，用来描述一个 coherent、runnable、single-purpose、可独立 evidence 和 failure-localization 的中间状态，不是某个 source 规定的固定 Git workflow。

## 9. Existing probe 足够时，不需要为了仪式先新增一堆 tests

“重构前必须先写新测试”不是本章规则。Current M05 已有 behavior probe，刚好覆盖这次最关键的 text compatibility surface，所以 reference 直接使用它作为 structural evidence。

如果现有 evidence 太弱，当然可能先补 characterization / golden / differential checks。真正问题不是“有没有先写新 pytest”，而是：**你有没有足够 evidence 支撑当前 behavior-preserving claim？**

Differential/golden evidence 也有边界。它可以证明 old/new 在选定 inputs 和 environment 下 observation 相同，却不能证明旧行为本身是产品应该保留的正确 contract；更不能因为 candidate 输出变了，就顺手 update golden 让 drift 重新变绿。Observed compatibility surface 与 desired behavior仍需要 separate authority。

M06 会故意拿走 M05 的舒服前提：当 behavior 本身不完整、环境依赖多、feedback weak 时，先建立可修改的 evidence surface会变成主问题。

## 10. Reference 选择 preparatory path，但 direct path 仍可能在另一个 context 胜出

为什么 reference 最后选择先隔离 facts？因为当前 JSON request 已经存在，而且两个 renderers 明显要共享 lifecycle/count interpretation；这使 structural preparation 能直接降低紧邻 feature 的 knowledge duplication 和 review burden。

如果产品改成“JSON 只给一次 debug，用完即删”，reference 甚至会倾向接受 direct path。复制十几行可能比三个 dataclass 更经济。Likewise，如果为了这个 feature 先整理整个 service/state/API，或者建立 generic renderer framework，那就已经离开“为当前 pressure 铺路”的最小集合。

这也是 `First / After / Later / Never` 作为 timing framework 的意义：structural cleanup 什么时候做取决于当前 change pressure、reversibility、review cost 和 future likelihood，不是“tidy first”口号。

`Design it twice` 也不要求真的维护两套 production implementation。M05 只要求认真构造 direct path 和 preparatory path，再比较 knowledge duplication、change amplification、evidence cost、rollback/reversal 和 abstraction cost。Reference path 是一次选择，不是课程答案结构。

## 11. Exploration patch 可以丢，已经获得的 information 不必丢

Agent 很容易第一次就生成“复制 JSON logic”的完整 patch。这个探索有时非常有价值，因为它会快速暴露到底重复了哪些 knowledge。

问题是，发现 shared policy 后不一定要继续在已经混乱的 diff 上层层 patch。若 exploration 同时混入 structure 和 behavior，review mental model 已经很差，可以保留 design notes，丢弃 exploratory code，从 clean base 按 staged topology 重做。

这不是浪费已经生成的代码，而是在区分两个产物：**code 可以丢，关于 system/change surface 的 information 可以保留。** Agent implementation bandwidth 很便宜时，sunk-cost attachment 更没有必要成为 change-design constraint。

## 12. Agent task 和 review 应围绕 change sequence，而不只描述 final tree

只给 Agent “重构 dashboard 并加 JSON”时，它很容易一次性生成最终结构；那个 tree 甚至可能不错，但 reviewer 会失去“哪部分本该 behavior-preserving、哪部分是新 behavior、drift 从哪一步开始”的 evidence chain。

更强的 delegation 会要求：先恢复 behavior inventory；比较 direct / preparatory candidates；如果选择 structural path，先提交 structural-only checkpoint并重放旧 probe；只有 checkpoint 通过后才加入 JSON；最后再做 full regression 与 independent review。

Review 也不应只检查“有没有 abstraction”。至少要问：

- structural diff 是否真的没有改变 text behavior；
- shared model 集中的是 knowledge 还是只是 syntax；
- snapshot 是否只是 projection，而没有形成第二 authority；
- JSON feature 是否被明确隔离在 behavior step；
- evidence 是否匹配每个 checkpoint，而不是只给最终 full-green；
- 是否出现与当前 feature 无关的 cleanup、formatting churn 或 speculative framework。

对于更大的 production repo，还要沿 public symbol/API、config、serialization、metrics/logging、performance、threading/async timing、external call sites 扩大 observable surface。TaskForge fixture 很小，不能把它的 probe scope误当成所有 refactor 的充分 evidence。

## 13. Instructor judgment

M05 reference 的重点不是“dataclass 是最佳实践”，而是下面这条可审查 change argument：

> 先观察旧 behavior，识别两个 outputs 真正共享的 semantic facts；如果 structural preparation 对当前 feature 有直接价值，就把它做成独立 behavior-preserving checkpoint，验证旧 output；随后再增加 JSON behavior，并再次验证旧 behavior没有 drift。

一个不同内部结构也完全可以是高质量答案，只要它能准确说明 shared knowledge、给 direct alternative 公平 trade-off、让 structural phase 有独立 preservation evidence、不把 projection 升级成 authority、不为了未来建立万能 framework，并让 feature behavior 在 separate proof obligation 中进入系统。

如果学生最后只能说“我把 dashboard 抽成了三个 dataclass，所以更 clean”，本 Lab 没完成。真正需要带走的是：**refactoring 的价值不来自结构看起来更漂亮，而来自我们能把一次变化拆成更小、更可推理、更可验证、可回退的 engineering propositions。**
