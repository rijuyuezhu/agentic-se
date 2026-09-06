# M08 — Dependency、Compatibility 与 Migration：正确的新版本也可能让系统坏掉

M07 把时间带进了单次运行：两个操作会交错，失败可以落在两个 side effect 之间，timeout 之后 caller 可能不知道工作到底发生了没有。M08 再把时间轴拉长一层：**同一个系统的不同版本会在一段时间里同时存在，而且它们会读写同一批长期存在的数据。**

这一章不会从 Semantic Versioning 的规则开始，也不会先给一张 migration pattern 清单。我们先看 TaskForge 里一个更具体的问题：新代码本身没有明显 bug，测试也可以全绿，但旧 binary 一旦和它共享 durable snapshot，系统仍然会在 rollout 或 rollback 时失败。

## 1. 两个各自正确的程序，为什么放在一起就坏了

TaskForge 当前的 snapshot writer 在 `labs/taskforge/src/taskforge/snapshot.py` 中写出 `schema_version = 1`。每个 job 的命令是一个 flat field：

```json
{
  "schema_version": 1,
  "jobs": [
    {
      "id": "job-41",
      "command": "echo historical",
      "status": "succeeded",
      "exit_code": 0
    }
  ]
}
```

这个表示足够支撑现在的 shell job。为了给后续 task kinds 留空间，本章采用一个**教学用的 v2 target candidate**：把 `command` 放进带 `kind` 的 task object。

```json
{
  "schema_version": 2,
  "jobs": [
    {
      "id": "job-41",
      "task": {
        "kind": "shell",
        "command": "echo historical"
      },
      "status": "succeeded",
      "exit_code": 0
    }
  ]
}
```

这里先不要把这个 shape 当成“TaskForge 必然应该这样设计”。它只是本章为了研究 migration 而选择的 working scenario；真正产品也可能选择别的 representation。我们现在只假设：某个未来版本确实需要写出旧 reader 不认识的新 durable representation。

先运行仓库提供的 baseline probe：

```bash
cd labs/taskforge
PYTHONPATH=src uv run --with pytest --no-project python tools/m08_compat_probe.py
```

当前输出里有五条很重要的事实：历史 v1 fixture 仍能被当前 reader 读取；当前 writer 仍能被一个 frozen v1 reader 读取；frozen v1 reader 会拒绝 v2；当前 TaskForge reader 也还不会读 v2；未知的 future schema version 会被明确拒绝。

`_legacy_v1_reader()` 很值得注意。它不是为了复刻所有旧实现细节，而是冻结了一个我们**不能随当前 PR 一起修改的 consumer**：它要求 `schema_version == 1`，并直接读取 `job["command"]`。假设机器 A 已升级，机器 B 仍在旧版本；如果 A 马上开始写 v2，B 下一次启动或读取 shared snapshot 就会失败。

这时问题已经不是“v2 parser 对不对”了。即使新 writer 写出的 v2 完全符合新 specification，新 reader 也完全正确，下面这个组合仍然不成立：

| Producer | Consumer | 当前/目标关系 |
|---|---|---|
| W1 | R1 | baseline，必须工作 |
| W1 | R2 | reader upgrade 后必须工作 |
| W2 | R2 | 最终新世界必须工作 |
| W2 | R1 | 当前已知不兼容 |

真正的故障发生在**版本组合**上，而不是单个版本内部。到这里才值得给这个问题命名：我们需要设计的是 **compatibility contract**，以及让系统从旧组合走到新组合的 **migration path**。

M05 已经告诉我们，最终 architecture 不是唯一的设计对象，change sequence 也需要设计。M08 把同一个判断推进到跨 release 的系统：最终格式只是终点；old/new coexistence window 本身也是系统状态。

## 2. Compatibility 不是一个布尔值

一句“v2 backward compatible”通常省掉了太多信息。至少要知道谁产生 representation、谁消费、各自是什么版本、在哪个 surface 上、要保持到什么语义层，以及这个承诺持续到什么时候。

为了强迫 review 把这些问题说清楚，本课程使用一个 reasoning aid：

```text
Compatibility =
    surface
  × producer version
  × consumer version
  × direction
  × semantic expectation
  × time window
```

这不是某个外部标准给出的公式，而是课程综合。它的价值在于阻止“compatible”变成一个没有主体和时间范围的形容词。

### 先找 surface，再谈版本号

