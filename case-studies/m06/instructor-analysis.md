# M06 Instructor Reference — Legacy Audit Takeover

> **Spoiler warning**：完成 [`../../labs/06-legacy-code-takeover.md`](../../labs/06-legacy-code-takeover.md) 前不要读。
>
> 这不是唯一正确 architecture。它记录一条 instructor reference：在旧行为不完全清楚、环境依赖很多的模块里，怎样先获得 trustworthy feedback，再判断当前 change 是否真的需要新的 production seam。来源与 course-synthesis 边界见 [`../../reading-notes/m06-source-audit.md`](../../reading-notes/m06-source-audit.md)。

M06 的 feature request 很小：`publish_daily_audit()` 增加一个 failed-only scope。真正让 change 变难的不是过滤条件，而是我们必须先回答：默认 audit 当前到底写什么、依赖哪些环境、怎样稳定重放，以及“保持旧行为”到底有哪些 evidence。

因此 reference 不从 `ClockProtocol`、repository interface 或 class redesign 开始。它先把现有 module 放进一个能重复运行、能观察真实 file/stdout semantics 的 feedback loop；只有在这条 loop 建立以后，才判断是否值得改变 production structure。

## 1. 第一步是恢复 effect surface，而不是先把它“设计正确”

`legacy_audit.publish_daily_audit()` 直接依赖：

```text
state.jobs
os.environ: TASKFORGE_AUDIT_DIR / TASKFORGE_AUDIT_OWNER
datetime.now(timezone.utc)
socket.gethostname()
Path.mkdir/open
stdout print
```

代码还隐含依赖 insertion order、`JobStatus.value` textual form、command verbatim rendering、same-day append、UTF-8/LF 等行为。它们并没有全部写成长期 product spec，但 Lab 已经给出一个本地 change contract：`scope="all"` 没有 intended behavior change，existing default behavior 是这次 exercise 的 broad preservation obligation；ordering、file naming、append、formatting 又是特别点名的高风险 surfaces。

这层 authority 很容易被写错。Characterization 只能告诉我们“当前受控 experiment 观察到了什么”，不能把未观测行为从 preservation obligation 中删除；反过来，观察到一个 historical quirk 也不自动把它升级成永久产品 promise。

## 2. Starter probe 先把真实行为和 harness limitation一起暴露出来

`m06_legacy_probe.py` 不修改 production code。它控制 audit directory/owner、冻结时间、固定 hostname、capture stdout，然后重放 empty / mixed / append 三个 scenarios。

这里有一个值得精确区分的 Python detail。Probe 中：

```python
legacy_audit.datetime = FrozenDateTime
legacy_audit.socket.gethostname = lambda: "lab-host"
```

第一行是 **module-local name rebinding**：`legacy_audit.py` 使用 `from datetime import datetime`，所以只替换该 module namespace 的 `datetime` binding。

第二行不同。`legacy_audit.py` 使用 `import socket`，`legacy_audit.socket` 与普通 `import socket` 指向同一个 module object；修改 `legacy_audit.socket.gethostname` 会让同一进程其他持有该 module object 的代码也看到替代 function。Starter probe 串行运行并在 `finally` 中恢复 original function，所以 reference 接受它作为 temporary harness control point，但明确记录 process-wide interference / parallel-test risk。`os.environ` 同样是 process-scoped state。

这两种 mechanism 都能帮助我们控制 nondeterminism，却不能因为“都能 monkeypatch”就被描述成同一种 stable public seam。

### Empty audit：没有 jobs 也会写 record

Probe 观察：

```text
== 2026-09-06T01:02:03Z lab-host owner=course-user ==
jobs=0
--
```

因此 `no jobs != no audit record`。在当前 preservation obligation 下，不能因为“空文件似乎没意义”就顺手优化成 skip write。

### Mixed audit：format 与 ordering 都暴露出来

```text
jobs=4
01 job-1 succeeded exit=0 :: true
02 job-2 failed    exit=7 :: false
03 job-3 cancelled exit=- :: sleep cancelled
04 job-4 queued    exit=- :: echo queued
```

这个 observation 把 insertion order、two-digit numbering、status padding、`exit=-`、separator、command verbatim 等 concrete old values变得可检查。它们是当前 evidence 覆盖到的 compatibility candidates；哪一项将来能改，需要新的 behavior decision，而不是由 characterization 自己决定。

### Append：effect semantics 跨 invocation 延续

同一天第二次 publish 会 append 第二个 block，而不是 overwrite。对于这次 change，这是很值得保护的 effect-level behavior。

