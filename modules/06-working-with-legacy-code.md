# M06 — Legacy Code：先建立 Feedback，再谈改进设计

M05 结束时，我们已经有了一条相当舒服的 change discipline：先说清楚 must-preserve behavior，再把 structural change 与 behavior change 分开，用匹配的 evidence 守住每个 checkpoint。

现在把最关键的前提拿掉。

你收到 TaskForge 的一个旧模块 `legacy_audit.py`。需求已经明确两件事：增加 `failed-only` scope；默认 scope 必须保持现有行为，而且 ordering、file naming、append 和 formatting semantics 不能被顺手改变。代码只有几十行，看起来甚至比 M05 的 dashboard 更容易改。但没有人先告诉你这些“现有 semantics”具体是什么，现有六个 core tests 也完全不覆盖这个模块。你知道 preservation obligation，却还没有足够 evidence 描述被 preservation 的对象。

这就是 M06 的问题：**当你需要改变一个系统，却还没有足够可信的 feedback 时，怎样先获得修改资格，再开始修改。**

## 1. 先别重构：你还不知道什么叫“没改坏”

先看当前实现的核心形状：

```python
def publish_daily_audit() -> str:
    root = Path(os.environ.get("TASKFORGE_AUDIT_DIR", ".taskforge-audit"))
    owner = os.environ.get("TASKFORGE_AUDIT_OWNER", "unknown")
    now = datetime.now(timezone.utc)
    hostname = socket.gethostname()
    jobs = list(state.jobs.values())

    root.mkdir(parents=True, exist_ok=True)
    path = root / f"audit-{now:%Y-%m-%d}.log"
    ...
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(block)

    print(f"audit: wrote {len(jobs)} job(s) -> {path}")
    return str(path)
```

它同时接触 process environment、时钟、hostname、filesystem、stdout 和 TaskForge 的 global state。一个常见反应是：依赖太乱了，先抽 `Clock`、`FileSystem`、`AuditRepository`，把它“变得可测试”，然后再加 scope。

问题在于，你此刻并不知道哪些怪异细节已经被依赖。空状态会不会仍然创建文件？文件名用 local date 还是 UTC date？同一天调用两次是 overwrite 还是 append？status 是否固定宽度？`exit_code=None` 怎样表示？stdout 是否被 operator script 读取？甚至 `owner=unknown` 这个看起来很随意的默认值，也可能已经出现在外部 workflow 里。

如果在回答这些问题前先重写结构，之后即使 tests 全绿，也很难判断你保存的是旧行为、自己猜出来的行为，还是重写以后才产生的新行为。

这让 M05 的第一步发生了变化。M05 已经有 exact dashboard text probe，所以可以直接写 `must preserve: current dashboard text bytes`。M06 的 issue 虽然告诉你要保持 ordering / file naming / append / formatting，却没有给出这些旧语义的完整 concrete value。此刻更诚实的记录是：

```text
must preserve: existing ordering / file naming / append / formatting semantics
unknown: what are those existing semantics under the scenarios relevant to this change?
```

preservation requirement 和 old-behavior knowledge 是两个不同维度。`UNKNOWN` 不是工作没做完的羞耻标记，而是当前 engineering model 的真实状态。

## 2. 第一次运行：把猜测变成观察，但别急着把观察写成 contract

课程提供了一个 starter probe：

```bash
cd labs/taskforge
PYTHONPATH=src uv run --with pytest --no-project python tools/m06_legacy_probe.py
```

当前 baseline 实际输出如下。工具自己的最后一行把它叫作 `characterization probe`；这里先把这个名字当工具标签，后面再解释 characterization 的认识论位置。

```text
[OK] empty:  file_sha256=7e90999a594bd448 stdout_sha256=d114f9f2994a6701
[OK] mixed:  file_sha256=7821f1fa9ec08dd4 stdout_sha256=3fd157cf98872494
[OK] append: file_sha256=4e15e48d03660f50 stdout_sha256=de715a35f8db4b21
legacy audit characterization probe passed
```

三个场景马上回答了一些静态阅读不够可靠的问题。

空 state 仍然产生一个 audit block：

```text
== 2026-09-06T01:02:03Z lab-host owner=course-user ==
jobs=0
--
```

mixed state 会按当前 job 顺序输出，并把 status、exit code 和 command 拼进固定格式。same-day second invocation 会把第二个 block append 到同一文件，而不是覆盖第一个。

