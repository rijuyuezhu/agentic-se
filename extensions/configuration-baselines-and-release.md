# Configuration、Baseline 与 Release：你到底在改变哪一个系统

假设一次上线出了问题。你把代码回滚到上一个 commit，服务重新启动，CI 也重新变绿。事故却没有结束：数据库已经执行了 migration，运行时 config 仍然是新版本，worker image 没有一起回滚，前端引用了新生成的 schema client，一部分节点还在跑旧 binary。

“代码已经回滚”在这里没有充分描述系统状态。

Software Configuration Management（SCM）研究的核心并不是 Git 命令，而是一个更基本的问题：**一个会持续变化的软件产品由哪些受控 artifact 构成，我们怎样知道某一时刻真正生效的是哪一组，以及改变它们需要什么 authority 和 evidence？**

M08/M13 已经把 compatibility、migration 和 rollback 的核心语义放进主线；只有当 build/release/deployment 由多种可独立变化的 artifact 共同决定时，才需要这层更完整的 configuration identity，因此它适合作为按需旁支而不是新的必修模块。

## 1. Version control 只是 SCM 的一个机制

Git 很重要，但它主要擅长回答 source tree 的版本历史。真实 release 往往还包含：

- source code；
- dependency lock / vendored component；
- build toolchain；
- generated code；
- database schema / migration state；
- runtime configuration；
- infrastructure definition；
- container/package/binary；
- model or data artifact；
- feature flag state；
- API/schema definition；
- deployment manifest。

如果这些东西能独立变化，那么只说“我们部署了 commit `abc123`”通常还不能唯一确定用户运行的系统。

SCM 的价值就在于把这种模糊性变成可管理的 **configuration identity**。

## 2. Configuration Item：什么东西值得被单独控制

传统术语 `configuration item`（CI）容易让人想到繁琐流程。其实它可以很朴素：**如果某个 artifact 的版本变化会改变产品行为、可构建性、可部署性、兼容性或审计结论，它就值得考虑作为受控配置的一部分。**

不是所有文件都需要独立审批。粒度取决于风险和组织方式。

例如一个 Python CLI 的 release 可能只需要：

```text
source commit
+ lockfile
+ build workflow revision
+ package artifact digest
```

一个有 durable state 的分布式服务则可能还必须记录：

```text
server binary set
+ worker binary set
+ schema version
+ migration phase
+ feature flags
+ deployment configuration
```

关键不是形式，而是让工程师能回答：

> 我现在声称“版本 X 正常”，这个 X 到底指哪一组东西？

## 3. Baseline：给 reasoning 一个共同起点

Baseline 可以理解为一个**已经被识别并获得相应认可的参考配置**。它的重要性不是“冻结后谁都不能动”，而是从这一刻起，change 有了明确的 before/after。

这和 M10 做 code review 时要求知道 base commit 是同一件事，只是范围更广。

假设两个 reviewer 都在审“release 2.4 的兼容性”：

- reviewer A 用 schema v4 + worker v2；
- reviewer B 用 schema v5 + worker v1；
- issue 作者脑中又默认 feature flag 已开启。

即使三个人都认真，他们也没有在讨论同一个系统。

一个 baseline 应让关键配置足够明确，使后续 claim 可复现。例如：

```text
release candidate RC3
source:        18f02ab
server image:  sha256:...
worker image:  sha256:...
schema phase:  expand-v2 / old+new readers
flags:         new_claim_protocol=off
```

小项目完全不需要如此正式；一个 tag + lockfile + reproducible build 可能就够。Baseline 的严格程度应由 consequence 决定。

## 4. “Current” 是一个危险的词

文档里最容易腐烂的词之一是“当前版本”。

在 rolling deployment、mobile client、browser cache、remote worker、database migration 中，系统经常没有唯一 current version，而是一个 **version set**。

M08 已经训练 mixed-version compatibility；SCM 补充的视角是：

> 这个共存窗口本身也应该是一个可识别、可报告、可审计的 configuration state。

例如：

```text
Phase A: old server + old/new reader compatible schema
Phase B: old/new server + new schema, new feature disabled
Phase C: all writers fenced, feature enabled
Phase D: compatibility window retired
```

如果 rollout plan 只写“先部署新版本，然后 migrate”，它没有给 reviewer 足够的信息判断每个阶段到底允许哪些组合。

## 5. Change control：不是所有 change 都需要委员会

传统 SCM 常让人联想到 Change Control Board。这个组织形式不是本课程要保留的核心。

真正要保留的是两个问题：

1. **什么变化需要谁的 authority？**
2. **改变一个 baseline 后，哪些 evidence 必须重新建立？**

例如：

- typo fix 可能只需要普通 code review；
- public API semantics 需要 API owner；
- schema compatibility window 需要 storage/service owner；
- SLO 改动不能由实现 Agent 顺手修改；
- production secret rotation 可能需要受控运维流程。

所以 change control 更像 **authority boundary + evidence invalidation rule**，不等于“审批越多越工程化”。

## 6. Status accounting：我们现在到底在哪里

