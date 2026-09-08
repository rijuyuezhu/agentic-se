---
id: lab-M10
type: lab
visibility: student
related: [M10]
---
# Lab 10 — 独立 Review 一个“9 passed”的 Agent PR

> 这不是“老师藏了几个 bug，学生负责猜答案”的实验。
>
> 你的任务是：**在 author summary、tests 和 CI 都很可信时，仍然独立恢复 change contract、找到 semantic risk，并用可复现 evidence 决定是否 merge。**

## 1. 实验材料与纪律

工作目录：

```text
labs/taskforge/
```

M10 review case：

```text
review-cases/m10/reviewer-brief.md
review-cases/m10/agent-pr-description.md
review-cases/m10/agent-pr.patch
```

replay tool：

```text
tools/m10_review_case.py
```

你不需要把 candidate patch 应用到自己的工作区；runner 会在 temporary copy 中 apply。

本实验有四条硬规则：

1. **先读 reviewer brief，再读 author description/patch。**
2. **先写 first-pass review，再运行 reviewer reveal probes。**
3. **不因为 CI green 自动 approve，也不因为“这是教学坏 PR”自动 request changes。**
4. **introduced regression、pre-existing issue、historical exception 和 out-of-scope cleanup 必须分开。**

课程维护侧保留 instructor-only reference，但它不进入 student-facing build，也不提供给 first-pass review。学生先完成自己的 finding/evidence，再由课程组织者决定是否提供 reference 做课后校准。

## 2. Phase A — 先把 issue/change contract 写出来

只读：

```text
review-cases/m10/reviewer-brief.md
```

然后停下，不看 author conclusion，不看 patch。写一页 change model：

```text
Change type:
Primary claim:
Semantic scope:
Behavior intentionally unchanged:
Explicit non-goals:
Likely high-risk surfaces:
```

至少回答：

- 这是 behavior change、refactor、architecture change，还是 mixture？
- “localize authority”与“preserve behavior”是不是同一个 proof obligation？
- brief 是否要求 complete mutation-capability isolation？
- M07 historical fault-injection artifact 是否属于 normal product-path rule？
- remote protocol / DB / queue 是否属于本轮？

一个合格模型应该意识到：这是一份 architecture-enabling structural refactor，它至少同时承担：

```text
normal transition/direct-state locality improves
+
existing behavior stays stable
```

不要把前者成功当作后者的证据。

## 3. Phase B — 从 starter 恢复 baseline，而不是从 patch 猜 contract

检查：

```text
src/taskforge/service.py
src/taskforge/worker.py
src/taskforge/metrics.py
src/taskforge/legacy_audit.py
src/taskforge/public_api.py
src/taskforge/snapshot.py
src/taskforge/concurrent_claim.py
```

并回看 M02/M03/M04/M06/M08/M09 与本 change 直接相关的已建立 contract。

完成下表：

| Surface | Current behavior / invariant | Source of truth | 本 PR 必须保持？ |
|---|---|---|---|
| normal transition/direct-state locality | ? | code / M09 | target property |
| list ordering | ? | code / M03 | ? |
| claim ordering | ? | code / M03 | ? |
| unknown cancel | ? | current boundary / M04 | ? |
| snapshot format/order | ? | code / M08 | ? |
| legacy audit output/order | ? | code / M06 | ? |
| mutable `Job` observation | ? | code / M02 | introduced by candidate? |
| `concurrent_claim.py` | ? | M07 / reviewer brief | normal-path blocker? |

特别写清：

```text
current behavior
!=
desired future behavior
```

如果一个 structural CL 声称 behavior-preserving，那么“当前设计不漂亮”不是偷偷改变它的许可证。

同时，M02 已知 `service.get()` 返回 authoritative mutable `Job`。本实验要求你识别这条 authority risk，但不能自动把它升级成本 PR blocker；先判断 candidate 是否引入/扩大了它，以及 brief 是否要求本轮关闭它。

## 4. Phase C — 先确认作者 evidence 真的是绿的

运行：

```bash
cd labs/taskforge
PYTHONPATH=src uv run --with pytest --no-project \
  python tools/m10_review_case.py
```

预期：

```text
[AUTHOR CI]
......... [100%]
author-supplied CI is green
```