Probe 自己也曾犯过一次错误：最初直接 fingerprint stdout，但 stdout 含 randomized temp path，导致 hash 每次变化。后来先把实际 scenario root normalize 成 `<ROOT>` 再 fingerprint。这个修正说明 **harness 的 nondeterminism 也会污染 characterization**；看到 golden/hash 不能自动推断 oracle 稳定。

## 3. 这时才需要区分 sensing、separation 与 seam

前面的 pressure 其实有两类。

- Clock / hostname 主要阻止 deterministic execution：这是 separation/control 问题。
- Filesystem 同时需要 separation 与 sensing：不能写真实用户目录，但又必须读取最终 bytes。
- Stdout 主要是 sensing：代码能运行，只是需要可靠观察输出。
- `state.jobs` 已经可以通过 `service.reset_for_tests()`、submit 和 worker lifecycle 构造，不需要为了测试再复制一套 repository state。

Starter 已经有足够 control/observation points：local name rebinding、shared-module attribute patch、environment variable、temp directory、stdout capture。用 Feathers 的术语看，它们提供了 seam / enabling-point opportunities；关键不是它们有没有 `IClock` 或 DI framework，而是能否以当前可接受的成本改变某处 behavior，让 change 进入 feedback loop。

这个判断随后带来 reference 最重要的 design choice：**发现 seam 不等于必须 formalize production seam。**

## 4. Reference 比较了三个方向，最后选择暂时不改 production structure

一个最激进 candidate 是引入：

```text
AuditRuntime
ClockProtocol
HostProvider
FileSystem
EnvironmentReader
JobRepository
```

它当然能让 dependency 更显式，但当前 feature 只改变 job selection policy；existing harness 已经能控制 time/host/filesystem/state/stdout。新增一整套 provider graph 会增加 production concepts，却没有关闭新的 current risk。

另一条中间路线是一个很小的 runtime context，例如：

```python
@dataclass(frozen=True)
class AuditContext:
    now: datetime
    hostname: str
```

由 private `_build_context()` 在 production entry 创建。如果某个 candidate 证明这能显著降低当前 test cost，同时保持 default bytes/public API，并且不继续为 symmetry 抽象 Environment/FileSystem/StateRepository，这条路线也完全可以接受。

Instructor reference 选择第三条：**当前不新增 production seam**。理由不是“DI 不好”，而是 current control points 已经足以提供 feedback。以后如果 parallel tests、binding brittleness、process isolation 或更多 runtime-dependent behavior 让现有 harness 成本上升，再 formalize 更稳定的 boundary 可能更合理。

同理，提前抽 `_select_jobs()` 也不是必要条件。当前只有一个 `if scope == "failed"` filter；pure helper 可以让 focused test 更直接，但也可能只是为一行 policy 提前制造 abstraction。等 selection 扩展到 terminal/active/time/owner 等多个维度时，它的收益会更明显。

## 5. Feedback loop 建立后，feature delta 才值得进入代码

Reference behavior change 很小：

```python
from taskforge.model import JobStatus


def publish_daily_audit(scope: str = "all") -> str:
    if scope not in {"all", "failed"}:
        raise ValueError(...)

    ...
    jobs = list(state.jobs.values())
    if scope == "failed":
        jobs = [job for job in jobs if job.status == JobStatus.FAILED]
    ...
```

Validation 必须发生在 `mkdir/open` 等 filesystem mutation 之前。这个 no-effect-on-invalid-input obligation来自当前 M06 feature contract，并复用 M04 的 boundary reasoning；它不意味着“所有 errors 都保证 no side effect”。

默认 `publish_daily_audit()` 仍走原来的 all-jobs behavior。Reference focused tests 只为新增 semantics 建 oracle：

- failed-only：从 succeeded / failed 7 / failed 9 / queued 中只输出两个 failed jobs，并保持它们的 relative order；输出重新编号 01/02，count 与 stdout write count 对齐；
- invalid scope：`banana -> ValueError`，并且 output directory 仍为空；
- default scope：不传参数仍包含原来四类 jobs。

Feature tests 的 authority 与 characterization 不同：前者回答“新 capability 必须做什么”，后者回答“旧系统在受控 scenario 中实际做什么”。把两者合成一个 giant golden 会模糊 observed fact 与 desired behavior 的来源。

## 6. Test fixture 自己也必须服从旧 lifecycle contract

Reference 第一次构造 failed-only fixture 时，顺序曾是：

```text
succeeded
failed-1
queued
failed-2
```

随后直接调用 `worker.claim_next()` 再 `worker.finish(failed_2, 9)`，结果失败：FIFO 合法地先 claim 了排在前面的 queued job，`failed_2` 仍是 `QUEUED`。