但要小心这里的认识论位置。**observed behavior 不等于 intended product contract。** 你已经有证据说“在这个受控实验里，当前实现表现为 X”；对于 issue 点名要求 preserve 的维度，这个 observation 现在帮助具体化本次 lab 的 local preservation contract，但它仍不能证明 X 是产品应永久承诺的最佳语义。

这一区分会贯穿整章。可以给 behavior inventory 多加一列 authority：

| Behavior | Current observation | Existing authority | 当前处理 |
|---|---|---|---|
| empty state 仍写 block | yes | general `default scope must preserve existing behavior` clause | 本次 change 的 must-preserve observation |
| same-day second run append | yes | issue 明确要求 preserve existing append semantics | 本次 change 的 must-preserve |
| job order follows current state order | yes | issue 明确要求 preserve existing ordering | 本次 change 的 must-preserve |
| `exit=None` renders `-` | yes | issue 明确要求 preserve existing formatting | 本次 change 的 must-preserve formatting observation |
| failed-only selects only `FAILED` | starter 不支持 | **新需求** | new specification |

因此 old observation 和 new requirement 不是简单二分。**requirement 提供“默认行为必须保持”的 normative authority，probe 提供“现状具体是什么”的 empirical evidence**；ordering/append/formatting 还被 requirement 特别点名，因而更容易定位 review surface。这个 local preservation obligation 仍然不等于证明所有 observed details 都应成为永久 product contract。

这也解释了 **characterization test** 与 specification-oriented test 的区别。Michael Feathers 用 characterization test 记录软件当前实际行为，使后续修改不会无意改变它。它首先是观测工具，不是价值判断工具。

如果你后来确认某个旧行为是 bug，正确流程不是让 characterization 永久把 bug 神圣化，而是显式进入 behavior change：写新的 specification，让新 test 在修复前失败，再有意识地更新或替换旧 characterization。它的价值在于让变化可见，而不是冻结历史。

## 3. “Legacy”在这里不是年龄，而是一种 change condition

到这里再给本章的术语会更有意义。

Feathers 常用 “code without tests” 作为 legacy code 的强 operational framing。本课程吸收它想强调的风险，但不把它当完整字典定义。一个二十年旧、关键 contract 有强测试且反馈很快的模块，未必是你今天最危险的 change target；昨天由 Agent 生成的四千行新代码，如果只有一个 happy-path smoke test，也可能已经非常难安全修改。

因此本课程使用一个更面向 change 的说法：

> **Legacy condition = 你需要改变代码，但缺少足够快速、可信、与当前变化相关的 feedback。**

年龄、语言、有没有 type hints、代码看起来“老不老”都不是核心变量。真正让风险升高的是 unknown behavior、slow/noisy feedback 和 hard-to-control dependencies。

这个定义也防止我们把 “legacy” 当侮辱词。`legacy_audit.py` 的价值判断此刻并不重要；重要的是：我们要改 `job selection by scope`，而当前对 surrounding effects 的认识还不足以支持一个 behavior-preserving claim。

## 4. 不要先追 coverage：围绕当前 change 画 effect sketch

面对陌生模块，一个看似稳妥的任务是“先把覆盖率补到 90%”。它的问题是没有告诉你 90% 的哪些 execution 与当前风险有关，也没有告诉你 oracle 是否有用。

failed-only 的真正 change point 很窄：**job selection policy**。从这里向外追 observable effects，可以画出：

```text
scope
  |
  v
selected jobs
  |-- count in file
  |-- numbering
  |-- relative ordering
  |-- status / exit / command lines
  |-- written file bytes
  `-- stdout count/path