Google AIP-180 对网络 API 区分 **source compatibility、wire compatibility 和 semantic compatibility**。这个区分可以帮助我们避免一个很常见的误判：调用还能 compile 或 payload 还能 parse，不代表 consumer 看到的含义没有变化。

例如 `list_jobs() -> list[Job]` 的函数签名可以完全不变，但如果以前返回 insertion order、现在变成 arbitrary order，source surface 可能没坏，behavioral/semantic contract 却可能已经变了。TaskForge 的 snapshot 也一样：root keys、schema version、job fields、status strings、ordering、field meanings 都可能是相关 surface；exact indentation 和 whitespace 则只有在真实 consumer 依赖它们时才应升级成 byte-level contract。测试里恰好出现某种格式，不等于测试有权凭空发明公共 API。

AIP-180 的 taxonomy 主要面向网络 API。本课程把“先区分 surface”这条 reasoning 扩展到 serialized files、config、CLI、database rows、library API 等场景，这是课程自己的推广，不应倒过来说 AIP 原文覆盖了所有这些系统。

### 与其争 backward / forward，不如把矩阵写出来

`backward compatible` 和 `forward compatible` 在不同团队里经常被说反。对于 migration review，更稳妥的做法通常是直接写 producer/consumer matrix。

在 TaskForge 里，我们真正关心的是：升级 reader 以后，旧数据还要不要能读？如果系统存在 mixed-version window，新 writer 产生的数据是否会被旧 reader 看见？如果答案是否定的，是不是可以通过 rollout ordering 保证这个组合根本不会发生？这些问题比术语本身更有操作性。

兼容性也不意味着“所有格子都必须 PASS”。`W2 -> R1` 可以是一个**明确允许失败的组合**，只要 migration contract 保证在任何 R1 仍可能读取 shared state 时，production writer 都不会默认产生 W2。设计目标不是兼容一切，而是明确哪些组合必须存在、哪些组合必须被禁止，以及这个约束何时结束。

## 3. Durable data 把旧世界留在了现场

普通函数调用通常只存在几十毫秒；serialized snapshot 可以跨 process lifetime、release lifetime，甚至在一个离线修复工具一年后运行时再次出现。正因为数据比产生它的程序活得更久，consumer inventory 往往比代码搜索复杂。

M08 的 `fixtures/m08/snapshot-v1.json` 就代表这种历史事实。它不是“方便构造测试输入的一段 JSON”，而是一个已经离开当前 producer 的 durable artifact。把 v2 实现写完后顺手把这个 fixture 也升级成 v2，会让测试继续全绿，却删掉了“今天的 reader 仍能读过去真实存在的数据”这一条证据。

这也解释了为什么 rollback 不能只理解成 deployment system 里的一个按钮。假设新 binary 已经写出 v2，事故发生后你把 executable 回退成只会 R1 的旧版本：代码是 rollback 了，系统却可能再也打不开当前 durable state。对 durable format，rollback readiness 应该问：**rollback target 能不能读 rollout 已经产生的数据？**

### Version field 是路标，不是 migration machinery

`schema_version` 很有价值，因为它让 reader 在不知道语义时明确拒绝，而不是猜。但数字本身不会完成 compatibility work。`schema_version = 2` 不能回答 R2 是否能读 v1、R1 是否会看到 v2、已有数据如何处理、rollback 是否安全，也不能证明 migration 已经结束。

反过来，并不是每次结构变化都必须 bump version。假设 v1 reader 已知会忽略一个新的 top-level metadata field，而且这个字段不改变它已经理解的语义，那么增加该字段可能仍属于同一个 compatibility envelope。Version bump 应表达 contract boundary，而不是“文件有 diff，所以数字加一”。

### “忽略 unknown”同样不是普遍规则

Unknown field 有时可以安全忽略；unknown semantic discriminator 往往不行。TaskForge 的教学 v2 包含 `task.kind = "shell"`。如果一个 reader 只取 `task.command`，完全不验证 `kind`，未来看到 `kind = "http"` 时就可能把另一个 task type 当 shell command 执行。这不是 forward compatibility，而是 silent semantic corruption。

所以 current reader 遇到 unknown future `schema_version` 时 fail closed，是一个有明确语义依据的选择：它不知道新 contract 是否还能按旧模型解释。相同原则也适用于 unknown enum、required invariant 或改变 interpretation 的新字段。不要把 Postel-style tolerance 机械升级成“reader 永远应该尽量猜”。

