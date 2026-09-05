# Lab 10 — Review 一个“9 tests green”但不该直接 merge 的 Agent PR

> 本实验不是找 instructor 藏了几个彩蛋。
>
> 你的目标是练：**在 author summary 和 CI 都显得可信时，怎样独立重建 change model，并用 contract-driven evidence 决定是否 approve。**

---

# 0. 实验材料

TaskForge 目录：

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

你**不需要**把 candidate patch 应用到自己的工作区。

runner 会在 temporary copy 中 apply。

---

# 1. 实验规则

## Rule 1 — 先独立建模，再读 author conclusion

先读：

```text
reviewer-brief.md
```

然后恢复 baseline contract。

不要先读 instructor analysis。

---

## Rule 2 — CI green 不是答案

你会看到 candidate：

```text
9 passed
```

你不能因此 approve。

但也不能因为“这是故意的教学 case”就默认一定有 blocker。

必须拿出工程证据。

---

## Rule 3 — 不把所有旧债都塞进当前 PR

TaskForge baseline 还有很多旧教学缺陷。

例如你可能记得 M02/M04 里的 representation / error issues。

本实验要求区分：

```text
introduced regression
necessary prerequisite
pre-existing issue
out-of-scope cleanup
```

---

## Rule 4 — 不以 comment 数量计分

一个准确 root-cause blocker 可以比 20 个 nit 得分高得多。

---

## Rule 5 — Reviewer probes 要晚于自己的 reasoning

只有在你已经写出第一版 review 后，才运行：

```bash
PYTHONPATH=src uv run --with pytest --no-project \
  python tools/m10_review_case.py --reviewer-probes
```

否则会把本实验变成“解释答案”。

---

# 2. Step 1 — 读取 Reviewer Brief

先读：

```text
review-cases/m10/reviewer-brief.md
```

然后**不要打开 candidate patch**，先写：

```text
change type:
primary claim:
intended semantic scope:
explicit non-goals:
likely high-risk surfaces:
```

至少判断：

```text
这是 refactor？behavior change？architecture change？
还是 mixture？
```

一个好的答案应该意识到：

```text
architecture-enabling structural refactor
```

也有多个 proof obligations：

```text
authority actually localizes
+
existing behavior remains stable
```

---

# 3. Step 2 — 建立 Baseline Review Sheet

在读 patch 前，回到当前 TaskForge，恢复与这次 change 有关的事实。

至少检查：

```text
src/taskforge/service.py
src/taskforge/worker.py
src/taskforge/metrics.py
src/taskforge/legacy_audit.py
src/taskforge/public_api.py
src/taskforge/snapshot.py
src/taskforge/concurrent_claim.py
```

并参考前面 lab 的已声明 contract。

写一个表：

| Surface | Current behavior / invariant | Source of truth | Must preserve in this PR? |
|---|---|---|---|
| lifecycle write ownership | ? | code / M09 | ? |
| list ordering | ? | M03 | ? |
| scheduling ordering | ? | M03 | ? |
| unknown-ID behavior | ? | current boundary / M04 | ? |
| snapshot format | ? | M08 | ? |
| audit output | ? | M06 characterization | ? |
| M07 fault injection | ? | reviewer brief | ? |

注意：

```text
current behavior
```

和：

```text
desired long-term behavior
```

不是同一列。

如果这个 PR 声称 behavior-preserving，哪怕当前行为“不漂亮”，它也不能悄悄改变。

---

# 4. Step 3 — 先看 Author CI

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

记录：

```text
What does this evidence actually prove?
What does it not prove?
```

至少写三条“它没有证明”的事情。

不要写抽象话：

```text
“tests 不可能证明一切”
```

而要针对本 change：

```text
没有覆盖哪个 ordering partition？
没有验证哪个 public behavior？
没有检查哪个 durable surface？
```

---

# 5. Step 4 — 阅读 Author/Agent Description

现在读：

```text
review-cases/m10/agent-pr-description.md
```

将每个 author claim 分类：

