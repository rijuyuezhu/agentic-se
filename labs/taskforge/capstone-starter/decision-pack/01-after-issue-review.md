# Human product decision after issue review

> 只有在你已经独立完成第一次 `ISSUE.md` review 后再读本文件。

原 feature request 把若干无法同时满足的 guarantee 混在了一起。产品 / 系统 authority 现作如下决策。

## D1 — 不承诺 arbitrary command exactly-once

TaskForge 无法仅靠自己的 SQLite state 判断一个超时 worker 是否已经对外部世界完成了副作用。

因此新的 contract 是：

- TaskForge 可以保证 **current-attempt state fencing**：stale attempt 的 heartbeat / finish 不得覆盖 current attempt；
- 对启用自动 recovery 的 job，执行语义是 **at-least-once**；
- 如果某个 command 的重复外部副作用不可接受，调用者必须使用 effect-owner 提供的 idempotency / fencing，或者不得启用自动 recovery；
- 不得在文档、API 或测试中重新声称 arbitrary shell command exactly-once。

## D2 — Legacy submission 保持 manual recovery

现有 `submit_job(command)`：

- response shape 不变；
- 创建的 job 默认 `recovery_policy=manual`；
- 不会因为 lease timeout 被自动 requeue。

允许新增一个明确的 v2 submission surface，使 caller 显式选择：

```text
recovery_policy = manual | automatic_at_least_once
```

## D3 — Worker protocol 引入 attempt identity

新 worker claim 必须得到 monotonic attempt token。

新 heartbeat / finish 必须携带：

```text
job_id
attempt
worker_id
```

只有 current running attempt 可以 renew / finish。

旧 v1 worker payload (`job_id + exit_code`) 在 migration window 继续支持，但只能完成 legacy attempt；它不能完成一个已经进入 v2 attempt protocol 的 row。

## D4 — 先修现有 claim race

在 mixed v1/v2 rollout 之前，现有 v1 claim handler 必须先做到单一原子 claim decision，而不能继续允许两个 worker 都成功返回同一个 queued job。

这个修复不得改变 v1 claim response shape。

## D5 — Expand → protocol migration → activation

Rollout 至少分为：

1. **Expand**：在线增加 nullable/default-safe columns；旧 binary 对 expanded schema 仍可运行。自动 recovery 关闭。
2. **Protocol migration**：部署支持 v1 + v2 worker protocol 的 server；逐步升级 worker。自动 recovery 仍关闭。
3. **Activation gate**：只有可观测地满足以下条件才允许打开 automatic requeue：
   - legacy worker count = 0；
   - running legacy attempt count = 0；
   - new-server rollback target 已被重新评估；
   - stale-attempt rejection evidence 已通过。
4. **Contract**：在另一个独立 change 中考虑移除 v1 protocol；本 capstone 不要求删除。

## D6 — Rollback guarantee 被收窄

原 issue 的“任意时刻都能回滚老 server binary”不成立。

- 在 **Expand-only** 阶段，必须保留 old binary 对 expanded schema 的读写兼容性，因此 binary rollback 是目标。
- 一旦 v2 attempt semantics 已被实际使用，回滚到不知道 attempt fencing 的老 server 可能重新接受 stale completion，因此不再承诺简单 binary rollback。
- Activation 之后的恢复策略是 **roll forward / disable recovery / restore from an explicitly planned state backup**，而不是盲目启动旧 binary。

## D7 — 不增加新基础设施作为默认答案

本 capstone 仍保持单 SQLite database，不要求 message broker / distributed database / orchestration platform。

如果你的设计认为必须增加基础设施，必须先证明当前 requirements 无法在现有 deployment model 下满足，并单独获得 architecture authority。