记录两列：

| This evidence proves | This evidence does not prove |
|---|---|
| ? | ? |

右列至少三项。

不要写抽象的“tests 可能不全”。要结合这次 change 的 risk：ordering、error semantics、authority scope、snapshot/audit downstream consequence 等。

## 5. Phase D — 读 author description，把 prose 变成可验证 proposition

现在读：

```text
review-cases/m10/agent-pr-description.md
```

逐条列 claim：

```text
C1 ...
C2 ...
C3 ...
```

对每条标记：

```text
baseline-supported
needs proof
contradicts another claim
out of requested scope
```

至少检查：

```text
“preserve all current behavior”
```

与：

```text
“unknown cancel returns False”
```

是否能同时成立。

也检查：

```text
“single owner of lifecycle state”
```

到底是 precise evidence-backed property，还是作者把 M09 的 locality direction 写成了更强的 complete authority claim。

## 6. Phase E — 找 semantic center，不按文件顺序 mechanical review

先看 patch stat：

```bash
git apply --stat review-cases/m10/agent-pr.patch
```

把 changed files 分成：

```text
semantic center
routing/adaptation
observable-output consumer
new evidence
```

然后优先读：

```text
job_authority.py
tests/test_job_authority.py
```

对 semantic operations 建表：

| Operation | Old semantic source | Candidate behavior | Same semantics? | Evidence |
|---|---|---|---:|---|
| submit | ? | ? | ? | ? |
| get | ? | ? | ? | ? |
| list | ? | ? | ? | ? |
| cancel | ? | ? | ? | ? |
| claim | ? | ? | ? | ? |
| finish | ? | ? | ? | ? |
| metrics/read | ? | ? | ? | ? |

寻找的不是“代码看起来像不像”，而是新 policy：

```text
ordering
error translation
default
state/capability exposure
failure behavior
```

## 7. Phase F — Review tests as code

Candidate 新 tests 不是自动可信的 oracle。逐条回答：

1. 这个 test 声明了什么 contract？
2. oracle 来源是 reviewer brief / prior contract，还是 candidate implementation 自己？
3. 输入 partition 是否能碰到真正 risk boundary？
4. 坏实现下它真的会 fail 吗？

特别比较：

```text
1 job
2 jobs
9 jobs
10 jobs
12 jobs
```

为什么这些不是等价 partition？

如果实现采用 identifier sort，先通过 reasoning 寻找：

```text
identifier order diverges from semantic creation order
```

的最小边界，不要先 fuzz 一千个 case。

## 8. Phase G — 从 contract 构造最小反例

对每个可疑点先写：

```text
Contract:
Candidate assumption:
Smallest discriminating case:
Expected:
Likely candidate result:
Downstream consequence:
```

至少尝试构造：

- ordering/FIFO 的 discriminating counterexample；
- unknown-ID behavior 的 baseline/candidate 对比。

对于 ordering，一旦找到 root cause，继续沿 dataflow 检查：

```text
list_jobs
  ├─ public API/readers
  ├─ dashboard
  ├─ snapshot
  └─ legacy audit
```

不要把一个 root cause 的多个 consequence 机械写成多个 blocker。

## 9. Phase H — 单独评估 architecture claim 与 scope

现在回答三个问题：

```text
A. authority-localization direction 是否合理？
B. implementation 是否保留 requested semantics？
C. change packaging 是否 coherent？
```

这三项可以给出不同 verdict。

同时明确分类下面两项：

### Mutable `Job`

如果 candidate `JobAuthority.get()` / `claim_next()` 仍返回 live mutable `Job`：

- 它是否证明 complete mutation-capability isolation？
- 这是 candidate 新引入的 regression，还是 M02 baseline residual？
- 本 brief 是否要求你强制加入 `JobView` / defensive copy？

### M07 historical exception

`concurrent_claim.py` 继续 direct state mutation：

- 是否违反 reviewer brief？
- 它是 production normal-path evidence 还是 historical fault-injection artifact？

禁止写 whole-repo grep 式 blocker，除非你能证明 architecture scope 真的是 whole repo。

## 10. Phase I — Historical probes 也要做 lifetime 判断

一个合法 authority refactor 会改变 source topology。

