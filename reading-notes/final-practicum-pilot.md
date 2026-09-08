---
id: practicum-pilot
type: reference
visibility: internal
related: [final-practicum, practicum-click]
---
# Final Transfer Practicum — Empirical Pilot

> 本记录对应 issue #3 的 practicum validation。它只说明这一次 frozen Click task / harness 是否真的产生了课程想测量的 engineering pressure，**不是通用 Agent benchmark，也不用于推出 productivity 数字或模型排名**。
>
> Pilot 日期：2026-09-08。所有 Click 工作副本都固定在 `333c28d79cd982990ee98eef61ec20ab1a4f38ba`，不访问 post-freeze Git history；student-facing repo 与 pilot repo 都删除 upstream remote。

## 1. 先验证 harness，而不是先测 Agent

正式 bootstrap 从空目录 fetch frozen SHA，校验 HEAD，删除 upstream remote，再建立本地 `practicum-work` branch。实际重放结果：

```text
Frozen HEAD: 333c28d79cd982990ee98eef61ec20ab1a4f38ba
Reachable pre-freeze commits: 3296
Remote removed: yes
Work branch: practicum-work
```

最小 baseline：

```bash
uv run --no-default-groups --group tests pytest -q
```

结果：

```text
1915 passed, 24 skipped, 31000 deselected, 1 xfailed
```

因此 frozen-history isolation 没有破坏正常测试，同时保留了足够真实历史做 archaeology。

Closure self-review 后，bootstrap 又补了一处 setup hardening：如果机器没有全局 Git `user.name/user.email`，只在 disposable practicum repo 内写 placeholder identity，避免 Phase 1 的 checkpoint commit 因环境配置失败。随后用空 `HOME` 从零重放 `bootstrap.py --verify-tests`：仍为 `1915 passed`，`HEAD/all` 均只有 3296 条 pre-freeze commits、remote 数量为 0；first-pass commit 能成功创建，parent 精确等于 frozen SHA。这个 fallback 不覆盖已有 Git identity。

一个早期错误方案也在这里被排除：普通 `git worktree` 虽然 checkout 到旧 commit，却共享 parent repo 的未来 refs，Agent 可以通过 `git log --all` 看到后续真实修复。正式 bootstrap 不使用这种 topology。

## 2. Task-shape blind check

在完整 implementation pilot 前，先把原始 stakeholder request 给一个 read-only Agent，只允许读 frozen code/tests/docs/pre-HEAD history，不允许 web，也不给 instructor reference。它自然追到了：

- `CliRunner.isolated_filesystem()` 的 process-global `os.chdir()`；
- `CliRunner.isolation()` 对 stdio / env 等 interpreter-global state 的修改；
- repo 里已有的 thread-related testing history；
- “runner-local filesystem root”不能透明改变 arbitrary callback 中普通 `open()` / `Path()` 的语义。

这说明核心 conflict 不依赖 instructor secret clue。一个合理的 system-model pass 本身就能暴露它。

这次 pilot 的 first-pass / authority 顺序也有独立时间证据：blind output `/tmp/issue3-click-pilot.txt` 在 00:53 完成；bounded implementation plan 在 00:56 才生成；candidate summary 在 01:05；summary-blind independent review 在 01:15。Blind output 本身已经包含 A/B/C 对应的 reconnaissance、issue judgment、decision-needed 与多条 response family；后续 bounded task、candidate/evidence、review/adjudication 分别覆盖 D–H，rollout reference 与本记录的 transfer retrospective 覆盖 I/J。

Pilot 当时**没有机械复刻**学生版 `submission/` 的目录名和“first-pass commit”这个 choreography，因此这里不声称做过不存在的提交历史。它实际验证的是更重要的 semantic boundary：first-pass 结论先产生并留存，maintainer authority 后到，后续实现/review 没有回写那份 blind judgment。学生版要求 commit，是把这个已验证的 hindsight boundary 固化成更容易审计的机制。

## 3. Lightweight A/C contrast

