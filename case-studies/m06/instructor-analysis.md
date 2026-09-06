# M06 Instructor Reference — Legacy Audit Takeover

> Spoiler：建议先自己做 `labs/06-legacy-code-takeover.md`。

---

# 0. Instructor 结论

这个 lab 的关键答案不是某一种 architecture。

最重要的判断是：

> **当前 change 并不要求先把 clock / host / filesystem 全部抽成 production dependency interfaces。**

现有 Python substitution points（local name rebinding + shared-module attribute patch）、环境变量和 `tmp_path` 已经足够把 legacy behavior 放进稳定 test harness。

因此一个成熟的 reference path 可以是：

```text
read-only reconnaissance
→ black-box/module-level characterization
→ confirm tests have teeth
→ decide no new production seam is necessary yet
→ add the smallest behavior delta
→ preserve default fingerprints
```

这比为了“展示 seam”而制造一个 `AuditRuntime/Clock/FileSystem/HostProvider` object graph 更符合本课程目标。

---

# 1. Starter 的 dependency map

`legacy_audit.publish_daily_audit()` 的直接依赖：

```text
state.jobs                 semantic state
os.environ                 ambient runtime context
  TASKFORGE_AUDIT_DIR
  TASKFORGE_AUDIT_OWNER

datetime.now(timezone.utc) nondeterminism
socket.gethostname()       machine identity / nondeterminism
Path.mkdir/open             filesystem side effects
print                       stdout side effect
```

它还有一些隐含 assumptions：

```text
state.jobs preserves insertion order
JobStatus.value is stable text
commands are rendered verbatim
same-day audit should append
UTF-8 + LF are expected
```

这些并没有全部 written spec。

---

# 2. Sensing vs Separation

## clock

主要是 separation / determinism 问题。

我们不希望测试依赖真实时间。

## hostname

同样主要是 separation / determinism。

## filesystem

既有 separation 又有 sensing：

```text
separation:
不应写真实用户目录

sensing:
需要读取写出的 bytes
```

`tmp_path` 同时很好地解决两者。

## stdout

主要是 sensing。

不需要为此引入 `Logger` abstraction；`redirect_stdout` 已经足够。

## state.jobs

在这个小系统里，已有 `service.reset_for_tests()`、`submit()`、worker lifecycle 就足够控制 state。

如果这里再引入 repository interface，只是为了 M06 测试，会明显过度设计。

---

# 3. Starter Probe 为什么是合法的第一步

`m06_legacy_probe.py` 使用：

```python
legacy_audit.datetime = FrozenDateTime
legacy_audit.socket.gethostname = lambda: "lab-host"
```

这两行都利用了可替换 behavior 的 seam，但 Python mechanism 不同。

第一行是 **module-local name rebinding**：`legacy_audit.py` 用 `from datetime import datetime`，所以 test 只重新绑定 `legacy_audit` namespace 里的 `datetime` name。

第二行不是 local rebinding。`legacy_audit.py` 用 `import socket`，因此 `legacy_audit.socket` 和普通 `import socket` 得到的是同一个 module object。给 `legacy_audit.socket.gethostname` 赋值会修改共享 module attribute；patch 生效期间，进程里其他使用该 object 的代码也会看到 `"lab-host"`。Starter probe 在 `finally` 里恢复原 function，而且串行执行，所以这里把这种 process-wide mutation 当成一个有明确 isolation cost 的临时 test-harness seam，而不是推荐的通用测试 API。

它们的共同优点：

- 0 production diff；
- 快速把时间/hostname deterministic 化；
- 很适合第一次 takeover；
- 可以先确认 behavior 再决定 architecture。

它们的风险并不完全相同：

- local `datetime` rebinding 依赖 `legacy_audit` 的 import/binding shape；
- shared `socket.gethostname` patch 还带 process-wide interference/blast-radius 风险；
- `os.environ` 同样是 process-scoped state；
- 不应该把这些 harness control points 误认为稳定 public API；
- 如果大量/并行测试依赖 shared mutations，会更 brittle，也更难隔离。

