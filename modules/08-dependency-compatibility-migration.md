# M08 — Dependency、Compatibility 与 Migration：软件变化必须穿过新旧世界共存期

> 这一章的目标不是让你背 Semantic Versioning，也不是教你写某一种 database migration framework。
>
> 真正目标是：**当旧 caller、旧 binary、旧配置、旧数据、旧协议或旧依赖已经存在时，你能明确 compatibility contract，并设计一个可验证、可回退、最终能够结束的 migration path。**

---

# 0. 从一个“新代码完全正确”的事故开始

假设 TaskForge 已经把 job snapshot 存成 JSON：

```json
{
  "schema_version": 1,
  "jobs": [
    {
      "id": "job-41",
      "command": "echo hi",
      "status": "queued",
      "exit_code": null
    }
  ]
}
```

现在你觉得 flat `command` 不够扩展。

未来可能有：

```text
shell task
HTTP task
Python task
container task
```

于是你设计 v2：

```json
{
  "schema_version": 2,
  "jobs": [
    {
      "id": "job-41",
      "task": {
        "kind": "shell",
        "command": "echo hi"
      },
      "status": "queued",
      "exit_code": null
    }
  ]
}
```

新 writer：正确。

新 reader：正确。

新 reader 的 tests：全绿。

你发布。

然后：

```text
node A already upgraded
node B still old
```

A 写出 v2 snapshot。

B 重启。

B 只认识：

```text
schema_version == 1
job["command"]
```

结果启动失败。

问题不是 v2 implementation 不正确。

问题是：

> **你只设计了最终状态，没有设计从 old world 到 new world 的路径。**

M05 已经说过：

```text
最终 architecture 是设计对象
change sequence 也是设计对象
```

M08 把这个原则推进到多版本系统：

```text
最终 contract 是设计对象
old/new coexistence window 同样是设计对象
```

---

# 1. Compatibility 不是一个 bool

工程讨论里经常听到：

```text
“这个改动 backward compatible。”
```

这句话通常信息不够。

至少应该问：

```text
谁产生数据？
谁消费数据？
哪个版本？
哪个方向？
兼容到什么语义层？
持续多久？
```

所以本课程使用：

```text
Compatibility =
    surface
  × producer version
  × consumer version
  × direction
  × semantic expectation
  × time window
```

这不是某个标准里的公式，而是本课程的 reasoning aid。

---

# 2. 先找 compatibility surface

一个 change 的 public surface 远不止函数签名。

常见 surface：

```text
source API
binary ABI
wire protocol
serialized data
DB schema
config file
CLI flags
exit codes
filesystem layout
environment variables
metrics/log names
ordering
timing/performance assumptions
```

例如：

```python
list_jobs() -> list[Job]
```

签名不变。

但：

```text
以前 insertion order
现在 arbitrary order
```

可能是：

```text
source-compatible
behavior-incompatible
```

Google AIP-180 明确把 compatibility 至少分成：

```text
source
wire
semantic
```

这个分类非常重要，因为：

> **“还能 compile / parse”不等于“调用者看到的含义没变”。**

---

# 3. Backward / Forward 到底是哪个方向

这两个词经常说反。

比起背名词，直接写 matrix 更安全。

假设：

```text
R1 = old reader
R2 = new reader
W1 = old writer
W2 = new writer
```

问：

| Producer | Consumer | 必须成功吗？ |
|---|---|---|
| W1 | R1 | baseline |
| W1 | R2 | ? |
| W2 | R1 | ? |
| W2 | R2 | new baseline |

对于 rolling upgrade，常见需求是：

```text
R2 reads W1
```

因为：

```text
old data survives after reader upgrade
```

但如果系统允许：

```text
new writer exists while old reader still exists
```

那么还要：

```text
R1 reads W2
```

或者：

```text
禁止 W2 在 old reader 退役前出现
```

注意，这两种都是合法设计。

关键是明确。

---

# 4. Durable data 比函数调用更难

函数调用通常是瞬时 interaction：