为了检查课程倡导的 workflow 是否在这个 task 上产生可观察差异，本轮只做一个**小型 A/C 对照**，没有补 Condition B。两边从同一 frozen revision 开始，均禁止 web / future history；目的不是比较模型，而是检查 task 是否能区分“直接实现 literal request”和“先恢复约束、再 bounded delegation”。

### Condition A — 直接给 vague stakeholder request

Implementation Agent 收到的核心要求是：

- same-process concurrent `CliRunner` filesystem isolation；
- 每个 runner 有自己的 filesystem root；
- 现有 API/source-compatible；
- existing commands/tests 不改写；
- 不用 subprocess；
- suggested direction 是不要再改 process cwd，而做 runner-local relative path routing。

Prompt 明确允许 Agent 在认为不可安全实现时停止并解释；它没有选择 escalation，而是进入 implementation。

在 instructor-side independent check 冻结 candidate 时，diff 为：

```text
3 files changed, 855 insertions(+), 82 deletions(-)
```

其中 `src/click/testing.py` 增加约 784 行 machinery，主要做法是：

- 新增 `CliRunner(filesystem_root=...)`；
- 用 context-local state 表示 virtual cwd；
- monkey-patch `builtins.open`、`io.open`、大量 `os.*` 与 `os.path.*`；
- 在 `invoke()` / `isolated_filesystem()` 期间安装和恢复这些 process-level monkey patches；
- 新增自己的 parallel runner tests。

Agent 最终自述：

```text
1919 passed, 24 skipped, 31000 deselected, 1 xfailed
ruff: passed
mypy: passed
```

我对冻结 candidate 独立重跑 full minimal suite，也得到：

```text
1919 passed, 24 skipped, 31000 deselected, 1 xfailed in 4.63s
```

所以这个 candidate 不是“明显连测试都跑不过”的 straw man。

### 3.1 一个 green suite 没排除的 deterministic counterexample

对同一冻结 candidate，instructor-side independent check 构造一个现有 command 完全可能做的行为：command 内启动普通 Python subprocess，让子进程用相对路径写 `child.txt`。

父 runner 使用：

```python
CliRunner(filesystem_root=root)
```

实际观察：

```text
exit_code=0
virtual_root_child_exists=False
real_cwd_child_exists=True
COUNTEREXAMPLE: subprocess relative filesystem access escapes runner filesystem_root
```

原因很直接：candidate 只改写当前 Python interpreter 中的 Python-level filesystem functions；child process 继承的仍是真实 process cwd。它没有、也不能凭 runner-local field 自动重写任意现有 command 的所有外部 filesystem effects。

这条 counterexample 直接击穿了 literal request 中“existing commands 不改写即可得到隔离”的强保证。与此同时，原 `CliRunner.isolation()` 的 stdio / environment global mutation 仍然存在，所以 filesystem-focused green tests 也不能升级成 whole-runner same-process concurrency guarantee。

这里得到的教学信号是：

> **test count 增加、full suite green、Agent 自述完成，仍然可能与真实 change claim 不一致。**

### Condition C — human reconnaissance + bounded authority

第二个工作副本先由 human/instructor-side reconnaissance 固定 conflict，再给 implementation Agent 一个明确 maintainer decision：

- 8.x 不承诺 same-process concurrent `CliRunner` safety；
- 保持现有 API source-compatible；
- deprecate `CliRunner.isolated_filesystem()`；
- compatibility window 内保留原 non-concurrent behavior；
- docs 明确 process-global/thread-safety boundary；
- 新 tests 优先 caller/test-framework-owned temp dir；
- Click 自己的 local tests 可迁移；
- 不授权 lock、VFS、subprocess runner、新 public FS API 或 unrelated cleanup。

Implementation Agent 的 candidate：

```text
11 files changed, 229 insertions(+), 190 deletions(-)
```

production semantic change很窄：`isolated_filesystem()` 在进入时发出 `DeprecationWarning`；原 `mkdtemp -> os.chdir -> yield -> restore -> cleanup` 仍保留。其余主要是 docs、upgrade/changelog 和 internal test migration。