```

这张图不是完整 system model。它只投影这次 change 的 effect region；没画出的 state、error 或 lifecycle dimension不代表不存在。它的用途是帮助我们问：为了证明“默认行为没被意外改，failed-only 只改变 selection”，哪些 observation 最有信息量？

这就是 **targeted feedback** 的思路。与其广泛给 private helpers 补低信息量 tests，不如优先观察 file bytes、append effect、stdout 和 selection 后的 count/order——因为这些正处在 change cone 上。

这里可以顺便区分三个位置：

- **change point**：真正准备改变行为的位置，例如 job selection；
- **test/control point**：可以控制输入或依赖的位置，例如 environment、module binding、temp directory；
- **observation point**：可以判断行为的地方，例如 written file、stdout、return value 或 post-state。

它们不必在同一个函数里。一个高价值位置甚至可能汇聚很多 upstream path：例如二十个入口最终都经过同一个 serializer，那么 serializer 附近可能成为 Feathers 所说的高-leverage **pinch point**，少量 observation 就能覆盖更大的 effect region。术语本身不用背，重点是学会寻找这种杠杆。

## 5. 为什么这个模块难测？先区分“看不见”和“控制不了”

假设你直接调用 `publish_daily_audit()`。它其实能跑，但结果同时散落在 file、stdout 和 return path；与此同时，真实时钟和 hostname 会让相同 setup 在不同运行里产生不同输出。

这两类困难不一样。Feathers 把它们区分为 **sensing** 与 **separation**。

**Sensing problem** 是：代码能运行，但你看不见或难以判断你关心的 effect。比如 audit 已经成功写盘，可 test 只拿到一个 path string；你还需要读取 file bytes，或者 capture stdout，才能知道 selection/count/formatting 到底发生了什么。

**Separation problem** 是：你无法在受控实验里运行目标代码，因为它会拖入你不想真实使用的 dependency。真实时间会变，真实 hostname 因机器而异，默认 output root 可能写进用户工作目录；一个更重的系统也许构造对象就会连接 production database。

这个 distinction 很实用，因为 remediation 不同。stdout 主要是 sensing：`redirect_stdout` 已经能观察它，没有必要因此设计一个 `Logger` interface。真实 database 连接则主要是 separation：再多 logging 也不能阻止 test 连 production。

Filesystem 在这里同时涉及两边：我们既不想写真实用户目录，又确实需要读取写出的 bytes。一个 temp directory 同时提供 isolation 和 observation，所以往往比“mock 所有 filesystem call”更简单、更真实。

## 6. 现有结构已经给了控制点：现在才需要认识 seam

看 starter probe 怎样让实验变得 deterministic：

```python
os.environ["TASKFORGE_AUDIT_DIR"] = str(root)
os.environ["TASKFORGE_AUDIT_OWNER"] = "course-user"
legacy_audit.datetime = FrozenDateTime
legacy_audit.socket.gethostname = lambda: "lab-host"
```

加上 `tempfile.TemporaryDirectory()` 和 `redirect_stdout`，我们已经可以控制 output root、owner、clock、hostname，并观察 file 与 stdout。注意：**为了得到这些 feedback，production code 一行都还没改。**

这时再引入 **seam** 才有实际对象可指。按照 Feathers 的 seam model，一个 seam 是程序中允许你在不直接修改目标位置的情况下，让这里采用另一种行为的结构机会；真正选择 alternate behavior 的地方叫 **enabling point**。

在这个 Python 例子里，`legacy_audit.datetime` 和 `legacy_audit.socket.gethostname` 的 module binding 就形成了现成 seam。测试把它们替换为 controlled behavior，那个替换动作就是 test harness 中的 enabling point。环境变量提供另一个 control surface；process boundary、function parameter、filesystem root、factory 或语言/链接机制也都可能形成 seam。

这解释了为什么 **seam 不是 interface 的同义词**。你完全可以有 seam 而没有 `ClockProtocol`；也可以拥有很多漂亮 interfaces，却没有一个便宜、可信的反馈路径。

现成 module-binding seam 也不是无条件“好设计”。它依赖 import/binding shape：如果实现从 `from datetime import datetime` 改成另一种 import 方式，monkeypatch target 可能失效。大量 tests 都 patch internal names，也会形成 brittle implementation coupling。因此这里的判断只是：**它目前是否以最低成本提供了足够 feedback？** 不是“以后所有时间依赖都应该 monkeypatch”。

## 7. Characterization 也要验证自己有牙齿

把一个 probe 叫作 characterization，并不会自动让它可信。

当前 `m06_legacy_probe.py` 会检查一些高信息量 fragments 和 stdout write count，并打印 file/stdout fingerprints。这里有一个容易误读的细节：**打印 hash 不等于断言 hash。** 现有 starter probe 并没有把三组 SHA 固化成 exact-byte golden；它的 programmed oracle 比“整个文件必须 byte-for-byte 等于某个 snapshot”更窄。

这反而是很好的阅读练习。你必须区分：

```text
probe printed evidence
!=
probe asserted contract
```

如果 lab 需要更强的 safety net，可以把确认过的 empty/mixed/append/default-owner/stdout observations 提炼成 deterministic characterization tests。但仍然应该围绕 change cone 选择 assertion，不需要为了“覆盖更多” snapshot 整个环境或巨大数据库。

接着做 M03 已经训练过的 negative control：临时把 append 变成 overwrite，或者反转 job order，确认对应 characterization 会失败，然后恢复 production code。若 test 对一个明显违反目标 observation 的 mutant 仍然绿，safety net 只是看起来存在。

测试工具自己也可能带 nondeterminism。Instructor case study 记录过一个很具体的修正：最初直接 hash stdout，但 stdout 含随机 temp path，所以每次 hash 都不同；后来先把 scenario root normalize 成 `<ROOT>` 再 fingerprint。**Golden/hash 本身不是稳定性的来源；你仍然要控制它包含的变量。**

## 8. 找到 seam 以后，最重要的决定可能是：什么都不抽

现在我们终于可以问最容易被“testability”口号遮住的问题：需要把这些 seam 正式变成 production abstractions 吗？

一种 candidate 是增加：

```text
AuditRuntime
ClockProtocol
HostProvider
FileSystem
EnvironmentReader
JobRepository
```

这样每个 dependency 都能显式注入，unit tests 看起来也很整齐。

另一种 candidate 是承认当前 control surfaces 已经够用：time/host 由 module binding 控制，filesystem root 由 env + temp directory 控制，stdout 可 capture，TaskForge state 可以通过已有 service/worker setup 构造。然后 **不做任何 production structural patch**，直接在已有 feedback 下实现最小 behavior delta。

Instructor reference 选择的是第二条路。这不是因为 production dependency abstraction 永远没价值，而是当前 change 只需要改变 job selection；新 object graph 没有解决一个尚未被现有 seam 解决的 current risk。

这正好把 M05 的 evolutionary design 与 M06 接起来：发现一个潜在 abstraction point，不等于已经拥有引入 abstraction 的 design authority。真实 pressure 应该决定它的深度。

当然，也存在第三种合理路径：如果现有 module patching 在真实 repo 中太脆、测试数量开始增长，或者需要在 production 中插入 probe/route old-new implementations，那么把 clock/host 封装成一个很小的 private runtime context 可能值得。Fowler 对 legacy seam 的现代讨论也提醒我们，seam 不只用于 unit test；它还可以服务 observability 或渐进 migration。

但那是**条件性的未来用途**，不能倒推成“既然以后可能迁移，现在就把每个 dependency 抽象一遍”。

### 什么时候不值得新增 seam

三个简单反例足以校正直觉。一个 pure、deterministic dependency 本来就便宜，不需要为了“可测试”套 provider；如果 seam abstraction 比被替换的一行逻辑更复杂，收益很可疑；如果新增 boundary 的唯一价值是让 test 可以断言 `mock.foo.called_once_with(...)`，却不再检查 caller-visible effect，那通常是在把 implementation choreography 当 contract。

所以 M06 的原则不是 “always add seams”，而是：**只有现有结构阻止你获得当前 change 所需的可信 feedback 时，才打开最小控制点。**

## 9. 有了 feedback，才进入新 behavior contract

现在回到真正需求：`failed-only`。

到这个阶段，我们已经把两类东西分开：一类是旧系统在受控实验里表现出来、目前应保守保护的 behavior；另一类是产品现在明确要求新增的 semantics。于是可以第一次写出新 contract：

```text
scope="all"
→ preserve the characterized default behavior relevant to this change