Protocol Buffers 提供了另一个有用的反例。在 protobuf binary wire format 里，field number 是 wire identity 的核心；source-level rename 和 field-number change 完全不是同一种变化，删除字段后复用旧 number 也有明确风险。这提醒我们：**schema evolution 必须理解真实 representation。** JSON、protobuf、SQL row、binary struct 的 compatibility rule 不会因为都叫“schema”就变得一样。

## 4. 从 failure matrix 推出 migration，而不是先套 pattern

现在回到 TaskForge。我们已经知道一个关键事实：`W2 -> R1` 不成立。于是最危险的 rollout 是先切 writer。只要有一个旧 reader 仍然可能读取 shared snapshot，新 data universe 就已经超出它的理解能力。

一个更稳妥的第一步是让新版本扩大**读取能力**，但暂时不扩大 production 默认 writer 的输出集合：R2 同时理解 v1/v2，W1 仍是默认 writer。这样部署新 reader 本身不会让旧 reader 突然看到新格式。

这时 Fowler/Danilo Sato 的 **Parallel Change** 才真正有用。原文把 backward-incompatible interface change 分成三阶段：**Expand** 时 supplier 同时支持 old/new form；**Migrate** 时逐步把 clients 从 old form 迁到 new form；**Contract** 时在所有 usages 都迁走后删除 old form。

这套 source pattern 给 TaskForge 的是“不要一次跨过 old/new coexistence window”的结构启发，不是角色的一一映射。TaskForge 当前第一步扩大的是 **reader/consumer capability**：R2 能读 v1/v2；这并不等于 Fowler 原义里 supplier interface 的 Expand。后面的 E/M/W/C 是课程为 durable producer/consumer timeline 做的 operational adaptation。

### Durable format 需要把 writer cutover 单独看见

TaskForge 的场景和一个普通 method signature change 有一个额外维度：client migration 之外，还有一个 durable **producer cutover**。如果我们直接把 writer cutover 叫作 Fowler 的 `Migrate`，就会把“clients 已升级”与“系统开始产生新 durable data”两个不同的时间点压成一个名字。

因此本章对 Parallel Change 做一个明确的课程适配，把 operational timeline 写成四个可区分的事件：

| Event | TaskForge 状态 | 主要证据/风险 |
|---|---|---|
| **Expand capability** | R2 code 能读 v1+v2；默认 W1 | 新能力存在，但尚未要求 old consumers 消失 |
| **Migrate readers/consumers** | supported readers/tools 逐步升级到 R2；仍默认 W1 | 要证明旧 reader 已退出 writer-visible path |
| **Writer cutover** | production default W1 → W2 | durable state universe 改变；rollback compatibility 需要重算 |
| **Contract** | 删除不再承诺的 W1 / old interface / transitional path；是否保留 v1 reader由产品 policy 决定 | 清理 temporary burden，但不能误删 intentional compatibility feature |

这里不要求 source roles 与 TaskForge roles 同构：`Expand capability` 是课程给“先扩大 reader capability”的 operational label；Fowler source 仍只对 supplier-interface Expand / client Migrate / Contract old form 负责。

### 第一阶段为什么只做 capability expansion

本章 Lab 的代码 change 只要求进入第一个 event：new reader 能读 v1/v2，default writer 继续写 v1。可以完全不暴露 production W2 writer；也可以提供显式 `format_version=2` 能力用于 fixture/integration test，但默认输出不能悄悄改变。

这不是“只做半个 feature”。它是一个可以独立部署、独立验证、保持 rollback space 的 transitional state。M05 的 staged change 到这里变成了 staged production compatibility。

### Reader migration 是一个 deployment fact，不是 parser feature

R2 code 已经合入仓库，不代表所有 consumer 都已经 R2。daemon、CLI、offline repair tool、backup restore image、supported rollback binary 都可能是 reader。真正进入 writer cutover 前，需要根据产品支持范围说明哪些 consumers 必须迁移，以及怎样证明它们已迁移。

如果某类 consumer 无法 inventory，这不是理由把它从模型里删掉；它意味着 writer cutover policy 必须更保守，或者产品需要显式终止对那类 consumer 的兼容承诺。

### Writer cutover 改变的是 rollback boundary

当所有 relevant readers 都已具备 v2 decode 能力后，系统才有资格单独评审 W2 cutover。这个 change 风险高于 reader capability expansion，因为从第一份 v2 durable object 写出开始，“rollback 到只会 R1 的 binary”可能不再成立。