```text
caller → callee → return
```

serialized data 可以跨越：

```text
process lifetime
release lifetime
machine lifetime
team lifetime
```

今天写入：

```text
snapshot-v1.json
```

三年后某个恢复工具可能仍在读。

因此 durable format 的 consumer inventory 很难完整。

这也是为什么：

```text
“新代码能读新格式”
```

远远不够。

你还需要问：

```text
已有数据怎么办？
rollback 后怎么办？
旧工具怎么办？
backup restore 怎么办？
离线 migration 中断怎么办？
```

---

# 5. Version field 是路标，不是魔法

TaskForge v1 有：

```json
{"schema_version": 1}
```

这有价值。

它允许 reader fail closed：

```text
version 99
→ reject
```

而不是：

```text
“看起来差不多，猜着读一下”
```

但 version field 本身不会解决 compatibility。

例如：

```text
schema_version = 2
```

只说明：

```text
producer 声称这是另一种 contract
```

它没有告诉你：

```text
旧 reader 是否能读
新 reader 是否能读旧数据
rollback 是否安全
migration 是否完成
```

---

# 6. 什么时候根本不需要 bump format version

假设 JSON reader 只读取：

```text
id
command
status
exit_code
```

现在 writer 多写：

```json
{"generated_by": "taskforge-5.0"}
```

如果：

```text
old reader ignores unknown top-level fields
```

且这个字段不改变已有语义，那么它可能仍属于 v1 compatible evolution。

反过来，如果你只是：

```text
1 → 2
```

但 layout 完全 compatible，也许只是制造额外升级成本。

所以：

> **Version bump 应表达 contract boundary，而不是“我改了文件所以数字加一”。**

---

# 7. 但“忽略 unknown”也不是万能规则

很多人会说：

```text
Be liberal in what you accept.
```

但无限 tolerant reader 可能把未来语义误读成旧语义。

例如 v3 新增：

```text
status = "paused"
```

旧 reader 如果把 unknown status 默认为：

```text
queued
```

那它不是兼容。

它是在 silent semantic corruption。

因此 reader 有两种不同策略：

```text
unknown field
→ maybe safe to ignore
```

vs.

```text
unknown enum / version / invariant
→ often safer to reject
```

真正的问题不是“strict or tolerant”。

而是：

> **这个未知信息是否可能改变 caller 必须理解的语义？**

---

# 8. Protocol Buffers 给我们的反例：representation identity 很具体

在 protobuf binary wire format 中：

```text
field number
```

是 wire identity 的核心。

所以：

```text
source rename
```

和：

```text
field number change
```

不是同一件事。

Protocol Buffers 官方文档明确警告：已有 field number 不能随意改变，删除后也不应复用，应 reserve。

这说明：

> **Schema evolution 必须理解真实 encoding，而不是只看 source diff。**

JSON、protobuf、SQL、binary struct 的 compatibility rules 不一样。

---

# 9. Semantic Versioning 能做什么

SemVer 的价值是 communication：

```text
MAJOR.MINOR.PATCH
```

向 consumer 传递 provider 对 public API change 的意图。

而且 SemVer 规范第一条就要求：

```text
必须先声明 public API
```

这很重要。

如果你不知道：

```text
ordering 是否 public API
exception type 是否 public API
config key 是否 public API
file layout 是否 public API
```

那么：

```text
patch / minor / major
```

没有可靠基础。

---

# 10. SemVer 不能做什么

SemVer 不是 correctness proof。

provider 说：

```text
1.4.2 → 1.4.3
```

不代表未知 consumer 一定不会坏。

例如用户依赖了 undocumented：

```text
stable iteration order
```

你把它改了。

版本还是 patch。

consumer 还是坏。

Software Engineering at Google 对 SemVer 的评价很谨慎：它把 SemVer 看成跨组织、低 visibility 条件下有用的 risk shorthand，但不是 dependency-management 的完整答案。

这和 Hyrum's Law 有直接关系：

> 用户足够多时，几乎所有 observable behavior 都可能有人依赖。