Agent 自己运行：

```text
focused pytest: 19 passed
full minimal suite: 1915 passed, 24 skipped, 31000 deselected, 1 xfailed
git diff --check: PASS
```

它的 final summary 也明确保留 residual risk：这次 change **没有**让 `CliRunner` thread-safe。

## 4. Independent review

第一轮 reviewer 被明确禁止读取 implementation Agent 的 plan / conclusion summary，只能读：

- frozen repo 与 pre-freeze history；
- maintainer-approved contract；
- current working-tree diff；
- 自己选择的 read-only probes。

最终 verdict：

```text
APPROVE
```

Reviewer 独立确认：

- helper signature/source compatibility 未变；
- warning 在实际调用 deprecated context manager 时触发；
- `stacklevel=3` 的独立 probe 把 warning 定位到 caller line；
- helper body 的 cwd/temp-dir/cleanup semantics 保持；
- repo 内只剩两处 intentional legacy helper usage，并显式断言 warning；
- testing docs / changelog / upgrade guide 对 deprecation 和 same-process concurrency limitation 一致；
- `git diff --check` 通过。

Reviewer 没有在自己的 raw environment 里安装 pytest，因此没有把 implementation Agent 的“full suite green”当作自己已经复现的事实；full suite 由 instructor-side 独立 run 负责确认。

### 4.1 Reviewer nit 的 human adjudication

Reviewer 还指出一条 non-blocking finding：部分 internal test 从 relative spelling（例如 `.`、`xxx`）迁移成 absolute `tmp_path` 后，对 relative-path behavior 的 evidence 略弱。

Adjudication：

| Finding | Real? | In scope? | Severity | Decision | Reasoning |
|---|---:|---:|---|---|---|
| 一些 test migration 弱化了 relative-path spelling 的直接 evidence | 是 | 是 | Low | 接受 finding；本 pilot 不挡 merge，但保留为 review criterion | deprecation 不等于允许降低旧 oracle fidelity；但这些 case 的主要被测行为仍由原 assertions 覆盖，且 change 不依赖“消灭所有 helper occurrence”作为 acceptance metric |

这个 finding 不应被扩张成“所有迁移都必须保留相对路径”。更一般的规则是：**先说清原 test 证明什么，再判断改写是否改变 oracle。** Instructor reference 已把“机械把所有 test 改成 absolute path”列为 plausible wrong migration；student rubric 也不以 grep occurrence 数量评分。

## 5. Pilot 暴露出的真实 evidence gap：pytest 不验证文档 build

Bounded implementation 修改了多份 Sphinx/MyST 文档，但 implementation Agent 的 evidence contract 只跑了 pytest 和 `git diff --check`。这些证据不能证明 MyST directive/reference 可以被 Sphinx 正确解析。

Instructor 因此补跑：

```bash
uv run --no-default-groups --group docs \
  sphinx-build -E -W -b dirhtml docs /tmp/click-final-practicum-docs
```

结果：

```text
build succeeded.
```

这不是 candidate bug，但属于**evidence packet 不完整**。因此 pilot 后 student materials 做了实际修订：

- `README.md` Phase 2 现在要求：若 candidate 修改了有独立 build/render contract 的 artifact，要运行对应 build/check；若环境无法运行，必须显式记录 evidence gap；
- `DELIVERABLES.md` 的 Evidence Packet 同样增加这个 conditional requirement。

这样避免把某个 Click-specific command机械写成所有 practicum 的固定 checklist，同时保留“evidence 必须跟随实际 changed artifact”的一般原则。

### 5.1 Closure self-review 又发现了一类 measurement leak

Pilot 完成后的人工 closure review 没有只检查 implementation correctness，还重新从“学生第一次打开材料时能看到什么”做了一次 dependency sweep。这个 sweep 找到几处会污染 first-pass measurement 的前置提示：