一种常见的 activation control 是 **feature flag / rollout gate**：W2 capability 可以先随代码发布但保持 disabled，等 reader-migration evidence 和授权条件满足后再打开。Fowler 也明确提到 migrate phase 可以用 Feature Flag 控制 old/new interface 的使用；TaskForge 这里只把它当作候选 activation mechanism，而不是必需实现。**Flag 本身不会创造 compatibility、不会证明 readers 已迁完，也不会自动让 rollback 变安全。**

这里不要把 writer cutover 写成普遍意义上的“不可逆操作”。如果系统有可靠 down-conversion、双向 representation compatibility，或 rollback target 本身能读 v2，它可以是可逆的。TaskForge 当前 teaching candidate 没有这些 mechanism，所以更精确的说法是：**W2 cutover 跨过了一个 compatibility boundary，并可能缩小可用 rollback set。**

Kubernetes 的 API deprecation policy 给这个 reasoning 提供了一个真实的大型系统例子：已经持久化过的 representation 不能因为 serving endpoint 下线就突然无法 decode；preferred/storage version 向前推进前，需要有 release 同时支持新旧版本；政策还明确保留 upgrade 后 rollback 的空间。本章借用的是这种 overlap/rollback reasoning，不要求 TaskForge 复制 Kubernetes 的 conversion machinery。

### Contract 不一定等于“删除所有旧 reader”

Fowler 的 interface example 在所有 clients 已迁移后删除 old version。但 durable file format 还多了历史 import policy。产品可能明确承诺“永久导入 v1 snapshot”；此时 v1 reader 是产品功能，不是 migration debt。

因此停止写 v1 和停止读 v1 是两个独立 lifecycle events。Contract 的核心不是把所有旧代码删光，而是**结束那些只为了过渡而存在、已经不再属于支持政策的 compatibility burden**。如果 old reader 被长期保留，就应有明确的 support policy，而不是一句“先留着以后再说”。

## 5. Migration evidence 必须跨过版本边界

当前 producer 和 current consumer 做 round-trip 很有用，但它只能证明“今天两边同意同一个 contract”。Migration 的关键问题恰恰在不同时间产生的程序和数据之间。

TaskForge 因此需要至少几种不同性质的 evidence。

### Historical fixture：过去 producer 的证据

`snapshot-v1.json -> R2` 应该继续 PASS，而且要验证 normalized `id / command / status / exit_code / ordering`。Historical fixture 不应随着 implementation 一起被“修”成 v2；否则 producer 和证据同时移动，compatibility regression 会被隐藏。

但 fixture 的 byte hash 不是自动 public API。保留这个文件 byte-for-byte 是为了确保实验中的 historical evidence 没被重写；它不意味着 exact indentation 本身已经被课程宣布成所有 TaskForge consumer 必须依赖的 contract。

### Frozen old reader：已经部署 consumer 的证据

`default current writer -> frozen R1` 必须继续 PASS。这个测试证明的不是 parser correctness，而是 expand-capability change 尚未越过 writer cutover boundary。

如果实现了显式 W2 writer，则应同时验证 `W2 -> R2` 成功和 `W2 -> frozen R1` 按预期失败。后者不是一个需要“修成绿色”的 bug；它是在 executable evidence 里记录 rollout constraint。

### Future/malformed input：不要用宽容掩盖语义未知

R2 还需要明确验证 unknown future version、missing v2 `task`、unknown `task.kind`、missing `command`、wrong type 等 case。这里的目标不是追求“所有奇怪 JSON 都 reject”，而是证明 reader 不会在缺少必要语义时 silent coerce。

于是 compatibility matrix 不是“多测几组更保险”的测试风格。**矩阵应由 rollout contract 推导。** 如果产品不承诺 W2 被 R1 读取，就不需要把那个格子硬改成 PASS；但必须把它测成明确的 known incompatibility，防止以后有人误以为可以安全打开 writer。

## 6. Rollback 要跟着 data state 一起推演

把 rollout 切成前面的事件后，rollback reasoning 会清楚很多。

在 capability expansion 或 reader migration 期间，只要 default writer 仍是 W1，durable data universe 仍停留在 v1。即使 R2 deployment 本身有 bug，回退到 R1 对 snapshot format 来说通常仍是安全的，因为新 binary 尚未留下旧 binary 不认识的 state。

W2 cutover 以后条件变了。此时 rollback target 必须至少满足一种条件：自己能读 v2；存在被验证过的 down-conversion；或者 rollout 保证尚未产生任何 v2 durable state。只写“出问题就 rollback binary”没有回答这些数据问题。

