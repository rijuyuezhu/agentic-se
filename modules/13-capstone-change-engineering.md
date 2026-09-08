---
id: M13
type: module
visibility: student
order: 13
---
# M13 — Capstone：让一次 Change 经得起现实世界

M13 不再引入新的 software-engineering principle。它把前面分开练过的 system model、contract、state ownership、testing、concurrency、migration、architecture、production evidence、review 与 Agent authority 放进同一个 change，检查这些判断能不能同时成立。

主案例仍然是 TaskForge，但不是前十二章那个逐步长大的 teaching baseline。Capstone 使用一个独立 starting point：[`../labs/taskforge/capstone-starter/`](../labs/taskforge/capstone-starter/)。它已经有旧 API 用户、SQLite schema v1、remote worker、background maintenance、历史 compatibility quirk、一个已知 race，以及一套全部通过却没有覆盖关键并发历史的 tests。你面对的不是“从零设计可靠 scheduler”，而是一个已经存在、已经被别人依赖的系统。

## 1. 六个绿测试之后，先别写 lease

先运行 starter 的 baseline：

```bash
cd labs/taskforge/capstone-starter
PYTHONPATH=src uv run --with pytest --no-project python -m pytest -q
PYTHONPATH=src uv run --with pytest --no-project \
  python tools/capstone_baseline_probe.py
```

当前 canonical baseline 是 `6 passed`。这六个 tests 覆盖 schema v1、legacy submit response、单 worker FIFO claim、legacy finish、maintenance scan 和 queued cancellation；它们都是真实 contract evidence，只是 evidence surface 很窄。

Deterministic probe 随后制造了一个更麻烦的 history：两个 v1 worker 先后观察到同一个 queued row，再各自执行 update，于是两个 caller 都收到 `job-1` 的 claim success。最终数据库里只有一个 `worker_id`，但这不能改写已经发生的两个 success receipts。M07 的 lesson 在这里重新出现：**final state 可以看起来唯一，history 仍然违法。**

第二个 probe 更直接击中 feature request。Worker A claim `job-1`；operator 用历史 emergency path 把 job requeue；worker B 再次 claim；这时 A 发送旧协议的 completion：

```json
{"job_id": "job-1", "exit_code": 0}
```

这个 payload 没有 worker identity，也没有任何能区分“旧执行”和“当前执行”的字段。Starter 会接受它。最后 row 甚至可能同时显示 `worker_id=worker-b` 与 `status=succeeded`，但 terminal transition 实际来自 A 的 stale completion。

这两条 evidence 已经足以否定一种常见工作方式：看到 feature request 说“加 30 秒 lease + sweeper”，就立即把任务交给 implementation Agent。系统当前连一个 queued job 的 single-winner claim history 都没有建立，旧 completion 也没有办法证明自己仍然属于 current execution。

## 2. Issue 真正卡住的不是 SQLite，而是 guarantee

Capstone issue 在 [`ISSUE.md`](../labs/taskforge/capstone-starter/ISSUE.md)。它同时要求 automatic recovery、arbitrary command exactly-once、旧 API 不变、old/new worker mixed rollout、旧 completion payload 不变、online schema migration，以及“rollout 任意时刻都可切回旧 server binary”。

先不要急着为这些要求挑实现。把它们和 failure history 放在一起：

```text
worker A executes an external effect
        ↓
TaskForge does not learn completion
        ↓
worker disappears / partition lasts past timeout
        ↓
automatic recovery executes the logical job again
```

TaskForge 自己的 SQLite 只知道它观察到了什么。它不知道 A 是否已经给信用卡扣款、发送邮件、写入远端对象，然后恰好在 completion record 到达之前失联。因此“timeout 后重新执行”与“任意外部副作用 exactly once”之间存在一个 knowledge/authority gap。

