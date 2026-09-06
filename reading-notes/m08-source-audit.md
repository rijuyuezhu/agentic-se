# M08 Source Audit — Dependency、Compatibility 与 Migration

> 目标：确认哪些材料真的支持“软件变化必须跨越新旧版本共存窗口”这一章的核心判断。
>
> 本模块不把 Semantic Versioning、API versioning 或 database migration pattern 当作仪式。所有规则都必须回答：**谁和谁需要同时工作多久，失败时能否回退，旧数据/旧客户端/旧依赖会发生什么？**

---

# 0. 本模块要回答的问题

M08 关注六个问题：

1. compatibility 到底兼容什么：source、binary/wire、serialized data、config、behavior，还是 performance？
2. provider 和 consumer 谁能被同步升级，谁是未知或不可控的？
3. 为什么“新版本测试全绿”仍可能是 breaking change？
4. 一个 breaking contract 怎样拆成 expand → migrate → contract？
5. durable data 为什么比普通函数调用更难迁移？
6. version number、deprecation warning、migration script 各自到底能证明什么，不能证明什么？

需要主动拒绝这些口号：

- “major version bump 了，所以 breaking change 就没问题”；
- “JSON 多一个字段肯定 backward compatible”；
- “数据库 schema 一次性改完然后同时发布所有服务”；
- “reader 永远应该忽略所有未知内容”；
- “只要新代码能读旧数据，migration 就完成了”；
- “依赖 pin 住就永远不用升级”。

---

# 1. Google AIP-180 — Backwards compatibility

**状态：主干采用（compatibility dimensions）**

原文：

- https://google.aip.dev/180

## 实际检查内容

AIP-180 明确区分：

1. source compatibility；
2. wire compatibility；
3. semantic compatibility。

它同时明确说明：旧 client 应能在同一 major version 下继续与新 server 工作，但 compatibility 判断并不总是机械的，尤其 semantic compatibility 需要工程判断。

## 本课程采用什么

这是 M08 最重要的 vocabulary source 之一。

例如函数签名完全不变：

```text
list_jobs() -> list[Job]
```

但如果排序从 FIFO 改成随机：

```text
source compatible   yes
wire compatible     maybe
semantic compatible maybe no
```

所以：

> **“能编译/能 parse”只是 compatibility 的一层。**

## 限制

AIP-180 主要面向网络 API，并假设 protobuf/JSON 等典型 transport。

本课程把它的三维模型推广到：

- Python library；
- CLI/config；
- file format；
- database rows；
- internal RPC。

这是课程综合，不是假装 AIP 原文覆盖所有这些系统。

---

# 2. Semantic Versioning 2.0.0

**状态：采用，但明确降级为 communication protocol，而非 correctness mechanism**

规范：

- https://semver.org/spec/v2.0.0.html

## 实际检查内容

规范首先要求：使用 SemVer 的软件必须声明 public API。

之后才定义：

```text
MAJOR.MINOR.PATCH
```

及其变化含义。

这意味着一个经常被忽略的前提是：

> 如果你根本说不清 public API 是什么，版本号无法替你判断 breaking change。

## 本课程采用什么

SemVer 用于：

```text
provider 对 consumer 传递兼容风险意图
```

而不是：

```text
证明这个 release 真 compatible
```

例如作者认为某个 ordering change 是 patch，但未知用户正依赖 ordering：

```text
1.2.3 → 1.2.4
```

并不会神奇地让 change 变 compatible。

## 与 Software Engineering at Google 的校正

SE at Google Dependency Management 章节把 SemVer 描述得非常谨慎：dependency management 本质上涉及跨组织、低可见性的长期 contract；它甚至把 SemVer概括成一种对 change risk 的 lossy shorthand，而不是完整解决方案。

所以本课不会教：

```text
SemVer rules memorized
=> dependency management solved
```

---

# 3. Software Engineering at Google — Dependency Management

**状态：主干采用（dependency as time-varying contract / visibility problem）**

正文：

- https://abseil.io/resources/swe-book/html/ch21.html

## 实际检查内容

实际检查了：

- dependency management 与 source-control problem 的区别；
- dependency network，而不是单个 package；
- diamond/conflicting requirements；
- compatibility promises；
- SemVer limitations；
- Live at Head 的适用前提；
- provider/consumer visibility 对 change 成本的影响。