Offline tool 会把这个问题变得更尖锐。假设主 fleet 已经全是 R2，但一年运行一次的 repair tool 仍是 R1。“fleet old process count = 0”并不能证明 writer cutover 安全。你可以选择先升级/退役 tool、提供 explicit export-v1、长期保持 W1，或增加 conversion layer；哪一个正确由产品 support policy 决定，课程不替你决定。但这个 consumer 不能因为不常运行就从 matrix 里消失。

这一节只投影 **behavior、data representation 与 mixed-version compatibility**。真实 release 还可能同时由 source、binary、schema、runtime config、generated artifact、feature-flag state 等多种 artifact 组成；这时“rollback”还必须先说明到底恢复哪一组 configuration。旁支 [Configuration、Baseline 与 Release](../extensions/configuration-baselines-and-release.md) 专门补这层 configuration identity / release composition，不应把本节的 snapshot condition 当成完整 release rollback model。

这也是为什么 migration completion criterion 必须可证伪。`大家应该都升级了` 不是 evidence；`supported reader inventory 中 R1=0`、`old API usage metric 在约定窗口内为 0`、`repo 中 supported old usages=0`、`所有 supported rollback targets 都能 decode v2` 才是可以 review 的 statement。具体系统选择哪些 signal 不必相同，但 exit criterion 必须能被现实反驳。

## 7. Representation migration 有多个 mechanism；先问 authority

知道 migration timeline 并不等于已经选定数据转换机制。下面几种方案都可能成立，但它们保护的 failure surface 不一样。

### Boundary dual-read：TaskForge 当前最小 candidate

对于这次小型 JSON change，最直接的方案是把 wire-version dispatch 留在 snapshot boundary：`_decode_v1_job()` 和 `_decode_v2_job()` 都 normalize 成同一个内部 `SnapshotJob(command=...)`。这样 domain code 不需要到处判断 flat `command` 与 `task` object。

这复用了 M04 的 boundary principle。它也保持了单一 production writer authority，所以在 TaskForge 这个特定场景里，比为了照顾 R1 而同时写两份 representation 更容易分析。**这不是“dual-read 永远优于 dual-write”的通用定律。** 它成立是因为当前 requirement 很小、reader-side normalization 足够，而且我们可以通过 rollout ordering 延后 W2。

### Lazy read migration

Reader 遇到 old representation 时先 decode/normalize，必要时以后再写成 new representation。它避免一次性大规模 rewrite，但可能让 mixed formats 长期存在，并把转换成本推到 first read。

### Eager/offline migration

协调 writes，扫描历史数据并批量 rewrite。它让最终状态更清晰，也可能更容易观察 contract criterion；代价是 downtime、blast radius、partial failure 和 rollback complexity。

### Dual write

同时写 old/new copy 可以帮助某些 consumer migration，但它立刻把 M02 与 M07 带回来：两份 representation 哪一个 authoritative？第一份写成功、第二份失败怎么办？reconciliation 谁负责？retry 会不会重复其中一个 effect？如果这些问题没有答案，“为了兼容就 dual-write”只是把一个 migration 问题换成一个 split-authority protocol。

### New store / shadow copy / cutover

当 mapping 不可逆、数据量巨大或 old/new ownership 差异很大时，新 store + shadow validation + cutover 也可能更适合。但它同样引入 dual state、同步和 reconciliation。有没有新 store 不是关键；**在任何 transitional state 中，哪份事实是 authority、怎样判断 cutover 完成**才是关键。

这些 mechanism 都是 design candidates。课程的 authority 来自 constraints 和 failure model，而不是 instructor reference 恰好用了哪一种。

## 8. Version number 能传达意图，但不能替代 downstream evidence

Semantic Versioning 的第一条前提其实比 `MAJOR.MINOR.PATCH` 更重要：软件需要先声明 public API。只有知道什么属于 public API，major/minor/patch 才有判断基础。

这对 TaskForge 很直接。Job ordering 是不是 contract？exception type 是不是？config key、filesystem layout、serialized representation 呢？如果这些问题还没有答案，把版本从 `1.4.2` 改成 `1.4.3` 并不会自动让 consumer 安全。

SemVer 更适合作为 provider 向 consumer 传递 change-risk intention 的 communication protocol，而不是 compatibility proof。Software Engineering at Google 的 Dependency Management 章节也对它保持谨慎：在跨组织、consumer visibility 很低的环境里，SemVer 是有价值但有损的信息压缩，不是完整的 dependency-management solution。