scope="failed"
→ include only jobs whose status is FAILED
→ jobs count equals selected jobs
→ numbering restarts at 01 over selected jobs
→ relative ordering among selected jobs follows existing job order
→ path/date/owner/header/block terminator remain unchanged
→ stdout count equals selected jobs

invalid scope
→ fail before filesystem mutation
```

这里有两个 qualifier 不能丢。

第一，`scope="all"` 的“保持”建立在我们实际 characterized 的 evidence surface 上，不是假装已经证明所有 hidden consumers 和所有可能输入。对于没有调查到的外部 parser、operator script 或异常路径，remaining risk 仍然存在。

第二，invalid scope 的 no-effect guarantee 是**新 contract 明确要求的 boundary semantics**。它复用了 M04 的 reasoning：如果我们要告诉 caller“这个 input 在 effect 之前被拒绝”，validation 就必须发生在 `mkdir/open/write` 之前。不能因为错误最终抛出来了，就自动宣称没有 side effect。

接下来才是普通 red-before / green-after：先写 mixed jobs + `scope="failed"` 的 focused test，确认 starter 因不支持参数而失败；再实现最小 selection logic；同时保留 old characterization，确保 default path 没 drift。

Reference 最小实现甚至不需要 `_select_jobs()` helper：

```python
def publish_daily_audit(scope: str = "all") -> str:
    if scope not in {"all", "failed"}:
        raise ValueError(...)

    ...
    jobs = list(state.jobs.values())
    if scope == "failed":
        jobs = [job for job in jobs if job.status == JobStatus.FAILED]
    ...