这里可以得到的是 **diagnosis**，不是新的 product contract：原 issue 不能按字面直接实现；TaskForge 当前没有足够 authority 证明 arbitrary external effects exactly once；旧 finish payload 也不能区分 stale execution。至于产品应该改成 at-least-once、禁用 retry、要求 effect-owner idempotency，还是采用其它约束，需要拥有 product/system authority 的人做决定。

这正是 M12 的直接下游：

> Implementation authority 不会因为 Agent 能写出 lease code，就自动升级成 product-guarantee authority。

高质量输出此时可以是 `STOP_AND_ESCALATE`。把 contradiction 说清楚，比在错误 specification 上高效编码更接近完成任务。

## 3. 先冻结自己的 Issue Review，再读取 authority decision

M13 故意把 human decision 放在 `decision-pack/01-after-issue-review.md`，并要求学生在第一次 issue review 完成前不要读它。目的不是制造考试仪式，而是保留一份独立 reasoning artifact：你究竟从 issue、代码和 baseline evidence 中发现了什么，而不是看过答案后觉得“我本来就会”。

第一次 review 至少区分四类东西：explicit requirements、existing contracts、assumptions、contradictions / unresolved decisions。尤其不要把现有 SQLite column、旧 worker payload 或 issue 中的“suggested implementation”自动升级成 domain contract。

冻结 first-pass review 后，再读取 human decision。当前 canonical decision 做了七件关键事：

- 撤回 arbitrary command exactly-once guarantee；**v2 attempt protocol** 才承诺 current-attempt state fencing，自动 recovery 的执行语义是 at-least-once。
- 保持 legacy `submit_job(command)` 的 response shape，并令旧 submission 默认 `recovery_policy=manual`；historical `operator_requeue()` 仍是 migration emergency path，但 legacy completion 没有 execution identity，因此这条 path 保留 stale-completion / duplicate-execution residual risk，不属于 v2 fencing guarantee。对 duplicate execution 不可接受、又没有 effect-owner protection 的 workload，它不能被当作安全 recovery。
- 允许新增显式 opt-in 的 `automatic_at_least_once` submission surface。
- 新 worker protocol 引入 monotonic attempt identity；heartbeat / finish 必须携带 `job_id + attempt + worker_id`。
- v1 completion 在 migration window 继续存在，但只能完成 legacy attempt；这只能隔离 legacy-vs-v2 domain，不能把两次 manual-requeue 前后的 legacy execution 区分开。
- mixed rollout 之前先修现有 v1-v1 claim race；进入 mixed window 后，所有 active claim entry point 还必须共享 queued-row single-winner invariant。Schema expand、protocol migration、recovery activation 继续分阶段。
- 收窄 rollback guarantee：Expand-only 阶段以 old-binary compatibility 为目标；一旦 v2 attempt semantics 已经写入系统状态，就不再承诺简单切回旧 server binary。

这组 decision 是本 Capstone 的 normative teaching contract。它不是从“lease 最佳实践”自然推导出的唯一设计，也不是 implementation Agent 可以自行发明的答案。

## 4. Human decision 之后，v2 attempt 才成为 current-execution authority

现在才有足够 authority 去解释 `attempt` 为什么重要。一个 logical job 可以被执行多次；TaskForge 需要区分 `job-7 / attempt 1` 与 `job-7 / attempt 2`，并决定哪一个 execution 仍有权提交 heartbeat 或 terminal transition。

因此 reference design 把 monotonic `attempt` 当作 fencing identity，而不是普通 retry counter。Conceptual acceptance condition可以写成：

```text
job.status == running
AND job.current_attempt == payload.attempt
AND job.current_worker == payload.worker_id
```

实现不要求照抄这个 predicate，也不要求使用特定 CAS primitive。关键 contract 是：旧 **v2** attempt 在新 v2 attempt 接管后不能再修改 current lifecycle state。