Hyrum's Law 提醒我们另一个现实：consumer 数量足够大时，几乎任何 observable behavior 都可能被依赖。因此“没有写进文档”只能降低 provider 的 formal obligation，不能证明 change 没有 migration risk。一个 provider 仍然需要根据 consumer visibility、support commitment 和 breakage cost 决定是否迁移、警告、提供兼容窗口，还是接受 breaking change。

这里也不要走向另一个极端：Hyrum's Law 不意味着所有历史行为都必须永久冻结。它说明的是 unknown dependencies 的风险会增加，**不是把 design authority 从产品 policy 转交给所有偶然 observable behavior。**

## 9. Dependency 是另一种跨时间 compatibility contract

到目前为止，我们一直把自己当 provider：TaskForge 改 snapshot format，旧 reader 是 consumer。换个方向，当 TaskForge `import library_x` 时，我们自己也成了 consumer。

引入 dependency 的成本不止“今天能不能安装”。长期关系还包括 security fixes、upstream API change、new runtime/OS、transitive dependency drift、license/policy change、abandonment 和 version conflicts。Software Engineering at Google 强调 dependency management 的困难来自 **network + time + weak coordination**：真实对象通常是 dependency graph，而不是 manifest 里的一行版本号。

```text
app
 ├─ A
 │   └─ X@1
 └─ B
     └─ X@2
```

因此一次看似局部的 `upgrade A` 可能让全局 constraint network 失去可满足解。Review dependency change 时应看 transitive graph、lockfile、supported version range、maintainer/upgrade cadence 和 rollback，而不只是 package 首页上的最新版本。

Pinning 能帮助 reproducibility：今天和明天使用同一个 resolved dependency state。但 pin 到 `1.2.3` 不会让安全漏洞、新 compiler、新 runtime 和 upstream ecosystem 停止变化。**Reproducible state** 与 **sustainable evolution** 是两个问题。

M08 Lab 里有人提议为“两版本的小 JSON parser”引入 schema/migration library。预期 reference 判断是 stdlib `json` 已经足够表达 version dispatch、field validation、normalization 和 error semantics，因此额外 dependency 的长期成本暂时不值得。但这只是当前 constraint 下的 judgment；如果以后出现很多版本、复杂 validation、跨语言 code generation 或共享 schema，答案可以变化。评分应看 reasoning，不看学生有没有机械得出“不要 dependency”。

Consumer visibility 同样会改变 dependency strategy。Google 的 monorepo/code-index/CI 环境可以把很多 provider change 转成 repo-wide source change；未知外部 consumers 则更依赖 compatibility promise、versioning、deprecation window 和 migration guide。本课程采用这个 visibility model，不把 `Live at Head` 或 monorepo 当成所有组织的默认答案。

## 10. 一个 migration 必须知道自己怎样结束

Compatibility branch 在 migrate period 中通常是**有计划的临时复杂度**。问题不在于 old/new path 同时存在，而在于没人知道它们何时可以退出。

Software Engineering at Google 的 Deprecation material 强调 warning 本身不会自动让 migration 完成：需要 owner、milestone、progress evidence，以及防止新代码继续引入 old usage 的机制。于是 `@deprecated`、日志 warning 或 TODO 都只是信号；如果没有 removal criterion，compatibility layer 很容易变成永久 architecture。

Prevent backsliding 也因此是 correctness 的一部分。假设 80% clients 已迁到 new API，但新代码仍然可以继续调用 old API，migration target 就会不断移动。根据环境，可以使用 deprecation annotation、lint/static check、CI ban、visibility restriction，以及更新 docs/examples 来阻止新增 old usage。

不过“必须结束 migration”仍需要 qualifier。如果产品明确承诺永久导入历史 v1 project file，那么保留 v1 decoder 就是 intentional compatibility policy，不应因为“contract phase”这个词把它删掉。真正要结束的是未经 policy 授权的 transitional burden。

一个好的 cleanup decision 因此至少回答：谁在用 old path、谁负责迁移、怎样测 progress、什么 criterion 允许停止 old writes、什么 criterion 允许停止 old reads，以及如果 old read support 是永久 feature，由谁维护它。

## 11. 把模型迁移到 config 和 API，才能看出它不是 JSON 技巧

Snapshot 只是 running case。相同 reasoning 会在其他 surface 上重新出现。