如果旧 M09 topology inventory 或 M03 source-site mutation harness 失败，先分类：

```text
long-lived contract evidence
historical characterization
source-topology harness
superseded fitness rule
```

回答：

> 这个 red signal 是 product regression，还是它所描述的历史 seam 被当前合法 change supersede？

同时指出：哪些 M05/M06/M08 observable/compatibility evidence 仍应继续作为 regression gate。

## 11. Phase J — 在 reveal probe 前写 first-pass review

现在写正式 first-pass。**Risk-first 允许你先报告已经足以推翻当前 patch 的 finding，但它不是 sampling permission。** 如果 broad blocker 使剩余代码很可能被重写，可以先发 first-pass；若最终要 Approve，则仍必须完成自己承担的其余 human-written review scope，或明确说明 partial scope / specialist coverage。

格式可用：

```text
Decision: Approve / Request changes / Split / Need specialist review

Reviewed scope
- files/aspects actually reviewed
- deferred/partial scope and who must cover it, if any

Change model
- ...

Finding 1 — <Blocker / Medium / Nit + short title>
Location:
Contract:
Observation:
Consequence:
Evidence / minimal counterexample:
Required outcome:

Finding 2 — ...

Non-blocking / residual risks
- ...

Scope not reviewed
- ...
```

要求：

- severity 清楚；
- findings 按 root cause 聚合；
- 不用 personal preference 充 blocker；
- 不要求 current change 修所有 baseline defects；
- 不因为 CI green/author confidence 给结论；
- required outcome 主要写“什么必须变真”，不强制唯一实现。

保存这一版。之后不允许假装它是在 reveal probe 之前想到的。

## 12. Phase K — 现在才运行 reviewer probes

运行：

```bash
PYTHONPATH=src uv run --with pytest --no-project \
  python tools/m10_review_case.py --reviewer-probes
```

对每条 output 标记：

```text
ALREADY FOUND
NEW FINDING
SAME ROOT CAUSE AS EXISTING FINDING
NOT A BLOCKER
```

probe 当前会给出高信息量 symptoms，但不要按 output ID 数量决定 comment 数量。

如果 reveal 让你发现 first-pass blind spot，诚实记录。这个实验评估的是 independent reasoning，不是“最后答案和 instructor 一样”。

## 13. Phase L — 重写 final review：聚合 root cause，校准 severity

再次检查：

- list/FIFO/snapshot/audit 是否来自同一个 mechanism？
- error change 是否与 structural scope 冲突？
- `JobAuthority` direction 本身是否被 regression 错误否定？
- mutable `Job` 是否只是 residual M02 issue？
- M07 historical artifact 是否被正确排除？
- 在 semantic center 之外，自己承担的其余 human-written implementation 是否已 review？
- maintainability / readability / understandability / complexity 是否有 material code-health regression，而不是被统统降成 nit？

Severity 以课程 canonical 三档为准：`Blocker / Medium / Nit`。`Important / Should fix` 可以作为 Medium 的 wording alias；`Optional / FYI` 是 comment intent，不是额外 severity。

- **Blocker**：material claim 不成立或存在 merge 前必须关闭的不可接受风险；
- **Medium**：有具体 evidence/material consequence，通常应在本 CL 修，但单独未必否定整份 change；
- **Nit**：non-mandatory polish / minor clarity，不应冒充 code-health blocker。

一个高质量 final review 可以很短，但必须有：

```text
precise decision
root-cause findings
material consequences
reproduction/evidence
required outcome
non-blocking scope notes
```

## 14. Phase M — 设计 corrected change topology，而不是直接替作者 coding

提出更可审查的 sequence。例如：

```text
CL 1 — authority localization only
  preserve submission/FIFO/error semantics
  route normal product access through the new seam
  add architecture fitness evidence
  add >9-job ordering/FIFO regression evidence

CL 2 — optional API error redesign
  only if product actually wants it
  define public behavior and compatibility explicitly

CL 3 — future remote worker
  protocol / retry / auth / timeout / idempotency / deployment
```

对每个 CL 写：

```text
engineering claim
proof obligation
rollback boundary
why independently reviewable
```

不要因为 reviewer 发现 blocker 就自动规定一份完整 replacement implementation。