```text
SUPPORTED
NEEDS VERIFICATION
CONTRADICTS REQUEST
OUT OF SCOPE
```

示例表：

| Author claim | Classification | Why? | Evidence needed |
|---|---|---|---|
| lifecycle authority centralized | ? | ? | ? |
| all current behavior preserved | ? | ? | ? |
| stable ordering is harmless | ? | ? | ? |
| unknown cancel normalization is low risk | ? | ? | ? |
| no public API behavior change | ? | ? | ? |
| later RPC can wrap authority | ? | ? | ? |

这一步的关键：

> **不要让 description 的措辞替你完成 reasoning。**

---

# 6. Step 5 — 阅读 Diffstat，再找 Semantic Center

先看 patch 的文件列表和大致规模：

```bash
git apply --stat review-cases/m10/agent-pr.patch
```

不要立刻逐行从第一文件读到最后。

先回答：

```text
Which file contains the new semantic authority?
Which files are mostly routing changes?
Which tests express new assumptions?
```

把文件分成：

```text
semantic center
call-site routing
observable-output consumer
new evidence
```

---

# 7. Step 6 — 先 Review 新 Tests

本 case 很适合先读：

```text
tests/test_job_authority.py
```

问：

### 7.1 这些 tests 分别声明了什么 contract？

不要只写 test function name。

### 7.2 哪些 test 只是重复实现的新 assumption？

### 7.3 input partition 是否太窄？

特别考虑：

```text
1 job
2 jobs
9 jobs
10 jobs
12 jobs
```

为什么这些可能不是等价 partition？

### 7.4 测试有没有把“作者新定义的行为”直接变成 oracle？

如果有，它是否有外部 contract 支撑？

---

# 8. Step 7 — Review Semantic Center

阅读 candidate 的：

```text
job_authority.py
```

逐个 semantic operation 写表：

| Operation | Old semantic source | New implementation | Same behavior? | Evidence |
|---|---|---|---:|---|
| submit | service | authority | ? | ? |
| get | service | authority | ? | ? |
| list | service | authority | ? | ? |
| cancel | service | authority | ? | ? |
| claim | worker | authority | ? | ? |
| finish | worker | authority | ? | ? |
| metrics | metrics | authority | ? | ? |

不要只检查代码“看起来一样”。

寻找：

```text
new policy
new ordering
new error translation
new state exposure
new default
```

这些都是 refactor 最容易偷偷带入的 behavior changes。

---

# 9. Step 8 — 从 Contract 构造反例

如果你怀疑某条 behavior 被改变：

先写：

```text
Contract:
Candidate implementation assumption:
Smallest discriminating counterexample:
Expected:
Candidate likely output:
```

例如一个 generic 结构：

```text
Contract: preserve creation order
Implementation assumption: sort by an identifier
Counterexample: identifier ordering diverges from creation ordering
```

不要直接 fuzz 1000 个 case。

先通过 reasoning 找 boundary。

---

# 10. Step 9 — 检查 Downstream Consequence

如果一个 helper 改了 ordering，不要只停在 helper。

沿 dataflow 看：

```text
list_jobs
  ├─ public API
  ├─ dashboard
  ├─ snapshot
  └─ legacy audit
```

问：

```text
一个 internal-looking change 是否穿过长期 contract surface？
```

这一步直接调用 M09。

---

# 11. Step 10 — 检查 Out-of-Scope Behavior Change

refactor 中最危险的一种 comment：

```text
“顺手让 error handling 更友好”
```

你必须判断：

```text
这是 behavior preservation？
还是新的 API policy？
```

即使你认为新 policy 最终更合理，也要回答：

```text
为什么它应该/不应该在当前 PR 里？
```

---

# 12. Step 11 — 检查 Architecture Claim 本身

不要因为发现 behavior regression 就完全否定新 authority direction。

分别判断：

```text
A. architecture direction
B. implementation correctness
C. change packaging
```

一个 PR 完全可能是：

```text
A = good
B = flawed
C = flawed
```