这也给 **v2 lease** 一个更精确的语义。Lease 不是证明“旧进程已经停止”；它是 TaskForge 在 v2 attempt protocol 中判断 current execution authority 的期限。Expiry 后，系统可以依据 recovery policy 撤销旧 v2 attempt 的 current authority，并允许新 attempt 接管；旧 v2 attempt 晚到的 heartbeat / finish 必须被 fence 掉。这段 contract 不倒推到没有 execution identity 的 legacy/manual v1 requeue path。

Reference schema 选择在 `jobs` 上增加 `attempt DEFAULT 0`、nullable `lease_expires_at`、`recovery_policy DEFAULT 'manual'`。这里的 `attempt=0` 是 migration sentinel，`manual` default 则保护 legacy submit semantics。另一种 schema，例如 separate attempts table，也完全可以成立；课程评分的是 authority 与 migration semantics，而不是结构与 reference 相同。

## 5. v2 state fencing 仍然没有拥有 external effect

现在可以重新回到最初的 exactly-once 冲突。假设 attempt 1 已经执行 `charge-card`，然后 lease expires；attempt 2 再执行一次。即使 attempt 1 的 late finish 被正确拒绝，外部世界仍可能已经发生两次扣款。

这不是 v2 attempt fencing 的失败。它说明两个 authority 不同：TaskForge 可以在 v2 protocol 内拥有 lifecycle state 的 current-attempt authority；支付系统、对象存储或其它 effect owner 才可能拥有外部副作用的 dedup / fencing semantics。

如果 effect owner 支持 logical-job idempotency key、attempt fencing token 或其它 transactional integration，可以设计更强的 workload-specific guarantee。但 TaskForge 的 arbitrary shell-command boundary 本身没有这些 knowledge。

因此 Capstone 必须保留一个反直觉的 **negative control**：构造两个 v2 execution attempts 都产生 external effect，同时证明 TaskForge 仍然正确拒绝 stale v2 state transition。这个 probe 通过，不表示实现坏了；它证明 acceptance statement 没有偷偷把 v2 state fencing 夸成 external exactly-once。

这条 distinction 也解释了为什么“把 claim/execute/finish 全放一个 SQLite transaction”或“换成 Kafka”都不能自动解决原 contradiction。SQLite transaction 不拥有远端副作用；broker 可以改变 delivery/coordination failure surface，但 lost acknowledgement 之后的 external effect ambiguity 仍然存在。反过来，简单地永远禁止 retry 也不符合 human decision 已授权的 opt-in automatic at-least-once recovery。

## 6. Migration 的难点是新旧语义共存

Schema migration 只是整个 migration 的第一段。当前 teaching contract 至少分成四个 phase。

**Expand。** 先增加 default-safe / nullable representation，使新 schema 可以存在而新 semantics 尚未激活。Reference 中 `attempt=0`、`lease_expires_at=NULL`、`recovery_policy=manual` 都承担 compatibility 含义。此时强 evidence 不是“SQL 看起来 additive”，而是真正 frozen v1 code 对 expanded DB 仍可读写 legacy contract。

**Protocol migration。** 部署同时理解 v1 与 v2 worker protocol 的 server，逐步升级 workers。Automatic requeue 仍关闭，因为“能够解释新协议”与“允许新 recovery semantics 改变 lifecycle”是两个不同 change。

**Activation。** 只有 observable gate 满足时才允许 automatic recovery，例如 `legacy_worker_count == 0`、`running_legacy_attempt_count == 0`、stale-attempt rejection evidence 已通过、post-activation rollback semantics 已被重新审查。Gate 是 system-state transition authority，不只是 deployment convenience。

**Later Contract。** 删除 v1 endpoint、attempt=0 compatibility 或旧 metrics 是另一个 change，不属于本 Capstone 必须完成的 scope。

这种 decomposition 不是因为 Expand→Contract 是万能模板。它只是当前 reader/writer/protocol dependency 下的一条可解释 topology。真正要保留的是：structure preparation、protocol coexistence 与 semantic activation 不要被混成一个不可审查的瞬间。