## 最重要的课程结论

### 1. dependency 不是一次性下载动作

引入 dependency 意味着建立一个长期关系：

```text
今天可用
+
未来安全升级
+
平台变化
+
安全修复
+
transitive dependencies
```

### 2. visibility 决定 change strategy

如果 provider 能看到所有 consumers：

```text
repo-wide search
CI
large-scale change
```

可以直接迁移 consumer。

如果 consumers 在未知组织：

```text
compatibility promise
versioning
deprecation window
migration guide
```

就重要得多。

### 3. dependency graph 是 network

只看：

```text
my app -> library A
```

容易忽略：

```text
my app
 ├─ A -> C@1
 └─ B -> C@2
```

所以 dependency update 的真实对象往往是 constraint network。

## 限制

Google 的 monorepo、code-index、CI 与 organizational control 很特殊。

`Live at Head` 不能直接推广成所有 OSS/企业项目的默认答案。

本课程采用它的 reasoning model，而不是照搬组织策略。

---

# 4. Software Engineering at Google — Deprecation

**状态：主干采用（migration 必须有 owner、milestone、anti-backsliding）**

正文：

- https://abseil.io/resources/swe-book/html/ch15.html

## 实际检查内容

实际检查：

- advisory vs compulsory deprecation；
- 为什么 warning 本身不会自动完成 migration；
- explicit process owner；
- incremental milestones；
- preventing backsliding；
- unknown dependents / Hyrum's Law 对 removal 的影响。

## 本课程采用什么

一个真正可结束的 migration 至少需要：

```text
replacement exists
owner exists
consumer inventory exists or bounded
migration progress measurable
new old-use prevented
removal criterion explicit
```

否则：

```text
@deprecated
```

可能只是永久增加了一条 warning。

这对应 expand-contract 的最后一步，但需要一个 durable-data qualifier：**transitional compatibility burden 必须有明确的 contract/removal decision。** 如果产品明确承诺永久导入历史格式，old reader 可以成为长期 compatibility feature；此时需要结束的是未被 policy 授权的过渡路径，而不是为了套 pattern 把所有 old-format support 删除。

---

# 5. Martin Fowler / Danilo Sato — Parallel Change

**状态：主干采用（expand → migrate → contract）**

原文：

- https://martinfowler.com/bliki/ParallelChange.html

## 实际检查内容

正文明确把 backward-incompatible interface change 拆成三阶段：

```text
Expand: supplier/interface 同时支持 old + new form
Migrate: 把 clients/usages 从 old 逐步迁到 new
Contract: 所有 usages 迁完后删除 old form
```

文章还明确讨论 Published Interface、external clients、database refactoring、remote API evolution、continuous delivery，以及 migrate period 同时维护两种形式的成本。这里的 **Migrate 主体是 clients/usages**；原文没有把“durable producer 开始默认写新格式”重新命名成 Migrate。原文还明确写到：在 migrate phase，可以用 **Feature Flag** 控制使用 old/new interface；这是 activation/decoupling mechanism，不等于 compatibility proof。

## 本课程采用什么

M08 不会只把它用于 function rename。API field、config、database column、serialized file、RPC/worker rollout 都可以借它思考 old/new coexistence；但不同 surface 的 concrete mechanism 不同，课程不会机械规定 dual-read 或 dual-write。

对于 TaskForge durable snapshot，本课程**额外**把 producer writer cutover 单独列成 operational event：

```text
Expand capability
-> Migrate readers/consumers
-> Writer cutover
-> Contract/cleanup
```

这不是把 Fowler 的三阶段改成四阶段 source taxonomy。TaskForge 的 E/M/W/C 是受 Parallel Change 启发的 durable-data adaptation：第一步实际扩大的是 **reader/consumer capability**，因此 source 中 supplier/client 的角色与 TaskForge producer/reader deployment roles **不要求一一同构**；课程保留原文 `Migrate clients` 的含义，同时把 durable producer 开始生成 W2 这一不同 rollback boundary 单独显式化。

---

# 6. Protocol Buffers — Updating a Message Type

**状态：主干采用（wire compatibility 是具体 encoding contract）**

正文：

- https://protobuf.dev/programming-guides/editions/#updating
- https://protobuf.dev/programming-guides/proto3/