高质量 review 应能表达这种区别。

例如：

```text
“集中 Job Authority 的方向符合 M09 decision；当前 patch 仍不能 merge，
因为它在结构迁移中混入了 ordering/error semantic changes。”
```

这比：

```text
“这个设计不好”
```

更精确。

---

# 13. Step 12 — 对 Historical Probe 做 Scope 判断

candidate 真的实现 authority refactor 后：

```text
tools/m09_architecture_probe.py
```

这个 baseline inventory 很可能不再满足旧 expected topology。

你需要判断：

```text
probe red = regression？
还是 probe 的 historical expectation 被合法 architecture change supersede？
```

不要形成：

```text
all old tests must stay byte-for-byte unchanged forever
```

M05/M08 要保持的是 contract evidence；
M09 inventory 本身是对某个版本 topology 的 characterization。

两者 lifetime 不同。

---

# 14. Step 13 — 写第一版 Review，暂时不要跑 Reveal Probe

提交一个 review memo：

```text
## Change model

## What I reviewed

## What I did not review

## Findings

### Blocker 1 — ...
Location:
Contract:
Observation:
Consequence:
Evidence / counterexample:
Required outcome:

### Blocker 2 — ...
...

### Non-blocking
...

## Overall decision
Approve / Request changes / Split / Need specialist review
```

要求：

- findings 按 severity 排序；
- 尽量按 root cause 聚合；
- 不写 personal-style blocker；
- 不要求修与 current change 无关的 baseline defect；
- conclusion 不能只写“CI 绿/红”。

---

# 15. Step 14 — 现在才运行 Reviewer Probes

```bash
PYTHONPATH=src uv run --with pytest --no-project \
  python tools/m10_review_case.py --reviewer-probes
```

这会在 temp tree 中：

1. apply candidate patch；
2. 再确认 author CI green；
3. 执行几组高信息量 counterexamples。

对每条 probe output，标记：

```text
ALREADY FOUND
NEW FINDING
SAME ROOT CAUSE AS EXISTING FINDING
NOT A BLOCKER
```

目标不是让 probe 替你 review。

目标是比较：

```text
human/Agent independent reasoning
vs
instructor-targeted evidence
```

---

# 16. Step 15 — Reviewer Probes 之后改写 Findings

如果 reveal 显示多个 symptoms 来自同一个 root cause，尝试合并。

例如：

```text
list ordering changed
scheduler ordering changed
snapshot ordering changed
```

未必需要三个 blocker。

可以是：

```text
Blocker — candidate replaces submission order with lexical ID order
```

然后列 consequences。

这更接近成熟 review。

---

# 17. Step 16 — 判断 New Tests 本身的问题

candidate 新增测试里如果存在：

```python
assert service.cancel("job-missing") is False
```

问：

```text
这个 assertion 是从 requested contract 推导的吗？
还是从 candidate implementation 推导的吗？
```

如果 request 明确说：

```text
behavior unchanged
```

而 baseline behavior 不是 `False`，那么：

```text
新 test 绿
```

实际上可能是 regression 的 evidence。

这是本章最重要的 lesson 之一：

> **A passing test can be evidence for the wrong contract.**

---

# 18. Step 17 — 设计 Corrected Change Topology

不要直接开始 coding。

先提出一个更好的 patch sequence。

例如：

```text
CL 1:
introduce in-process JobAuthority
preserve ordering/error semantics exactly
route service/worker/metrics/audit
add architecture fitness test

CL 2 (separate behavior change, only if desired):
redesign unknown-ID error semantics
update public contract + tests

CL 3 (future):
remote worker protocol
```

解释：

```text
为什么这样更容易 review？
为什么 rollback 更清楚？
每个 CL 的 proof obligation 是什么？
```

---

# 19. Step 18 — 写一个 Corrected PR Description

在不实现修复的前提下，写一版理想 description：

```text
Problem
Scope
Behavior changed
Behavior intentionally unchanged
Design decision
Evidence
Risks
Out of scope
Follow-up
```

