---
id: practicum-candidate-audit
type: reference
visibility: internal
related: [final-practicum]
---
# Final Transfer Practicum — Candidate Audit

> 本记录对应 issue #3。目标不是给 Final Practicum 找一个“著名项目”，而是实际比较几个真实 OSS 在陌生仓库建模、change judgment、Agent orchestration 与 evidence review 上的教学 fit。
>
> 审计日期：2026-09-08。候选工作副本放在课程仓库外的 scratch workspace；课程仓库不 vendoring 这些项目源码。

## 1. 选择标准

候选必须同时满足几类约束：

- **需要 system modeling**：不能一眼把全部 control/data flow 装进工作记忆，但也不能大到主要难度变成搜索耐力；
- **有真实 contract surface**：API、CLI、filesystem、protocol、configuration 或长期兼容行为至少有一类真实 consumer；
- **tests 足够强但不是完整 oracle**：能够提供 baseline，也允许 reviewer 构造 tests 没覆盖的 counterexample；
- **历史可读**：旧 issue/PR/changelog 能提供真实设计和兼容性证据，而不是只有代码快照；
- **setup 可控**：最终 timed practicum 不应主要花在容器、云凭据、编译器或 release tooling；
- **与 TaskForge 不同**：优先 CLI/tooling/library，而不是后台 job queue；
- **许可允许固定 revision**：若未来需要 teaching fork，必须能保留 provenance/license；本轮优先不 fork，只固定 upstream revision。

LOC 只作为诊断，不作为硬阈值。真正重要的是 change 是否跨越多个边界、学生是否必须自己建立 model。

## 2. 五个实际候选

| Candidate | Snapshot used for audit | Language / rough shape | License | Baseline evidence | Teaching fit | Main cost |
|---|---|---|---|---|---|---|
| Pallets Click | `6aabf099bfdd4c1e75fe8d0e0d4241372b988ab1` | Python CLI framework；约 177 tracked files，source/tests 数万行 | BSD-3-Clause | current HEAD `2059 passed, 24 skipped, 1 xfailed`；test phase约 5.5s | 很强：public API、parser/context/testing、stdio/env/filesystem global state、Windows/shell compatibility、长期 deprecation history | 默认 `uv` dev groups 会多装 lint/type tooling；需给 minimal test command |
| spf13/cobra | `adbc8813901bba65827259daa8e22ff94ec1f30e` | Go CLI framework；约 66 tracked files，约 16.8k Go source/tests | Apache-2.0 | `go test ./...` 约 2.4s | 强：command tree、flags、shell completion、`os.Args`、兼容行为；setup 极轻 | 复杂度较集中在 `command.go` / completion surface，整体 model 较快可恢复 |
| sharkdp/fd | `bb80489efb9fe2bdeabe1844feb5ee0af6fc9b1c` | Rust filesystem CLI；约 60 tracked files，约 8.3k Rust source/tests | Apache-2.0 + MIT | `111 passed`；test 本身约 0.75s | 强：filesystem、ignore、symlink、path/output semantics，真实 platform failure surface | 首次 `cargo test` 约 70s、峰值约 794MB RSS；Rust/toolchain 成本容易污染 timed practicum |
| encode/httpx | `b5addb64f0161ff6bfe94c124ef76f6a1fba5254` | Python HTTP client；sync/async、transport、TLS、proxy、auth 等多个 boundary | BSD-3-Clause | 官方 bootstrap 首次 setup 实测约 167s；另见 frozen pilot 的 lean TLS harness | 很强：public API、environment、transport、release compatibility、migration | 官方 dev environment 同时安装 docs/release tooling，直接照搬不适合 practicum |
| pytest-dev/pluggy | `4821148db2f4c6daa62ad8bdcae2918ecf27a731` | Python plugin framework；约 79 tracked files，约 5.7k Python source/tests | MIT | `144 passed in 0.21s`；首次环境约 18.7s | 语义深：hook ordering、wrapper、plugin registration、downstream compatibility | 核心体量偏小，熟练学生较容易整体装进工作记忆，system-model pressure 不够稳定 |

这些结果来自真实 clone/build/test，不是 README 推测。

## 3. 历史质量抽查

### Click

近期历史里同时存在：

- `Command.main()` 的 late `KeyboardInterrupt` race（PR #3818）；
- `CliRunner.isolated_filesystem()` 的 thread-safety / deprecation 讨论（issues #3501/#3700，PR #3704）；
- `help` 参数 collision 改变 parser/public semantics（PR #3678）；
- shell completion、Windows error、stream lifecycle 等跨平台兼容变更。