## 7. Rollback 不是“把旧 binary 放回去”

在 Expand-only 阶段，如果 frozen v1 binary 已经真实跑过 expanded schema，并且没有新语义 state 被旧 binary误解释，那么 old-binary rollback 可以是合理目标。

一旦 v2 attempt semantics 已经实际使用，问题发生变化。旧 server 不理解 attempt fencing；让它重新处理只有 `job_id + exit_code` 的 completion，可能再次接受当前 contract 明确要求拒绝的 stale transition。此时 schema 仍然 readable，并不能说明 system state 对旧 binary 仍然 semantically safe。

Instructor reference 曾在临时 solution copy 中记录两条直接证据：Expand-only 后 frozen v1 code 继续工作；v2 attempt active 后，frozen old server 会接受 unfenced finish。后者把“任意时刻都能切回旧 server”从模糊风险变成 runnable counterexample。这个结果只描述 reference path，不是所有 migration 的普遍定律。

因此 rollback plan 必须回答的是当前 **state** 能被哪个 binary/protocol 安全解释，而不只是“上一版镜像还在不在”。识别 point of no safe old-binary return 不是 migration 失败；没有识别却仍承诺随时 rollback 才是。

## 8. 先修旧 race，再扩大 lifecycle

Capstone starter 已经有 `SELECT candidate → later UPDATE` 的 v1 claim race。如果直接在这个 protocol 上叠 lease，新的 recovery feature 会继承旧的非法 history。

一个合理的早期 stage 是先把 v1-v1 claim 修成 single-winner，同时完全保留 v1 response shape。Reference 用 conditional update；`BEGIN IMMEDIATE` transaction 或其它等价原子 decision 也可以。但一旦 v2 claim entry point 加入 migration window，contract 不能退化成“每个 protocol 各自 single-winner”：同一个 queued row 面对所有同时 active 的 claim calls，最多一个 caller 获得 success receipt。至少要有 deterministic v1-v1 与 v1-v2 evidence；如果 v2 使用独立 claim path，也要说明/验证 v2-v2。这里要求的是 history invariant，不指定共享哪种 primitive。

这体现 M05 的 change topology：先把独立、已知的 protocol defect 收敛，再引入需要 migration 的新 semantics。不是因为“小 PR”本身更道德，而是这样每一步的 claim、evidence 与 rollback/reversal boundary 都更清楚。

对于整个 Capstone，一条合理但非唯一的 topology 是：characterize → fix v1 claim atomicity → expand schema → dual worker protocol/fencing → opt-in recovery submission → observability/gate → activate automatic recovery。删除 legacy protocol 留给 later change。

## 9. Design Memo 要把多个模型接在一起

Capstone 不接受一张 architecture diagram 代替 system model，也不接受只写“lease-based recovery”的 design memo。你需要把几个 view 接起来：responsibility / knowledge、state authority、runtime protocol、durable compatibility、failure / rollback。

在 TaskForge 中最关键的两个知识问题是：谁知道 current execution？谁知道 external effect 是否真正发生？如果答案不是同一个 authority，design memo 就不能用一个 SQLite field 把两者假装合并。

Compatibility matrix 也不能只问“新代码能不能读旧 DB”。至少要覆盖 old/new server、old/new worker、schema v1/v2、manual/automatic job，以及 v2 semantic state 已经出现后的 old-server rollback。Protocol syntax compatible 与 protocol semantics compatible 是两件事。

一份可审查的 memo 至少让读者找到：current model、desired contract、preserved contract、explicit non-guarantees、authority placement、state/interleaving model、compatibility matrix、rollout gates、rollback boundary 与 residual risk。它可以比较多个 plausible implementation shapes，但不能把 preference 写成 specification。

## 10. Agent 负责加速工程工作，不负责补齐 authority