所以：

```text
“not documented”
```

不能自动推出：

```text
“safe to change”
```

它只能降低 provider 的 formal obligation，不消灭 migration risk。

---

# 11. Dependency 是 contract，不是 import statement

你写：

```python
import library_x
```

只完成了 dependency lifecycle 的第一分钟。

长期成本包括：

```text
security fixes
platform updates
upstream API changes
transitive dependency drift
license/policy changes
abandonment
version conflicts
```

所以真正的问题是：

```text
Can I keep this dependency healthy over time?
```

不是：

```text
Can pip install it today?
```

---

# 12. Dependency graph，不是 dependency list

项目 manifest 看起来可能是：

```text
A
B
C
```

真实 graph：

```text
app
 ├─ A
 │   └─ X@1
 └─ B
     └─ X@2
```

于是你的局部选择：

```text
upgrade A
```

可能造成全局 unsatisfiable constraints。

Software Engineering at Google 强调 dependency-management 的核心困难正是 network + time + weak coordination。

所以 review dependency change 时不要只问：

```text
这个 package 版本新不新？
```

还要问：

```text
transitive graph 怎么变？
锁文件怎么变？
谁维护？
升级 cadence？
能否 rollback？
最低/最高版本假设？
```

---

# 13. Pinning 解决 reproducibility，不解决 eternity

把 dependency pin 到：

```text
1.2.3
```

可以帮助：

```text
今天和明天 build 一样
```

但不能保证：

```text
永远不用升级
```

因为：

```text
CVEs
new compiler
new OS
new runtime
transitive ecosystem
```

都会逼你动。

因此：

> **Reproducible dependency state 和 sustainable dependency evolution 是两个问题。**

---

# 14. Expand → Migrate → Contract

这是本章最核心的 migration pattern。

## 14.1 Expand

系统先支持 old + new。

例如：

```text
reader supports v1 and v2
writer still writes v1
```

此时：

```text
old reader + new reader
```

都还能处理新 writer 产生的数据。

这是安全 rolling upgrade 的关键。

## 14.2 Migrate

把 consumers 逐步换成 new-capable version。

你需要知道：

```text
谁还在 old path？
```

可能通过：

```text
code search
telemetry
version metrics
fleet inventory
logs
migration dashboard
```

## 14.3 Contract

确认 old consumers 已退役后：

```text
writer starts v2
```

之后如果 policy 允许，再删除：

```text
v1 reader
v1 converter
deprecated API
old config key
```

真正的 contract phase 是：

```text
remove compatibility burden
```

不是：

```text
留 TODO “later cleanup”
```

---

# 15. 为什么 writer 通常要比 reader 晚升级

考虑 rolling fleet：

```text
machine A: new binary
machine B: old binary
```

如果先切 new writer：

```text
A writes v2
B reads v2
→ fail
```

如果先部署 dual reader：

```text
A reads v1/v2, writes v1
B reads v1,    writes v1
```

此时仍安全。

等 B 也升级：

```text
A reads v1/v2
B reads v1/v2
```

才可以考虑：

```text
writer → v2
```

Kubernetes deprecation/storage policy 的一个重要思想就是类似的 overlap window：新旧 representation 先共同被支持，再推进 preferred/storage representation，从而保留 upgrade/rollback 空间。

---

# 16. Migration 的第一性问题：谁可能同时存在

不要先写 migration code。

先画 deployment matrix。

例如：

| Component | old/new 可共存？ | 是否同时读同一 durable data？ |
|---|---:|---:|
| CLI | yes | yes |
| daemon | yes | yes |
| worker | yes | maybe |
| offline repair tool | yes, 很久 | yes |
| tests | yes | fixtures |

如果：

```text
offline repair tool
```

一年才运行一次，那么“fleet metrics 里 old binary = 0”也不一定证明旧 reader 消失了。

这就是 unknown consumers 的现实。

---

# 17. Rollback 不是 deployment button，而是 data contract

很多 rollout 方案说：

```text
出问题就 rollback binary
```