- student `README.md` 在 checkpoint 之前的可见说明里直接使用了 `deprecated` / `thread-safe` 对照；
- `DELIVERABLES.md` 的 rollout wording 提前出现 `deprecation` 与 `warning suppression`；
- 顶层 `README.md` 的课程状态直接链接 candidate audit 与 empirical pilot，而两份 instructor-side record 都包含 conflict、checkpoint direction 和 counterexample。

这些内容即使不等于完整标准答案，也会把“应该往哪个 design family 想”提前告诉学生，因此不能以“学生被要求不要看答案”为理由保留。Closure self-review 已做三类修订：

- student-facing wording 改回 generic `maintainer decision` / compatibility / release language；
- student task 不再报 instructor reference 的具体文件路径；
- 顶层学生导航只链接 practicum 入口，不再链接 instructor validation record。

这轮修订说明 Final Transfer Practicum 的 dependency order 不只存在于讲义叙事里：**assessment material 本身也必须维护 evidence-before-authority 的顺序。** 网站未来仍需在 build/export 层真正隔离 instructor material；当前修订解决的是内容和导航层的提前泄漏，不把它冒充访问控制。

## 6. 为什么没有把 Condition A 的失败做成 hidden test

Subprocess counterexample 不放进 student starter 作为 secret gate。原因是 Final Transfer Practicum 要测的是：学生能否从真实 system model 设计高信息量 evidence，而不是能否碰巧触发 instructor 预埋 test。

Instructor reference 可以保留这条 probe，评分时也接受其它能证明同一事实的 evidence，例如：

- unrelated thread 观察 process cwd；
- third-party/C-extension relative file access；
- stdio/env overlap 的 deterministic interleaving；
- 能精确说明 transparent VFS mechanism coverage hole 的其它 counterexample。

只要 reasoning 与 evidence 指向真实 contract gap，就不要求复刻 instructor probe。

## 7. 从这一次 pilot 可以、不能推出什么

这次 pilot 支持的窄结论：

1. frozen Click repo 的 setup/history 足够真实且可控；
2. initial issue 确实会诱发 plausible implementation，而不是一眼即可机械拒绝；
3. repo 自身有足够 evidence 让 first-pass reviewer 在不知道未来答案时质疑 literal request；
4. vague implementation 可以做到 full suite green，却仍被独立 counterexample 击穿；
5. human issue review + bounded maintainer authority 在这次 sample 中显著缩小了 patch/claim surface，并留下更可审查的 compatibility argument；
6. independent review 仍能提出 implementation Agent 没主动强调的 test-fidelity concern；
7. pilot 真的暴露了一个课程材料缺口（docs build evidence），而 student task 已据此修改。

不能推出：

- 某模型普遍更适合软件工程；
- bounded prompt 一定更快；
- 这里的 churn 数量能转换成通用 productivity metric；
- deprecation 是所有同类问题的唯一答案；
- reference candidate 是学生必须复制的实现。

## 8. Issue #3 acceptance closure

本次 pilot 完成后，issue #3 的关键 acceptance chain 已闭环：

- 多 candidate 真实 audit：见 [`final-practicum-candidate-audit.md`](final-practicum-candidate-audit.md)；
- frozen revision / license / setup / baseline 已记录并重放；
- student task 明显不同于 TaskForge，且不泄露 authority map / must-preserve list / target design；
- flawed stakeholder request 有真实 ambiguity/overclaim，但 system modeling 可以自然发现，不是寻宝题；
- A–J deliverables 与 reasoning-heavy rubric 已落地；
- deterministic high-information counterexample 已实际运行；
- instructor reference 明确保留多个 reasonable first-pass family，不把 patch 当标准答案；
- 完整 bounded Agent implementation + independent review 已实际 pilot；
- vague direct-request 对照产生了 green-but-wrong candidate，验证了 task 的区分力；
- 根据真实 pilot 补了 docs/build evidence requirement；
- 顶层课程导航明确把它标为 **Final Transfer Practicum，而不是 M14**。

因此从内容与 empirical validation 角度，issue #3 可以进入 PR review；后续网站对 instructor material 的真正 visibility/build exclusion 仍由 content information architecture issue 负责，而不是在 #3 内用 CSS 假装解决。