这说明 Click 的真实维护工作不是单一 parser bug：同一个 public testing helper 会触碰 cwd、environment、stdio、filesystem cleanup 和 test-framework assumptions。

### Cobra

抽查到 completion 修改 `os.Args`、不同 shell completion quoting、flag parsing 与 platform test failures。它有真实 contract，但很多难点集中在 completion subsystem；作为最终 transfer 环境略窄于 Click。

### fd

抽查到 path-separator semantics、invalid cwd、symlink、error-message escaping、timestamp panic 与 performance regression。failure surface 很真实，但编译/toolchain 成本是明显负担。

### HTTPX

抽查到 0.28 TLS/API upgrade、URL/query behavior、proxy schemes 与 transport API。它是 migration/compatibility 训练的优秀候选，但官方 `scripts/install` 将 docs、packaging、Twine、MkDocs、mypy 等一并安装；教学环境若采用 HTTPX 必须自己提供 lean setup。

### pluggy

hook ordering、multi-impl unregister、Python-version annotation compatibility 与 downstream breakage 都很真实。缺点不是“太简单”，而是 repo 尺寸和中心 abstraction 数量使完整 mental model 相对容易恢复，不足以稳定测量陌生仓库 decomposition。

## 4. Top-two frozen pilot

最终进入 pilot 的是 Click 与 HTTPX。两者都不使用 current HEAD，而固定在真实 change pressure 之前。

### 4.1 Click frozen revision

选择：

```text
333c28d79cd982990ee98eef61ec20ab1a4f38ba
2026-07-17
Mark clearly functions private status. Deprecated Python 2 utilities. (#3695)
```

这是 `isolated_filesystem()` deprecation PR #3704 之前的 revision。此时：

- `CliRunner.isolation()` 会替换 `sys.stdin/stdout/stderr` 并修改 `os.environ`；
- `CliRunner.isolated_filesystem()` 会调用 `os.chdir()`；
- testing docs 已直接说明这些 helpers 会改变整个 interpreter state，**not thread-safe**；
- 更早历史里已经有 `StreamMixer` 多线程 race 与 thread-related tests，因此“threading”不是 instructor 凭空植入的秘密 clue。

为避免答案泄漏，pilot 不是普通 `git worktree`。普通 worktree 会共享未来 refs，Agent 可以 `git log --all` 看到后来的真实修复。实际 frozen student repo 只 fetch 到上面这个 SHA 的可达历史，然后删除 remote；验证 `--all` 没有任何 post-HEAD commit。

最小 baseline：

```bash
uv run --no-default-groups --group tests pytest -q
```

实测：

```text
1915 passed, 24 skipped, 31000 deselected, 1 xfailed in 2.90s
wall clock ≈ 4.03s
```

因此环境不会成为主要难度。

### 4.2 HTTPX frozen revision

选择 release tag `0.27.2`：

```text
609df7ecc0f7cb10a1c998aa9c269bba77337c5f
2024-08-27
```

这是 0.28 TLS simplification / compatibility change 之前的 stable release。此时 public behavior 明确包括：

- `verify` 接受 bool、path string、`ssl.SSLContext`；
- `cert` 仍是 public argument；
- `trust_env=True` 时 `SSL_CERT_FILE` / `SSL_CERT_DIR` 参与 TLS configuration；
- tests 与 docs 都明确记录这些行为。

官方全量 dev bootstrap 在当前网络环境首次安装约 **167s**，主要成本来自 docs/release/type tooling；这对 timed practicum 不合格。但只为 TLS pilot 建最小环境后：

```text
tests/test_config.py: 31 passed in 0.46s
wall clock ≈ 5.01s
```

所以 HTTPX 的问题是官方 bootstrap topology，而不是 core testability。

## 5. 两个 pilot issue 都不是“寻宝题”

### Click pilot pressure

Stakeholder request 表面要求：让多个 `CliRunner` 在同一 Python process 中并发执行，给每个 runner 一个 filesystem root，保持 source compatibility，不用 subprocess。

不用知道未来 PR，也能从 current repo 推出 contradiction。Instructor 实际运行了一个 deterministic probe：一个线程进入 `runner.isolated_filesystem()` 后停在 barrier，另一个完全不调用 Click 的线程读取 cwd 并用相对路径写文件。观察到：

```text
observer_cwd == runner_temp
observer-marker.txt 被写入 runner 的 temporary directory
```

因此仅给 runner 增加 instance field 或只给 runner invocation 加锁，都不能把 Python 进程的 cwd 虚拟成 thread-local。更广的 `CliRunner.isolation()` 还修改 env/stdin/stdout/stderr。这个风险由 system model 自然推出，不依赖 secret buggy line。