Reference 没有为了方便直接写：

```python
state.jobs[failed_2].status = RUNNING
```

那会让测试绕过 M01/M02 已建立的 lifecycle authority。正确修复只是调整 setup order，让 `failed-2` 在 queued survivor 之前进入 claim path。

这个小事故很有价值：**test fixture 不是可以为了制造 expected state 而随意作弊的平行世界。** Characterization / feature evidence 的可信度依赖 setup 是否走真实 contract。

## 7. Reference evidence：旧 behavior保持，新 delta 单独得到证明

临时 reference implementation 实际记录：

```text
-- legacy characterization after change --
[OK] empty
[OK] mixed
[OK] append
legacy audit characterization probe passed

-- full tests --
.........
9 passed
```

即原 core 6 tests + M06 3 focused feature tests。Default characterization fingerprints 保持不变。

不过 evidence scope 必须继续说窄：current probe 只证明它实际 assert/observe 的 empty/mixed/append surfaces；printed hash 也不应被夸成一个它代码中没有 assert 的 exact-byte oracle。**Broad default-preservation obligation 大于当前 characterization coverage。** 未 characterize input/error/consumer behavior 是 `unproved / remaining risk`，不是因此变成 out-of-contract。

Characterization 也不表示“旧行为永远不可改”。若后续 owner 决定某个 formatting quirk 是 bug，可以显式建立新 behavior contract，然后有意识更新/替换旧 characterization evidence。它的作用是让 change 显式，而不是冻结历史。

## 8. 哪些 takeover path 看起来积极，实际上会降低证据质量

**一次把 module rewrite 成 classes**：`AuditService / AuditRepository / AuditFormatter / Clock / HostProvider / FileWriter / OutputSink` 如果没有当前 pressure 支撑，只是 speculative architecture，反而扩大 reviewer 必须理解的 surface。

**顺手 clean up output format**：spacing/newline/separator 改动即使更美观，也是 behavior/compatibility change；不能藏在 failed-only feature 中。

**全部 assert mock calls**：`writer.append called once`、`clock.now called once` 可能让 test deterministic，却不验证真正 file bytes / append semantics，fidelity 反而下降。External effect 不等于必须 mock；应为当前 risk 选择 minimum sufficient fidelity。

**直接 mutation `state.jobs` 构造 fixture**：会绕过 lifecycle owner，让 test 描述一个 production path 根本不会产生的 state history。

**把 characterized surface 偷换成 preservation contract 全集**：这是本章最危险的 evidence-authority drift。`scope="all"` 的 broad existing-behavior preservation来自 Lab；probe 只决定当前证明到哪里。

## 9. Agent 接管 legacy code 时，最重要的是允许“不新增 abstraction”成为正确答案

模糊任务 “make this legacy module testable and clean” 很容易让 Agent 同时新增 interfaces、dependency container、DTOs、exceptions、test helpers 和 behavior。实现量很大，却把 understanding / feedback / structure / feature 四种 proof obligations 混在一个 diff。

更好的 workflow 是：先做 read-only dependency/effect sketch；运行 probe并记录 observed behavior；明确 broad preservation obligation 与 current evidence coverage；判断当前问题是 sensing 还是 separation；只有 existing control point 不足时才授权最小 structural seam；随后实现 requested delta，再让 separate review 检查 evidence 与 remaining unknowns。

一个高质量 review 可以明确说：default scope 没有 intended behavior change；current characterization 只覆盖 empty/mixed/append，但 broad exercise-local preservation obligation仍成立；existing harness control points 足够 deterministic，因此本 patch 不需要新 dependency framework；invalid scope 在 filesystem mutation 前拒绝；uncharacterized inputs/error paths/stdout consumers/external parsers 仍是 remaining risk，而不是 out-of-contract。

## 10. Instructor judgment

M06 的 reference 结论最终是：**当前 change 不要求先把 clock / host / filesystem 全部抽成 production dependency interfaces。** 但这句话只有在前面的 evidence 恢复之后才有 authority：现有 Python control points + env + tempdir + stdout capture 已足以建立可信 feedback，而新增 provider graph没有关闭当前新增风险。

本 Lab 真正训练的是一个更稳定的判断：先找到足够便宜、足够可信的 feedback path；只有当当前结构阻止你观察/控制这次 change 所需的行为时，才为它打开最小 seam。Agent 可以很快制造 abstraction，但**是否需要 abstraction**仍应由 change pressure、evidence quality、fidelity 与 maintenance cost决定。M07 会在这个 feedback foundation 上再加入 concurrency、crash、retry 等 temporal pressure；M06 不提前替它建立那套 execution model。