但如果新 binary 已经写入 old binary 不懂的数据：

```text
rollback code
≠
rollback system
```

例如：

```text
new binary writes schema v2
↓
incident
↓
rollback to old binary
↓
old binary cannot decode v2
```

所以 rollback readiness 应问：

```text
binary rollback 后能读当前 durable state 吗？
```

而不是：

```text
CI 平台有没有 rollback 按钮？
```

本章主要关心 behavior、data representation 和 mixed-version compatibility；如果一个 release 由 source、binary、schema、runtime config、generated artifact 等多部分共同决定，还需要再问“我们正在 rollback 的到底是哪一组 configuration”。旁支 [Configuration、Baseline 与 Release](../extensions/configuration-baselines-and-release.md) 专门补这层 artifact identity、baseline 和 release composition 推理。

---

# 18. Data migration 的几种形态

## 18.1 Lazy read migration

```text
read old
→ convert in memory
→ optionally write new later
```

优点：

```text
无大规模 upfront rewrite
```

风险：

```text
old path 长期存在
first-read latency
mixed format 很久
```

## 18.2 Eager offline migration

```text
stop/coordinate writes
scan all old data
rewrite new format
```

优点：

```text
状态清晰
contract phase 容易
```

风险：

```text
downtime
large blast radius
partial failure
rollback difficulty
```

## 18.3 Dual write

```text
write old + new
```

优点：

```text
支持逐步 consumer migration
```

风险：

```text
partial write
consistency
which copy authoritative?
reconciliation
```

M02 已经告诉我们：

> **dual write 会重新引入 state ownership 问题。**

所以不要机械选择它。

---

# 19. Dual-read 通常比 dual-write 更容易，但也不是免费

例如：

```python
if version == 1:
    return parse_v1(raw)
if version == 2:
    return parse_v2(raw)
```

好处：

```text
单一 writer authority
```

但成本是：

```text
两个 parser
两套 fixtures
更多 compatibility tests
更长 support window
```

所以 expand phase 有技术债，但这是**有计划的临时复杂度**。

这和 accidental complexity 不一样。

前提是：

```text
contract criterion 已定义
```

---

# 20. Compatibility code 必须有删除条件

看到：

```python
if legacy_mode:
    ...
```

review 不应该只问：

```text
work 吗？
```

还应问：

```text
谁在用？
如何测？
何时不再用？
谁负责删？
哪个 release 可以删？
```

否则 migration layer 很容易变成永久 architecture。

Google Deprecation 章节强调：warning 本身通常不会让 migration 自动完成；需要明确 owner、milestone 和防止新增旧用法的机制。

---

# 21. Prevent backsliding

假设你已经迁移了 80% callers：

```text
old_api → new_api
```

但没有阻止新代码继续写：

```python
old_api(...)
```

那么 migration 可能永远收不完。

因此 migrate phase 往往需要：

```text
deprecation annotation
lint/static check
CI ban for new uses
visibility restriction
docs/examples updated
```

这不是“管理流程附属物”。

它是 migration correctness 的一部分。

---

# 22. Compatibility test 应该是 matrix test

只写：

```text
v2 writer ↔ v2 reader
```

几乎没有测 migration。

至少考虑：

```text
old fixture → new reader
new writer in compatibility mode → old reader
new writer → new reader
unknown future version → explicit failure
```

如果 rollout 要求 old reader 能读 new writer：

还必须测：

```text
new writer → old reader
```

注意：

> **测试矩阵来自 rollout contract，而不是来自“多测几组总没坏处”。**

---

# 23. Golden fixture 是时间机器

M08 中 historical fixture 很重要。

例如：

```text
fixtures/m08/snapshot-v1.json
```

它代表：

```text
一个已经离开当前 implementation 的 producer
```

因此 new reader 测它，不是在测 mock。

而是在问：

```text
今天的 binary 还能不能理解过去真实可能存在的数据？
```

这种 fixture 最好：

```text
来自真实 historical format
不可随着 implementation 随便重写
```