M13 应该大量使用 Agent，因为 reconnaissance、call-path search、state-writer inventory、compatibility surface mapping、test audit 和 evidence collection 都是高价值的机械/探索工作。这些 read-heavy questions 也很适合并行。

真正进入 implementation 时，授权应按 stage 给出：goal、allowed write paths、preserved invariants、forbidden actions、evidence contract 与 stop/escalate conditions。Agent 如果发现 public response shape、migration gate ownership、external-effect guarantee 或 release authority 未被授予，正确行为仍然是停止并升级。

Independent Review Agent 不应只消费 implementation Agent 的 final summary。它需要从 issue、human decision、current code、candidate diff、raw tests/probes、migration artifacts 重新建立 change model，并主动寻找能推翻 author claim 的 counterexample。M12 已经区分 independent verification 与 independent review；M13 要把两者组合到真实 change acceptance 中，再由 human/policy authority 做最终 adjudication。

重点仍然不是 Agent 数量。一个 context 足够完整的 Agent 可以承担多个 bounded phase；不应该发生的是同一个 implementer narrative 同时成为 product decision、verification oracle、review conclusion 与 rollout authority。

## 11. Evidence 要证明 history、compatibility 与 limitation

`all tests passed` 不是 Capstone 的 acceptance statement。更有信息量的 evidence 至少覆盖这些 claim：

| Claim | 必须能看到的 evidence | 关键反例 / limitation |
|---|---|---|
| v1 API contract preserved | old-client characterization | unknown external clients 仍是 residual uncertainty |
| migration-window claim is single-winner | deterministic v1-v1 + v1-v2 history；独立 v2 path 再覆盖 v2-v2 | 各 protocol 单独绿不等于 coexistence history 合法 |
| schema Expand 对旧 binary 可用 | frozen v1 code 实际读写 expanded DB | schema readable 不等于 post-activation safe |
| stale v2 finish / heartbeat 被 fence | attempt1 → expiry → attempt2 → stale message | compatibility handler 不能绕过 v2 fencing |
| legacy jobs 仍是 manual | expired manual job 不被 sweeper requeue；记录 manual-requeue residual history | v1 manual requeue 不具 current-execution fencing guarantee |
| activation 有真实 gate | blocker state closes gate; clean state may open | inventory freshness 仍需运营保证 |
| external exactly-once 未被声称 | duplicate-effect negative control | 更强 guarantee 需要 effect-owner mechanism |
| rollback boundary 被识别 | expand-only old binary works；post-v2 old server counterexample | binary rollback != system rollback |

Concurrency test 应控制 interleaving，而不是靠 `sleep()` 赌 timing。Compatibility test 应尽量运行真实 frozen consumer/binary，而不是让新代码自己模拟 `legacy=True`。Negative control 的任务则是证明某个 **non-guarantee** 仍然真实存在，避免测试套件只会证明自己写下的 happy path。

Production evidence 同样要服务 decision。当前 teaching contract 至少需要能回答：还有多少 legacy workers？是否仍有 legacy running attempts？mixed v1/v2 claim 是否维持 single-winner？v2 stale finish/heartbeat 是否被拒绝？automatic requeue 是否只影响 opt-in jobs？migration window 中是否发生/使用了具有已知 stale-completion 风险的 legacy manual requeue？activation gate 是否满足？`job_id / attempt / worker_id` 很适合 diagnostic event correlation，但不应机械成为 aggregate metric 的高基数 label。

## 12. Review 与 rollout 是 change acceptance 的最后两道不同问题

Independent review 至少要重新检查 contract、authority、concurrency、migration、rollback、evidence 与 scope。典型 blocker 包括：实现已有 v2 attempt fencing，却把它写成所有 legacy/manual executions 都被 fenced；v1/v2 各自 claim test 都绿，却没有 cross-protocol single-winner evidence；README 又写回“exactly-once guaranteed”；或者 schema additive 就直接宣称 post-activation old-binary rollback safe。这些分别混淆 guarantee scope、coexistence history、external-effect authority 与 representation compatibility。