## 实际检查内容

官方文档明确说明 binary wire format 下哪些 changes safe/unsafe，并特别强调：

```text
field number identifies a field on the wire
```

因此已有 field number 不能随意改变，也不应该复用删除字段的 number；删除后应 reserve number，JSON/TextFormat 场景还应考虑 field name。

## 为什么这对 M08 重要

例如：

```text
source code:
name -> display_name
```

看起来只是 rename。

但 wire representation 的 identity 可能根本不是 source identifier，而是 field number。

反过来 JSON 的 compatibility 规则又与 protobuf binary 不完全相同。

因此：

> **“这个 schema change 是否安全”不能脱离实际 representation。**

## 限制

TaskForge M08 使用 JSON，不使用 protobuf。

Proto 只作为一个高质量反例：serialization semantics 是协议本身的一部分。

---

# 7. Kubernetes Deprecation Policy

**状态：主干采用（overlap window / storage compatibility / rollback）**

正文：

- https://kubernetes.io/docs/reference/using-api/deprecation-policy/

## 实际检查内容

Kubernetes 对 API version 演化有几个特别适合 M08 的要求，而且这几条已直接对照现行 policy 原文核过：

- API element 不能在同一 version 内随意删除或显著改变；
- persisted storage 中出现过的 API representation 不能因为 serving endpoint 下线就变得无法 decode/convert；
- preferred/storage version 向前推进前，应先有 release 同时支持 new 与 previous version；
- policy 明确要求用户能够 upgrade 到新 release 后再 rollback，而不需要先把数据转换成 new API version（显式使用 newer-only feature 的情况除外）。

## 本课程采用什么

最重要的不是 Kubernetes 的具体版本期限，而是这个 rollout invariant：

```text
先部署能读新旧格式的 reader
      ↓
确认 fleet 足够新
      ↓
再切 writer 到新格式
```

如果顺序反过来：

```text
new writer first
      ↓
old reader encounters new durable data
      ↓
breakage / rollback failure
```

这会直接成为 TaskForge M08 lab。

## 限制

Kubernetes 是大型分布式 API server，拥有复杂 conversion/storage machinery。

本课程只借用 overlap/rollback reasoning，不要求学生复制 Kubernetes version machinery。

---

# 8. 本模块的课程综合

综合上述材料，M08 使用下面的 compatibility model：

```text
Compatibility =
    surface
  × producer version
  × consumer version
  × direction
  × time window
  × semantic expectation
```

例如一句：

```text
“v2 backward compatible”
```

信息是不够的。

至少应该问：

```text
new reader reads old data?
old reader reads new data?
old client calls new server?
new client calls old server?
rollback after new writes?
semantic behavior preserved?
```

这套矩阵是本课程综合，不是某个 source 的原始 taxonomy。TaskForge 的四个 operational events（capability expansion、reader/consumer migration、writer cutover、contract/cleanup）也属于课程综合；其中只有 `Expand → Migrate clients → Contract` 三阶段 interface pattern 直接来自 Parallel Change。

---

# 9. M08 的 source policy

## 主干采用

- AIP-180：source / wire / semantic compatibility；
- SemVer 2.0.0：版本声明 contract，但不作为证明；
- SE at Google Dependency Management：dependency network、time、visibility；
- SE at Google Deprecation：owner/milestone/backsliding；
- Parallel Change：supplier Expand → migrate clients/usages → contract old interface，并明确提到 migrate phase 可用 Feature Flag 控制 old/new interface；TaskForge 的 reader-capability expansion / reader migration / writer cutover / cleanup 是课程适配，角色不要求一一同构；
- Protocol Buffers：具体 wire representation 规则；
- Kubernetes Deprecation Policy：old/new overlap、storage decode、rollback reasoning。

## 明确不升级为定律

- “所有 API 都必须 SemVer”；
- “所有 migration 都必须 dual-write”；
- “reader 应无限 tolerant”；
- “永远保留旧 schema”；
- “major bump 后可以不提供 migration path”；
- “数据库/API/file format version 越多越专业”。

M08 的目标不是兼容一切。

目标是：

> **明确选择 compatibility contract，并设计一个可以从 old world 走到 new world、同时知道何时能安全删除旧世界的 migration path。**