否则：

```text
producer + fixture 一起升级
```

会把 compatibility regression 隐藏掉。

---

# 24. Frozen old consumer 比 current-code round-trip 更强

这个测试：

```python
x = new_writer()
assert new_reader(x) == expected
```

只能证明：

```text
current producer / current consumer agree
```

但 compatibility 问题经常是：

```text
current producer / old consumer
```

所以 M08 probe 里保留一个 frozen v1 reader。

它代表：

```text
你无法回头给已部署 consumer 打补丁
```

这是一种非常高信息量的 test double：

它模拟的是**版本边界**，不是实现细节。

---

# 25. Unknown future version：为什么 fail closed 有时更好

假设 current reader 支持：

```text
1, 2
```

遇到：

```text
99
```

它可以：

```text
guess
```

也可以：

```text
reject clearly
```

对于 durable state，后者通常更安全。

因为 silent misinterpretation 可能导致：

```text
data loss
incorrect execution
wrong migration
```

M04 的 error semantics 在这里再次出现：

```text
unsupported format
```

应该成为稳定、可操作的 failure，而不是随机 `KeyError`。

---

# 26. Config migration 也有相同问题

例如旧配置：

```yaml
retry_limit: 3
```

你觉得名字不好，改成：

```yaml
max_attempts: 3
```

但两个词未必语义相同：

```text
retry_limit = 初始 attempt 后再 retry 几次？
max_attempts = 总 attempt 数？
```

这不是纯 rename。

所以 migration 必须先回答 semantic mapping。

可能是：

```text
retry_limit=3
→ max_attempts=4
```

而不是：

```text
3 → 3
```

M01 的 specification 在这里直接约束 migration。

---

# 27. API migration 不只是 endpoint version

最粗暴的做法：

```text
/v1
/v2
/v3
```

有时合理。

但如果每次小 change 都开新 version：

```text
maintenance surface ↑
client confusion ↑
deprecation burden ↑
```

Parallel Change 提供另一种可能：

```text
old + new field/method coexist
↓
clients migrate
↓
remove old
```

选择哪种取决于：

```text
change magnitude
consumer control
release cadence
support commitment
wire representation
```

不存在 universal answer。

---

# 28. Breaking change 的成本应该由谁承担

如果 provider 能看到并修改所有 consumers：

```text
provider/team can migrate them
```

这往往比：

```text
发布 breaking change
让每个 consumer 自己修
```

更可控。

Software Engineering at Google 的 dependency/deprecation 经验特别强调 visibility 和 ownership：同组织、可搜索、可统一 CI 的系统，可以把很多 dependency problem 转化成 source-control / large-scale-change problem。

这不是说 monorepo 总是更好。

而是：

> **Consumer visibility 是 change strategy 的一等输入。**

---

# 29. Migration plan 应该像 protocol

一个好的 migration plan 不应该写：

```text
先兼容一阵子，然后升级，最后删除旧代码。
```

而应该写成状态机。

例如 TaskForge：

```text
Phase E0
R1 only / W1 only

Phase E1
R2 deployed gradually
R2 reads v1+v2
all writers still W1

Exit criterion:
all processes that may read shared snapshots are R2+
rollback binary also R2-capable or v2 writes still disabled

Phase M
writer feature flag enables W2
historical v1 remains readable

Exit criterion:
no supported rollback target requires R1
all durable datasets inventoried/migrated as policy requires

Phase C
remove W1
later remove R1 if support policy allows
```

这才是 migration protocol。

---

# 30. 每个 phase 都必须 deployable

Parallel Change 的价值之一是：

```text
每一步都可以发布
```

也就是说：

```text
Expand state
```

不是半成品。

它应该是：

```text
production-safe transitional state
```

M05 的 staged change 在这里升级成：

```text
staged production compatibility
```

---

# 31. Reversibility 是 migration 设计指标

问每一步：

```text
如果这一阶段出事故，回退到哪里？
```

例如：

```text
R2 deployed, still W1
```

通常容易 rollback：