## 15. Phase N — 写 corrected PR description

不实现修复，只写一份更可 review 的 description：

```text
Problem
Scope
Behavior intentionally changed
Behavior intentionally unchanged
Design/authority decision
Evidence
Known residual risks
Out of scope
Follow-up
```

禁止只写：

```text
Risk: Low
```

必须把“为什么 risk bounded”展开成可验证 claim。

## 16. Phase O — 设计 re-review plan

假设 author 发来新 patch set 并说：

```text
fixed all comments
```

写出你会重新检查什么。至少包含：

```text
inspect patch-set delta
rerun blocker reproductions
review changed tests/oracles
verify no new behavior scope
confirm authority-localization goal still achieved
re-evaluate residual risk
```

注意 stale approval：resolved thread 不等于 engineering proposition 已成立。

## 17. Optional bridge to M11 — 用 Agent 帮 review，但不交出 acceptance authority

这部分是可选练习，不计 M10 核心分。给 Agent 两次任务：

第一次：

```text
Review this PR. Is it good to merge?
```

第二次给 engineering review contract：

```text
Act as an independent reviewer.
Treat author summary and green CI as claims, not facts.
Reconstruct the requested change from reviewer-brief.md and the baseline.
List behavior that must remain unchanged.
Review tests as code and identify copied assumptions.
Trace semantic changes through scheduler/public/snapshot/audit surfaces.
Separate introduced regressions from baseline issues and historical probes.
Report root-cause findings with severity, consequence, evidence, and required outcome.
```

比较两次结果，但不要把 Agent verdict 当课程答案。如何进一步设计 agent context、task decomposition、parallel reviewer/implementer 与 merge conflict 属于 M11。

## 18. Deliverables

提交一个 `m10-review.md`，至少包含：

### A. Change model

- change type；
- requested claim；
- scope/non-goals；
- baseline contracts；
- architecture intent。

### B. Evidence audit

- author CI 实际证明什么；
- author tests 的 oracle/partition 弱点；
- 哪些 evidence 仍需补。

### C. First-pass review

必须是在 reveal probe 前保存的版本。

### D. Probe comparison

明确标出 independent finding 与 reveal-added finding。

### E. Final review

root-cause 聚合、severity、evidence、required outcome、non-blocking residual。

### F. Corrected change topology

每个 CL 的 claim / proof obligation / rollback boundary。

### G. Re-review plan

说明新 patch set 到来后如何重新建立 acceptance argument。

Optional：Agent vague-prompt vs engineering-contract comparison。

## 19. Grading

总分 100：

| Dimension | 分值 | 优秀表现 |
|---|---:|---|
| Independent system reconstruction | 20 | 不依赖 author summary；恢复正确 baseline、M07 exception、M02 residual |
| Finding quality | 25 | 找到 material semantic findings；有最小反例；按 root cause 聚合；Blocker/Medium/Nit evidence 标准清楚 |
| Evidence review | 20 | 不被 9 passed 锚定；能审 tests/oracles；targeted probe 对应 uncertainty |
| Scope discipline | 15 | regression / baseline issue / historical harness / cleanup 分类正确；risk-first 不变成 sampling；partial/specialist scope 明确 |
| Change engineering | 10 | structural / behavioral / future remote work 拆分清楚 |
| Decision & re-review quality | 10 | severity 明确；code health 不被降成 nits；知道何时 approve/request/split/specialist；patch-set re-review 有证据 |

以下不会自动加分：

```text
写很多 comments
找很多 formatting nit
随机 fuzz 很久
把个人 pattern preference 写成 blocker
要求本 PR 清掉所有旧债
因为“instructor case 肯定有 bug”而 Request Changes
```

## 20. 完成标准

完成这个 Lab 后，你看到：

```text
✅ CI passed
✅ Agent summary says behavior-preserving
✅ diff looks cleaner
```

第一反应应该是：

```text
What is the engineering claim?
What must stay true?
Where is the semantic center?
What would falsify the claim?
Did the submitted evidence actually try that?
What risk remains after it passes?
```

如果你能在 reveal probe 之前回答这些问题，并把结果写成别人可复现的 review，M10 的目标就达到了。