```

把两行 selection 抽成 pure helper 当然也可以，但“更容易单测”本身还不足以证明新 abstraction 必要。等 scope 真正扩展到 terminal/active/time range/owner 等多个 policy 时，新的 selection abstraction 可能才更有压力支撑。

## 10. Test fixture 也必须服从已有 state authority

Legacy takeover 很容易让人产生一种错觉：production code 需要谨慎，但 test setup 为了方便可以随便改 state。

Instructor reference 曾经构造两个 failed jobs 时遇到一个真实 fixture 错误。它先留下一个 queued job，再想 `claim_next()` 后直接 finish 后面那个 target；但 TaskForge 的 claim 是 FIFO，实际被 claim 的是前面的 queued job，target 仍处于 `QUEUED`，所以合法地得到：

```text
ValueError: cannot finish job-4 from queued
```

最快的“修复”当然是：

```python
state.jobs[target].status = JobStatus.RUNNING
```

但这会绕过 M01/M02 已经建立的 lifecycle/ownership semantics。测试如果通过作弊 setup 产生一个 production path 无法产生的 pre-state，它的 fidelity 会下降，甚至可能保护错误的 mental model。

Reference 最后调整的是 setup 顺序，让真实 `submit → claim_next → finish` path 产生需要的 states。这个例子很值得保留，因为它提醒我们：**characterization 的可信度不仅取决于 assertion，也取决于输入状态是否通过合法 authority 构造。**

同样，audit 文件本身只是 TaskForge state 的一个 reporting projection：它记录 id、status、exit code、command 等当前需要展示的字段，不因为写进文件就成为 job lifecycle 的第二 authority；没投影的 state dimension 也不能被解释为“不存在”。

## 11. 为什么第一批 legacy tests 不一定应该是 unit tests

`legacy_audit.py` 天然就是一个 integration-shaped function：env + clock + hostname + state 输入，filesystem + stdout 输出。为了第一次 takeover，直接在 tempdir 中运行它并检查 boundary effects，可能比先拆十二个 injectable classes 更安全。

这种较高层 characterization 有明显优点：production diff 可以保持为零；真实 serializer、newline、append 和 ordering 都参与实验；它对第一次理解 unknown behavior 很有 fidelity。

代价也真实存在：它通常更慢，failure localization 较差，setup 更重，也不适合穷举所有 edge cases。等 system model 稳定以后，再增加更 focused 的 tests 可能有价值。

这就是 hermeticity 与 fidelity 的 trade-off。Google testing material 强调 hermetic test 的 determinism/isolation，同时 Larger Testing 也提醒我们 fidelity 是另一个维度。全 mock 的 unit test 可以非常 deterministic，却只验证自己复制出来的 call choreography；tempdir + real formatter 稍重，却可能更接近这次 compatibility risk。

因此不要寻找“最专业的测试层级”。更实用的是一个 evidence portfolio：便宜、稳定的本地 feedback，加上足够真实的 boundary/regression probe。具体比例随系统和风险变化，不是固定 test pyramid 宗教。

## 12. Static reading、history 和 runtime probe 要互相校正

第一次接手陌生代码，只把 repo 从头读到尾并不等于理解完成。更有效的一种工作方式是 hypothesis-driven exploration。

例如你先猜：“daily audit 会 overwrite 当天文件。”然后在同一天受控运行两次，观察到第二个 block 出现在第一个后面，于是更新 model：append 是 observed behavior。

再例如你猜：“job rows 按 id 排序。”构造一个能区分排序与 insertion order 的 scenario，实际观察 current state order，于是承认原 hypothesis 错了。

这种 `hypothesis → probe → observation → model update` 的循环比“读完以后写 architecture summary”更能暴露误解。Agent 尤其需要这个约束：读得多并不等于知道 production runtime、hidden consumer 或 historical quirk。

Repository history、issue、old PR 和 comments 也很有价值。它们可能解释某个奇怪格式为什么存在、某个 workaround 为什么不能删。但 history 可能过时，也可能记录了一个当时就错误的 assumption，更不保证覆盖 unknown consumers。

所以 history 是 evidence，不是 oracle。高质量 takeover 会把 code reading、history、current tests 和 runtime characterization 交叉使用，并允许 unresolved items 继续标 `UNKNOWN`。

## 13. Agent 接管 legacy repo：控制它什么时候有资格写代码

最危险的 prompt 之一是：

```text
Clean up legacy_audit.py, make it testable, and add failed-only mode.
```

它把三个不同任务压成一句话：理解 current behavior、改变 structure、改变 behavior。一个 Agent 很容易一次生成新的 interfaces、dependency container、DTO、tests 和 feature；最终 tree 甚至可能很漂亮，但 reviewer 很难知道哪些旧 behavior 被无意改掉。

更可靠的 Agent workflow 可以围绕 epistemic state 分阶段。

第一阶段只做 read-only reconnaissance：定位 entry points、state reads/writes、side effects、nondeterminism、relevant tests 和 unknowns，并给证据位置。

第二阶段只设计最小 runtime probes，回答 change cone 上最重要的 unknowns；仍然不改 production code。

第三阶段把确认过的 observations 变成 deterministic characterization，并用 negative control 证明 safety net 有牙齿。

第四阶段才问：现有 seam 是否已经足够？如果不够，只打开当前 change 需要的最小 control point，并把这个 structural patch 与 feature 分开；如果已经够，就允许 **no production seam change** 这个答案。

第五阶段在显式新 contract 下实现 requested behavior，展示 fail-before / pass-after，并重跑旧 characterization。

最后让独立 reviewer 不依赖作者总结，检查：requested delta 之外的 characterized behavior 是否保持？seam 是否被无理由扩大？tests 是否保护 effect 而非新 helper choreography？哪些 unknown 仍未闭合？

一个具体 task contract 可以是：

```text
Goal:
- add failed-only audit scope