```text
R2 → R1
```

因为数据仍是 v1。

但：

```text
W2 already emitted v2
```

以后 rollback 可能需要：

```text
R1 cannot read state
```

所以 writer cutover 往往是一个比 reader rollout 更重的 irreversible boundary。

---

# 32. “Migration complete” 必须可证伪

不要定义：

```text
大家应该都升级了
```

应该定义：

```text
old reader process count = 0
old API call metric = 0 for N days
repo search = 0 supported usages
durable v1 objects = 0, if eager migration required
no rollback target older than version X
```

不同系统选不同 evidence。

但 criterion 必须可观察。

---

# 33. 什么时候保留 old reader 是合理的

不是所有 contract phase 都要删掉 old format support。

例如产品承诺：

```text
永久导入历史 project file
```

那么：

```text
old reader
```

就是产品功能，不是 migration debt。

区别是：

```text
intentional compatibility policy
```

vs.

```text
忘记删除的 transitional code
```

所以：

> **“旧代码存在”不是问题；没有明确 ownership 和 support policy 才是问题。**

---

# 34. 什么时候不要做 in-place migration

如果：

```text
semantic mapping 不可逆
数据量巨大
失败恢复复杂
旧新系统 ownership 完全不同
```

可能更适合：

```text
new store
shadow copy
validation
cutover
```

而不是：

```text
ALTER everything in place
```

但新 store 也会引入：

```text
dual state
sync
cutover
reconciliation
```

仍然要回到 M02：谁 authoritative？

---

# 35. Agent 最容易怎样把 migration 做坏

## 35.1 只实现 final schema

Prompt：

```text
把 snapshot 升级到 v2。
```

Agent 很容易：

```text
replace parser
replace writer
update tests
```

然后所有 current tests 都绿。

但 old data / old reader 全坏。

## 35.2 同时更新 fixture

Agent 看到 test fail：

```text
snapshot-v1.json no longer matches
```

于是把 historical fixture 改成 v2。

这等于删除了证据。

## 35.3 自动“宽容解析”

Agent 可能写：

```python
version = raw.get("schema_version", 1)
```

然后对 unknown structure 猜测。

结果 silent corruption。

## 35.4 dual-write without authority model

为了兼容：

```text
write old
write new
```

但没定义：

```text
第一步成功第二步失败怎么办？
谁 authoritative？
recovery 怎么做？
```

M07 的 partial failure 又回来了。

## 35.5 永久 compatibility branch

Agent 添加：

```python
if legacy:
```

却没有：

```text
removal condition
metric
owner
```

于是 transitional code 永久化。

---

# 36. 给 Agent 的 migration task contract

不要只说：

```text
Upgrade snapshot format to v2.
```

更好的 contract：

```text
目标：把 TaskForge snapshot 从 v1 flat command 演化到 v2 task object。

必须先只读：
- 找到所有 snapshot readers/writers/fixtures。
- 明确 historical v1 fixture 的 contract。
- 画 R1/R2 × W1/W2 compatibility matrix。

Phase 1 — Expand only:
- new reader must read v1 and v2；
- default writer MUST remain v1；
- frozen v1 reader must still accept default output；
- unknown future version must fail explicitly；
- do not modify historical v1 fixture。

Evidence:
- old fixture -> new reader PASS；
- new v2 fixture -> new reader PASS；
- default writer -> frozen v1 reader PASS；
- future version -> explicit rejection PASS。

Phase 2 is NOT part of this change:
- do not switch default writer to v2；
- do not remove v1 reader。

Deliver:
- compatibility matrix；
- exact writer cutover precondition；
- rollback analysis；
- changed files and tests。
```

这比“注意兼容性”强得多。

---

# 37. 为什么要把 writer cutover 单独一个 change

因为它改变的是：

```text
系统未来产生的数据 universe
```

reader expansion 只是增加能力：

```text
accept old + new
```

writer cutover 则可能让旧世界无法再运行。

所以这两个 diff 的风险完全不同。

应该独立 review。

