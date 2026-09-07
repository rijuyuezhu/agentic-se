# Final Transfer Practicum — Click

这是一份最终迁移考核，不是新的教材模块。你面对的是 Pallets Click 的真实历史代码，而不是 TaskForge；题目不会给 writer map、authority map、must-preserve list、target architecture、建议修改文件或“应该找到哪类 bug”。

## 1. Frozen repository

- Upstream：Pallets Click
- License：BSD-3-Clause
- Frozen revision：

```text
333c28d79cd982990ee98eef61ec20ab1a4f38ba
```

用课程提供的 bootstrap 创建工作副本：

```bash
python practicum/final-transfer-click/bootstrap.py /path/to/click-final-transfer
cd /path/to/click-final-transfer
```

Bootstrap 只获取截至 frozen revision 的可达 Git history，校验 HEAD 后删除 upstream remote，再建立本地 `practicum-work` branch。**不要重新添加 upstream remote，不要 fetch 更新版本。** 这是为了保留真实 pre-change archaeology，同时避免未来真实修复泄露答案。

最小 baseline：

```bash
uv run --no-default-groups --group tests pytest -q
```

课程验证过的 frozen baseline 是：

```text
1915 passed, 24 skipped, 31000 deselected, 1 xfailed
```

具体 wall time 取决于机器和首次依赖下载；测试本身应是秒级，而不是本实验的主要难度。

## 2. 任务边界

先读 [`ISSUE.md`](ISSUE.md)。把它当成一个真实 maintainer request，不要假设：

- issue 一定合理；
- suggested implementation 一定可行；
- tests green 就能证明需求成立；
- 最终一定需要 production patch。

你可以读 frozen repo 里的代码、tests、docs 和**截至 frozen revision** 的 Git history。你可以运行任意本地 probe、临时实验和 test。

为了保持考核有效性，在第一次完整提交前：

- **不要搜索 web/GitHub 上 Click 在 frozen revision 之后发生了什么**；
- 不要添加/fetch upstream remote；
- 不要阅读任何 instructor-only Final Transfer Practicum material；
- 不要打开 `checkpoint/01-after-issue-review.md`，直到 Phase 1 的 first-pass artifacts 已冻结。

可以查 Python 标准库或通用工具文档；限制针对的是会直接泄露这个真实历史 change 答案的 Click 后续资料。

## 3. Agent 使用要求

必须实际使用至少一个 coding agent，但不规定产品或模型。Agent 可以帮助 reconnaissance、history search、probe design、implementation 或 review；**不能因为 Agent 给了结论就跳过独立 evidence。**

保留可以审查的交互 artifact，例如：

- 你给 Agent 的 task/context；
- Agent 的 plan / proposed change；
- 实际 patch；
- 它声称运行过的 commands/evidence；
- independent reviewer 的输入和输出；
- 你对 Agent/reviewer 的修正、拒绝和 escalation。

不要求、也不要提交模型的 private chain-of-thought。只保留正常可见的 prompt、response、plan、tool/evidence summary 等工程 artifact。

## 4. Phase 1 — 不实现，先判断 issue

先完成 [`DELIVERABLES.md`](DELIVERABLES.md) 的 A、B、C：

- A. Reconnaissance Record
- B. Issue Review
- C. first-pass Design Memo

你自己决定应该画什么、搜索什么、跑什么 probe。不要按课程章节顺序逐项套术语。

把 first-pass artifacts 放到工作副本的 `submission/`，然后冻结：

```bash
git add submission/
git commit -m "practicum: freeze first-pass review"
```

这个 commit 的价值是保存**看 decision 之前你真正知道什么**，不是追求漂亮 Git history。

只有这一步完成后，才读：

```text
checkpoint/01-after-issue-review.md
```

该文件位于课程 repo，不在 Click worktree。读完以后，新增 `submission/issue-review-addendum.md`；不要回写 first-pass 让 hindsight 消失。

## 5. Phase 2 — 收敛 change，并使用 Agent

根据 maintainer reply 更新 design judgment，并完成 D–F：

- D. Delegation / Agent Contract
- E. Candidate Change（只有现在仍 ready 才实现）
- F. Evidence Packet

Human-only decision 必须在 delegation artifact 中显式保留。你可以让 Agent 写 patch，但至少要自己独立检查：

- change scope；
- public/compatibility behavior；
- tests/oracle 来源；
- docs/release semantics；
- 有没有把 maintainer decision 偷换成更强 claim，或把 implementation suggestion 当成新的 authority。

至少重新运行 full minimal suite 和 `git diff --check`。若 candidate 修改了有独立 build/render contract 的 artifact（例如 Sphinx 文档），还要运行该仓库对应的 build/check；如果环境确实无法运行，要把它明确列为 evidence gap，不能让 pytest green 代替。若你认为还需要 targeted probe，自己决定并说明它究竟区分什么。

## 6. Phase 3 — Independent review

完成 G、H：

- G. Independent Review
- H. Human Adjudication

第一轮 reviewer **不要先读 implementation Agent 的结论性 summary**。给 reviewer issue、maintainer reply、relevant baseline/context 和 candidate diff；让它自己恢复 claim/evidence。

随后逐条 adjudicate：finding 是否真实、是否 in scope、严重度、需要 contract change / implementation change / no change。不要机械接受 reviewer wording。

如果 rework，保存原 finding 和修复后 evidence，而不是把失败历史擦掉。

## 7. Phase 4 — Release judgment 与 retrospective

完成 I、J：

- I. Rollout / Migration / Reversal Judgment
- J. Retrospective

这里不要求真的发布 Click。你需要说明当前 library change 在什么 evidence 下可进入 release、哪些 consumer behavior 仍需兼容、如果 rollback package version 能恢复什么、已经发生的 downstream migration/documentation adoption 又不一定能“回滚”什么。

最后回答：在这个陌生 repo 里，哪些课程方法真的帮助了你，哪些 checklist 没有帮助，哪些错误如果没有自己建立 model 就很容易被 Agent 合理地猜错。

完整格式与评分见 [`DELIVERABLES.md`](DELIVERABLES.md)。