Before implementation:
- do not edit production code
- characterize empty, mixed, repeated-write, default-owner and stdout behavior
- record observed vs specified vs unknown separately
- map the effect region around job selection

Feedback:
- control clock/host/output root using the cheapest trustworthy mechanism
- verify characterization can fail under at least one relevant negative control
- do not introduce a production dependency framework unless existing control points are insufficient

Behavior change:
- scope=failed includes only FAILED jobs
- scope=all preserves characterized default behavior
- invalid scope fails before filesystem mutation

Non-goals:
- no audit format redesign
- no TaskForge state-ownership rewrite
- no dashboard/public-API cleanup
- no broad DI framework

Evidence:
- show observations before implementation
- show negative-control failure
- show feature red -> green
- re-run old characterization and core tests
```

这个 prompt 的重点不是更长，而是让 Agent 的 write authority 依赖于它已经获得什么 evidence。Agent 可以替你做大量机械探索和实现，但不能靠一句“我已理解现有行为”自行授予修改权限。

## 14. Review legacy change 时，先审 epistemic chain

一个 legacy patch 的 code style 可能很好，tests 也可能全绿，但 reviewer 仍然应该先追一条更基本的链：作者原来不知道什么？用什么 observation 把 unknown 变成 evidence？哪些 observation 被有意识地保护？哪里开始进入新 specification？有没有把自己的新设计误写成历史事实？

围绕这条链，可以压缩成几组 review questions：

**Change understanding**：change point 和 effect region 是否明确？unknown 是否被诚实保留，还是被作者猜成了 contract？

**Feedback**：characterization 是否真的对应当前风险？oracle 是 current observation、written spec 还是新 requirement？有没有验证 test 会 red？

**Control / seam**：当前困难是 sensing、separation 还是两者？已有 control point 是否已经够用？若新增 seam，enabling point 在哪里，scope 是否超过 current change？

**Behavior**：structural preparation 与 requested delta 是否分开？默认 append/order/format 等 characterized behavior 是否被无意识“clean up”？invalid input 的 no-effect claim 是否真的发生在 mutation 前？

**Remaining risk**：哪些 behavior 仍然 unknown？哪些 consumer 没调查？哪些高-fidelity scenario 没跑？是否需要后续 compatibility work 或 production observation？

尤其不要把 “characterized” 自动翻译成 “forever public contract”。M08 会专门处理 unknown consumers、compatibility 和 migration。M06 只要求你在证据不足时不要无意识破坏现状，并在决定改变时明确宣布 delta。

## 15. Legacy system 不会因为一次“现代化”突然毕业

M06 的目标也不是把一个系统从 `legacy` 一次性改造成 `modern`。

更现实的变化是累积式的：change A 让你建立一组 characterization；change B 迫使你打开一个小 seam；change C 让某个过去模糊的 boundary 得到明确 contract。几轮以后，系统的 unknowns 变少、feedback 变快、boundaries 更清楚。

这也是为什么三行 control point 加两条高信息量 tests，有时比一次 architecture rewrite 更有工程价值。一次 change 没必要顺便建立新 domain layer、repository layer、adapter layer 和 event bus；除非当前 pressure 真正需要它们。

当某个 seam 在多次变化中反复显示稳定价值，它可能逐渐上升成更正式的 architectural boundary；当一个 observed quirk 被证明没有 consumer 或已完成 migration，它也可以被显式删除。**渐进式“去 legacy 化”是持续减少 change uncertainty，不是追求某一种现代代码外形。**

## 16. 来源边界与本章不能推出的结论

本章主干来自 Michael Feathers 的 *Working Effectively with Legacy Code*：working with feedback、sensing/separation、seam/enabling point、characterization 和 targeted testing。课程采用这些 decision models，而不是照搬 2004 年 Java/C++/C# 背景下的 dependency-breaking technique catalog。

Martin Fowler 的 `Legacy Seam` 用现代语言补充 seam：它不只可用于 unit-test dependency substitution，也可能支持 probe、observability 或渐进 displacement。Google testing material用来校正另一个方向的误区：hermeticity 很重要，但 isolation 与 fidelity 是不同维度，test doubles 过度绑定 implementation 会产生维护成本。

有几项表述明确属于课程 synthesis：`Legacy condition = change without enough trustworthy change-relevant feedback` 是对 Feathers framing 的扩展，不是他的字典定义；effect sketch、Agent staged takeover/task contract 和“write authority 依赖 evidence”的表达也是本课程把这些来源与前置模块组合后的工作模型。

因此本章不能推出这些规则：旧代码就是坏代码；没有 tests 的代码都必须先全面补 coverage；characterization 证明当前 behavior 正确；所有 observed behavior 都要永久保留；seam 必须是 interface/DI；发现 seam 就应该 formalize；unit test 永远比 process/integration probe 好；Agent 读完整个 repo 就可以直接重构。

真正要带走的是一条更窄的 reasoning chain：

```text
requested change
→ admit what is unknown
→ read and form hypotheses
→ run targeted probes
→ separate observed behavior from intended contract
→ build characterization with a real oracle
→ distinguish sensing from separation
→ reuse or open the smallest sufficient control point
→ make the requested behavior change explicitly
→ preserve evidence outside the intended delta
→ record remaining uncertainty
```

下一章 M07 会再拿走一个舒适条件：即使你已有测试、control points 和清楚的 single-thread behavior，并发、cancellation、retry、crash 与 restart 仍会让 temporal/lifecycle reasoning 变得困难。

## 可选原始资料

本章自包含；希望核对原始观点时可看：

- Michael Feathers, *Working Effectively with Legacy Code* public samples / TOC: https://www.informit.com/store/working-effectively-with-legacy-code-9780132931779
- Feathers, *Testing Effectively With Legacy Code*: https://www.informit.com/articles/article.aspx?p=359417
- Feathers, *Changing Software and Legacy Code*: https://www.informit.com/articles/article.aspx?p=359418
- Martin Fowler, `Legacy Seam`: https://martinfowler.com/bliki/LegacySeam.html
- *Software Engineering at Google*, Testing Overview: https://abseil.io/resources/swe-book/html/ch11.html
- *Software Engineering at Google*, Test Doubles: https://abseil.io/resources/swe-book/html/ch13.html
- *Software Engineering at Google*, Larger Testing: https://abseil.io/resources/swe-book/html/ch14.html

具体来源审计与取舍见 [`../reading-notes/m06-source-audit.md`](../reading-notes/m06-source-audit.md)。