可以合理比较的 response family 至少包括：

1. 改产品要求：不承诺 same-process parallel runner isolation，把 serialization/process isolation 交给 test framework；
2. 迁移/弃用 process-global helper，鼓励 caller-owned temp directory（例如 pytest `tmp_path`），同时保持旧 API 一段兼容期；
3. 真正 redesign application/filesystem boundary，但这无法在“任意现有 Click command source-compatible”前提下透明拦截 `open("relative")` / `Path("relative")`，因此需要更大的 contract change。

### HTTPX pilot pressure

Stakeholder request 表面要求在 0.28 删除 verify-path/cert/env CA support，同时宣称普通 `verify=True/False` 用户无行为变化。

当前 repo 自己已经提供 counterexample：

```bash
pytest -q \
  'tests/test_config.py::test_load_ssl_config_verify_env_file[SSL_CERT_FILE]' \
  'tests/test_config.py::test_load_ssl_config_verify_env_file[SSL_CERT_DIR]'
```

实测 `2 passed`。这两条测试说明 `verify=True + trust_env=True` 的 standard path 本来就会服从 environment CA；“删除 env support”与“standard verify=True behavior unchanged”不能同时成为无条件 claim。

合理 family 包括 staged deprecation/compat window，以及由 release/product authority 明确批准 breaking change 后的 immediate migration；还可以把“简化 verify/cert API”与“是否继续保留 env trust”拆成两个 decision，而不是把它们绑成一个 implementation cleanup。

## 6. 选择结论：Click

最终建议选 **Click frozen at `333c28d...`**。

不是因为 Click 更有名，而是它在本轮实际审计里拥有更好的综合教学 fit：

- domain 与 TaskForge 足够远：CLI library / testing helper；
- setup 快，Python incidental complexity 低；
- 学生必须跨 `testing.py`、command invocation、docs、tests、history 与 process-global runtime state 建 model；
- issue 的错误不是“藏着一个 race”，而是 requirement 与 process semantics 的冲突；
- 正确结果允许 escalation，而不是强迫 patch；
- maintainer decision 后又可以继续做 compatibility-safe deprecation/test migration，覆盖真实 implementation、evidence 与 review；
- history 本身足够丰富，可用于 archaeology，但 frozen cutoff 可以可靠阻止未来答案通过 Git refs 泄漏。

HTTPX 保留为很好的替代 practicum，尤其适合以后设计 migration-focused variant；本轮不选它的主要原因是教学 harness 需要额外裁剪，且 TLS/release compatibility 任务更容易收敛成单一 API migration，而 Click 的 process-global boundary 能更广地测量 system modeling。

## 7. 课程 fork / provenance 决定

本轮**不维护 Click teaching fork，也不 vendoring Click source**。Student setup 只做：

1. 从 `https://github.com/pallets/click.git` fetch 固定 SHA；
2. 保留仅截至该 SHA 的历史；
3. 校验 HEAD；
4. 删除 upstream remote；
5. 创建本地 `practicum-work` branch。

这样：

- upstream source 仍由 Pallets Click 的 BSD-3-Clause license 覆盖；
- 课程只发布自己的 task/bootstrap/instructor artifacts；
- provenance 与 frozen revision 明确；
- 不会因为普通 clone/worktree 暴露 future commits。

如果未来网站要提供预打包 student archive，archive 必须保留 Click license/provenance，并在 build/export 层排除 instructor material；不能只靠 CSS 隐藏。

## 8. Issue #3 closure status

候选审计之后要求的 practicum closure work 已经完成：

- student task、A–J deliverables 与 grading rubric 已落地；
- bootstrap/frozen-history isolation 已从空目录重放，保留 3296 个 pre-freeze commits，full baseline 仍为 `1915 passed`；
- instructor reference 记录 system model、multiple acceptable response families、dangerous designs 与 deterministic counterexample；
- bounded coding-agent implementation 已完成，随后由未读取 implementation summary 的独立 reviewer 给出 `APPROVE`；
- vague direct-request 对照得到 `1919 passed` 的 green candidate，但被独立 subprocess counterexample 击穿其 filesystem-isolation guarantee；
- pilot 暴露出“pytest 不验证 Sphinx docs”这一 evidence gap，student task / Evidence Packet 已据此增加 conditional artifact-build validation；
- 顶层 README 已把它明确列为 **Final Transfer Practicum，而不是 M14**。

完整 empirical record 见 [`final-practicum-pilot.md`](final-practicum-pilot.md)。网站公开版如何在 build/export 层真正隔离 instructor material，仍留给后续 content information architecture issue。