---

# 38. M08 TaskForge lab 的目标

Starter 现在只有：

```text
R1 / W1
```

而需求是最终支持：

```text
v2:
command
  ↓
task: {
  kind: "shell",
  command: ...
}
```

但你第一阶段**不能直接切 W2**。

你需要完成：

```text
R2 reads v1 + v2
W1 remains default
```

并写 rollout plan。

这看起来不像“完成 feature”。

但它是一个完整、可部署、降低未来风险的 migration step。

---

# 39. Review checklist

面对 compatibility/migration PR，问：

### Surface

- 哪些 observable contracts 被改？
- source/wire/data/config/semantic 哪几层？

### Consumers

- consumers 是否全部可见？
- 是否能同步升级？
- 有离线/长期旧工具吗？

### Matrix

- old producer → new consumer？
- new producer → old consumer？
- rollback consumer → current data？

### Migration

- expand phase 是什么？
- writer 何时切？
- migration completion 怎样观测？
- contract 何时发生？

### Failure

- partial migration 怎么恢复？
- dual-write 是否 split authority？
- rollback 会不会遇到新格式？

### Evidence

- historical fixture 保留了吗？
- frozen old consumer 测了吗？
- future version failure 测了吗？
- compatibility test 是 matrix 还是 current-current roundtrip？

### Cleanup

- compatibility code 的 owner？
- removal criterion？
- 是否防止 backsliding？

---

# 40. 本章与前面模块的连接

M08 不是新主题岛。

它复用了前面的全部模型。

## M01 — Contract

```text
兼容什么？
```

没有 contract 就没有 compatibility。

## M02 — Ownership

```text
old/new stores dual-write 时谁 authoritative？
```

## M03 — Evidence

```text
historical fixture / frozen reader / compatibility matrix
```

都是 executable evidence。

## M04 — Boundary

```text
schema/config/API
```

都是 boundary contract。

## M05 — Evolution

```text
expand → migrate → contract
```

本质上是跨 release 的 staged change。

## M06 — Legacy

old format 往往就是你无法控制的 historical dependency。

## M07 — Failure

migration 和 dual-write 一旦 partial failure，就重新出现 crash window / retry / idempotency 问题。

---

# 41. 一句话模型

如果只记住一句：

> **Compatibility 不是“新版本是否正确”，而是“在你承诺的时间窗口里，哪些新旧 producer/consumer/数据组合必须继续正确”；Migration 则是把系统从这个兼容窗口安全地推进到新的稳定世界。**

---

# 42. 下一章预告

M09 会继续把视角拉高到 Architecture。

你已经拥有：

```text
contract
ownership
evidence
boundary
refactoring
legacy takeover
concurrency/failure
compatibility/migration
```

接下来要问：

> **哪些决定值得成为系统级 architecture boundary？哪些只是局部 implementation detail？**

TaskForge 会开始从“几个模块”升级成真正有：

```text
control flow
data flow
failure domain
authority boundary
persistence boundary
```

的系统设计问题。

---

# 43. 本章材料来源

逐项 source audit 见：

[`../reading-notes/m08-source-audit.md`](../reading-notes/m08-source-audit.md)

主干来源：

- Google AIP-180 — Backwards compatibility
  - https://google.aip.dev/180
- Semantic Versioning 2.0.0
  - https://semver.org/spec/v2.0.0.html
- Software Engineering at Google — Dependency Management
  - https://abseil.io/resources/swe-book/html/ch21.html
- Software Engineering at Google — Deprecation
  - https://abseil.io/resources/swe-book/html/ch15.html
- Martin Fowler / Danilo Sato — Parallel Change
  - https://martinfowler.com/bliki/ParallelChange.html
- Protocol Buffers — Updating a Message Type / Proto 3 guide
  - https://protobuf.dev/programming-guides/editions/#updating
  - https://protobuf.dev/programming-guides/proto3/
- Kubernetes Deprecation Policy
  - https://kubernetes.io/docs/reference/using-api/deprecation-policy/
