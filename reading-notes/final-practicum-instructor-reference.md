---
id: practicum-click-instructor-reference
type: practicum
visibility: instructor
related: [practicum-click]
---
# Final Transfer Practicum — Instructor Reference

> **Instructor / post-submission material.** Student first-pass review 完成前不要提供本文件。后续网站必须在 build/export 层排除 instructor visibility；CSS 隐藏不算隔离。
>
> 本文件不是“标准答案 patch”。它记录 frozen repo 的已核事实、task adaptation、可接受判断空间、dangerous designs、counterexamples 与 pilot evidence。

## 1. Provenance：真实 repo + 课程改写的 stakeholder issue

Practicum 使用 Pallets Click，upstream：

- [1. Provenance：真实 repo + 课程改写的 stakeholder issue](https://github.com/pallets/click)
- BSD-3-Clause
- frozen commit `333c28d79cd982990ee98eef61ec20ab1a4f38ba`（2026-07-17）

选择点在 upstream PR #3704（`Deprecate isolated_filesystem and document its limits`）之前。真实 upstream history 提供了这组 pressure：

- issue #3501 讨论 `isolated_filesystem()` thread safety；maintainer 明确指出它调用 process-global `os.chdir`，且同进程线程安全/serialization 更应由 test framework 管理；
- issue #3700 决定 deprecate `isolated_filesystem()`；
- PR #3704 最终做 deprecation、docs/test migration；
- 更早的 #2993 / stream-lifecycle history 已经表明 Click testing 与 threads 不是课程凭空加入的主题。

**Student `ISSUE.md` 不是 upstream issue 的逐字复制。** 课程故意把真实 pressure 改写成一个 plausible stakeholder overclaim：要求 same-process true parallel isolation、source compatibility、no subprocess，并建议 per-runner filesystem root。这是 course task design，用来测试 issue review；不要把这段 stakeholder wording 归给 Pallets maintainers。

Checkpoint 的 maintainer reply 与真实 upstream direction 一致，但仍是课程 authority artifact，不是假装 upstream PR body。

## 2. Frozen system model

### 2.1 `CliRunner.invoke()` 并不运行在独立 runtime

Relevant path 集中在 `src/click/testing.py`，但只读这个文件仍不够。`CliRunner.invoke()` 最终执行的是任意 user `Command.main()` / callback；callback 可以调用 Python 标准 `open()`、`Path()`、第三方库或任意 process API。Click 没有一个统一 filesystem abstraction 可以透明拦截所有 relative-path access。

### 2.2 `CliRunner.isolation()` 修改 interpreter-global state

Frozen implementation 在 invocation isolation 期间至少：

- 保存/替换 `sys.stdin`；
- 保存/替换 `sys.stdout`；
- 保存/替换 `sys.stderr`；
- 修改并在退出时恢复 `os.environ` 的 override；
- 安装/恢复 Click prompt/getchar helpers 与 stream state。

Testing docs 在 frozen revision 已说明 helpers 为 simplicity 修改整个 interpreter state，并非 thread-safe。这是 current documentation evidence，不需要看未来 issue 才能发现。

### 2.3 `isolated_filesystem()` 修改 process cwd

Frozen helper：

1. 记录 `cwd = os.getcwd()`；
2. 创建或选择 temp directory；
3. `os.chdir(dt)`；
4. yield；
5. finally `os.chdir(cwd)` 并按既有规则 cleanup。

`os.chdir` 是 process-global。runner instance 并不拥有“自己的 cwd”。

### 2.4 Public/compatibility surface

`CliRunner` / `isolated_filesystem()` 是 documented testing API；已有 external callers 可能依赖：

- context manager source shape；
- enter 后 relative path 的真实 process cwd semantics；
- yielded temp directory；
- optional caller-supplied temp dir 不自动删除的 behavior；
- exception/finally 后 cwd restoration；
- current invocation capture/env behavior。

Deprecation 不授权在 8.x 偷改这些 semantics。

## 3. 为什么 initial issue 不能按字面直接实现

Literal request 同时要求：

- arbitrary existing command 不修改；
- two runners 在同一 interpreter 真正并发；
- relative filesystem behavior 相互隔离；
- 不用 subprocess；
- suggested per-runner root 应透明工作。

一个 `CliRunner.filesystem_root` field 只能被 Click 自己读取；它不能改变：

```python
open("relative.txt")
Path("relative.txt")
os.getcwd()
third_party_library_that_opens_relative_paths()
```

在 arbitrary callback 中的含义。若继续用 `os.chdir`，它又是 process-global；若不用 `os.chdir`，就破坏现有 arbitrary command 的 relative-path behavior。这里缺少 mechanism/authority，不是“再找一个 helper”能补上的 implementation gap。

同时，即使 filesystem 单独解决，`CliRunner.isolation()` 仍修改 stdio/env 等 interpreter-global state；“filesystem safe”不能升级成 whole-runner concurrent-safe。

因此高质量 first-pass 可以是 `NEEDS_DECISION` / `STOP_AND_ESCALATE`。强迫学生此时先写 patch 反而违反 practicum 目标。

## 4. Deterministic high-information counterexample

Instructor 实际在 frozen revision 运行：

```python
import threading
from pathlib import Path
from click.testing import CliRunner

runner = CliRunner()
entered = threading.Event()
release = threading.Event()
observed = {}


def invoke_context():
    with runner.isolated_filesystem():
        observed["runner"] = Path.cwd()
        entered.set()
        assert release.wait(5)


t = threading.Thread(target=invoke_context)
t.start()
assert entered.wait(5)

observed["observer"] = Path.cwd()
Path("observer-marker.txt").write_text("observer")
observed["marker"] = Path("observer-marker.txt").resolve()

release.set()
t.join(5)
```

Observed：

```text
observer cwd == runner temporary cwd
observer-marker.txt lands inside runner temporary directory
```

这个 probe 很有区分力，因为 observer thread **完全不调用 Click**。所以：

- runner-local field 不能保护它；
- “只给 `CliRunner` method 加锁”也不能保护它，observer 不会获取那个 lock；
- 反复 stress 不是必要 evidence，barrier/event 已确定性制造 overlap。

这条 probe 是 instructor evidence，不要求 student 恰好写同一段代码。任何能证明同一 semantic fact 的独立 counterexample 都应接受。

## 5. First-pass acceptable response families

在 checkpoint 之前，不应把“deprecate helper”提前升级成唯一答案。至少有几类合理 proposal，前提不同：

### Family A — 改 product requirement / execution model

承认真正 isolation 是 process boundary concern；使用 pytest-xdist/process workers/subprocess 等。满足强 isolation，但违反 stakeholder 的 no-subprocess preference，因此需要 decision。

### Family B — 明确 unsupported same-process concurrency，由 framework serialization

保留现有 helper，要求同一 interpreter 串行化相关 tests。变化最小，但不满足 stakeholder 的 true parallel performance goal，也需要 decision。

### Family C — 迁移离开 process-global convenience helper

Deprecate `isolated_filesystem()`，新 tests 用 caller/framework-owned temp dirs；existing API 暂时保持 compatibility。它减少 Click 自己鼓励 global cwd mutation，但**不声称整个 CliRunner 变 thread-safe**。

### Family D — 新 filesystem abstraction / command contract

只有在愿意改变 application contract，让 command 所有 file access 都经过显式 filesystem capability 时才可能真正 virtualize cwd。对 arbitrary existing Click command 不 source-compatible，因此不能作为 literal-request 的“内部重构”偷偷实施。

## 6. Checkpoint authority

课程 checkpoint 选择 Family C 的兼容迁移方向：

- 不承诺 same-process concurrent runner safety；
- 8.x 保持 API source-compatible；
- deprecate `isolated_filesystem()`；
- preserve existing non-concurrent semantics；
- docs 推荐 caller/test-framework temp dir（pytest `tmp_path`）；
- Click 自己的 tests 尽量迁移；
- no global lock / VFS / subprocess runner / new public FS API；
- breaking removal 留给未来 major authority。

这是**新的 maintainer decision**。学生应该 append issue-review addendum，而不是把 first-pass 改成“我一开始就知道”。

## 7. Candidate implementation acceptance space

Reference patch 不是唯一答案。一个 acceptable candidate 通常需要满足：

- warning 在使用 deprecated context manager 时触发，而不是让所有 `CliRunner` 用户无条件收到 warning；
- 使用适当 deprecation category / stacklevel，使 caller 能定位自己的 call site；
- helper body/cleanup semantics 保持；
- docs 不再把 helper 当新测试默认方案；
- docs 明确 `CliRunner` 使用 interpreter-global state、same-process concurrent invocations unsupported；
- internal test migration 不改变原 test 实际想验证的 semantic boundary；
- release/changelog/upgrade guidance 与 repo conventions 一致；
- full minimal suite + focused warning evidence green。

Internal test migration 可以有多个合理形状。例如：

- 用 `tmp_path` 构造 explicit file path；
- 当被测 behavior 本身依赖 cwd 时，用 pytest `monkeypatch.chdir(tmp_path)` 明确把 process-global setup 归给 test framework；
- 对真正只需要 caller-owned directory 的 case，直接把 path 参数传给 command/helper。

不能为了“消灭 grep occurrence”改变 command semantics。

## 8. Plausible wrong implementations

### Wrong A — global lock + “thread-safe” docs

可能让两个 cooperative runner calls 不重叠，但：

- stakeholder 明确要 true parallel；
- unrelated threads 不获取 lock；
- cwd/env/stdio 仍 process-global；
- docs guarantee 比 mechanism 更强。

### Wrong B — `filesystem_root` + path joining inside Click only

无法透明改变 arbitrary callback / third-party relative file access。可能新 tests 只覆盖 Click-owned helpers而 green，却没有覆盖 user command contract。

### Wrong C — deprecation warning but helper semantics drift

例如改变 cleanup、yielded path、custom `temp_dir` lifecycle；“反正 deprecated”不是 compatibility waiver。

### Wrong D — 把所有 internal tests机械改成 absolute paths

可能让 test 不再验证原本的 cwd-dependent CLI behavior，只是为了减少 helper occurrence。每个迁移都要问原 oracle 到底保护什么。

### Wrong E — docs 只说 filesystem helper deprecated，却暗示其它 `CliRunner` isolation 可并发

整个 invocation 还有 stdio/env global mutation。Scope wording 必须精确。

## 9. Review rubric

Independent reviewer 应优先检查：

1. candidate 是否与 checkpoint authority 一致；
2. warning timing/category/stacklevel 与 compatibility；
3. internal test migration 有没有降低 fidelity 或改 oracle；
4. docs 是否仍有旧推荐/互相矛盾的 thread-safety claim；
5. 是否引入 lock/VFS/new API 等未授权 scope；
6. full suite 是否真的运行，focused test 是否会在 missing-warning / behavior drift 下 fail；
7. candidate 是否错误声称解决 same-process concurrency。

Nits 不应掩盖上述 contract findings。

## 10. Rollout / reversal reference

这是 library deprecation，不是真实 durable-state migration：

- 8.x release 必须保留 runtime behavior并发出 migration signal；
- downstream 用户可以逐步改到 `tmp_path` / own temp dirs；
- package rollback 可以恢复 warning/runtime package behavior，但已经修改的 downstream tests/docs 不会“自动回滚”；
- removal 或更强 concurrency contract 都需要未来独立 authority；
- deprecation telemetry 很有限，不能假装知道整个生态 adoption；release notes/upgrade guide 是主要 communication artifact。

## 11. Candidate-selection comparison

课程维护侧另有完整 5-repo candidate audit 作为 internal provenance record。HTTPX 0.27.2 是第二名：TLS migration/compatibility pressure 很强，focused harness `31 passed`/约 5s；但 official dev bootstrap 实测约 167s，必须另做教学 setup。Click 在 setup、system-model breadth、historical pressure 与 unfamiliar-domain transfer 之间更均衡。

## 12. Pilot record

课程维护侧另有完整 coding-agent + independent-review pilot record，作为 internal validation provenance。本节只保留 acceptance principle：pilot 的 Agent patch 只是对 task/harness 的一次 empirical sample，不能升级成唯一 student answer，也不能从一次模型表现推出通用 productivity 数字。