要求避免：

```text
“low risk”
```

这种没有论证的结论。

应该说 risk 为什么 bounded。

---

# 20. Step 19 — Agent Reviewer 对比实验

先给 Agent 一个模糊 prompt：

```text
Review this PR. Is it good to merge?
```

记录它是否：

- 主要重复 author summary；
- 因 9 tests pass 而倾向 approve；
- comment 集中在命名/结构；
- 真正检查 ordering/error/compatibility；
- 区分 pre-existing issues。

然后给 Agent 一个 engineering review contract：

```text
Act as an independent reviewer.
Do not treat the author summary or green CI as facts.
Reconstruct the requested change from reviewer-brief.md and current baseline.
Classify the change type and list the behaviors that must remain unchanged.
Review tests as code and identify copied assumptions.
Trace changes through public API, scheduler, snapshot, and audit consumers.
Construct minimal counterexamples for ordering/error changes.
Separate introduced regressions from pre-existing issues and historical probes.
Report root-cause findings with severity, contract, consequence, evidence,
and required outcome. Do not prescribe implementation unless necessary.
```

比较两次输出。

---

# 21. Step 20 — Independent Re-review

假设 author 回复：

```text
“fixed all comments”
```

你不能只检查 comment thread 是否 resolved。

写出 re-review plan：

```text
1. inspect patch-set delta
2. rerun blocker reproductions
3. verify no new behavior scope
4. re-check tests changed to address root cause rather than expectation update
5. confirm architecture target still achieved
```

---

# 22. Deliverables

至少提交：

## A. Change model

包含：

```text
change type
claim
scope
contracts/invariants
architecture intent
```

## B. Evidence audit

对 author tests 和 CI 的实际证明能力做说明。

## C. First-pass review

必须在 reveal probe 前写。

## D. Probe comparison

说明哪些问题你自己找到，哪些由 probe 暴露。

## E. Final review

root-cause + severity 排序。

## F. Corrected change topology

说明应该怎样拆 change。

## G. Agent comparison

模糊 prompt vs engineering review contract。

---

# 23. Grading

总分 100。

## 23.1 Independent system reconstruction — 20

优秀：

- 不依赖 author summary；
- 恢复正确 baseline contracts；
- 明确 M07 historical exception；
- 知道 durable/public consumers。

---

## 23.2 Finding quality — 25

优秀：

- 能找到真正 semantic blocker；
- 有最小 counterexample；
- 按 root cause 聚合；
- 不把个人偏好当 blocker。

---

## 23.3 Evidence review — 20

优秀：

- 不被 9 passed 锚定；
- 能指出 candidate tests 的 weak partition / copied assumption；
- targeted probe 与 uncertainty 对应。

---

## 23.4 Scope discipline — 15

优秀：

- introduced regression / pre-existing issue 分开；
- historical probe scope 判断正确；
- 不产生无限 cleanup request。

---

## 23.5 Change engineering — 10

优秀：

- 能设计更好的 CL sequence；
- structural / behavioral / remote mechanism 分开；
- rollback/review boundary 清楚。

---

## 23.6 Agent orchestration — 10

优秀：

- Agent review 有 independent contract；
- 不信 self-summary；
- 需要 evidence；
- human 保持 acceptance authority。

---

# 24. 不加分的事情

以下不会因为做了就自动高分：

```text
写 30 个 comments
找到很多 formatting nit
跑很多随机 fuzz
说“最佳实践是 repository pattern”
把所有旧问题都要求修
因为 instructor case 肯定有 bug 而 request changes
```

---

# 25. 本实验真正训练的习惯

以后看到：

```text
✅ CI passed
✅ Agent summary: behavior-preserving
✅ diff looks cleaner
```

不要立刻产生：

```text
LGTM
```

先问：

```text
What is the engineering claim?
What must stay true?
Where is the semantic center?
What would falsify the claim?
Did the submitted evidence actually try that?
```

如果这五个问题已经成为自动反应，M10 的目的就达到了。