所以课程的判断不是：

```text
monkeypatch good
```

而是：

> **它是否足以在当前阶段以最低成本建立 trustworthy feedback？**

这里答案是 yes。

---

# 4. Characterized behavior

当前 probe 实际锁住三组 file behavior。

## empty

观察到：

```text
== 2026-09-06T01:02:03Z lab-host owner=course-user ==
jobs=0
--
```

也就是说：

```text
no jobs
!=
no audit record
```

这可能很重要，因为空 audit 也可能表示“任务执行了，只是没有 job”。

不要擅自优化成“不写文件”。

## mixed

观察到：

```text
jobs=4
01 job-1 succeeded exit=0 :: true
02 job-2 failed    exit=7 :: false
03 job-3 cancelled exit=- :: sleep cancelled
04 job-4 queued    exit=- :: echo queued
```

这里暴露了多个 compatibility candidates：

- insertion order；
- two-digit numbering；
- fixed-width status padding；
- `exit=-`；
- `::` separator；
- command verbatim。

这不代表它们都应该永远保留，但在没有证据前不应顺便改。

## append

同一天第二次运行：

```text
first block
--
second block
--
```

而不是 overwrite。

这是这次 lab 中最值得保护的 effect-level behavior 之一。

---

# 5. Probe 的一个自我修正

最初 probe 直接 hash stdout。

但 stdout 包含：

```text
/tmp/taskforge-m06-<random>/...
```

因此每次 hash 不稳定。

修正为：

```text
replace actual scenario root with <ROOT>
→ then fingerprint
```

这是一个很小但重要的教学点：

> **测试工具自己的 nondeterminism 也可能污染 characterization。**

不要看到“golden/hash”就默认它稳定。

---

# 6. 是否需要新增 production seam？

Reference 决定：**暂时不需要。**

理由：

1. time/host 已经可通过 module seam 控制；
2. filesystem root 已经由 env 控制；
3. state 已经有现成 test setup surface；
4. stdout 可直接 capture；
5. 当前需求只改变 job selection policy。

如果现在加：

```text
AuditRuntime
ClockProtocol
HostProvider
FileSystem
EnvironmentReader
JobRepository
```

会让 production concepts 增加很多，但没有解决新的 current risk。

这是一个典型：

```text
we found seams
≠
we must formalize all seams
```

---

# 7. Reference Behavior Change

最小 reference diff 是：

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

重要的是 validation 放在 filesystem mutation 之前。

Default：

```text
publish_daily_audit()
```

仍然经过原 path。

---

# 8. 为什么不先 Extract `_select_jobs()`

这是一个可接受方案，但 reference 不认为它是必要条件。

你当然可以写：

```python
def _select_jobs(scope, jobs):
    ...
```

好处：

- pure；
- focused test 容易；
- selection policy 更明显。

但当前逻辑只有：

```python
if scope == "failed":
    jobs = [job for job in jobs if job.status == JobStatus.FAILED]
```

抽 helper 可能只是提前制造一个 abstraction。

如果后续 scope 扩大成：

```text
failed
terminal
active
since timestamp
owner filter
```

再提炼 selection abstraction 更合理。

这体现 M05 的 evolutionary design：

> **让当前 pressure 决定 abstraction 的深度。**

---

# 9. Reference Feature Tests

Reference 在临时副本中增加三条 focused tests。

## failed-only

构造：

```text
job-1 succeeded
job-2 failed 7
job-3 failed 9
job-4 queued
```

检查：

```text
jobs=2
01 job-2 failed ...
02 job-3 failed ...
job-1 absent
job-4 absent
stdout says wrote 2
```

这同时验证：

```text
selection
relative ordering
renumbering
count
stdout
```

## invalid scope

```text
scope=banana
→ ValueError
→ tmp output dir remains empty
```

这复用 M04 no-effect-on-rejection。

## default scope