### Config rename 可能根本不是 rename

M07 特别区分了 `max attempts` 和含糊的 `retry N times`。假设旧配置叫：

```yaml
retry_limit: 3
```

新配置想改成：

```yaml
max_attempts: 3
```

如果 `retry_limit` 的旧语义是“initial attempt 之后最多再 retry 3 次”，真正等价的 mapping 可能是 `max_attempts: 4`。机械做 `3 -> 3` 会在 migration 中改变 behavior。M01 的 specification 因此直接约束 config migration：先写 semantic mapping，再决定 parser alias、deprecation 或 one-time conversion。

### API version 也不是越多越好

`/v1`、`/v2` 可以是合理 boundary，但不是每个小 change 都值得永久复制一套 endpoint。Parallel Change 提供另一种可能：old/new field 或 method 并存，clients migrate，最后删除 old form。选择策略要看 change magnitude、consumer control、release cadence、wire representation 和 support commitment，而不是“有 version number 看起来更专业”。

如果 provider 能看到并修改所有 consumers，provider-side migration 往往比把 breaking cost 分散给所有 clients 更可控；如果 consumers 不可见，则 compatibility promise 与 deprecation window 的权重会上升。**Consumer visibility 是 change strategy 的输入，不是背景信息。**

## 12. 给 Agent 的任务，不要只有“把 schema 升到 v2”

一个模糊 prompt 很容易诱导 Agent 做 final-state patch：把 `SCHEMA_VERSION` 直接改成 2，替换 parser，更新 historical fixture，再让 current writer/current reader round-trip 变绿。单看 diff 可能很整洁，却把 migration contract 全部删除了。

对本章 TaskForge case，更好的 task contract 应先限定 authority 和时间范围：

```text
Goal:
Prepare TaskForge snapshot v1 -> teaching-candidate v2 migration.
This change is capability expansion only; it must not cut over the production writer.

Read first:
- inventory snapshot readers, writers, historical fixtures, and frozen old-consumer evidence;
- write the R1/R2 x W1/W2 compatibility matrix;
- state which consumers are controllable and which represent deployed/history boundaries.

Preserve:
- historical v1 fixture;
- v1-format decode semantics and job ordering;
- default writer output remains schema_version=1;
- frozen R1 accepts default output;
- unknown future version fails explicitly.

Add:
- R2 accepts v1 and teaching-candidate v2;
- version-specific wire forms normalize to the same internal SnapshotJob semantics;
- malformed/unknown v2 task semantics fail explicitly.

Do not in this change:
- switch production default to W2;
- remove v1 decode support;
- invent dual-write or a new persistence system;
- rewrite historical fixtures.

Evidence:
- historical W1 fixture -> R2 PASS;
- default W1 -> frozen R1 PASS;
- v2 fixture/explicit W2 -> R2 PASS if W2 capability is implemented;
- W2 -> frozen R1 remains an explicit known incompatibility;
- future version and malformed v2 cases reject deliberately.

Deliver separately:
- reader-migration exit criterion;
- writer-cutover precondition and rollback analysis;
- long-term v1 read-support policy/removal criterion.
```

这个 contract 没有规定必须用某个 parser architecture，也没有让 instructor reference 变成唯一答案。它约束的是 compatibility envelope、non-goal、evidence 和 design authority。

Writer cutover 应单独成 change，原因也不只是“PR 小一点更好 review”。Capability expansion 主要增加 reader 能力；writer cutover 改变未来可能存在的 durable representation 集合，并可能让旧 rollback target 退出安全集合。这是不同的 risk boundary，应该有独立证据和授权。

## 13. Review migration PR 时沿着谁、什么版本、哪个时间点检查

面对 compatibility/migration change，可以把 review 压缩成几组问题。

**Surface 与语义**

- 哪些 observable surface 真的改变：source、wire/data、config、behavior，还是别的？
- 哪些是明确 contract，哪些只是 observed implementation 或 historical evidence？
- representation 里哪些 identity/unknown values 会改变语义，不能被 reader 随便忽略？

**Producer / consumer matrix**

- old producer -> new consumer 是否必须工作？
- new producer -> old consumer 是否必须工作，还是应被 rollout 阻止？
- offline tools、backup/restore image、rollback binaries 有没有被算进 consumer inventory？

**Timeline 与 authority**