一个长期 migration 最危险的状态是：每个人都知道“正在迁移”，但没人能准确说出哪些节点完成了哪一步。

Configuration status accounting 这个传统名字听起来像行政报表，工程本质却很实用：

> 对重要配置和变更，能够回答它们的 identity、状态、历史和已批准关系。

对现代系统，这可能表现为：

- deployment inventory；
- migration state table；
- artifact registry metadata；
- SBOM/provenance；
- release manifest；
- feature flag audit history；
- CI attestation；
- Git tag + signed artifact digest。

你不一定需要一套独立“SCM 系统”。很多项目已有工具能提供这些事实，缺的是把它们当作 correctness evidence 使用。

## 7. Release 是一组 artifact 的组合，不只是一个 tag

Release engineering 常被简化为“打 tag、build、publish”。但如果 release 的行为依赖多个独立 artifact，那么 release identity 应能把它们重新关联起来。

一个有用的问题是：

> 六个月后出现 bug，我们能否重建当时用户拿到的组合，而不是只 checkout 当时 source？

如果不能，就很难做可靠 regression reproduction，也很难判断 vulnerability/compatibility 影响范围。

这也是 provenance 的意义：不是为了给 artifact 多加 metadata，而是回答**它从什么 source、dependency、toolchain 和过程产生，最后进入了哪个 release**。

NIST 的 SSDF 甚至把 release component provenance 明确放入 secure software development practice。安全只是它的一个重要用途；对普通 debugging 和 rollback，provenance 同样有价值。

## 8. Reproducible 不等于 bit-for-bit，但必须知道你要复现什么

“可复现 build”有多个强度层次。

最低限度，你应该能够在合理条件下回答：

- 使用哪个 source；
- 使用哪些依赖；
- 需要什么构建环境；
- 产生哪个 artifact；
- 如何验证 artifact identity。

更严格的项目可能要求 deterministic/bit-for-bit reproducibility，但这不是所有系统的默认要求。

不要为了 SCM 纯洁性给一个小型内部工具增加复杂供应链。和本课程其他地方一样，**严格度由 failure consequence 和 future investigation cost 支付。**

## 9. Rollback 不是“把所有东西恢复成旧版本”

M08/M13 已经说明 durable migration 的 rollback 经常不对称。SCM 可以把这个问题说得更精确。

假设 release 改变了：

```text
code C1 -> C2
schema S1 -> S2
written data D1 -> D2
external side effects E1 -> E2
```

回滚 code 只能直接改变 `C2 -> C1`。它不会自动把新数据变回旧表示，更无法撤销已经发生的外部 effect。

因此真正的 rollback plan 必须说明**哪些 configuration item 可逆、哪些状态只能 roll forward、哪些需要 compatibility window、哪些 consequence 根本不可逆**。

“有 Git revert”不是 rollback evidence。

## 10. Agent 让 artifact identity 更重要，而不是更不重要

Coding agent 可以在很短时间里：

- 修改 source；
- 更新 lockfile；
- regenerate client；
- 改 workflow；
- bump version；
- 生成 migration；
- publish preview artifact。

如果任务 contract 只说“实现并测试”，它可能给你一组局部自洽、但 provenance 和 release boundary 不清楚的变化。

因此给 Agent 的 change contract 可以显式说明：

- 哪些 configuration items 允许写；
- 哪些 generated artifact 必须由 canonical generator 产生；
- version bump / release / publish 是否被授权；
- baseline/base commit 是什么；
- evidence 要绑定哪个 artifact digest / schema phase；
- 不允许把“本地测试过”描述成“release 已验证”。

这不是额外 ceremony，而是在 implementation 变快以后保护**change identity**。

## 11. 一个最小 Configuration Review

对涉及 release、migration 或多 artifact 的 change，可以快速问：

1. 这次 change 实际改变了哪些受控 artifact？
2. 我们的 before baseline 是什么？reviewer 是否真的在同一 baseline 上 reasoning？
3. rollout 期间会出现哪些合法 version combinations？
4. 哪个 artifact/phase 决定 public behavior？
5. source、generated output、binary 和 deployment 是否可以追溯？
6. 哪一步需要额外 authority，而不是普通代码写权限？
7. rollback 能逆转哪些东西？哪些只能继续 migrate/repair？
8. 六个月后能否重建“当时到底发布了什么”？

如果一个系统很小，这八个问题可能五分钟就回答完。那正说明不需要复杂 SCM 流程。

## 12. 这篇旁支不教什么

这里没有要求建立 Change Control Board、填写固定表单、给每个文件编号，也没有把 Git branching strategy 当作软件工程定律。

真正应该保留的是：**software change 不是对一堆无名文件的编辑，而是从一个可识别 baseline 到另一个可识别 configuration 的受控迁移。**

这条思路会直接增强 M08 的 compatibility reasoning、M10 的 review、M12 的 evidence packet 和 M13 的 rollout/rollback judgment。

材料来源与取舍见 [`reading-notes/extensions-source-audit.md`](../reading-notes/extensions-source-audit.md)。