Reviewer 也不能把个人偏好升级成 blocker。Separate attempts table、transaction vs conditional update、文件名、是否使用 Postgres，都只有在能连到 contract、invariant、migration、failure 或 maintainability consequence 时才构成 finding。

Review closure 后仍不能把 rollout 写成“deploy succeeded”。Activation 前要检查 observable gate；activation 后要观察 stale rejection、requeue、manual-policy violations 等 contract-relevant signals。若 gate 或 production evidence 不满足，正确 action 可能是保持 recovery disabled、roll forward、停止进一步 migration，或执行事先定义的 state-aware recovery plan，而不是盲目启动旧 binary。

## 13. Reference 是一条可行 path，不是答案结构

Instructor reference 选择单 SQLite jobs table、conditional claim、monotonic attempt、nullable lease expiry、manual default、dual worker protocol 与 activation gate。它在临时 solution copy 中记录了 `14 passed`（6 个 baseline + 8 个 focused tests），并记录 frozen-v1 expand compatibility、external duplicate negative control 与 post-v2 old-server rollback counterexample；但那组 focused tests 只验证了 v1-v1 claim single-winner，没有覆盖当前 contract 明确要求的 v1-v2 concurrent arbitration。

这些结果的 provenance 由课程维护侧的 instructor-only M13 audit 与 instructor analysis 记录。Historical `14 passed` 只证明它实际覆盖的局部 claims，不是 clarified current contract 的完整 acceptance proof；reference solution 本身也不是 canonical starter 或学生 oracle。你可以采用 transaction、separate attempts table 或其它等价结构，只要自己的 contract、mixed-protocol ownership history、compatibility、v2 fencing、legacy residual risk、migration、rollback 与 production evidence 闭合。

Reference 也没有解决真实 scheduler 的所有问题：clock uncertainty、worker authentication、DB corruption recovery、多 server heavy contention、真实 worker inventory、external-effect idempotency、operator UI、schema downgrade tooling 与 v1 protocol removal 都仍在 scope 外。Capstone 的目标不是把这个教学系统伪装成 production-grade scheduler。

## 14. 最后的产物不是 Patch，而是 Change Record

完整 Capstone 最终要回答的不是“代码有没有写完”，而是“为什么这个 change 现在应该被接受，或者为什么它还不应该”。因此 patch 只是 change record 的一部分；issue review、system model、design memo、compatibility matrix、staged plan、Agent delegation、raw evidence、independent review、rollout/rollback plan、production evidence plan 与 retrospective 都是在为同一个 acceptance claim提供可审查上下文。

回顾整个过程，最值得区分的不是“哪些工作人做、哪些工作 AI 做”这种静态名单，而是 knowledge 与 authority 放在哪里。Agent 很适合做 repo reconnaissance、writer search、version matrix、focused implementation、race-test scaffolding 与 regression execution；产品 guarantee、compatibility break、residual-risk acceptance、merge/activation authority 则必须来自被明确授权的 decision owner。

课程从 M00 开始一直在训练同一种能力：change 发生时，先恢复 what is true，再确定 what should be true；把 knowledge/state 放到正确 owner；让 evidence 能否证自己的 claim；让新旧世界在 migration 中共存；让 Agent 加速 execution 而不吞掉 engineering authority。

课程最初给出的工作定义到这里仍然不需要改：

> **Software Engineering 是建立、表达和维护软件中的 boundaries、contracts、invariants 与 mental models，从而让复杂系统可以被人或 Agent 安全地持续修改。**

如果看到下一张 issue，你已经会自然追问：它真正改变哪条 contract？哪个 failure history 会击穿直觉？谁可以做这个决定？什么 evidence 会让我改变结论？新状态出现后哪些 rollback path 失效？reviewer 如何独立否证？上线后什么 signal 才说明这条 guarantee 正在成立？那么 M13 就完成了它的任务。