- 当前 PR 是 expand capability、consumer migration、writer cutover，还是 contract？不要把不同 event 混成一个“migration 完成”。
- writer cutover 的前置 evidence 是什么？它会不会改变 rollback-compatible targets？
- dual representation/store 如果出现，哪一份 authoritative，partial failure/reconciliation 怎么处理？

**Evidence**

- historical fixture 有没有被偷偷更新？
- frozen old consumer 有没有真的运行？
- compatibility tests 是否来自 rollout matrix，而不只是 current-current roundtrip？
- future/unknown semantics 是明确 reject，还是通过猜测制造 silent corruption？

**结束条件**

- migration progress 怎样观测？
- 如何防止新增 old usage？
- 什么时候停止 old writes，什么时候停止 old reads？
- 被长期保留的 compatibility path 是明确产品 policy，还是忘记删除的 transitional code？

这些问题的共同点是：它们都把“compatibility”从标签重新还原成一个可验证的时序 contract。

## 14. 本章哪些判断来自材料，哪些是课程综合

M08 的主要来源承担不同角色，不能互相代替。

Google AIP-180 支撑 source / wire / semantic compatibility 的 vocabulary，但它主要面向网络 API；本章把“先区分 surface”推广到 file/config/DB 等，是课程综合。

Semantic Versioning 2.0.0 支撑 public API 先于版本规则、以及 major/minor/patch 的 communication contract；它不证明未知 downstream consumer 一定安全。Software Engineering at Google 的 Dependency Management 与 Deprecation 分别支撑 dependency network/time/visibility，以及 migration owner/milestone/backsliding reasoning；Google 的组织环境和 `Live at Head` 前提不被课程推广成普遍策略。

Fowler/Danilo Sato 的 Parallel Change 明确提供 **supplier Expand → Migrate clients → Contract** 三阶段 interface pattern，并提到 migrate phase 可用 Feature Flag 控制 old/new interface 的使用。TaskForge 的 reader-capability expansion、reader migration、durable **writer cutover** 与 cleanup 是课程针对 producer/consumer data lifecycle 的适配；这些 operational roles 不要求与 Fowler 的 supplier/client roles 一一同构。Feature flag 在本章也只作为候选 activation control，不承担 compatibility proof。

Protocol Buffers 文档用于说明 encoding-specific compatibility rule；TaskForge 并不使用 protobuf。Kubernetes deprecation policy 则真实支撑 persisted representation 的 decode obligation、old/new version overlap 和 upgrade/rollback reasoning；课程只借这些 invariants，不复制 Kubernetes 的 machinery。

本章的六维 compatibility formula、TaskForge R/W matrix、historical fixture/frozen reader 的具体 evidence design、v2 task-object scenario、dual-read/dual-write comparison、四事件 operational timeline，以及 Agent task contract，都是课程自己的工程综合或 repo-fixture reasoning。

本章也把此前模块重新接到同一条时间轴上：M01 提供 semantic contract，M02 约束 transitional state authority，M03 要求 compatibility claim 有 executable evidence，M04 提供 representation-normalization boundary，M05 提供 staged change，M06 提醒我们旧 consumer/数据可能不可控，M07 则让 dual-write、partial migration 和 retry 的 failure window 变得不可忽视。

真正需要带走的不是“所有系统都该兼容旧版本”，而是下面这个判断：

> **一个新版本是否正确，只说明一个时间点上的实现；compatibility 要说明哪些新旧 producer、consumer 和数据组合在什么时间窗口里仍必须正确，migration 则要让这些组合按可验证的条件逐步变化，直到系统进入新的稳定世界。**

动手前请完成 [`Lab 08 — Compatibility 与 Migration`](../labs/08-compatibility-migration.md)。逐项 provenance 与 limitations 见 [`M08 Source Audit`](../reading-notes/m08-source-audit.md)。

### 可选主材料

- Google AIP-180 — Backwards compatibility: <https://google.aip.dev/180>
- Semantic Versioning 2.0.0: <https://semver.org/spec/v2.0.0.html>
- Software Engineering at Google — Dependency Management: <https://abseil.io/resources/swe-book/html/ch21.html>
- Software Engineering at Google — Deprecation: <https://abseil.io/resources/swe-book/html/ch15.html>
- Danilo Sato / Martin Fowler — Parallel Change: <https://martinfowler.com/bliki/ParallelChange.html>
- Protocol Buffers — Updating a Message Type: <https://protobuf.dev/programming-guides/editions/#updating>
- Kubernetes — API deprecation policy: <https://kubernetes.io/docs/reference/using-api/deprecation-policy/>