```text
no scope arg
→ all 4 jobs remain
```

---

# 10. Reference 实际验证

临时 reference implementation 实际运行：

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

因此：

```text
old core tests:       6
new M06 feature tests:3
-----------------------
total:                9
```

同时 default file characterization fingerprint 保持不变。

---

# 11. 一个测试夹具错误，以及为什么值得记录

第一次写 reference fixture 时，顺序是：

```text
succeeded
failed-1
queued
failed-2
```

然后调用：

```python
worker.claim_next()
worker.finish(failed_2, 9)
```

这失败了，因为 FIFO `claim_next()` 合法地 claim 了前面的 queued job，`failed_2` 仍然是 QUEUED。

错误是：

```text
ValueError: cannot finish job-4 from queued
```

Reference 没有为了快速通过而：

```python
state.jobs[bad2].status = RUNNING
```

因为这会绕过 M02/M01 建立的 lifecycle semantics。

正确修复是调整 test setup 顺序：

```text
succeeded
failed-1
failed-2
queued
```

这个插曲很有教学价值：

> **legacy takeover 的测试代码同样必须服从已有 contract；test fixture 不是可以随意作弊的世界。**

---

# 12. Characterization 与 Feature Test 的角色不同

Reference 保留两组 evidence：

```text
m06_legacy_probe.py
→ broad current-behavior characterization

focused pytest tests
→ new failed-only specification
```

不要把两组混成一个 giant golden test。

原因：

```text
characterization answers:
what did the old thing do?

feature tests answer:
what must the new capability do?
```

这对 review 非常重要。

---

# 13. 如果学生选择正式打开 Seam，什么算合理？

也可以接受：

```python
@dataclass(frozen=True)
class AuditContext:
    now: datetime
    hostname: str
```

并由一个 private helper：

```python
_build_context()
```

在 production 入口创建。

但必须证明：

- default bytes 不变；
- public API 没被不必要扩大；
- context abstraction 确实降低当前测试成本；
- 没有继续抽象 `Environment/FileSystem/StateRepository` 只是为了对称。

---

# 14. 什么方案应该扣分

## 14.1 先把整个 module rewrite 成 classes

例如：

```text
AuditService
AuditRepository
AuditFormatter
Clock
HostProvider
FileWriter
OutputSink
```

如果没有证据证明这些边界必要，属于 speculative architecture。

## 14.2 改格式“顺便 clean up”

例如：

```text
pipe/spacing/newline 改掉
```

却没有 compatibility decision。

## 14.3 Tests 全部 assert mock calls

例如：

```text
writer.append called once
clock.now called once
```

但不检查最终 file semantics。

这会降低 fidelity。

## 14.4 直接改 state

为了方便 fixture：

```python
state.jobs[id].status = FAILED
```

会绕过真实 lifecycle，削弱测试可信度。

## 14.5 Characterization 后认为所有旧行为永远不可改

这同样错误。

Characterization 是：

```text
make change explicit
```

不是：

```text
freeze history forever
```

---

# 15. Agent Review 的理想输出

一个高质量 Agent review 应该类似：

```text
Contract: default scope has no intended behavior change;
existing default behavior remains the exercise-local preservation obligation.
Evidence: the characterized empty/mixed/append scenarios still match their baseline,
and the requested delta is limited to job selection.
Existing harness control points are sufficient for deterministic tests,
so the patch does not introduce a new dependency framework.
Invalid scope is rejected before mkdir/open.
Remaining risk: uncharacterized inputs, error paths, stdout consumers, and external parsers
mean the broad preservation obligation is not fully proved; they are not out of contract.
```

而不是：

```text
Code looks cleaner and tests pass.
```

---

# 16. 本 Lab 最重要的答案

不是：

```text
always add seams
```

而是：

> **先找到足够便宜的反馈路径；只有当现有结构阻止你获得可信反馈时，才为当前 change 打开最小 seam。**

这就是 M06 想建立的 judgment。
